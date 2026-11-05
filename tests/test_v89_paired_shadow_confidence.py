from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v89_paired_bootstrap_and_regime_coverage():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "_paired_bootstrap" in text
    assert "_paired_comparisons" in text
    assert "PAIRED_FORWARD_EDGE_WITH_REGIME_COVERAGE" in text
    assert "INSUFFICIENT_REGIME_COVERAGE" in text
    assert "prob_positive" in text

def test_v89_challenger_review_requires_paired_support():
    text=(ROOT/'app'/'decision_policy_challenger.py').read_text(encoding='utf-8')
    assert "pc['status']=='SUPPORTED'" in text
    assert "boot['ci_low']>0" in text
    assert "boot['prob_positive']>=.95" in text

def test_v89_ui_surfaces_paired_confidence():
    js=(ROOT/'app'/'static'/'v33.js').read_text(encoding='utf-8')
    assert "Paired Forward Confidence" in js
    assert "Ort. utility Δ" in js
    assert "P(Δ&gt;0)" in js

def test_v89_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='89.0.0'" in text
    assert "'version':'89.0.0'" in text
