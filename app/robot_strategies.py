"""Prospective paper strategies built from public, reproducible principles. No proprietary vendor robot code."""
# V30 release anchor: strategy logic validated by CI and prospective-paper safety tests.
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .community_indicators import _validate, _rma

CATALOG=[
 {'id':'baseline','name':'Kapalı Bar Baseline','origin':'Terminal','rules':'Kısa/uzun skor + MACD + Supertrend + ADX. Kontrol grubu; optimize edilmiş ürün değildir.','parameters':{},'execution':{'stop_atr':2.0,'target_r':2.0,'trail_atr':None}},
 {'id':'alphatrend','name':'AlphaTrend · bağımsız uyarlama','origin':'Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/3wdQu7P3-AlphaTrend-Strategy/','rules':'MFI/TR tabanlı trend çizgisi; kapanmış bar. Trend sürerken sabit hedef yerine ATR trailing.','parameters':{'length':14,'atr_mult':1},'execution':{'stop_atr':2.5,'target_r':None,'trail_atr':2.5}},
 {'id':'ott','name':'OTT · bağımsız uyarlama','origin':'Anıl Özekşi / Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/HPbRZvsV/','rules':'VIDYA/OTT trend durumu; trend robotunda sabit 2R kaldırıldı.','parameters':{'length':2,'percent':1.4},'execution':{'stop_atr':2.5,'target_r':None,'trail_atr':2.5}},
 {'id':'tott','name':'TOTT · bağımsız uyarlama','origin':'Anıl Özekşi / Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/eENf7NpJ/','rules':'VIDYA40/TOTT trend durumu; stratejiye özel trailing çıkış.','parameters':{'length':40,'percent':1.0},'execution':{'stop_atr':2.7,'target_r':None,'trail_atr':2.7}},
 {'id':'momentum','name':'Göreli Momentum','origin':'Kamuya açık momentum prensipleri','rules':'EMA50 üstü + XU100 göre RS20/60 pozitif + ADX. EMA50/trend bozulunca çıkar.','parameters':{},'execution':{'stop_atr':2.5,'target_r':None,'trail_atr':2.5}},
 {'id':'tsmomentum','name':'Time-Series Momentum','origin':'AQR / akademik trend-following prensibi','url':'https://www.aqr.com/insights/research/journal-article/time-series-momentum','rules':'120/200 işlem günü momentum pozitif, EMA200 üstü, endeks rejimi olumlu. 3ATR trailing ile kazananı taşır.','parameters':{'lookbacks':[120,200]},'execution':{'stop_atr':3.0,'target_r':None,'trail_atr':3.0}},
 {'id':'donchian55','name':'Donchian 55 Breakout','origin':'Klasik trend breakout prensibi','rules':'Önceki 55 günlük zirve üstü kapanış + ADX + hacim + rejim.','parameters':{'entry':55,'exit':20},'execution':{'stop_atr':2.5,'target_r':None,'trail_atr':2.5}},
 {'id':'meanrev','name':'Rejim Filtreli Mean Reversion','origin':'Klasik mean-reversion prensibi','rules':'Yalnız ana trend yukarıyken RSI2 çok düşük + z-score<-2. Ortalama dönüşte çıkar.','parameters':{'rsi2':10,'zscore':-2},'execution':{'stop_atr':1.6,'target_r':1.5,'trail_atr':None}},
 {'id':'lowvolbreak','name':'Low-Volatility Breakout','origin':'Volatilite sıkışması + breakout prensibi','rules':'20G volatilite 60G rejimine göre düşükken breakout + hacim + güçlü kapanış.','parameters':{'compression_ratio':.75},'execution':{'stop_atr':2.0,'target_r':3.0,'trail_atr':2.0}},
 {'id':'defmom','name':'Defensive Momentum','origin':'Momentum + defensive risk filtreleri','rules':'RS60/120 pozitif, EMA200 üstü, volatilite görece düşük.','parameters':{},'execution':{'stop_atr':2.3,'target_r':None,'trail_atr':2.3}},
 {'id':'codex','name':'Codex Rejim & Teyit V2','origin':'BIST AI özgün','rules':'Breakout + RS + breadth + benchmark + hacim + close-location + gap/extension + Trap Defense CLEAR.','parameters':{'breadth_min':55},'execution':{'stop_atr':2.2,'target_r':3.0,'trail_atr':2.2}},
 {'id':'codexpro','name':'Codex Adaptive Ensemble','origin':'BIST AI özgün','rules':'Rejime göre trend, breakout, mean-reversion ve defensive momentum oylarını birleştirir. Trap Defense CLEAR zorunlu.','parameters':{'min_votes':3},'execution':{'stop_atr':2.4,'target_r':None,'trail_atr':2.4}},
 {'id':'qqe_ssl_wae','name':'QQE + SSL + WAE Fusion','origin':'Kamuya açık QQE/SSL/WAE prensiplerinin bağımsız uyarlaması','rules':'Çift QQE momentumu + SSL trend/baseline + Waddah Attar momentum/volatilite patlaması aynı yönde; benchmark ve Trap Defense teyidi zorunlu.','parameters':{'qqe_factors':[3.0,1.61],'ssl_baseline':60,'wae_fast':20,'wae_slow':40},'execution':{'stop_atr':2.2,'target_r':None,'trail_atr':2.2}},
 {'id':'kama_regime','name':'KAMA Efficiency Regime','origin':'Perry Kaufman adaptive trend prensibi','rules':'KAMA yönü + Efficiency Ratio + ADX + göreli güç + benchmark rejimi; yatay piyasada işlem azaltmayı hedefler.','parameters':{'er_length':10,'fast':2,'slow':30,'er_min':0.35},'execution':{'stop_atr':2.4,'target_r':None,'trail_atr':2.4}},
 {'id':'regimemeta','name':'Regime Meta Router','origin':'BIST AI özgün hiyerarşik meta-strateji','rules':'Önce piyasa rejimini sınıflandırır; trend, breakout, adaptive momentum veya mean-reversion alt mantıklarından yalnız uygun olanları oylar. Yüksek risk/volatilitede işlem açmaz.','parameters':{'breadth_bull':55,'breadth_riskoff':38,'high_vol_ratio':1.35,'min_votes':3},'execution':{'stop_atr':2.5,'target_r':None,'trail_atr':2.5}}
]
EXTERNAL=[
 {'name':'IBKR VWAP/TWAP/POV/Adaptive/Accumulate-Distribute','status':'RESEARCHED_PUBLIC_PRINCIPLES','url':'https://www.interactivebrokers.com/en/trading/ordertypes.php','reason':'Execution algoritmalarıdır; yön tahmini robotu değildir. Emir parçalama, katılım oranı ve market-impact prensipleri referans alındı; kod kopyalanmadı.'},
 {'name':'Nasdaq VWAP/TWAP/PVOL/Implementation Shortfall','status':'RESEARCHED_PUBLIC_PRINCIPLES','url':'https://www.nasdaq.com/products/european-markets/execution-algorithms','reason':'Kurumsal execution sınıfları incelendi; BIST broker API olmadan gerçek execution uygulanmaz.'},
 {'name':'J.P. Morgan Algorithmic Trading Guide','status':'RESEARCHED_PUBLIC_PRINCIPLES','url':'https://privatebank.jpmorgan.com/','reason':'TWAP/VWAP ve urgency yaklaşımı araştırma referansı; kapalı modeller kopyalanmadı.'},
 {'name':'TradingView Strategies / Alerts','status':'PLATFORM_REFERENCE','url':'https://www.tradingview.com/support/solutions/43000481368-strategy-alerts/','reason':'Broker emulator ve gerçek-zaman alarm davranışı referans alındı; ücretli Pine stratejileri kopyalanmadı.'},
 {'name':'AQR Time-Series Momentum','status':'RESEARCHED_PUBLIC_PRINCIPLES','url':'https://www.aqr.com/insights/research/journal-article/time-series-momentum','reason':'Kamuya açık akademik trend-following prensibi; BIST için performans garantisi değildir.'},
 {'name':'QNB Akıllı Robo / Matriks IQ / iDeal / ticari robotlar','status':'EXTERNAL_ONLY','url':'https://www.matriksdata.com/','reason':'Kapalı/lisanslı strateji mantığı kamuya açık değilse kopyalanmaz; yalnız doğrulanabilir genel prensipler uygulanır.'}
]
AUDIT=[
 'Eski sürümde tüm robotlara aynı 2ATR stop + 2R hedef uygulanıyordu; trend robotlarının kazananları erken kesiliyordu. Stratejiye özel exit profili getirildi.',
 'Trend durumunun devamı ile yeni giriş aynı görülüyordu; yeni robotlar rejim, momentum, breadth ve risk teyidi kullanıyor.',
 'Trap Defense CLEAR bütün yeni girişlerde zorunlu.',
 'Başarı yalnız win-rate ile değil net getiri, max drawdown, profit factor, ücret/kayma ve XU100 referansıyla izlenir.',
 'Hiçbir robot geçmiş performans nedeniyle canlı emre bağlanmaz; prospective paper doğrulama şarttır.'
]

