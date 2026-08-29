import unittest
import os
import tempfile
from memory.conversation import ConversationMemory
from memory.knowledge import KnowledgeMemory


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.conv = ConversationMemory(db_path=self.temp_db.name)
        self.know = KnowledgeMemory(db_path=self.temp_db.name)

    def tearDown(self):
        self.conv = None
        self.know = None
        import gc
        gc.collect()
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_conversation_history(self):
        self.conv.add_message("user", "Hello Cortex")
        self.conv.add_message("assistant", "Greetings.")
        history = self.conv.get_recent_history(limit=5)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello Cortex")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Greetings.")

    def test_knowledge_persistence(self):
        self.know.save_fact("pin_mapping", "D3", "Red LED - Second from left")
        val = self.know.get_fact("pin_mapping", "D3")
        self.assertEqual(val, "Red LED - Second from left")

        # Update fact
        self.know.save_fact("pin_mapping", "D3", "Red LED - Verified")
        val2 = self.know.get_fact("pin_mapping", "D3")
        self.assertEqual(val2, "Red LED - Verified")

        # Search facts
        results = self.know.search_facts("Red LED")
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["key"], "D3")


if __name__ == "__main__":
    unittest.main()
