from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v121_scan_batches_are_larger_but_concurrency_bounded():
    md=(ROOT/'app'/'market_data.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'app.js').read_text(encoding='utf-8')
    assert "missing[i:i+50]" in md
    assert "ThreadPoolExecutor(max_workers=min(2,len(chunks)))" in md
    assert "threading.BoundedSemaphore(2)" in md
    assert "const batch=40" in js

def test_v121_performance_telemetry():
    md=(ROOT/'app'/'market_data.py').read_text(encoding='utf-8')
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "performance_snapshot" in md
    assert "score_cache_hit_pct" in md
    assert "provider_batches" in md
    assert "/api/performance" in main

def test_v121_api_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='121.0.0'" in main
    assert "'version':'121.0.0'" in main
