from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v110_keeps_quality_and_timing_separate():
    text=(ROOT/'app'/'fundamental_price_fusion.py').read_text(encoding='utf-8')
    assert "GOOD_COMPANY_BAD_ENTRY" in text
    assert "STRONG_CHART_WEAK_FUNDAMENTALS" in text
    assert "FUNDAMENTAL_RISK_OVERRIDE" in text
    assert "Technical strength cannot override" in text

def test_v110_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v48.js').read_text(encoding='utf-8')
    assert "/api/fundamental-price-fusion/{ticker}" in main
    assert "Fundamental + Price Action Fusion" in js

def test_v110_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='110.0.0'" in text
    assert "'version':'110.0.0'" in text
