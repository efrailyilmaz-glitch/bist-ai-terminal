from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v116_factory_has_integrity_preflight():
    text=(ROOT/'app'/'research_factory_v2.py').read_text(encoding='utf-8')
    for token in ['DATA_TRUST_BLOCK','PIT_UNIVERSE_NOT_READY','RESEARCH_INTEGRITY_BLOCK','FEATURE_LINEAGE_BLOCK','PREFLIGHT_BLOCK']:
        assert token in text
    assert "No stage can bypass integrity blockers" in text

def test_v116_factory_is_research_paper_only():
    text=(ROOT/'app'/'research_factory_v2.py').read_text(encoding='utf-8')
    assert "'live_execution':False" in text
    assert "no run can auto-promote or place orders" in text

def test_v116_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v53.js').read_text(encoding='utf-8')
    assert "/api/research-factory/run" in main
    assert "/api/research-factory/status" in main
    assert "Continuous Research Factory" in js

def test_v116_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=116
    assert "'version':" in text
