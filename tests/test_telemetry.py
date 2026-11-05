import os
import sys
import threading
import time
import uuid

import telemetry
import utils


def wait_for_crash_logs(firebase, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        logs = firebase.read("crash_logs")
        if logs:
            return list(logs.values())
        time.sleep(0.01)
    return []


def unique(text="boom"):
    return f"{text} {uuid.uuid4().hex}"


def test_crash_reports_are_sent_by_default(firebase):
    assert telemetry.report_crash_log("ValueError", unique(), "Traceback")[0] is True
    assert len(wait_for_crash_logs(firebase)) == 1


def test_opting_out_stops_reports(firebase):
    utils.save_settings({"community_firebase_url": firebase.url, "auto_crash_reporting": False})
    assert telemetry.report_crash_log("ValueError", unique(), "Traceback") == (True, "opted_out")
    time.sleep(0.2)
    assert firebase.writes() == []


def test_opting_out_also_stops_python_crashes_caught_by_the_global_hook(firebase):
    utils.save_settings({"community_firebase_url": firebase.url, "auto_crash_reporting": False})
    saved = sys.excepthook, threading.excepthook
    stderr = sys.stderr
    try:
        telemetry.install_exception_hooks()
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
        sys.excepthook(ValueError, ValueError(unique()), None)
    finally:
        sys.stderr.close()
        sys.stderr = stderr
        sys.excepthook, threading.excepthook = saved
    time.sleep(0.2)
    assert firebase.writes() == []


def test_the_global_hook_reports_crashes_when_enabled(firebase):
    saved = sys.excepthook, threading.excepthook
    stderr = sys.stderr
    try:
        telemetry.install_exception_hooks()
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
        sys.excepthook(ValueError, ValueError(unique()), None)
    finally:
        sys.stderr.close()
        sys.stderr = stderr
        sys.excepthook, threading.excepthook = saved
    assert len(wait_for_crash_logs(firebase)) == 1


def test_windows_user_names_are_removed_from_messages_and_tracebacks(firebase):
    telemetry.report_crash_log(
        "OSError",
        unique(r"cannot open C:\Users\Some Real Name\Documents\file.txt"),
        r'File "C:\Users\Some Real Name\AppData\Local\Temp\_MEI123\bridge.py", line 1',
    )
    sent = wait_for_crash_logs(firebase)[0]
    assert "Some Real Name" not in sent["error_message"]
    assert "Some Real Name" not in sent["traceback"]
    assert r"Documents\file.txt" in sent["error_message"]


def test_other_home_folder_styles_are_cleaned():
    assert "alex" not in telemetry.sanitize_text("/home/alex/.config/app")
    assert "alex" not in telemetry.sanitize_text("/Users/alex/Library")
    assert "alex" not in telemetry.sanitize_text("C:/Users/alex/Desktop")


def test_this_machines_home_folder_is_cleaned(monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda path: r"D:\Profiles\jamie" if path == "~" else path)
    assert "jamie" not in telemetry.sanitize_text(r"D:\Profiles\jamie\AppData\x.log")


def test_secrets_in_urls_are_hidden():
    cleaned = telemetry.sanitize_text("GET https://db.example/a.json?auth=SUPERSECRET&x=1 failed")
    assert "SUPERSECRET" not in cleaned
    assert "x=1" in cleaned


def test_repeated_crashes_are_sent_once(firebase):
    message = unique()
    telemetry.report_crash_log("ValueError", message, f"Traceback {message}")
    assert telemetry.report_crash_log("ValueError", message, f"Traceback {message}") == (True, "already_reported")
    assert len(wait_for_crash_logs(firebase)) == 1


def test_a_failure_while_reporting_never_raises(firebase_down):
    assert telemetry.report_crash_log("ValueError", unique(), "Traceback")[0] is True
