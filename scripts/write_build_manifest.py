from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--platform',required=True)
p.add_argument('--arch',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
pkg=json.loads((root/'package.json').read_text(encoding='utf-8'))
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
files=[]
for x in sorted(out.parent.iterdir()):
    if x.is_file() and x.suffix.lower() in {'.exe','.dmg'}:
        h=hashlib.sha256()
        with x.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        files.append({'name':x.name,'size_bytes':x.stat().st_size,'sha256':h.hexdigest()})
data={'product':'BIST AI Terminal','version':pkg['version'],'git_commit':os.getenv('GITHUB_SHA'),
      'platform':a.platform,'arch':a.arch,'artifacts':files,
      'backend':'LOCAL_LOOPBACK','live_execution_default':False}
out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)
