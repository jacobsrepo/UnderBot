"""
Cortex Persistent Conversation Memory
Stores all dialogue turns, timestamps, and sessions in a local SQLite database.
"""

import sqlite3
import time
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cortex_memory.db")


class ConversationMemory:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_time ON messages (session_id, timestamp)
            """)
            conn.commit()

    def add_message(self, role: str, content: str, session_id: str = "default"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, time.time())
            )
            conn.commit()

    def get_recent_history(self, limit: int = 20, session_id: str = "default") -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            # Return in chronological order
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def clear_session(self, session_id: str = "default"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()
