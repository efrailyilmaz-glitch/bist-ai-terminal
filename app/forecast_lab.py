"""Historical analog scenarios with purged, chronological validation.

No fitted feature or label uses observations after the simulated forecast date.
This is a close-to-close research experiment, not an execution simulator.
"""
from __future__ import annotations
import re, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from .market_data import yahoo_rows
from .scoring import indicator_frame

_CACHE = {}
_LOCK = threading.Lock()
EMBARGO = 5
MAX_NEIGHBORS = 24
MIN_NEIGHBORS = 12


def features(df):
    ind = indicator_frame(df)
    c = df.Close
    vol = df.Volume / df.Volume.rolling(20).mean().replace(0, np.nan)
    return pd.DataFrame({
        'rsi': ind.RSI14 / 100,
        'stoch': ind.STOCH_RSI_K / 100,
        'macd_atr': ind.MACD_HIST / ind.ATR14.replace(0, np.nan),
        'adx': ind.ADX14 / 100,
        'return5': c.pct_change(5), 'return20': c.pct_change(20),
        'ema50_distance': c / ind.EMA50 - 1,
        'volatility': c.pct_change().rolling(20).std(),
        'volume': np.log1p(vol.clip(lower=0)),
    }).replace([np.inf, -np.inf], np.nan)


def neighbors(x, query, horizon):
    # Outcomes must finish strictly before query minus an embargo.
    pool = np.flatnonzero(np.isfinite(x).all(axis=1) & (np.arange(len(x)) + horizon < query - EMBARGO))
    if not len(pool) or not np.isfinite(x[query]).all(): return [], None
    past = x[pool]
    center = np.median(past, axis=0)
    scale = np.maximum(np.quantile(past, .75, axis=0) - np.quantile(past, .25, axis=0), .01)
    distance = np.sqrt(np.mean(((past - x[query]) / scale) ** 2, axis=1))
    chosen = []
    for j in np.argsort(distance, kind='stable'):
        i = int(pool[j])
        if all(abs(i - other[0]) > horizon for other in chosen):
            chosen.append((i, float(distance[j])))
        if len(chosen) == MAX_NEIGHBORS: break
    return chosen, pool


def wilson(p, n):
    z = 1.96; den = 1 + z*z/n
    mid = (p + z*z/(2*n)) / den
    radius = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return [round(100*(mid-radius), 1), round(100*(mid+radius), 1)]


