from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v107_capacity_scale_worsens_with_size_only():
    text=(ROOT/'app'/'capacity_scale_analysis.py').read_text(encoding='utf-8')
    assert "Larger capital can only worsen or preserve execution assumptions" in text
    assert "max_clear_notional" in text
    assert "first_block_notional" in text

def test_v107_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v45.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/capacity-scale/{ticker}" in main
    assert "Capacity Scale Analysis" in js
    assert 'data-view="capacityscale"' in html

def test_v107_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='107.0.0'" in text
    assert "'version':'107.0.0'" in text
