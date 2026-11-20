"""CIV2-T006: keep pre-existing legacy translation bytes and Display UI keys.

The German and Esperanto language packs are *not UTF-8*: editing them through
text-only Git APIs will corrupt their original code page. These tests work
without any commercial Civilization II files.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_web import lang_file

EXPECTED = {
    'de': ('windows-1252', ['Anzeige', 'Pixelgenau', 'An Fenster anpassen',
                           'Vollbild', 'Vollbild verlassen']),
    'eo': ('iso-8859-3', ['Ekrano', 'Tutaj pikseloj', 'Adapti al fenestro',
                        'Plenekrane', 'Forlasi plenekranon']),
    'la': ('windows-1252', ['Aspectus', 'Puncta integra', 'Ad fenestram aptare',
                           'Plena tegmen', 'Exire e pleno tegmine']),
}
KEYS = ['web.display', 'web.display_integer', 'web.display_fit',
        'web.enter_fullscreen', 'web.exit_fullscreen']


class LegacyLanguageEncodingTests(unittest.TestCase):
    def test_original_locale_codepages_and_all_display_labels(self):
        for code, (expected_cp, expected) in EXPECTED.items():
            path = ROOT / 'data' / 'native' / 'lang' / (code + '.txt')
            with self.subTest(language=code):
                source = path.read_bytes()
                self.assertEqual(source.decode(expected_cp).encode(expected_cp), source)
                cp, entries = lang_file(path)
                self.assertEqual(cp, expected_cp)
                self.assertEqual([entries['openciv2.' + k] for k in KEYS], expected)

    def test_legacy_files_are_not_utf8_reencoded(self):
        for code in ('de', 'eo'):
            data = (ROOT / 'data' / 'native' / 'lang' / (code + '.txt')).read_bytes()
            with self.subTest(language=code):
                with self.assertRaises(UnicodeDecodeError):
                    data.decode('utf-8')


if __name__ == '__main__':
    unittest.main()
