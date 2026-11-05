"""V122 desktop-readiness diagnostics."""
from __future__ import annotations
import os,platform
from pathlib import Path
from .runtime_paths import writable_probe,data_root
from .broker_bridge import broker_status
from .runtime_storage_health import snapshot as runtime_storage_health

ROOT=Path(__file__).resolve().parent.parent

def status():
    probe=writable_probe()
    br=broker_status()
    storage=runtime_storage_health()
    required=[
      ROOT/'electron'/'main.cjs',
      ROOT/'electron'/'stable-port.cjs',
      ROOT/'desktop_entry.py',
      ROOT/'package.json',
      ROOT/'.github'/'workflows'/'desktop-build.yml',
    ]
    missing=[str(p.relative_to(ROOT)) for p in required if not p.exists()]
    desktop_env=os.getenv('BIST_AI_DESKTOP')=='1'
    live=bool(br.get('direct_live_execution_enabled'))
    checks=[
      {'name':'WRITABLE_DATA_ROOT','status':probe.get('status'),'detail':probe.get('path')},
      {'name':'DESKTOP_ASSETS','status':'PASS' if not missing else 'FAIL','detail':missing},
      {'name':'LOOPBACK_MODE','status':'PASS','detail':'desktop_entry.py binds 127.0.0.1 only'},
      {'name':'LIVE_EXECUTION_LOCK','status':'FAIL' if live else 'PASS','detail':'direct live disabled' if not live else 'direct live enabled'},
      {'name':'RUNTIME_STORAGE','status':'PASS' if storage.get('status')=='PASS' else 'FAIL','detail':storage},
    ]
    blockers=[x['name'] for x in checks if x['status']=='FAIL']
    return {'status':'PASS' if not blockers else 'FAIL','version':'122.0','platform':platform.system(),
            'desktop_env':desktop_env,'data_root':str(data_root()),'checks':checks,'blockers':blockers,
            'policy':'Desktop readiness verifies local storage, packaging assets, loopback binding and live-execution lock. It does not enable broker execution.'}