def catalog():
    return {'version':'33.0','bots':CATALOG,'external':EXTERNAL,'audit':AUDIT,'adaptation':'Kamuya açık prensipler bağımsız Python kurallarıyla uygulanır; proprietary robot kodu kopyalanmaz.','validation':'PROSPECTIVE_FORWARD_PAPER_ONLY'}

def vidya(c,length):
    change=c.diff();up=change.clip(lower=0).rolling(9).sum();dn=(-change.clip(upper=0)).rolling(9).sum()
    ratio=((up-dn)/(up+dn).replace(0,np.nan)).abs().fillna(0).to_numpy();v=c.to_numpy(float);out=np.empty(len(c));out[0]=v[0]
    for i in range(1,len(c)):
        alpha=2/(length+1)*ratio[i];out[i]=alpha*v[i]+(1-alpha)*out[i-1]
    return pd.Series(out,index=c.index)

def ott(c,length,percent):
    ma=vidya(c,length);mv=ma.to_numpy();loss=mv*percent/100;lo=mv-loss;hi=mv+loss;direction=1;line=np.empty(len(c))
    for i in range(len(c)):
        if i:
            if mv[i]>lo[i-1]:lo[i]=max(lo[i],lo[i-1])
            if mv[i]<hi[i-1]:hi[i]=min(hi[i],hi[i-1])
            if direction<0 and mv[i]>hi[i-1]:direction=1
            elif direction>0 and mv[i]<lo[i-1]:direction=-1
        rail=lo[i] if direction>0 else hi[i];line[i]=rail*(1+percent/200) if mv[i]>rail else rail*(1-percent/200)
    return ma,pd.Series(line,index=c.index).shift(2)

