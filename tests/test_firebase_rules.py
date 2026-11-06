"""End-to-end tests of firebase/database.rules.json on the official Firebase emulator.

Skipped unless the emulator is running. To run them:

    npx firebase-tools --config firebase/firebase.json emulators:exec --only database \
        --project demo-link-extractor "python -m pytest tests/test_firebase_rules.py"

They replay what the current app really sends, what older released versions send, and
what an attacker would send. Run them after any change to the rules, because the same
rules protect every installed copy of the app.
"""

import json
import os
import pathlib
import time
import urllib.error
import urllib.request

import pytest

import community
import issues
import telemetry

EMULATOR = os.environ.get("FIREBASE_DATABASE_EMULATOR_HOST")
pytestmark = pytest.mark.skipif(not EMULATOR, reason="Needs the Firebase database emulator")

NAMESPACE = "demo-link-extractor"
RULES_FILE = pathlib.Path(__file__).resolve().parents[1] / "firebase" / "database.rules.json"
NOW = "2026-11-05T00:00:00Z"
GOOD_LINK = "https://dl.fuckingfast.co/dl/abc#Game.part001.rar"
EVIL_LINK = "https://evil.example/setup.exe#Game.part001.rar"
SCREENSHOT = "data:image/jpeg;base64,AAAA"


def call(method, path, body=None, *, admin=False, raw=None):
    url = f"http://{EMULATOR}/{path}.json?ns={NAMESPACE}"
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    request = urllib.request.Request(url, data=data, method=method)
    if admin:
        request.add_header("Authorization", "Bearer owner")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def read(path):
    request = urllib.request.Request(f"http://{EMULATOR}/{path}.json?ns={NAMESPACE}")
    request.add_header("Authorization", "Bearer owner")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def game_meta(**overrides):
    meta = {
        "title": "A Game",
        "source_url": "https://fitgirl-repacks.site/a-game/",
        "image_url": "https://example.com/a.jpg",
        "timestamp_utc": NOW,
        "total_parts": 1,
        "resolved_count": 1,
        "total_size_str": "1 GB",
        "total_size_bytes": 1073741824,
        "used_count": 3,
        "uploader": "Anonymous",
        "app_version": "v3.8.1",
    }
    meta.update(overrides)
    return meta


def old_report(**overrides):
    report = {
        "id": "rep_1", "subject": "Crash", "category": "Bug Report", "description": "It crashes",
        "screenshot_data": "", "status": "open", "affected_users_count": 1, "admin_remark": "",
        "created_at": NOW, "app_version": "v3.8.1", "os_info": "win32",
        "telemetry": {"app_version": "v3.8.1", "platform": "win32", "theme": ""},
    }
    report.update(overrides)
    return report


def old_comment(**overrides):
    comment = {
        "id": "c_1", "author_type": "gamer", "author_name": "Gamer", "text": "Same here",
        "screenshot_data": "", "created_at": NOW, "app_version": "v3.8.1",
    }
    comment.update(overrides)
    return comment


@pytest.fixture(autouse=True)
def fresh_database():
    assert call("PUT", ".settings/rules", raw=RULES_FILE.read_bytes(), admin=True) == 200
    assert call("PUT", "", {}, admin=True) == 200
    yield


def seed_game():
    assert call("PUT", "games_meta/a-game", game_meta(), admin=True) == 200
    assert call("PUT", "games_urls/a-game", {"urls": [GOOD_LINK], "updated_at": NOW}, admin=True) == 200


def seed_report():
    assert call("PUT", "reports/rep_1", old_report(), admin=True) == 200


# Reading


@pytest.mark.parametrize("path", ["games_meta", "games_urls", "reports", "report_screenshots"])
def test_public_data_can_be_read(path):
    assert call("GET", path) == 200


@pytest.mark.parametrize("path", ["crash_logs", "anything_else", ""])
def test_private_data_cannot_be_read(path):
    assert call("GET", path) == 401


# What the current app sends


def replay(firebase):
    """Send the requests the real client code made to the local stand-in, in order."""
    statuses = []
    for sent in firebase.requests:
        if sent["method"] != "GET":
            statuses.append(call(sent["method"], sent["path"].lstrip("/").removesuffix(".json"), sent["body"]))
    return statuses


