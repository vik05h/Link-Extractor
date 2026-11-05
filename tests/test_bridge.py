"""The bridge is an adapter, so these tests cover what it adds: limits on what the page may do."""

import json
import os
import re
import threading
import time

import pytest

import bridge
import palette
import updater
import utils


class FakeWindow:
    def __init__(self):
        self.events = []

    def evaluate_js(self, code):
        match = re.search(r"CustomEvent\('([^']+)', \{ detail: (.*) \}\)\);$", code, re.DOTALL)
        self.events.append((match.group(1), json.loads(match.group(2))))


@pytest.fixture
def app():
    instance = bridge.AppBridge()
    instance._window = FakeWindow()
    return instance


def event_names(app):
    return [name for name, _ in app._window.events]


def wait_for_event(app, name, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for event, payload in list(app._window.events):
            if event == name:
                return payload
        time.sleep(0.01)
    raise AssertionError(f"Event {name} never arrived. Got: {event_names(app)}")


def test_pywebview_cannot_see_the_window_object(app):
    """Public attributes are reflected into JavaScript, which recursed through COM objects."""
    public = [name for name in vars(app) if not name.startswith("_")]
    assert public == []


# Settings


def test_the_page_can_save_normal_settings(app):
    app.save_settings({"concurrency": 5, "auto_crash_reporting": False})
    assert utils.load_settings()["concurrency"] == 5
    assert utils.load_settings()["auto_crash_reporting"] is False


def test_the_page_cannot_redirect_the_database(app):
    app.save_settings({"community_firebase_url": "https://evil.example"})
    assert "evil.example" not in json.dumps(utils.load_settings())


# Clipboard


def test_the_clipboard_watcher_reports_a_copied_game_link(app):
    app._check_clipboard("https://fitgirl-repacks.site/some-game/")
    assert app._window.events[0][0] == "clipboard:detected"
    assert app._window.events[0][1]["slug"] == "some-game"


def test_copying_from_the_app_does_not_trigger_its_own_watcher(app, monkeypatch):
    monkeypatch.setattr(bridge.pyperclip, "copy", lambda text: None)
    link = "https://fuckingfast.co/abc#Game.part1.rar"
    assert app.copy_to_clipboard(link)["success"] is True
    app._check_clipboard(link)
    assert app._window.events == []


def test_finished_direct_links_on_the_clipboard_are_ignored(app):
    app._check_clipboard("https://dl.fuckingfast.co/dl/abc#Game.part1.rar")
    assert app._window.events == []


def test_unrelated_clipboard_text_is_ignored(app):
    app._check_clipboard("just some text about fitgirl-repacks.site")
    assert app._window.events == []


# Requests the page can trigger


@pytest.mark.parametrize(
    "url",
    ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:9666/", "file:///C:/Windows/win.ini", "https://evil.example/x"],
)
def test_health_checks_refuse_anything_but_direct_links(app, url):
    result = app.check_health(url)
    assert result["is_alive"] is False
    assert result["status_code"] == 0


@pytest.mark.parametrize(
    "url", ["http://169.254.169.254/x.png", "http://127.0.0.1:9666/flash/add", "file:///C:/secret.png", "data:image/svg+xml;utf8,x"]
)
def test_cover_palette_never_fetches_private_addresses(url, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A private address was fetched")

    monkeypatch.setattr(palette._opener, "open", forbidden)
    result = palette.extract_game_palette(url)
    assert set(result) == {"primary", "secondary", "glow"}


def test_cover_palette_refuses_a_redirect_to_a_private_address():
    handler = palette._PublicRedirectsOnly()
    with pytest.raises(OSError):
        handler.redirect_request(None, None, 302, "Found", {}, "http://127.0.0.1:9666/flash/add")


def test_cover_palette_is_stable_without_an_image():
    assert palette.extract_game_palette("") == palette.DEFAULT_PALETTE
    first = palette.extract_game_palette("data:image/svg+xml;utf8,abc")
    assert first == palette.extract_game_palette("data:image/svg+xml;utf8,abc")


# Updates


def test_the_page_cannot_choose_what_gets_downloaded(app):
    with pytest.raises(TypeError):
        app.start_update_download("https://evil.example/malware.exe")


def test_a_release_without_an_installer_cannot_be_downloaded(app, monkeypatch):
    monkeypatch.setattr(updater, "download_update", lambda *a, **k: pytest.fail("Download must not start"))
    app._latest_release_info = {"has_binary": False, "download_url": ""}
    assert app.start_update_download()["status"] == "error"


def test_only_a_file_verified_in_this_session_can_be_installed(app, app_data_dir):
    leftover = os.path.join(str(app_data_dir), "updates", "LinkExtractor_update.exe")
    os.makedirs(os.path.dirname(leftover))
    with open(leftover, "wb") as handle:
        handle.write(b"MZ old unverified file")
    assert app.apply_update_and_restart()["status"] == "error"
    assert app.launch_downloaded_binary()["status"] == "not_found"


def test_a_rejected_download_reaches_the_user_and_can_be_retried(app, monkeypatch):
    def reject(*args, **kwargs):
        raise updater.UpdateError("The downloaded file failed its checksum, so it was not installed.")

    monkeypatch.setattr(updater, "download_update", reject)
    app._latest_release_info = {"has_binary": True}
    assert app.start_update_download()["status"] == "started"
    assert "checksum" in wait_for_event(app, "updater:error")["error"]
    assert app.apply_update_and_restart()["status"] == "error"
    assert app._update_downloading is False


# Extraction wiring


def test_unsupported_input_ends_with_an_error_event_and_allows_a_new_run(app):
    assert app.start_extraction("https://evil.example/x")["status"] == "started"
    assert "not supported" in wait_for_event(app, "pipeline:error")["message"]
    deadline = time.time() + 2
    while app._is_running and time.time() < deadline:
        time.sleep(0.01)
    assert app._is_running is False


def test_only_one_extraction_runs_at_a_time(app):
    app._is_running = True
    assert app.start_extraction("https://fuckingfast.co/a")["status"] == "error"


def test_empty_input_is_refused(app):
    assert app.start_extraction("  ")["status"] == "error"


def test_cancel_wakes_a_run_that_is_waiting_for_the_duplicate_dialog(app):
    app._is_running = True
    answers = []
    worker = threading.Thread(target=lambda: answers.append(app._ask_duplicate({"slug": "x"})))
    worker.start()
    wait_for_event(app, "pipeline:duplicate_detected")
    app.cancel_pipeline()
    worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert app._cancel_event.is_set()


# History display


def test_history_says_when_a_record_is_incomplete(app):
    app._history.add_record("Some Game", "https://fitgirl-repacks.site/some-game/", 3, 2, urls=["https://dl.fuckingfast.co/a#a.rar"])
    record = app.get_history()[0]
    assert record["is_partial"] is True
    assert record["resolved_count"] == 2
    assert record["parts_count"] == 3


def test_a_failed_export_is_not_reported_as_saved(app, monkeypatch):
    monkeypatch.setattr(bridge.integrations, "export_text", lambda *a, **k: False)
    monkeypatch.setattr(bridge.utils, "open_folder_cross_platform", lambda path: None)
    assert app.export_urls("txt", ["https://dl.fuckingfast.co/a#a.rar"], "Game")["success"] is False
