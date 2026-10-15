"""Explainable OHLCV warnings, not manipulation detection or a calibrated probability."""
import math
import numpy as np
import pandas as pd


def assess(df):
    flags=[]
    def flag(code, message, weight):
        flags.append({'code':code,'message':message,'weight':weight})
    needed=['Open','High','Low','Close','Volume']
    if any(c not in df for c in needed) or len(df)<30:
        return {'status':'BLOCK','score':100,'flags':[{'code':'MISSING_DATA','message':'En az 30 geçerli OHLCV barı gerekiyor.','weight':100}], 'version':1}
    x=df[needed].apply(pd.to_numeric,errors='coerce')
    a=x.to_numpy(dtype=float)
    if not np.isfinite(a).all() or (x[['Open','High','Low','Close']]<=0).any().any() or (x.Volume<0).any() or (x.High<x[['Open','Close','Low']].max(axis=1)).any() or (x.Low>x[['Open','Close','High']].min(axis=1)).any() or df.index.has_duplicates or not df.index.is_monotonic_increasing:
        return {'status':'BLOCK','score':100,'flags':[{'code':'INVALID_BARS','message':'Eksik, sırasız, yinelenen veya tutarsız fiyat/hacim barları.','weight':100}],'version':1}
    prior=x.iloc[-21:-1];last=x.iloc[-1];prev=x.iloc[-2]
    high=float(prior.High.max());low=float(prior.Low.min())
    span=float(last.High-last.Low);wick=float(last.High-max(last.Open,last.Close))/span if span else 0
    avgvol=float(prior.Volume.mean());vr=float(last.Volume/avgvol) if avgvol>0 else None
    turnover=float((prior.Close*prior.Volume).mean())
    tr=pd.concat([x.High-x.Low,(x.High-x.Close.shift()).abs(),(x.Low-x.Close.shift()).abs()],axis=1).max(axis=1)
    atr=float(tr.iloc[-15:-1].mean());gap=abs(float(last.Open/prev.Close-1))*100
    if (prior.Volume==0).sum()>=3 or last.Volume==0:
        flag('NO_TRADING','Sıfır hacim veya kesintili işlem geçmişi.',70)
    if turnover<10_000_000:flag('LOW_LIQUIDITY','20 günlük ortalama işlem tutarı 10 milyon TL altında; kayma riski.',35)
    if last.High>high and last.Close<=high:flag('FAILED_BREAKOUT','Fiyat önceki 20 barın tepesini aşıp altında kapandı.',45)
    if last.Low<low and last.Close>=low:flag('LOW_SWEEP','Önceki 20 barın dibi altına inip geri döndü; tek başına dönüş teyidi değil.',25)
    if wick>=.5 and vr is not None and vr>=2:flag('VOLUME_REJECTION','Yüksek hacimle uzun üst fitil; fiyat artışı reddedilmiş olabilir.',40)
    median=float(prior.Volume.median())
    if median>0 and last.Volume/median>=5:flag('VOLUME_SPIKE','Hacim önceki 20 barın medyanının en az 5 katı; haber/tek seferlik işlem kontrol edilmeli.',30)
    if gap>=5 or (atr>0 and abs(last.Open-prev.Close)>2*atr):flag('GAP','Açılış boşluğu büyük; görülen fiyat varsayımsal dolum fiyatı olmayabilir.',30)
    if atr>0 and last.Close-prev.Close>3*atr:flag('EXTENSION','Tek bardaki artış önceki ATR’nin 3 katını aşıyor; geç giriş riski.',30)
    confirmed=bool(last.Close>high and prev.Close>x.High.iloc[-22:-2].max() and vr is not None and vr>=1.2 and wick<.35)
    if last.Close>high and not confirmed:flag('UNCONFIRMED_BREAKOUT','Kırılım için ikinci kapanış ve hacim/fitil teyidi birlikte yok.',20)
    score=min(100,sum(f['weight'] for f in flags));status='BLOCK' if score>=65 else 'WAIT' if flags else 'CLEAR'
    return {'version':1,'status':status,'score':score,'flags':flags,'breakout_confirmed':confirmed,'turnover20':round(turnover),'volume_ratio_prior20':round(vr,2) if vr is not None else None,'limits':'OHLCV uyarısıdır; manipülasyon olasılığı değildir. Emir ekleme/iptal akışı olmadan spoofing doğrulanamaz. Eşikler ileri testle doğrulanmadı.'}


def daily_metadata(row, as_of, now=None):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now=now or datetime.now(ZoneInfo('Europe/Istanbul'))
    day=pd.Timestamp(as_of).date()
    g=row['signal_guard']
    row['as_of']=str(day)
    row['bar_provisional']=bool(day==now.date() and (now.hour,now.minute)<(18,20))
    age=(now.date()-day).days
    if age>7 or age<0:
        g['flags'].append({'code':'STALE_DATA','message':'Veri tarihi eski veya gelecekte; güncel sinyal üretilmez.','weight':100})
        g['status']='BLOCK';g['score']=100
    elif row['bar_provisional']:
        g['flags'].append({'code':'OPEN_BAR','message':'Bugünkü günlük bar kapanmadı; değerler değişebilir.','weight':20})
        if g['status']=='CLEAR':g['status']='WAIT'
        g['score']=min(100,g['score']+20)
    row['guard_clear']=g['status']=='CLEAR'
    if not row['guard_clear']:
        cap=47 if g['status']=='BLOCK' else 67
        for k in ['short_score','long_score','alpha_score']:row[k]=min(row[k],cap)
        for horizon in ['short','long']:
            score=row[horizon+'_score']
            row[horizon+'_signal']='GÜÇLÜ' if score>=80 else 'POZİTİF' if score>=68 else 'NÖTR' if score>=48 else 'ZAYIF'
    return row
