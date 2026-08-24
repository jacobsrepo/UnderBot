import os
import sys
import subprocess
import shutil
import glob
import psutil
import time
from typing import Dict, List, Optional, Any

class DesktopAgent:
    """
    Windows Desktop Automation & OS Control Agent for Contender.
    Provides direct window control (minimize all, show desktop), application launching,
    file operations, desktop organization, and telemetry.
    """

    KNOWN_APPS = {
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "chrome": "chrome",
        "google chrome": "chrome",
        "terminal": "wt",
        "windows terminal": "wt",
        "powershell": "powershell",
        "cmd": "cmd",
        "command prompt": "cmd",
        "calculator": "calc",
        "calc": "calc",
        "notepad": "notepad",
        "spotify": "spotify",
        "file explorer": "explorer",
        "explorer": "explorer",
        "task manager": "taskmgr",
        "device manager": "devmgmt.msc",
        "settings": "ms-settings:"
    }

    def __init__(self):
        self.user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Public")
        self.desktop_path = os.path.join(self.user_profile, "Desktop")
        self.documents_path = os.path.join(self.user_profile, "Documents")
        self.downloads_path = os.path.join(self.user_profile, "Downloads")

    # ==================== WINDOW & DESKTOP CONTROLS ====================

    def minimize_all_windows(self) -> Dict[str, Any]:
        """Minimizes all open windows on the Windows desktop."""
        cmd = "powershell -Command \"(New-Object -ComObject Shell.Application).MinimizeAll()\""
        try:
            subprocess.run(cmd, shell=True, check=True, timeout=5)
            return {"success": True, "message": "All desktop windows minimized."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def undo_minimize_all(self) -> Dict[str, Any]:
        """Restores previously minimized windows."""
        cmd = "powershell -Command \"(New-Object -ComObject Shell.Application).UndoMinimizeALL()\""
        try:
            subprocess.run(cmd, shell=True, check=True, timeout=5)
            return {"success": True, "message": "Desktop windows restored."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def organize_desktop_files(self) -> Dict[str, Any]:
        """
        Organizes loose desktop files into categorized folders:
        Documents, Images, Code, Archives, Media.
        """
        if not os.path.exists(self.desktop_path):
            return {"success": False, "error": "Desktop path not found"}

        categories = {
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"],
            "Code": [".py", ".js", ".html", ".css", ".ino", ".cpp", ".json", ".ts"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Media": [".mp4", ".mkv", ".mp3", ".wav"]
        }

        moved_count = 0
        try:
            for item in os.listdir(self.desktop_path):
                full_path = os.path.join(self.desktop_path, item)
                if os.path.isfile(full_path) and not item.endswith(".lnk"):
                    ext = os.path.splitext(item)[1].lower()
                    for folder_name, extensions in categories.items():
                        if ext in extensions:
                            target_dir = os.path.join(self.desktop_path, folder_name)
                            os.makedirs(target_dir, exist_ok=True)
                            shutil.move(full_path, os.path.join(target_dir, item))
                            moved_count += 1
                            break

            return {"success": True, "moved_count": moved_count, "message": f"Organized {moved_count} desktop files into categories."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== APPLICATION MANAGEMENT ====================

    def launch_application(self, app_name: str) -> Dict[str, Any]:
        """Launches a desktop application."""
        clean_name = app_name.strip().lower()
        cmd = self.KNOWN_APPS.get(clean_name, clean_name)

        try:
            if sys.platform == "win32":
                subprocess.Popen(f"start {cmd}", shell=True)
            else:
                subprocess.Popen([cmd])

            return {
                "success": True,
                "app_name": app_name,
                "message": f"Launched {app_name} successfully."
            }
        except Exception as e:
            return {"success": False, "app_name": app_name, "error": str(e)}

    # ==================== SYSTEM TELEMETRY ====================

    def get_system_metrics(self) -> Dict[str, Any]:
        """Retrieves real-time CPU, RAM, Disk, and Battery metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if sys.platform == "win32" else "/")

        battery_status = "N/A"
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_status = f"{battery.percent}% {'(Charging)' if battery.power_plugged else ''}"
        except Exception:
            pass

        return {
            "cpu_percent": cpu_percent,
            "ram_used_gb": round(ram.used / (1024 ** 3), 1),
            "ram_total_gb": round(ram.total / (1024 ** 3), 1),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "battery": battery_status
        }

    # ==================== FILE MANAGEMENT ====================

    def copy_file(self, src: str, dst: str) -> Dict[str, Any]:
        try:
            resolved_src = self._resolve_path(src)
            resolved_dst = self._resolve_path(dst)
            if os.path.isdir(resolved_src):
                shutil.copytree(resolved_src, resolved_dst, dirs_exist_ok=True)
            else:
                shutil.copy2(resolved_src, resolved_dst)
            return {"success": True, "src": resolved_src, "dst": resolved_dst}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, src: str, dst: str) -> Dict[str, Any]:
        try:
            resolved_src = self._resolve_path(src)
            resolved_dst = self._resolve_path(dst)
            shutil.move(resolved_src, resolved_dst)
            return {"success": True, "src": resolved_src, "dst": resolved_dst}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        try:
            resolved_path = self._resolve_path(path)
            if os.path.isdir(resolved_path):
                shutil.rmtree(resolved_path)
            else:
                os.remove(resolved_path)
            return {"success": True, "path": resolved_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_directory(self, path: str = "Desktop") -> Dict[str, Any]:
        try:
            resolved_path = self._resolve_path(path)
            items = []
            for item in os.listdir(resolved_path):
                full = os.path.join(resolved_path, item)
                items.append({
                    "name": item,
                    "is_dir": os.path.isdir(full),
                    "size_bytes": os.path.getsize(full) if os.path.isfile(full) else 0
                })
            return {"success": True, "path": resolved_path, "count": len(items), "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file_text(self, path: str, max_chars: int = 4000) -> Dict[str, Any]:
        try:
            resolved_path = self._resolve_path(path)
            with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
            return {"success": True, "path": resolved_path, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file_text(self, path: str, content: str) -> Dict[str, Any]:
        try:
            resolved_path = self._resolve_path(path)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": resolved_path, "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, query: str, root: str = "Desktop") -> Dict[str, Any]:
        try:
            resolved_root = self._resolve_path(root)
            pattern = os.path.join(resolved_root, f"**/*{query}*")
            matches = glob.glob(pattern, recursive=True)
            return {"success": True, "query": query, "count": len(matches), "matches": matches[:25]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def capture_screen_base64(self) -> Optional[str]:
        try:
            import mss
            import mss.tools
            import io
            from PIL import Image
            import base64

            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            print(f"[DesktopAgent] Screen grab notice: {e}")
            return None

    def _resolve_path(self, path: str) -> str:
        p_lower = path.strip().lower()
        if p_lower == "desktop" or p_lower.startswith("desktop/"):
            return os.path.join(self.desktop_path, path[7:].lstrip("/\\"))
        elif p_lower == "documents" or p_lower.startswith("documents/"):
            return os.path.join(self.documents_path, path[9:].lstrip("/\\"))
        elif p_lower == "downloads" or p_lower.startswith("downloads/"):
            return os.path.join(self.downloads_path, path[9:].lstrip("/\\"))
        return os.path.abspath(path)
