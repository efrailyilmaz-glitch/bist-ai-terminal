"""V112 current sector & factor neutralization 2.0.
Purifies V111 relative scores from broad momentum/volatility/trend and sector exposures.
Metadata gaps remain explicit; neutralization never creates live authority.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
import pandas as pd
from .cross_sectional_ranking_v2 import rank as rank_v2
from .market_data import daily_frames
from .fundamentals import get_fundamentals
from .factor_neutralization import neutralize

def analyze(limit=150):
    base=rank_v2(limit=max(30,min(int(limit),300)),min_coverage_pct=75)
    if base.get('status')!='OK':return {'status':base.get('status'),'version':'112.0','base':base}
    ranked=(base.get('rows') or [])[:max(30,min(int(limit),300))]
    codes=[x['ticker'] for x in ranked]
    frames=daily_frames(codes);sectors={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        fut={pool.submit(get_fundamentals,c):c for c in codes}
        for q in as_completed(fut):
            code=fut[q]
            try:sectors[code]=(q.result().get('sector') or '')
            except Exception:sectors[code]=''
    rows=[]
    for r in ranked:
        code=r['ticker'];df=frames.get(code)
        if df is None or df.empty or len(df)<60:continue
        c=pd.to_numeric(df['Close'],errors='coerce').dropna()
        if len(c)<60:continue
        ret20=float(c.iloc[-1]/c.iloc[-21]-1)
        vol20=float(c.pct_change().tail(20).std()*np.sqrt(252))
        ema50=float(c.ewm(span=50,adjust=False).mean().iloc[-1])
        gap=float(c.iloc[-1]/ema50-1) if ema50>0 else 0
        rows.append({'ticker':code,'raw_score':float(r['relative_rank_score']),'sector':sectors.get(code,''),
                     'ret_20':ret20,'vol_20':vol20,'ema50_gap':gap,'original_rank':r['rank']})
    if len(rows)<20:return {'status':'INSUFFICIENT_SAMPLE','version':'112.0','rows':rows}
    res=neutralize(pd.DataFrame(rows),score_col='raw_score',sector_col='sector',min_rows=20,min_sector_coverage=.65)
    df=res.get('frame')
    out=[]
    if df is not None:
        for x in df.to_dict('records'):
            out.append({'ticker':x['ticker'],'sector':x.get('sector'),'raw_score':round(float(x.get('raw_score',0)),3),
                        'neutral_score_z':round(float(x.get('score',0)),4),'original_rank':int(x.get('original_rank') or 0)})
    out.sort(key=lambda x:-x['neutral_score_z'])
    for i,x in enumerate(out,1):x['neutral_rank']=i;x['rank_change']=int(x['original_rank'])-i
    return {'status':res.get('status'),'version':'112.0','flags':res.get('flags') or [],
            'diagnostics':res.get('diagnostics') or {},'rows':out,
            'policy':'Neutralized rank removes estimated broad sector/momentum/volatility/trend exposure. It is a research ranking transform, not proof of pure alpha and never enables execution.'}
