from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v97_regime_adaptive_is_shadow_only():
    text=(ROOT/'app'/'regime_adaptive_policy.py').read_text(encoding='utf-8')
    assert "SHADOW_REGIME_CHALLENGER" in text
    assert "No automatic regime-based policy switching" in text
    assert "'live_execution':False" in text

def test_v97_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v37.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/regime-adaptive-policy" in main
    assert "Regime-Adaptive Decision Layer" in js
    assert "/static/v37.js" in html

def test_v97_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=97
    assert "'version':" in text
