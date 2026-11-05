from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v82_model_robot_trust_navigation_and_script():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert 'data-view="modeltrust"' in html
    assert 'Model / Robot Güven' in html
    assert '/static/v31.js?v=82.0.0' in html
    assert '\\\\n' not in html

def test_v82_trust_center_sources_are_forward_and_reproducible():
    js=(ROOT/'app'/'static'/'v31.js').read_text(encoding='utf-8')
    assert "/api/model-registry?limit=20" in js
    assert "arenaAPI('account')" in js
    assert "forward paper" in js.lower()
    assert "Canlı işlem" in js
    assert "KAPALI" in js

def test_v82_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=82
    assert "'version':" in text
