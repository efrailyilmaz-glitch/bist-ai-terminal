from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def test_v118_sidebar_has_five_priority_groups():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert html.count('<details class="navGroup"')==5
    for label in ['KARAR & FIRSAT','TARAMA & HİSSE ANALİZİ','PORTFÖY, RİSK & PİYASA','AI, ROBOT & ARAŞTIRMA','VERİ, SİSTEM & ARAÇLAR']:
        assert label in html

def test_v118_critical_views_remain_available():
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    views=set(re.findall(r'data-view="([^"]+)"',html))
    required={'overview','unifieddecision','opportunity','screener','detail','portfoliointel','execution',
              'robotarena','researchcontrol','decisionlearning','health','systemaudit'}
    assert required.issubset(views)

def test_v118_api_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "version='118.0.0'" in main
    assert "'version':'118.0.0'" in main
