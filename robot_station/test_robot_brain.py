import unittest
import subprocess
from unittest.mock import patch
from robot_brain import identity_answer, fetch_plan, memory_snapshot


class BrainTests(unittest.TestCase):
    def setUp(self):
        self.memory = {'available': True, 'people': ['Sam Jacob']}

    def test_identity_comes_from_database(self):
        self.assertIn('Sam Jacob', identity_answer('Who is Sam?', self.memory))
        self.assertIn('Alex Green', identity_answer('Who is Alex?', {'available': True, 'people': ['Alex Green']}))

    def test_unknown_does_not_invent_identity(self):
        self.assertIn('no matching', identity_answer('Who is Alfred?', self.memory))

    def test_offline_does_not_guess(self):
        self.assertIn('unavailable', identity_answer('Who is Sam?', {'available': False}))

    def test_ambiguous_first_name_needs_clarification(self):
        self.assertIn('multiple', identity_answer('Who is Sam?', {'available': True, 'people': ['Sam Jacob', 'Sam Jones']}))

    def test_plan_never_executes_and_marks_unknown_recipient(self):
        plan = fetch_plan('Bring Alfred the red ball.', self.memory)
        self.assertFalse(plan['executable'])
        self.assertEqual(len(plan['steps']), 7)
        self.assertTrue(any('Recipient' in b for b in plan['blockers']))

    def test_plan_resolves_enrolled_recipient(self):
        plan = fetch_plan('Bring Sam the red ball.', self.memory)
        self.assertEqual(plan['steps'][-1]['target'], 'Sam Jacob')

    def test_failed_memory_process_is_handled(self):
        with patch('subprocess.run', side_effect=TimeoutError):
            self.assertFalse(memory_snapshot('python', 'config')['available'])

    def test_memory_timeout_is_distinguishable(self):
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('helper', 20)):
            result = memory_snapshot('python', 'config')
        self.assertEqual(result['error_code'], 'helper_timeout')
        self.assertIn('timed out', identity_answer('Who is Sam?', result))

    def test_helper_failure_does_not_expose_stderr(self):
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'secret DSN')):
            result = memory_snapshot('python', 'config')
        self.assertEqual(result['error_code'], 'helper_exit')
        self.assertNotIn('secret', str(result))
