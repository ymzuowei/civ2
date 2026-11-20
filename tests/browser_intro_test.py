"""CIV2-B006: browser first-start intro policy, no private CD media required."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrowserOpeningTests(unittest.TestCase):
    def test_native_skip_is_narrow_and_preserves_original_path(self):
        game = (ROOT / "src/auto/game.cpp").read_text(encoding="utf-8")
        start = game.index("void __cdecl intro_play_opening_video(void)")
        end = game.index("void __cdecl intro_video_on_end(void)", start)
        intro = game[start:end]
        self.assertIn('getenv("CIV2_SKIP_OPENING")', intro)
        self.assertIn("hd_art ||", intro)
        self.assertIn("player.palette.new_version()", intro)
        self.assertIn("player.play()", intro)
        self.assertIn("intro_video_on_click", intro)
        self.assertNotIn("setPointerCapture", intro)
        self.assertEqual(game.count('getenv("CIV2_SKIP_OPENING")'), 1)

    def test_browser_original_movie_has_gesture_gate_and_explicit_skip(self):
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        options = (ROOT / "src/web/options.js").read_text(encoding="utf-8")
        host = (ROOT / "src/web/host.js").read_text(encoding="utf-8")
        self.assertIn("skipBrowserOpening(location.search)", main)
        self.assertIn("env.CIV2_SKIP_OPENING = '1'", main)
        self.assertIn("get('intro') === 'skip'", options)
        self.assertIn("openingVideoNeedsGesture(entries, hdArtAvailable, location.search)", main)
        self.assertIn("hd && !!window.civ2Hd?.packBytes", main)
        self.assertIn("window.civ2Intro = {", main)
        self.assertIn("ownedOpeningPresent:", main)
        self.assertIn("audio: introNeedsGesture ? 'pending' : 'not-required'", main)
        self.assertIn("!hd && !skipBrowserOpening(search)", options)
        self.assertIn("unlockOpeningAudio()", main)
        self.assertIn("audioContext: introAudio", main)
        self.assertIn("opts.audioContext || null", host)
        self.assertIn("resumeOpeningAudioContext(audio)", main)
        self.assertIn("env.CIV2_NOSOUND = '1'", main)
        sound = (ROOT / "src/auto/sound.cpp").read_text(encoding="utf-8")
        self.assertIn('getenv("CIV2_LOG_VIDEO")', sound)
        self.assertIn("last_video_trace_ms", sound)
        self.assertIn('video: clock playing=', sound)
        self.assertNotIn("video: raw bytes", sound)
        self.assertNotIn("civ2ClickToSkip", main)
        self.assertNotIn("store.clear()", main[main.index("const env = {CIV2_DATA:"):main.index("if (window.civ2Test)", main.index("const env = {CIV2_DATA:"))])

    def test_original_intro_remains_explicitly_testable(self):
        docs = (ROOT / "docs/BROWSER.md").read_text(encoding="utf-8")
        self.assertIn("?intro=play", docs)
        self.assertIn("CIV2-B006", docs)
        self.assertIn("owner", docs.lower())


if __name__ == "__main__":
    unittest.main()
