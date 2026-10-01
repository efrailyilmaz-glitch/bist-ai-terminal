"""Fixed-rule, next-open research. Never authorizes an order or claims live alpha."""
from __future__ import annotations
import hashlib, json, re, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from .market_data import yahoo_rows
from .research_data import daily_frame, align_daily

PROTOCOL = 'edge-1.0'
RULES = [
    {'id':'relative_momentum','name':'Göreli momentum','horizon':20,
     'rule':'Son 21 bar hariç 252 bar getirisi XU100 üstünde ve pozitif; hisse ve endeks SMA200 üstünde.'},
    {'id':'trend_pullback','name':'Trend içinde geri çekilme','horizon':5,
     'rule':'Hisse ve XU100 SMA200 üstünde; hissenin 5 bar getirisi en fazla −%3 ve XU100 gerisinde.'},
    {'id':'volume_breakout','name':'Hacim destekli kırılım','horizon':20,
     'rule':'Kapanış önceki 60 kapanışın maksimumunu aşıyor; hacim önceki 20 bar ortalamasının 1,5 katı; XU100 SMA200 üstünde.'},
]
PROTOCOL_HASH = hashlib.sha256(json.dumps({'version':PROTOCOL,'rules':RULES,'split':.65,
    'entry':'next_open','exit':'entry_plus_horizon_open','cost':'round_trip_bps',
    'band':'descriptive_moving_block_bootstrap_extreme_quantiles'},sort_keys=True).encode()).hexdigest()[:16]
_CACHE={}; _LOCK=threading.Lock()


def signals(stock, bench):
    c=stock.Close; b=bench.Close
    trend=(c>c.rolling(200).mean()) & (b>b.rolling(200).mean())
    m=c.shift(21)/c.shift(252)-1; bm=b.shift(21)/b.shift(252)-1
    return {
        'relative_momentum':((m>0)&(m>bm)&trend).fillna(False),
        'trend_pullback':((c.pct_change(5)<=-.03)&(c.pct_change(5)<b.pct_change(5))&trend).fillna(False),
        'volume_breakout':((c>c.shift(1).rolling(60).max()) &
            (stock.Volume>1.5*stock.Volume.shift(1).rolling(20).mean()) &
            (b>b.rolling(200).mean())).fillna(False),
    }


def trades(stock, bench, mask, horizon, start, stop, cost_bps):
    """Signal at t close, entry t+1 open, exit t+1+h open; no overlap."""
    result=[]; next_signal=start; skipped=0
    for i in range(start,stop-horizon-1):
        if i<next_signal or not bool(mask.iloc[i]): continue
        entry=i+1; end=entry+horizon
        s=stock.iloc[i:end+1]; b=bench.iloc[i:end+1]
        # An unresolved calendar window is never silently treated as a fill.
        # Do not censor using future intraday ranges/volumes after the opening exit.
        gaps=any(not np.all(np.diff(f['_source_pos'])==1) for f in (s,b))
        blocked=gaps
        if blocked:
            skipped+=1; next_signal=end
            continue
        gross=float((stock.Open.iloc[end]/stock.Open.iloc[entry]-1)*100)
        baseline=float((bench.Open.iloc[end]/bench.Open.iloc[entry]-1)*100)
        net=gross-cost_bps/100
        result.append({'signal_date':str(stock.time.iloc[i]),'entry_date':str(stock.time.iloc[entry]),
            'exit_date':str(stock.time.iloc[end]),'signal_index':i,'entry_index':entry,'exit_index':end,
            'gross_pct':gross,'net_pct':net,'benchmark_pct':baseline,'excess_pct':net-baseline,
            'stress_excess_pct':gross-2*cost_bps/100-baseline,
            'entry_gap_pct':float((stock.Open.iloc[entry]/stock.Close.iloc[i]-1)*100),
            'worst_excursion_pct':float((stock.Low.iloc[entry:end].min()/stock.Open.iloc[entry]-1)*100),
            'regime':'UP' if bench.Close.iloc[i]>bench.Close.iloc[i-60] else 'WEAK_UP'})
        next_signal=end  # Another close signal may follow that day's opening exit.
    return result,skipped


