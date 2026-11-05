from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def test_v127_fastapi_uses_lifespan_not_deprecated_on_event():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "lifespan=lifespan" in text
    assert "@app.on_event('startup')" not in text

def test_v127_offline_chart_loader_and_desktop_vendor_step():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    loader=(ROOT/'app'/'static'/'chart-loader.js').read_text(encoding='utf-8')
    workflow=(ROOT/'.github'/'workflows'/'desktop-build.yml').read_text(encoding='utf-8')
    assert '/static/chart-loader.js' in html
    assert 'unpkg.com/lightweight-charts@5.2.1' in loader
    assert '/static/vendor/lightweight-charts.standalone.production.js' in loader
    assert 'Vendor chart library for offline desktop' in workflow
    assert 'node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js' in workflow

def test_v127_sqlite_runtime_hardening():
    db=(ROOT/'app'/'runtime_db.py').read_text(encoding='utf-8')
    assert 'journal_mode=WAL' in db
    assert 'busy_timeout=15000' in db
    assert 'foreign_keys=ON' in db
    assert 'PRAGMA quick_check' in db
    for p in ['xs_paper.py','model_registry.py','experience_engine.py','champion_governance.py']:
        assert 'runtime_db import connect as db_connect' in (ROOT/'app'/p).read_text(encoding='utf-8')

def test_v127_runtime_storage_health_exposed():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    desktop=(ROOT/'app'/'desktop_readiness.py').read_text(encoding='utf-8')
    assert "/api/runtime-storage-health" in main
    assert 'RUNTIME_STORAGE' in desktop

def test_v127_versions():
    pkg=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert pkg['version']=='127.0.0'
    assert "version='127.0.0'" in main
    assert 'V127.0.0' in html
