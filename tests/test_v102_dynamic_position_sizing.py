from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v102_sizing_only_reduces_base_exposure():
    text=(ROOT/'app'/'dynamic_position_sizing.py').read_text(encoding='utf-8')
    assert "amount=min(base,base*combined)" in text
    assert "pct=min(base_pct,base_pct*combined)" in text
    assert "cannot enlarge exposure" in text

def test_v102_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v42.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/dynamic-position-sizing/{ticker}" in main
    assert "Dynamic Position Sizing" in js
    assert 'data-view="positionsizing"' in html

def test_v102_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='102.0.0'" in text
    assert "'version':'102.0.0'" in text
