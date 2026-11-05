from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v119_command_center_is_exposed():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v55.js').read_text(encoding='utf-8')
    assert '/static/v55.js?v=119.0.0' in html
    assert 'Premium Command Center' in js
    assert 'BUGÜNÜN ARAŞTIRMA DURUŞU' in js
    assert '/api/research-integrity-master' in js
    assert '/api/background/status' in js
    assert 'Canlı işlem' in js and 'KAPALI' in js

def test_v119_api_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(main.split("version='",1)[1].split('.',1)[0])
    assert current>=119
    assert "'version':" in main
