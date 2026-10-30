"""Market-microstructure diagnostics.
No data vendor is called here. The functions accept licensed/authorized order-book
snapshots when supplied by an upstream adapter. Missing data never becomes a bullish signal.
"""
from __future__ import annotations
import math

def _num(x):
    return isinstance(x,(int,float)) and math.isfinite(float(x))

def book_imbalance(bids,asks,levels=5):
    b=[x for x in (bids or [])[:levels] if _num(x.get('qty')) and float(x['qty'])>=0]
    a=[x for x in (asks or [])[:levels] if _num(x.get('qty')) and float(x['qty'])>=0]
    if not b or not a:return None
    bv=sum(float(x['qty']) for x in b);av=sum(float(x['qty']) for x in a)
    den=bv+av
    return None if den<=0 else (bv-av)/den

def spread_bps(bids,asks):
    if not bids or not asks:return None
    bp=bids[0].get('price');ap=asks[0].get('price')
    if not (_num(bp) and _num(ap)) or bp<=0 or ap<=0 or ap<bp:return None
    mid=(float(bp)+float(ap))/2
    return (float(ap)-float(bp))/mid*10000 if mid>0 else None

def normalized_order_flow(events):
    """Signed add/cancel/trade pressure in [-1,1].
    Expected event: side=BID/ASK, action=ADD/CANCEL/TRADE, qty>0.
    TRADE uses aggressor_side when available.
    """
    buy=sell=0.0;valid=0
    for e in events or []:
        q=e.get('qty')
        if not _num(q) or q<=0:continue
        q=float(q);action=str(e.get('action','')).upper();side=str(e.get('side','')).upper()
        if action=='ADD':
            if side=='BID':buy+=q
            elif side=='ASK':sell+=q
            else:continue
        elif action=='CANCEL':
            # cancelling bids removes buy support; cancelling asks removes sell pressure
            if side=='BID':sell+=q
            elif side=='ASK':buy+=q
            else:continue
        elif action=='TRADE':
            ag=str(e.get('aggressor_side','')).upper()
            if ag in {'BUY','BID'}:buy+=q
            elif ag in {'SELL','ASK'}:sell+=q
            else:continue
        else:continue
        valid+=1
    den=buy+sell
    return {'ofi':None if den<=0 else (buy-sell)/den,'buy_pressure':buy,'sell_pressure':sell,'event_count':valid}

def cancellation_asymmetry(events):
    bid=ask=0.0
    for e in events or []:
        if str(e.get('action','')).upper()!='CANCEL' or not _num(e.get('qty')):continue
        if str(e.get('side','')).upper()=='BID':bid+=float(e['qty'])
        elif str(e.get('side','')).upper()=='ASK':ask+=float(e['qty'])
    den=bid+ask
    return None if den<=0 else (ask-bid)/den

def microstructure_guard(snapshot):
    """Returns a conservative gate. GOOD cannot increase risk; BAD may veto entry."""
    if not isinstance(snapshot,dict):
        return {'status':'UNKNOWN','score':0,'flags':['NO_MICROSTRUCTURE_DATA'],'risk_multiplier':1.0}
    bids=snapshot.get('bids') or [];asks=snapshot.get('asks') or [];events=snapshot.get('events') or []
    imb=book_imbalance(bids,asks,5);spr=spread_bps(bids,asks);flow=normalized_order_flow(events);ofi=flow['ofi'];cancel=cancellation_asymmetry(events)
    flags=[];score=50
    if spr is None:flags.append('SPREAD_UNKNOWN')
    elif spr>80:flags.append('WIDE_SPREAD');score-=25
    elif spr>40:flags.append('ELEVATED_SPREAD');score-=12
    if imb is not None:
        score+=max(-15,min(15,imb*20))
        if imb<-.55:flags.append('ASK_HEAVY_BOOK')
    if ofi is not None:
        score+=max(-20,min(20,ofi*25))
        if ofi<-.5:flags.append('NEGATIVE_ORDER_FLOW')
    else:flags.append('FLOW_UNKNOWN')
    if cancel is not None:
        # positive means more ask cancellations, negative means more bid cancellations
        score+=max(-8,min(8,cancel*10))
        if cancel<-.55:flags.append('BID_CANCELLATION_PRESSURE')
    if flow['event_count'] and flow['event_count']<20:flags.append('LOW_EVENT_SAMPLE')
    score=max(0,min(100,round(score)))
    hard=any(x in flags for x in ['WIDE_SPREAD','NEGATIVE_ORDER_FLOW','BID_CANCELLATION_PRESSURE'])
    status='BAD' if hard or score<35 else 'CAUTION' if score<50 or 'LOW_EVENT_SAMPLE' in flags else 'GOOD'
    rm=.5 if status=='BAD' else .75 if status=='CAUTION' else 1.0
    return {'status':status,'score':score,'flags':flags,'risk_multiplier':rm,
            'book_imbalance':None if imb is None else round(imb,4),'spread_bps':None if spr is None else round(spr,2),
            'ofi':None if ofi is None else round(ofi,4),'cancellation_asymmetry':None if cancel is None else round(cancel,4),
            'event_count':flow['event_count'],
            'limits':'Order-flow evidence is short-horizon and venue/feed dependent. GOOD never authorizes leverage or bypasses other risk gates.'}
