import unittest

from bin.mock_caption_server import caption_event


class MockCaptionServerTests(unittest.TestCase):
    def test_emits_caption_v2_shape(self):
        event = caption_event(3, "teste", "sessao")
        self.assertEqual(event["version"], 2)
        self.assertEqual(event["type"], "caption")
        self.assertEqual(event["session_id"], "sessao")
        self.assertEqual(event["sequence"], 3)
        self.assertEqual(event["text"], "teste")
        self.assertTrue(event["final"])
        self.assertEqual(event["engine"], "mock")


if __name__ == "__main__":
    unittest.main()
