from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v113_model_zoo_has_license_gates():
    text=(ROOT/'app'/'model_zoo_v2.py').read_text(encoding='utf-8')
    for token in ['qlib','finrl_x','pybroker','chronos2','timesfm3','moirai2']:
        assert token in text
    assert "NON_COMMERCIAL_RESEARCH_ONLY" in text
    assert "No automatic package/model download" in text

def test_v113_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v51.js').read_text(encoding='utf-8')
    assert "/api/model-zoo-v2" in main
    assert "External Model Zoo 2.0" in js

def test_v113_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=113
    assert "'version':" in text
