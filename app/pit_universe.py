"""V64 point-in-time universe registry.
Only explicitly VERIFIED+COMPLETE historical membership datasets may clear survivorship risk.
No heuristic/current-universe data is silently promoted to PIT truth.
"""
from __future__ import annotations
from contextlib import closing
import hashlib,json,sqlite3,time
from .runtime_db import connect as db_connect
from .runtime_paths import data_path

def _db():return data_path('pit_universe.db')

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS datasets(
      id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, status TEXT, coverage_start TEXT, coverage_end TEXT,
      source_hash TEXT, created_epoch REAL, created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS memberships(
      dataset_id INTEGER, ticker TEXT, start_date TEXT, end_date TEXT,
      PRIMARY KEY(dataset_id,ticker,start_date)
    )''')
    c.commit();return c

def _hash(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def register_dataset(rows,source,status='INCOMPLETE',coverage_start=None,coverage_end=None,source_hash=None):
    """Internal ingestion hook. COMPLETE means the source claims historical universe completeness.
    Callers are responsible for source licensing/provenance; no API auto-promotes a dataset.
    """
    clean=[]
    for r in rows or []:
        ticker=str(r.get('ticker') or '').upper().replace('.IS','').strip()
        start=str(r.get('start_date') or '')[:10]
        end=str(r.get('end_date') or '')[:10] or None
        if ticker and start:clean.append({'ticker':ticker,'start_date':start,'end_date':end})
    if not clean:return {'status':'NO_ROWS'}
    st='COMPLETE' if str(status).upper()=='COMPLETE' else 'INCOMPLETE'
    sh=source_hash or _hash(clean)
    now=time.time()
    with closing(_conn()) as c, c:
        cur=c.execute('INSERT INTO datasets(source,status,coverage_start,coverage_end,source_hash,created_epoch,created_at) VALUES(?,?,?,?,?,?,?)',
          (str(source or 'UNKNOWN'),st,coverage_start,coverage_end,sh,now,time.strftime('%d.%m.%Y %H:%M:%S')))
        did=cur.lastrowid
        c.executemany('INSERT INTO memberships(dataset_id,ticker,start_date,end_date) VALUES(?,?,?,?)',
          [(did,x['ticker'],x['start_date'],x['end_date']) for x in clean])
    return {'status':'OK','dataset_id':did,'rows':len(clean),'dataset_status':st,'source_hash':sh}

def active_dataset():
    with closing(_conn()) as c, c:
        c.row_factory=sqlite3.Row
        r=c.execute("SELECT * FROM datasets WHERE status='COMPLETE' ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None

def dataset_status():
    with closing(_conn()) as c, c:
        c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT * FROM datasets ORDER BY id DESC LIMIT 20').fetchall()]
    active=next((x for x in rows if x.get('status')=='COMPLETE'),None)
    return {'status':'PIT_VERIFIED' if active else 'CURRENT_UNIVERSE_PROXY','active_dataset':active,'datasets':rows,
            'historical_universe_point_in_time':bool(active),
            'survivorship_bias_risk':not bool(active)}

def training_universe(current_tickers,limit=120):
    active=active_dataset()
    if not active:
        names=list(dict.fromkeys([str(x).upper().replace('.IS','') for x in (current_tickers or [])]))[:max(5,min(int(limit),500))]
        return {'tickers':names,'integrity':{'status':'CAUTION','flags':['HISTORICAL_UNIVERSE_NOT_POINT_IN_TIME','CURRENT_UNIVERSE_PROXY'],
                'historical_universe_point_in_time':False,'current_universe_proxy':True,'survivorship_bias_risk':True,
                'dataset_id':None,'source':None}}
    with closing(_conn()) as c, c:
        names=[r[0] for r in c.execute('SELECT DISTINCT ticker FROM memberships WHERE dataset_id=? ORDER BY ticker',(int(active['id']),)).fetchall()]
    names=names[:max(5,min(int(limit),500))]
    return {'tickers':names,'integrity':{'status':'PASS','flags':[],'historical_universe_point_in_time':True,
            'current_universe_proxy':False,'survivorship_bias_risk':False,'dataset_id':active['id'],
            'source':active.get('source'),'source_hash':active.get('source_hash'),
            'coverage_start':active.get('coverage_start'),'coverage_end':active.get('coverage_end')}}

def intervals(ticker,dataset_id=None):
    active=active_dataset()
    did=dataset_id or (active or {}).get('id')
    if not did:return []
    code=str(ticker).upper().replace('.IS','')
    with closing(_conn()) as c, c:
        rows=c.execute('SELECT start_date,end_date FROM memberships WHERE dataset_id=? AND ticker=? ORDER BY start_date',(int(did),code)).fetchall()
    return [{'start_date':a,'end_date':b} for a,b in rows]

def date_allowed(ticker,date_text,dataset_id=None):
    ints=intervals(ticker,dataset_id)
    if not ints:return False
    d=str(date_text)[:10]
    return any(d>=x['start_date'] and (not x['end_date'] or d<=x['end_date']) for x in ints)

def filter_frame(ticker,frame,integrity):
    if frame is None or getattr(frame,'empty',True):return frame
    if (integrity or {}).get('status')!='PASS':return frame
    did=integrity.get('dataset_id')
    mask=[date_allowed(ticker,x,did) for x in frame.index.astype(str)]
    return frame.loc[mask]
