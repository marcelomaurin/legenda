import unittest

from bin.benchmark_stt import normalize_text, word_error_rate


class BenchmarkTests(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(
            normalize_text("Olá, Mundo!"),
            ["olá", "mundo"],
        )

    def test_wer_exact(self):
        self.assertEqual(
            word_error_rate("bom dia a todos", "bom dia a todos"),
            0.0,
        )

    def test_wer_substitution(self):
        self.assertAlmostEqual(
            word_error_rate("bom dia a todos", "bom dia para todos"),
            0.25,
        )

    def test_wer_deletion(self):
        self.assertAlmostEqual(
            word_error_rate("bom dia a todos", "bom dia todos"),
            0.25,
        )

    def test_wer_empty_reference(self):
        self.assertEqual(word_error_rate("", ""), 0.0)
        self.assertEqual(word_error_rate("", "texto"), 1.0)


if __name__ == "__main__":
    unittest.main()
