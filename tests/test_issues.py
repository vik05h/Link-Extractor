import json
import os

import pytest

import issues

SCREENSHOT = "data:image/jpeg;base64," + "A" * 400


def submit(subject="App crashes on start", **kwargs):
    return issues.submit_user_report(
        subject=subject, category="Bug Report", description="It crashes.", force_create=True, **kwargs
    )


def local_reports(app_data_dir):
    path = os.path.join(str(app_data_dir), "community_reports.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# Reports reach the server, and the app says so honestly


def test_a_report_is_sent_to_the_server(firebase):
    result = submit()
    assert result.outcome == "sent"
    stored = firebase.read(f"reports/{result.report_id}")
    assert stored["subject"] == "App crashes on start"
    assert stored["status"] == "open"


def test_a_report_that_cannot_be_sent_is_kept_and_not_called_a_success(firebase):
    firebase.deny = lambda method, path, auth: method != "GET"
    result = submit()
    assert result.outcome == "queued"
    assert "not" in result.message.lower()
    assert firebase.read(f"reports/{result.report_id}") is None


def test_a_queued_report_is_delivered_once_the_server_accepts_it(firebase, app_data_dir):
    firebase.deny = lambda method, path, auth: method != "GET"
    report_id = submit().report_id

    firebase.deny = None
    ok, reports, _ = issues.fetch_all_reports()
    assert ok is True
    assert firebase.read(f"reports/{report_id}")["subject"] == "App crashes on start"
    assert local_reports(app_data_dir) == {}
    assert [r["id"] for r in reports] == [report_id]
    assert not reports[0].get("pending_upload")


def test_a_queued_report_stays_visible_and_marked_while_undelivered(firebase):
    firebase.deny = lambda method, path, auth: method != "GET"
    report_id = submit().report_id
    _, reports, _ = issues.fetch_all_reports()
    assert [(r["id"], r["pending_upload"]) for r in reports] == [(report_id, True)]


def test_unreachable_server_is_reported_and_local_reports_still_show(firebase_down):
    submit()
    ok, reports, message = issues.fetch_all_reports()
    assert ok is False
    assert len(reports) == 1
    assert message


# The reporter sees the maintainer's reply


def test_the_servers_status_and_remark_win_over_the_local_copy(firebase, app_data_dir):
    firebase.seed("reports/rep_1", {
        "subject": "Crash", "status": "fixed", "admin_remark": "Fixed in 3.8.1", "affected_users_count": 9,
    })
    issues._save_local_reports({"rep_1": {
        "subject": "Crash", "status": "open", "admin_remark": "", "affected_users_count": 1,
    }})
    _, reports, _ = issues.fetch_all_reports()
    report = reports[0]
    assert (report["status"], report["admin_remark"], report["affected_users_count"]) == ("fixed", "Fixed in 3.8.1", 9)
    assert local_reports(app_data_dir) == {}


def test_old_local_only_reports_are_shown_but_not_uploaded_again(firebase):
    issues._save_local_reports({"rep_old": {"subject": "Old", "status": "open"}})
    _, reports, _ = issues.fetch_all_reports()
    assert reports[0]["local_only"] is True
    assert firebase.writes() == []


def test_comments_come_back_as_a_sorted_list(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash", "comments": {
        "c_b": {"id": "c_b", "created_at": "2026-02-01T00:00:00Z"},
        "c_a": {"id": "c_a", "created_at": "2026-01-01T00:00:00Z"},
    }})
    _, reports, _ = issues.fetch_all_reports()
    assert [c["id"] for c in reports[0]["comments"]] == ["c_a", "c_b"]
    assert reports[0]["comments_count"] == 2


# Votes


