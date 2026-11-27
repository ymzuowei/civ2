"""T015 narrow experimental provider source contract; no media or build."""
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class IntroAtlasPolicy(unittest.TestCase):
    def test_opt_in_and_original_fallback(self):
        game = (ROOT / "src/auto/game_setup.cpp").read_text(encoding="utf-8")
        body = game.split("void __cdecl setup_picwnd_load_image", 1)[1].split("void SetupPicWindow::reset_fields", 1)[0]
        for item in ('getenv("CIV2_T015_INTRO_ATLAS")', 'strcmp(intro_atlas,"1") == 0 && hd_art',
                     "image_id >= 1 && image_id <= 13", "hd_intro_picture_size(image_id,width,height)",
                     "dest->set_palette(&palette)", "dest->fill(0)", "hd_intro_picture((void *)dest->bits",
                     "surface.load_gif_resource", "gfx_copy_rect_same_pos"):
            self.assertIn(item, body)
        self.assertLess(body.index("palette.init()"), body.index("hd_intro_picture_size"))
        self.assertLess(body.index("hd_intro_picture((void *)"), body.index("surface.load_gif_resource"))
        load = game.split("void SetupPicWindow::load_dll()",1)[1].split("void SetupPicWindow::free_dll()",1)[0]
        self.assertIn("dll.load(",load)
        self.assertNotIn("INTRO_ATLAS",load)
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        self.assertIn("if (query.get('introAtlas') === '1')", main)
        self.assertIn("env.CIV2_T015_INTRO_ATLAS = '1';", main)

    def test_only_exact_opaque_intro_picture(self):
        hd = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        body = hd.split("static int intro_picture_id",1)[1].split("int hd_picture(void",1)[0]
        for item in ("!hd_on || !hd_art", "image_id < 1 || image_id > 13",
                     '"resource/intro.dll/gifs/%d"', "entries[id - 1].w != (unsigned)w",
                     "entries[id - 1].h != (unsigned)h", "b->bpp != 8", "b->w - w > 3",
                     "!px || !solid", "paint_solid_picture", "commit_rect", "b->hd_own = 1"):
            self.assertIn(item,body)
        self.assertNotIn("plat_res_module",body)
        self.assertNotIn("res_load(",body)
        self.assertLess(body.index("!px || !solid"),body.index("paint_solid_picture"))
        self.assertIn("reported & (1u << image_id)",body)


if __name__ == "__main__":
    unittest.main()
