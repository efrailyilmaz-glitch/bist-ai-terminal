from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v115_new_features_are_not_production_eligible():
    text=(ROOT/'app'/'feature_governance_v3.py').read_text(encoding='utf-8')
    assert "'production_eligible':False" in text
    assert "UNREGISTERED_RESEARCH_ONLY" in text
    assert "FORWARD_EVIDENCE_BUILDING" in text
    assert "LEAKAGE_RISK_BLOCK" in text

def test_v115_leakage_is_explicit_metadata_not_name_guess():
    text=(ROOT/'app'/'feature_governance_v3.py').read_text(encoding='utf-8')
    assert "future_derived" in text
    assert "point_in_time" in text
    assert "Explicit lineage metadata" in text

def test_v115_protected_features_remain_immutable():
    text=(ROOT/'app'/'feature_governance_v3.py').read_text(encoding='utf-8')
    assert "is_protected" in text
    assert "state='PROTECTED'" in text
    assert "Safety/integrity feature is immutable" in text

def test_v115_api_and_ui():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    js=(ROOT/'app'/'static'/'v52.js').read_text(encoding='utf-8')
    assert "/api/feature-governance-v3" in main
    assert "/api/feature-governance-v3/register" in main
    assert "Feature Governance 3.0" in js

def test_v115_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='115.0.0'" in text
    assert "'version':'115.0.0'" in text
