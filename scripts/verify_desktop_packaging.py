from __future__ import annotations
import json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
errors=[]

pkg=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
version=str(pkg.get('version') or '')
main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
index=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
electron=(ROOT/'electron'/'main.cjs').read_text(encoding='utf-8')
entry=(ROOT/'desktop_entry.py').read_text(encoding='utf-8')
workflow=(ROOT/'.github'/'workflows'/'desktop-build.yml').read_text(encoding='utf-8')

if f"version='{version}'" not in main: errors.append('package.json version != FastAPI version')
if f'V{version}' not in index: errors.append('package.json version != UI version')
for token in ["nodeIntegration: false","contextIsolation: true","sandbox: true","127.0.0.1","BIST_AI_DATA_DIR"]:
    if token not in electron: errors.append('electron security/runtime token missing: '+token)
if 'host="127.0.0.1"' not in entry: errors.append('desktop backend is not explicitly loopback-bound')
for token in ['windows-latest','macos-15-intel','macos-15','dist:win','dist:mac:x64','dist:mac:arm64']:
    if token not in workflow: errors.append('desktop workflow target missing: '+token)
for icon in ['icon.png','icon.ico','icon.icns']:
    if not (ROOT/'build'/icon).exists(): errors.append('generated icon missing: '+icon)
extra=(pkg.get('build') or {}).get('extraResources') or []
if not any(x.get('from')=='dist/bist-ai-backend' and x.get('to')=='backend' for x in extra if isinstance(x,dict)):
    errors.append('packaged Python backend resource mapping missing')

if errors:
    print('\n'.join('ERROR: '+x for x in errors))
    sys.exit(1)
print(f'Desktop packaging inputs verified for {version}.')
