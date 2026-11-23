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
        cls.wave_port = (ROOT / "src/platform/sound.c").read_text(encoding="utf-8")

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
        # A suspended AudioContext still accepts scheduled BufferSource PCM.
        # Do not report the first Council clip consumed while resume() is pending.
        self.assertIn("export function audioContextCanSchedule(context)", self.host)
        self.assertIn("context.state === 'suspended'", self.host)
        self.assertIn("export function queuedAudioBytes(context, d)", self.host)
        self.assertIn("if (!d || !audioContextCanSchedule(audio))", self.host)
        self.assertIn("return queuedAudioBytes(audio, d);", self.host)
        self.assertIn("council-trace webaudio-queued-suspended", self.host)
        self.assertNotIn("if (!d || !audioOk())", self.host)
        # The B012 >2 GiB pointer bridge must remain in the PCM data path.
        self.assertIn("wasm32Bytes(memory, data, frames * bps * d.ch)", self.host)
        self.assertIn("if (councilTrace && d.end > 0", self.host)
        self.assertIn("council-trace webaudio-queue-gap", self.host)
        self.assertIn("council-trace wasm-block", self.host)
        self.assertIn("if (councilTrace && busy >= 50 && councilLongTasks++ < 40)",
                      self.host)
        self.assertIn("const at = Math.max(audio.currentTime, d.end);", self.host)
        self.assertIn("stats.busyMs += busy;", self.host)
        self.assertNotIn("src.stop(); // skipped audio", self.host)

    def test_waveout_played_bytes_clamped_before_unsigned_subtraction(self):
        # The old uint64_t difference wrapped when WebAudio's time-based
        # rounding said 4097 queued bytes after just 4096 were written:
        # sound_poll instantly completed every WOM_DONE buffer.
        total, remaining = 4096, 4097
        self.assertEqual((total - remaining) & ((1 << 64) - 1),
                         (1 << 64) - 1)
        self.assertEqual(max(0, total - remaining), 0)
        self.assertEqual(max(0, total - total), 0)
        self.assertEqual(max(0, total - 3072), 1024)
        body = self.wave_port.split("static uint64_t played_bytes(WaveOut *w)", 1)[1].split(
            "void sound_poll(void)", 1)[0]
        self.assertIn("uint64_t remaining = host_audio_queued(w->dev);", body)
        self.assertIn("if (remaining >= w->queued_total)", body)
        self.assertIn("return 0;", body)
        self.assertIn("return w->queued_total - remaining;", body)
        self.assertLess(body.index("if (remaining >= w->queued_total)"),
                        body.index("return w->queued_total - remaining;"))
        self.assertIn("stage=wave-queue-overhang", body)
        # Browser side also removes only IEEE-754 near-integer noise, so a
        # 4096-frame first buffer must not appear to have 4097 frames left.
        self.assertIn("Math.ceil(left * d.freq - 1e-7)", self.host)
        browser_unit = (ROOT / "src/web/test/unit.mjs").read_text(encoding="utf-8")
        self.assertIn("firstBufferFrames = 4096", browser_unit)
        self.assertIn("one-sample overhang reproduction", browser_unit)
        self.assertIn("played_bytes(w) >= w->end_bytes[0]", self.wave_port)
        self.assertIn("host_audio_queue(w->dev, hdr->lpData, hdr->dwBufferLength);",
                      self.wave_port)

    def test_log_excludes_user_media_content(self):
        self.assertNotIn("console.info('council-trace wav-data'", self.host)
        self.assertNotIn('plat_log("council-trace media=', self.reports)
        self.assertNotIn('plat_log("council-trace speech=', self.reports)


if __name__ == "__main__":
    unittest.main()
