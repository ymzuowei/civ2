"""CIV2-T008/T017 browser master+separate music/effects audio contracts.

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

    def test_native_audio_streams_are_routed_to_independent_channels(self):
        self.assertEqual(self.host.count("src.connect(audioDestination('music'));"), 1)
        self.assertEqual(self.host.count("src.connect(audioDestination('effects'));"), 1)
        self.assertNotIn("src.connect(audioDestination());", self.host)
        self.assertIn("musicGain = audio.createGain();", self.host)
        self.assertIn("effectsGain = audio.createGain();", self.host)
        self.assertIn("musicGain.connect(masterGain);", self.host)
        self.assertIn("effectsGain.connect(masterGain);", self.host)
        self.assertIn("musicGain?.disconnect();", self.host)
        self.assertIn("effectsGain?.disconnect();", self.host)
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
                       'aria-pressed="false"', 'id="audio-level"',
                       'id="audio-music"', 'id="audio-effects"', 'id="audio-mixer-panel"',
                       'id="audio-mixer-toggle"', 'aria-expanded="false"'):
            self.assertIn(needle, self.html)
        self.assertIn("browserAudio.setLevel(", self.page)
        self.assertIn("browserAudio.setMusicLevel(", self.page)
        self.assertIn("browserAudio.setEffectsLevel(", self.page)
        self.assertIn("setMixerOpen(", self.page)
        self.assertIn("musicGain.gain.value = opts.audioVolume.musicGain;", self.host)
        self.assertIn("effectsGain.gain.value = opts.audioVolume.effectsGain;", self.host)
        self.assertIn(".audio-mixer-panel", self.html)
        self.assertIn("browserAudio.setMuted(", self.page)
        self.assertIn("controls.addEventListener('keydown', (e) => e.stopPropagation())", self.page)
        self.assertIn("controls.addEventListener('keyup', (e) => e.stopPropagation())", self.page)

    def test_t012_mute_is_high_contrast_svg_and_fold_toggle_accessible(self):
        toolbar = (ROOT / "src/web/toolbar.js").read_text(encoding="utf-8")
        for marker in ('id="game-controls-content"', 'id="controls-toggle"',
                       'aria-controls="game-controls-content"',
                       'aria-expanded="true"', 'id="controls-toggle-chevron"',
                       'id="audio-waves"', 'id="audio-slash"',
                       '#game-controls #audio-mute[aria-pressed="true"]',
                       '#game-controls .icon-button'):
            self.assertIn(marker, self.html)
        self.assertNotIn("🔊", self.html)
        self.assertNotIn("🔇", self.html)
        self.assertNotIn("audioMute.textContent =", self.page)
        for marker in ("content.hidden = collapsed",
                       "browserToolbar.setCollapsed(", "syncToolbar();",
                       "chevron.setAttribute('d'", "$('audio-waves').style.display = muted ? 'none' : ''",
                       "$('audio-slash').style.display = muted ? '' : 'none'",
                       "mode.title = hint", "syncDisplayHelp();"):
            self.assertIn(marker, self.page)
        self.assertIn("openciv2.browser-toolbar.v1", toolbar)
        self.assertIn("getItem(TOOLBAR_KEY) === 'collapsed'", toolbar)
        self.assertIn("setItem(TOOLBAR_KEY", toolbar)
        self.assertNotIn("indexedDB", toolbar)
        self.assertNotIn("new AudioContext", toolbar)
        self.assertIn("import {createToolbarCollapse, toolbarLabels} from './toolbar.js'", self.page)
        self.assertIn("'toolbar.js'", self.build)

    def test_t012_display_help_explains_matching_scale_without_changing_math(self):
        toolbar = (ROOT / "src/web/toolbar.js").read_text(encoding="utf-8")
        host = (ROOT / "src/web/host.js").read_text(encoding="utf-8")
        self.assertIn('aria-describedby="display-help"', self.html)
        self.assertIn('id="display-help"', self.html)
        self.assertIn('Pixel perfect: prefer whole-number pixel scaling', toolbar)
        self.assertIn('两种模式可能看起来相同', toolbar)
        self.assertIn("mode === 'fit' || available < 1 ? available : Math.floor(available)", host)
        self.assertIn("window.dispatchEvent(new Event('civ2-display-change'))", self.page)
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
