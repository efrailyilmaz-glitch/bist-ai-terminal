from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def test_v122_shared_runtime_data_root():
    rp=(ROOT/'app'/'runtime_paths.py').read_text(encoding='utf-8')
    assert "BIST_AI_DATA_DIR" in rp
    for p in ['broker_bridge.py','experience_engine.py','background_supervisor.py','opportunity_engine.py','model_registry.py','champion_governance.py','xs_paper.py']:
        text=(ROOT/'app'/p).read_text(encoding='utf-8')
        assert 'runtime_paths' in text

def test_v122_electron_passes_userdata_to_backend_in_both_modes():
    text=(ROOT/'electron'/'main.cjs').read_text(encoding='utf-8')
    assert "app.getPath('userData')" in text
    assert text.count('BIST_AI_DATA_DIR: dataDir')==2

def test_v122_desktop_readiness_and_package_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    pkg=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
    assert "/api/desktop-readiness" in main
    assert int(pkg['version'].split('.',1)[0])>=122
    assert int(main.split("version='",1)[1].split('.',1)[0])>=122
