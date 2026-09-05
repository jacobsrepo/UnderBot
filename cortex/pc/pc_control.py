"""
Cortex PC Controller - Native Windows System Control
Provides volume, app launching, window management, screen capture,
mouse/keyboard input, process inspection, file operations, and clipboard.
All operations are async-safe via asyncio.to_thread().
"""

import asyncio
import base64
import io
import os
import subprocess
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Lazy importers -- keep startup fast; only fail at call-time if missing
# ---------------------------------------------------------------------------

def _pycaw():
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    return AudioUtilities, IAudioEndpointVolume, CLSCTX_ALL

def _pyautogui():
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui

def _win32gui():
    import win32gui, win32con
    return win32gui, win32con

def _psutil():
    import psutil
    return psutil

def _mss():
    import mss
    return mss

def _pyperclip():
    import pyperclip
    return pyperclip

def _appopener():
    import AppOpener
    return AppOpener


# ---------------------------------------------------------------------------
# PCController
# ---------------------------------------------------------------------------

class PCController:
    """
    Thin async wrapper around native Windows desktop APIs.
    All blocking calls are wrapped in asyncio.to_thread() so the asyncio
    event loop (FastAPI / uvicorn) is never blocked.
    """

    # ------------------------------------------------------------------ #
    # Volume                                                               #
    # ------------------------------------------------------------------ #

    def _get_volume_interface(self):
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        # AudioDevice.EndpointVolume is an IAudioEndpointVolume-like interface
        return devices.EndpointVolume


    async def get_volume(self) -> Dict[str, Any]:
        """Return current system volume (0-100) and mute state."""
        def _work():
            vol = self._get_volume_interface()
            level = vol.GetMasterVolumeLevelScalar()  # 0.0 – 1.0
            muted = bool(vol.GetMute())
            return {"volume": round(level * 100), "muted": muted}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set system volume. level is 0-100."""
        level = max(0, min(100, int(level)))
        def _work():
            vol = self._get_volume_interface()
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return {"volume": level, "status": "ok"}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def mute_audio(self) -> Dict[str, Any]:
        def _work():
            vol = self._get_volume_interface()
            vol.SetMute(1, None)
            return {"muted": True, "status": "ok"}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def unmute_audio(self) -> Dict[str, Any]:
        def _work():
            vol = self._get_volume_interface()
            vol.SetMute(0, None)
            return {"muted": False, "status": "ok"}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # App launching                                                        #
    # ------------------------------------------------------------------ #

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        """
        Launch an application by name (uses AppOpener first, falls back to
        subprocess.Popen for direct .exe paths or known system commands).
        """
        def _work():
            # Direct .exe path
            if app_name.lower().endswith(".exe") or os.path.sep in app_name:
                subprocess.Popen([app_name], shell=True)
                return {"status": "launched", "app": app_name}
            # Try AppOpener (handles Chrome, Notepad, Spotify, etc. by name)
            try:
                ao = _appopener()
                ao.open(app_name, match_closest=True, output=False)
                return {"status": "launched", "app": app_name}
            except Exception:
                pass
            # Fallback: shell start
            subprocess.Popen(f'start "" "{app_name}"', shell=True)
            return {"status": "launched", "app": app_name}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def open_file(self, path: str) -> Dict[str, Any]:
        """Open any file with its default application (os.startfile equivalent)."""
        def _work():
            os.startfile(path)
            return {"status": "opened", "path": path}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Window management                                                    #
    # ------------------------------------------------------------------ #

    async def list_windows(self) -> Dict[str, Any]:
        """List all visible top-level window titles."""
        def _work():
            win32gui, _ = _win32gui()
            titles: List[str] = []
            def _cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd)
                    if t:
                        titles.append(t)
            win32gui.EnumWindows(_cb, None)
            return {"windows": titles}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    def _find_hwnd(self, title_fragment: str) -> Optional[int]:
        win32gui, _ = _win32gui()
        result = [None]
        frag_lower = title_fragment.lower()
        def _cb(hwnd, _):
            if result[0]:
                return
            t = win32gui.GetWindowText(hwnd)
            if frag_lower in t.lower() and win32gui.IsWindowVisible(hwnd):
                result[0] = hwnd
        win32gui.EnumWindows(_cb, None)
        return result[0]

    async def focus_window(self, title: str) -> Dict[str, Any]:
        """Bring a window matching the title fragment to the foreground."""
        def _work():
            win32gui, win32con = _win32gui()
            hwnd = self._find_hwnd(title)
            if not hwnd:
                return {"error": f"No window matching '{title}' found."}
            import win32api
            # Restore if minimized
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return {"status": "focused", "window": win32gui.GetWindowText(hwnd)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def minimize_window(self, title: str) -> Dict[str, Any]:
        def _work():
            win32gui, win32con = _win32gui()
            hwnd = self._find_hwnd(title)
            if not hwnd:
                return {"error": f"No window matching '{title}' found."}
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return {"status": "minimized", "window": win32gui.GetWindowText(hwnd)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def maximize_window(self, title: str) -> Dict[str, Any]:
        def _work():
            win32gui, win32con = _win32gui()
            hwnd = self._find_hwnd(title)
            if not hwnd:
                return {"error": f"No window matching '{title}' found."}
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return {"status": "maximized", "window": win32gui.GetWindowText(hwnd)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def close_window(self, title: str) -> Dict[str, Any]:
        def _work():
            win32gui, win32con = _win32gui()
            hwnd = self._find_hwnd(title)
            if not hwnd:
                return {"error": f"No window matching '{title}' found."}
            name = win32gui.GetWindowText(hwnd)
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return {"status": "close_sent", "window": name}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Screen capture                                                       #
    # ------------------------------------------------------------------ #

    async def take_screenshot(self) -> Dict[str, Any]:
        """Capture the full screen. Returns a base64-encoded JPEG."""
        def _work():
            mss_mod = _mss()
            with mss_mod.mss() as sct:
                monitor = sct.monitors[0]  # Full virtual desktop
                raw = sct.grab(monitor)
                # Convert to PIL then JPEG
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
    # Process management                                                   #
    # ------------------------------------------------------------------ #

    async def get_running_processes(self, limit: int = 20) -> Dict[str, Any]:
        """Return top processes sorted by CPU usage."""
        def _work():
            psutil = _psutil()
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    info = p.info
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu": info["cpu_percent"],
                        "mem_mb": round(info["memory_info"].rss / 1024 / 1024, 1) if info["memory_info"] else 0
                    })
                except Exception:
                    pass
            procs.sort(key=lambda x: x["cpu"], reverse=True)
            return {"processes": procs[:limit]}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def kill_process(self, identifier: str) -> Dict[str, Any]:
        """
        Kill a process by name fragment or PID.
        identifier can be a name (e.g. 'chrome') or numeric PID.
        """
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
    # Mouse & keyboard                                                     #
    # ------------------------------------------------------------------ #

    async def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """Type text at the current cursor position."""
        def _work():
            pag = _pyautogui()
            pag.write(text, interval=interval)
            return {"status": "typed", "length": len(text)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def press_keys(self, keys: List[str]) -> Dict[str, Any]:
        """
        Press a key or hotkey combination.
        keys: list of key names, e.g. ['ctrl', 'c'] or ['enter'].
        """
        def _work():
            pag = _pyautogui()
            if len(keys) == 1:
                pag.press(keys[0])
            else:
                pag.hotkey(*keys)
            return {"status": "pressed", "keys": keys}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def move_mouse(self, x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
        """Move mouse to absolute screen coordinates."""
        def _work():
            pag = _pyautogui()
            pag.moveTo(x, y, duration=duration)
            return {"status": "moved", "x": x, "y": y}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def click_mouse(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Click mouse at position. If x/y omitted, clicks at current position."""
        def _work():
            pag = _pyautogui()
            pag.click(x=x, y=y, button=button, clicks=clicks)
            return {"status": "clicked", "x": x, "y": y, "button": button}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # Clipboard                                                            #
    # ------------------------------------------------------------------ #

    async def read_clipboard(self) -> Dict[str, Any]:
        def _work():
            pyperclip = _pyperclip()
            text = pyperclip.paste()
            return {"clipboard": text}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def write_clipboard(self, text: str) -> Dict[str, Any]:
        def _work():
            pyperclip = _pyperclip()
            pyperclip.copy(text)
            return {"status": "copied", "length": len(text)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    # File system helpers                                                  #
    # ------------------------------------------------------------------ #

    async def list_directory(self, path: str) -> Dict[str, Any]:
        """List contents of a directory (files + folders with sizes)."""
        def _work():
            entries = []
            try:
                for e in os.scandir(path):
                    entry = {"name": e.name, "is_dir": e.is_dir()}
                    if e.is_file():
                        entry["size_bytes"] = e.stat().st_size
                    entries.append(entry)
                entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            except PermissionError:
                return {"error": f"Permission denied: {path}"}
            return {"path": path, "entries": entries, "count": len(entries)}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}

    async def find_files(self, root: str, pattern: str, max_results: int = 50) -> Dict[str, Any]:
        """Recursively search for files matching a name pattern (case-insensitive)."""
        import fnmatch
        def _work():
            found = []
            pat_lower = pattern.lower()
            for dirpath, _, files in os.walk(root):
                for f in files:
                    if fnmatch.fnmatch(f.lower(), pat_lower):
                        found.append(os.path.join(dirpath, f))
                        if len(found) >= max_results:
                            return {"files": found, "truncated": True}
            return {"files": found, "truncated": False}
        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            return {"error": str(e)}
