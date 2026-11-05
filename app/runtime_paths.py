"""V122 shared writable runtime paths for web/desktop deployments."""
from __future__ import annotations
import os,platform,tempfile
from pathlib import Path

APP_NAME='BIST AI Terminal'

def data_root()->Path:
    override=os.getenv('BIST_AI_DATA_DIR')
    if override:
        p=Path(override).expanduser()
    elif platform.system()=='Darwin':
        p=Path.home()/'Library'/'Application Support'/APP_NAME
    elif platform.system()=='Windows':
        p=Path(os.getenv('APPDATA') or Path.home())/APP_NAME
    else:
        p=Path.home()/'.bist-ai-terminal'
    p.mkdir(parents=True,exist_ok=True)
    return p

def data_path(*parts)->Path:
    p=data_root().joinpath(*[str(x) for x in parts])
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def writable_probe():
    root=data_root()
    try:
        fd,name=tempfile.mkstemp(prefix='.bist-write-',dir=str(root))
        os.close(fd);os.unlink(name)
        return {'status':'PASS','path':str(root),'override':bool(os.getenv('BIST_AI_DATA_DIR'))}
    except Exception as e:
        return {'status':'FAIL','path':str(root),'error':str(e)[:180],'override':bool(os.getenv('BIST_AI_DATA_DIR'))}
