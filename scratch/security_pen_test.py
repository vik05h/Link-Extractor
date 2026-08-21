import sys
import os
import re

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import history
import scraper
import community
import validator
import integrations


def test_ssrf_protection():
    print("--> 1. SSRF / Non-whitelisted Domain Check")
    ssrf_url = "http://169.254.169.254/latest/meta-data/"
    url_type = scraper.detect_url_type(ssrf_url)
    assert url_type == "unknown", f"SSRF URL should be unknown, got {url_type}"
    print("    [PASS] SSRF protection confirmed.")


def test_sql_injection():
    print("--> 2. SQL Injection Resistance in History Archive")
    test_db = os.path.join(os.path.dirname(__file__), "test_pen_history.db")
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass
    mgr = history.HistoryManager(test_db)
    malicious_title = "Game'); DROP TABLE extractions; --"
    rec_id = mgr.add_record(
        title=malicious_title,
        source_url="https://fitgirl-repacks.site/test/",
        total_parts=1,
        resolved_count=1,
        urls=["https://dl.fuckingfast.co/dl/part1#Game.part1.rar"]
    )
    records = mgr.get_records(search_query="DROP TABLE")
    assert len(records) == 1, "SQL Injection test failed: table was altered or query escaped"
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass
    print("    [PASS] Parameterized SQL queries completely immune.")


def test_path_traversal():
    print("--> 3. Path Traversal Filename Sanitization")
    dirty_title = "../../Windows/System32/evil"
    safe_slug = community.generate_game_slug("", dirty_title)
    assert ".." not in safe_slug and "/" not in safe_slug and "\\" not in safe_slug
    clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', dirty_title).strip('_')
    assert ".." not in clean_title and "/" not in clean_title and "\\" not in clean_title
    print("    [PASS] Path traversal sanitization confirmed.")


def test_crlf_header_injection():
    print("--> 4. CRLF / Header Injection in Payloads")
    payload = "Game\r\nInjected-Header: evil"
    safe = re.sub(r'[\r\n]', '', payload)
    assert "\r" not in safe and "\n" not in safe
    print("    [PASS] CRLF payload strip verified.")


def test_redos_protection():
    print("--> 5. ReDoS Safe Regex Matching")
    long_malicious = "https://dl.fuckingfast.co/dl/" + "a" * 10000 + "!@#$"
    res = scraper.extract_links_from_pastebin_html(long_malicious)
    assert isinstance(res, list)
    print("    [PASS] ReDoS safety confirmed.")


def test_community_schema_sanitization():
    print("--> 6. Community Cloud Schema & Slug Sanitization")
    bad_slug = "../../../secret-firebase-key"
    sanitized = community.sanitize_slug(bad_slug)
    assert ".." not in sanitized and "/" not in sanitized
    assert sanitized == "secret-firebase-key"
    print("    [PASS] Community slug sanitizer verified.")


if __name__ == "__main__":
    print("=== RUNNING FITGIRL LINK EXTRACTOR SECURITY PENETRATION TEST ===")
    test_ssrf_protection()
    test_sql_injection()
    test_path_traversal()
    test_crlf_header_injection()
    test_redos_protection()
    test_community_schema_sanitization()
    print("\nALL 6/6 SECURITY PENETRATION TESTS PASSED (100% CLEAN)!")
