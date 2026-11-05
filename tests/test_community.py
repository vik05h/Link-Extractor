import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

import community

GOOD_LINK = "https://dl.fuckingfast.co/dl/abc#Game.part001.rar"
EVIL_LINK = "https://evil.example/setup.exe#Game.part002.rar"


def iso_hours_ago(hours=0.0):
    moment = datetime.now(timezone.utc) - timedelta(hours=hours)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def meta(title, **extra):
    return {"title": title, "timestamp_utc": iso_hours_ago(), "total_parts": 1, **extra}


def wait_until(condition, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def sync_feed():
    """Force a feed sync and wait for it to finish."""
    done = threading.Event()
    community.get_community_games(force_refresh=True, on_synced=lambda games: done.set())
    assert done.wait(3.0)


@pytest.fixture(autouse=True)
def clean_feed_state():
    community.reset_feed_cache()
    yield
    community.reset_feed_cache()


# Item 1: links from the shared database are checked before use


def test_genuine_links_are_returned(firebase):
    firebase.seed("games_urls/a-game", {"urls": [GOOD_LINK]})
    assert community.get_game_urls("a-game") == [GOOD_LINK]


def test_a_record_with_any_foreign_link_is_rejected_whole(firebase):
    firebase.seed("games_urls/a-game", {"urls": [GOOD_LINK, EVIL_LINK]})
    assert community.get_game_urls("a-game") == []


def test_links_stored_as_a_plain_list_are_checked_too(firebase):
    firebase.seed("games_urls/a-game", [EVIL_LINK])
    assert community.get_game_urls("a-game") == []


def test_unreachable_database_gives_no_links_not_made_up_ones(firebase_down):
    assert community.get_game_urls("god-of-war-ragnarok") == []


def test_upload_refuses_foreign_links_and_writes_nothing(firebase):
    ok, _ = community.upload_game_record(
        slug="x", title="X", source_url="", image_url="",
        urls=[GOOD_LINK, "https://evil.example/fuckingfast.co/setup.exe"],
        total_parts=2, total_size_str="1 GB",
    )
    assert ok is False
    assert firebase.writes() == []


def test_upload_stores_links_and_metadata(firebase):
    ok, _ = community.upload_game_record(
        slug="a-game", title="A Game", source_url="https://fitgirl-repacks.site/a-game/",
        image_url="https://example.com/a.jpg", urls=[GOOD_LINK], total_parts=1,
        total_size_str="1 GB", total_size_bytes=1073741824,
    )
    assert ok is True
    assert firebase.read("games_urls/a-game")["urls"] == [GOOD_LINK]
    stored = firebase.read("games_meta/a-game")
    assert stored["title"] == "A Game"
    assert stored["total_size_bytes"] == 1073741824


def test_upload_failure_is_reported_as_a_failure(firebase):
    firebase.deny = lambda method, path, auth: method != "GET"
    ok, message = community.upload_game_record(
        slug="a-game", title="A Game", source_url="", image_url="", urls=[GOOD_LINK],
        total_parts=1, total_size_str="1 GB",
    )
    assert ok is False
    assert message


def test_re_upload_keeps_the_usage_count_and_presence_on_that_record(firebase):
    firebase.seed("games_meta/grand-theft-auto-v", {
        "title": "GTA V", "used_count": 12, "presence": {"sid": {"t": iso_hours_ago()}},
    })
    community.upload_game_record(
        slug="grand-theft-auto-v", title="GTA V", source_url="", image_url="",
        urls=[GOOD_LINK], total_parts=1, total_size_str="1 GB",
    )
    stored = firebase.read("games_meta/grand-theft-auto-v")
    assert stored["used_count"] == 12
    assert "sid" in stored["presence"]


def test_a_new_upload_appears_in_the_feed_without_another_download(firebase):
    sync_feed()
    firebase.requests.clear()
    community.upload_game_record(
        slug="a-game", title="A Game", source_url="", image_url="", urls=[GOOD_LINK],
        total_parts=1, total_size_str="1 GB",
    )
    assert [g["slug"] for g in community.get_community_games()] == ["a-game"]
    assert not [r for r in firebase.requests if r["path"] == "/games_meta.json"]


# Item 3: clients never delete shared records


def test_loading_the_feed_never_writes_or_deletes_anything(firebase):
    for title in [
        "Warhammer 40,000: Space Marine",
        "Warhammer 40,000: Space Marine 2",
        "Call of Duty: Modern Warfare II",
        "Call of Duty: Modern Warfare III",
    ]:
        firebase.seed(f"games_meta/{community.game_records.sanitize_slug(title)}", meta(title))
    firebase.seed("games_meta/duplicate-upload", meta("Call of Duty: Modern Warfare III"))
    sync_feed()
    assert firebase.writes() == []
    assert len(firebase.read("games_meta")) == 5


def test_sequels_all_appear_in_the_feed(firebase):
    titles = ["Warhammer 40,000: Space Marine", "Warhammer 40,000: Space Marine 2"]
    for title in titles:
        firebase.seed(f"games_meta/{community.game_records.sanitize_slug(title)}", meta(title))
    sync_feed()
    assert sorted(g["title"] for g in community.get_community_games()) == titles


def test_out_of_scope_records_are_left_out_of_the_feed(firebase):
    firebase.seed("games_meta/a-game", meta("A Game"))
    firebase.seed("games_meta/other", meta("Other", source_url="https://steamrip.com/other/"))
    firebase.seed("games_meta/blob", meta("FuckingFast Direct Parts"))
    sync_feed()
    assert [g["slug"] for g in community.get_community_games()] == ["a-game"]


# Item 7: exact matching


def _feed_with_ragnarok(firebase):
    firebase.seed("games_meta/god-of-war-ragnarok", meta(
        "God of War: Ragnarok", source_url="https://fitgirl-repacks.site/god-of-war-ragnarok/"
    ))
    firebase.seed("games_urls/god-of-war-ragnarok", {"urls": [GOOD_LINK]})
    sync_feed()


def test_a_different_game_is_never_returned(firebase):
    _feed_with_ragnarok(firebase)
    assert community.find_existing_game("https://fitgirl-repacks.site/god-of-war/", [])["exists"] is False


def test_the_right_game_is_returned_with_its_links(firebase):
    _feed_with_ragnarok(firebase)
    found = community.find_existing_game("https://fitgirl-repacks.site/god-of-war-ragnarok/", [])
    assert found["exists"] is True
    assert found["source"] == "community"
    assert found["record"]["slug"] == "god-of-war-ragnarok"
    assert found["record"]["urls"] == [GOOD_LINK]
    assert found["is_expired"] is False


def test_a_game_missing_from_the_cached_list_is_still_found_by_exact_slug(firebase):
    sync_feed()
    firebase.seed("games_meta/new-game", meta("New Game", source_url="https://fitgirl-repacks.site/new-game/"))
    firebase.seed("games_urls/new-game", {"urls": [GOOD_LINK]})
    found = community.find_existing_game("https://fitgirl-repacks.site/new-game/", [])
    assert found["exists"] is True


def test_old_records_are_marked_expired(firebase):
    firebase.seed("games_meta/old", {**meta("Old Game"), "timestamp_utc": iso_hours_ago(30)})
    firebase.seed("games_urls/old", {"urls": [GOOD_LINK]})
    sync_feed()
    assert community.find_existing_game("Old Game", [])["is_expired"] is True


def test_a_record_with_tampered_links_counts_as_no_match(firebase):
    firebase.seed("games_meta/a-game", meta("A Game"))
    firebase.seed("games_urls/a-game", {"urls": [EVIL_LINK]})
    sync_feed()
    assert community.find_existing_game("A Game", [])["exists"] is False


def _history_row(**overrides):
    row = {
        "id": 1, "title": "Local Game", "source_url": "https://fitgirl-repacks.site/local-game/",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "total_parts": 2, "resolved_count": 2,
        "total_size_str": "2 GB", "urls": [GOOD_LINK, GOOD_LINK],
    }
    row.update(overrides)
    return row


def test_local_history_is_used_when_the_community_has_no_match(firebase):
    found = community.find_existing_game("https://fitgirl-repacks.site/local-game/", [_history_row()])
    assert found["exists"] is True
    assert found["source"] == "history"
    assert found["is_expired"] is False


def test_a_longer_history_title_does_not_match_a_shorter_game(firebase):
    rows = [_history_row(title="God of War Ragnarok", source_url="https://fitgirl-repacks.site/god-of-war-ragnarok/")]
    assert community.find_existing_game("https://fitgirl-repacks.site/god-of-war/", rows)["exists"] is False


def test_incomplete_history_records_are_never_offered_as_a_match(firebase):
    rows = [_history_row(resolved_count=1, urls=[GOOD_LINK])]
    assert community.find_existing_game("https://fitgirl-repacks.site/local-game/", rows)["exists"] is False


def test_old_history_records_are_marked_expired(firebase):
    two_days_ago = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 172800))
    rows = [_history_row(timestamp=two_days_ago)]
    assert community.find_existing_game("https://fitgirl-repacks.site/local-game/", rows)["is_expired"] is True


