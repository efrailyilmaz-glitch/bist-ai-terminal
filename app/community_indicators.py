"""Independent, causal formula adaptations; not byte-for-byte Pine Script ports.
References and selection decisions: community_catalog.py. No copied third-party code.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

PARAMETERS={'wavetrend':{'channel':10,'average':21,'signal':4},'squeeze':{'length':20,'bb_mult':2.0,'kc_mult':1.5},'chandelier':{'length':22,'atr_mult':3.0,'extremes':'close'},'utbot':{'atr_length':10,'mult':1.0,'source':'regular close'},'chop':{'length':14}}


def confirmed_frame(df,interval='1d',now=None):
    """Use Istanbul session cutoff; exclude the open daily/weekly bar conservatively."""
    now=now or datetime.now(ZoneInfo('Europe/Istanbul'))
    x=df.copy()
    dates=pd.DatetimeIndex(pd.to_datetime(x['time'] if 'time' in x else x.index,errors='coerce'))
    if dates.isna().any():raise ValueError('Geçersiz bar tarihi.')
    keep=[]
    for stamp in dates:
        day=stamp.date()
        end=day+timedelta(days=4-day.weekday()) if interval=='1wk' else day
        keep.append(end<now.date() or (end==now.date() and now.weekday()<5 and (now.hour,now.minute)>=(18,20)))
    return x.loc[np.asarray(keep)].copy(),int(len(x)-sum(keep))


def _validate(df):
    names=['Open','High','Low','Close','Volume']
    x=df[names].apply(pd.to_numeric,errors='coerce').astype(float)
    a=x.to_numpy()
    if not np.isfinite(a).all() or (x[names[:4]]<=0).any().any() or (x.Volume<0).any() or (x.High<x[['Open','Low','Close']].max(axis=1)).any() or (x.Low>x[['Open','High','Close']].min(axis=1)).any():
        raise ValueError('Eksik veya tutarsız OHLCV barları.')
    dates=pd.DatetimeIndex(pd.to_datetime(df['time'] if 'time' in df else df.index,errors='coerce'))
    if dates.isna().any() or dates.has_duplicates or not dates.is_monotonic_increasing:raise ValueError('Bar tarihleri sıralı ve benzersiz olmalı.')
    return x


def _rma(s,n):
    # Wilder smoothing with an SMA seed, matching the published ATR definition.
    values=s.to_numpy(float);out=np.full(len(s),np.nan)
    if len(s)>=n:
        out[n-1]=np.mean(values[:n])
        for i in range(n,len(s)):out[i]=(out[i-1]*(n-1)+values[i])/n
    return pd.Series(out,index=s.index)


def _ema(s,n):return s.ewm(span=n,adjust=False,min_periods=1,ignore_na=True).mean().where(s.notna())


def calculate(df):
    x=_validate(df);c=x.Close;h=x.High;l=x.Low;v=x.Volume;tp=(h+l+c)/3
    esa=_ema(tp,10);dev=_ema((tp-esa).abs(),10)
    ci=(tp-esa)/(0.015*dev.replace(0,np.nan))
    wt=_ema(ci,21).where(np.arange(len(x))>=49);ws=wt.rolling(4).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    mid=c.rolling(20).mean();std=c.rolling(20).std(ddof=0);rng=tr.rolling(20).mean()
    sq=((mid-2*std>mid-1.5*rng)&(mid+2*std<mid+1.5*rng)).where(mid.notna())
    off=((mid-2*std<mid-1.5*rng)&(mid+2*std>mid+1.5*rng)).where(mid.notna())
    delta=c-((h.rolling(20).max()+l.rolling(20).min())/2+mid)/2
    axis=np.arange(20,dtype=float);centered=axis-axis.mean();den=float(centered@centered)
    mom=delta.rolling(20).apply(lambda a:float(a.mean()+((a@centered)/den)*(19-axis.mean())),raw=True)
    atr22=_rma(tr,22);long_base=c.rolling(22).max()-3*atr22;short_base=c.rolling(22).min()+3*atr22
    long=long_base.to_numpy(copy=True);short=short_base.to_numpy(copy=True);direction=np.full(len(x),np.nan);cv=c.to_numpy()
    for i in range(21,len(x)):
        if i==21:direction[i]=1;continue
        if cv[i-1]>long[i-1]:long[i]=max(long[i],long[i-1])
        if cv[i-1]<short[i-1]:short[i]=min(short[i],short[i-1])
        direction[i]=1 if cv[i]>short[i-1] else -1 if cv[i]<long[i-1] else direction[i-1]
    atr10=_rma(tr,10);ut=np.full(len(x),np.nan)
    for i in range(9,len(x)):
        loss=float(atr10.iloc[i])
        if i==9:ut[i]=cv[i]-loss;continue
        prev=ut[i-1]
        if cv[i]>prev and cv[i-1]>prev:ut[i]=max(prev,cv[i]-loss)
        elif cv[i]<prev and cv[i-1]<prev:ut[i]=min(prev,cv[i]+loss)
        else:ut[i]=cv[i]-loss if cv[i]>prev else cv[i]+loss
    long=pd.Series(long,index=x.index);short=pd.Series(short,index=x.index);direction=pd.Series(direction,index=x.index);ut=pd.Series(ut,index=x.index)
    chop=100*np.log10(tr.rolling(14).sum()/(h.rolling(14).max()-l.rolling(14).min()).replace(0,np.nan))/np.log10(14)
    out=pd.DataFrame({'wt':wt,'wt_signal':ws,'sq_momentum':mom,'sq_on':sq,'sq_off':off,'ce_long':long,'ce_short':short,'ce_direction':direction,'ut_stop':ut,'chop':chop},index=x.index)
    cross_up=lambda a,b:(a>b)&(a.shift()<=b.shift())
    cross_down=lambda a,b:(a<b)&(a.shift()>=b.shift())
    out['wt_cross_up']=cross_up(wt,ws);out['wt_cross_down']=cross_down(wt,ws)
    out['sq_release']=sq.shift().eq(True)&off.eq(True)
    out['ce_cross_up']=direction.eq(1)&direction.shift().eq(-1);out['ce_cross_down']=direction.eq(-1)&direction.shift().eq(1)
    out['ut_cross_up']=cross_up(c,ut);out['ut_cross_down']=cross_down(c,ut)
    out['volume_ratio']=v/v.shift().rolling(20).mean().replace(0,np.nan)
    return out.replace([np.inf,-np.inf],np.nan)


def snapshot(df,interval='1d',now=None):
    frame,omitted=confirmed_frame(df,interval,now)
    if len(frame)<60:return {'community_status':'INSUFFICIENT_DATA','community_as_of':None}
    f=calculate(frame);a=f.iloc[-1]
    day=str(pd.Timestamp(frame['time'].iloc[-1] if 'time' in frame else frame.index[-1]).date())
    from .signal_guard import assess
    guard=assess(frame)
    current=(now or datetime.now(ZoneInfo('Europe/Istanbul'))).date()
    if not 0<=(current-pd.Timestamp(day).date()).days<=7:guard['status']='BLOCK'
    num=lambda k:round(float(a[k]),5) if pd.notna(a[k]) else None
    boolean=lambda k:bool(a[k]) if pd.notna(a[k]) else None
    return {'community_status':'OK','community_as_of':day,'community_open_omitted':omitted,
            'community_guard':guard['status'],'community_guard_clear':guard['status']=='CLEAR','community_volume_ratio':num('volume_ratio'),
            'wt_value':num('wt'),'wt_signal':num('wt_signal'),'wt_cross_up':boolean('wt_cross_up'),'wt_cross_down':boolean('wt_cross_down'),
            'sq_momentum':num('sq_momentum'),'sq_on':boolean('sq_on'),'sq_release':boolean('sq_release'),
            'ce_bull':bool(a.ce_direction==1) if pd.notna(a.ce_direction) else None,'ce_cross_up':boolean('ce_cross_up'),'ce_cross_down':boolean('ce_cross_down'),
            'ut_cross_up':boolean('ut_cross_up'),'ut_cross_down':boolean('ut_cross_down'),'chop14':num('chop')}


def chart_series(df,interval='1d',now=None):
    frame,omitted=confirmed_frame(df,interval,now)
    if len(frame)<60:return {'series':{},'open_bars_omitted':omitted,'message':'En az 60 kapanmış bar gerekiyor; daha uzun dönem seçin.'}
    try:f=calculate(frame)
    except ValueError:return {'series':{},'open_bars_omitted':omitted,'message':'Topluluk hesapları için barlar geçersiz.'}
    times=frame['time'].tolist() if 'time' in frame else [str(pd.Timestamp(t).date()) for t in frame.index]
    keys=['wt','wt_signal','sq_momentum','ce_long','ce_short','ut_stop','chop']
    series={k:[{'time':t,'value':round(float(a),5)} for t,a in zip(times,f[k]) if pd.notna(a)] for k in keys}
    for k in ['ce_long','ce_short']:
        sign=1 if k=='ce_long' else -1
        # Whitespace entries break lines across direction changes.
        series[k]=[{'time':t,**({'value':round(float(a),5)} if d==sign and pd.notna(a) else {})} for t,a,d in zip(times,f[k],f.ce_direction)]
    return {'series':series,'open_bars_omitted':omitted,'parameters':PARAMETERS}


def evaluate(df,cost_bps=30):
    """Fixed 10-bar holding, next-open fills, disjoint trades, descriptive holdout."""
    x,_=confirmed_frame(df);f=calculate(x)
    if len(x)<200:return {'status':'INSUFFICIENT_DATA','bars':len(x)}
    result=[];split=int(len(x)*.65)
    masks={'WaveTrend':f.wt_cross_up & (f.wt<-53),'Squeeze Momentum':f.sq_release & (f.sq_momentum>0),'Chandelier Exit':f.ce_cross_up,'UT Bot':f.ut_cross_up}
    for name,mask in masks.items():
        periods=[]
        for start,stop in [(60,split),(split,len(x))]:
            trades=[];next_i=start
            for i in range(start,stop-11):
                if i<next_i or not bool(mask.iloc[i]):continue
                entry=float(x.Open.iloc[i+1]);end=float(x.Open.iloc[i+11]);net=(end/entry-1)*100-cost_bps/100
                trades.append(net);next_i=i+11
            periods.append({'trades':len(trades),'mean_net_pct':round(float(np.mean(trades)),3) if trades else None,'win_rate_pct':round(float(np.mean(np.array(trades)>0)*100),1) if trades else None,'worst_trade_pct':round(min(trades),3) if trades else None})
        result.append({'name':name,'early':periods[0],'late':periods[1],'evidence':'UNVALIDATED'})
    return {'status':'OK','bars':len(x),'cost_bps':cost_bps,'holding_bars':10,'split_date':str(x.time.iloc[split]),'results':result,
            'limits':'Sabit parametreli, yalnız uzun yönlü, 10 bar sonra açılış çıkışlı betimsel deney. XU100 karşılaştırması, stop dolumu, fiyat limiti, kurumsal işlem ve ileri test doğrulaması içermez. En yüksek geçmiş ortalama, en iyi gösterge kanıtı değildir.'}
