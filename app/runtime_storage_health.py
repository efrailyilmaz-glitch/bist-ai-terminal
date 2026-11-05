"""V127 runtime storage and SQLite integrity diagnostics."""
from __future__ import annotations
import shutil
from .runtime_paths import data_root
from .runtime_db import integrity

KNOWN_DBS=[
 'experience.db','xs_paper.db','model_registry.db','champion_governance.db'
]

def snapshot():
    root=data_root()
    total,used,free=shutil.disk_usage(root)
    dbs=[integrity(root/name) for name in KNOWN_DBS]
    failed=[x for x in dbs if x.get('status')=='FAIL']
    low_space=free < 512*1024*1024
    status='FAIL' if failed else 'WARN' if low_space else 'PASS'
    return {
      'status':status,'version':'127.0','data_root':str(root),
      'disk':{'total_bytes':total,'used_bytes':used,'free_bytes':free,'low_space':low_space},
      'databases':dbs,
      'policy':'Read-only runtime storage diagnostic. Database integrity uses SQLite quick_check and never modifies ledger contents.'
    }
