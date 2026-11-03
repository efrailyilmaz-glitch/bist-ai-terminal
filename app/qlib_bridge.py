"""V49 BIST -> Qlib-style feature bridge and optional adapter.
No hard dependency on Qlib/LightGBM. Feature generation is point-in-time and causal.
External model execution remains lab-only.
"""
from __future__ import annotations
import math
import pandas as pd
import numpy as np
from .market_data import yahoo_rows

FEATURES=[
 'ret_1','ret_5','ret_20','vol_20','range_1','volume_z20',
 'ema20_gap','ema50_gap','ema200_gap','rsi14','macd_hist','atr_pct'
]

def _rsi(c,n=14):
    d=c.diff();up=d.clip(lower=0);dn=(-d.clip(upper=0))
    au=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    ad=dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    rs=au/ad.replace(0,np.nan)
    return 100-100/(1+rs)

def feature_frame_from_rows(rows):
    if not rows:return pd.DataFrame()
    df=pd.DataFrame(rows).copy()
    ren={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'}
    df=df.rename(columns=ren)
    req=['Open','High','Low','Close','Volume']
    if any(x not in df.columns for x in req):return pd.DataFrame()
    for k in req:df[k]=pd.to_numeric(df[k],errors='coerce')
    c=df.Close;h=df.High;l=df.Low;v=df.Volume
    ret=c.pct_change()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean()
    e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean();e200=c.ewm(span=200,adjust=False).mean()
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    sig=macd.ewm(span=9,adjust=False).mean()
    vm=v.rolling(20,min_periods=20).mean();vs=v.rolling(20,min_periods=20).std().replace(0,np.nan)
    out=pd.DataFrame({
      'ret_1':ret,
      'ret_5':c.pct_change(5),
      'ret_20':c.pct_change(20),
      'vol_20':ret.rolling(20,min_periods=20).std()*math.sqrt(252),
      'range_1':(h-l)/c.replace(0,np.nan),
      'volume_z20':(v-vm)/vs,
      'ema20_gap':c/e20-1,
      'ema50_gap':c/e50-1,
      'ema200_gap':c/e200-1,
      'rsi14':_rsi(c,14)/100,
      'macd_hist':(macd-sig)/c.replace(0,np.nan),
      'atr_pct':atr/c.replace(0,np.nan)
    })
    out['label_5d']=c.shift(-5)/c-1
    if 'time' in df.columns:out.index=df['time'].astype(str)
    out.index.name='datetime'
    return out.replace([np.inf,-np.inf],np.nan)

def feature_frame(ticker,period='5y'):
    raw=yahoo_rows(ticker,period=period,interval='1d')
    f=feature_frame_from_rows(raw.get('candles') or [])
    return f

def causality_check_rows(rows):
    """Prefix-invariance test for the feature bridge."""
    full=feature_frame_from_rows(rows)
    if len(full)<260:return {'status':'INSUFFICIENT_DATA'}
    failures=[];checks=0
    for cut in sorted(set([len(rows)//2,len(rows)-126,len(rows)-63])):
        if cut<220 or cut>=len(rows):continue
        short=feature_frame_from_rows(rows[:cut])
        common=[x for x in FEATURES if x in full.columns and x in short.columns]
        n=min(len(short),cut)
        checks+=1
        a=full.iloc[:n][common].to_numpy(float);b=short.iloc[:n][common].to_numpy(float)
        if a.shape!=b.shape or not np.allclose(a,b,equal_nan=True,atol=1e-12):
            failures.append({'cut':cut})
    return {'status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures,
            'note':'Appending future bars must not alter previously emitted BIST->Qlib features.'}

def qlib_dataset_payload(ticker,period='5y',drop_unlabeled=True):
    f=feature_frame(ticker,period)
    if f.empty:return {'status':'NO_DATA','ticker':ticker.upper(),'rows':0}
    x=f.copy()
    if drop_unlabeled:x=x.dropna(subset=['label_5d'])
    usable=x.dropna(subset=FEATURES)
    return {'status':'OK' if len(usable) else 'INSUFFICIENT_DATA','ticker':ticker.upper(),'rows':len(usable),
            'feature_names':FEATURES,'label':'label_5d','frame':usable,
            'point_in_time':True,'execution_mode':'LAB_ONLY'}

def adapter_status():
    try:
        import qlib  # noqa
        qlib_ok=True
    except Exception:
        qlib_ok=False
    try:
        import lightgbm  # noqa
        lgb_ok=True
    except Exception:
        lgb_ok=False
    return {'qlib_installed':qlib_ok,'lightgbm_installed':lgb_ok,
            'status':'READY' if qlib_ok and lgb_ok else 'ADAPTER_UNAVAILABLE',
            'note':'The bridge remains usable without optional ML packages. No package is auto-installed at runtime.'}

def fit_predict_lab(ticker,period='5y',train_ratio=.7):
    """Optional LightGBM challenger. No live/paper orders; returns research predictions only."""
    ds=qlib_dataset_payload(ticker,period)
    if ds.get('status')!='OK':return ds
    st=adapter_status()
    if not st['lightgbm_installed']:
        return {'status':'ADAPTER_UNAVAILABLE','ticker':ticker.upper(),**st}
    import lightgbm as lgb
    df=ds['frame'];n=len(df);cut=max(200,min(n-40,int(n*train_ratio)))
    if n-cut<30:return {'status':'INSUFFICIENT_OOS','ticker':ticker.upper(),'rows':n}
    train=df.iloc[:cut];test=df.iloc[cut:]
    model=lgb.LGBMRegressor(n_estimators=80,max_depth=3,num_leaves=15,learning_rate=.03,
                            subsample=.8,colsample_bytree=.8,random_state=49,verbosity=-1)
    model.fit(train[FEATURES],train['label_5d'])
    pred=model.predict(test[FEATURES])
    corr=float(np.corrcoef(pred,test['label_5d'].to_numpy())[0,1]) if np.std(pred)>1e-12 and test['label_5d'].std()>1e-12 else 0.0
    hit=float(np.mean((pred>0)==(test['label_5d'].to_numpy()>0))*100)
    return {'status':'LAB_RESULT','ticker':ticker.upper(),'train_rows':len(train),'test_rows':len(test),
            'oos_information_coefficient':round(corr,4),'oos_directional_hit_pct':round(hit,1),
            'predictions':[{'datetime':str(idx),'prediction':round(float(p),6),'label_5d':round(float(y),6)}
                           for idx,p,y in zip(test.index[-50:],pred[-50:],test['label_5d'].to_numpy()[-50:])],
            'model_card':{'name':'BIST Qlib-bridge LightGBM challenger','source':'BIST AI / LightGBM optional adapter',
                          'version':'49.0','input_schema':FEATURES,'output_schema':['5d_return_prediction'],
                          'point_in_time':True,'execution_compatible':False},
            'note':'Research-only OOS diagnostic. This result does not pass V48 gates or authorize paper/live trading.'}
