import http.server
import json
import os
import threading
import urllib.parse

import pytest

import integrations

URLS = ["https://dl.fuckingfast.co/dl/a#Game.part1.rar", "https://dl.fuckingfast.co/dl/b"]


def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().split("\n")


def test_crawljob_lists_links_and_settings(tmp_path):
    path = str(tmp_path / "x.crawljob")
    assert integrations.export_crawljob(path, URLS, "My Game") is True
    lines = read_lines(path)
    assert lines[0] == (
        r"text=https://dl.fuckingfast.co/dl/a#Game.part1.rar\r\n"
        r"https://dl.fuckingfast.co/dl/b#My_Game.part002.rar"
    )
    assert "packageName=My Game" in lines
    assert "autoStart=false" in lines


def test_a_shared_game_title_cannot_inject_crawljob_settings(tmp_path):
    path = str(tmp_path / "x.crawljob")
    integrations.export_crawljob(path, URLS, "Game\r\ndownloadFolder=C:\\Windows\nautoStart=true")
    lines = read_lines(path)
    assert not any(line.startswith("downloadFolder=") for line in lines)
    assert [line for line in lines if line.startswith("autoStart=")] == ["autoStart=false"]


def test_text_and_json_exports(tmp_path):
    text_path = str(tmp_path / "x.txt")
    json_path = str(tmp_path / "x.json")
    assert integrations.export_text(text_path, URLS, "My Game") is True
    assert integrations.export_json(json_path, "My Game", "https://fitgirl-repacks.site/x/", URLS, "2 GB") is True
    assert read_lines(text_path)[1] == "https://dl.fuckingfast.co/dl/b#My_Game.part002.rar"
    with open(json_path, encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["total_parts"] == 2
    assert data["total_size"] == "2 GB"


def test_a_failed_export_reports_failure(tmp_path):
    assert integrations.export_text(str(tmp_path / "missing" / "x.txt"), URLS) is False


class JDHandler(http.server.BaseHTTPRequestHandler):
    received = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        JDHandler.received.append((self.path, urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))))
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


@pytest.fixture
def jdownloader():
    JDHandler.received = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), JDHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def test_push_sends_named_links_to_jdownloader(jdownloader):
    ok, _ = integrations.push_to_jdownloader(URLS, "My Game", port=jdownloader)
    assert ok is True
    path, form = JDHandler.received[0]
    assert path == "/flash/add"
    assert form["package"] == ["My Game"]
    assert form["urls"][0].split("\r\n") == [URLS[0], "https://dl.fuckingfast.co/dl/b#My_Game.part002.rar"]


def test_push_falls_back_to_the_watch_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "get_jd_folderwatch_dirs", lambda: [str(tmp_path)])
    ok, message = integrations.push_to_jdownloader(URLS, "My Game", port=9, timeout=1.0)
    assert ok is True
    assert "folderwatch" in message
    assert len(os.listdir(tmp_path)) == 1


def test_push_reports_when_jdownloader_cannot_be_found(monkeypatch):
    monkeypatch.setattr(integrations, "get_jd_folderwatch_dirs", lambda: [])
    ok, message = integrations.push_to_jdownloader(URLS, "My Game", port=9, timeout=1.0)
    assert ok is False
    assert "JDownloader" in message


def test_pushing_nothing_is_refused():
    assert integrations.push_to_jdownloader([], "My Game")[0] is False
