import unittest
from devices.serial_device import SerialDevice


class TestDevices(unittest.TestCase):
    def setUp(self):
        self.device = SerialDevice()

    def test_checksum_calculation(self):
        # cmd=1 (SET_PIN), pin=3, val=1 -> 1 ^ 3 ^ 1 = 3
        cs = self.device._calc_checksum(1, 3, 1)
        self.assertEqual(cs, 3)

    def test_pin_actuation(self):
        self.device.set_pin(3, 1)
        self.assertEqual(self.device.read_pin(3), 1)

        self.device.set_pin(3, 0)
        self.assertEqual(self.device.read_pin(3), 0)

    def test_set_all_low(self):
        self.device.set_pin(2, 1)
        self.device.set_pin(5, 1)
        self.device.set_all_low()
        states = self.device.get_all_states()
        self.assertTrue(all(v == 0 for v in states.values()))


if __name__ == "__main__":
    unittest.main()