# Item 8: the Hub shows current, honest data


def test_startup_returns_the_saved_list_then_reports_when_new_data_arrives(firebase):
    community._save_cached_feed([{**meta("Old From Disk"), "slug": "old-from-disk"}])
    firebase.seed("games_meta/new-game", meta("New From Cloud"))

    synced = threading.Event()
    received = []

    def on_synced(games):
        received.extend(games)
        synced.set()

    first = community.get_community_games(on_synced=on_synced)
    assert [g["title"] for g in first] == ["Old From Disk"]
    assert synced.wait(3.0)
    assert [g["title"] for g in received] == ["New From Cloud"]
    assert [g["title"] for g in community.get_community_games()] == ["New From Cloud"]


def test_a_saved_list_gets_its_age_recalculated(firebase):
    community._save_cached_feed([{
        "slug": "old", "title": "Old", "timestamp_utc": iso_hours_ago(40), "freshness": "fresh", "age_str": "Just now",
    }])
    game = community.get_community_games()[0]
    assert game["freshness"] == "expired"
    assert game["age_str"] == "1 day ago"


def test_every_caller_waiting_during_a_sync_is_told_when_it_ends(firebase):
    calls = []
    community.get_community_games(on_synced=lambda games: calls.append("first"))
    community.get_community_games(force_refresh=True, on_synced=lambda games: calls.append("second"))
    assert wait_until(lambda: len(calls) == 2)


