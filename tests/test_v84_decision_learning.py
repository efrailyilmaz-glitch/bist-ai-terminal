from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v84_decision_learning_navigation_and_script():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert 'data-view="decisionlearning"' in html
    assert 'Karar Öğrenme' in html
    assert '/static/v33.js?v=84.0.0' in html
    assert '\\n' not in html

def test_v84_committee_gates_are_persisted_to_forward_ledger():
    text=(ROOT/'app'/'experience_engine.py').read_text(encoding='utf-8')
    assert "'committee_gates':committee.get('gates')" in text

def test_v84_gate_calibration_is_review_only():
    text=(ROOT/'app'/'decision_calibration.py').read_text(encoding='utf-8')
    assert "REVIEW_TOO_STRICT" in text
    assert "never weakened or removed automatically" in text
    assert "settled_" in text
    assert "excess_" in text

def test_v84_api_and_ui_sources():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/decision-calibration" in main
    assert "/api/decision-calibration/report" in main
    assert "/api/experience/settle" in js
    assert "/api/experience/calibration" in js
    assert "/api/decision-calibration?" in js

def test_v84_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='84.0.0'" in text
    assert "'version':'84.0.0'" in text
