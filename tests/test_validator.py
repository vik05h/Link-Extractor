import http.server
import threading
import time

import pytest

import validator


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, headers=None, body=b""):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path
        if path == "/part":
            self._send(206, {
                "Content-Range": "bytes 0-0/2147483648",
                "Content-Type": "application/octet-stream",
                "Content-Disposition": "attachment; filename=\"..\\..\\evil<name>.rar\"",
            }, b"x")
        elif path == "/plain200":
            self._send(200, {"Content-Type": "application/octet-stream"}, b"0123456789")
        elif path == "/html200":
            self._send(200, {"Content-Type": "text/html; charset=utf-8"}, b"<html>File not found</html>")
        elif path == "/gone":
            self._send(404, {}, b"")
        elif path == "/forbidden":
            self._send(403, {}, b"")
        elif path == "/ratelimited":
            self._send(429, {}, b"")
        elif path == "/servererror":
            self._send(503, {}, b"")
        elif path == "/flaky":
            with state_lock:
                state["flaky_calls"] = state.get("flaky_calls", 0) + 1
                first = state["flaky_calls"] == 1
            if first:
                self._send(503, {}, b"")
            else:
                self._send(206, {"Content-Range": "bytes 0-0/10", "Content-Type": "application/octet-stream"}, b"x")
        elif path == "/slow":
            time.sleep(0.5)
            self._send(206, {"Content-Range": "bytes 0-0/10", "Content-Type": "application/octet-stream"}, b"x")


state = {}
state_lock = threading.Lock()


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 128


@pytest.fixture
def site():
    state.clear()
    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_a_real_part_is_alive_with_its_full_size(site):
    link = validator.validate_single_url(0, f"{site}/part#Game.part1.rar")
    assert link.verdict == "alive"
    assert link.is_valid is True
    assert link.content_length_bytes == 2147483648
    assert link.content_length_str == "2.00 GB"


def test_filenames_from_headers_are_sanitized(site):
    link = validator.validate_single_url(0, f"{site}/part")
    assert "/" not in link.filename and "\\" not in link.filename and "<" not in link.filename
    assert ".." not in link.filename


def test_a_server_that_ignores_range_requests_still_counts_as_alive(site):
    assert validator.validate_single_url(0, f"{site}/plain200").verdict == "alive"


def test_an_html_error_page_with_status_200_is_dead(site):
    link = validator.validate_single_url(0, f"{site}/html200")
    assert link.verdict == "dead"
    assert link.is_valid is False


@pytest.mark.parametrize("path", ["/gone", "/forbidden"])
def test_client_errors_are_dead(site, path):
    link = validator.validate_single_url(0, f"{site}{path}")
    assert link.verdict == "dead"


@pytest.mark.parametrize("path", ["/ratelimited", "/servererror"])
def test_temporary_server_problems_are_unknown_not_dead(site, path):
    link = validator.validate_single_url(0, f"{site}{path}")
    assert link.verdict == "unknown"
    assert link.is_valid is False


def test_an_unreachable_host_is_unknown_not_dead():
    link = validator.validate_single_url(0, "http://127.0.0.1:9/x", timeout=1.0)
    assert link.verdict == "unknown"


def test_summary_counts_each_verdict_and_totals_only_live_sizes(site):
    summary = validator.validate_links([f"{site}/part", f"{site}/gone", f"{site}/servererror"], max_workers=3)
    assert (summary.valid_count, summary.dead_count, summary.unknown_count) == (1, 1, 1)
    assert summary.failed_count == 2
    assert summary.total_bytes == 2147483648
    assert summary.total_size_str == "2.00 GB"


def test_unknown_links_get_a_second_chance(site):
    summary = validator.validate_links([f"{site}/flaky"], max_workers=1)
    assert summary.valid_count == 1
    assert summary.unknown_count == 0


def test_progress_is_reported_for_every_link(site):
    seen = []
    validator.validate_links([f"{site}/part", f"{site}/part"], on_progress=lambda *args: seen.append(args))
    assert sorted(item[0] for item in seen) == [1, 2]
    assert all(item[1] == 2 for item in seen)


def test_cancel_returns_without_waiting_for_queued_links(site):
    cancel = threading.Event()
    urls = [f"{site}/slow"] * 60
    started = time.time()
    summary = validator.validate_links(urls, max_workers=3, on_progress=lambda *args: cancel.set(), cancel_event=cancel)
    assert summary.cancelled is True
    # 60 links at 0.5 s with 3 workers would take 10 s if the queue kept running.
    assert time.time() - started < 3.0


def test_a_cancelled_run_skips_the_second_chance(site):
    cancel = threading.Event()
    cancel.set()
    summary = validator.validate_links([f"{site}/servererror"], cancel_event=cancel)
    assert summary.cancelled is True
