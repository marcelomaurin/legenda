import unittest

from bin.translation import CachedTranslator, Translator


class CountingTranslator(Translator):
    def __init__(self):
        self.calls = 0

    def translate(self, text, source, target):
        self.calls += 1
        return f"{target}:{text}"


class TranslationTests(unittest.TestCase):
    def test_same_language_bypasses_provider(self):
        provider = CountingTranslator()
        translator = CachedTranslator(provider)
        self.assertEqual(translator.translate("oi", "pt-BR", "pt"), "oi")
        self.assertEqual(provider.calls, 0)

    def test_cache(self):
        provider = CountingTranslator()
        translator = CachedTranslator(provider)
        first = translator.translate("oi", "pt", "en")
        second = translator.translate("oi", "pt-BR", "en-US")
        self.assertEqual(first, "en:oi")
        self.assertEqual(second, "en:oi")
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
