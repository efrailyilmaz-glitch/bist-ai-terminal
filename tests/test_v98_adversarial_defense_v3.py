from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v98_adversarial_v3_scenarios():
    text=(ROOT/'app'/'adversarial_v3.py').read_text(encoding='utf-8')
    for token in ['close_spike_reversal','volume_inflation_no_progress','breakout_retest_failure','gap_chase_fade_cluster','liquidity_vacuum_squeeze']:
        assert token in text
    assert "cannot prove manipulation" in text

def test_v98_joint_guard_and_trap_detection():
    text=(ROOT/'app'/'adversarial_v3.py').read_text(encoding='utf-8')
    assert "detected_any" in text
    assert "detected_both" in text
    assert "assess_signal_guard" in text
    assert "assess_traps" in text

def test_v98_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v38.js').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert "/api/adversarial-v3/{ticker}" in main
    assert "Adversarial Defense 3.0" in js
    assert 'data-view="adversarial3"' in html

def test_v98_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=98
    assert "'version':" in text
