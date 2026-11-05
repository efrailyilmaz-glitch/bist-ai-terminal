"""V57 immutable model/reproducibility registry for XS decisions."""
from __future__ import annotations
from contextlib import closing
from .runtime_db import connect as db_connect
import hashlib,json,platform,sqlite3,sys,time
from pathlib import Path

def _db():
    from .runtime_paths import data_path
    return data_path('model_registry.db')

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS artifacts(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_epoch REAL, created_at TEXT,
      model_name TEXT, model_version TEXT, train_cutoff TEXT, as_of TEXT, seed INTEGER,
      feature_schema_hash TEXT, data_fingerprint TEXT, dependency_fingerprint TEXT,
      model_fingerprint TEXT, metadata_json TEXT
    )''')
    c.commit();return c

def _h(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def register(meta:dict):
    deps={'python':sys.version.split()[0],'platform':platform.platform()}
    try:
        import numpy,pandas
        deps.update({'numpy':numpy.__version__,'pandas':pandas.__version__})
    except Exception:pass
    try:
        import lightgbm
        deps['lightgbm']=lightgbm.__version__
    except Exception:deps['lightgbm']='UNAVAILABLE'
    feature_hash=_h(meta.get('features') or [])
    data_fp=_h({'train_rows':meta.get('train_rows'),'train_dates':meta.get('train_dates'),
                'train_cutoff':meta.get('train_cutoff'),'symbols':meta.get('symbols'),
                'label':meta.get('label'),'as_of':meta.get('as_of'),
                'universe_integrity':meta.get('universe_integrity')})
    dep_fp=_h(deps)
    model_fp=_h({'name':meta.get('model_name'),'version':meta.get('model_version'),'seed':meta.get('seed'),
                 'features':feature_hash,'data':data_fp,'deps':dep_fp,'params':meta.get('params')})
    now=time.time()
    with closing(_conn()) as c:
        cur=c.execute('''INSERT INTO artifacts(created_epoch,created_at,model_name,model_version,train_cutoff,as_of,seed,
          feature_schema_hash,data_fingerprint,dependency_fingerprint,model_fingerprint,metadata_json)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
          (now,time.strftime('%d.%m.%Y %H:%M:%S'),meta.get('model_name'),meta.get('model_version'),
           meta.get('train_cutoff'),meta.get('as_of'),meta.get('seed'),feature_hash,data_fp,dep_fp,model_fp,
           json.dumps({**meta,'dependencies':deps},ensure_ascii=False,sort_keys=True,default=str)))
        rid=cur.lastrowid
    return {'registry_id':rid,'model_fingerprint':model_fp,'feature_schema_hash':feature_hash,
            'data_fingerprint':data_fp,'dependency_fingerprint':dep_fp}

def history(limit=100):
    with closing(_conn()) as c:
        c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT * FROM artifacts ORDER BY id DESC LIMIT ?',(max(1,min(int(limit),1000)),)).fetchall()]
    return {'status':'OK','rows':rows}

def get(registry_id:int):
    with closing(_conn()) as c:
        c.row_factory=sqlite3.Row
        r=c.execute('SELECT * FROM artifacts WHERE id=?',(int(registry_id),)).fetchone()
    return {'status':'OK','row':dict(r)} if r else {'status':'NOT_FOUND'}
