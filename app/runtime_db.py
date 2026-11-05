"""V127 resilient SQLite connection helpers for desktop/runtime ledgers."""
from __future__ import annotations
import sqlite3
from pathlib import Path

class SafeConnection(sqlite3.Connection):
    def __del__(self):
        try:self.close()
        except Exception:pass

def connect(path,timeout=15):
    c=sqlite3.connect(Path(path),timeout=timeout,factory=SafeConnection)
    try:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=NORMAL')
        c.execute('PRAGMA busy_timeout=15000')
        c.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    return c

def integrity(path):
    p=Path(path)
    if not p.exists():return {'status':'NOT_CREATED','path':str(p)}
    c=connect(p)
    try:
        row=c.execute('PRAGMA quick_check').fetchone()
        ok=bool(row and str(row[0]).lower()=='ok')
        return {'status':'PASS' if ok else 'FAIL','path':str(p),'result':row[0] if row else None}
    finally:c.close()
