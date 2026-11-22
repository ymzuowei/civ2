"""CIV2-R019 opt-in High Council AVI timing diagnostics.

Source-only regression; never bundles or decodes proprietary game media.
Runtime latency and native-vs-browser causality require Owner measurement.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CouncilTraceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = (ROOT / "src/auto/reports.cpp").read_text(encoding="utf-8")
        cls.sound = (ROOT / "src/auto/sound.cpp").read_text(encoding="utf-8")
        cls.video = (ROOT / "src/platform/video.c").read_text(encoding="utf-8")
        cls.main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        cls.host = (ROOT / "src/web/host.js").read_text(encoding="utf-8")

    def test_opt_in_metadata_trace_for_clicked_and_auto_advisors(self):
        self.assertIn('getenv("CIV2_LOG_COUNCIL")', self.reports)
        for state in ("click", "click-seek-start", "click-seek-complete",
                      "click-play-issued", "video-end", "auto-seek-start",
                      "auto-seek-complete", "auto-play-issued"):
            with self.subTest(state=state):
                self.assertIn('council_trace("' + state + '"', self.reports)
        self.assertIn("council_trace", self.reports)
        self.assertIn("speech_line_advisors[self->speech_advisor_index]", self.reports)
        # Do not accidentally remove originally scripted follow-up animation.
        self.assertIn("self->move_video_to_slot", self.reports)
        self.assertIn("self->video.show_frame(", self.reports)
        self.assertIn("self->video.play_range(", self.reports)

    def test_source_distinguishes_open_cost_from_seek_cost(self):
        self.assertIn('stage=avi-open bytes=%ld streams=%d duration_ms=%lu', self.video)
        self.assertIn('stage=avi-seek target=%lu key=%ld preroll=%d decode_ms=%lu', self.sound)
        self.assertIn('stage=audio-ended frame=%lu start=%lu end=%lu ms=%lu', self.sound)
        self.assertIn('getenv("CIV2_LOG_COUNCIL")', self.sound)
        self.assertIn('getenv("CIV2_LOG_COUNCIL")', self.video)
        # Trace is strictly conditional; no change to output codec or AVI semantics.
        self.assertIn("AVIStreamFindSample(", self.sound)
        self.assertIn("avi_decode_frame(player,0x80000000);", self.sound)
        self.assertIn('memcmp(a->data + 8, "AVI ", 4)', self.video)

    def test_browser_flag_only_enabled_by_explicit_query(self):
        self.assertIn("get('councilTrace') === '1'", self.main)
        self.assertIn("env.CIV2_LOG_COUNCIL = '1'", self.main)
        self.assertIn("!introDiagnose && !councilTrace", self.main)
        self.assertIn("audioVolume: browserAudio, councilTrace,", self.main)
        self.assertIn("const councilTrace = !!opts.councilTrace;", self.host)

    def test_web_audio_clock_gap_and_nonblocking_trace(self):
        self.assertIn("if (councilTrace && d.end > 0", self.host)
        self.assertIn("council-trace webaudio-queue-gap", self.host)
        self.assertIn("council-trace wasm-block", self.host)
        self.assertIn("if (councilTrace && busy >= 50 && councilLongTasks++ < 40)",
                      self.host)
        self.assertIn("const at = Math.max(audio.currentTime, d.end);", self.host)
        self.assertIn("stats.busyMs += busy;", self.host)
        self.assertNotIn("src.stop(); // skipped audio", self.host)

    def test_log_excludes_user_media_content(self):
        self.assertNotIn("console.info('council-trace wav-data'", self.host)
        self.assertNotIn('plat_log("council-trace media=', self.reports)
        self.assertNotIn('plat_log("council-trace speech=', self.reports)


if __name__ == "__main__":
    unittest.main()
