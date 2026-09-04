"""
tool_registry.py — Cortex Unified Tool Registry
OpenClaw-style JSON-schema tool definitions wrapping every subsystem.
The Brain picks tools by name; this module executes them safely.
"""

import asyncio
import subprocess
import os
import re
import shlex
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable

# ─────────────────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# JSON Schema compatible. These are sent to the LLM as available tools.
# ─────────────────────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "minimize_windows",
            "description": "Minimize all open desktop windows to the taskbar (show desktop).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restore_windows",
            "description": "Restore/unminimize all previously minimized desktop windows.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_desktop",
            "description": "Organize and sort files on the user's desktop into categorized folders.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_app",
            "description": "Launch a desktop application by name (e.g. 'chrome', 'notepad', 'vscode', 'spotify').",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the application to launch."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Capture and OCR the current desktop screen. Returns extracted text visible on screen.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_metrics",
            "description": "Get current system telemetry: CPU %, RAM usage, battery level, disk usage.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal",
            "description": "Execute a shell command in a sandboxed PowerShell terminal. Returns stdout/stderr. "
                           "Use for file operations, script execution, git, pip install, etc. "
                           "NEVER run destructive commands (format, rm -rf, del /F /S) without explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute."},
                    "cwd": {"type": "string", "description": "Working directory (optional, defaults to user home)."},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30, max 120)."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_boards",
            "description": "Detect and list all connected microcontrollers (Arduino, ESP32, etc.) and their COM ports.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "program_board",
            "description": "Generate, compile, and upload firmware to a connected Arduino or ESP32. "
                           "Automatically retries with LLM-based error correction on compile failures. "
                           "Use this for any 'blink', 'sensor read', 'servo control', 'motor', etc. requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "What the firmware should do (plain English)."},
                    "board_hint": {"type": "string", "description": "Board type hint: 'nano', 'uno', 'esp32', or 'auto'."}
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_serial",
            "description": "Send a string command or data over the active serial connection to the microcontroller.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data string to send over serial."}
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_visual",
            "description": "Analyze an image from camera or screen capture. Returns a description of what is visible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["screen", "camera"], "description": "Which source to inspect."},
                    "question": {"type": "string", "description": "What to look for or describe."}
                },
                "required": ["source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search past conversation history for relevant context on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in past conversations."},
                    "limit": {"type": "integer", "description": "Max number of results (default 3)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file on the filesystem (creates parent dirs if needed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to."},
                    "content": {"type": "string", "description": "Text content to write."},
                    "append": {"type": "boolean", "description": "If true, append instead of overwrite (default false)."}
                },
                "required": ["path", "content"]
            }
        }
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DANGEROUS COMMAND PATTERNS
# ─────────────────────────────────────────────────────────────────────────────
_BLOCKED_PATTERNS = [
    r"rm\s+-rf", r"del\s+/[fFsS]", r"format\s+[a-zA-Z]:",
    r"rd\s+/[sS]", r"Remove-Item.*-Recurse.*-Force",
    r"diskpart", r"shutdown\s+/[sfr]", r"taskkill.*explorer",
    r"reg\s+delete", r"bcdedit", r"fdisk", r"mkfs\.", r"dd\s+if=",
]

