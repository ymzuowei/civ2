"""Regression: source-font fallback and GitHub blob integrity, no downloads."""
import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import lang_fonts


class CompleteCjkSourceTests(unittest.TestCase):
    def test_git_blob_hash_is_exact(self):
        self.assertEqual(lang_fonts.git_blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")
        self.assertNotEqual(lang_fonts.git_blob_sha(b"hello"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_missing_glyphs_trigger_fallback(self):
        source = SimpleNamespace(getBestCmap=lambda: {ord("文"):1, ord("明"):2})
        self.assertTrue(lang_fonts.font_covers(source, [ord("文"),ord("明")]))
        self.assertFalse(lang_fonts.font_covers(source, [ord("文"),ord("简")]))

    def test_official_full_fonts_have_pinned_git_blob_hashes(self):
        for output in ("NotoSerifTC-Regular.otf", "NotoSansTC-Regular.otf"):
            fonts = lang_fonts.FULL_CJK_FONTS[output]
            self.assertGreaterEqual(len(fonts), 1)
            for name,url,sha in fonts:
                self.assertTrue(name.endswith(".otf"))
                self.assertTrue(url.startswith("https://raw.githubusercontent.com/notofonts/noto-cjk/"))
                self.assertRegex(sha, r"^[0-9a-f]{40}$")
