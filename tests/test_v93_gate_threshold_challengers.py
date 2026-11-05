from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v93_threshold_catalog():
    text=(ROOT/'app'/'gate_threshold_challenger.py').read_text(encoding='utf-8')
    for token in ["guard_50","guard_60","guard_65","guard_70","trap_50","trap_60","trap_65","trap_70","risk_75","risk_82","risk_88","anomaly_80","anomaly_90","anomaly_95"]:
        assert token in text

def test_v93_is_prospective_and_non_mutating():
    text=(ROOT/'app'/'gate_threshold_challenger.py').read_text(encoding='utf-8')
    assert "STALE_SIGNAL_ID" in text
    assert "max_signal_age_sec=120" in text
    assert "historical backfill is forbidden" in text
    assert "thresholds are never changed automatically" in text

def test_v93_background_records_threshold_shadows():
    text=(ROOT/'app'/'background_supervisor.py').read_text(encoding='utf-8')
    assert "record_gate_threshold_shadow" in text

def test_v93_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/gate-threshold-challengers" in main
    assert "Gate Threshold Challenger Lab" in js

def test_v93_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='93.0.0'" in text
    assert "'version':'93.0.0'" in text
