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
        self.assertIn('getenv("CIV2_BROWSER_HD_OPENING")', intro)
        self.assertIn("hd_art && !(browser_hd_opening &&", intro)
        self.assertIn("browser_skip_intro && browser_skip_intro[0] == '1'", intro)
        self.assertNotIn("hd_art ||", intro)
        self.assertIn("player.palette.new_version()", intro)
        self.assertIn("player.play()", intro)
        self.assertIn("intro_video_on_click", intro)
        self.assertNotIn("setPointerCapture", intro)
        self.assertEqual(game.count('getenv("CIV2_SKIP_OPENING")'), 1)
        self.assertEqual(game.count('getenv("CIV2_BROWSER_HD_OPENING")'), 1)
        # Native original-HD skip is the fallback: browser opt-in is explicit.
        self.assertIn("browser_hd_opening[0] == '1' && !browser_hd_opening[1]", intro)

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
        self.assertIn("return !skipBrowserOpening(search) && openingVideoPresent(entries)", options)
        self.assertIn("env.CIV2_BROWSER_HD_OPENING = '1'", main)
        self.assertIn("hdMovieOptIn = hdArtAvailable && introNeedsGesture", main)
        self.assertIn("hdMovieOptIn,", main)
        self.assertIn("unlockOpeningAudio()", main)
        self.assertIn("audioContext: introAudio", main)
        self.assertIn("opts.audioContext || null", host)
        self.assertIn("resumeOpeningAudioContext(audio)", main)
        self.assertIn("env.CIV2_NOSOUND = '1'", main)
        fetch = (ROOT / "tools/fetch-toolchain.sh").read_text(encoding="utf-8")
        self.assertIn("CIV2_TOOLCHAIN_ARCHIVE_DIR", fetch)
        self.assertIn("CIV2_LOCAL_TOOLCHAIN_ARCHIVE=", fetch)
        self.assertIn("520273336", fetch)
        self.assertIn("tar -tzf", fetch)
        self.assertIn("mktemp -d", fetch)
        self.assertIn("curl -fL# --retry 5 --retry-all-errors --retry-delay 5 -C - -o", fetch)
        self.assertNotIn(" | tar xz", fetch)
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
