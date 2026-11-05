from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v96_confidence_calibration_metrics():
    text=(ROOT/'app'/'confidence_calibration.py').read_text(encoding='utf-8')
    for token in ['brier_score','expected_calibration_error','OVERCONFIDENT','UNDERCONFIDENT','CALIBRATED']:
        assert token in text
    assert "Committee score is not automatically rescaled" in text

def test_v96_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v36.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/confidence-calibration" in main
    assert "Confidence Calibration" in js
    assert "/static/v36.js" in html

def test_v96_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=96
    assert "'version':" in text
