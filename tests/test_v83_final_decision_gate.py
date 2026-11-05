from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v83_final_decision_gate_navigation_and_script():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert 'data-view="decisiongate"' in html
    assert 'Nihai Karar Kapısı' in html
    assert '/static/v32.js' in html
    assert '\\n' not in html

def test_v83_committee_hard_gates_signal_guard():
    text=(ROOT/'app'/'investment_committee.py').read_text(encoding='utf-8')
    assert "gate('Sinyal Kontrolü'" in text
    assert "guard.get('status')=='CLEAR'" in text
    assert "'signal_guard':guard" in text

def test_v83_decision_gate_uses_committee_api_and_surfaces_vetoes():
    js=(ROOT/'app'/'static'/'v32.js').read_text(encoding='utf-8')
    assert "/api/committee/" in js
    assert "Hard veto" in js
    assert "Signal Guard" in js
    assert "Trap Defense" in js
    assert "KAP PIT" in js

def test_v83_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=83
    assert "'version':" in text
