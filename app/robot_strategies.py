"""Causal independent formula adaptations. No vendor code or return claims imported."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .community_indicators import _validate, _rma

CATALOG=[
 {'id':'baseline','name':'Mevcut Kapalı Bar Robotu','origin':'Terminal V27','rules':'Kısa ≥75, uzun ≥68, MACD+, Supertrend+, ADX≥22, RSI45–72. Ters trendde çıkış.','parameters':{}},
 {'id':'alphatrend','name':'AlphaTrend · bağımsız uyarlama','origin':'Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/3wdQu7P3-AlphaTrend-Strategy/','rules':'MFI14 ve TR SMA14 ile iz süren çizgi; iki bar gecikmeli çizginin üstünde uzun yön. Tersinde çıkış.','parameters':{'length':14,'atr_mult':1}},
 {'id':'ott','name':'OTT · bağımsız uyarlama','origin':'Anıl Özekşi / Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/HPbRZvsV/','rules':'VIDYA2 (CMO9) destek çizgisi, %1,4 iz süren OTT çizgisinin iki bar gecikmeli değerinin üzerinde. Tersinde çıkış.','parameters':{'length':2,'percent':1.4,'cmo':9,'lag':2}},
 {'id':'tott','name':'TOTT · bağımsız uyarlama','origin':'Anıl Özekşi / Kıvanç Özbilgiç','url':'https://www.tradingview.com/script/eENf7NpJ/','rules':'VIDYA40 / %1 OTT; ±%0,6 bant ve iki bar gecikme. Üst bantta giriş, alt bantta çıkış.','parameters':{'length':40,'percent':1.,'coefficient':.006,'cmo':9,'lag':2}},
 {'id':'momentum','name':'Göreli Momentum Sepeti','origin':'Açık kurallı karşılaştırma stratejisi; ticari robot kopyası değil','rules':'Fiyat EMA50 üstü, endekse göre RS20/60 pozitif, ADX≥20, RSI45–70; en güçlü göreli momentum öncelikli. EMA50 altı çıkış.','parameters':{}},
 {'id':'codex','name':'Codex Rejim & Teyit','origin':'Bu terminal için özgün, sabit kurallı strateji','rules':'Endeks EMA50 üstü, EMA50 yükseliyor; kapsam≥%80 ve hisselerin ≥%55’i EMA50 üstünde. RS20/60+, ADX≥22, RSI45–68, hacim≥1,2x; önceki 20 bar zirvesi üstünde kapanış, kapanış konumu≥%65, üst fitil≤%25, açılış boşluğu≤1,5ATR, EMA20 uzaklığı≤2ATR. Endeks/EMA20 bozulunca çıkış.','parameters':{'breadth_min':55,'volume_min':1.2,'breakout_bars':20,'gap_atr_max':1.5,'extension_atr_max':2.}}
]
EXTERNAL=[
 {'name':'QNB Akıllı Robo BIST','status':'EXTERNAL_ONLY','url':'https://www.qnbinvest.com.tr/akilli-robo-bist-performans','reason':'Kapalı model; veri/API ve kullanım izni bağlı değil. Performansı laboratuvara aktarılmaz.'},
 {'name':'Roboritma','status':'EXTERNAL_ONLY','url':'https://roboritma.com/','reason':'Kapalı robotlar; bağlantı yok. Momentum/grid kopyası veya resmî entegrasyon iddiası yok.'},
 {'name':'YatırımUzmanı','status':'EXTERNAL_ONLY','url':'https://www.borsateknolojileri.com/YatirimUzmani-Borsa-Robotu.html','reason':'Ücretli kapalı stratejiler; lisans/API bağlı değil.'},
 {'name':'Matriks IQ / iDeal','status':'PLATFORM_ONLY','url':'https://www.matriksdata.com/','reason':'Strateji geliştirme/emir platformları; tek bir robot getirisi yok. Bu laboratuvarla emir bağlantısı kurulmadı.'},
 {'name':'Finemar / Parada Pusula','status':'RESEARCH_ONLY','url':'https://finemar.com/model/','reason':'Tam strateji, bağımsız işlem kayıtları ve bağlantı yok; yayımlanan getiriler deney sonucu sayılmaz.'},
 {'name':'Holly / Tickeron / Danelfin / FinRL','status':'RESEARCH_ONLY','url':'https://github.com/AI4Finance-Foundation/FinRL','reason':'BIST için karşılaştırmalı canlı doğrulama yok; indirilen model/kod veya hesap bağlantısı yok.'}
]

def catalog():
    return {'version':'28.0','bots':CATALOG,'external':EXTERNAL,'adaptation':'Topluluk formülleri Python ile bağımsız uyarlanmıştır. Pine ile bar bar eşitlik doğrulanmadı; başlangıç/ATR/ortalama uygulamaları farklı olabilir. Ticari robotlar kopyalanmadı.','validation':'UNVALIDATED_FORWARD_PAPER'}

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
        rail=lo[i] if direction>0 else hi[i]
        line[i]=rail*(1+percent/200) if mv[i]>rail else rail*(1-percent/200)
    return ma,pd.Series(line,index=c.index).shift(2)

def features(df,benchmark=None):
    x=_validate(df)
    if len(x)<200:raise ValueError('En az 200 bar gerekir')
    c=x.Close;h=x.High;l=x.Low;v=x.Volume
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14).mean();typ=(h+l+c)/3;flow=typ*v
    pos=flow.where(typ.diff()>0,0).rolling(14).sum();neg=flow.where(typ.diff()<0,0).rolling(14).sum()
    mfi=100*pos/(pos+neg).replace(0,np.nan)
    line=np.full(len(x),np.nan)
    for i in range(13,len(x)):
        if not pd.notna(mfi.iloc[i]):continue
        up=l.iloc[i]-atr.iloc[i];dn=h.iloc[i]+atr.iloc[i];prev=line[i-1] if i and np.isfinite(line[i-1]) else (up if mfi.iloc[i]>=50 else dn)
        line[i]=max(up,prev) if mfi.iloc[i]>=50 else min(dn,prev)
    alpha=pd.Series(line,index=x.index);ma,ot=ott(c,2,1.4);tm,to=ott(c,40,1.)
    e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean();a=float(_rma(tr,14).iloc[-1]);span=float(h.iloc[-1]-l.iloc[-1]);px=float(c.iloc[-1])
    out={'alpha_bull':bool(alpha.iloc[-1]>alpha.iloc[-3]),'alpha_bear':bool(alpha.iloc[-1]<alpha.iloc[-3]),'ott_bull':bool(ma.iloc[-1]>ot.iloc[-1]),'ott_bear':bool(ma.iloc[-1]<ot.iloc[-1]),'tott_bull':bool(tm.iloc[-1]>to.iloc[-1]*1.006),'tott_bear':bool(tm.iloc[-1]<to.iloc[-1]*.994),
         'ema50_bull':bool(c.iloc[-1]>e50.iloc[-1]),'ema20_bull':bool(c.iloc[-1]>e20.iloc[-1]),'breakout_prior20':bool(c.iloc[-1]>h.shift().rolling(20).max().iloc[-1]),
         'volume_confirm':float(v.iloc[-1]/v.shift().rolling(20).mean().iloc[-1]) if v.shift().rolling(20).mean().iloc[-1]>0 else None,
         'close_location':float((px-l.iloc[-1])/span) if span else 0.,'upper_wick':float((h.iloc[-1]-max(px,x.Open.iloc[-1]))/span) if span else 1.,
         'gap_atr':float(abs(x.Open.iloc[-1]-c.iloc[-2])/a) if a>0 else None,'extension_atr':float((px-e20.iloc[-1])/a) if a>0 else None,'benchmark_bull':None}
    if benchmark is not None and len(benchmark)>=200 and benchmark.index[-1]==df.index[-1]:
        bc=benchmark.Close.astype(float);be=bc.ewm(span=50,adjust=False).mean();out['benchmark_bull']=bool(bc.iloc[-1]>be.iloc[-1] and be.iloc[-1]>be.iloc[-6])
    return out

def finite(r,*keys):return all(isinstance(r.get(k),(int,float)) and not isinstance(r.get(k),bool) and math.isfinite(r[k]) for k in keys)

def entry(strategy,r):
    from .auto_paper import signal
    if strategy=='baseline':return signal(r)
    if r.get('signal_guard',{}).get('status')!='CLEAR' or r.get('bar_provisional') or r.get('history_bars',0)<200:return None
    if not finite(r,'atr','price','avg_value_turnover_20','risk') or r['atr']<=0 or r['price']<=0 or r['avg_value_turnover_20']<10_000_000 or r['risk']>=80:return None
    f=r.get('robot_features',{});s=None;rank=50.
    if strategy in {'alphatrend','ott','tott'}:
        prefix='alpha' if strategy=='alphatrend' else strategy
        if f.get(prefix+'_bull'):s='BUY'
        elif f.get(prefix+'_bear'):s='SHORT'
        # Rank within the same trend by liquid turnover, without ticker preference.
        rank=min(99.,50+math.log10(max(1,r['avg_value_turnover_20']/10_000_000))*10)
    elif strategy in {'momentum','codex'}:
        if not finite(r,'relative_strength_20','relative_strength_60','adx','rsi'):return None
        good=r['relative_strength_20']>0 and r['relative_strength_60']>0
        if strategy=='momentum':
            if good and f.get('ema50_bull') and r['adx']>=20 and 45<=r['rsi']<=70:s='BUY'
        elif good and r['adx']>=22 and 45<=r['rsi']<=68 and f.get('benchmark_bull') is True and finite(f,'breadth_pct','volume_confirm','close_location','upper_wick','gap_atr','extension_atr') and f['breadth_pct']>=55 and f['volume_confirm']>=1.2 and f['close_location']>=.65 and f['upper_wick']<=.25 and f['gap_atr']<=1.5 and 0<=f['extension_atr']<=2 and f.get('breakout_prior20'):s='BUY'
        rank=min(99.,max(0.,50+r['relative_strength_20']+r['relative_strength_60']/2))
    if s:
        label=next(b['name'] for b in CATALOG if b['id']==strategy)
        detail=(' RS20='+str(r['relative_strength_20'])+', RS60='+str(r['relative_strength_60'])+', genişlik %'+str(round(f['breadth_pct'],1))+', hacim '+str(round(f['volume_confirm'],2))+'x, boşluk '+str(round(f['gap_atr'],2))+'ATR.') if strategy=='codex' else ''
        return s,label+' · kapanmış günlük bar, sabit v1 kuralları sağlandı.'+detail,rank
    return None

def exit_reason(strategy,r,p):
    long=p['quantity']>0;f=r.get('robot_features',{})
    if strategy=='baseline':bad=r.get('supertrend')==('BEARISH' if long else 'BULLISH')
    elif strategy in {'alphatrend','ott','tott'}:
        prefix='alpha' if strategy=='alphatrend' else strategy;bad=f.get(prefix+('_bear' if long else '_bull'))
    elif strategy=='momentum':bad=f.get('ema50_bull') is False
    else:bad=f.get('ema20_bull') is False or f.get('benchmark_bull') is False
    return 'Kapanmış günlük barda stratejinin çıkış koşulu oluştu.' if bad else None
