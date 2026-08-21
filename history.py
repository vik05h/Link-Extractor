import os
import sys
import json
import sqlite3
import time
import re
from typing import List, Dict, Any, Optional


def get_app_data_dir() -> str:
    """Get persistent user data directory for database and configuration."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA')
        if app_data:
            dir_path = os.path.join(app_data, 'FitGirlLinkExtractor')
            os.makedirs(dir_path, exist_ok=True)
            return dir_path
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_db_path() -> str:
    """Get location for history SQLite database."""
    return os.path.join(get_app_data_dir(), "history.db")


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
            # Auto-cleanup any preexisting duplicate records by title, keeping the newest entry
            conn.execute("""
                DELETE FROM extractions
                WHERE id NOT IN (
                    SELECT MAX(id) FROM extractions GROUP BY title
                )
            """)
            conn.commit()

    def _ensure_url_hashes(self, urls: List[str], title: str) -> List[str]:
        """Ensure all URLs have #filename.rar fragments."""
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title).strip('_') or "FitGirl_Repack"
        formatted = []
        for i, u in enumerate(urls):
            clean = u.strip()
            if not clean:
                continue
            if "#" in clean:
                formatted.append(clean)
            else:
                formatted.append(f"{clean}#{safe_title}.part{i+1:03d}.rar")
        return formatted

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
        """Add or update an extraction record in database without duplicates."""
        clean_title = title.strip() or "FitGirl Repack Download"
        formatted_urls = self._ensure_url_hashes(urls or [], clean_title)
        urls_json = json.dumps(formatted_urls)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if matching record exists by title or source_url
            cursor.execute("""
                SELECT id FROM extractions
                WHERE title = ? OR (source_url = ? AND source_url != '')
                ORDER BY id DESC LIMIT 1
            """, (clean_title, source_url.strip() if source_url else ""))
            existing = cursor.fetchone()

            if existing:
                rec_id = existing[0]
                cursor.execute("""
                    UPDATE extractions SET
                        title = ?,
                        source_url = ?,
                        timestamp = ?,
                        total_parts = ?,
                        resolved_count = ?,
                        total_size_bytes = ?,
                        total_size_str = ?,
                        urls_json = ?
                    WHERE id = ?
                """, (
                    clean_title, source_url, now_str, total_parts,
                    resolved_count, total_size_bytes, total_size_str, urls_json,
                    rec_id
                ))
                conn.commit()
                return rec_id
            else:
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
                    raw_urls = json.loads(item["urls_json"])
                    item["urls"] = self._ensure_url_hashes(raw_urls, item["title"])
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
                    raw_urls = json.loads(item["urls_json"])
                    item["urls"] = self._ensure_url_hashes(raw_urls, item["title"])
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
