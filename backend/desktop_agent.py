import os
import sys
import shutil
import glob
import subprocess
import psutil
import io
import base64
import time
from typing import Dict, List, Optional, Any
from PIL import Image, ImageGrab

class DesktopAgent:
    """
    Windows Desktop OS Automation Engine for Contender.
    Provides file operations, application launching, system metrics,
    screen capture, and safe command execution.
    """

    KNOWN_APPS = {
        "vscode": ["code", "code.cmd", "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"],
        "visual studio code": ["code", "code.cmd", "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"],
        "chrome": ["chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"],
        "google chrome": ["chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
        "edge": ["msedge", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
        "windows terminal": ["wt.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "spotify": ["spotify.exe", "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Spotify\\Spotify.exe"],
        "task manager": ["taskmgr.exe"],
        "paint": ["mspaint.exe"]
    }

    def __init__(self):
        self.user_dir = os.path.expanduser("~")
        self.desktop_dir = os.path.join(self.user_dir, "Desktop")
        self.documents_dir = os.path.join(self.user_dir, "Documents")
        self.downloads_dir = os.path.join(self.user_dir, "Downloads")

    # ==================== SCREEN PERCEPTION ====================

    def capture_screen_base64(self, max_dim: int = 1280) -> Optional[str]:
        """
        Captures the primary desktop display and returns JPEG base64 string.
        """
        try:
            img = ImageGrab.grab()
            img.thumbnail((max_dim, int(max_dim * 9 / 16)))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            # Fallback if headless/session context
            return None

    # ==================== APPLICATION MANAGEMENT ====================

    def launch_application(self, app_name: str) -> Dict[str, Any]:
        """
        Launches a known desktop application or system executable.
        """
        clean_name = app_name.lower().strip()
        candidates = self.KNOWN_APPS.get(clean_name, [clean_name])

        for candidate in candidates:
            expanded = os.path.expandvars(candidate)
            try:
                if os.path.isfile(expanded) or shutil.which(candidate):
                    subprocess.Popen([expanded], shell=True)
                    return {
                        "success": True,
                        "app": app_name,
                        "message": f"Successfully launched {app_name}."
                    }
            except Exception:
                continue

        # Try generic start command in Windows
        try:
            subprocess.Popen(f'start "" "{clean_name}"', shell=True)
            return {
                "success": True,
                "app": app_name,
                "message": f"Executed start command for {app_name}."
            }
        except Exception as e:
            return {
                "success": False,
                "app": app_name,
                "error": f"Could not launch application '{app_name}': {str(e)}"
            }

    def open_path_or_url(self, target: str) -> Dict[str, Any]:
        """
        Opens a directory in File Explorer or a URL in the default browser.
        """
        try:
            expanded = os.path.expandvars(os.path.expanduser(target.strip()))
            os.startfile(expanded)
            return {"success": True, "target": target, "message": f"Opened {target}"}
        except Exception as e:
            return {"success": False, "target": target, "error": str(e)}

    # ==================== FILE SYSTEM OPERATIONS ====================

    def resolve_path(self, path_str: str) -> str:
        """Resolves friendly alias paths like Desktop, Documents, Downloads."""
        p = path_str.strip()
        if p.lower().startswith("desktop"):
            return os.path.join(self.desktop_dir, p[7:].lstrip("\\/"))
        elif p.lower().startswith("documents"):
            return os.path.join(self.documents_dir, p[9:].lstrip("\\/"))
        elif p.lower().startswith("downloads"):
            return os.path.join(self.downloads_dir, p[9:].lstrip("\\/"))
        return os.path.abspath(os.path.expandvars(os.path.expanduser(p)))

    def copy_file(self, src: str, dst: str) -> Dict[str, Any]:
        src_path = self.resolve_path(src)
        dst_path = self.resolve_path(dst)
        try:
            if os.path.isdir(dst_path):
                dst_path = os.path.join(dst_path, os.path.basename(src_path))
            shutil.copy2(src_path, dst_path)
            return {"success": True, "source": src_path, "destination": dst_path, "message": f"Copied {os.path.basename(src_path)} to destination."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, src: str, dst: str) -> Dict[str, Any]:
        src_path = self.resolve_path(src)
        dst_path = self.resolve_path(dst)
        try:
            shutil.move(src_path, dst_path)
            return {"success": True, "source": src_path, "destination": dst_path, "message": f"Moved {os.path.basename(src_path)} to destination."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        target = self.resolve_path(path)
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.isfile(target):
                os.remove(target)
            else:
                return {"success": False, "error": f"Path not found: {path}"}
            return {"success": True, "path": target, "message": f"Deleted {os.path.basename(target)}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_directory(self, path: str = "Desktop") -> Dict[str, Any]:
        target = self.resolve_path(path)
        try:
            if not os.path.exists(target):
                return {"success": False, "error": f"Directory does not exist: {path}"}

            items = []
            for item in os.listdir(target):
                full = os.path.join(target, item)
                is_dir = os.path.isdir(full)
                size_bytes = os.path.getsize(full) if not is_dir else 0
                items.append({
                    "name": item,
                    "is_dir": is_dir,
                    "size_kb": round(size_bytes / 1024, 1) if not is_dir else 0
                })

            return {"success": True, "directory": target, "items": items[:40], "count": len(items)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file_text(self, path: str, max_chars: int = 4000) -> Dict[str, Any]:
        target = self.resolve_path(path)
        try:
            if not os.path.isfile(target):
                return {"success": False, "error": f"File not found: {path}"}
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
            return {"success": True, "path": target, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file_text(self, path: str, content: str) -> Dict[str, Any]:
        target = self.resolve_path(path)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": target, "message": f"Wrote {len(content)} characters to {os.path.basename(target)}."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, query: str, search_dir: str = "Desktop") -> Dict[str, Any]:
        root = self.resolve_path(search_dir)
        matches = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                for f in filenames:
                    if query.lower() in f.lower():
                        matches.append(os.path.join(dirpath, f))
                        if len(matches) >= 20:
                            break
                if len(matches) >= 20:
                    break
            return {"success": True, "query": query, "matches": matches, "count": len(matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== SYSTEM METRICS & SHELL ====================

    def get_system_metrics(self) -> Dict[str, Any]:
        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")

            battery_info = "N/A"
            if hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat:
                    battery_info = f"{round(bat.percent)}% ({'Charging' if bat.power_plugged else 'On Battery'})"

            return {
                "success": True,
                "cpu_percent": cpu_pct,
                "ram_used_gb": round((mem.total - mem.available) / (1024**3), 1),
                "ram_total_gb": round(mem.total / (1024**3), 1),
                "ram_percent": mem.percent,
                "disk_free_gb": round(disk.free / (1024**3), 1),
                "disk_percent": disk.percent,
                "battery": battery_info
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_powershell_safe(self, command: str) -> Dict[str, Any]:
        # Block hazardous destructive scripts
        forbidden = ["format ", "del /s", "rmdir /s /q c:", "diskpart"]
        for bad in forbidden:
            if bad in command.lower():
                return {"success": False, "error": f"Command blocked by safety filter: {bad}"}

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 10 seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}
