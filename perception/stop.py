"""Ask this checkout's perception supervisor to stop and release its webcam."""
from pathlib import Path

Path(__file__).with_name('.stop-request').touch()
print('Stop requested for this checkout. Camera/inference should exit within a second.')
