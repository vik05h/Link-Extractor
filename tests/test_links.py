import pytest

import links


@pytest.mark.parametrize(
    "url",
    [
        "https://dl.fuckingfast.co/dl/abc123#Game.part001.rar",
        "https://dl.fuckingfast.co/dl/abc123",
    ],
)
def test_real_direct_links_are_accepted(url):
    assert links.is_direct_link(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/setup.exe#Game.part001.rar",
        "https://evil.example/fuckingfast.co/setup.exe",
        "https://evil.example/dl.fuckingfast.co/x",
        "https://dl.fuckingfast.co.evil.example/x",
        "https://notdl.fuckingfast.co.evil.example/x",
        "https://dl.fuckingfast.co@evil.example/x",
        "https://user:pass@dl.fuckingfast.co/x",
        "http://dl.fuckingfast.co/x",
        "file:///C:/Windows/System32/cmd.exe",
        "javascript:alert(1)",
        "https://bzzhr.to/abc",
        "https://www.filecrypt.cc/Container/abc",
        "https://dl.fuckingfast.co/x y",
        "https://dl.fuckingfast.co\\@evil.example/x",
        "https://dl.fuckingfast.co/x\nhttps://evil.example/y",
        "",
    ],
)
def test_anything_else_is_rejected_as_a_direct_link(url):
    assert not links.is_direct_link(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://fitgirl-repacks.site/black-myth-wukong/",
        "http://fitgirl-repacks.site/black-myth-wukong",
        "https://www.fitgirl-repacks.site/black-myth-wukong/",
    ],
)
def test_fitgirl_game_pages_are_recognised(url):
    assert links.is_fitgirl_page_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://fitgirl-repacks.site/",
        "https://fitgirl-repacks.site",
        "https://fitgirl-repacks.site.evil.example/game/",
        "https://evil.example/fitgirl-repacks.site/game/",
        "https://paste.fitgirl-repacks.site/?abc#key",
        "https://notfitgirl-repacks.site/game/",
    ],
)
def test_lookalikes_and_non_game_pages_are_not_fitgirl_pages(url):
    assert not links.is_fitgirl_page_url(url)


def test_only_the_exact_paste_host_counts_as_a_pastebin():
    assert links.is_fitgirl_paste_url("https://paste.fitgirl-repacks.site/?abc#key")
    assert not links.is_fitgirl_paste_url("https://paste.fitgirl-repacks.site.evil.example/?a#b")
    assert not links.is_fitgirl_paste_url("https://evil.example/paste.fitgirl-repacks.site/?a")


def test_hoster_pages_are_separate_from_direct_links():
    assert links.is_hoster_page_url("https://fuckingfast.co/abc123#Game.part001.rar")
    assert links.is_hoster_page_url("https://www.fuckingfast.co/abc123")
    assert not links.is_hoster_page_url("https://dl.fuckingfast.co/dl/abc")
    assert not links.is_hoster_page_url("https://notfuckingfast.co/abc")
    assert not links.is_hoster_page_url("https://fuckingfast.co.evil.example/abc")
    assert not links.is_hoster_page_url("https://fuckingfast.co/")


@pytest.mark.parametrize(
    "url,allowed",
    [
        ("", True),
        ("https://fitgirl-repacks.site/some-game/", True),
        ("https://paste.fitgirl-repacks.site/?a#b", True),
        ("https://fuckingfast.co/abc", True),
        ("https://steamrip.com/game", False),
        ("javascript:alert(1)", False),
        ("https://fitgirl-repacks.site.evil.example/x", False),
    ],
)
def test_source_urls_shown_as_clickable_links_are_restricted(url, allowed):
    assert links.is_allowed_source_url(url) is allowed


@pytest.mark.parametrize(
    "url,allowed",
    [
        ("https://shared.akamai.steamstatic.com/apps/1/header.jpg", True),
        ("http://example.com/cover.jpg", True),
        ("data:image/svg+xml;utf8,%3Csvg%3E", True),
        ("", False),
        ("javascript:alert(1)", False),
        ("file:///C:/secret.png", False),
        ("http://169.254.169.254/latest/meta-data/", False),
        ("http://127.0.0.1:9666/flash/add", False),
        ("http://localhost/x.png", False),
        ("http://192.168.1.1/x.png", False),
        ("http://10.0.0.8/x.png", False),
        ("http://[::1]/x.png", False),
        ("data:text/html,<script>1</script>", False),
    ],
)
def test_cover_images_cannot_point_at_private_addresses_or_scripts(url, allowed):
    assert links.is_safe_image_url(url) is allowed


def test_public_http_check_blocks_private_targets_only():
    assert links.is_public_http_url("https://example.com/a.png")
    assert not links.is_public_http_url("http://169.254.169.254/")
    assert not links.is_public_http_url("ftp://example.com/a")
    assert not links.is_public_http_url("https://user:pw@example.com/")


def test_extract_urls_handles_newlines_commas_spaces_and_glued_links():
    text = (
        "https://fuckingfast.co/a#a.rar\r\n"
        "https://fuckingfast.co/b#b.rar, https://fuckingfast.co/c#c.rar "
        "https://fuckingfast.co/d#d.rarhttps://fuckingfast.co/e#e.rar"
    )
    assert links.extract_urls(text) == [
        "https://fuckingfast.co/a#a.rar",
        "https://fuckingfast.co/b#b.rar",
        "https://fuckingfast.co/c#c.rar",
        "https://fuckingfast.co/d#d.rar",
        "https://fuckingfast.co/e#e.rar",
    ]


def test_part_name_prefers_the_filename_fragment_then_the_last_path_segment():
    assert links.part_name("https://fuckingfast.co/abc#Game.part001.rar") == "Game.part001.rar"
    assert links.part_name("https://fuckingfast.co/abc") == "abc"
    assert links.part_name("https://fuckingfast.co/abc/") == "abc"


def test_with_filename_fragments_only_fills_in_missing_names():
    result = links.with_filename_fragments(
        ["https://dl.fuckingfast.co/dl/a", " https://dl.fuckingfast.co/dl/b#Keep.rar ", ""],
        "Black Myth: Wukong",
    )
    assert result == [
        "https://dl.fuckingfast.co/dl/a#Black_Myth__Wukong.part001.rar",
        "https://dl.fuckingfast.co/dl/b#Keep.rar",
    ]
