from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v111_ranking_is_cross_sectional_and_coverage_gated():
    text=(ROOT/'app'/'cross_sectional_ranking_v2.py').read_text(encoding='utf-8')
    assert "audit_current_snapshot" in text
    assert "DATA_BLOCK" in text
    assert "relative_rank_score" in text
    assert "universe_percentile" in text

def test_v111_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v49.js').read_text(encoding='utf-8')
    assert "/api/cross-sectional-ranking-v2" in main
    assert "Cross-Sectional Ranking 2.0" in js

def test_v111_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='111.0.0'" in text
    assert "'version':'111.0.0'" in text
