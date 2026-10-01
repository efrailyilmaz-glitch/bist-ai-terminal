from __future__ import annotations
import json, os, platform, threading, time, uuid
from pathlib import Path
from .market_data import scan_codes

_LOCK=threading.Lock()
_STATE={'kill_switch':False,'paper_orders':[],'paper_positions':{},'daily_realized':{},'risk':{'max_order_value':250000.0,'max_position_pct':12.0,'max_daily_loss_pct':2.0,'max_positions':8}}
TRADINGVIEW_URL='https://www.tradingview.com/chart/?symbol=BIST%3A{ticker}'

def _dir():
    if platform.system()=='Darwin':base=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':base=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:base=Path.home()/'.bist-ai-terminal'
    base.mkdir(parents=True,exist_ok=True);return base
def _file():return _dir()/'execution_state.json'
def _save():
    try:
        with _LOCK:d=dict(_STATE)
        _file().write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:pass
def _load():
    try:
        p=_file()
        if p.exists():
            d=json.loads(p.read_text(encoding='utf-8'))
            with _LOCK:
                _STATE['kill_switch']=bool(d.get('kill_switch',False))
                _STATE['paper_orders']=d.get('paper_orders') or []
                _STATE['paper_positions']=d.get('paper_positions') or {}
                _STATE['daily_realized']=d.get('daily_realized') or {}
                if isinstance(d.get('risk'),dict):
                    old=d.get('risk') or {}
                    if 'max_open_orders' in old and 'max_positions' not in old:old['max_positions']=old['max_open_orders']
                    _STATE['risk'].update({k:v for k,v in old.items() if k in _STATE['risk']})
    except Exception:pass
_load()

def broker_status():
    direct=bool(os.getenv('INFO_OFFICIAL_API_URL') and os.getenv('INFO_API_TOKEN'))
    return {
      'broker':'INFO_YATIRIM',
      'tradingview_supported':True,
      'tradingview_live_market_data':'Broker-connected live data supported by Info; volume may require paid data entitlement.',
      'direct_official_api_configured':direct,
      'direct_live_execution_enabled':False,
      'live_execution_reason':'Public official REST/WebSocket trading contract not verified. Direct live submission remains locked.',
      'paper_trading':True,
      'kill_switch':_STATE['kill_switch'],
      'risk':dict(_STATE['risk']),
      'paper_positions':dict(_STATE.get('paper_positions') or {}),
      'daily_realized_pnl':float((_STATE.get('daily_realized') or {}).get(time.strftime('%Y-%m-%d'),0) or 0),
      'risk_controls':['max_order_value','max_position_pct (post-trade)','max_positions','max_daily_loss_pct (realized P&L)','kill_switch'],
      'security':'Broker credentials are never stored in BIST AI Terminal.'
    }

def quote(ticker):
    code=ticker.upper().replace('.IS','');rows=scan_codes([code]);r=rows[0] if rows else {}
    return {'ticker':code,'price':r.get('price'),'avg_value_turnover_20':r.get('avg_value_turnover_20'),'risk':r.get('risk'),'short_score':r.get('short_score'),'long_score':r.get('long_score')}

