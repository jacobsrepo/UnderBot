import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from demonstrations import Recorder, load_demo, replay


class DemonstrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.limits = {'elbow': (-1, 1)}

    def record(self):
        recorder = Recorder(self.temp.name, self.limits, {'elbow': 0}, 10)
        recorder.add('observation', 10, positions={'elbow': 0})
        recorder.add('action', 10.1, joint='elbow', target=0.2)
        recorder.add('observation', 10.3, positions={'elbow': 0.18})
        recorder.finish()
        return recorder.path

    def test_roundtrip_distinguishes_action_from_measurement(self):
        pose, commands, duration = load_demo(self.record(), self.limits)
        self.assertEqual(pose, {'elbow': 0})
        self.assertEqual(commands[0]['target'], 0.2)
        self.assertAlmostEqual(duration, 0.3)

    def test_full_vector_action_roundtrip(self):
        recorder = Recorder(self.temp.name, self.limits, {'elbow': 0}, 10)
        recorder.add('action', 10.1, targets={'elbow': 0.2}, positions={'elbow': 0.01})
        recorder.finish()
        _, commands, _ = load_demo(recorder.path, self.limits)
        self.assertEqual(commands[0]['targets'], {'elbow': 0.2})
        self.assertEqual(commands[0]['positions'], {'elbow': 0.01})

    def test_task_metadata_is_saved_and_blocks_incomplete_replay(self):
        metadata = {'task': 'pick_place', 'replayable': False, 'grasp_assist': True}
        recorder = Recorder(self.temp.name, self.limits, {'elbow': 0}, 10, metadata)
        recorder.add('action', 10.1, targets={'elbow': 0.2})
        recorder.finish()
        header = json.loads(recorder.path.read_text().splitlines()[0])
        self.assertEqual(header['metadata'], metadata)
        with self.assertRaisesRegex(ValueError, 'training data'):
            load_demo(recorder.path, self.limits)

    def test_limits_and_nonfinite_rejected_before_replay(self):
        for target in (2, float('nan')):
            path = self.record()
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            rows[2]['target'] = target
            path.write_text('\n'.join(json.dumps(row) for row in rows))
            with self.assertRaises(ValueError):
                load_demo(path, self.limits)

    def test_clock_reset_leaves_unreplayable_record(self):
        recorder = Recorder(self.temp.name, self.limits, {'elbow': 0}, 10)
        recorder.add('action', 9, joint='elbow', target=0.2)
        self.assertTrue(recorder.file.closed)
        with self.assertRaises(ValueError):
            load_demo(recorder.path, self.limits)

    def test_truncated_record_rejected(self):
        path = self.record()
        path.write_text('\n'.join(path.read_text().splitlines()[:-1]))
        with self.assertRaises(ValueError):
            load_demo(path, self.limits)

    def test_replay_and_cancel(self):
        class FakeTransport:
            limits = self.limits
            closed = threading.Event()
            positions = {'elbow': 0}
            sent = []
            stats_at = positions_at = time.monotonic()
            @property
            def stats(self):
                elapsed = time.monotonic() - self.stats_at
                return {'simTime': {'sec': int(elapsed), 'nsec': int((elapsed % 1) * 1e9)}}
            def publish(self, name, value):
                self.sent.append((name, value))
                self.positions[name] = value
        transport = FakeTransport()
        stop = threading.Event()
        replay(transport, self.record(), stop)
        self.assertEqual(transport.sent, [('elbow', 0), ('elbow', 0.2)])
        stop.set()
        with self.assertRaisesRegex(RuntimeError, 'stopped'):
            replay(transport, self.record(), stop)
        self.assertEqual(len(transport.sent), 2)


if __name__ == '__main__':
    unittest.main()