def _rsi_series(c,n=6):
    d=c.diff();up=d.clip(lower=0);dn=(-d.clip(upper=0))
    au=_rma(up.fillna(0),n);ad=_rma(dn.fillna(0),n)
    rs=au/ad.replace(0,np.nan)
    return 100-100/(1+rs)

def _kama(c,er_length=10,fast=2,slow=30):
    change=(c-c.shift(er_length)).abs()
    noise=c.diff().abs().rolling(er_length).sum()
    er=(change/noise.replace(0,np.nan)).clip(0,1)
    fast_sc=2/(fast+1);slow_sc=2/(slow+1)
    sc=(er*(fast_sc-slow_sc)+slow_sc)**2
    out=np.full(len(c),np.nan);vals=c.to_numpy(float)
    start=next((i for i,v in enumerate(sc.to_numpy()) if np.isfinite(v)),None)
    if start is not None:
        out[start]=vals[start]
        for i in range(start+1,len(c)):
            k=float(sc.iloc[i]) if pd.notna(sc.iloc[i]) else slow_sc**2
            out[i]=out[i-1]+k*(vals[i]-out[i-1])
    return pd.Series(out,index=c.index),er

def _indicator_fusion(x,tr):
    c=x.Close.astype(float);h=x.High.astype(float);l=x.Low.astype(float)
    rsi=_rsi_series(c,6);sm=rsi.ewm(span=5,adjust=False).mean()
    atr_rsi=(sm-sm.shift()).abs();wild=11
    qqe_vol=atr_rsi.ewm(span=wild,adjust=False).mean().ewm(span=wild,adjust=False).mean()
    q1=(sm>50+qqe_vol*3.0)&(sm.diff()>0)
    q2=(sm>50+qqe_vol*1.61)&(sm.diff()>0)
    baseline=c.ewm(span=60,adjust=False).mean();atr14=_rma(tr,14)
    hi_ma=h.rolling(10).mean();lo_ma=l.rolling(10).mean();hlv=np.zeros(len(c))
    for i in range(1,len(c)):
        hlv[i]=1 if c.iloc[i]>hi_ma.iloc[i] else -1 if c.iloc[i]<lo_ma.iloc[i] else hlv[i-1]
    ssl_up=pd.Series(np.where(hlv<0,hi_ma,lo_ma),index=c.index)
    ssl_bull=(c>baseline+.2*atr14)&(c>ssl_up)
    macd=c.ewm(span=20,adjust=False).mean()-c.ewm(span=40,adjust=False).mean()
    wae=(macd-macd.shift())*150
    explosion=4*c.rolling(20).std(ddof=0)
    dead=_rma(tr,100)*3.7
    wae_bull=(wae>explosion)&(wae>dead)&(wae>wae.shift())&(explosion>=explosion.shift())
    kama,er=_kama(c)
    kama_bull=(c>kama)&(kama>kama.shift())
    return {'qqe_primary_bull':bool(q1.iloc[-1]) if pd.notna(q1.iloc[-1]) else False,
            'qqe_secondary_bull':bool(q2.iloc[-1]) if pd.notna(q2.iloc[-1]) else False,
            'ssl_bull':bool(ssl_bull.iloc[-1]) if pd.notna(ssl_bull.iloc[-1]) else False,
            'wae_bull':bool(wae_bull.iloc[-1]) if pd.notna(wae_bull.iloc[-1]) else False,
            'wae_strength':float(wae.iloc[-1]/max(float(explosion.iloc[-1]),1e-9)) if pd.notna(wae.iloc[-1]) and pd.notna(explosion.iloc[-1]) else 0.,
            'kama_bull':bool(kama_bull.iloc[-1]) if pd.notna(kama_bull.iloc[-1]) else False,
            'kama_er':float(er.iloc[-1]) if pd.notna(er.iloc[-1]) else 0.}

