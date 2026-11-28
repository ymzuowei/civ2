"""T025 source contract: the browser Council decoder must never stall legacy playback."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CouncilShadowIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(path):
            return (ROOT / path).read_text(encoding="utf-8")
        cls.video = read("src/platform/video.c")
        cls.sound = read("src/auto/sound.cpp")
        cls.header = read("src/host/host.h")
        cls.host = read("src/web/host.js")
        cls.trial = read("src/web/council_native_trial.js")
        cls.bridge = read("src/web/council_host_bridge.js")
        cls.ranges = read("src/web/council_range_provider.js")
        cls.main = read("src/web/main.js")
        cls.pair = read("src/web/council_local_pair.js")
        cls.build = read("tools/build_web.py")

    def test_shadow_callback_runs_after_original_visible_decode(self):
        body = self.sound.split("int __cdecl avi_decode_frame", 1)[1].split("\n}", 1)[0]
        legacy = body.index("result = avi_ic_decompress_ex(")
        shadow = body.index("plat_council_shadow_frame(")
        self.assertGreater(shadow, legacy)
        self.assertIn("result == 0 && decode_flags == 0 && player->transparent == 0", body)
        self.assertIn('getenv("CIV2_T025_COUNCIL_SHADOW")', body)
        self.assertIn("draw_frame(c, &fr, d);", self.video)

    def test_exact_source_gate_and_nonblocking_native_import(self):
        self.assertIn('memcmp(a->data, "RIFF", 4)', self.video)
        for name in ("COUNCIL0.AVI","COUNCIL1.AVI","COUNCIL2.AVI"):
            self.assertIn(name, self.video)
        self.assertIn('getenv("CIV2_T025_COUNCIL_ERA")', self.video)
        self.assertIn("selected && !strcasecmp(base, selected)", self.video)
        self.assertIn("host_council_open(a->data, (uint32_t)a->size)", self.video)
        self.assertIn("host_council_frame(frame, last, (uint32_t)w, (uint32_t)h)", self.video)
        self.assertIn("int HOST_API(host_council_frame)(uint32_t frame, uint32_t last, uint32_t width, uint32_t height);",
                      self.header)
        self.assertNotIn("council_rgba", self.video)
        self.assertIn("if (a->council_trial) host_council_close();", self.video)
        self.assertIn("host_council_frame: (frame,last,width,height)", self.host)
        self.assertIn("councilTrial.schedule(frame>>>0,last>>>0,width>>>0,height>>>0)", self.host)
        self.assertNotIn("return councilTrial.prepare(frame", self.host)

    def test_latest_frame_scheduler_is_bounded_and_nonblocking(self):
        for token in ("queued=null", "pumping=false", "counters.dropped++",
                      "counters.scheduled++", "void pump()", "width!==clip.config.codedWidth",
                      "height!==clip.config.codedHeight"):
            self.assertIn(token, self.trial)
        self.assertIn("host_council_frame", self.host)
        self.assertIn("councilTrial.dispose();", self.host)

    def test_decoder_and_canvas_resources_are_released(self):
        for token in ("MAX_FRAMES=16", "MAX_RGBA_ESTIMATE=16*1024*1024",
                      "frame.close()", "previous.close()", "payload=null",
                      "samples.length=0", "gops.length=0"):
            self.assertIn(token, self.ranges)
        for token in ("old?.close()", "prepared=null", "canvas.width=0",
                      "canvas.height=0", "discard(ticket)"):
            self.assertIn(token, self.bridge)
        self.assertIn("dispose(){close();clip=null;changed();}", self.trial)

    def test_visible_trial_exact_frame_and_original_opacity_gate(self):
        self.assertIn("fr->mask || fr->has_transparency", self.video)
        self.assertIn("host_council_take(render_frame, (uint32_t)fr->width, (uint32_t)fr->height, c->render_pixels", self.video)
        self.assertIn("draw_frame_rgb(c, fr, d, c->render_pixels)", self.video)
        self.assertIn("free(c->render_pixels)", self.video)
        self.assertIn("plat_council_render_begin(", self.sound)
        self.assertIn("plat_council_render_end();", self.sound)
        self.assertIn("slot.frame!==frame", self.trial)
        self.assertIn("slot=null", self.trial)
        self.assertIn("query.get('councilRender')==='1'", self.main)

    def test_owner_local_entry_and_built_module(self):
        self.assertIn("query.get('councilShadow') === '1'", self.main)
        self.assertIn("['localhost','127.0.0.1'].includes(location.hostname)", self.main)
        self.assertIn("verifyCouncilShadowPair", self.pair)
        self.assertIn("配对清单 JSON", self.pair)
        self.assertIn("Transcoded MP4", self.pair)
        self.assertIn("'council_local_pair.js'", self.build)


if __name__ == "__main__":
    unittest.main()
