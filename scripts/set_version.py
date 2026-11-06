"""Set the app version in every file that records it.

    python scripts/set_version.py 4.0.0

Add a matching entry to VERSION_CHANGELOGS in updater.py as well. The test suite
fails until every file agrees and the new version has a changelog.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _replace(path: pathlib.Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text)
    if count == 0:
        raise SystemExit(f"Could not find the version in {path}")
    path.write_text(updated, encoding="utf-8", newline="\n")


def _update_json(path: pathlib.Path, number: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = number
    if "packages" in data:
        data["packages"][""]["version"] = number
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def set_version(root: pathlib.Path, number: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", number):
        raise SystemExit(f"Version must look like 4.0.0, not {number!r}")
    major, minor, patch = number.split(".")

    _replace(root / "version.py", r'APP_VERSION = "v[^"]+"', f'APP_VERSION = "v{number}"')
    _update_json(root / "frontend" / "package.json", number)
    _update_json(root / "frontend" / "package-lock.json", number)

    version_info = root / "file_version_info.txt"
    _replace(version_info, r"filevers=\([\d, ]+\)", f"filevers=({major}, {minor}, {patch}, 0)")
    _replace(version_info, r"prodvers=\([\d, ]+\)", f"prodvers=({major}, {minor}, {patch}, 0)")
    _replace(version_info, r"u'FileVersion', u'[\d.]+'", f"u'FileVersion', u'{number}.0'")
    _replace(version_info, r"u'ProductVersion', u'[\d.]+'", f"u'ProductVersion', u'{number}.0'")

    _replace(root / "README.md", r"Release-v[\d.]+-blue", f"Release-v{number}-blue")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    set_version(ROOT, sys.argv[1].lstrip("vV"))
    print(f"Version set to v{sys.argv[1].lstrip('vV')}. Remember the changelog entry in updater.py.")
