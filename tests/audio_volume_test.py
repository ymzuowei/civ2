"""CIV2-T008 browser master-audio + city grid tint source contracts.

No original game files, HD pack, AudioContext or network required.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MasterAudioSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host = (ROOT / "src/web/host.js").read_text(encoding="utf-8")
        cls.page = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")
        cls.volume = (ROOT / "src/web/audio_volume.js").read_text(encoding="utf-8")
        cls.grid = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        cls.build = (ROOT / "tools/build_web.py").read_text(encoding="utf-8")

    def test_every_native_web_audio_stream_uses_one_gain_bus(self):
        self.assertEqual(self.host.count("src.connect(audioDestination());"), 2)
        self.assertNotIn("src.connect(audio.destination);", self.host)
        self.assertIn("masterGain = audio.createGain();", self.host)
        self.assertIn("masterGain.connect(audio.destination);", self.host)
        self.assertIn("masterGain.gain.value = opts.audioVolume?.gain ?? 1;", self.host)
        self.assertIn("opts.audioVolume.subscribe((gain)", self.host)
        self.assertIn("masterGain?.disconnect();", self.host)
        self.assertIn("audioVolume: browserAudio", self.page)
        self.assertIn("audioContext: introAudio", self.page)

    def test_toolbar_controls_and_no_input_forwarding(self):
        for needle in ("id=\"audio-volume\"", 'type="range"', 'id="audio-mute"',
                       'aria-pressed="false"', 'id="audio-level"'):
            self.assertIn(needle, self.html)
        self.assertIn("browserAudio.setLevel(", self.page)
        self.assertIn("browserAudio.setMuted(", self.page)
        self.assertIn("controls.addEventListener('keydown', (e) => e.stopPropagation())", self.page)
        self.assertIn("controls.addEventListener('keyup', (e) => e.stopPropagation())", self.page)

    def test_user_owned_game_content_and_autoplay_unchanged(self):
        self.assertIn("openciv2.browser-audio.v1", self.volume)
        self.assertNotIn("new AudioContext", self.volume)
        self.assertNotIn("indexedDB", self.volume)
        self.assertIn("function resumeAudio()", self.host)
        self.assertIn("CIV2_BROWSER_HD_OPENING", self.page)

    def test_city_tint_only_no_geometry_or_alpha_change(self):
        self.assertIn("? 0xfaf8f4u : 0x0b1815u", self.grid)
        self.assertIn("double path[10], stroke = 0.56", self.grid)
        self.assertIn("return 164u;", self.grid)
        self.assertIn("return 104u;", self.grid)
        self.assertIn("strength = radius_tile ? hd_radius_grid_strength(w) : 40u;", self.grid)
        self.assertIn("uint16_t sample = (uint16_t)(a | (radius_tile ? 0x100u : 0u))", self.grid)

    def test_audio_fixture_is_block_scoped(self):
        # Older graphics tests already declare top-level `prefs`. A second
        # top-level const prevented Node from parsing any of the tests.
        unit = (ROOT / "src/web/test/unit.mjs").read_text(encoding="utf-8")
        marker = "// CIV2-T008: one persisted browser preference for effects, music and AVI."
        self.assertEqual(unit.count(marker), 1)
        self.assertIn("{\n" + marker, unit)
        self.assertIn("}\n\nconsole.log('src/web unit tests passed');", unit)

    def test_module_reaches_static_public_build(self):
        self.assertIn("'audio_volume.js'", self.build)
        self.assertIn("import {createAudioVolume, audioLabels} from './audio_volume.js'", self.page)


if __name__ == "__main__":
    unittest.main()
