from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v109_event_study_uses_actual_classifier_field():
    text=(ROOT/'app'/'alpha_engine.py').read_text(encoding='utf-8')
    assert "'category':it.get('event')" in text

def test_v109_taxonomy_and_event_horizons():
    kap=(ROOT/'app'/'kap_engine.py').read_text(encoding='utf-8')
    intel=(ROOT/'app'/'kap_intelligence_v2.py').read_text(encoding='utf-8')
    for token in ['MANAGEMENT_CHANGE','ASSET_TRANSACTION','SHARE_SALE_RISK','DEBT_RISK']:
        assert token in kap
    assert "for h in (1,5,20)" in intel
    assert "day-granular" in intel

def test_v109_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v47.js').read_text(encoding='utf-8')
    assert "/api/kap-intelligence-v2/{ticker}" in main
    assert "KAP Intelligence 2.0" in js

def test_v109_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='109.0.0'" in text
    assert "'version':'109.0.0'" in text
