"""H022 source contracts and premultiplied blend reference math."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def scaled(pixel, opacity, rgb=(255,255,255)):
    return (pixel[0] * opacity // 255,) + tuple(
        c * (opacity * scale // 255) // 255 for c,scale in zip(pixel[1:],rgb))

def composite(pixel, base, opacity, rgb=(255,255,255)):
    a, r, g, b = scaled(pixel, opacity,rgb)
    return tuple(c + d * (255 - a) // 255 for c, d in zip((r,g,b), base))

class FieldTerrainTests(unittest.TestCase):
    def test_only_two_terrains_and_three_existing_field_draws(self):
        src = (ROOT / "src/auto/mapview.cpp").read_text(encoding="utf-8")
        helper = src.split("static void draw_field_overlay(",1)[1].split("/* Part of MapView",1)[0]
        self.assertIn("hd_art && (terrain == TERRAIN_GRASSLAND || terrain == TERRAIN_PLAINS)",helper)
        self.assertLess(helper.index("hd_field_overlay(sprite,opacity,"),helper.index("sprite->draw("))
        self.assertLess(helper.index("sprite->draw("),helper.index("hd_field_overlay(NULL,255,0xffffffu)"))
        self.assertIn("terrain == TERRAIN_GRASSLAND ? 0xd0ffe8u : 0xffe0b8u",helper)
        self.assertEqual(src.count("terrain2,191);"),2)
        self.assertEqual(src.count("terrain2,166);"),1)

    def test_premultiplied_channels_and_scoped_hd_only_path(self):
        src = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        paint = src.split("static void paint_opacity(",1)[1].split("static void paint(",1)[0]
        for marker in ("a = a * opacity / 255","((s >> 16) & 255) * red_scale / 255",
                       "((s >> 8) & 255) * green_scale / 255","(s & 255) * blue_scale / 255",
                       "opacity * ((rgb_scale >> 16) & 255) / 255"):
            self.assertIn(marker,paint)
        self.assertIn("hd_art && s == field_sprite && (field_opacity != 255 || field_rgb_scale != 0xffffffu)",src)
        self.assertIn("sprite_mode == HD_SPRITES_GREY || tint >= 0 ? 0xffffffu : field_rgb_scale",src)
        self.assertIn("bot, tint, 255, 0xffffffu);",src)
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

    def test_field_rgb_distinction_without_alpha_or_texture_replacement(self):
        grass, plains = (208,255,232),(255,224,184)
        pixel, base = (255,150,150,100),(120,140,80)
        for opacity in (166,191):
            g,p = composite(pixel,base,opacity,grass), composite(pixel,base,opacity,plains)
            self.assertGreater(g[1]-g[0],p[1]-p[0])
            for rgb in (grass,plains):
                self.assertEqual(scaled(pixel,opacity,rgb)[0],scaled(pixel,opacity)[0])
                self.assertEqual(composite((0,0,0,0),base,opacity,rgb),base)
                for alpha in (0,1,64,128,255):
                    result = scaled((alpha,alpha,alpha//2,alpha),opacity,rgb)
                    self.assertTrue(all(0 <= c <= result[0] for c in result[1:]))

if __name__ == "__main__":
    unittest.main()
