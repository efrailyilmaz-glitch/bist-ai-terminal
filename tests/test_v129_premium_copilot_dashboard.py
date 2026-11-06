from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v129_copilot_is_server_side_and_research_only():
    text=(ROOT/'app'/'copilot.py').read_text(encoding='utf-8')
    assert "https://api.openai.com/v1/responses" in text
    assert "OPENAI_API_KEY" in text
    assert "API key is never returned to the renderer" in text
    assert "cannot place broker orders" in text
    assert "paper/sandbox" in text
    assert "broker_bridge" not in text
    assert "paper_order" not in text

def test_v129_copilot_context_is_selective():
    text=(ROOT/'app'/'copilot.py').read_text(encoding='utf-8')
    assert "need_committee" in text
    assert "need_fund" in text
    assert "need_kap" in text
    assert "ThreadPoolExecutor" in text
    assert "'scan':lambda" in text
    assert "'market':lambda" in text

def test_v129_api_routes():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "/api/copilot/status" in main
    assert "/api/copilot/config" in main
    assert "/api/copilot/chat" in main
    assert "version='129.0.0'" in main

def test_v129_premium_dashboard_and_vertical_market_rail():
    js=(ROOT/'app'/'static'/'v59.js').read_text(encoding='utf-8')
    css=(ROOT/'app'/'static'/'styles.css').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    for token in ['Takip Ettiklerim','En Çok Kazananlar','En Çok Kaybedenler','CANLI FİYAT AKIŞI','BIST AI Copilot']:
        assert token in js
    assert "marketTape129" in css
    assert "animation:marketTape129" in css
    assert '/static/v59.js?v=129.0.0' in html

def test_v129_copilot_uses_active_ticker_and_terminal_context():
    js=(ROOT/'app'/'static'/'v59.js').read_text(encoding='utf-8')
    assert "ticker:state.current" in js
    assert "view:state.view" in js
    assert "watchlist:[...state.watchlist]" in js
    assert "gainers:movers129" in js
    assert "losers:movers129" in js

def test_v129_desktop_key_config_is_local_only():
    text=(ROOT/'app'/'copilot.py').read_text(encoding='utf-8')
    assert "BIST_AI_DESKTOP" in text
    assert "LOCAL_DESKTOP_ONLY" in text
    assert "os.chmod(_SETTINGS,0o600)" in text
