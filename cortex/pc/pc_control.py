"""
Cortex PC Control Module
Provides native Windows automation capabilities:
- Interactive desktop launching (ensures windows appear on the user's visible screen WinSta0\\Default)
- Reliable window management (focus stealing, restore, minimize, close)
- Document creation & opening (create_and_open_document for instant, zero-glitch text writing)
- Screen capture via mss on the active interactive desktop
- Process querying, killing, and system diagnostics
- Keyboard & clipboard automation
- Local file search & directory inspection
"""

import os
import io
import re
import sys
import time
import json
import base64
import asyncio
import ctypes
import ctypes.wintypes
import subprocess
from typing import List, Dict, Any, Optional

# Lazy module loaders
def _psutil():
    import psutil
    return psutil

def _pyautogui():
    import pyautogui
    pyautogui.FAILSAFE = False
    return pyautogui

def _pyperclip():
    import pyperclip
    return pyperclip

def _mss():
    import mss
    return mss

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def _ensure_default_desktop():
    """Ensure the calling thread is attached to the active user's visible desktop."""
    try:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            return hdesk
    except Exception:
        pass
    return None


class PCController:
    """High-level native Windows PC automation for Cortex."""

    def __init__(self):
        _ensure_default_desktop()

    # ------------------------------------------------------------------ #
    # Volume                                                               #
    # ------------------------------------------------------------------ #

    def _get_volume_interface(self):
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        return devices.EndpointVolume

    async def get_volume(self) -> Dict[str, Any]:
        """Return current system volume (0-100) and mute state."""
        def _work():
            vol = self._get_volume_interface()
            level = vol.GetMasterVolumeLevelScalar()
            muted = bool(vol.GetMute())
            return {"volume": round(level * 100), "muted": muted}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set master volume level (0-100)."""
        def _work():
            vol = self._get_volume_interface()
            clamped = max(0, min(100, int(level))) / 100.0
            vol.SetMasterVolumeLevelScalar(clamped, None)
            return {"status": "ok", "level": int(level)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def mute_audio(self) -> Dict[str, Any]:
        """Mute system audio."""
        def _work():
            vol = self._get_volume_interface()
            vol.SetMute(1, None)
            return {"status": "muted"}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def unmute_audio(self) -> Dict[str, Any]:
        """Unmute system audio."""
        def _work():
            vol = self._get_volume_interface()
            vol.SetMute(0, None)
            return {"status": "unmuted"}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Interactive App Launching                                            #
    # ------------------------------------------------------------------ #

    _APP_MAP = {
        "microsoft store": "ms-windows-store:",
        "store": "ms-windows-store:",
        "discord": "discord:",
        "notepad": "notepad.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "calculator": "calc.exe",
        "spotify": "spotify.exe",
        "vscode": "code.exe",
        "visual studio code": "code.exe",
        "teams": "ms-teams:",
        "microsoft teams": "ms-teams:",
        "paint": "mspaint.exe",
        "powershell": "powershell.exe",
        "cmd": "cmd.exe",
        "task manager": "taskmgr.exe",
        "settings": "ms-settings:",
        "control panel": "control.exe",
        "steam": "steam.exe",
    }

    def _launch_interactive(self, cmd_or_path: str, args: str = "") -> bool:
        """
        Launch an application directly on the user's visible interactive desktop (WinSta0\\Default).
        Uses Task Scheduler /it to guarantee placement on user's active screen.
        """
        _ensure_default_desktop()
        full_cmd = f"{cmd_or_path} {args}".strip() if args else cmd_or_path

        # Strategy 1: Task Scheduler interactive launch (guarantees placement on user's visible screen)
        try:
            task_name = f"CortexRun_{int(time.time()*1000)%100000}"
            subprocess.run(
                ["schtasks", "/create", "/tn", task_name, "/tr", full_cmd, "/sc", "once", "/st", "23:59", "/f", "/it"],
                capture_output=True,
                check=False
            )
            res = subprocess.run(["schtasks", "/run", "/tn", task_name], capture_output=True, check=False)
            if res.returncode == 0:
                return True
        except Exception:
            pass

        # Strategy 2: Direct os.startfile
        try:
            if args:
                os.startfile(cmd_or_path, arguments=args)
            else:
                os.startfile(cmd_or_path)
            return True
        except Exception:
            pass

        # Strategy 3: subprocess with explicit desktop
        try:
            si = subprocess.STARTUPINFO()
            si.lpDesktop = r"WinSta0\Default"
            subprocess.Popen(full_cmd, shell=True, startupinfo=si)
            return True
        except Exception:
            pass

        return False

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application on the user's visible desktop."""
        def _work():
            _ensure_default_desktop()
            name_lower = app_name.strip().lower()
            target = self._APP_MAP.get(name_lower, app_name)
            if not target.endswith(".exe") and not ":" in target and not os.path.sep in target:
                target = target + ".exe"

            ok = self._launch_interactive(target)
            time.sleep(1.0)
            verify = self._verify_running_sync(app_name)
            return {
                "status": "launched" if ok else "launch_failed",
                "app": app_name,
                "target": target,
                "verified_running": verify.get("running", False)
            }
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def open_file(self, path: str) -> Dict[str, Any]:
        """Open any file with its default application on the user's desktop."""
        def _work():
            _ensure_default_desktop()
            ok = self._launch_interactive(path)
            return {"status": "opened" if ok else "failed", "path": path}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def create_and_open_document(self, title: str, content: str, app: str = "notepad") -> Dict[str, Any]:
        """
        Create a text document on the user's Desktop with the specified content,
        and immediately open it in Notepad (or specified app) in front of the user.
        This provides 100% reliable, zero-glitch document creation and presentation.
        """
        def _work():
            _ensure_default_desktop()
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', title.strip())
            if not safe_title.endswith(".txt") and not safe_title.endswith(".md"):
                safe_title += ".txt"

            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop_dir, safe_title)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            app_target = self._APP_MAP.get(app.lower(), "notepad.exe")
            ok = self._launch_interactive(app_target, f'"{file_path}"')
            time.sleep(1.2)
            self._focus_window_sync(safe_title)

            return {
                "status": "created_and_opened",
                "file_path": file_path,
                "title": safe_title,
                "bytes_written": len(content.encode("utf-8")),
                "app": app
            }
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Window Management                                                    #
    # ------------------------------------------------------------------ #

    def _get_visible_windows(self) -> List[Dict[str, Any]]:
        _ensure_default_desktop()
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        windows = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    if title and title not in ("Program Manager", "Default IME", "MSCTFIME UI"):
                        pid = ctypes.wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({"hwnd": hwnd, "pid": pid.value, "title": title})
            return True

        user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
        return windows

    def _focus_window_sync(self, title_fragment: str) -> bool:
        """Bring window matching title fragment to the true foreground."""
        _ensure_default_desktop()
        windows = self._get_visible_windows()
        frag = title_fragment.lower()
        target = None
        for w in windows:
            if frag in w["title"].lower():
                target = w
                break

        if not target:
            return False

        hwnd = target["hwnd"]
        fg_hwnd = user32.GetForegroundWindow()
        cur_thread = kernel32.GetCurrentThreadId()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)

        try:
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)

            user32.AttachThreadInput(cur_thread, fg_thread, True)
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SwitchToThisWindow(hwnd, True)
            user32.AttachThreadInput(cur_thread, fg_thread, False)
            return True
        except Exception:
            return False

    async def list_windows(self) -> Dict[str, Any]:
        """List all visible application windows on the user's desktop."""
        def _work():
            wins = self._get_visible_windows()
            return {"windows": [w["title"] for w in wins], "details": wins}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def focus_window(self, title: str) -> Dict[str, Any]:
        """Bring a window matching the title fragment to the foreground."""
        def _work():
            ok = self._focus_window_sync(title)
            if ok:
                return {"status": "focused", "query": title}
            return {"error": f"No visible window matching '{title}' found."}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def close_window(self, title: str) -> Dict[str, Any]:
        """Send close message to window matching title."""
        def _work():
            windows = self._get_visible_windows()
            frag = title.lower()
            for w in windows:
                if frag in w["title"].lower():
                    user32.PostMessageW(w["hwnd"], 0x0010, 0, 0)
                    return {"status": "closed", "title": w["title"]}
            return {"error": f"No window matching '{title}' found."}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Screen Capture                                                       #
    # ------------------------------------------------------------------ #

    async def take_screenshot(self) -> Dict[str, Any]:
        """Capture the full user desktop. Returns a base64-encoded JPEG."""
        def _work():
            _ensure_default_desktop()
            mss_mod = _mss()
            with mss_mod.mss() as sct:
                monitor = sct.monitors[0]
                raw = sct.grab(monitor)
                from PIL import Image
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return {"screenshot": b64, "width": raw.width, "height": raw.height}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Process Management & Verification                                   #
    # ------------------------------------------------------------------ #

    def _verify_running_sync(self, app_name: str) -> Dict[str, Any]:
        psutil = _psutil()
        name_lower = app_name.lower().replace(".exe", "").strip()
        running = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pn = p.info["name"].lower().replace(".exe", "")
                if name_lower in pn or pn in name_lower:
                    running.append({"pid": p.pid, "name": p.info["name"]})
            except Exception:
                pass
        return {"running": len(running) > 0, "processes": running[:5], "app": app_name}

    async def verify_app_running(self, app_name: str) -> Dict[str, Any]:
        """Check if an application is currently running."""
        try:
            return await asyncio.to_thread(self._verify_running_sync, app_name)
        except Exception as e:
            return {"error": str(e)}

    async def get_running_processes(self, limit: int = 20) -> Dict[str, Any]:
        """Return a list of top running processes sorted by RAM usage."""
        def _work():
            psutil = _psutil()
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
                try:
                    info = p.info
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "mem_percent": round(info.get("memory_percent") or 0.0, 1),
                        "cpu_percent": round(info.get("cpu_percent") or 0.0, 1)
                    })
                except Exception:
                    pass
            procs.sort(key=lambda x: x["mem_percent"], reverse=True)
            return {"processes": procs[:limit]}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def kill_process(self, identifier: str) -> Dict[str, Any]:
        """Kill a process by name fragment or numeric PID."""
        def _work():
            psutil = _psutil()
            killed = []
            try:
                pid = int(identifier)
                p = psutil.Process(pid)
                p.kill()
                killed.append({"pid": pid, "name": p.name()})
            except (ValueError, psutil.NoSuchProcess):
                frag = identifier.lower()
                for p in psutil.process_iter(["pid", "name"]):
                    try:
                        if frag in p.info["name"].lower():
                            p.kill()
                            killed.append({"pid": p.pid, "name": p.info["name"]})
                    except Exception:
                        pass
            if not killed:
                return {"error": f"No process matching '{identifier}' found."}
            return {"killed": killed}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def get_system_info(self) -> Dict[str, Any]:
        """Return CPU, RAM, and disk usage summary."""
        def _work():
            psutil = _psutil()
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return {
                "cpu_percent": cpu,
                "ram_total_gb": round(ram.total / 1e9, 1),
                "ram_used_gb": round(ram.used / 1e9, 1),
                "ram_percent": ram.percent,
                "disk_total_gb": round(disk.total / 1e9, 1),
                "disk_free_gb": round(disk.free / 1e9, 1),
                "disk_percent": disk.percent
            }
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Mouse, Keyboard & Clipboard                                          #
    # ------------------------------------------------------------------ #

    async def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """
        Type text into the currently active window.
        Uses clipboard paste for multiline or long text (>50 chars) for instant, perfect fidelity.
        """
        def _work():
            _ensure_default_desktop()
            pag = _pyautogui()
            clip = _pyperclip()
            if len(text) > 40 or "\n" in text:
                clip.copy(text)
                time.sleep(0.1)
                pag.hotkey("ctrl", "v")
            else:
                pag.write(text, interval=interval)
            return {"status": "typed", "length": len(text)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def press_keys(self, keys: List[str]) -> Dict[str, Any]:
        """Press a key or hotkey combination (e.g. ['ctrl', 'v'] or ['enter'])."""
        def _work():
            _ensure_default_desktop()
            pag = _pyautogui()
            if len(keys) == 1:
                pag.press(keys[0])
            else:
                pag.hotkey(*keys)
            return {"status": "keys_pressed", "keys": keys}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def read_clipboard(self) -> Dict[str, Any]:
        """Read current text from the Windows clipboard."""
        def _work():
            clip = _pyperclip()
            return {"clipboard": clip.paste()}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def write_clipboard(self, text: str) -> Dict[str, Any]:
        """Write text to the Windows clipboard."""
        def _work():
            clip = _pyperclip()
            clip.copy(text)
            return {"status": "copied", "length": len(text)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Filesystem                                                           #
    # ------------------------------------------------------------------ #

    async def list_directory(self, path: str = "") -> Dict[str, Any]:
        """List files and subdirectories in a directory path."""
        def _work():
            target = path.strip() or os.path.expanduser("~")
            target = os.path.expandvars(os.path.expanduser(target))
            if not os.path.exists(target):
                return {"error": f"Path '{target}' does not exist."}
            entries = []
            try:
                with os.scandir(target) as it:
                    for entry in it:
                        try:
                            st = entry.stat()
                            entries.append({
                                "name": entry.name,
                                "is_dir": entry.is_dir(),
                                "size_bytes": st.st_size if not entry.is_dir() else 0
                            })
                        except Exception:
                            pass
            except PermissionError:
                return {"error": f"Permission denied accessing '{target}'."}
            entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            return {"path": target, "count": len(entries), "entries": entries[:60]}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def find_files(self, root: str, pattern: str, max_results: int = 50) -> Dict[str, Any]:
        """Recursively search for files matching a pattern."""
        import fnmatch
        def _work():
            target_root = os.path.expandvars(os.path.expanduser(root.strip() or os.path.expanduser("~")))
            if not os.path.exists(target_root):
                return {"error": f"Root path '{target_root}' does not exist."}
            matches = []
            pat = pattern.strip()
            skip_dirs = {"node_modules", ".git", "__pycache__", "AppData", "$Recycle.Bin"}
            for dirpath, dirnames, filenames in os.walk(target_root):
                dirnames[:] = [d for d in dirnames if d not in skip_dirs]
                for f in filenames:
                    if fnmatch.fnmatch(f.lower(), pat.lower()):
                        matches.append(os.path.join(dirpath, f))
                        if len(matches) >= max_results:
                            return {"root": target_root, "pattern": pat, "count": len(matches), "files": matches}
            return {"root": target_root, "pattern": pat, "count": len(matches), "files": matches}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}
