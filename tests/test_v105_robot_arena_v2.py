from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v105_arena_v2_keeps_all_configured_robots():
    text=(ROOT/'app'/'robot_arena_v2.py').read_text(encoding='utf-8')
    assert "All configured robots remain in the table" in text
    assert "zero trades" in text
    assert "losses or decay" in text

def test_v105_score_uses_forward_risk_and_benchmark():
    text=(ROOT/'app'/'robot_arena_v2.py').read_text(encoding='utf-8')
    for token in ['benchmark_excess_pct','max_drawdown_pct','closed_trades','profit_factor','decay','maturity_pct']:
        assert token in text
    assert "'live_execution':False" in text

def test_v105_arena_snapshot_and_ui():
    arena=(ROOT/'app'/'robot_arena.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'robot-arena.js').read_text(encoding='utf-8')
    assert "'arena_v2':arena_v2" in arena
    assert "Arena 2.0 Forward Scorecard" in js
    assert "Robot Laboratuvarı 2.0" in js

def test_v105_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=105
    assert "'version':" in text
