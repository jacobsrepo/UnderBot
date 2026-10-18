import io
import json
import unittest
from unittest.mock import patch
from ai_backend import chat


class ChatTests(unittest.TestCase):
    def test_request_is_bounded_text_only(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"message":{"content":"Hello"}}')) as call:
            self.assertEqual(chat('http://localhost:11435', 'qwen2.5:1.5b', 'Hi', 'demo'), 'Hello')
        request = call.call_args.args[0]
        body = json.loads(request.data)
        self.assertFalse(body['stream'])
        self.assertNotIn('tools', body)
        self.assertEqual(body['options']['num_predict'], 192)
        self.assertEqual(call.call_args.kwargs['timeout'], 150)

    def test_empty_reply_fails(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"message":{"content":""}}')):
            with self.assertRaises(ValueError):
                chat('http://localhost', 'qwen', 'Hi', 'demo')

    def test_oversized_reply_fails(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'x' * 131073)):
            with self.assertRaises(ValueError):
                chat('http://localhost', 'qwen', 'Hi', 'demo')

    def test_connection_failure_propagates(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                chat('http://localhost', 'qwen', 'Hi', 'demo')
