from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v85_missed_opportunity_audit_is_exposed():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "/api/decision-calibration/missed-opportunities" in main
    assert "missed_opportunity_audit" in main

def test_v85_false_negative_audit_is_forward_only_and_non_mutating():
    text=(ROOT/'app'/'decision_calibration.py').read_text(encoding='utf-8')
    assert "committee_decision='NO_TRADE'" in text
    assert "settled_" in text
    assert "excess_" in text
    assert "no gate is auto-disabled" in text

def test_v85_decision_learning_ui_surfaces_missed_opportunities():
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "missedOpportunityBox33" in js
    assert "/api/decision-calibration/missed-opportunities" in js
    assert "Kaçırılan Fırsat Denetimi" in js
    assert "NO_TRADE settle" in js

def test_v85_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='85.0.0'" in text
    assert "'version':'85.0.0'" in text
