"""Live smoke check: record a small elbow movement, replay, and leave paused."""
import json
import threading
import time
import tkinter as tk

from controls import Panel, ROOT
from demonstrations import load_demo, replay


def main():
    window = tk.Tk()
    window.withdraw()
    panel = Panel(window)
    t = panel.transport
    def wait_for(predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            window.update()
            if predicate():
                return
            time.sleep(0.03)
        raise RuntimeError('Live demonstration verification timed out')
    try:
        wait_for(lambda: t.stats_at > 0)
        t.control(False)
        wait_for(lambda: len(t.positions) == len(t.limits) and not t.stats.get('paused', False))
        # Start from a repeatable neutral pose, rather than a transient startup pose.
        for name in t.limits:
            t.publish(name, 0)
        wait_for(lambda: all(abs(v) < 0.06 for v in t.positions.values()))
        panel.record_demo()
        assert t.recorder is not None, panel.demo_status.cget('text')
        name = 'left_elbow_joint'
        panel.variables[name].set(10)
        panel.send(name)
        wait_for(lambda: abs(t.positions[name] - 0.174533) < 0.05)
        panel.save_demo()
        path = panel.last_demo
        pose, commands, duration = load_demo(path, t.limits)
        assert commands and duration > 0
        stop = threading.Event()
        replay(t, path, stop)
        target = commands[-1]['targets'][name]
        wait_for(lambda: abs(t.positions[name] - target) < 0.05)
        report = {'file': str(path), 'commands': len(commands), 'duration_sim_seconds': duration,
                  'target_rad': target, 'measured_rad': t.positions[name],
                  'record_and_replay_passed': True}
        (ROOT / 'generated/demonstration-verification.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        try:
            t.control(True)
        finally:
            panel.close()


if __name__ == '__main__':
    main()