def features(df,benchmark=None):
    x=_validate(df)
    if len(x)<200:raise ValueError('En az 200 bar gerekir')
    c=x.Close.astype(float);h=x.High.astype(float);l=x.Low.astype(float);v=x.Volume.astype(float)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1);atr=tr.rolling(14).mean()
    typ=(h+l+c)/3;flow=typ*v;pos=flow.where(typ.diff()>0,0).rolling(14).sum();neg=flow.where(typ.diff()<0,0).rolling(14).sum();mfi=100*pos/(pos+neg).replace(0,np.nan)
    line=np.full(len(x),np.nan)
    for i in range(13,len(x)):
        if not pd.notna(mfi.iloc[i]):continue
        up=l.iloc[i]-atr.iloc[i];dn=h.iloc[i]+atr.iloc[i];prev=line[i-1] if i and np.isfinite(line[i-1]) else (up if mfi.iloc[i]>=50 else dn)
        line[i]=max(up,prev) if mfi.iloc[i]>=50 else min(dn,prev)
    alpha=pd.Series(line,index=x.index);ma,ot=ott(c,2,1.4);tm,to=ott(c,40,1.)
    e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean();e200=c.ewm(span=200,adjust=False).mean()
    d=c.diff();up2=d.clip(lower=0).ewm(alpha=.5,adjust=False).mean();dn2=(-d.clip(upper=0)).ewm(alpha=.5,adjust=False).mean();rsi2=100-100/(1+(up2/dn2.replace(0,np.nan)))
    z20=(c-c.rolling(20).mean())/c.rolling(20).std().replace(0,np.nan)
    ret=c.pct_change();vol20=ret.rolling(20).std();vol60=ret.rolling(60).std()
    a=float(_rma(tr,14).iloc[-1]);span=float(h.iloc[-1]-l.iloc[-1]);px=float(c.iloc[-1]);hi20=h.shift().rolling(20).max();hi55=h.shift().rolling(55).max();lo20=l.shift().rolling(20).min()
    out={'alpha_bull':bool(alpha.iloc[-1]>alpha.iloc[-3]),'alpha_bear':bool(alpha.iloc[-1]<alpha.iloc[-3]),'ott_bull':bool(ma.iloc[-1]>ot.iloc[-1]),'ott_bear':bool(ma.iloc[-1]<ot.iloc[-1]),'tott_bull':bool(tm.iloc[-1]>to.iloc[-1]*1.006),'tott_bear':bool(tm.iloc[-1]<to.iloc[-1]*.994),
         'ema20_bull':bool(c.iloc[-1]>e20.iloc[-1]),'ema50_bull':bool(c.iloc[-1]>e50.iloc[-1]),'ema200_bull':bool(c.iloc[-1]>e200.iloc[-1]),'breakout_prior20':bool(c.iloc[-1]>hi20.iloc[-1]),'breakout_prior55':bool(c.iloc[-1]>hi55.iloc[-1]),'below_low20':bool(c.iloc[-1]<lo20.iloc[-1]),
         'mom120':float((c.iloc[-1]/c.iloc[-121]-1)*100),'mom200':float((c.iloc[-1]/c.iloc[-200]-1)*100),'rsi2':float(rsi2.iloc[-1]) if pd.notna(rsi2.iloc[-1]) else 50.,'zscore20':float(z20.iloc[-1]) if pd.notna(z20.iloc[-1]) else 0.,
         'vol_ratio_20_60':float(vol20.iloc[-1]/vol60.iloc[-1]) if pd.notna(vol60.iloc[-1]) and vol60.iloc[-1]>0 else 1.,'volume_confirm':float(v.iloc[-1]/v.shift().rolling(20).mean().iloc[-1]) if v.shift().rolling(20).mean().iloc[-1]>0 else None,
         'close_location':float((px-l.iloc[-1])/span) if span else 0.,'upper_wick':float((h.iloc[-1]-max(px,x.Open.iloc[-1]))/span) if span else 1.,'gap_atr':float(abs(x.Open.iloc[-1]-c.iloc[-2])/a) if a>0 else None,'extension_atr':float((px-e20.iloc[-1])/a) if a>0 else None,'benchmark_bull':None}
    out.update(_indicator_fusion(x,tr))
    if benchmark is not None and len(benchmark)>=200 and benchmark.index[-1]==df.index[-1]:
        bc=benchmark.Close.astype(float);be=bc.ewm(span=50,adjust=False).mean();out['benchmark_bull']=bool(bc.iloc[-1]>be.iloc[-1] and be.iloc[-1]>be.iloc[-6])
    return out

