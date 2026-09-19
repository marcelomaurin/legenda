import unittest

from bin.security_utils import (
    bearer_matches,
    is_loopback_host,
    require_token_for_remote_bind,
)


class SecurityUtilsTests(unittest.TestCase):
    def test_bearer_matches(self):
        self.assertTrue(bearer_matches("Bearer segredo", "segredo"))
        self.assertFalse(bearer_matches("Bearer errado", "segredo"))
        self.assertTrue(bearer_matches("", ""))

    def test_loopback_detection(self):
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertTrue(is_loopback_host("localhost"))
        self.assertFalse(is_loopback_host("0.0.0.0"))
        self.assertFalse(is_loopback_host("192.168.1.10"))

    def test_remote_bind_requires_token(self):
        with self.assertRaises(ValueError):
            require_token_for_remote_bind("0.0.0.0", "", "teste")
        require_token_for_remote_bind("0.0.0.0", "segredo", "teste")
        require_token_for_remote_bind("127.0.0.1", "", "teste")


if __name__ == "__main__":
    unittest.main()
