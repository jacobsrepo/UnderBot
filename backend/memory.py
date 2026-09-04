"""
memory.py — Cortex Persistent Memory Engine
SQLite-backed long-term conversation store.
Every exchange is recorded permanently and recalled on startup.
"""

import os
import re
import sqlite3
import time
import json
import threading
from typing import List, Dict, Any, Optional

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory.db")


class Memory:
    """
    Persistent long-term memory for Cortex.
    - Stores every user/assistant exchange permanently to SQLite.
    - Provides recent history for conversation context (rolling window).
    - Provides semantic recall: keyword search over all past interactions.
    - Thread-safe writes with a single shared connection.
    """

    def __init__(self, db_path: str = _DB_PATH, session_id: str = "default"):
        self.db_path = db_path
        self.session_id = session_id
        self._lock = threading.Lock()
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    role        TEXT    NOT NULL,
                    content     TEXT    NOT NULL,
                    tool_calls  TEXT,
                    tool_name   TEXT,
                    timestamp   REAL    NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_ts
                ON conversations (session_id, timestamp)
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
                USING fts5(content, session_id UNINDEXED)
            """)
        return conn

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def record(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_name: Optional[str] = None
    ):
        """Persist a single conversation turn."""
        ts = time.time()
        tc_json = json.dumps(tool_calls) if tool_calls else None
        with self._lock:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO conversations (session_id, role, content, tool_calls, tool_name, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (self.session_id, role, content, tc_json, tool_name, ts)
                )
                row_id = cur.lastrowid
                self._conn.execute(
                    "INSERT INTO conversations_fts (rowid, content, session_id) VALUES (?, ?, ?)",
                    (row_id, content, self.session_id)
                )

    def record_exchange(self, user_text: str, assistant_text: str, tool_name: Optional[str] = None):
        """Convenience: record a user + assistant pair atomically."""
        self.record("user", user_text)
        self.record("assistant", assistant_text, tool_name=tool_name)

    # ------------------------------------------------------------------
    # READ — recent history
    # ------------------------------------------------------------------

    def get_recent(self, n_turns: int = 20) -> List[Dict[str, str]]:
        """
        Returns the last n_turns of this session as OpenAI-format messages.
        Tool calls are embedded as text in the assistant role for compatibility.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content, tool_calls FROM conversations "
                "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (self.session_id, n_turns * 2)
            ).fetchall()

        messages = []
        for row in reversed(rows):
            content = row["content"]
            if row["tool_calls"]:
                try:
                    tc = json.loads(row["tool_calls"])
                    content = f"{content}\n[Tool Calls: {json.dumps(tc)}]"
                except Exception:
                    pass
            messages.append({"role": row["role"], "content": content})
        return messages

    # ------------------------------------------------------------------
    # READ — semantic recall
    # ------------------------------------------------------------------

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Full-text search over all past conversations (all sessions).
        Returns the most relevant past exchanges for context injection.
        """
        # Build FTS query — simple tokenize + quote
        tokens = re.sub(r"[^\w\s]", "", query).split()
        if not tokens:
            return []
        fts_query = " OR ".join(tokens)

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT c.role, c.content, c.session_id, c.timestamp, c.tool_name
                FROM conversations c
                JOIN conversations_fts f ON c.rowid = f.rowid
                WHERE conversations_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit)
            ).fetchall()

        results = []
        for row in rows:
            results.append({
                "role": row["role"],
                "content": row["content"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "tool_name": row["tool_name"],
            })
        return results

    # ------------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            sessions = self._conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM conversations"
            ).fetchone()[0]
            oldest = self._conn.execute(
                "SELECT MIN(timestamp) FROM conversations"
            ).fetchone()[0]
        return {
            "total_messages": total,
            "total_sessions": sessions,
            "oldest_memory_ts": oldest,
            "db_path": self.db_path,
        }

    def get_all_sessions(self) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT session_id FROM conversations ORDER BY MAX(timestamp) DESC"
            ).fetchall()
        return [r["session_id"] for r in rows]

    def close(self):
        with self._lock:
            self._conn.close()
