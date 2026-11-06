"""Checks on firebase/database.rules.json that need no emulator.

These confirm the file is well formed and that the server and the app agree on which
links are allowed. How the rules behave end to end is covered by test_firebase_rules.py.
"""

import json
import pathlib
import re

import pytest

import links

RULES_FILE = pathlib.Path(__file__).resolve().parents[1] / "firebase" / "database.rules.json"
RULES = json.loads(RULES_FILE.read_text(encoding="utf-8"))["rules"]


def regex_from(rule):
    """Pull the /.../ pattern out of a rule expression, converted for Python."""
    return re.search(r"matches\(/(.*)/\)", rule).group(1).replace("\\/", "/")


LINK_PATTERN = regex_from(RULES["games_urls"]["$slug"]["urls"]["$index"][".validate"])
SOURCE_PATTERN = regex_from(RULES["games_meta"]["$slug"]["source_url"][".validate"])
IMAGE_PATTERN = regex_from(RULES["games_meta"]["$slug"]["image_url"][".validate"])


def all_rule_expressions(node):
    for key, value in node.items():
        if isinstance(value, dict):
            yield from all_rule_expressions(value)
        elif key in (".read", ".write", ".validate") and isinstance(value, str):
            yield value


def test_every_expression_has_balanced_brackets_and_quotes():
    for expression in all_rule_expressions(RULES):
        without_patterns = re.sub(r"matches\(/.*/\)", "matches()", expression)
        assert without_patterns.count("(") == without_patterns.count(")"), expression
        assert without_patterns.count("'") % 2 == 0, expression


def test_everything_is_closed_unless_opened_on_purpose():
    assert RULES[".read"] is False
    assert RULES[".write"] is False


def test_crash_logs_can_be_written_but_not_read():
    assert ".read" not in RULES["crash_logs"]


def test_only_public_data_is_readable():
    readable = {name for name, rule in RULES.items() if isinstance(rule, dict) and rule.get(".read") is True}
    assert readable == {"games_meta", "games_urls", "reports", "report_screenshots"}


def test_games_cannot_be_deleted_by_clients():
    assert RULES["games_meta"]["$slug"][".write"] == "newData.exists()"
    assert RULES["games_urls"]["$slug"][".write"] == "newData.exists()"


def test_reports_and_comments_can_only_be_created_not_changed():
    create_only = "!data.exists() && newData.exists()"
    assert RULES["reports"]["$report"][".write"] == create_only
    assert RULES["reports"]["$report"]["comments"]["$comment"][".write"] == create_only
    assert RULES["crash_logs"]["$crash"][".write"] == create_only


def test_clients_cannot_post_as_admin():
    validate = RULES["reports"]["$report"]["comments"]["$comment"][".validate"]
    assert "'admin'" not in validate
    assert "'reporter'" in validate and "'gamer'" in validate


@pytest.mark.parametrize(
    "url",
    [
        "https://dl.fuckingfast.co/dl/abc#Game.part001.rar",
        "https://evil.example/setup.exe#Game.part002.rar",
        "https://evil.example/fuckingfast.co/setup.exe",
        "https://dl.fuckingfast.co.evil.example/x",
        "https://dl.fuckingfast.co@evil.example/x",
        "http://dl.fuckingfast.co/x",
        "https://dl.fuckingfast.co/x y",
        "https://bzzhr.to/abc",
        "javascript:alert(1)",
    ],
)
def test_server_and_app_agree_on_direct_links(url):
    assert bool(re.search(LINK_PATTERN, url)) == links.is_direct_link(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://fitgirl-repacks.site/some-game/",
        "https://www.fitgirl-repacks.site/some-game/",
        "https://paste.fitgirl-repacks.site/?a#b",
        "https://fuckingfast.co/abc#x.rar",
        "https://steamrip.com/game/",
        "https://fitgirl-repacks.site.evil.example/x/",
        "javascript:alert(1)",
    ],
)
def test_server_and_app_agree_on_source_links(url):
    assert bool(re.search(SOURCE_PATTERN, url)) == links.is_allowed_source_url(url)


@pytest.mark.parametrize(
    "url,allowed",
    [
        ("", True),
        ("https://example.com/cover.jpg", True),
        ("http://example.com/cover.jpg", True),
        ("data:image/svg+xml;utf8,%3Csvg%3E", True),
        ("javascript:alert(1)", False),
        ("data:text/html,x", False),
    ],
)
def test_server_rejects_scripts_as_cover_images(url, allowed):
    assert bool(re.search(IMAGE_PATTERN, url)) is allowed