def test_the_current_app_can_publish_a_game(firebase):
    community.upload_game_record(
        slug="a-game", title="A Game", source_url="https://fitgirl-repacks.site/a-game/",
        image_url="https://example.com/a.jpg", urls=[GOOD_LINK], total_parts=1, total_size_str="1 GB",
    )
    assert replay(firebase) == [200, 200]


def test_the_current_app_can_count_a_grab(firebase):
    seed_game()
    firebase.seed("games_meta/a-game", {"title": "A Game", "used_count": 3})
    community.increment_game_usage("a-game")
    assert replay(firebase) == [200]
    assert read("games_meta/a-game/used_count") == 4


def test_the_current_app_can_send_a_report_with_a_screenshot(firebase):
    result = issues.submit_user_report(
        subject="Crash", category="Bug Report", description="It crashes", screenshot_data=SCREENSHOT,
        telemetry={"app_version": "v3.8.1", "platform": "win32", "theme": ""}, force_create=True,
    )
    assert result.outcome == "sent"
    assert replay(firebase) == [200, 200]


def test_the_current_app_can_comment_and_vote(firebase):
    seed_report()
    firebase.seed("reports/rep_1", {"subject": "Crash", "affected_users_count": 1})
    issues.add_comment("rep_1", "Same here", author_type="gamer", screenshot_data=SCREENSHOT)
    issues.increment_report_affected("rep_1")
    assert replay(firebase) == [200, 200, 200]
    assert read("reports/rep_1/affected_users_count") == 2


def test_the_current_app_can_send_a_crash_report(firebase):
    telemetry.report_crash_log("ValueError", "rules test", "Traceback", extra={"client": "WebView2_Svelte"})
    for _ in range(100):
        if firebase.requests:
            break
        time.sleep(0.02)
    assert replay(firebase) == [200]


def test_the_current_app_can_update_presence_and_clear_old_sessions():
    seed_game()
    assert call("PUT", "games_meta/grand-theft-auto-v", game_meta(title="GTA V"), admin=True) == 200
    assert call("PUT", "games_meta/grand-theft-auto-v/presence/s1", {"t": NOW, "v": "v3.8.1"}) == 200
    assert call("DELETE", "games_meta/grand-theft-auto-v/presence/s1") == 200


# What older released versions send, so installed copies keep working


def test_old_versions_can_publish_and_update_the_count():
    assert call("PUT", "games_meta/a-game", game_meta()) == 200
    assert call("PUT", "games_urls/a-game", {"urls": [GOOD_LINK], "updated_at": NOW}) == 200
    assert call("PATCH", "games_meta/a-game", {"used_count": 4}) == 200


def test_old_versions_can_republish_over_an_existing_game():
    seed_game()
    assert call("PUT", "games_meta/a-game", game_meta(timestamp_utc="2026-11-06T00:00:00Z")) == 200


def test_old_versions_can_send_reports_comments_and_votes():
    assert call("PUT", "reports/rep_1", old_report()) == 200
    assert call("PUT", "reports/rep_1/comments/c_1", old_comment()) == 200
    assert call("PATCH", "reports/rep_1", {"affected_users_count": 2}) == 200


def test_old_versions_can_send_crash_reports():
    crash = {
        "error_type": "ValueError", "error_message": "boom", "traceback": "Traceback", "context": "runtime",
        "app_version": "v3.8.1", "platform": "win32", "timestamp_utc": NOW,
    }
    assert call("PUT", "crash_logs/crash_1", crash) == 200


def test_old_versions_trying_to_delete_games_are_harmlessly_refused():
    seed_game()
    assert call("DELETE", "games_meta/a-game") == 401
    assert call("DELETE", "games_urls/a-game") == 401


# What an attacker would try


def test_links_cannot_be_replaced_with_foreign_ones():
    seed_game()
    assert call("PUT", "games_urls/a-game", {"urls": [EVIL_LINK], "updated_at": NOW}) != 200
    assert read("games_urls/a-game")["urls"] == [GOOD_LINK]


def test_a_foreign_link_cannot_be_added_to_a_list():
    seed_game()
    assert call("PUT", "games_urls/a-game/urls/1", EVIL_LINK) != 200