def mean_interval(values):
    """Descriptive resampling band. NOT a calibrated confidence interval."""
    a=np.asarray(values,float); n=len(a)
    if n<12:return None
    rng=np.random.default_rng(20261001); block=max(2,int(np.sqrt(n)))
    starts=rng.integers(0,n,size=(2500,int(np.ceil(n/block))))
    ix=(starts[:,:,None]+np.arange(block))%n
    means=a[ix.reshape(2500,-1)[:,:n]].mean(axis=1)
    return [round(float(v),3) for v in np.quantile(means,[.05/6,1-.05/6])]


def summarize(rows):
    if not rows:return {'n':0,'mean_net_pct':None,'mean_excess_pct':None,'resampling_band':None,
        'stress_excess_pct':None,'positive_pct':None,'worst_trade_pct':None,'break_even_cost_bps':None}
    vals=np.array([r['excess_pct'] for r in rows]); net=np.array([r['net_pct'] for r in rows])
    return {'n':len(rows),'mean_net_pct':round(float(net.mean()),3),
        'mean_excess_pct':round(float(vals.mean()),3),'resampling_band':mean_interval(vals),
        'stress_excess_pct':round(float(np.mean([r['stress_excess_pct'] for r in rows])),3),
        'positive_pct':round(float((net>0).mean()*100),1),
        'worst_trade_pct':round(float(net.min()),3),
        'break_even_cost_bps':round(float(np.mean([r['gross_pct']-r['benchmark_pct'] for r in rows]))*100,1)}


def analyze(stock, bench, ticker='TEST', cost_bps=30):
    stock,bench,audit=align_daily(stock,bench); n=len(stock)
    if n<900:return {'status':'INSUFFICIENT_DATA','bars':n,'alignment':audit}
    masks=signals(stock,bench); split=int(n*.65); results=[]
    for spec in RULES:
        early,skip1=trades(stock,bench,masks[spec['id']],spec['horizon'],252,split,cost_bps)
        late,skip2=trades(stock,bench,masks[spec['id']],spec['horizon'],split,n,cost_bps)
        es=summarize(early); ls=summarize(late); ci=ls['resampling_band']; reasons=[]
        if skip1+skip2:reasons.append('Çözülemeyen tarih pencereleri var; yalnız hesaplanabilen işlemlerin ortalaması seçim yanlılığı içerebilir.')
        if audit['internal_unmatched_dates']:reasons.append('Ortak dönemde eksik tarihler var; göstergelerin geçmiş pencereleri etkilenebilir.')
        if ls['n']<20:reasons.append('Son dönem örnek sayısı 20 altında.')
        if ci is None or ci[0]<=0:reasons.append('Betimsel yeniden örnekleme bandı sıfırı dışlamıyor; bu bant anlamlılık testi değildir.')
        if es['mean_excess_pct'] is None or es['mean_excess_pct']<=0:reasons.append('İlk dönemde endeks üstü ortalama net getiri yok.')
        if ls['stress_excess_pct'] is None or ls['stress_excess_pct']<=0:reasons.append('İki kat maliyette endeks üstü avantaj kalmıyor.')
        mid=len(late)//2
        if mid<5 or any(np.mean([r['excess_pct'] for r in part])<=0 for part in (late[:mid],late[mid:]) if part):
            reasons.append('Son dönemin iki yarısında yeterli ve tutarlı avantaj yok.')
        results.append({**spec,'current_setup':bool(masks[spec['id']].iloc[-1]),
            'evidence':'PAPER_RESEARCH_CANDIDATE' if not reasons else 'INSUFFICIENT_EVIDENCE',
            'reasons':reasons,'early':es,'late':ls,'skipped_unreliable_windows':skip1+skip2,
            'recent_trades':late[-10:][::-1]})
    return {'status':'OK','ticker':ticker,'protocol':PROTOCOL,'protocol_hash':PROTOCOL_HASH,
        'cost_bps':cost_bps,'bars':n,'as_of':str(stock.time.iloc[-1]),'split_date':str(stock.time.iloc[split]),
        'alignment':audit,'strategies':results,'live_approved':False,
        'limits':[
            'Geçmişe dönük araştırma: zaman sıralı %65/%35 bölme gerçek ileri test değildir; parametre optimizasyonu yapılmaz.',
            'Sonraki açılışta işlem varsayılır. Emir sırası, gerçek spread, fiyat limiti, tedbir ve gerçekleşme verisi yoktur; işlem garantisi yoktur.',
            'Temettü/sermaye işlemleri ve geçmiş evren doğrulanmamıştır. Fiyat getirisi toplam getiri değildir.',
            'Sabit maliyet varsayımıdır; iki kat maliyet stresidir, ölçülmüş gerçekleşme maliyeti değildir.',
            'Bantlar betimsel blok yeniden örneklemedir; kalibre edilmiş güven aralığı veya istatistiksel anlamlılık kanıtı değildir. Çoklu hisse ve parametre denemesi yanlış keşif riskini büyütür.',
            'Sonuçlar işlem başına koşullu ortalamadır; portföy CAGR/Sharpe veya faktörlerden arındırılmış alfa değildir. Nakit faizi, enflasyon ve vergiler dahil değildir.',
            'Olumlu sonuç yalnız kağıt üzerinde ileri araştırma adayıdır. Lisanslı veri, tarihsel işlem kuralları ve ileri kayıt olmadan canlı onay yoktur.'
        ]}


