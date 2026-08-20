import os
import sys
import json
import sqlite3
import time
from typing import List, Dict, Any, Optional


def get_db_path() -> str:
    """Get location for history SQLite database."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "history.db")


class HistoryManager:
    """
    Embedded SQLite manager for extraction history and saved game downloads.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
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
            conn.commit()

    def add_record(
        self,
        title: str,
        source_url: str,
        total_parts: int,
        resolved_count: int,
        total_size_bytes: int = 0,
        total_size_str: str = "0 B",
        urls: Optional[List[str]] = None
    ) -> int:
        """Add a new extraction record to database."""
        clean_title = title.strip() or "FitGirl Repack Download"
        urls_json = json.dumps(urls or [])
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO extractions (
                    title, source_url, timestamp, total_parts,
                    resolved_count, total_size_bytes, total_size_str, urls_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clean_title, source_url, now_str, total_parts,
                resolved_count, total_size_bytes, total_size_str, urls_json
            ))
            conn.commit()
            return cursor.lastrowid

    def get_records(self, search_query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve extraction records, optionally filtered by title or URL."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search_query.strip():
                pattern = f"%{search_query.strip()}%"
                cursor.execute("""
                    SELECT * FROM extractions
                    WHERE title LIKE ? OR source_url LIKE ?
                    ORDER BY id DESC LIMIT ?
                """, (pattern, pattern, limit))
            else:
                cursor.execute("""
                    SELECT * FROM extractions
                    ORDER BY id DESC LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["urls"] = json.loads(item["urls_json"])
                except Exception:
                    item["urls"] = []
                results.append(item)
            return results

    def get_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single record by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM extractions WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                item = dict(row)
                try:
                    item["urls"] = json.loads(item["urls_json"])
                except Exception:
                    item["urls"] = []
                return item
            return None

    def delete_record(self, record_id: int) -> bool:
        """Delete a record by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM extractions WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_history(self) -> bool:
        """Clear all records from database."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM extractions")
            conn.commit()
            return True
