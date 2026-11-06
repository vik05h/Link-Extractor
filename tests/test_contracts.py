"""Checks that catch a whole class of bug: names that drift apart across the Python and web sides."""

import ast
import json
import pathlib
import re

import updater
import version

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
PYTHON_ONLY_METHODS = {"bind_window", "dispatch_event"}


def frontend_source():
    files = [path for path in FRONTEND.rglob("*") if path.suffix in {".svelte", ".ts", ".astro"}]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def bridge_methods():
    tree = ast.parse((ROOT / "bridge.py").read_text(encoding="utf-8"))
    bridge = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppBridge")
    return {node.name for node in bridge.body if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")}


def frontend_api_calls():
    source = frontend_source()
    calls = set(re.findall(r"pywebview\??\.api\??\.([a-zA-Z_][a-zA-Z0-9_]*)", source))
    calls |= set(re.findall(r"waitForBridge\('([a-zA-Z_][a-zA-Z0-9_]*)'", source))
    return calls


def python_events():
    events = set()
    for path in ROOT.glob("*.py"):
        events |= set(re.findall(r"""(?:dispatch_event|_emit)\(\s*["']([\w:]+)["']""", path.read_text(encoding="utf-8")))
    return events


def frontend_events():
    source = frontend_source()
    return set(re.findall(r"""["'`]((?:pipeline|community|updater|clipboard):[\w]+)["'`]""", source))


def test_every_call_from_the_page_has_a_python_method():
    assert frontend_api_calls() - bridge_methods() == set()


def test_python_exposes_no_method_the_page_does_not_use():
    assert bridge_methods() - frontend_api_calls() - PYTHON_ONLY_METHODS == set()


def test_every_event_python_sends_is_listened_for():
    assert python_events() - frontend_events() == set()


def test_every_event_the_page_listens_for_is_sent():
    assert frontend_events() - python_events() == set()


# One version everywhere


def test_all_version_numbers_agree():
    number = version.APP_VERSION.lstrip("v")
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == number

    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == number
    assert lock["packages"][""]["version"] == number

    version_info = (ROOT / "file_version_info.txt").read_text(encoding="utf-8")
    assert f"u'FileVersion', u'{number}.0'" in version_info
    assert f"u'ProductVersion', u'{number}.0'" in version_info
    assert f"filevers=({number.replace('.', ', ')}, 0)" in version_info
    assert f"prodvers=({number.replace('.', ', ')}, 0)" in version_info

    assert f"Release-v{number}-blue" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_frontend_has_no_hardcoded_version_numbers():
    pattern = re.compile(r"\bv\d+\.\d+")
    offenders = []
    for path in FRONTEND.rglob("*"):
        # SVG path data in the icon set is full of strings that look like v2.5.
        if path.suffix not in {".svelte", ".ts", ".astro"} or path.name == "Icon.svelte":
            continue
        markup_and_script = path.read_text(encoding="utf-8").split("<style")[0]
        offenders += [f"{path.name}: {match.group()}" for match in pattern.finditer(markup_and_script)]
    assert offenders == []


def test_python_uses_the_single_version_constant():
    assert updater.CURRENT_VERSION == version.APP_VERSION
    for path in ROOT.glob("*.py"):
        if path.name != "version.py":
            source = path.read_text(encoding="utf-8")
            assert not re.search(r"FitGirlLinkExtractor/\d", source), path.name


def test_documented_python_version_matches_pyproject():
    assert 'requires-python = ">=3.12"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "Python-3.12+" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "3.10" not in (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")


def test_docs_only_import_modules_that_exist():
    for doc in ("AGENTS.md", "CONTRIBUTING.md"):
        for command in re.findall(r'python -c "(.*?)"', (ROOT / doc).read_text(encoding="utf-8")):
            for names in re.findall(r"^\s*import ([\w, ]+)|;\s*import ([\w, ]+)", command):
                for name in ",".join(names).split(","):
                    name = name.strip()
                    if name:
                        assert (ROOT / f"{name}.py").exists(), f"{doc} imports {name}, which does not exist"
            assert "from ui" not in command
