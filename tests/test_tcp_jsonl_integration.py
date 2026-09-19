import json
import socket
import threading
import unittest

from bin.mock_caption_server import serve_client


class TcpJsonlIntegrationTests(unittest.TestCase):
    def test_receives_complete_jsonl_frames(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        error = []

        def worker():
            try:
                client, _ = server.accept()
                with client:
                    serve_client(client, 3, 0.0, "session-test")
            except Exception as exc:
                error.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=worker)
        thread.start()

        received = b""
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            client.settimeout(3)
            while received.count(b"\n") < 3:
                chunk = client.recv(4096)
                if not chunk:
                    break
                received += chunk

        thread.join(timeout=3)

        self.assertFalse(error)
        lines = [line for line in received.decode("utf-8").splitlines() if line]
        self.assertEqual(len(lines), 3)

        events = [json.loads(line) for line in lines]
        self.assertTrue(all(event["version"] == 2 for event in events))
        self.assertTrue(all(event["type"] == "caption" for event in events))
        self.assertEqual([event["sequence"] for event in events], [1, 2, 3])
        self.assertTrue(all(event["session_id"] == "session-test" for event in events))


if __name__ == "__main__":
    unittest.main()
