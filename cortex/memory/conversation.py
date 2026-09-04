"""
Cortex Persistent Conversation Memory
Stores sanitized dialogue turns, timestamps, and sessions in a local SQLite database,
with real-time temporal and environmental system grounding.
"""

import sqlite3
import time
import datetime
import os
import platform
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

    @staticmethod
    def get_grounding_context() -> str:
        """
        Dynamically returns current real-world timestamp, day, timezone, and OS context.
        Injected into the agent prompt on every turn to prevent time/date hallucinations.
        """
        now = datetime.datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        tz_str = time.tzname[time.daylight] if time.daylight else time.tzname[0]
        
        return (
            f"[LIVE SYSTEM GROUNDING]\n"
            f"- Current Date: {date_str} ({day_name})\n"
            f"- Current Time: {time_str} ({tz_str})\n"
            f"- Host OS: {platform.system()} {platform.release()} (Windows PowerShell 7 / Desktop)\n"
            f"- Working Directory: {os.path.abspath(os.path.dirname(os.path.dirname(__file__)))}\n"
        )

    def add_message(self, role: str, content: str, session_id: str = "default"):
        clean_content = content.strip()
        if not clean_content:
            return

        # Anti-corrupted-echo filter: do not persist template placeholders or repetitive canned replies
        lower = clean_content.lower()
        if "[insert current time" in lower or "[insert" in lower:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, clean_content, time.time())
            )
            conn.commit()

    def get_recent_history(self, limit: int = 15, session_id: str = "default") -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def clear_session(self, session_id: str = "default"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()

    def purge_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            conn.commit()