def order_preview(payload):
    code=str(payload.get('ticker','')).upper().replace('.IS','')
    side=str(payload.get('side','BUY')).upper()
    qty=max(0,int(float(payload.get('quantity',0) or 0)))
    order_type=str(payload.get('order_type','LIMIT')).upper()
    q=quote(code);market_price=float(q.get('price') or 0)
    limit=float(payload.get('limit_price') or market_price or 0)
    px=limit if order_type=='LIMIT' and limit>0 else market_price
    notional=qty*px
    portfolio=float(payload.get('portfolio_value') or 1_000_000)
    pos_pct=(notional/portfolio*100) if portfolio>0 else 100
    adv=float(q.get('avg_value_turnover_20') or 0)
    issues=[];warnings=[]
    if not code:issues.append('Ticker gerekli')
    if side not in {'BUY','SELL'}:issues.append('Geçersiz yön')
    if qty<=0:issues.append('Adet sıfırdan büyük olmalı')
    if px<=0:issues.append('Geçerli fiyat bulunamadı')
    if _STATE['kill_switch']:issues.append('KILL SWITCH aktif')
    risk=_STATE['risk']
    if notional>float(risk['max_order_value']):issues.append('Emir değeri maksimum emir limitini aşıyor')
    positions=_STATE.get('paper_positions') or {};cur=positions.get(code) or {'quantity':0,'avg_price':0}
    cur_qty=int(cur.get('quantity') or 0);post_qty=cur_qty+(qty if side=='BUY' else -qty)
    post_notional=max(0,post_qty)*px;post_pct=(post_notional/portfolio*100) if portfolio>0 else 100
    if side=='SELL' and qty>cur_qty:issues.append('Paper long pozisyondan fazla satış yapılamaz')
    if post_pct>float(risk['max_position_pct']):issues.append('İşlem sonrası pozisyon portföy yüzdesi limitini aşıyor')
    if side=='BUY' and cur_qty<=0 and post_qty>0 and len([p for p in positions.values() if int(p.get('quantity') or 0)>0])>=int(risk['max_positions']):issues.append('Maksimum açık paper pozisyon sayısına ulaşıldı')
    today=time.strftime('%Y-%m-%d');realized=float((_STATE.get('daily_realized') or {}).get(today,0) or 0)
    if side=='BUY' and portfolio>0 and realized<=-(portfolio*float(risk['max_daily_loss_pct'])/100):issues.append('Günlük gerçekleşmiş zarar limiti aşıldı; yeni paper alış bloke')
    if adv>0 and notional>adv*.05:warnings.append('Emir değeri 20G ortalama işlem değerinin %5 üzerinde')
    if (q.get('risk') or 0)>=80:warnings.append('Hisse risk skoru yüksek')
    return {'ticker':code,'side':side,'quantity':qty,'order_type':order_type,'reference_price':round(px,4),'notional':round(notional,2),
            'portfolio_value':portfolio,'position_pct':round(pos_pct,2),'post_position_pct':round(post_pct,2),'quote':q,'blocked':bool(issues),'issues':issues,'warnings':warnings,
            'tradingview_url':TRADINGVIEW_URL.format(ticker=code),'execution_mode':'PAPER_OR_MANUAL_TRADINGVIEW',
            'note':'Live direct broker execution is disabled until an official documented Info API contract is configured.'}

def paper_order(payload):
    p=order_preview(payload)
    if p['blocked']:return {'status':'BLOCKED','preview':p}
    order={'id':uuid.uuid4().hex[:12],'created_at':time.strftime('%d.%m.%Y %H:%M:%S'),'status':'PAPER_FILLED',
           'ticker':p['ticker'],'side':p['side'],'quantity':p['quantity'],'price':p['reference_price'],'notional':p['notional'],'order_type':p['order_type']}
    with _LOCK:
        code=p['ticker'];qty=int(p['quantity']);px=float(p['reference_price']);pos=_STATE['paper_positions'].get(code) or {'quantity':0,'avg_price':0}
        cq=int(pos.get('quantity') or 0);avg=float(pos.get('avg_price') or 0)
        if p['side']=='BUY':
            nq=cq+qty;navg=((cq*avg)+(qty*px))/nq if nq else 0
            _STATE['paper_positions'][code]={'quantity':nq,'avg_price':round(navg,4)}
        else:
            pnl=(px-avg)*qty;day=time.strftime('%Y-%m-%d');_STATE['daily_realized'][day]=round(float(_STATE['daily_realized'].get(day,0) or 0)+pnl,2)
            nq=cq-qty
            if nq>0:_STATE['paper_positions'][code]={'quantity':nq,'avg_price':avg}
            else:_STATE['paper_positions'].pop(code,None)
            order['realized_pnl']=round(pnl,2)
        _STATE['paper_orders'].insert(0,order);_STATE['paper_orders']=_STATE['paper_orders'][:1000]
    _save();return {'status':'OK','order':order,'preview':p,'positions':dict(_STATE['paper_positions'])}

def orders(limit=100):
    with _LOCK:return {'orders':list(_STATE['paper_orders'][:max(1,min(int(limit),500))])}

def set_kill_switch(enabled):
    with _LOCK:_STATE['kill_switch']=bool(enabled)
    _save();return {'kill_switch':_STATE['kill_switch']}

def update_risk(payload):
    allowed={'max_order_value','max_position_pct','max_daily_loss_pct','max_positions'}
    with _LOCK:
        for k in allowed:
            if k in payload:
                try:_STATE['risk'][k]=max(0,float(payload[k]))
                except Exception:pass
    _save();return {'risk':dict(_STATE['risk'])}
