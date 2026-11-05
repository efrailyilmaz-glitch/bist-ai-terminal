from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v117_master_is_veto_oriented():
    text=(ROOT/'app'/'research_integrity_master.py').read_text(encoding='utf-8')
    assert "research_decision_allowed" in text
    assert "Critical integrity failures block" in text
    assert "'live_execution':False" in text

def test_v117_master_aggregates_current_governance():
    text=(ROOT/'app'/'research_integrity_master.py').read_text(encoding='utf-8')
    for token in ['Data Trust 2.0','Feature Governance 3.0','Confidence Calibration','Policy Promotion Governance','Research Factory','Forward Evidence Ledger']:
        assert token in text

def test_v117_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v54.js').read_text(encoding='utf-8')
    assert "/api/research-integrity-master" in main
    assert "Research Integrity Master Dashboard" in js

def test_v117_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='117.0.0'" in text
    assert "'version':'117.0.0'" in text
