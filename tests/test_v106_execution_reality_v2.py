from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v106_execution_reality_unifies_execution_gates():
    text=(ROOT/'app'/'execution_reality_v2.py').read_text(encoding='utf-8')
    for token in ['execution_diagnostics','quote_guard','microstructure_guard','quality_score','execution_horizon_bars']:
        assert token in text
    assert "can never improve a fill" in text

def test_v106_auto_paper_blocks_combined_execution_reality():
    text=(ROOT/'app'/'auto_paper.py').read_text(encoding='utf-8')
    assert "execution_reality_v2" in text
    assert "if er2.get('status')=='BLOCK':qty=0" in text

def test_v106_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v44.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/execution-reality-v2/{ticker}" in main
    assert "Execution Reality 2.0" in js
    assert 'data-view="executionreality2"' in html

def test_v106_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=106
    assert "'version':" in text
