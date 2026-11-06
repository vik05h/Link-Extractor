import importlib.util
import json
import pathlib
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ["version.py", "README.md", "file_version_info.txt", "frontend/package.json", "frontend/package-lock.json"]


def load_script():
    spec = importlib.util.spec_from_file_location("set_version", ROOT / "scripts" / "set_version.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo_copy(tmp_path):
    for name in FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, target)
    return tmp_path


def test_every_file_gets_the_new_version(repo_copy):
    load_script().set_version(repo_copy, "4.0.0")

    assert 'APP_VERSION = "v4.0.0"' in (repo_copy / "version.py").read_text(encoding="utf-8")
    assert json.loads((repo_copy / "frontend/package.json").read_text(encoding="utf-8"))["version"] == "4.0.0"
    lock = json.loads((repo_copy / "frontend/package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == "4.0.0"
    assert lock["packages"][""]["version"] == "4.0.0"
    info = (repo_copy / "file_version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(4, 0, 0, 0)" in info
    assert "prodvers=(4, 0, 0, 0)" in info
    assert "u'FileVersion', u'4.0.0.0'" in info
    assert "u'ProductVersion', u'4.0.0.0'" in info
    assert "Release-v4.0.0-blue" in (repo_copy / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["4.0", "v4.0.0", "four", "4.0.0-beta"])
def test_malformed_versions_are_refused(repo_copy, bad):
    with pytest.raises(SystemExit):
        load_script().set_version(repo_copy, bad)
