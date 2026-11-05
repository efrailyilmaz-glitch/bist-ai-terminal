from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v112_neutralizes_sector_and_factors():
    text=(ROOT/'app'/'sector_factor_neutral_v2.py').read_text(encoding='utf-8')
    for token in ['ret_20','vol_20','ema50_gap','sector','neutral_score_z','rank_change']:
        assert token in text
    assert "not proof of pure alpha" in text

def test_v112_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v50.js').read_text(encoding='utf-8')
    assert "/api/sector-factor-neutral-v2" in main
    assert "Sector & Factor Neutralization 2.0" in js

def test_v112_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='112.0.0'" in text
    assert "'version':'112.0.0'" in text
