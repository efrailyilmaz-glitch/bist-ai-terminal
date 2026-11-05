from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v108_critical_data_failures_block_decisions():
    text=(ROOT/'app'/'data_provider_trust_v2.py').read_text(encoding='utf-8')
    assert "DATA_BLOCK" in text
    assert "decision_allowed" in text
    assert "Critical market/universe integrity failures block" in text

def test_v108_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v46.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/data-trust-v2" in main
    assert "Data Quality & Provider Trust 2.0" in js
    assert 'data-view="datatrust2"' in html

def test_v108_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='108.0.0'" in text
    assert "'version':'108.0.0'" in text
