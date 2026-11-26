"""H022 source contracts and premultiplied blend reference math."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def scaled(pixel, opacity):
    return tuple(channel * opacity // 255 for channel in pixel)

def composite(pixel, base, opacity):
    a, r, g, b = scaled(pixel, opacity)
    return tuple(c + d * (255 - a) // 255 for c, d in zip((r,g,b), base))

class FieldTerrainTests(unittest.TestCase):
    def test_only_two_terrains_and_three_existing_field_draws(self):
        src = (ROOT / "src/auto/mapview.cpp").read_text(encoding="utf-8")
        helper = src.split("static void draw_field_overlay(",1)[1].split("/* Part of MapView",1)[0]
        self.assertIn("hd_art && (terrain == TERRAIN_GRASSLAND || terrain == TERRAIN_PLAINS)",helper)
        self.assertLess(helper.index("hd_field_overlay(sprite,opacity)"),helper.index("sprite->draw("))
        self.assertLess(helper.index("sprite->draw("),helper.index("hd_field_overlay(NULL,255)"))
        self.assertEqual(src.count("terrain2,191);"),2)
        self.assertEqual(src.count("terrain2,166);"),1)

    def test_premultiplied_channels_and_scoped_hd_only_path(self):
        src = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        paint = src.split("static void paint_opacity(",1)[1].split("static void paint(",1)[0]
        for marker in ("a = a * opacity / 255","((s >> 16) & 255) * opacity / 255",
                       "((s >> 8) & 255) * opacity / 255","(s & 255) * opacity / 255"):
            self.assertIn(marker,paint)
        self.assertIn("hd_art && s == field_sprite && field_opacity != 255",src)
        self.assertIn("bot, tint, 255);",src)
        self.assertNotIn("malloc(",paint)

    def test_reference_math_preserves_base_difference(self):
        p = (255,150,110,60)
        a,b = (100,180,70),(180,140,60)
        self.assertEqual(composite(p,a,255),composite(p,b,255))
        for opacity in (166,191):
            self.assertNotEqual(composite(p,a,opacity),composite(p,b,opacity))
            for alpha in (0,1,64,128,255):
                v=scaled((alpha,alpha,alpha//2,0),opacity)
                self.assertTrue(all(0 <= c <= v[0] for c in v[1:]))
        self.assertEqual(composite((0,0,0,0),a,166),a)

if __name__ == "__main__":
    unittest.main()