def edge_research(ticker,cost_bps=30):
    code=ticker.upper().removesuffix('.IS')
    if not re.fullmatch(r'[A-Z0-9]{2,12}',code):return {'status':'INVALID_SYMBOL'}
    now=time.time(); key=(code,float(cost_bps))
    with _LOCK:
        cached=_CACHE.get(key)
        if cached and now-cached[0]<1800:return cached[1]
    try:
        frames=[]; omitted=False; today=datetime.now(ZoneInfo('Europe/Istanbul'))
        for symbol in (code,'XU100'):
            rows=yahoo_rows(symbol,period='10y',interval='1d').get('candles') or []
            if not rows:return {'status':'NO_DATA','ticker':code,'missing_symbol':symbol}
            frame=daily_frame(rows)
            if len(frame) and frame.time.iloc[-1]>=today.strftime('%Y-%m-%d') and today.hour*60+today.minute<1095:
                frame=frame[frame.time<today.strftime('%Y-%m-%d')].reset_index(drop=True); omitted=True
            frames.append(frame)
        out=analyze(*frames,ticker=code,cost_bps=cost_bps)
        out.update({'source':'Yahoo daily OHLCV / XU100 price index','open_bar_omitted':omitted,
                    'retrieved_at':today.isoformat()})
        if out['status']=='OK':
            age=(today.date()-datetime.strptime(out['as_of'],'%Y-%m-%d').date()).days
            out['data_age_calendar_days']=age
            if age>7:
                out['status']='STALE_DATA';out['message']='Son ortak fiyat tarihi 7 takvim gününden eski; güncel değerlendirme engellendi.'
    except ValueError as exc:return {'status':'DATA_QUALITY_BLOCKED','message':str(exc)}
    except Exception:return {'status':'SOURCE_UNAVAILABLE','message':'Fiyat kaynağına erişilemedi; tekrar deneyin.'}
    with _LOCK:
        if len(_CACHE)>=100:_CACHE.clear()
        _CACHE[key]=(now,out)
    return out
