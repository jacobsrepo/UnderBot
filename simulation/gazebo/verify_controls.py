"""Integration check against the running, isolated Gazebo simulation."""
import json
import math
import time
from controls import Transport, ROOT


def wait_for(predicate, description, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise RuntimeError(f'Timed out: {description}')


def main():
    transport = Transport()
    name = 'left_elbow_joint'
    original = None
    was_paused = True
    try:
        wait_for(lambda: transport.stats_at > 0, 'Gazebo status')
        was_paused = transport.stats.get('paused', False)
        for invalid in (float('nan'), 100.0):
            try:
                transport.publish(name, invalid)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid target was accepted')
        transport.control(False)
        wait_for(lambda: name in transport.positions, 'initial joint feedback')
        original = transport.positions[name]
        transport.submit(name, 0.25)
        wait_for(lambda: abs(transport.positions.get(name, -100) - 0.25) < 0.05,
                 'elbow reaches slider target')
        achieved = transport.positions[name]
        transport.control(True)
        wait_for(lambda: transport.stats.get('paused'), 'pause acknowledgement')
        report = {'target_rad': 0.25, 'measured_rad': achieved,
                  'measured_degrees': math.degrees(achieved),
                  'invalid_targets_rejected': True, 'pause_verified': True}
        (ROOT / 'generated/control-verification.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
    finally:
        try:
            if original is not None:
                transport.publish(name, original)
                transport.control(False)
                wait_for(lambda: abs(transport.positions.get(name, -100) - original) < 0.05,
                         'restore initial arm pose')
            transport.control(was_paused)
        finally:
            transport.close()


if __name__ == '__main__':
    main()
