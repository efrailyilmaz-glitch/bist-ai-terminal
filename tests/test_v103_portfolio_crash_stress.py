from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v103_stress_scenarios_include_macro_proxies():
    text=(ROOT/'app'/'portfolio_crash_scenarios.py').read_text(encoding='utf-8')
    for token in ['BIST_MINUS_10','BIST_MINUS_15','CORRELATION_SPIKE','LIQUIDITY_DRY_UP','SECTOR_CLUSTER_SHOCK','RATE_SHOCK_PROXY','FX_SHOCK_PROXY','VOLATILITY_REGIME_BREAK']:
        assert token in text
    assert "Proxy scenarios are explicitly labelled" in text

def test_v103_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v43.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/portfolio-crash-stress" in main
    assert "Portfolio Stress & Crash Scenarios" in js
    assert 'data-view="portfoliostress"' in html

def test_v103_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=103
    assert "'version':" in text
