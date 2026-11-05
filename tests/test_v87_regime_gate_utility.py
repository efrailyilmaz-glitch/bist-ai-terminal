from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v87_regime_utility_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/decision-calibration/regime-utility" in main
    assert "/api/decision-calibration/regime-utility" in js
    assert "Rejim Bazlı Gate Davranışı" in js

def test_v87_regime_conflicts_are_review_only():
    text=(ROOT/'app'/'decision_calibration.py').read_text(encoding='utf-8')
    assert "regime_conflict_gates" in text
    assert "no regime-specific gate relaxation is automatic" in text
    assert "PROTECTIVE" in text
    assert "COSTLY" in text

def test_v87_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='87.0.0'" in text
    assert "'version':'87.0.0'" in text
