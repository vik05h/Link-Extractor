import os
import threading

import pytest

import engine
import pipeline
import validator
from history import HistoryManager
from pipeline import ExtractionPipeline, PipelinePorts

GAME_PAGE = "https://fitgirl-repacks.site/some-game/"
PASTE = "https://paste.fitgirl-repacks.site/?abc#key"
PARTS = [f"https://fuckingfast.co/p{i}#Some_Game.part{i:03d}.rar" for i in (1, 2, 3)]


def direct(url):
    return f"https://dl.fuckingfast.co/dl/{url.split('/')[-1].split('#')[0]}#{url.split('#')[-1]}"


class FakeEngine:
    """Stands in for the browser pool."""

    def __init__(self, world):
        self.world = world

    async def fetch_pastebin_links(self, url, log_cb=None):
        self.world.pastebins_opened.append(url)
        if self.world.on_paste:
            self.world.on_paste()
        return list(self.world.parts)

    def resolve_all(self, urls, on_progress=None, on_log=None, cancel_event=None):
        self.world.resolved_urls = list(urls)
        if on_log:
            on_log("engine says hello")
        if self.world.on_resolve:
            self.world.on_resolve()
        results = []
        for index, url in enumerate(urls):
            ok = url not in self.world.unresolvable
            name = url.split("#")[-1] if "#" in url else url.split("/")[-1]
            results.append(engine.ResolvedLink(
                index=index, original_url=url, part_name=name,
                direct_url=direct(url) if ok else None, status="resolved" if ok else "failed",
            ))
            if on_progress:
                on_progress(index + 1, len(urls), 1.0, 0.0, 1, name, results[-1].direct_url, results[-1].status)
        return results


class World:
    """Everything outside the pipeline, recorded so tests can check what happened."""

    def __init__(self, tmp_path):
        self.parts = list(PARTS)
        self.unresolvable = set()
        self.verdicts = {}
        self.on_paste = None
        self.on_resolve = None
        self.on_validate = None
        self.pastebins_opened = []
        self.resolved_urls = None
        self.validate_calls = 0
        self.published = []
        self.publish_result = (True, "ok")
        self.existing = {"exists": False}
        self.duplicate_answer = "fresh"
        self.duplicate_questions = []
        self.events = []
        self.engines_made = 0
        self.settings = {"auto_validate": True, "community_auto_upload": True}
        self.history = HistoryManager(os.path.join(str(tmp_path), "history.db"))
        self.game_page = ([{"hoster": "FuckingFast", "url": PASTE, "label": "FuckingFast"}], "Some Game", "https://example.com/c.jpg")
        self.cancel = threading.Event()

    def make_engine(self, concurrency):
        self.engines_made += 1
        return FakeEngine(self)

    def validate(self, urls, max_workers=15, on_progress=None, cancel_event=None):
        self.validate_calls += 1
        if self.on_validate:
            self.on_validate()
        summary = validator.ValidationSummary(total_links=len(urls))
        summary.cancelled = bool(cancel_event and cancel_event.is_set())
        for index, url in enumerate(urls):
            link = validator.ValidatedLink(index=index, url=url, verdict=self.verdicts.get(url, validator.ALIVE))
            if link.is_valid:
                link.content_length_bytes = 1024
                link.content_length_str = "1 KB"
            summary.links.append(link)
            if on_progress:
                on_progress(index + 1, len(urls), link)
        summary.valid_count = sum(1 for link in summary.links if link.verdict == validator.ALIVE)
        summary.dead_count = sum(1 for link in summary.links if link.verdict == validator.DEAD)
        summary.unknown_count = sum(1 for link in summary.links if link.verdict == validator.UNKNOWN)
        summary.total_bytes = 1024 * summary.valid_count
        summary.total_size_str = validator.format_bytes(summary.total_bytes)
        return summary

    def publish(self, **record):
        self.published.append(record)
        return self.publish_result

    def run(self, url=GAME_PAGE, force_fresh=False):
        ports = PipelinePorts(
            make_engine=self.make_engine,
            validate_links=self.validate,
            fetch_game_page=lambda page: self.game_page,
            resolve_paste_metadata=lambda paste, parts: {
                "title": "Some Game", "image_url": "", "source_url": GAME_PAGE, "slug": "some-game",
            },
            publish=self.publish,
            find_existing=lambda query: self.existing,
            ask_duplicate=self._ask,
        )
        return ExtractionPipeline(ports, self.history, self.settings, self.emit).run(
            url, concurrency=3, force_fresh=force_fresh, cancel_event=self.cancel
        )

    def _ask(self, record):
        self.duplicate_questions.append(record)
        return self.duplicate_answer

    def emit(self, name, payload=None):
        self.events.append((name, payload))

    def names(self):
        return [name for name, _ in self.events]

    def event(self, name):
        return next(payload for event_name, payload in self.events if event_name == name)

    def rows(self):
        return self.history.get_records()


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def assert_nothing_kept(world):
    assert world.rows() == []
    assert world.published == []
    assert "pipeline:complete" not in world.names()


