from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v94_gate_interaction_labels_and_overlap():
    text=(ROOT/'app'/'gate_interaction_analysis.py').read_text(encoding='utf-8')
    for token in ['REDUNDANCY_REVIEW','JOINT_PROTECTIVE','JOINT_COSTLY','failure_jaccard_pct','interaction_delta_pct']:
        assert token in text
    assert "no gate is removed or weakened automatically" in text

def test_v94_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v34.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/gate-interactions" in main
    assert "Gate Interaction Analysis" in js
    assert "/static/v34.js?v=94.0.0" in html

def test_v94_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=94
    assert "'version':" in text
