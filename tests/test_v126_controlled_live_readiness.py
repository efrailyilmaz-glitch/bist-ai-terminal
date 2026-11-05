from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v126_readiness_never_enables_live_execution():
    text=(ROOT/'app'/'controlled_live_readiness.py').read_text(encoding='utf-8')
    assert "'direct_live_execution_enabled':False" in text
    assert "'automatic_live_enable_supported':False" in text
    assert "contains no live-order method" in text
    assert "Verified official broker contract" in text

def test_v126_requires_forward_evidence_and_external_dependencies():
    text=(ROOT/'app'/'controlled_live_readiness.py').read_text(encoding='utf-8')
    for token in ['Minimum prospective evidence','Policy promotion evidence','Licensed realtime market feed','Research integrity']:
        assert token in text
    assert "NOT_READY_FOR_LIVE" in text
    assert "READY_FOR_MANUAL_INTEGRATION_REVIEW" in text

def test_v126_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v58.js').read_text(encoding='utf-8')
    assert "/api/controlled-live-readiness" in main
    assert 'data-view="livereadiness"' in html
    assert '/static/v58.js?v=126.0.0' in html
    assert 'Direct live' in js and 'KAPALI' in js

def test_v126_current_version_is_at_least_126():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(main.split("version='",1)[1].split('.',1)[0])
    assert current>=126
