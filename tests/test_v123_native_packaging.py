from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def test_v123_desktop_workflow_runs_preflight_and_manifest():
    text=(ROOT/'.github'/'workflows'/'desktop-build.yml').read_text(encoding='utf-8')
    assert 'verify_desktop_packaging.py' in text
    assert 'write_build_manifest.py' in text
    assert 'desktop-dist/BUILD-*.json' in text
    assert 'SHA256SUMS.txt' in text

def test_v123_all_native_targets_remain():
    text=(ROOT/'.github'/'workflows'/'desktop-build.yml').read_text(encoding='utf-8')
    for token in ['windows-latest','macos-15-intel','macos-15','dist:win','dist:mac:x64','dist:mac:arm64']:
        assert token in text

def test_v123_package_and_api_versions_match():
    pkg=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
    main=(ROOT/'app'/'main.py').read_text(encoding='utf-8')
    html=(ROOT/'app'/'templates'/'index.html').read_text(encoding='utf-8')
    assert int(pkg['version'].split('.',1)[0])>=123
    assert int(main.split("version='",1)[1].split('.',1)[0])>=123
    assert '<title>BIST AI Terminal V' in html