def _is_safe_command(cmd: str) -> tuple[bool, str]:
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False, f"Blocked dangerous pattern: {pattern}"
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# TOOL REGISTRY CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Unified tool registry for Cortex.
    Wraps desktop, embedded, vision, memory, and terminal subsystems
    as named, schema-validated async callables.
    """

    def __init__(self, desktop, embedded, vision, memory, camera=None):
        self.desktop = desktop
        self.embedded = embedded
        self.vision = vision
        self.memory = memory
        self.camera = camera

    @property
    def schemas(self) -> List[Dict]:
        return TOOL_SCHEMAS

    async def dispatch(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given args.
        Returns: {"success": bool, "result": Any, "error": str|None}
        """
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                return {"success": False, "result": None, "error": f"Unknown tool: {tool_name}"}
            result = await handler(**args)
            return {"success": True, "result": result, "error": None}
        except Exception as e:
            return {"success": False, "result": None, "error": str(e)}

    # ─── Desktop Tools ───────────────────────────────────────────────────────

    async def _tool_minimize_windows(self) -> str:
        res = await asyncio.to_thread(self.desktop.minimize_all_windows)
        return "All windows minimized." if res.get("success") else res.get("error", "Failed.")

    async def _tool_restore_windows(self) -> str:
        res = await asyncio.to_thread(self.desktop.undo_minimize_all)
        return "Windows restored." if res.get("success") else res.get("error", "Failed.")

    async def _tool_organize_desktop(self) -> str:
        res = await asyncio.to_thread(self.desktop.organize_desktop_files)
        moved = res.get("moved_count", 0)
        return f"Organized desktop: {moved} files categorized."

    async def _tool_launch_app(self, app_name: str) -> str:
        res = await asyncio.to_thread(self.desktop.launch_application, app_name)
        if res.get("success"):
            return f"Launched {app_name}."
        return f"Could not launch {app_name}: {res.get('error', 'unknown error')}"

    async def _tool_read_screen(self) -> str:
        text = await asyncio.to_thread(self.desktop.capture_screen_context)
        if text:
            return f"Screen OCR:\n{text[:2000]}"
        return "Screen captured but no readable text found."

    async def _tool_get_system_metrics(self) -> str:
        m = await asyncio.to_thread(self.desktop.get_system_metrics)
        return (
            f"CPU: {m.get('cpu_percent')}% | "
            f"RAM: {m.get('ram_used_gb')}/{m.get('ram_total_gb')} GB ({m.get('ram_percent')}%) | "
            f"Battery: {m.get('battery', 'N/A')} | "
            f"Disk: {m.get('disk_used_gb', '?')}/{m.get('disk_total_gb', '?')} GB"
        )

    # ─── Terminal Tool ────────────────────────────────────────────────────────

    async def _tool_run_terminal(self, command: str, cwd: str = None, timeout: int = 30) -> str:
        is_safe, reason = _is_safe_command(command)
        if not is_safe:
            return f"[BLOCKED] {reason}. Confirm with the user before executing."

        timeout = min(int(timeout or 30), 120)
        effective_cwd = cwd or os.path.expanduser("~")

        def _run():
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                    capture_output=True, text=True, timeout=timeout,
                    cwd=effective_cwd if os.path.isdir(effective_cwd) else None
                )
                out = result.stdout.strip()
                err = result.stderr.strip()
                if out and err:
                    return f"STDOUT:\n{out[:3000]}\n\nSTDERR:\n{err[:500]}"
                return out or err or "(No output)"
            except subprocess.TimeoutExpired:
                return f"[TIMEOUT] Command exceeded {timeout}s limit."
            except Exception as e:
                return f"[ERROR] {e}"

        return await asyncio.to_thread(_run)

    # ─── Embedded Hardware Tools ──────────────────────────────────────────────

    async def _tool_list_boards(self) -> str:
        boards = await asyncio.to_thread(self.embedded.detect_boards)
        if not boards:
            return "No connected microcontrollers detected."
        lines = []
        for b in boards:
            lines.append(f"{b.get('port')} — {b.get('board_type', 'Unknown')} ({b.get('chip', '')})")
        return "Connected boards:\n" + "\n".join(lines)

    async def _tool_program_board(self, prompt: str, board_hint: str = "auto") -> str:
        def _flash():
            return self.embedded.auto_compile_flash_with_reflection(
                prompt=prompt,
                board_hint=board_hint or "auto",
                progress_cb=None,
                code_reflector_cb=None
            )
        res = await asyncio.to_thread(_flash)
        if res.get("success"):
            board = res.get("board", "board")
            port = res.get("port", "?")
            retries = res.get("reflection_attempts", 0)
            msg = f"Firmware uploaded to {board} on {port}."
            if retries:
                msg += f" ({retries} compile fix(es) applied)"
            return msg
        return f"Flash failed: {res.get('error', 'unknown')}"

    async def _tool_send_serial(self, data: str) -> str:
        res = await asyncio.to_thread(self.embedded.send_serial_data, data)
        return "Sent." if res.get("success") else f"Serial error: {res.get('error')}"

    # ─── Vision Tool ─────────────────────────────────────────────────────────

    async def _tool_inspect_visual(self, source: str = "screen", question: str = "") -> str:
        if source == "camera" and self.camera:
            img_b64 = await asyncio.to_thread(self.camera.capture_frame_b64)
        else:
            img_b64 = None  # vision_engine.inspect_visual_target handles screen fallback

        result = await asyncio.to_thread(
            self.vision.inspect_visual_target,
            img_b64,
            question or "Describe what you see."
        )
        return result or "Visual inspection returned no data."

    # ─── Memory Tool ─────────────────────────────────────────────────────────

    async def _tool_recall_memory(self, query: str, limit: int = 3) -> str:
        results = await asyncio.to_thread(self.memory.recall, query, int(limit))
        if not results:
            return "No relevant memories found."
        out = []
        for r in results:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["timestamp"]))
            out.append(f"[{ts}] ({r['role']}): {r['content'][:200]}")
        return "Recalled memories:\n" + "\n".join(out)

    # ─── File Tools ──────────────────────────────────────────────────────────

    async def _tool_read_file(self, path: str) -> str:
        def _read():
            expanded = os.path.expandvars(os.path.expanduser(path))
            if not os.path.isfile(expanded):
                return f"File not found: {expanded}"
            size = os.path.getsize(expanded)
            if size > 100_000:
                return f"File too large ({size} bytes). Read first 10000 chars only:\n" + \
                       open(expanded, "r", errors="replace").read(10000)
            return open(expanded, "r", errors="replace").read()
        return await asyncio.to_thread(_read)

    async def _tool_write_file(self, path: str, content: str, append: bool = False) -> str:
        def _write():
            expanded = os.path.expandvars(os.path.expanduser(path))
            os.makedirs(os.path.dirname(os.path.abspath(expanded)), exist_ok=True)
            mode = "a" if append else "w"
            with open(expanded, mode, encoding="utf-8") as f:
                f.write(content)
            return f"Written to {expanded} ({len(content)} chars)."
        return await asyncio.to_thread(_write)
