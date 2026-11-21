"""CIV2-T006: no missing-resource probes during local BYO game startup."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_web import mark_bundled_game, SITE_GAME_MARKER


class BrowserOptionalResources(unittest.TestCase):
    def test_build_site_mode_stamps_only_bundled_game_html(self):
        with tempfile.TemporaryDirectory(prefix="civ2-byo-html-") as td:
            page = Path(td) / "index.html"
            original = "<head>" + SITE_GAME_MARKER + "</head>"
            page.write_text(original, encoding="utf-8")
            mark_bundled_game(str(page), False)
            self.assertEqual(page.read_text(encoding="utf-8"), original)
            mark_bundled_game(str(page), True)
            self.assertIn('name="openciv2-bundled-game" content="1"',
                          page.read_text(encoding="utf-8"))
            self.assertEqual(page.read_text(encoding="utf-8").count("openciv2-bundled-game"), 1)

    def test_missing_or_duplicate_mode_marker_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="civ2-site-marker-") as td:
            page = Path(td) / "index.html"
            for content in ("<head></head>", SITE_GAME_MARKER * 2):
                page.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "bundled-game HTML marker"):
                    mark_bundled_game(str(page), False)

    def test_no_expected_404_or_eager_relay_in_solo_page(self):
        html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        net = (ROOT / "src/web/net.js").read_text(encoding="utf-8")
        self.assertIn(SITE_GAME_MARKER, html)
        self.assertIn('<link rel="icon" href="data:,">', html)
        self.assertIn("siteBundlesGame(document)", main)
        self.assertIn("fetch('game/index.json'", main)
        self.assertIn("const ensureInfo = () => {", net)
        self.assertLess(net.index("const ensureInfo = () => {"), net.index("tcpListen:"))
        self.assertIn("            ensureInfo();", net)
        self.assertNotIn("    if (relay && WS) {", net)


if __name__ == "__main__":
    unittest.main()
