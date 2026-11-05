from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v92_promotion_requires_forward_governance_gates():
    text=(ROOT/'app'/'policy_promotion_governance.py').read_text(encoding='utf-8')
    for token in ['Minimum forward span','Minimum settled signals','Paired CI support','Regime coverage','Persistence','Multi-horizon maturity','Utility drawdown','Missed-opportunity rate']:
        assert token in text
    assert "Historical backtests cannot satisfy these gates" in text

def test_v92_no_automatic_activation_or_live_execution():
    text=(ROOT/'app'/'policy_promotion_governance.py').read_text(encoding='utf-8')
    assert "PROMOTION_REVIEW" in text
    assert "'live_execution':False" in text
    assert "no policy is activated" in text

def test_v92_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "/api/policy-promotion" in main
    assert "Policy Promotion Governance" in js
    assert "Forward gün" in js

def test_v92_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=92
    assert "'version':" in text