# A full, verified run


def test_a_complete_verified_run_is_saved_published_and_reported(world):
    result = world.run()
    assert result.status == "complete"
    assert result.verified is True
    assert len(world.rows()) == 1
    assert world.rows()[0]["total_parts"] == 3
    assert world.rows()[0]["resolved_count"] == 3
    assert len(world.published) == 1
    assert world.published[0]["slug"] == "some-game"
    done = world.event("pipeline:complete")
    assert done["status"] == "complete"
    assert done["verified"] is True
    assert done["published"] is True
    assert done["failed_parts"] == []
    assert done["parts_count"] == done["expected_parts"] == 3
    assert "community:feed_updated" in world.names()


# Cancelling stops the run, and nothing is kept


def test_cancel_during_validation_keeps_nothing(world):
    world.on_validate = world.cancel.set
    result = world.run()
    assert result.status == "cancelled"
    assert_nothing_kept(world)
    assert "pipeline:cancelled" in world.names()


def test_cancel_during_resolving_keeps_nothing_and_skips_validation(world):
    world.on_resolve = world.cancel.set
    assert world.run().status == "cancelled"
    assert_nothing_kept(world)
    assert world.validate_calls == 0


def test_cancel_while_opening_the_pastebin_stops_before_resolving(world):
    world.on_paste = world.cancel.set
    assert world.run().status == "cancelled"
    assert_nothing_kept(world)
    assert world.resolved_urls is None


# Incomplete runs


def test_a_missing_part_is_kept_locally_flagged_and_never_published(world):
    world.unresolvable = {PARTS[1]}
    result = world.run()
    assert result.status == "partial"
    assert world.published == []
    row = world.rows()[0]
    assert (row["total_parts"], row["resolved_count"]) == (3, 2)
    done = world.event("pipeline:complete")
    assert done["status"] == "partial"
    assert done["parts_count"] == 2
    assert done["expected_parts"] == 3
    assert done["published"] is False
    assert [part["filename"] for part in done["failed_parts"]] == ["Some_Game.part002.rar"]


def test_a_dead_link_is_removed_flagged_and_stops_publishing(world):
    dead = direct(PARTS[0])
    world.verdicts = {dead: validator.DEAD}
    result = world.run()
    assert result.status == "partial"
    assert dead not in result.urls
    assert len(result.urls) == 2
    assert world.published == []
    assert [part["filename"] for part in world.event("pipeline:complete")["failed_parts"]] == ["Some_Game.part001.rar"]


def test_a_link_that_could_not_be_checked_is_kept_but_not_called_verified(world):
    uncertain = direct(PARTS[0])
    world.verdicts = {uncertain: validator.UNKNOWN}
    result = world.run()
    assert result.status == "complete"
    assert result.verified is False
    assert uncertain in result.urls
    assert world.published == []
    done = world.event("pipeline:complete")
    assert done["verified"] is False
    assert done["unverified_count"] == 1


def test_when_every_link_is_dead_nothing_is_kept_and_the_user_is_told(world):
    world.verdicts = {direct(url): validator.DEAD for url in PARTS}
    assert world.run().status == "failed"
    assert_nothing_kept(world)
    assert "pipeline:error" in world.names()


def test_when_nothing_resolves_nothing_is_kept_and_the_user_is_told(world):
    world.unresolvable = set(PARTS)
    assert world.run().status == "failed"
    assert_nothing_kept(world)
    assert "pipeline:error" in world.names()


# When publishing is not allowed


def test_links_are_not_published_when_they_were_not_checked(world):
    world.settings["auto_validate"] = False
    result = world.run()
    assert result.status == "complete"
    assert result.verified is False
    assert world.validate_calls == 0
    assert world.published == []
    assert len(world.rows()) == 1


def test_the_community_upload_opt_out_is_respected(world):
    world.settings["community_auto_upload"] = False
    world.run()
    assert world.published == []
    assert world.event("pipeline:complete")["published"] is False


def test_placeholder_titles_are_not_published(world):
    world.game_page = (world.game_page[0], "FitGirl Repack", "")
    world.run()
    assert world.published == []


def test_a_publish_failure_does_not_lose_the_links(world):
    world.publish_result = (False, "Could not publish")
    result = world.run()
    assert result.status == "complete"
    assert len(world.rows()) == 1
    done = world.event("pipeline:complete")
    assert done["published"] is False
    assert done["publish_error"] == "Could not publish"
    assert "community:feed_updated" not in world.names()


