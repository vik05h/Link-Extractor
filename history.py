"""Embedded SQLite archive of past extractions."""

import json
import os
import sqlite3
import time
from contextlib import closing
from typing import Any, Dict, List, Optional

import game_records
import links
import utils


def get_db_path() -> str:
    """Location of the history database."""
    return os.path.join(utils.get_app_data_dir(), "history.db")


class HistoryManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source_url TEXT,
                    timestamp TEXT NOT NULL,
                    total_parts INTEGER NOT NULL,
                    resolved_count INTEGER NOT NULL,
                    total_size_bytes INTEGER DEFAULT 0,
                    total_size_str TEXT DEFAULT '0 B',
                    urls_json TEXT NOT NULL
                )
            """)

    def add_record(
        self,
        title: str,
        source_url: str,
        total_parts: int,
        resolved_count: int,
        total_size_bytes: int = 0,
        total_size_str: str = "0 B",
        urls: Optional[List[str]] = None,
    ) -> int:
        """Add an extraction, or update the record for the same source or the same named game."""
        clean_title = title.strip() or "FitGirl Repack Download"
        clean_source = (source_url or "").strip()
        urls_json = json.dumps(links.with_filename_fragments(urls or [], clean_title))
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # Placeholder titles like "Direct Repack" say nothing about the game, so they
        # must never make two different extractions look like the same one.
        match_title = "" if game_records.is_generic_title(clean_title) else clean_title
        values = (clean_title, clean_source, now, total_parts, resolved_count, total_size_bytes, total_size_str, urls_json)

        with closing(self._connect()) as connection, connection:
            existing = connection.execute(
                """
                SELECT id FROM extractions
                WHERE (source_url = ? AND source_url != '') OR (title = ? AND title != '')
                ORDER BY id DESC LIMIT 1
                """,
                (clean_source, match_title),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE extractions SET
                        title = ?, source_url = ?, timestamp = ?, total_parts = ?,
                        resolved_count = ?, total_size_bytes = ?, total_size_str = ?, urls_json = ?
                    WHERE id = ?
                    """,
                    (*values, existing["id"]),
                )
                return existing["id"]

            cursor = connection.execute(
                """
                INSERT INTO extractions (
                    title, source_url, timestamp, total_parts,
                    resolved_count, total_size_bytes, total_size_str, urls_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            return cursor.lastrowid or 0

    def get_records(self, search_query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Newest records first, optionally filtered by title or URL."""
        query = search_query.strip()
        with closing(self._connect()) as connection:
            if query:
                pattern = f"%{query}%"
                rows = connection.execute(
                    "SELECT * FROM extractions WHERE title LIKE ? OR source_url LIKE ? ORDER BY id DESC LIMIT ?",
                    (pattern, pattern, limit),
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM extractions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        try:
            item["urls"] = links.with_filename_fragments(json.loads(item["urls_json"]), item["title"])
        except (TypeError, ValueError):
            item["urls"] = []
        return item

    def delete_record(self, record_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            return connection.execute("DELETE FROM extractions WHERE id = ?", (record_id,)).rowcount > 0
