import os
import sqlite3

import pytest

from history import HistoryManager

LINK_A = "https://dl.fuckingfast.co/a#a.rar"
LINK_B = "https://dl.fuckingfast.co/b#b.rar"


@pytest.fixture
def db_path(tmp_path):
    return os.path.join(str(tmp_path), "history.db")


@pytest.fixture
def manager(db_path):
    return HistoryManager(db_path)


def add(manager, title="A Game", source="https://fitgirl-repacks.site/a-game/", urls=None, total=None):
    urls = [LINK_A] if urls is None else urls
    return manager.add_record(
        title=title, source_url=source, total_parts=total or len(urls), resolved_count=len(urls), urls=urls
    )


def test_two_different_direct_extractions_are_both_kept(manager):
    add(manager, "Direct Repack", "https://fuckingfast.co/a", [LINK_A])
    add(manager, "Direct Repack", "https://fuckingfast.co/b", [LINK_B])
    assert sorted(row["source_url"] for row in manager.get_records()) == [
        "https://fuckingfast.co/a",
        "https://fuckingfast.co/b",
    ]


def test_same_title_records_survive_a_restart(db_path, manager):
    add(manager, "Direct Repack", "https://fuckingfast.co/a", [LINK_A])
    add(manager, "Direct Repack", "https://fuckingfast.co/b", [LINK_B])
    assert len(HistoryManager(db_path).get_records()) == 2


def test_extracting_the_same_game_again_updates_its_record(manager):
    add(manager, urls=[LINK_A])
    add(manager, urls=[LINK_B])
    rows = manager.get_records()
    assert len(rows) == 1
    assert rows[0]["urls"] == [LINK_B]


def test_a_named_game_reached_a_different_way_updates_its_record(manager):
    add(manager, "Foo Bar", "https://paste.fitgirl-repacks.site/?a#b")
    add(manager, "Foo Bar", "https://fitgirl-repacks.site/foo-bar/")
    assert len(manager.get_records()) == 1


def test_partial_runs_keep_both_counts(manager):
    add(manager, urls=[LINK_A], total=3)
    row = manager.get_records()[0]
    assert (row["total_parts"], row["resolved_count"]) == (3, 1)


def test_links_get_filenames_when_missing(manager):
    add(manager, "Some Game", urls=["https://dl.fuckingfast.co/a"])
    assert manager.get_records()[0]["urls"] == ["https://dl.fuckingfast.co/a#Some_Game.part001.rar"]


def test_search_finds_by_title_and_url(manager):
    add(manager, "Foo Bar", "https://fitgirl-repacks.site/foo-bar/")
    add(manager, "Other", "https://fitgirl-repacks.site/other/")
    assert [row["title"] for row in manager.get_records("Foo")] == ["Foo Bar"]
    assert [row["title"] for row in manager.get_records("other/")] == ["Other"]


def test_sql_in_titles_and_searches_is_treated_as_text(manager, db_path):
    title = "Game'); DROP TABLE extractions; --"
    add(manager, title)
    assert [row["title"] for row in manager.get_records("DROP TABLE")] == [title]
    assert manager.get_records("' OR '1'='1") == []
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM extractions").fetchone()[0] == 1


def test_records_can_be_deleted(manager):
    record_id = add(manager)
    assert manager.delete_record(record_id) is True
    assert manager.get_records() == []


def test_the_database_file_is_not_left_locked(db_path, manager):
    add(manager)
    manager.get_records()
    os.remove(db_path)
    assert not os.path.exists(db_path)
