from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v95_error_cost_matrix_keeps_neutral_separate():
    text=(ROOT/'app'/'decision_error_cost.py').read_text(encoding='utf-8')
    assert "NEUTRAL_SELECTED" in text
    assert "NEUTRAL_REJECTED" in text
    assert "FP" in text and "FN" in text
    assert "neutral outcomes are excluded from binary accuracy" in text

def test_v95_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v35.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/decision-error-cost" in main
    assert "False Positive / False Negative Cost Matrix" in js
    assert "/static/v35.js?v=95.0.0" in html

def test_v95_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=95
    assert "'version':" in text
