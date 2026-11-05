import hashlib
import http.server
import json
import os
import shutil
import subprocess
import threading
import time

import pytest

import updater

GOOD_EXE = b"MZ" + b"\x90" * 4096
GOOD_DIGEST = "sha256:" + hashlib.sha256(GOOD_EXE).hexdigest()
HTML_PAGE = b"<html>This is the release page</html>"


class Handler(http.server.BaseHTTPRequestHandler):
    release = {}

    def log_message(self, *args):
        pass

    def _send(self, body, length=None):
        self.send_response(200)
        self.send_header("Content-Length", str(len(body) if length is None else length))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_GET(self):
        if self.path == "/api":
            self._send(json.dumps(Handler.release).encode("utf-8"))
        elif self.path == "/releases/download/LinkExtractor.exe":
            self._send(GOOD_EXE)
        elif self.path == "/releases/download/page.exe":
            self._send(HTML_PAGE)
        elif self.path == "/releases/download/cut-short.exe":
            self._send(GOOD_EXE[:100], length=len(GOOD_EXE))
            self.close_connection = True
        else:
            self.send_error(404)


@pytest.fixture
def github(monkeypatch):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setattr(updater, "API_URL", f"{base}/api")
    monkeypatch.setattr(updater, "RELEASE_DOWNLOAD_PREFIX", f"{base}/releases/download/")
    yield base
    server.shutdown()
    server.server_close()


def release(base, tag="v99.0.0", assets=None):
    if assets is None:
        assets = [{
            "name": "LinkExtractor.exe",
            "browser_download_url": f"{base}/releases/download/LinkExtractor.exe",
            "size": len(GOOD_EXE),
            "digest": GOOD_DIGEST,
        }]
    Handler.release = {"tag_name": tag, "name": tag, "body": "", "assets": assets, "html_url": f"{base}/page"}


def info_for(base, **overrides):
    return {
        "download_url": f"{base}/releases/download/LinkExtractor.exe",
        "asset_size": len(GOOD_EXE),
        "asset_digest": GOOD_DIGEST,
        **overrides,
    }


# Reading release information


def test_a_newer_release_with_an_installer_is_offered(github):
    release(github)
    has_update, info, _ = updater.check_for_updates()
    assert has_update is True
    assert info["has_binary"] is True
    assert info["asset_digest"] == GOOD_DIGEST
    assert info["download_url"].endswith("LinkExtractor.exe")


def test_a_release_without_an_installer_has_nothing_to_download(github):
    release(github, assets=[])
    has_update, info, _ = updater.check_for_updates()
    assert has_update is True
    assert info["has_binary"] is False
    assert info["download_url"] == ""


def test_an_installer_hosted_elsewhere_is_not_offered(github):
    release(github, assets=[{
        "name": "LinkExtractor.exe", "browser_download_url": "https://evil.example/LinkExtractor.exe",
        "size": 1, "digest": GOOD_DIGEST,
    }])
    _, info, _ = updater.check_for_updates()
    assert info["has_binary"] is False


def test_the_same_version_is_not_an_update(github):
    release(github, tag=updater.CURRENT_VERSION)
    assert updater.check_for_updates()[0] is False


@pytest.mark.parametrize(
    "text,expected",
    [("v3.1", (3, 1, 0)), ("3.1.0", (3, 1, 0)), ("v4.0.0-beta1", (4, 0, 0)), ("V10.2.3+build", (10, 2, 3))],
)
def test_versions_compare_as_three_numbers(text, expected):
    assert updater.parse_version(text) == expected


def test_the_running_version_has_a_changelog():
    assert updater.CURRENT_VERSION in updater.VERSION_CHANGELOGS


# Downloading


def downloaded_file():
    return os.path.join(updater.utils.get_app_data_dir(), "updates", "LinkExtractor_update.exe")


def test_a_good_download_is_accepted(github):
    path = updater.download_update(info_for(github))
    assert path == downloaded_file()
    with open(path, "rb") as handle:
        assert handle.read() == GOOD_EXE


