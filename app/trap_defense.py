from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _f(x,d=0.0):
    try:
        v=float(x);return d if not math.isfinite(v) else v
    except Exception:return d

def assess_traps(df:pd.DataFrame):
    """Explainable multi-bar OHLCV deception-risk heuristics. Never claims intent or identifies an actor."""
    need=['Open','High','Low','Close','Volume']
    if df is None or len(df)<60 or any(c not in df for c in need):
        return {'status':'UNKNOWN','score':100,'flags':[{'code':'INSUFFICIENT_HISTORY','message':'Tuzak savunması için en az 60 geçerli OHLCV barı gerekiyor.','weight':100}],
                'limits':'OHLCV ile spoofing/katılımcı niyeti doğrulanamaz; Level-2/işlem tarafı verisi gerekir.'}
    x=df[need].apply(pd.to_numeric,errors='coerce').dropna()
    if len(x)<60:return {'status':'UNKNOWN','score':100,'flags':[{'code':'INVALID_HISTORY','message':'Geçerli bar sayısı yetersiz.','weight':100}],'limits':'OHLCV proxy.'}
    o,h,l,c,v=[x[k].astype(float) for k in need]
    ret=c.pct_change();rng=(h-l).replace(0,np.nan);body=(c-o).abs()
    upper=(h-np.maximum(o,c))/rng;lower=(np.minimum(o,c)-l)/rng
    tr=pd.concat([(h-l).abs(),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14).mean().replace(0,np.nan)
    vr=v/v.shift(1).rolling(20).median().replace(0,np.nan)
    high20=h.shift(1).rolling(20).max();low20=l.shift(1).rolling(20).min()
    flags=[]
    def flag(code,msg,w):flags.append({'code':code,'message':msg,'weight':w})

    # 1) repeated failed breakouts / bull traps
    failed=((h>high20)&(c<=high20)).tail(10).sum()
    if failed>=2:flag('REPEATED_FAILED_BREAKOUT',f'Son 10 barda {int(failed)} başarısız yukarı kırılım var.',28)
    # 2) high-volume churn: lots of volume, little net progress
    r5=(c/c.shift(5)-1).abs()*100
    churn=((vr>=2.0)&(r5<=3.0)).tail(8).sum()
    if churn>=2:flag('HIGH_VOLUME_CHURN','Yüksek hacme rağmen fiyat ilerlemesi zayıf; dağıtım/absorpsiyon riski.',25)
    # 3) upper wick cluster
    wick_cluster=((upper>=.42)&(vr>=1.25)).tail(8).sum()
    if wick_cluster>=2:flag('UPPER_WICK_CLUSTER','Yüksek hacimli üst fitiller kümeleniyor; yukarı hareket reddediliyor olabilir.',24)
    # 4) parabolic extension
    ema20=c.ewm(span=20,adjust=False).mean()
    ext=((c-ema20)/atr).replace([np.inf,-np.inf],np.nan)
    if _f(ext.iloc[-1])>=3.0 and _f(ret.tail(10).sum()*100)>=12:flag('PARABOLIC_EXTENSION','Fiyat EMA20/ATR bazında aşırı uzamış; geç giriş ve geri verme riski.',22)
    # 5) volume climax + weak close
    clv=((c-l)-(h-c))/rng
    if _f(vr.iloc[-1])>=3 and _f(clv.iloc[-1])<-.15:flag('VOLUME_CLIMAX_WEAK_CLOSE','Hacim zirvesi zayıf kapanışla birleşiyor.',30)
    # 6) volatility regime shock
    vol10=ret.rolling(10).std();vol60=ret.rolling(60).std()
    if _f(vol10.iloc[-1])>2.1*max(_f(vol60.iloc[-1]),1e-9):flag('VOLATILITY_REGIME_SHOCK','Kısa vadeli volatilite normal rejimin iki katından fazla.',18)
    # 7) whipsaw around EMA20
    sides=np.sign(c-ema20)
    crosses=(sides!=sides.shift()).tail(12).sum()
    if crosses>=5:flag('WHIPSAW','Fiyat EMA20 çevresinde sık yön değiştiriyor; trend sinyalleri güvenilmez olabilir.',16)
    # 8) breakdown/reclaim trap / stop sweep context
    sweeps=((l<low20)&(c>low20)).tail(10).sum()
    if sweeps>=2:flag('REPEATED_LOW_SWEEP','Son 10 barda birden fazla dip süpürme/geri dönüş var; stop avı benzeri görünüm.',12)
    # 9) liquidity instability
    adv=(c*v).shift(1).rolling(20).median()
    if _f(adv.iloc[-1])<10_000_000:flag('THIN_LIQUIDITY','Likidite düşük; fiyat/hacim sinyalleri daha kolay bozulabilir.',20)
    vcv=v.shift(1).rolling(20).std()/v.shift(1).rolling(20).mean().replace(0,np.nan)
    if _f(vcv.iloc[-1])>1.6:flag('UNSTABLE_VOLUME','Hacim dağılımı çok düzensiz; tekil işlemler göstergeleri bozabilir.',14)
    # 10) gap-up fade: a large opening gap that is sold into before the close
    prev_close=c.shift(1)
    gap_pct=(o/prev_close-1)*100
    atr_pct=atr/prev_close.replace(0,np.nan)*100
    if _f(gap_pct.iloc[-1])>=max(2.0,_f(atr_pct.iloc[-1])*.8) and _f(c.iloc[-1])<_f(o.iloc[-1]) and _f(clv.iloc[-1])<-.15:
        flag('GAP_UP_FADE','Yukarı boşluk açılışı gün içinde satılmış; haber/gap kovalamaca tuzağı riski.',26)

    # 11) marginal breakout: technically above resistance but without enough distance/volume to trust it
    breakout_margin=(c-high20)/atr.replace(0,np.nan)
    if _f(c.iloc[-1])>_f(high20.iloc[-1],1e99) and _f(breakout_margin.iloc[-1])<.25 and _f(vr.iloc[-1])<1.4:
        flag('MARGINAL_BREAKOUT','Direnç üstü kapanış marjı ve hacim zayıf; tek-bar sahte kırılım riski.',18)

    # 12) one-bar breakout rejection: prior breakout immediately falls back under its reference
    if len(x)>=3:
        prev_ref=_f(high20.iloc[-2],0)
        if prev_ref>0 and _f(c.iloc[-2])>prev_ref and _f(c.iloc[-1])<=prev_ref and _f(vr.iloc[-2])>=1.25:
            flag('ONE_BAR_BREAKOUT_REJECTION','Önceki barın kırılımı bir sonraki kapalı barda geri verilmiş.',32)

    # 13) volume spike with a small body: activity is high but directional conviction is weak
    body_ratio=(body/rng).replace([np.inf,-np.inf],np.nan)
    if _f(vr.iloc[-1])>=2.5 and _f(body_ratio.iloc[-1])<=.25 and abs(_f(clv.iloc[-1]))<.30:
        flag('VOLUME_SPIKE_SMALL_BODY','Çok yüksek hacim küçük gövdeyle birleşiyor; yön teyidi yerine churn/transfer olabilir.',22)

    # 14) pump-and-fade echo: strong 10d rise then quick reversal on volume
    run=(c/c.shift(10)-1)*100
    fade=(c/c.shift(3)-1)*100
    if _f(run.iloc[-4])>=18 and _f(fade.iloc[-1])<=-7 and _f(vr.iloc[-1])>=1.4:flag('PUMP_FADE_ECHO','Hızlı yükseliş sonrası hacimli sert geri verme paterni.',32)

    raw=sum(f['weight'] for f in flags)
    score=min(100,raw)
    critical=any(f['code'] in {'VOLUME_CLIMAX_WEAK_CLOSE','PUMP_FADE_ECHO'} for f in flags)
    status='BLOCK' if score>=60 or (critical and score>=45) else 'WAIT' if score>=28 else 'CLEAR'
    return {'version':2,'status':status,'score':score,'flags':flags,
            'metrics':{'failed_breakouts_10':int(failed),'upper_wick_cluster_8':int(wick_cluster),'churn_8':int(churn),
                       'ema20_atr_extension':round(_f(ext.iloc[-1]),2),'volume_ratio_median20':round(_f(vr.iloc[-1]),2),
                       'volatility_ratio_10_60':round(_f(vol10.iloc[-1])/max(_f(vol60.iloc[-1]),1e-9),2),
                       'gap_pct':round(_f(gap_pct.iloc[-1]),2),'breakout_margin_atr':round(_f(breakout_margin.iloc[-1]),2),
                       'body_to_range':round(_f(body_ratio.iloc[-1]),2)},
            'limits':'Bu motor yalnız fiyat/hacim davranışından risk işaretleri üretir. Manipülasyon, spoofing veya belirli bir kişi/kurumun niyeti OHLCV ile doğrulanamaz; Level-2, emir ekleme/iptal ve işlem tarafı verisi gerekir.'}

def combined_guard(signal_guard,trap):
    g=dict(signal_guard or {});g['flags']=list(g.get('flags') or [])
    if trap.get('status') in {'WAIT','BLOCK'}:
        g['flags'] += [{'code':'TRAP_'+f['code'],'message':'Tuzak Savunması: '+f['message'],'weight':f['weight']} for f in trap.get('flags',[])[:6]]
        g['score']=min(100,max(int(g.get('score') or 0),int(trap.get('score') or 0)))
        if trap.get('status')=='BLOCK':g['status']='BLOCK'
        elif g.get('status','CLEAR')=='CLEAR':g['status']='WAIT'
    return g
