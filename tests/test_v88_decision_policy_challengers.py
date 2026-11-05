from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v88_shadow_policy_module_is_prospective_only():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "record(signal_id,committee)" in text
    assert "policy_shadow" in text
    assert "JOIN signals" in text
    assert "settled_" in text
    assert "never mutates incumbent thresholds automatically" in text
    assert "STALE_SIGNAL_ID" in text
    assert "max_signal_age_sec=120" in text

def test_v88_background_records_shadow_at_signal_time():
    text=(ROOT/'app'/'background_supervisor.py').read_text(encoding='utf-8')
    assert "record_policy_shadow" in text
    assert "if rid: record_policy_shadow(rid,c)" in text

def test_v88_shadow_challenger_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/decision-policy-challengers" in main
    assert "/api/decision-policy-challengers" in js
    assert "Decision Policy Challengers" in js
    assert "CHALLENGER_REVIEW" in js
    assert "shadow only" in js

def test_v88_policy_catalog_has_incumbent_strict_adaptive():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "'id':'incumbent'" in text
    assert "'id':'strict'" in text
    assert "'id':'adaptive'" in text

def test_v88_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='88.0.0'" in text
    assert "'version':'88.0.0'" in text
