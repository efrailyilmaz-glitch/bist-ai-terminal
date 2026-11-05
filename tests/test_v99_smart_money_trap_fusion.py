from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v99_fusion_separates_clean_and_conflicted_bullish_setups():
    text=(ROOT/'app'/'smart_money_trap_fusion.py').read_text(encoding='utf-8')
    assert "CLEAN_ACCUMULATION_WATCH" in text
    assert "BULLISH_CONFLICT_TRAP_RISK" in text
    assert "DISTRIBUTION_AND_TRAP_RISK" in text
    assert "do not identify a manipulator" in text

def test_v99_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v39.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/smart-money-trap/{ticker}" in main
    assert "/api/smart-money-trap-radar" in main
    assert "Smart Money + Trap Defense Fusion" in js
    assert 'data-view="smartfusion"' in html

def test_v99_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=99
    assert "'version':" in text
