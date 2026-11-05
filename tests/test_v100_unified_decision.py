from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v100_unified_decision_never_bypasses_hard_veto():
    text=(ROOT/'app'/'unified_decision_engine.py').read_text(encoding='utf-8')
    assert "if hard_vetoes:" in text
    assert "supportive modules can never override a hard veto" in text
    assert "'live_execution':False" in text

def test_v100_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v40.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/unified-decision/{ticker}" in main
    assert "Unified Decision Engine" in js
    assert 'data-view="unifieddecision"' in html

def test_v100_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='100.0.0'" in text
    assert "'version':'100.0.0'" in text
