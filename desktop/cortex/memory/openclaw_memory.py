import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class OpenClawMemory:
    """Three-tier memory engine integrating Markdown storage with SQLite FTS5 search."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.memory_file = self.base_dir / "MEMORY.md"
        self.daily_dir = self.base_dir / "daily"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "fts_index.db"
        self._last_mtime: float = 0.0
        self._init_fts()

    def _init_fts(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    source,
                    section,
                    content,
                    tokenize='porter unicode61'
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );
            """)
            conn.commit()

    def sync_if_modified(self) -> None:
        if not self.memory_file.exists():
            return
        current_mtime = os.path.getmtime(self.memory_file)
        if current_mtime > self._last_mtime:
            self._reindex_memory_file()
            self._last_mtime = current_mtime

    def _reindex_memory_file(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_fts WHERE source = 'MEMORY.md'")
            text = self.memory_file.read_text(encoding="utf-8")
            raw_sections = text.split("\n## ")
            
            for section in raw_sections:
                if not section.strip():
                    continue
                lines = section.split("\n", 1)
                header = lines[0].replace("#", "").strip()
                body = lines[1].strip() if len(lines) > 1 else ""
                
                conn.execute(
                    "INSERT INTO memory_fts (source, section, content) VALUES (?, ?, ?)",
                    ("MEMORY.md", header, f"## {header}\n{body}")
                )
            conn.commit()

    @staticmethod
    def _sanitize_message(text: str) -> str:
        if not text:
            return ""
        clean = re.sub(r'\[?[A-Za-z]*[Ll]ombok[A-Za-z0-9;:_<>#\s\-]*\]?>*', '', text)
        clean = re.sub(r'ombok;>*(?:glow:[^>]+>)?(?:mood:[^;\n]+;)?', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\[[^\]]*(?:mood|glow|eye|intensity)[^\]]*\]', '', clean, flags=re.IGNORECASE)
        return clean.strip()

    def append_daily_log(self, action: str, details: str) -> None:
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.daily_dir / f"{today_str}.md"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        clean_details = self._sanitize_message(details)
        entry = f"\n### [{timestamp}] {action}\n{clean_details}\n"
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(entry)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memory_fts (source, section, content) VALUES (?, ?, ?)",
                (f"daily/{today_str}.md", action, entry.strip())
            )
            conn.commit()

    def search_memory(self, query: str, limit: int = 4) -> List[str]:
        self.sync_if_modified()
        sanitized_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not sanitized_query:
            return []

        formatted_query = " OR ".join(sanitized_query.split())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT content FROM memory_fts 
                WHERE memory_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (formatted_query, limit))
            return [row[0] for row in cursor.fetchall()]

    def get_grounding_context(self) -> str:
        self.sync_if_modified()
        if not self.memory_file.exists():
            return "No persistent memory available."
        return self.memory_file.read_text(encoding="utf-8")

    def save_fact(self, category: str, key: str, value: str):
        """Append or update fact in MEMORY.md and log to daily."""
        self.sync_if_modified()
        entry = f"- **{key}**: {value} (Category: {category})"
        text = self.memory_file.read_text(encoding="utf-8") if self.memory_file.exists() else "# Cortex Root Knowledge Base\n"
        
        if "## System Knowledge" not in text:
            text += "\n## System Knowledge\n"
        text += f"\n{entry}\n"
        
        self.memory_file.write_text(text, encoding="utf-8")
        self.sync_if_modified()
        self.append_daily_log(f"Saved Fact: {category}/{key}", value)

    def add_message(self, role: str, content: str, session_id: str = "default"):
        clean_content = self._sanitize_message(content)
        if not clean_content:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM session_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,)
            )
            last = cursor.fetchone()
            if last and last[0] == role and last[1].strip() == clean_content:
                return

            cursor.execute(
                "INSERT INTO session_messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, clean_content, datetime.now().timestamp())
            )
            conn.commit()

    def get_recent_history(self, session_id: str = "default", limit: int = 8) -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content FROM (
                    SELECT id, role, content FROM session_messages
                    WHERE session_id = ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
            """, (session_id, limit * 2))
            rows = cursor.fetchall()

        history: List[Dict[str, str]] = []
        for role, content in rows:
            clean_c = self._sanitize_message(content)
            if not clean_c:
                continue
            if history and history[-1]["role"] == role and history[-1]["content"] == clean_c:
                continue
            history.append({"role": role, "content": clean_c})
        return history[-limit:]

    def clear_session(self, session_id: str = "default"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
            conn.commit()
