"""Security checks against real app code. Related checks sit beside the code they cover:
link trust in test_links.py, moderation in test_issues.py, what the page may trigger in
test_bridge.py, update safety in test_updater.py, SQL handling in test_history.py.
"""

import json
import os
import time

import pytest

import bridge
import community
import game_records
import links
import scraper
import telemetry
import validator


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge.utils, "get_export_dir", lambda: str(tmp_path / "exports"))
    monkeypatch.setattr(bridge.utils, "open_folder_cross_platform", lambda path: None)
    return bridge.AppBridge()


@pytest.mark.parametrize("title", ["../../Windows/System32/evil", "..\\..\\evil", "CON:evil", "a/b\\c"])
@pytest.mark.parametrize("format_type", ["txt", "json", "crawljob"])
def test_game_titles_cannot_escape_the_export_folder(app, tmp_path, title, format_type):
    result = app.export_urls(format_type, ["https://dl.fuckingfast.co/a#a.rar"], title)
    assert result["success"] is True
    exports = os.path.realpath(tmp_path / "exports")
    assert os.path.realpath(result["file_path"]).startswith(exports + os.sep)
    assert os.path.dirname(os.path.realpath(result["file_path"])) == exports


def test_slugs_cannot_change_the_database_path(firebase):
    community.get_game_urls("../../reports")
    assert firebase.requests[-1]["path"] == "/games_urls/reports.json"


def test_a_slug_from_a_shared_record_is_cleaned_before_use(firebase):
    assert game_records.generate_game_slug("", "../../secret/[x]") == "secret"


@pytest.mark.parametrize(
    "call",
    [
        lambda text: links.extract_urls(text),
        lambda text: scraper.detect_url_type(text),
        lambda text: scraper.extract_links_from_pastebin_html(text),
        lambda text: game_records.normalize_title(text),
        lambda text: game_records.find_match(text, []),
        lambda text: telemetry.sanitize_text(text),
        lambda text: validator._filename_from_header(text),
    ],
)
@pytest.mark.parametrize(
    "text",
    [
        " " * 200_000,
        "-" * 200_000,
        "v1" * 100_000,
        "https://" * 50_000,
        "https://dl.fuckingfast.co/dl/" + "a" * 200_000,
        "C:\\Users\\" * 50_000,
        "filename=" * 50_000,
    ],
)
def test_huge_hostile_input_cannot_stall_the_app(call, text):
    started = time.perf_counter()
    call(text)
    assert time.perf_counter() - started < 2.0


def test_the_app_does_not_ship_a_way_to_become_admin_locally():
    import issues

    assert not hasattr(issues, "get_admin_key_path")
    assert not hasattr(issues, "ensure_admin_key_file")


def test_secrets_do_not_appear_in_crash_reports():
    message = "GET https://x.firebasedatabase.app/reports.json?auth=SECRETKEY123 failed"
    assert "SECRETKEY123" not in telemetry.sanitize_text(message)


def test_settings_written_to_disk_never_contain_an_admin_key(app, app_data_dir):
    app.save_settings({"admin_key": "SECRETKEY123", "concurrency": 2})
    with open(os.path.join(str(app_data_dir), "settings.json"), encoding="utf-8") as handle:
        assert "SECRETKEY123" not in json.dumps(json.load(handle))
