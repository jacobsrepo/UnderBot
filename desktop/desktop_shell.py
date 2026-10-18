import os
import sys
import time
import json
import socket
import threading
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

try:
    import webview
except ImportError:
    webview = None

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_C = 0x43  # 'C' key
VK_M = 0x4D  # 'M' key
VK_SPACE = 0x20

HOTKEY_TOGGLE_ID = 101
HOTKEY_MUTE_ID = 102

STATE_FILE = os.path.join(_ROOT_DIR, "window_state.json")

class WindowStateManager:
    """Persists desktop window dimensions and coordinates across sessions."""
    @staticmethod
    def load_state() -> Dict[str, Any]:
        default_state = {
            "is_mini": False,
            "studio": {"width": 1180, "height": 780, "x": None, "y": None},
            "mini": {"width": 360, "height": 105, "x": None, "y": None}
        }
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_state.update(data)
            except Exception:
                pass
        return default_state

    @staticmethod
    def save_state(state: Dict[str, Any]):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

class CortexNativeAPI:
    """Native Python bridge exposed to JavaScript in the desktop shell."""
    def __init__(self, window, state_manager: WindowStateManager, initial_state: Dict[str, Any]):
        self._window = window
        self.state_mgr = state_manager
        self.state = initial_state
        self.is_mini = initial_state.get("is_mini", False)
        self.is_hidden = False

    def toggle_mini_mode(self) -> bool:
        """Switches between Tactical Studio and the Always-on-Top Floating Mini HUD."""
        if not self._window:
            return False

        if not self.is_mini:
            # Switch to Mini HUD
            mini_cfg = self.state.get("mini", {})
            w = mini_cfg.get("width", 360)
            h = mini_cfg.get("height", 105)
            self._window.resize(w, h)
            self._window.on_top = True
            self.is_mini = True
            if mini_cfg.get("x") is not None and mini_cfg.get("y") is not None:
                self._window.move(mini_cfg["x"], mini_cfg["y"])
        else:
            # Expand to full Tactical Studio
            studio_cfg = self.state.get("studio", {})
            w = studio_cfg.get("width", 1180)
            h = studio_cfg.get("height", 780)
            self._window.resize(w, h)
            self._window.on_top = False
            self.is_mini = False
            if studio_cfg.get("x") is not None and studio_cfg.get("y") is not None:
                self._window.move(studio_cfg["x"], studio_cfg["y"])

        self.state["is_mini"] = self.is_mini
        self.state_mgr.save_state(self.state)
        return self.is_mini

    def expand_studio_mode(self) -> bool:
        """Expands back into full Tactical Studio."""
        if self._window and self.is_mini:
            return self.toggle_mini_mode()
        return True

    def toggle_visibility(self) -> bool:
        """Toggles window visibility (summon from background or hide)."""
        if not self._window:
            return False

        if self.is_hidden:
            self._window.show()
            self._window.restore()
            self.is_hidden = False
        else:
            self._window.hide()
            self.is_hidden = True
        return not self.is_hidden

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def hide_to_tray(self):
        """Hides window to notification area."""
        if self._window:
            self._window.hide()
            self.is_hidden = True

    def save_window_bounds(self, x: int, y: int, width: int, height: int):
        """Saves current window coordinates."""
        key = "mini" if self.is_mini else "studio"
        self.state[key] = {"width": width, "height": height, "x": x, "y": y}
        self.state["is_mini"] = self.is_mini
        self.state_mgr.save_state(self.state)

    def close_app(self):
        """Terminates Cortex and all background worker threads."""
        if self._window:
            self._window.destroy()
        os._exit(0)

