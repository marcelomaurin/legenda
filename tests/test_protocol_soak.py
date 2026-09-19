import unittest

from bin.protocol_soak import run_soak


class ProtocolSoakTests(unittest.TestCase):
    def test_thousand_events_without_loss(self):
        result = run_soak(1000, payload_size=128)
        self.assertEqual(result["sent"], 1000)
        self.assertEqual(result["received"], 1000)
        self.assertEqual(result["lost"], 0)
        self.assertEqual(result["malformed"], 0)
        self.assertEqual(result["send_errors"], [])
        self.assertEqual(result["last_sequence"], 1000)


if __name__ == "__main__":
    unittest.main()
