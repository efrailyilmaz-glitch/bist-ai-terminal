from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v128_frontend_scan_and_request_reuse():
    js=(ROOT/'app'/'static'/'app.js').read_text(encoding='utf-8')
    assert "const batch=100" in js
    assert "const workers=Math.min(3" in js
    assert "API_CACHE=new Map()" in js
    assert "API_FLIGHTS=new Map()" in js
    assert "apiTTL(url)" in js
    assert "autoScanViews=new Set(['overview','all','short','long','setups','anomaly','portfolio','screener','community'])" in js
    assert "restored?8000:500" in js

def test_v128_backend_provider_concurrency_is_faster_but_bounded():
    md=(ROOT/'app'/'market_data.py').read_text(encoding='utf-8')
    assert "threading.BoundedSemaphore(3)" in md
    assert "ThreadPoolExecutor(max_workers=min(3,len(chunks)))" in md
    assert "provider_download_concurrency']=3" in md

def test_v128_active_ticker_is_global_and_persistent():
    js=(ROOT/'app'/'static'/'app.js').read_text(encoding='utf-8')
    route=(ROOT/'app'/'static'/'v19.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "bist-ai-current-ticker" in js
    assert "setActiveTicker" in js
    assert 'id="activeTickerSearch"' in html
    assert 'id="activeTickerOptions"' in html
    assert "localStorage.setItem('bist-ai-current-ticker',state.current)" in route

def test_v128_heavy_workers_are_deferred():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "def _start_background_deferred()" in main
    assert "time.sleep(20)" in main
    assert "time.sleep(10)" in main
    assert "auto_paper.start_worker(); robot_arena.start_worker(); xs_scheduler_start_worker()" in main

def test_v128_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(main.split("version='",1)[1].split('.',1)[0])
    assert current>=128
