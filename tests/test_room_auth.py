import time
import unittest

from bin.room_auth import RoomTokenManager


class RoomTokenTests(unittest.TestCase):
    def setUp(self):
        self.manager = RoomTokenManager("segredo-de-teste-com-mais-de-16")

    def test_valid_token(self):
        token = self.manager.create("principal", role="viewer", ttl_seconds=60)
        claims = self.manager.verify(token, expected_room="principal")
        self.assertEqual(claims.room, "principal")
        self.assertEqual(claims.role, "viewer")

    def test_wrong_room(self):
        token = self.manager.create("principal", ttl_seconds=60)
        with self.assertRaises(ValueError):
            self.manager.verify(token, expected_room="outra")

    def test_expired_token(self):
        token = self.manager.create("principal", ttl_seconds=-1)
        with self.assertRaises(ValueError):
            self.manager.verify(token)

    def test_tampered_token(self):
        token = self.manager.create("principal", ttl_seconds=60)
        payload, signature = token.split(".", 1)
        tampered = payload[:-1] + ("A" if payload[-1] != "A" else "B") + "." + signature
        with self.assertRaises(ValueError):
            self.manager.verify(tampered)


if __name__ == "__main__":
    unittest.main()
