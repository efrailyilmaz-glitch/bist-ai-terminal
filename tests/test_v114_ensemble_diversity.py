from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v114_ensemble_measures_real_diversity():
    text=(ROOT/'app'/'ensemble_challenger.py').read_text(encoding='utf-8')
    for token in ['top_quartile_disagreement','effective_models','diversity_score','LOW_ENSEMBLE_DIVERSITY']:
        assert token in text
    assert "Correlated models do not count as independent diversity" in text

def test_v114_model_registry_version():
    text=(ROOT/'app'/'ensemble_challenger.py').read_text(encoding='utf-8')
    assert "'model_version':'114.0'" in text

def test_v114_api_version():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(text.split("version='",1)[1].split('.',1)[0])
    assert current>=114
    assert "'version':" in text