def analyze_frame(df, ticker='TEST', horizon=20, cost_bps=30):
    df = df.copy().reset_index(drop=True)
    if len(df) < 600: return {'ticker':ticker,'status':'INSUFFICIENT_DATA','bars':len(df)}
    feature_frame = features(df)
    x = feature_frame.to_numpy(float); close = df.Close.to_numpy(float)
    cost = cost_bps / 100
    returns = (df.Close.shift(-horizon) / df.Close - 1).to_numpy(float)*100 - cost
    query = len(df)-1
    matches, pool = neighbors(x, query, horizon)
    if len(matches) < MIN_NEIGHBORS:
        return {'ticker':ticker,'status':'INSUFFICIENT_ANALOGS','bars':len(df),'analog_count':len(matches)}
    vals = np.array([returns[i] for i,_ in matches]); prob = float(np.mean(vals>0))
    # Last two years of non-overlapping forecasts; each trained solely on its past.
    validation = []
    for q in range(max(550, len(df)-504), len(df)-horizon, horizon+1):
        analogs, eligible = neighbors(x, q, horizon)
        if len(analogs) < MIN_NEIGHBORS or not np.isfinite(returns[q]): continue
        labels = np.array([returns[i] for i,_ in analogs])
        # Baseline uses a separate chronological, non-overlapping sample grid.
        grid = eligible[::horizon+1]
        p0 = float(np.mean(returns[grid]>0)); p = float(np.mean(labels>0))
        lo, hi = np.quantile(labels,[.1,.9]); outcome = float(returns[q]); y = float(outcome>0)
        validation.append({'time':str(df.iloc[q].time),'query_index':q,'latest_label_end':max(i+horizon for i,_ in analogs),
                           'probability':p,'baseline':p0,'outcome_pct':outcome,'brier':(p-y)**2,
                           'baseline_brier':(p0-y)**2,'covered':bool(lo<=outcome<=hi),
                           'distance':float(np.median([d for _,d in analogs]))})
    n = len(validation)
    bs = float(np.mean([v['brier'] for v in validation])) if n else None
    b0 = float(np.mean([v['baseline_brier'] for v in validation])) if n else None
    skill = 1-bs/b0 if b0 and bs is not None else None
    dist = float(np.median([d for _,d in matches]))
    distance_limit = float(np.quantile([v['distance'] for v in validation],.95)) if n>=12 else None
    reasons = []
    if n<20: reasons.append('Zaman sıralı test sayısı 20 altında; kanıt sınırlı.')
    if skill is None or skill<=0: reasons.append('Model, geçmiş pozitif oranı baz çizgisini geçemedi.')
    if distance_limit is not None and dist>distance_limit: reasons.append('Bugünkü yapı geçmiş testlere göre alışılmadık; benzerlik zayıf.')
    spread = wilson(prob,len(vals))
    if spread[1]-spread[0]>45: reasons.append('Olasılık belirsizliği geniş.')
    coverage = float(np.mean([v['covered'] for v in validation])*100) if n else None
    if coverage is not None and coverage<65: reasons.append('Senaryo bandı geçmiş testlerde yeterli kapsama göstermedi.')
    analog_rows = []
    for i,d in matches:
        future = df.iloc[i+1:i+horizon+1]
        analog_rows.append({'time':str(df.iloc[i].time),'outcome_time':str(df.iloc[i+horizon].time),
                           'distance':round(d,3),'net_return_pct':round(float(returns[i]),2),
                           'worst_excursion_pct':round(float(future.Low.min()/close[i]-1)*100,2),
                           'best_excursion_pct':round(float(future.High.max()/close[i]-1)*100,2)})
    quantiles = np.quantile(vals,[.1,.5,.9])
    return {'ticker':ticker,'status':'OK','evidence':'ABSTAIN' if reasons else 'PROMISING_RESEARCH',
            'reasons':reasons,'as_of':str(df.iloc[-1].time),'bars':len(df),'horizon':horizon,'cost_bps':cost_bps,
            'analog_count':len(vals),'positive_rate_pct':round(prob*100,1),'positive_rate_ci95':spread,
            'return_p10_pct':round(float(quantiles[0]),2),'return_median_pct':round(float(quantiles[1]),2),
            'return_p90_pct':round(float(quantiles[2]),2),'reference_price':round(float(close[-1]),2),
            'scenario_prices':[round(float(close[-1]*(1+(v+cost)/100)),2) for v in quantiles],
            'baseline_positive_pct':round(float(np.mean(returns[pool[::horizon+1]]>0))*100,1),
            'validation':{'n':n,'brier':round(bs,4) if bs is not None else None,
                          'baseline_brier':round(b0,4) if b0 is not None else None,
                          'brier_skill_pct':round(skill*100,1) if skill is not None else None,
                          'interval_coverage_pct':round(coverage,1) if coverage is not None else None,
                          'recent':validation[-8:]},'analogs':analog_rows,
            'method':{'features':list(feature_frame.columns),'embargo_bars':EMBARGO,'overlap_removed':True,
                      'holdout':'rolling chronological; labels finish before each query with a 5-bar embargo',
                      'limits':['Benzer dönemler bağımsız deneyler değildir; güven aralığı yaklaşık bir ölçüdür.',
                                'Senaryolar geçmiş benzerliklerdir; kalibre edilmiş gelecek olasılığı veya fiyat hedefi değildir.',
                                '10 yıllık mevcut hisse geçmişi; hayatta kalan hisse ve veri revizyonu yanlılığı sürebilir.',
                                'Maliyet sabit varsayımdır; emir defteri, likidite, fiyat boşluğu ve gerçekleşme modellenmez.',
                                'Pozitif test becerisi gelecekte üstünlük kanıtı değildir.']}}


def forecast(ticker, horizon=20, cost_bps=30):
    code = ticker.upper().removesuffix('.IS')
    if not re.fullmatch(r'[A-Z0-9]{2,12}',code): return {'status':'INVALID_SYMBOL'}
    key = (code,horizon,cost_bps); now = time.time()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and now-cached[0]<1800: return cached[1]
    rows = yahoo_rows(code,period='10y',interval='1d').get('candles') or []
    if not rows: return {'ticker':code,'status':'NO_DATA'}
    df = pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    df['time'] = pd.to_datetime(df['time'],errors='coerce')
    df = df.dropna(subset=['time']).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    now_tr = datetime.now(ZoneInfo('Europe/Istanbul'))
    omitted_open_bar = False
    if len(df) and df.iloc[-1].time.date()==now_tr.date() and (now_tr.hour*60+now_tr.minute)<18*60+15:
        df = df.iloc[:-1]; omitted_open_bar = True
    for c in ['Open','High','Low','Close','Volume']: df[c] = pd.to_numeric(df[c],errors='coerce')
    df = df.dropna(subset=['Open','High','Low','Close','Volume'])
    df = df[(df.Close>0)&(df.Volume>=0)&(df.Low>0)&(df.High>=df.Low)]
    df['time'] = df.time.dt.strftime('%Y-%m-%d')
    result = analyze_frame(df,code,horizon,cost_bps)
    result['open_bar_omitted'] = omitted_open_bar
    with _LOCK:
        if len(_CACHE)>100: _CACHE.clear()
        _CACHE[key] = (now,result)
    return result
