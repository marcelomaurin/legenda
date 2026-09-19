import unittest

from bin.telemetry import Telemetry


class TelemetryTests(unittest.TestCase):
    def test_snapshot_contains_latency_and_clients(self):
        telemetry = Telemetry()
        telemetry.record_event(final=False, latency_ms=100)
        telemetry.record_event(final=True, latency_ms=300)
        telemetry.record_stt_error()
        telemetry.record_translation_error()
        telemetry.record_dropped_partial()

        snap = telemetry.snapshot(
            session_id="sessao",
            room_id="principal",
            room_name="Sala principal",
            engine="faster-whisper",
            event_queue_size=2,
            event_queue_capacity=100,
            stt_queue_size=1,
            stt_queue_capacity=8,
            tcp_clients=1,
            websocket_clients=[
                {"language": "pt-BR", "role": "viewer"},
                {"language": "en", "role": "admin"},
            ],
        )

        self.assertEqual(snap["events"]["final"], 1)
        self.assertEqual(snap["events"]["partial"], 1)
        self.assertEqual(snap["stt"]["latency_avg_ms"], 200.0)
        self.assertEqual(snap["clients"]["websocket"], 2)
        self.assertEqual(snap["clients"]["by_language"]["pt-BR"], 1)
        self.assertEqual(snap["clients"]["by_role"]["admin"], 1)
        self.assertEqual(snap["queues"]["events"]["size"], 2)


if __name__ == "__main__":
    unittest.main()
