from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v104_long_entries_require_v2_confirmation():
    helper=(ROOT/'app'/'auto_paper_v2.py').read_text(encoding='utf-8')
    engine=(ROOT/'app'/'auto_paper.py').read_text(encoding='utf-8')
    assert "V2_LONG_CONFIRMED" in helper
    assert "V2_UNIFIED_DECISION_BLOCK" in helper
    assert "confirm_fn=confirm_candidate" in engine
    assert "v2_confirmation" in engine

def test_v104_benchmark_and_excess_are_persisted():
    engine=(ROOT/'app'/'auto_paper.py').read_text(encoding='utf-8')
    ui=(ROOT/'app'/'static'/'auto-paper.js').read_text(encoding='utf-8')
    assert "'benchmark':{'ticker':'XU100'" in engine
    assert "'benchmark_return_pct'" in engine
    assert "'excess_pct'" in engine
    assert "XU100 üstü fark" in ui
    assert "UNIFIED CONFIRMATION" in ui

def test_v104_remains_paper_only():
    helper=(ROOT/'app'/'auto_paper_v2.py').read_text(encoding='utf-8')
    engine=(ROOT/'app'/'auto_paper.py').read_text(encoding='utf-8')
    assert "Never calls a broker or submits real orders" in engine
    assert "legacy-short" in helper
    assert "live" not in helper.lower() or "live" in helper.lower()

def test_v104_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=104
    assert "'version':" in text
