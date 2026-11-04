from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_v81_research_control_navigation_and_script():
    html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'data-view="researchcontrol"' in html
    assert 'Araştırma Kontrol Merkezi' in html
    assert '/static/v30.js?v=81.0.0' in html

def test_v81_research_control_uses_paper_only_endpoints():
    js = (ROOT / "app" / "static" / "v30.js").read_text(encoding="utf-8")
    assert "/api/research-integrity" in js
    assert "/api/autonomous-research/status" in js
    assert "/api/autonomous-research/run" in js
    assert "auto_create_paper:true" in js
    assert "broker" in js.lower()
    assert "canlı işlem yetkisi vermez" in js

def test_v81_api_version():
    text = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "version='81.0.0'" in text
    assert "'version':'81.0.0'" in text