def test_a_substring_of_the_real_host_does_not_pass():
    assert call("PUT", "games_urls/x", {"urls": ["https://evil.example/dl.fuckingfast.co/x"]}) != 200
    assert call("PUT", "games_urls/x", {"urls": ["https://dl.fuckingfast.co.evil.example/x"]}) != 200


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_url", "javascript:alert(1)"),
        ("source_url", "https://evil.example/"),
        ("image_url", "javascript:alert(1)"),
        ("title", ""),
        ("total_parts", "many"),
        ("surprise_field", "x"),
    ],
)
def test_bad_game_fields_are_refused(field, value):
    assert call("PUT", "games_meta/a-game", game_meta(**{field: value})) != 200


def test_empty_records_cannot_be_created_through_the_usage_counter():
    assert call("PATCH", "games_meta/ghost", {"used_count": 1}) != 200
    assert call("PUT", "games_meta/ghost/used_count", 1) != 200


def test_a_game_cannot_be_stripped_of_its_title():
    seed_game()
    assert call("DELETE", "games_meta/a-game/title") != 200
    assert read("games_meta/a-game/title") == "A Game"


def test_status_and_remark_cannot_be_changed_without_the_key():
    seed_report()
    assert call("PATCH", "reports/rep_1", {"status": "fixed"}) == 401
    assert call("PATCH", "reports/rep_1", {"admin_remark": "Hacked"}) == 401
    assert call("PUT", "reports/rep_1/status", "fixed") == 401


def test_reports_cannot_be_deleted_or_overwritten_without_the_key():
    seed_report()
    assert call("DELETE", "reports/rep_1") == 401
    assert call("PUT", "reports/rep_1", old_report(subject="Hacked")) == 401


def test_a_new_report_cannot_claim_to_be_fixed():
    assert call("PUT", "reports/rep_2", old_report(id="rep_2", status="fixed")) != 200
    assert call("PUT", "reports/rep_2", old_report(id="rep_2", admin_remark="Official")) != 200


def test_nobody_can_post_as_admin_without_the_key():
    seed_report()
    assert call("PUT", "reports/rep_1/comments/c_1", old_comment(author_type="admin")) != 200


def test_comments_cannot_be_edited_or_deleted_without_the_key():
    seed_report()
    assert call("PUT", "reports/rep_1/comments/c_1", old_comment()) == 200
    assert call("PUT", "reports/rep_1/comments/c_1", old_comment(text="Changed")) == 401
    assert call("DELETE", "reports/rep_1/comments/c_1") == 401


def test_votes_cannot_go_down():
    seed_report()
    assert call("PUT", "reports/rep_1/affected_users_count", 0) != 200


def test_screenshots_must_be_images_and_cannot_be_replaced():
    assert call("PUT", "report_screenshots/rep_1/report", "data:text/html;base64,AAAA") != 200
    assert call("PUT", "report_screenshots/rep_1/report", SCREENSHOT) == 200
    assert call("PUT", "report_screenshots/rep_1/report", SCREENSHOT + "BBBB") == 401
    assert call("DELETE", "report_screenshots/rep_1/report") == 401


def test_crash_logs_cannot_be_read_changed_or_deleted():
    crash = {"error_type": "ValueError", "timestamp_utc": NOW}
    assert call("PUT", "crash_logs/crash_1", crash) == 200
    assert call("GET", "crash_logs/crash_1") == 401
    assert call("PUT", "crash_logs/crash_1", {**crash, "error_type": "Changed"}) == 401
    assert call("DELETE", "crash_logs/crash_1") == 401


def test_the_rest_of_the_database_is_closed():
    assert call("PUT", "anything_else", {"a": 1}) == 401


# The admin key still works


def test_the_admin_key_can_moderate():
    seed_report()
    assert call("PATCH", "reports/rep_1", {"status": "fixed", "admin_remark": "Done", "updated_at": NOW}, admin=True) == 200
    assert call("PUT", "reports/rep_1/comments/c_9", old_comment(id="c_9", author_type="admin"), admin=True) == 200
    assert call("DELETE", "reports/rep_1", admin=True) == 200
