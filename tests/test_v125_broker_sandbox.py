from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v125_sandbox_has_no_live_submit_path():
    text=(ROOT/'app'/'broker_sandbox.py').read_text(encoding='utf-8')
    assert "SANDBOX_ONLY" in text
    assert "direct_live_execution_enabled':False" in text
    assert "No live-order submission method exists here" in text
    assert "paper_order" in text

def test_v125_idempotency_reserves_before_paper_fill():
    text=(ROOT/'app'/'broker_sandbox.py').read_text(encoding='utf-8')
    reserve=text.index("'state':'RESERVED'")
    execute=text.index("result=paper_order(body)")
    assert reserve < execute
    assert "DUPLICATE_PENDING" in text
    assert "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT" in text

def test_v125_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v57.js').read_text(encoding='utf-8')
    assert "/api/broker-sandbox/status" in main
    assert "/api/broker-sandbox/preview" in main
    assert "/api/broker-sandbox/submit" in main
    assert "x_idempotency_key" in main
    assert 'data-view="brokersandbox"' in html
    assert '/static/v57.js' in html
    assert 'Live execution' in js and 'KAPALI' in js

def test_v125_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='125.0.0'" in main
    assert "'version':'125.0.0'" in main