def test_a_recent_sync_is_reused_so_listening_to_the_update_cannot_loop(firebase):
    sync_feed()
    firebase.requests.clear()
    calls = []
    community.get_community_games(on_synced=lambda games: calls.append(1))
    time.sleep(0.2)
    assert calls == []
    assert firebase.requests == []


def test_a_forced_refresh_downloads_again(firebase):
    sync_feed()
    firebase.requests.clear()
    sync_feed()
    assert [r["path"] for r in firebase.requests] == ["/games_meta.json"]


def test_a_sync_that_hits_unexpected_data_still_ends(firebase, monkeypatch):
    def explode(raw):
        raise RuntimeError("unexpected shape")

    monkeypatch.setattr(community, "_clean_feed", explode)
    done = threading.Event()
    community.get_community_games(force_refresh=True, on_synced=lambda games: done.set())
    assert done.wait(3.0)
    assert community.feed_status()["syncing"] is False


def test_offline_with_no_saved_list_shows_nothing_rather_than_made_up_games(firebase_down):
    done = threading.Event()
    games = community.get_community_games(on_synced=lambda g: done.set())
    assert games == []
    assert done.wait(5.0)
    assert community.get_community_games() == []
    assert community.feed_status()["offline"] is True


def test_offline_keeps_the_saved_list_and_says_so(firebase_down):
    community._save_cached_feed([{**meta("Saved"), "slug": "saved"}])
    done = threading.Event()
    community.get_community_games(on_synced=lambda g: done.set())
    assert done.wait(5.0)
    assert [g["title"] for g in community.get_community_games()] == ["Saved"]
    assert community.feed_status()["offline"] is True


def test_coming_back_online_clears_the_offline_flag(firebase):
    sync_feed()
    assert community.feed_status()["offline"] is False


def test_made_up_records_saved_by_older_versions_are_dropped(app_data_dir, firebase_down):
    path = os.path.join(str(app_data_dir), "community_games_cache.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump([
            {"slug": "god-of-war-ragnarok", "title": "God of War", "uploader": "KratosBlade", "timestamp_utc": iso_hours_ago()},
            {"slug": "real", "title": "Real Game", "uploader": "Anonymous", "timestamp_utc": iso_hours_ago()},
        ], handle)
    assert [g["slug"] for g in community.get_community_games()] == ["real"]


# Item 10: fewer downloads


def test_heartbeat_stats_never_download_the_game_list(firebase):
    firebase.seed("games_meta/a-game", meta("A Game", used_count=3))
    sync_feed()
    firebase.requests.clear()
    community._feed.synced_at = 0.0  # Even a very old list must not be refreshed by stats.
    stats = community.get_community_stats()
    time.sleep(0.2)
    assert stats["total_grabs"] == 3
    assert firebase.requests == []


def test_one_presence_tick_touches_only_presence(firebase):
    community.ping_presence("session-1")
    paths = {r["path"] for r in firebase.requests}
    assert paths and all("/presence" in path for path in paths)


def test_presence_counts_recent_sessions_and_removes_stale_ones(firebase):
    base = "games_meta/grand-theft-auto-v/presence"
    firebase.seed(f"{base}/active", {"t": iso_hours_ago()})
    firebase.seed(f"{base}/stale", {"t": iso_hours_ago(1)})
    assert community.ping_presence("me") == 2
    assert wait_until(lambda: firebase.read(f"{base}/stale") is None)
    assert community.get_community_stats()["live_gamers"] == 2


def test_presence_failure_is_not_fatal(firebase_down):
    assert community.ping_presence("me") == 1


# Item 15: the usage counter


def test_usage_counter_ignores_games_that_are_not_in_the_database(firebase):
    assert community.increment_game_usage("direct-repack") == 0
    assert firebase.writes() == []
    assert firebase.read("games_meta/direct-repack") is None


def test_usage_counter_uses_a_server_side_increment(firebase):
    firebase.seed("games_meta/a-game", meta("A Game", used_count=4))
    assert community.increment_game_usage("a-game") == 5
    assert community.increment_game_usage("a-game") == 6
    assert firebase.read("games_meta/a-game/used_count") == 6
    assert firebase.writes()[0]["body"] == {".sv": {"increment": 1}}
