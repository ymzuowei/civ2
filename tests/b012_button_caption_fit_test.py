"""CIV2-B012 / native UI: bounded Chinese BUTTON text-fit source regression.

Media-free static policy. Owner real-browser visual comparison is required
for palace/council/Save-Load buttons and is not implied by source PASS.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = (ROOT / "src/platform/controls.c").read_text(encoding="utf-8")
TEXT = (ROOT / "src/platform/text.c").read_text(encoding="utf-8")


class CjkButtonCaptionFit(unittest.TestCase):
    def test_only_utf8_non_ascii_builtin_button_captions_are_adjusted(self):
        body = CONTROLS.split("static void button_caption(", 1)[1].split(
            "LRESULT ctl_button_proc(", 1
        )[0]
        self.assertIn("if (plat_text_utf8)", body)
        self.assertIn("if (*p)", body)
        self.assertIn("caption.left += 4;", body)
        self.assertIn("caption.right -= 4;", body)
        self.assertIn("caption.top += 3;", body)
        self.assertIn("caption.bottom -= 3;", body)
        self.assertIn('!strcasecmp(base->lf.lfFaceName, "System")', body)
        self.assertIn("tm.tmHeight + 2 > avail_h || extent.cx + 2 > avail_w", body)
        self.assertIn("smaller.tmHeight + 2 <= avail_h", body)
        self.assertIn("measured.cx + 2 <= avail_w", body)
        self.assertIn("DrawTextA(hdc, text, -1, &caption,", body)
        self.assertIn("if (original)", body)
        self.assertIn("SelectObject(hdc, original);", body)
        self.assertNotIn("focus_rect(", body)

    def test_compact_font_cache_is_bounded_not_per_paint_allocation(self):
        self.assertIn("static HFONT button_compact_fonts[17];", CONTROLS)
        body = CONTROLS.split("static HFONT button_compact_font(", 1)[1].split(
            "static void button_caption(", 1
        )[0]
        self.assertIn("if (px < 6 || px > 16)", body)
        self.assertIn("if (button_compact_fonts[px])", body)
        self.assertIn('strcpy(lf.lfFaceName, "System")', body)
        self.assertIn("CreateFontIndirectA(&lf)", body)
        self.assertIn("lf.lfHeight = -px;", body)

    def test_builtin_button_not_other_window_text_or_global_cjk_glyph(self):
        proc = CONTROLS.split("LRESULT ctl_button_proc(", 1)[1].split(
            "LRESULT ctl_static_proc(", 1
        )[0]
        self.assertIn("case WM_PAINT:", proc)
        self.assertIn("draw_edge(hdc, &r, 0);", proc)
        self.assertIn("button_caption(hdc, w->text, &r);", proc)
        self.assertNotIn("focus_rect(", proc)
        # All other glyph fallback and text metric paths remain independent.
        self.assertIn("int text_width(FontFace *f, const char *s, int n)", TEXT)
        self.assertIn("int WINAPI DrawTextA(", TEXT)
        self.assertIn("stbtt_ScaleForMappingEmToPixels", TEXT)


if __name__ == "__main__":
    unittest.main()
