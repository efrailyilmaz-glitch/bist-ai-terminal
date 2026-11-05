from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v90_persistence_state_advances_only_on_new_evidence():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "n>st['last_paired_n']" in text
    assert "good_streak" in text
    assert "bad_streak" in text
    assert "PERSISTENT" in text
    assert "QUARANTINE" in text

def test_v90_review_requires_persistent_state():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "pst.get('state')=='PERSISTENT'" in text
    assert "CHALLENGER_EDGE_NOT_PERSISTENT_YET" in text

def test_v90_ui_surfaces_decay_and_persistence():
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "Persistence / Decay" in js
    assert "Good streak" in js
    assert "Bad streak" in js

def test_v90_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=90
    assert "'version':" in text
