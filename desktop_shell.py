import os
import sys
import time
import threading
import socket
import uvicorn
import webview

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from backend.app import app

class ContenderNativeAPI:
    """Native Python bridge exposed to JavaScript in the desktop shell."""
    def __init__(self, window):
        self._window = window
        self.is_mini = False

    def toggle_mini_mode(self):
        """Switches into the compact Always-on-Top Floating Companion HUD."""
        if not self._window:
            return False

        if not self.is_mini:
            self._window.resize(360, 105)
            self._window.on_top = True
            self.is_mini = True
        else:
            self._window.resize(1180, 780)
            self._window.on_top = False
            self.is_mini = False
        return self.is_mini

    def expand_studio_mode(self):
        """Expands back into full Tactical Studio."""
        if self._window:
            self._window.resize(1180, 780)
            self._window.on_top = False
            self.is_mini = False
        return True

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def close_app(self):
        if self._window:
            self._window.destroy()
        os._exit(0)

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def wait_for_server(port=8000, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False

def main():
    # Start backend server in dedicated thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("[Contender] Initializing Native Desktop Shell...")
    wait_for_server(8000)

    # Create native WebView2 window
    window = webview.create_window(
        title="Contender // Tactical Studio",
        url="http://127.0.0.1:8000",
        width=1180,
        height=780,
        min_size=(340, 95),
        resizable=True,
        text_select=True,
        background_color="#0b0c0e"
    )

    api = ContenderNativeAPI(window)
    window.expose(api.toggle_mini_mode, api.expand_studio_mode, api.minimize_window, api.close_app)

    webview.start(debug=False)

if __name__ == "__main__":
    main()
