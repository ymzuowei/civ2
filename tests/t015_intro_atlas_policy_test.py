"""T015 narrow experimental alpha provider contract; no media or build."""
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class IntroAtlasPolicy(unittest.TestCase):
    def test_opt_in_and_original_fallback(self):
        game = (ROOT / "src/auto/game_setup.cpp").read_text(encoding="utf-8")
        body = game.split("void __cdecl setup_picwnd_load_image", 1)[1].split("void SetupPicWindow::reset_fields", 1)[0]
        for item in ('getenv("CIV2_T015_INTRO_ATLAS")', 'strcmp(intro_atlas,"1") == 0',
                     "hd_intro_picture_size(image_id,width,height)", "surface.alloc_dib8(&rect)",
                     "surface.set_palette(&palette)", "surface.fill(0)", "hd_intro_picture((void *)surface.bits",
                     "hd_intro_surface_failed(image_id)", "surface.load_gif_resource", "gfx_copy_rect_same_pos"):
            self.assertIn(item, body)
        self.assertLess(body.index("palette.init()"), body.index("hd_intro_picture_size"))
        self.assertLess(body.index("hd_intro_picture((void *)"), body.index("surface.load_gif_resource"))
        self.assertEqual(body.count("gfx_copy_rect_same_pos"),1)
        load = game.split("void SetupPicWindow::load_dll()",1)[1].split("void SetupPicWindow::free_dll()",1)[0]
        self.assertIn("dll.load(",load)
        self.assertNotIn("INTRO_ATLAS",load)
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        self.assertIn("if (query.get('introAtlas') === '1')", main)
        self.assertIn("env.CIV2_T015_INTRO_ATLAS = '1';", main)

    def test_exact_alpha_plane_and_bounded_fallback(self):
        hd = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        body = hd.split("enum IntroResult",1)[1].split("int hd_picture(void",1)[0]
        for item in ("!hd_on || !hd_art", "image_id < 1 || image_id > 13",
                     '"resource/intro.dll/gifs/%d"', "entries[id - 1].w != (unsigned)w",
                     "entries[id - 1].h != (unsigned)h", "b->bpp != 8", "b->w - w > 3",
                     "if (!px)", "paint_solid_picture", "b->hd_alpha = !solid",
                     "commit_rect", "b->hd_own = 1", "INTRO_KEY_MISSING", "INTRO_SIZE_MISMATCH",
                     "INTRO_SURFACE", "INTRO_PLANE", "INTRO_DECODE", "INTRO_HD_OFF",
                     "reported[result] & (1u << slot)", "CIV2_T015_INTRO_ATLAS_FALLBACK"):
            self.assertIn(item,body)
        self.assertNotIn("plat_res_module",body)
        self.assertNotIn("res_load(",body)
        self.assertNotIn("!px || !solid",body)
        self.assertLess(body.index("if (!px)"),body.index("paint_solid_picture"))
        self.assertLess(body.index("b->hd_alpha = !solid"),body.index("intro_report(image_id, INTRO_DIRECT)"))
        self.assertIn("if (src->hd_alpha && src != dst)",hd)

    def test_palette_rng_call_only_on_success(self):
        game = (ROOT / "src/auto/game_setup.cpp").read_text(encoding="utf-8")
        body = game.split("void __cdecl setup_picwnd_load_image",1)[1].split("void SetupPicWindow::reset_fields",1)[0]
        self.assertEqual(body.count("palette.new_version();"),1)
        success, fallback = body.split("  if (direct) {",1)[1].split("  } else {",1)
        self.assertIn("palette.new_version();",success)
        self.assertNotIn("palette.new_version();",fallback)
        self.assertIn("surface.load_gif_resource",fallback)
        gfx = (ROOT / "src/auto/graphics_surface.cpp").read_text(encoding="utf-8")
        self.assertIn('crt_rand_at("palette_new_version")',gfx)
        self.assertIn("commit_range(first,count);",gfx)


if __name__ == "__main__":
    unittest.main()
