from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_v120_full_audit_module_exists_and_is_read_only():
    text=(ROOT/'app'/'full_system_audit.py').read_text(encoding='utf-8')
    assert "_python_syntax" in text
    assert "_static_wiring" in text
    assert "_navigation" in text
    assert "_routes" in text
    assert "_modules" in text
    assert "Read-only integrity audit" in text

def test_v120_system_audit_wires_full_audit_and_fixes_stale_backend_label():
    text=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    assert "/api/full-system-audit" in text
    assert "V120 Full Source/Wiring Audit" in text
    assert "BIST AI backend 120.0" in text
    assert "BIST AI backend 80.0" not in text

def test_v120_api_version():
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    current=int(main.split("version='",1)[1].split('.',1)[0])
    assert current>=120
    assert "'version':" in main