class GlobalHotkeyManager:
    """Manages system-wide global hotkeys via native Win32 API without external dependencies."""
    def __init__(self, on_toggle_callback, on_mute_callback):
        self.on_toggle = on_toggle_callback
        self.on_mute = on_mute_callback
        self.is_running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if sys.platform == "win32":
            self.is_running = True
            self.thread = threading.Thread(target=self._hotkey_loop, daemon=True)
            self.thread.start()

    def _hotkey_loop(self):
        user32 = ctypes.windll.user32
        
        # Register Ctrl + Alt + C (Summon / Toggle Cortex)
        res_toggle = user32.RegisterHotKey(None, HOTKEY_TOGGLE_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_C)
        if res_toggle:
            print("[DesktopApp] Registered Global Hotkey: Ctrl+Alt+C (Summon Cortex)")

        # Register Ctrl + Alt + M (Toggle Mute)
        res_mute = user32.RegisterHotKey(None, HOTKEY_MUTE_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_M)
        if res_mute:
            print("[DesktopApp] Registered Global Hotkey: Ctrl+Alt+M (Toggle Microphone)")

        msg = wintypes.MSG()
        while self.is_running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                hotkey_id = msg.wParam
                if hotkey_id == HOTKEY_TOGGLE_ID and self.on_toggle:
                    self.on_toggle()
                elif hotkey_id == HOTKEY_MUTE_ID and self.on_mute:
                    self.on_mute()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnregisterHotKey(None, HOTKEY_TOGGLE_ID)
        user32.UnregisterHotKey(None, HOTKEY_MUTE_ID)

    def stop(self):
        self.is_running = False

def check_single_instance() -> bool:
    """Ensures only one instance of Cortex runs at a time."""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        mutex_name = "Local\\CortexStudioMutex"
        mutex = kernel32.CreateMutexW(None, True, mutex_name)
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            print("[DesktopApp] Cortex is already running. Focusing existing instance...")
            # Try to find and bring existing window to foreground
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "Cortex // AI Studio")
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            return False
    return True

def run_server():
    import uvicorn
    from backend.app import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def wait_for_server(port=8000, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False

def main():
    if not check_single_instance():
        sys.exit(0)

    if not webview:
        print("[DesktopShell] pywebview is not installed in the current environment.")
        print("               Please install via: uv pip install pywebview")
        return

    # 1. Start backend server in dedicated thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("[Cortex] Initializing Dedicated Desktop Application...")
    wait_for_server(8000)

    state_mgr = WindowStateManager()
    initial_state = state_mgr.load_state()

    is_mini = initial_state.get("is_mini", False)
    cfg = initial_state.get("mini" if is_mini else "studio", {})
    init_w = cfg.get("width", 360 if is_mini else 1180)
    init_h = cfg.get("height", 105 if is_mini else 780)
    init_x = cfg.get("x")
    init_y = cfg.get("y")

    # 2. Create native WebView2 window
    window = webview.create_window(
        title="Cortex // AI Studio",
        url="http://127.0.0.1:8000",
        width=init_w,
        height=init_h,
        x=init_x,
        y=init_y,
        min_size=(340, 95),
        resizable=True,
        text_select=True,
        on_top=is_mini,
        background_color="#0b0c0e"
    )

    api = CortexNativeAPI(window, state_mgr, initial_state)
    window.expose(
        api.toggle_mini_mode,
        api.expand_studio_mode,
        api.toggle_visibility,
        api.minimize_window,
        api.hide_to_tray,
        api.save_window_bounds,
        api.close_app
    )

    # 3. Setup Win32 Global Hotkeys (Ctrl+Alt+C to summon/toggle)
    def on_global_toggle():
        try:
            window.evaluate_js("if (window.cortexApp) window.cortexApp.toggleMiniHud();")
        except Exception:
            api.toggle_mini_mode()

    def on_global_mute():
        try:
            window.evaluate_js("if (window.cortexApp) window.cortexApp.toggleMute();")
        except Exception:
            pass

    hotkey_mgr = GlobalHotkeyManager(on_global_toggle, on_global_mute)
    hotkey_mgr.start()

    try:
        webview.start(debug=False)
    finally:
        hotkey_mgr.stop()

if __name__ == "__main__":
    main()

