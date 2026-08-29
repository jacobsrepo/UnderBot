import unittest
import asyncio
from core.brain import CortexBrain


class TestBrain(unittest.TestCase):
    def setUp(self):
        self.brain = CortexBrain()

    def test_identity(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resp = loop.run_until_complete(self.brain.process_user_message("Cortex, who are you?"))
        self.assertIn("Cortex", resp)
        self.assertIn("assistant", resp.lower())

    def test_web_research_trigger(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resp = loop.run_until_complete(self.brain.process_user_message("search arduino nano pinout"))
        self.assertIn("Arduino Nano", resp)
        self.assertIn("pinout", resp.lower())

    def test_led_mapping_routine(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        events = []

        async def record_event(e):
            events.append(e)

        resp = loop.run_until_complete(self.brain.process_user_message("Map the LEDs on this board", record_event))
        self.assertIn("LED Pin Mapping Complete", resp)
        self.assertTrue(any(e.get("state") == "programming" for e in events))
        self.assertTrue(any(e.get("state") == "seeing" for e in events))


if __name__ == "__main__":
    unittest.main()