def test_votes_use_a_server_side_increment(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash", "affected_users_count": 4})
    assert issues.increment_report_affected("rep_1") == (True, 5)
    assert firebase.writes()[0]["body"] == {".sv": {"increment": 1}}


def test_a_duplicate_subject_adds_a_vote_instead_of_a_new_report(firebase):
    firebase.seed("reports/rep_1", {"subject": "App crashes on start", "affected_users_count": 1})
    result = issues.submit_user_report(subject="App crashes on start", category="Bug", description="Same")
    assert result.outcome == "duplicate"
    assert result.record["id"] == "rep_1"
    assert firebase.read("reports/rep_1/affected_users_count") == 2


# Item 2: only the server can grant admin powers


def test_the_right_key_is_accepted_by_the_server(firebase):
    assert issues.verify_admin_key(firebase.admin_key)[0] is True
    assert firebase.requests[-1]["auth"] == firebase.admin_key


def test_a_wrong_key_is_refused(firebase):
    assert issues.verify_admin_key("wrong")[0] is False


def test_a_local_key_file_or_environment_variable_grants_nothing(firebase, app_data_dir, monkeypatch):
    with open(os.path.join(str(app_data_dir), "admin_key.secret"), "w", encoding="utf-8") as handle:
        handle.write("anything\n")
    monkeypatch.setenv("LINK_EXTRACTOR_ADMIN_PIN", "anything")
    monkeypatch.setenv("APPDATA", str(app_data_dir))
    assert issues.verify_admin_key("anything")[0] is False


def test_an_unreachable_server_is_not_described_as_a_wrong_key(firebase_down):
    ok, message = issues.verify_admin_key("anything")
    assert ok is False
    assert "reach" in message.lower()


def _only_admin_may_change(firebase):
    def deny(method, path, auth):
        return method != "GET" and auth != firebase.admin_key

    firebase.deny = deny


def test_admin_changes_carry_the_key_and_take_effect(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash", "status": "open"})
    _only_admin_may_change(firebase)
    ok, _ = issues.update_report("rep_1", "fixed", "Done", firebase.admin_key)
    assert ok is True
    assert firebase.read("reports/rep_1/status") == "fixed"
    assert firebase.read("reports/rep_1/admin_remark") == "Done"


def test_a_refused_admin_change_is_reported_as_a_failure(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash", "status": "open"})
    _only_admin_may_change(firebase)
    ok, message = issues.update_report("rep_1", "fixed", "Hacked", "wrong")
    assert ok is False
    assert message
    assert firebase.read("reports/rep_1/status") == "open"


def test_delete_with_a_wrong_key_changes_nothing_even_with_a_local_key_file(firebase, app_data_dir):
    with open(os.path.join(str(app_data_dir), "admin_key.secret"), "w", encoding="utf-8") as handle:
        handle.write("anything\n")
    firebase.seed("reports/rep_1", {"subject": "Crash"})
    _only_admin_may_change(firebase)
    ok, _ = issues.delete_report("rep_1", "anything")
    assert ok is False
    assert firebase.read("reports/rep_1") is not None


def test_delete_removes_the_report_and_its_screenshots(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash"})
    firebase.seed("report_screenshots/rep_1/report", SCREENSHOT)
    ok, _ = issues.delete_report("rep_1", firebase.admin_key)
    assert ok is True
    assert firebase.read("reports/rep_1") is None
    assert firebase.read("report_screenshots/rep_1") is None


def test_unknown_statuses_are_refused(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash", "status": "open"})
    ok, _ = issues.update_report("rep_1", "hacked", "", firebase.admin_key)
    assert ok is False


@pytest.mark.parametrize("bad_id", ["../games_meta", "a/b", "", "a.b"])
def test_unsafe_report_ids_never_reach_the_server(firebase, bad_id):
    assert issues.update_report(bad_id, "fixed", "", firebase.admin_key)[0] is False
    assert issues.delete_report(bad_id, firebase.admin_key)[0] is False
    assert issues.delete_comment(bad_id, "c_1", firebase.admin_key)[0] is False
    assert issues.add_comment(bad_id, "hi")[0] is False
    assert issues.increment_report_affected(bad_id)[0] is False
    assert issues.get_screenshot(bad_id, "report") == ""
    assert firebase.requests == []


# Comments


def test_anyone_can_comment_but_the_comment_is_not_marked_admin(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash"})
    ok, comment_id, comment = issues.add_comment("rep_1", "Same here", author_type="gamer")
    assert ok is True
    assert firebase.read(f"reports/rep_1/comments/{comment_id}")["author_type"] == "gamer"
    assert comment["text"] == "Same here"


def test_admin_comments_need_a_key_that_the_server_accepts(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash"})
    _only_admin_may_change(firebase)
    assert issues.add_comment("rep_1", "Official", author_type="admin")[0] is False
    assert issues.add_comment("rep_1", "Official", author_type="admin", admin_key="wrong")[0] is False
    assert issues.add_comment("rep_1", "Official", author_type="admin", admin_key=firebase.admin_key)[0] is True


def test_a_failed_comment_is_reported_as_a_failure(firebase):
    firebase.deny = lambda method, path, auth: method != "GET"
    assert issues.add_comment("rep_1", "Hello")[0] is False


def test_deleting_a_comment_needs_the_server_to_agree(firebase):
    firebase.seed("reports/rep_1/comments/c_1", {"id": "c_1", "text": "x"})
    firebase.seed("report_screenshots/rep_1/c_1", SCREENSHOT)
    _only_admin_may_change(firebase)
    assert issues.delete_comment("rep_1", "c_1", "wrong")[0] is False
    assert firebase.read("reports/rep_1/comments/c_1") is not None
    assert issues.delete_comment("rep_1", "c_1", firebase.admin_key)[0] is True
    assert firebase.read("reports/rep_1/comments/c_1") is None
    assert firebase.read("report_screenshots/rep_1/c_1") is None


# Item 10: screenshots are downloaded only when someone looks at them


def test_screenshots_are_stored_apart_from_the_report_list(firebase):
    report_id = submit(screenshot_data=SCREENSHOT).report_id
    assert "screenshot_data" not in firebase.read(f"reports/{report_id}")
    assert firebase.read(f"reports/{report_id}/has_screenshot") is True
    assert issues.get_screenshot(report_id, "report") == SCREENSHOT


def test_comment_screenshots_are_stored_apart_too(firebase):
    firebase.seed("reports/rep_1", {"subject": "Crash"})
    _, comment_id, comment = issues.add_comment("rep_1", "See this", screenshot_data=SCREENSHOT)
    assert comment["has_screenshot"] is True
    assert "screenshot_data" not in firebase.read(f"reports/rep_1/comments/{comment_id}")
    assert issues.get_screenshot("rep_1", comment_id) == SCREENSHOT


def test_screenshots_stay_inline_until_the_new_database_rules_allow_the_new_path(firebase):
    firebase.deny = lambda method, path, auth: path.startswith("report_screenshots")
    report_id = submit(screenshot_data=SCREENSHOT).report_id
    assert firebase.read(f"reports/{report_id}")["screenshot_data"] == SCREENSHOT


def test_oversized_screenshots_are_refused_instead_of_being_cut_off(firebase):
    result = submit(screenshot_data="data:image/jpeg;base64," + "A" * (900 * 1024))
    assert result.outcome == "invalid"
    assert firebase.writes() == []


def test_oversized_comment_screenshots_are_refused(firebase):
    assert issues.add_comment("rep_1", "x", screenshot_data="data:image/png;base64," + "A" * (900 * 1024))[0] is False
    assert firebase.writes() == []


@pytest.mark.parametrize("data", ["data:text/html;base64,AAAA", "https://evil.example/x.png", "data:image/svg+xml;base64,AAAA"])
def test_only_plain_image_data_is_accepted(firebase, data):
    assert submit(screenshot_data=data).outcome == "invalid"


def test_empty_subject_is_refused(firebase):
    assert issues.submit_user_report(subject="  ", category="Bug", description="x").outcome == "invalid"