def regime_state(r):
    f=r.get('robot_features',{})
    breadth=f.get('breadth_pct');vr=f.get('vol_ratio_20_60',1);risk=r.get('risk',100);adx=r.get('adx',0)
    if risk>=75 or f.get('benchmark_bull') is False and isinstance(breadth,(int,float)) and breadth<38:return 'RISK_OFF'
    if isinstance(vr,(int,float)) and vr>=1.35:return 'HIGH_VOL'
    if f.get('benchmark_bull') is True and isinstance(breadth,(int,float)) and breadth>=55 and adx>=22:return 'BULL_TREND'
    return 'RANGE'

def finite(r,*keys):return all(isinstance(r.get(k),(int,float)) and not isinstance(r.get(k),bool) and math.isfinite(r[k]) for k in keys)
def _profile(strategy):return dict(next(b for b in CATALOG if b['id']==strategy).get('execution') or {})

def entry(strategy,r):
    from .auto_paper import signal
    if strategy=='baseline':
        s=signal(r);return (*s,_profile(strategy)) if s else None
    if r.get('signal_guard',{}).get('status')!='CLEAR' or (r.get('trap_defense') is not None and r.get('trap_defense',{}).get('status')!='CLEAR') or r.get('bar_provisional') or r.get('history_bars',0)<200:return None
    if not finite(r,'atr','price','avg_value_turnover_20','risk') or r['atr']<=0 or r['price']<=0 or r['avg_value_turnover_20']<15_000_000 or r['risk']>=78:return None
    f=r.get('robot_features',{});s=None;rank=50.
    if strategy in {'alphatrend','ott','tott'}:
        prefix='alpha' if strategy=='alphatrend' else strategy;bull=f.get(prefix+'_bull');bear=f.get(prefix+'_bear')
        if bull and f.get('ema50_bull') and f.get('benchmark_bull') is not False:s='BUY'
        elif bear and r.get('supertrend')=='BEARISH' and f.get('benchmark_bull') is False:s='SHORT'
        rank=min(99.,50+math.log10(max(1,r['avg_value_turnover_20']/15_000_000))*10+max(0,r.get('adx',0)-20)/2)
    elif strategy=='momentum':
        if finite(r,'relative_strength_20','relative_strength_60','adx','rsi') and r['relative_strength_20']>0 and r['relative_strength_60']>0 and f.get('ema50_bull') and f.get('benchmark_bull') is True and r['adx']>=20 and 45<=r['rsi']<=70:s='BUY'
        rank=min(99.,50+max(0,r.get('relative_strength_20',0))+max(0,r.get('relative_strength_60',0))/2)
    elif strategy=='tsmomentum':
        if f.get('benchmark_bull') is True and f.get('ema200_bull') and f.get('mom120',0)>4 and f.get('mom200',0)>8 and r.get('relative_strength_60',0)>0:s='BUY'
        rank=min(99.,45+max(0,f.get('mom120',0))*.5+max(0,f.get('mom200',0))*.25)
    elif strategy=='donchian55':
        if f.get('benchmark_bull') is True and f.get('breakout_prior55') and r.get('adx',0)>=22 and (f.get('volume_confirm') or 0)>=1.15 and f.get('close_location',0)>=.60 and f.get('upper_wick',1)<=.30:s='BUY'
        rank=min(99.,55+max(0,r.get('adx',0)-20)+max(0,((f.get('volume_confirm') or 1)-1)*10))
    elif strategy=='meanrev':
        if f.get('benchmark_bull') is True and f.get('ema200_bull') and f.get('rsi2',50)<=10 and f.get('zscore20',0)<=-2 and r.get('risk',100)<65:s='BUY'
        rank=min(99.,50+max(0,-f.get('zscore20',0))*8+max(0,10-f.get('rsi2',50)))
    elif strategy=='lowvolbreak':
        if f.get('benchmark_bull') is True and f.get('vol_ratio_20_60',1)<=.75 and f.get('breakout_prior20') and (f.get('volume_confirm') or 0)>=1.3 and f.get('close_location',0)>=.65 and f.get('upper_wick',1)<=.25:s='BUY'
        rank=min(99.,55+max(0,(1-f.get('vol_ratio_20_60',1))*30)+max(0,((f.get('volume_confirm') or 1)-1)*10))
    elif strategy=='defmom':
        if f.get('benchmark_bull') is True and f.get('ema200_bull') and r.get('relative_strength_60',0)>3 and f.get('mom120',0)>5 and r.get('volatility',100)<40 and r.get('risk',100)<60:s='BUY'
        rank=min(99.,50+max(0,r.get('relative_strength_60',0))+max(0,40-r.get('volatility',40))*.4)
    elif strategy=='codex':
        if finite(r,'relative_strength_20','relative_strength_60','adx','rsi') and r['relative_strength_20']>0 and r['relative_strength_60']>0 and r['adx']>=22 and 45<=r['rsi']<=68 and f.get('benchmark_bull') is True and finite(f,'breadth_pct','volume_confirm','close_location','upper_wick','gap_atr','extension_atr') and f['breadth_pct']>=55 and f['volume_confirm']>=1.2 and f['close_location']>=.65 and f['upper_wick']<=.25 and f['gap_atr']<=1.5 and 0<=f['extension_atr']<=2 and f.get('breakout_prior20'):s='BUY'
        rank=min(99.,50+r.get('relative_strength_20',0)+r.get('relative_strength_60',0)/2)
    elif strategy=='qqe_ssl_wae':
        if f.get('benchmark_bull') is True and f.get('qqe_primary_bull') and f.get('qqe_secondary_bull') and f.get('ssl_bull') and f.get('wae_bull') and r.get('adx',0)>=18 and r.get('relative_strength_20',0)>0:s='BUY'
        rank=min(99.,55+max(0,f.get('wae_strength',0))*8+max(0,r.get('adx',0)-18)+max(0,r.get('relative_strength_20',0))*.5)
    elif strategy=='kama_regime':
        if f.get('benchmark_bull') is True and f.get('kama_bull') and f.get('kama_er',0)>=.35 and r.get('adx',0)>=20 and r.get('relative_strength_60',0)>0 and r.get('risk',100)<65:s='BUY'
        rank=min(99.,50+f.get('kama_er',0)*30+max(0,r.get('adx',0)-20)+max(0,r.get('relative_strength_60',0))*.4)
    elif strategy=='regimemeta':
        state=regime_state(r);votes=0;reasons=[]
        if state in {'RISK_OFF','HIGH_VOL'}:return None
        if state=='BULL_TREND':
            if f.get('ema200_bull') and f.get('mom120',0)>4 and r.get('relative_strength_60',0)>0:votes+=1;reasons.append('trend')
            if f.get('breakout_prior20') and (f.get('volume_confirm') or 0)>=1.15 and f.get('close_location',0)>=.6:votes+=1;reasons.append('breakout')
            if f.get('qqe_primary_bull') and f.get('ssl_bull') and f.get('wae_bull'):votes+=1;reasons.append('QQE/SSL/WAE')
            if f.get('kama_bull') and f.get('kama_er',0)>=.35:votes+=1;reasons.append('KAMA')
            if r.get('supertrend')=='BULLISH' and r.get('ichimoku')!='BEARISH':votes+=1;reasons.append('trend teyidi')
        else:
            if f.get('ema200_bull') and f.get('rsi2',50)<=12 and f.get('zscore20',0)<=-1.8:votes+=2;reasons.append('mean-reversion')
            if f.get('kama_er',1)<.25:votes+=1;reasons.append('düşük etkinlik/yatay')
            if r.get('risk',100)<55:votes+=1;reasons.append('düşük risk')
        if votes>=3 and f.get('benchmark_bull') is not False:s='BUY';rank=min(99.,55+votes*7+max(0,r.get('relative_strength_20',0))*.25)
        if s:r['_regime_meta']={'state':state,'votes':votes,'reasons':reasons}
    elif strategy=='codexpro':
        if f.get('benchmark_bull') is not True or not finite(f,'breadth_pct') or f['breadth_pct']<52:return None
        votes=0;reasons=[]
        if f.get('ema200_bull') and f.get('mom120',0)>4 and r.get('relative_strength_60',0)>0:votes+=1;reasons.append('trend')
        if f.get('breakout_prior55') and r.get('adx',0)>=22 and (f.get('volume_confirm') or 0)>=1.15:votes+=1;reasons.append('55G breakout')
        if f.get('ema200_bull') and f.get('rsi2',50)<=15 and f.get('zscore20',0)<=-1.5:votes+=1;reasons.append('mean-reversion')
        if r.get('relative_strength_60',0)>3 and r.get('risk',100)<60:votes+=1;reasons.append('defensive momentum')
        if r.get('supertrend')=='BULLISH' and r.get('ichimoku')!='BEARISH':votes+=1;reasons.append('trend teyidi')
        if votes>=3:s='BUY';rank=min(99.,55+votes*7+max(0,r.get('relative_strength_20',0))*.3)
        if s:r['_codexpro_reasons']=reasons
    if s:
        label=next(b['name'] for b in CATALOG if b['id']==strategy);detail=(' · oylar: '+', '.join(r.get('_codexpro_reasons',[]))) if strategy=='codexpro' else ''
        return s,label+' · kapanmış günlük bar; Trap Defense CLEAR.'+detail,rank,_profile(strategy)
    return None

