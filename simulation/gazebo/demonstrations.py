"""Versioned joint demonstrations. Uses only the Python standard library."""
import json
import math
from pathlib import Path
import threading
import time
from datetime import datetime, timezone


def sim_seconds(stats):
    stamp = stats.get('simTime', {})
    return float(stamp.get('sec', 0)) + float(stamp.get('nsec', 0)) * 1e-9


class Recorder:
    def __init__(self, folder, limits, positions, start, metadata=None):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ') + '.jsonl')
        self.file = self.path.open('x', encoding='utf-8')
        self.lock = threading.Lock()
        self.start = start
        self.last = start
        self.count = 0
        header = {'type': 'header', 'version': 2, 'units': 'radians',
                  'environment': 'underbot-r09-native', 'joint_limits': limits,
                  'initial_positions': positions,
                  'timing': 'simulation time from latest world stats; command time is local publish completion'}
        if metadata is not None:
            header['metadata'] = metadata
        self.write(header)

    def write(self, value):
        self.file.write(json.dumps(value, allow_nan=False) + '\n')
        self.file.flush()

    def add(self, kind, stamp, **values):
        with self.lock:
            if self.file.closed:
                return
            if stamp < self.last - 1e-6:
                self.finish_locked('simulation clock reset')
                return
            self.last = stamp
            self.write({'type': kind, 't': stamp - self.start, **values})
            self.count += 1

    def finish_locked(self, reason):
        if not self.file.closed:
            self.write({'type': 'end', 'reason': reason, 'records': self.count})
            self.file.close()

    def finish(self, reason='saved'):
        with self.lock:
            self.finish_locked(reason)


def load_demo(path, limits):
    """Validate the entire file before allowing any replay movement."""
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]
    if len(rows) < 3 or not all(isinstance(row, dict) for row in rows) or rows[0].get('version') not in (1, 2) or rows[0].get('type') != 'header':
        raise ValueError('Not a supported Underbot demonstration')
    header = rows[0]
    if header.get('units') != 'radians' or header.get('environment') != 'underbot-r09-native':
        raise ValueError('Demonstration units or environment do not match')
    if header.get('metadata', {}).get('replayable') is False:
        raise ValueError('This task demonstration is training data and cannot be replayed without its task events')
    if rows[-1].get('type') != 'end' or rows[-1].get('reason') != 'saved':
        raise ValueError('Session was interrupted; record a complete demonstration for replay')
    def validate_pose(pose, complete=False):
        if not isinstance(pose, dict) or (complete and set(pose) != set(limits)):
            raise ValueError('Missing joint positions')
        for name, value in pose.items():
            if name not in limits or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Unknown joint or non-finite position')
            low, high = limits[name]
            if not low <= value <= high:
                raise ValueError(f'{name} exceeds current joint limits')
    validate_pose(header.get('initial_positions'), True)
    commands = []
    last = 0.0
    for row in rows[1:-1]:
        stamp = row.get('t')
        if not isinstance(stamp, (int, float)) or not math.isfinite(stamp) or stamp < last:
            raise ValueError('Invalid demonstration timestamps')
        last = stamp
        if row.get('type') == 'action':
            if 'targets' in row:
                validate_pose(row['targets'], True)
            else:
                validate_pose({row.get('joint'): row.get('target')})
            commands.append(row)
        elif row.get('type') == 'observation':
            # Physics may briefly overshoot limits; observations are never replay targets.
            pose = row.get('positions', {})
            if set(pose) != set(limits) or not all(isinstance(v, (float, int)) and math.isfinite(v) for v in pose.values()):
                raise ValueError('Invalid observation')
        else:
            raise ValueError('Unknown record type')
    if not commands:
        raise ValueError('No commanded movements in this demonstration')
    return header['initial_positions'], commands, last


def replay(transport, path, stop):
    """Best-effort command timing, with feedback-based initial pose settling."""
    pose, commands, duration = load_demo(path, transport.limits)
    def check():
        if stop.is_set() or transport.closed.is_set():
            raise RuntimeError('Replay stopped')
        if time.monotonic() - min(transport.stats_at, transport.positions_at) > 3:
            raise RuntimeError('Replay stopped: simulator feedback lost')
        if transport.stats.get('paused', False):
            raise RuntimeError('Replay stopped: simulator paused')
    check()
    if hasattr(transport, 'publish_pose'):
        transport.publish_pose(pose)
    else:
        for name, value in pose.items():
            check()
            transport.publish(name, value)
    deadline = time.monotonic() + 20
    while any(abs(transport.positions.get(n, math.inf) - v) > 0.06 for n, v in pose.items()):
        check()
        if time.monotonic() > deadline:
            raise RuntimeError('Initial pose did not settle within 20 seconds')
        stop.wait(0.05)
    start = sim_seconds(transport.stats)
    last = start
    def wait_until(target):
        nonlocal last
        deadline = time.monotonic() + 60
        while True:
            check()
            current = sim_seconds(transport.stats)
            if current < last - 1e-6:
                raise RuntimeError('Replay stopped: simulation clock reset')
            last = current
            if current - start >= target:
                return
            if time.monotonic() > deadline:
                raise RuntimeError('Replay stopped: simulation clock stalled or too slow')
            stop.wait(0.03)
    for action in commands:
        wait_until(action['t'])
        if 'targets' in action:
            transport.publish_pose(action['targets'])
        else:
            transport.publish(action['joint'], action['target'])
    wait_until(duration)
