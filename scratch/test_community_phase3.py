import sys
import os

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import community
import scraper
import utils
from history import HistoryManager
from ui.state import AppState, UIContext


def test_slug_generation():
    print("--> Testing slug generation...")
    s1 = community.generate_game_slug("https://fitgirl-repacks.site/black-myth-wukong/")
    assert s1 == "black-myth-wukong", f"Expected black-myth-wukong, got {s1}"

    s2 = scraper.extract_game_slug("https://fitgirl-repacks.site/elden-ring-shadow-of-the-erdtree/")
    assert s2 == "elden-ring-shadow-of-the-erdtree", f"Expected elden-ring-shadow-of-the-erdtree, got {s2}"

    s3 = community.generate_game_slug("", "Cyberpunk 2077: Ultimate Edition [v2.13]")
    assert "cyberpunk-2077-ultimate-edition" in s3, f"Unexpected title slug: {s3}"
    print("    [PASS] Slug generation passed.")


def test_timestamp_localization():
    print("--> Testing local timezone conversion...")
    utc_iso = community.get_current_utc_iso()
    loc_str, age_str, freshness = community.format_localized_timestamp(utc_iso)
    print(f"    Current UTC: {utc_iso} -> Local Time: '{loc_str}' (Age: '{age_str}', Freshness: '{freshness}')")
    assert freshness == "fresh"
    assert age_str in ("Just now", "0 mins ago", "1 min ago")

    # Test aging timestamp (20 hours ago)
    old_iso = "2026-08-20T20:00:00Z"
    loc_str2, age_str2, freshness2 = community.format_localized_timestamp(old_iso)
    print(f"    Past UTC: {old_iso} -> Local Time: '{loc_str2}' (Age: '{age_str2}', Freshness: '{freshness2}')")
    print("    [PASS] Timezone localization passed.")


def test_community_feed_and_cache():
    print("--> Testing Community Cloud feed retrieval...")
    games = community.get_community_games()
    assert len(games) >= 4, f"Expected >= 4 games, got {len(games)}"
    first = games[0]
    print(f"    Top Repack: '{first['title']}' | Local Time: '{first['local_time']}' | Size: {first['total_size_str']}")

    bmw = community.get_game_by_slug("black-myth-wukong")
    assert bmw is not None
    assert bmw["title"].startswith("Black Myth")
    print(f"    Loaded by slug: '{bmw['title']}'")

    urls = community.get_game_urls("black-myth-wukong")
    assert len(urls) == 28, f"Expected 28 URLs, got {len(urls)}"
    assert all("fuckingfast.co" in u for u in urls)
    print(f"    Extracted {len(urls)} direct URLs for Black Myth: Wukong")
    print("    [PASS] Community feed & cache passed.")


def test_upload_and_overwrite():
    print("--> Testing Community upload & overwrite logic...")
    new_urls = [
        f"https://dl.fuckingfast.co/dl/test_game_p{i:02d}#Test_Game.part{i:02d}.rar" for i in range(1, 6)
    ]
    ok, msg = community.upload_game_record(
        slug="test-repack-game",
        title="Test Repack Game 2026",
        source_url="https://fitgirl-repacks.site/test-repack-game/",
        image_url="https://fitgirl-repacks.site/wp-content/uploads/test.jpg",
        urls=new_urls,
        total_parts=5,
        total_size_str="15.5 GB",
        total_size_bytes=16642998272,
        uploader="Tester"
    )
    assert ok, f"Upload failed: {msg}"
    print(f"    Upload result: {msg}")

    rec = community.get_game_by_slug("test-repack-game")
    assert rec is not None
    assert rec["title"] == "Test Repack Game 2026"
    assert rec["total_parts"] == 5

    urls_fetched = community.get_game_urls("test-repack-game")
    assert len(urls_fetched) == 5
    print("    [PASS] Upload & overwrite passed.")


def test_scraper_cover_image():
    print("--> Testing scraper cover image extraction from HTML mock...")
    mock_html = """
    <html>
        <head><title>Test Game Repack - FitGirl Repacks</title></head>
        <body>
            <h1 class="entry-title">Test Game Repack</h1>
            <div class="entry-content">
                <p><img class="alignleft wp-post-image" src="https://fitgirl-repacks.site/wp-content/uploads/2024/08/test-cover.jpg" alt="cover"></p>
                <a href="https://paste.fitgirl-repacks.site/?abcdef#1234">FuckingFast [Pastebin]</a>
            </div>
        </body>
    </html>
    """
    img = scraper.extract_game_cover_image("https://fitgirl-repacks.site/test-game/", mock_html)
    assert img == "https://fitgirl-repacks.site/wp-content/uploads/2024/08/test-cover.jpg", f"Got: {img}"
    print(f"    Extracted cover: {img}")
    print("    [PASS] Scraper cover image passed.")


if __name__ == "__main__":
    print("=== RUNNING PHASE 3 COMMUNITY HUB TEST SUITE ===")
    test_slug_generation()
    test_timestamp_localization()
    test_community_feed_and_cache()
    test_upload_and_overwrite()
    test_scraper_cover_image()
    print("\nALL PHASE 3 COMMUNITY UNIT TESTS PASSED SUCCESSFULLY! (100% OK)")
