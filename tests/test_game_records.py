from datetime import datetime, timedelta, timezone

import pytest

import game_records


def iso_hours_ago(hours):
    moment = datetime.now(timezone.utc) - timedelta(hours=hours)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def record(slug, title, source="", hours=1.0, **extra):
    return {"slug": slug, "title": title, "source_url": source, "timestamp_utc": iso_hours_ago(hours), **extra}


# Slugs


def test_slug_is_taken_from_a_real_fitgirl_page():
    assert game_records.generate_game_slug("https://fitgirl-repacks.site/god-of-war/") == "god-of-war"


def test_slug_ignores_lookalike_hosts_and_falls_back_to_the_title():
    slug = game_records.generate_game_slug("https://fitgirl-repacks.site.evil.example/x/", "Some Game [v1]")
    assert slug == "some-game"


def test_slug_cannot_escape_the_database_path():
    assert game_records.sanitize_slug("../../../secret-firebase-key") == "secret-firebase-key"


# Freshness: one rule everywhere


@pytest.mark.parametrize(
    "hours,expected",
    [(0.5, "fresh"), (11.9, "fresh"), (12.1, "aging"), (23.9, "aging"), (24.1, "expired"), (200, "expired")],
)
def test_freshness_boundaries(hours, expected):
    assert game_records.describe_age(iso_hours_ago(hours)).freshness == expected


def test_unreadable_timestamps_are_treated_as_expired_not_fresh():
    assert game_records.describe_age("not-a-date").freshness == "expired"
    assert game_records.describe_age("").freshness == "expired"


def test_timestamps_far_in_the_future_cannot_stay_fresh_forever():
    assert game_records.describe_age(iso_hours_ago(-24 * 365)).freshness == "expired"


def test_age_text_is_readable():
    assert game_records.describe_age(iso_hours_ago(2.5)).age_str == "2 hours ago"
    assert game_records.describe_age(iso_hours_ago(0)).age_str == "Just now"


# Cleaning untrusted shared records


def test_clean_record_keeps_normal_fields():
    cleaned = game_records.clean_feed_record(
        "a-game",
        {
            "title": "A Game",
            "source_url": "https://fitgirl-repacks.site/a-game/",
            "image_url": "https://example.com/a.jpg",
            "timestamp_utc": "2026-10-01T00:00:00Z",
            "total_parts": 3,
            "total_size_str": "1 GB",
            "used_count": 7,
        },
    )
    assert cleaned["slug"] == "a-game"
    assert cleaned["used_count"] == 7
    assert cleaned["source_url"] == "https://fitgirl-repacks.site/a-game/"


def test_clean_record_drops_records_without_a_title():
    assert game_records.clean_feed_record("ghost", {"used_count": 4}) is None
    assert game_records.clean_feed_record("ghost", "not a record") is None


@pytest.mark.parametrize("title", ["FuckingFast Direct Parts", "FitGirl Pastebin Download", "FitGirl Repack", "Part 3"])
def test_clean_record_hides_placeholder_titles(title):
    assert game_records.clean_feed_record("x", {"title": title}) is None


def test_clean_record_accepts_any_page_on_the_real_fitgirl_site_as_a_source():
    cleaned = game_records.clean_feed_record("x", {"title": "X", "source_url": "https://fitgirl-repacks.site/?s=x"})
    assert cleaned is not None


def test_clean_record_drops_out_of_scope_or_tampered_sources():
    assert game_records.clean_feed_record("x", {"title": "X", "source_url": "https://steamrip.com/x"}) is None
    assert game_records.clean_feed_record("x", {"title": "X", "source_url": "javascript:alert(1)"}) is None


def test_clean_record_blanks_unsafe_images_but_keeps_the_record():
    cleaned = game_records.clean_feed_record("x", {"title": "X", "image_url": "javascript:alert(1)"})
    assert cleaned["image_url"] == ""


def test_clean_record_removes_presence_data_and_bad_numbers():
    cleaned = game_records.clean_feed_record(
        "grand-theft-auto-v", {"title": "GTA V", "presence": {"sid": {"t": "x"}}, "used_count": "lots", "total_parts": None}
    )
    assert "presence" not in cleaned
    assert cleaned["used_count"] == 0
    assert cleaned["total_parts"] == 0


# Duplicate removal for display


def test_sequels_and_numbered_games_are_never_merged():
    titles = [
        "Warhammer 40,000: Space Marine",
        "Warhammer 40,000: Space Marine 2",
        "The Legend of Heroes: Trails of Cold Steel",
        "The Legend of Heroes: Trails of Cold Steel II",
        "The Legend of Heroes: Trails of Cold Steel III",
        "Mario + Rabbids Kingdom Battle",
        "Mario + Rabbids Sparks of Hope",
    ]
    records = [record(game_records.sanitize_slug(t), t, hours=i) for i, t in enumerate(titles)]
    assert sorted(r["title"] for r in game_records.dedupe_feed(records)) == sorted(titles)


def test_same_page_uploaded_under_two_slugs_shows_once_and_keeps_the_newest():
    page = "https://fitgirl-repacks.site/a-game/"
    records = [
        record("a-game-old", "A Game", page, hours=5, used_count=9),
        record("a-game", "A Game", page, hours=1, used_count=2),
    ]
    result = game_records.dedupe_feed(records)
    assert [r["slug"] for r in result] == ["a-game"]
    assert result[0]["used_count"] == 9


def test_same_game_with_a_different_version_suffix_shows_once():
    records = [
        record("foo-1", "Foo Bar – v1.2.3 + 5 DLCs", hours=9),
        record("foo-2", "Foo Bar – v1.3", hours=1),
    ]
    assert [r["slug"] for r in game_records.dedupe_feed(records)] == ["foo-2"]


# Exact matching


GAMES = [
    record("god-of-war-ragnarok", "God of War: Ragnarok", "https://fitgirl-repacks.site/god-of-war-ragnarok/"),
    record("elden-ring", "ELDEN RING – v1.12", "https://fitgirl-repacks.site/elden-ring/"),
]


def test_a_shorter_slug_never_matches_a_longer_game():
    assert game_records.find_match("https://fitgirl-repacks.site/god-of-war/", GAMES) is None
    assert game_records.find_match("god-of-war", GAMES) is None
    assert game_records.find_match("God of War", GAMES) is None


@pytest.mark.parametrize(
    "query",
    [
        "https://fitgirl-repacks.site/god-of-war-ragnarok/",
        "https://fitgirl-repacks.site/god-of-war-ragnarok",
        "god-of-war-ragnarok",
        "God of War: Ragnarok",
        "god of war ragnarok",
    ],
)
def test_the_exact_game_is_found_from_a_url_slug_or_title(query):
    assert game_records.find_match(query, GAMES)["slug"] == "god-of-war-ragnarok"


def test_version_suffixes_do_not_stop_a_title_match():
    assert game_records.find_match("Elden Ring - v1.14", GAMES)["slug"] == "elden-ring"


def test_generic_titles_never_match():
    games = [record("direct", "Direct Repack")]
    assert game_records.find_match("Direct Repack", games) is None


def test_empty_queries_never_match():
    assert game_records.find_match("   ", GAMES) is None
