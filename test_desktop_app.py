import os
import sys
import tempfile
import json

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from desktop_shell import WindowStateManager, ContenderNativeAPI, check_single_instance

def run_desktop_app_tests():
    print("=" * 60)
    print("   CONTENDER - DEDICATED DESKTOP APP VERIFICATION")
    print("=" * 60)

    # 1. State Persistence
    print("\n[1/3] Testing Window State Manager & Position Persistence...")
    state = WindowStateManager.load_state()
    assert "studio" in state and "mini" in state
    print(f"  [OK] Default Studio Size: {state['studio']['width']}x{state['studio']['height']}")
    print(f"  [OK] Default Mini HUD Size: {state['mini']['width']}x{state['mini']['height']}")

    state["mini"]["x"] = 100
    state["mini"]["y"] = 200
    WindowStateManager.save_state(state)

    reloaded = WindowStateManager.load_state()
    assert reloaded["mini"]["x"] == 100 and reloaded["mini"]["y"] == 200
    print("  [OK] Successfully saved and reloaded window coordinates.")

    # 2. Single-Instance Mutex
    print("\n[2/3] Testing Single-Instance Mutex...")
    is_first_instance = check_single_instance()
    assert is_first_instance == True
    print("  [OK] Mutex initialized. Single-instance enforcement active.")

    # 3. Native API Mock Bridge
    print("\n[3/3] Testing ContenderNativeAPI Bridge...")
    class MockWindow:
        def __init__(self):
            self.w, self.h = 1180, 780
            self.x, self.y = 0, 0
            self.on_top = False
            self.is_minimized = False
            self.is_destroyed = False
        def resize(self, w, h):
            self.w, self.h = w, h
        def move(self, x, y):
            self.x, self.y = x, y
        def minimize(self):
            self.is_minimized = True
        def show(self):
            pass
        def hide(self):
            pass
        def restore(self):
            self.is_minimized = False
        def destroy(self):
            self.is_destroyed = True

    mock_win = MockWindow()
    api = ContenderNativeAPI(mock_win, WindowStateManager(), reloaded)

    is_mini = api.toggle_mini_mode()
    assert is_mini == True
    assert mock_win.w == 360 and mock_win.h == 105
    assert mock_win.on_top == True
    print("  [OK] Switched to Mini HUD mode (360x105, Always-on-Top).")

    is_mini = api.toggle_mini_mode()
    assert is_mini == False
    assert mock_win.w == 1180 and mock_win.h == 780
    assert mock_win.on_top == False
    print("  [OK] Restored to full Tactical Studio mode (1180x780).")

    api.minimize_window()
    assert mock_win.is_minimized == True
    print("  [OK] Minimize window operation verified.")

    print("\n" + "=" * 60)
    print("   DEDICATED DESKTOP APPLICATION SUBSYSTEMS VERIFIED")
    print("=" * 60)

if __name__ == "__main__":
    run_desktop_app_tests()
