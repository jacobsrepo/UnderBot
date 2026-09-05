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
    def get_grounding_context(
        hw_status: Optional[Dict[str, Any]] = None,
        camera_active: bool = False,
        learned_facts: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Dynamically returns current real-world timestamp, day, timezone, OS context,
        real-time physical hardware connection status, and persistent knowledge.
        Injected into the agent prompt on every turn to prevent time/date/hardware hallucinations.
        """
        now = datetime.datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        tz_str = time.tzname[time.daylight] if time.daylight else time.tzname[0]

        hw_lines = ""
        if hw_status:
            is_conn = hw_status.get("connected", False)
            port = hw_status.get("port") or "COM4"
            dev = hw_status.get("device", "Arduino Nano")
            detail = hw_status.get("status", "Online" if is_conn else "Offline")
            if is_conn:
                hw_lines = (
                    f"- Physical Hardware Status: CONNECTED (ONLINE)\n"
                    f"- Active Microcontroller: {dev} on {port}\n"
                    f"- Hardware Connection Detail: {detail}\n"
                )
            else:
                hw_lines = (
                    f"- Physical Hardware Status: DISCONNECTED (No USB microcontroller detected)\n"
                    f"- Scanned Ports: None active\n"
                )

        cam_line = (
            f"- Camera Sensor Status: {'ACTIVE (Streaming live video from user)' if camera_active else 'OFF / INACTIVE (No video feed from user)'}\n"
            f"- Camera Ground Truth: {'Webcam is active and streaming live video.' if camera_active else 'The webcam is currently turned OFF. You CANNOT see through the camera. Note: You CANNOT turn on the webcam remotely; only the user can enable their camera in the browser UI. Never offer to turn on the camera yourself.'}\n"
        )

        facts_block = ""
        if learned_facts:
            f_lines = "\n".join([f"  * {k}: {v}" for k, v in learned_facts.items()])
            facts_block = f"- Persistent Long-Term Memory:\n{f_lines}\n"

        return (
            f"[LIVE SYSTEM GROUNDING]\n"
            f"- Current Date: {date_str} ({day_name})\n"
            f"- Current Time: {time_str} ({tz_str})\n"
            f"- Host OS: {platform.system()} {platform.release()} (Windows PowerShell 7 / Desktop)\n"
            f"{hw_lines}"
            f"{cam_line}"
            f"{facts_block}"
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

            # Prevent storing exact duplicate consecutive assistant messages
            if role == "assistant":
                cursor.execute(
                    "SELECT content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (session_id,)
                )
                last_row = cursor.fetchone()
                if last_row and last_row[0].strip().lower() == clean_content.lower():
                    # Skip duplicate identical message
                    return

            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, clean_content, time.time())
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10, session_id: str = "default") -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Fetch up to 2x limit to allow deduplication of repetitive boilerplate
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit * 2)
            )
            rows = cursor.fetchall()

        # Deduplicate consecutive repetitive assistant messages
        deduped = []
        last_assistant_snippet = ""
        for r in rows:
            role, content = r[0], r[1]
            if role == "assistant":
                # Check for repetitive identical prefix or exact duplicate
                snippet = content[:60].strip().lower()
                if snippet and snippet == last_assistant_snippet:
                    # Skip duplicate assistant response to prevent autoregressive looping
                    continue
                last_assistant_snippet = snippet
            else:
                last_assistant_snippet = ""
            deduped.append({"role": role, "content": content})
            if len(deduped) >= limit:
                break

        return list(reversed(deduped))

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
