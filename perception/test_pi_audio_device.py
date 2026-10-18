import unittest
from unittest.mock import patch
import pi_audio_device as device


class AudioDeviceTests(unittest.TestCase):
    def test_playback_uses_requested_native_rate(self):
        with patch('sys.argv', ['pi_audio_device', 'play', '--rate', '48000']), \
             patch.object(device, 'microphone', return_value='real_microphone'), \
             patch.object(device, 'pulse', return_value=[{'name': 'bluez_sink.DD_66_D6_29_BA_CD.handsfree_head_unit'}]), \
             patch.object(device.os, 'execvp') as execute:
            device.main()
        program, arguments = execute.call_args.args
        self.assertEqual(program, 'paplay')
        self.assertIn('--rate=48000', arguments)
        self.assertIn('--channels=1', arguments)

    def test_speaker_monitor_is_not_used_as_microphone(self):
        card = {'name': device.CARD, 'active_profile': 'handsfree_head_unit',
                'profiles': {'handsfree_head_unit': {'sources': 1, 'available': True}}}
        with patch.object(device, 'pulse', side_effect=[[card], [{'name': 'bluez_sink.DD_66_D6_29_BA_CD.monitor'}]]):
            with self.assertRaisesRegex(RuntimeError, 'No unique Bluetooth microphone'):
                device.microphone()

    def test_capture_defaults_to_16khz(self):
        with patch('sys.argv', ['pi_audio_device', 'capture']), \
             patch.object(device, 'microphone', return_value='real_microphone'), \
             patch.object(device.os, 'execvp') as execute:
            device.main()
        self.assertIn('--rate=16000', execute.call_args.args[1])
