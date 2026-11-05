from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v91_tournament_uses_all_three_horizons():
    text=(ROOT/'app'/'decision_policy_tournament.py').read_text(encoding='utf-8')
    assert "for h in (5,20,60)" in text
    assert "WEIGHTS={5:0.20,20:0.50,60:0.30}" in text

def test_v91_single_horizon_cannot_win_alone():
    text=(ROOT/'app'/'decision_policy_tournament.py').read_text(encoding='utf-8')
    assert "cross_horizon_ok=mature>=2" in text
    assert "supported_horizons" in text
    assert "single 5d/20d/60d result cannot win alone" in text

def test_v91_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/decision-policy-tournament" in main
    assert "Policy Tournament" in js
    assert "20 / 50 / 30" in js

def test_v91_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='91.0.0'" in text
    assert "'version':'91.0.0'" in text
