from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v124_adapter_catalog_is_explicit_and_non_synthetic():
    text=(ROOT/'app'/'live_data_adapters.py').read_text(encoding='utf-8')
    for token in ['yahoo_delayed','matriks','is_yatirim','info_yatirim']:
        assert token in text
    assert "synthetic':False" in text
    assert "Provider slot only" in text
    assert "No proprietary endpoint or protocol is guessed" in text

def test_v124_depth_requires_real_connected_feed():
    text=(ROOT/'app'/'live_data_adapters.py').read_text(encoding='utf-8')
    assert "LICENSED_DEPTH_FEED_NOT_CONNECTED" in text
    assert "PROVIDER_DOES_NOT_SUPPORT_DEPTH" in text
    assert "status')!='CONNECTED'" in text

def test_v124_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v56.js').read_text(encoding='utf-8')
    assert "/api/live-data-adapters" in main
    assert "/api/live-data/quote/{ticker}" in main
    assert "/api/live-data/depth/{ticker}" in main
    assert 'data-view="liveadapters"' in html
    assert '/static/v56.js' in html
    assert 'Depth sentezi' in js

def test_v124_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='124.0.0'" in main
    assert "'version':'124.0.0'" in main