def test_a_url_outside_the_project_releases_is_refused(github):
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, download_url="https://evil.example/x.exe"))


def test_a_release_without_a_checksum_is_refused(github):
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, asset_digest=""))
    assert not os.path.exists(downloaded_file())


def test_a_web_page_saved_as_an_exe_is_refused(github):
    page = {
        "download_url": f"{github}/releases/download/page.exe",
        "asset_size": len(HTML_PAGE),
        "asset_digest": "sha256:" + hashlib.sha256(HTML_PAGE).hexdigest(),
    }
    with pytest.raises(updater.UpdateError):
        updater.download_update(page)
    assert not os.path.exists(downloaded_file())


def test_a_download_cut_short_is_refused(github):
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, download_url=f"{github}/releases/download/cut-short.exe"))
    assert not os.path.exists(downloaded_file())


def test_a_wrong_checksum_is_refused(github):
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, asset_digest="sha256:" + "0" * 64))
    assert not os.path.exists(downloaded_file())


def test_a_wrong_size_is_refused(github):
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, asset_size=5))
    assert not os.path.exists(downloaded_file())


def test_a_failed_download_leaves_an_earlier_good_one_untouched(github):
    good = updater.download_update(info_for(github))
    with pytest.raises(updater.UpdateError):
        updater.download_update(info_for(github, asset_digest="sha256:" + "0" * 64))
    with open(good, "rb") as handle:
        assert handle.read() == GOOD_EXE


def test_cancelling_a_download_keeps_nothing(github):
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(updater.UpdateCancelled):
        updater.download_update(info_for(github), cancel_event=cancel)
    assert not os.path.exists(downloaded_file())


def test_progress_is_reported(github):
    seen = []
    updater.download_update(info_for(github), progress_callback=lambda *args: seen.append(args))
    assert seen[-1][0] == len(GOOD_EXE)
    assert seen[-1][2] == 100.0


# The script that replaces the running exe, run for real on throwaway files


def small_program():
    """A real, harmless Windows program that exits immediately when launched."""
    return os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "hostname.exe")


def run_update_script(tmp_path, src, dest, backup):
    script = updater.build_update_script(src, dest, backup, pid=999999)
    bat = tmp_path / "apply_update.bat"
    bat.write_text(script, encoding="utf-8")
    subprocess.run(["cmd.exe", "/c", str(bat)], check=False, timeout=60, cwd=str(tmp_path),
                   creationflags=subprocess.CREATE_NO_WINDOW)
    return bat


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


@pytest.mark.skipif(os.name != "nt", reason="Windows update script")
def test_the_script_replaces_the_exe_and_keeps_a_backup(tmp_path):
    folder = tmp_path / "App Folder 100%"
    folder.mkdir()
    dest = folder / "LinkExtractor.exe"
    src = folder / "LinkExtractor_update.exe"
    backup = folder / "LinkExtractor_previous.exe"
    shutil.copy(small_program(), dest)
    shutil.copy(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "whoami.exe"), src)
    new_contents = read_bytes(src)
    old_contents = read_bytes(dest)

    bat = run_update_script(tmp_path, str(src), str(dest), str(backup))

    assert read_bytes(dest) == new_contents
    assert read_bytes(backup) == old_contents
    assert not src.exists()
    deadline = time.time() + 5
    while bat.exists() and time.time() < deadline:
        time.sleep(0.05)
    assert not bat.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows update script")
def test_the_script_keeps_the_old_exe_when_the_new_file_cannot_be_copied(tmp_path):
    dest = tmp_path / "LinkExtractor.exe"
    backup = tmp_path / "LinkExtractor_previous.exe"
    shutil.copy(small_program(), dest)
    old_contents = read_bytes(dest)

    run_update_script(tmp_path, str(tmp_path / "does_not_exist.exe"), str(dest), str(backup))

    assert read_bytes(dest) == old_contents


def test_the_script_starts_the_new_exe_with_a_clean_environment():
    script = updater.build_update_script("a.exe", "b.exe", "c.exe", pid=1)
    assert 'set "PYINSTALLER_RESET_ENVIRONMENT=1"' in script