def test_a_crash_while_publishing_does_not_lose_the_links(world):
    def explode(**record):
        raise RuntimeError("boom")

    world.publish = explode
    result = world.run()
    assert result.status == "complete"
    assert "pipeline:complete" in world.names()


# Other kinds of input


def test_several_pasted_links_are_resolved_one_by_one(world):
    result = world.run("https://fuckingfast.co/a#Foo_Bar.part1.rar\nhttps://fuckingfast.co/b#Foo_Bar.part2.rar")
    assert world.resolved_urls == ["https://fuckingfast.co/a#Foo_Bar.part1.rar", "https://fuckingfast.co/b#Foo_Bar.part2.rar"]
    assert result.status == "complete"
    assert world.published == []
    assert result.title == "Foo Bar"


def test_a_single_part_link_is_resolved_but_not_published(world):
    result = world.run("https://fuckingfast.co/a#Foo_Bar.part1.rar")
    assert world.resolved_urls == ["https://fuckingfast.co/a#Foo_Bar.part1.rar"]
    assert result.status == "complete"
    assert world.published == []


def test_a_link_without_a_scheme_still_works(world):
    world.run("fuckingfast.co/a#Foo.rar")
    assert world.resolved_urls == ["https://fuckingfast.co/a#Foo.rar"]


def test_part_names_sent_to_the_ui_match_for_links_without_a_filename(world):
    world.run("https://fuckingfast.co/abc123")
    init = world.event("pipeline:init_parts")
    update = world.event("pipeline:part_update")
    assert init[0]["filename"] == update["part_name"] == "abc123"


def test_unsupported_input_is_refused_without_starting_a_browser(world):
    result = world.run("https://evil.example/fitgirl-repacks.site/x")
    assert result.status == "failed"
    assert world.engines_made == 0
    assert "pipeline:error" in world.names()


def test_finished_direct_links_are_refused_with_a_clear_message(world):
    world.run("https://dl.fuckingfast.co/dl/abc#a.rar")
    assert "already" in world.event("pipeline:error")["message"].lower()


def test_a_page_with_no_mirrors_reports_an_error(world):
    world.game_page = ([], "Some Game", "")
    assert world.run().status == "failed"
    assert world.engines_made == 0


def test_the_fuckingfast_mirror_is_preferred(world):
    other = "https://paste.fitgirl-repacks.site/?other#key"
    world.game_page = (
        [{"hoster": "DataNodes", "url": other, "label": "DN"}, {"hoster": "FuckingFast", "url": PASTE, "label": "FF"}],
        "Some Game", "",
    )
    world.run()
    assert world.pastebins_opened == [PASTE]


def test_engine_messages_reach_the_ui_log(world):
    world.run()
    assert world.event("pipeline:log")["message"] == "engine says hello"


def test_a_crash_in_the_engine_is_reported_not_swallowed(world):
    def explode(concurrency):
        raise RuntimeError("Browser failed to start")

    world.make_engine = explode
    assert world.run().status == "failed"
    assert "Browser failed to start" in world.event("pipeline:error")["message"]


# Pastebin runs can find a cached copy partway through


def existing(is_expired=False):
    return {"exists": True, "is_expired": is_expired, "record": {"slug": "some-game", "age_str": "1 hour ago", "urls": ["x"]}}


def test_choosing_the_cached_copy_stops_the_run_quietly(world):
    world.existing = existing()
    world.duplicate_answer = "instant"
    assert world.run(PASTE).status == "cancelled"
    assert_nothing_kept(world)
    assert world.event("pipeline:cancelled")["reason"] == "instant"


def test_closing_the_duplicate_dialog_cancels_the_run(world):
    world.existing = existing()
    world.duplicate_answer = "cancel"
    assert world.run(PASTE).status == "cancelled"
    assert_nothing_kept(world)
    assert world.event("pipeline:cancelled")["reason"] == "user"


def test_choosing_fresh_continues_the_run(world):
    world.existing = existing()
    world.duplicate_answer = "fresh"
    assert world.run(PASTE).status == "complete"


def test_an_expired_copy_is_replaced_without_asking(world):
    world.existing = existing(is_expired=True)
    assert world.run(PASTE).status == "complete"
    assert world.duplicate_questions == []


def test_force_fresh_never_asks(world):
    world.existing = existing()
    assert world.run(PASTE, force_fresh=True).status == "complete"
    assert world.duplicate_questions == []


def test_status_names_are_exactly_what_the_ui_expects():
    assert pipeline.COMPLETE == "complete"
    assert pipeline.PARTIAL == "partial"
