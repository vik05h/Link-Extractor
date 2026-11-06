import pytest

import scraper

PAGE = """
<html><head><title>Some Game &#8211; FitGirl Repacks</title></head><body>
<h1 class="entry-title">Some Game &#8211; v1.2 + 3 DLCs</h1>
<img class="alignleft wp-post-image" src="https://example.com/cover.jpg" />
<ul>
  <li><a href="https://paste.fitgirl-repacks.site/?aaa#key1">Filehoster: FuckingFast</a></li>
  <li><a href="https://paste.fitgirl-repacks.site/?bbb#key2">Filehoster: DataNodes</a></li>
</ul>
</body></html>
"""


@pytest.mark.parametrize(
    "text,expected",
    [
        ("https://fitgirl-repacks.site/black-myth-wukong/", "fitgirl_game_page"),
        ("fitgirl-repacks.site/black-myth-wukong/", "fitgirl_game_page"),
        ("  https://fitgirl-repacks.site/black-myth-wukong/  ", "fitgirl_game_page"),
        ("https://paste.fitgirl-repacks.site/?dc64365f494f3ba0#abc", "fitgirl_pastebin"),
        ("paste.fitgirl-repacks.site/?dc64365f494f3ba0#abc", "fitgirl_pastebin"),
        ("https://fuckingfast.co/abc123#Game.part001.rar", "fuckingfast_direct"),
        ("fuckingfast.co/abc123", "fuckingfast_direct"),
        ("https://fuckingfast.co/a#a.rar\nhttps://fuckingfast.co/b#b.rar", "raw_links"),
        ("https://fuckingfast.co/a#a.rarhttps://fuckingfast.co/b#b.rar", "raw_links"),
    ],
)
def test_supported_links_are_recognised(text, expected):
    assert scraper.detect_url_type(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "hello world",
        "http://169.254.169.254/latest/meta-data/",
        "https://fitgirl-repacks.site.evil.example/game/",
        "https://evil.example/fitgirl-repacks.site/game/",
        "https://paste.fitgirl-repacks.site.evil.example/?a#b",
        "https://notfuckingfast.co/abc",
        "https://fuckingfast.co.evil.example/abc",
        "https://fitgirl-repacks.site/",
        "check out https://fitgirl-repacks.site/some-game/ it is great",
        "I read about fitgirl-repacks.site yesterday",
        # Links this app already produced need no resolving.
        "https://dl.fuckingfast.co/dl/token#Game.part001.rar",
        "https://dl.fuckingfast.co/dl/a#a.rar\nhttps://dl.fuckingfast.co/dl/b#b.rar",
        # A mix with anything foreign is not treated as a list of parts.
        "https://fuckingfast.co/a#a.rar\nhttps://evil.example/b#b.rar",
    ],
)
def test_everything_else_is_unknown(text):
    assert scraper.detect_url_type(text) == "unknown"


def test_parts_are_read_from_pasted_text():
    text = "https://fuckingfast.co/a#a.rar\r\nhttps://fuckingfast.co/b#b.rar, https://fuckingfast.co/a#a.rar"
    assert scraper.extract_hoster_links(text) == ["https://fuckingfast.co/a#a.rar", "https://fuckingfast.co/b#b.rar"]


def test_game_page_details_are_parsed_from_html():
    assert scraper.extract_game_title("https://fitgirl-repacks.site/some-game/", PAGE) == "Some Game – v1.2 + 3 DLCs"
    assert scraper.extract_game_cover_image("https://fitgirl-repacks.site/some-game/", PAGE) == "https://example.com/cover.jpg"


def test_pastebin_links_and_their_hosters_are_parsed_from_html():
    pastes = scraper.parse_pastebins_from_html(PAGE)
    assert [(p["hoster"], p["url"]) for p in pastes] == [
        ("FuckingFast", "https://paste.fitgirl-repacks.site/?aaa#key1"),
        ("DataNodes", "https://paste.fitgirl-repacks.site/?bbb#key2"),
    ]


def test_pastebin_html_yields_unique_hoster_links_only():
    html = (
        '<a href="https://fuckingfast.co/a#a.rar">1</a> https://fuckingfast.co/a#a.rar '
        '<a href="https://fuckingfast.co/b#b.rar">2</a> '
        '<a href="https://evil.example/fuckingfast.co/c">3</a>'
    )
    assert scraper.extract_links_from_pastebin_html(html) == [
        "https://fuckingfast.co/a#a.rar",
        "https://fuckingfast.co/b#b.rar",
    ]


def test_a_game_name_is_inferred_from_part_filenames():
    urls = ["https://fuckingfast.co/a#Crimson_Desert_Enhanced_--_fitgirl-repacks.site_--_.part01.rar"]
    assert scraper.extract_game_info_from_part_urls(urls)[0] == "Crimson Desert Enhanced"


def test_generated_banners_escape_the_title():
    banner = scraper.generate_procedural_banner_svg("<script>alert(1)</script>")
    assert "<script>" not in banner and "%3Cscript%3E" not in banner
