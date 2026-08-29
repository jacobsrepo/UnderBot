"""
Cortex Persistent Long-Term Knowledge Memory
Stores hardware pin mappings, user notes, and learned facts across server restarts.
"""

import sqlite3
import time
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cortex_memory.db")


class KnowledgeMemory:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(category, key)
                )
            """)
            conn.commit()

    def save_fact(self, category: str, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge (category, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (category, key, value, time.time()))
            conn.commit()

    def get_fact(self, category: str, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM knowledge WHERE category = ? AND key = ?",
                (category, key)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_category_facts(self, category: str) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value FROM knowledge WHERE category = ?",
                (category,)
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def search_facts(self, query: str) -> List[Dict[str, str]]:
        q = f"%{query.lower()}%"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, key, value FROM knowledge
                WHERE LOWER(category) LIKE ? OR LOWER(key) LIKE ? OR LOWER(value) LIKE ?
                ORDER BY updated_at DESC LIMIT 20
            """, (q, q, q))
            return [{"category": r[0], "key": r[1], "value": r[2]} for r in cursor.fetchall()]

    def delete_fact(self, category: str, key: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge WHERE category = ? AND key = ?", (category, key))
            conn.commit()
