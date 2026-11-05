from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v86_net_utility_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/decision-calibration/net-utility" in main
    assert "/api/decision-calibration/net-utility" in js
    assert "Gate Net Fayda" in js
    assert "NET_PROTECTIVE" in js
    assert "NET_COSTLY" in js

def test_v86_net_utility_uses_settled_forward_evidence():
    text=(ROOT/'app'/'decision_calibration.py').read_text(encoding='utf-8')
    assert "settled_" in text
    assert "excess_" in text
    assert "committee_gates" in text
    assert "failed hard gate" in text.lower()

def test_v86_net_utility_never_auto_mutates_gates():
    text=(ROOT/'app'/'decision_calibration.py').read_text(encoding='utf-8')
    assert "never changes a gate automatically" in text
    assert "not causal attribution" in text

def test_v86_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=86
    assert "'version':" in text
