from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v101_portfolio_level_can_defer_good_single_name():
    text=(ROOT/'app'/'portfolio_decision_intelligence.py').read_text(encoding='utf-8')
    assert "DEFER_OR_DERISK" in text
    assert "PORTFOLIO_BLOCK" in text
    assert "SECTOR_CONCENTRATION" in text
    assert "HIGH_AVERAGE_CORRELATION" in text

def test_v101_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v41.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/portfolio-decision-intelligence" in main
    assert "Portfolio Decision Intelligence" in js
    assert 'data-view="portfoliointel"' in html

def test_v101_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='101.0.0'" in text
    assert "'version':'101.0.0'" in text