def exit_reason(strategy,r,p):
    long=p['quantity']>0;f=r.get('robot_features',{})
    if r.get('trap_defense',{}).get('status')=='BLOCK':return 'Trap Defense BLOCK: yeni fiyat/hacim yapısı pozisyon tezini veto etti.'
    if strategy=='baseline':bad=r.get('supertrend')==('BEARISH' if long else 'BULLISH')
    elif strategy in {'alphatrend','ott','tott'}:
        prefix='alpha' if strategy=='alphatrend' else strategy;bad=f.get(prefix+('_bear' if long else '_bull'))
    elif strategy=='momentum':bad=f.get('ema50_bull') is False or f.get('benchmark_bull') is False
    elif strategy=='tsmomentum':bad=f.get('ema50_bull') is False or f.get('mom120',0)<0 or f.get('benchmark_bull') is False
    elif strategy=='donchian55':bad=f.get('ema20_bull') is False
    elif strategy=='meanrev':bad=f.get('zscore20',-9)>=0 or f.get('rsi2',0)>=70 or f.get('ema200_bull') is False
    elif strategy=='lowvolbreak':bad=f.get('ema20_bull') is False or r.get('macd_hist',0)<0
    elif strategy=='defmom':bad=f.get('ema50_bull') is False or r.get('relative_strength_60',0)<0 or f.get('benchmark_bull') is False
    elif strategy=='qqe_ssl_wae':bad=not f.get('ssl_bull') or not f.get('qqe_secondary_bull') or f.get('benchmark_bull') is False
    elif strategy=='kama_regime':bad=not f.get('kama_bull') or f.get('kama_er',0)<.20 or f.get('benchmark_bull') is False
    elif strategy=='regimemeta':bad=regime_state(r) in {'RISK_OFF','HIGH_VOL'} or f.get('benchmark_bull') is False
    elif strategy=='codex':bad=f.get('ema20_bull') is False or f.get('benchmark_bull') is False
    else:bad=f.get('ema20_bull') is False or f.get('benchmark_bull') is False or r.get('relative_strength_20',0)<-2
    return 'Kapanmış günlük barda stratejiye özgü çıkış koşulu oluştu.' if bad else None
