"""B012: closed-window bitmap teardown and bounded native memory telemetry.

Source-only guards: the separate Windows WASM build and real saved-game
regression remain mandatory. Never reads licensed media or saved games.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class B012WindowMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.window = (ROOT / "src/platform/window.c").read_text("utf-8")
        cls.gdi = (ROOT / "src/platform/gdi.c").read_text("utf-8")
        cls.hd = (ROOT / "src/platform/hd.c").read_text("utf-8")
        cls.host = (ROOT / "src/web/host.js").read_text("utf-8")
        cls.build = (ROOT / "tools/build_native.py").read_text("utf-8")

    def test_wm_ncdestroy_precedes_teardown_and_window_shell_is_retained(self):
        body = self.window.split("static void destroy_storage(Window *w)", 1)[1].split(
            "WINBOOL WINAPI DestroyWindow", 1
        )[0]
        for needle in (
            "wnd_send(w, WM_NCDESTROY, 0, 0);",
            "DeleteDC(w->own_dc);",
            "bmp_destroy(w->surf);",
            "w->surf = NULL;",
            "free(w->text);",
            "w->text = NULL;",
            "free(w->extra);",
            "w->extra = NULL;",
            "closed_windows++;",
        ):
            self.assertIn(needle, body)
        self.assertLess(body.index("WM_NCDESTROY"), body.index("DeleteDC(w->own_dc)"))
        self.assertLess(body.index("obj_free(h);"), body.index("bmp_destroy(w->surf);"))
        self.assertNotIn("free(w);", body)  # outstanding DCs may still point to shell
        self.assertIn("if (w->own_dc)", body)

    def test_gdi_and_hd_live_counters_follow_allocation_and_free(self):
        for needle in (
            "bitmap_live_bytes +=",
            "bitmap_live_bytes -=",
            "bitmap_live_count++",
            "bitmap_live_count--",
            "plat_diag_bitmap_bytes",
            "plat_diag_bitmap_count",
            "hd_bitmap_free(b);",
        ):
            self.assertIn(needle, self.gdi)
        for needle in (
            "hd_live_bytes +=",
            "hd_live_bytes -=",
            "hd_live_planes++",
            "hd_live_planes--",
            "plat_diag_hd_bytes",
            "plat_diag_hd_planes",
            "if (b->hd && b->hd_prev && b->hd_big",
        ):
            self.assertIn(needle, self.hd)

    def test_only_telemetry_exports_no_game_asset_output(self):
        for key in (
            "plat_diag_bitmap_bytes", "plat_diag_bitmap_count",
            "plat_diag_hd_bytes", "plat_diag_hd_planes",
            "plat_diag_closed_windows",
        ):
            self.assertIn("--export=" + key, self.build)
            self.assertIn("exports." + key, self.host)
        self.assertIn("if (memoryTrace && performance.now() - lastMemoryLog >= 60000)", self.host)
        self.assertIn("gdiMiB:", self.host)
        self.assertIn("hdPlaneMiB:", self.host)


if __name__ == "__main__":
    unittest.main()
