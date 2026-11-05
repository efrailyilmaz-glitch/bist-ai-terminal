"""V104 autonomous paper portfolio 2.0 confirmation layer.
Adds unified-decision and dynamic-sizing confirmation to prospective paper entries.
Long entries use the V100/V102 stack; short entries remain on the existing guarded short rules
and are explicitly marked as legacy-short until a symmetric short research stack exists.
"""
from __future__ import annotations
from .dynamic_position_sizing import size as dynamic_size

def confirm_candidate(code,side,row,account):
    equity=float((account or {}).get('last_equity') or (account or {}).get('capital') or 1_000_000)
    positions=list(((account or {}).get('positions') or {}).keys())
    if str(side).upper()=='BUY':
        d=dynamic_size(code,portfolio_value=equity,portfolio_codes=positions)
        if d.get('status')!='OK':
            return {'allow':False,'reason':'V2_DYNAMIC_SIZING_UNAVAILABLE','risk_multiplier':0.0,'detail':d}
        if d.get('unified_decision') not in {'RESEARCH_PASS','WATCH'} or float(d.get('combined_multiplier') or 0)<=0:
            return {'allow':False,'reason':'V2_UNIFIED_DECISION_BLOCK','risk_multiplier':0.0,'detail':d}
        rm=max(0.0,min(1.0,float(d.get('combined_multiplier') or 0)))
        return {'allow':True,'reason':'V2_LONG_CONFIRMED','risk_multiplier':rm,'detail':d}
    # Existing short path is retained but cannot claim parity with the long unified research stack.
    return {'allow':True,'reason':'V2_LEGACY_SHORT_GUARDED','risk_multiplier':0.60,
            'detail':{'note':'Short candidate uses existing closed-bar, trap, execution and portfolio guards; symmetric unified short thesis engine is not yet available.'}}
