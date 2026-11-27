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
        self.assertIn("bool farmland",helper)
        self.assertIn("? (farmland ? 0xf0ffc0u : 0xd0ffe8u) : 0xffe0b8u",helper)
        self.assertIn("hd_field_overlay(sprite,opacity,rgb)",helper)
        self.assertEqual(src.count("terrain2,191,true);"),2)
        self.assertEqual(src.count("terrain2,166,false);"),1)
        self.assertIn("farmland_sprite,(RECT *)farmland_rect,surface,screen_x,screen_y,terrain2,191,true);",src)
        self.assertIn("farmland_sprite,(RECT *)farm_rect,surface,screen_x,screen_y,terrain2,191,true);",src)
        self.assertIn("land_improvement_sprites[0],(RECT *)irrig_rect,surface,screen_x,screen_y,terrain2,166,false);",src)

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
        grass_irrig, grass_farm, plains = (208,255,232),(240,255,192),(255,224,184)
        pixel, base = (255,150,150,100),(120,140,80)
        for opacity,grass in ((166,grass_irrig),(191,grass_farm)):
            g,p = composite(pixel,base,opacity,grass), composite(pixel,base,opacity,plains)
            self.assertGreater(g[1]-g[0],p[1]-p[0])
            for rgb in (grass,plains):
                self.assertEqual(scaled(pixel,opacity,rgb)[0],scaled(pixel,opacity)[0])
                self.assertEqual(composite((0,0,0,0),base,opacity,rgb),base)
                for alpha in (0,1,64,128,255):
                    result = scaled((alpha,alpha,alpha//2,alpha),opacity,rgb)
                    self.assertTrue(all(0 <= c <= result[0] for c in result[1:]))

    def test_grassland_farmland_warms_without_replacing_green_identity(self):
        irrig, farm, plains = (208,255,232),(240,255,192),(255,224,184)
        pixel, base = (255,150,150,100),(120,140,80)
        # Isolate the color change at identical opacity and source pixels.
        old, new = composite(pixel,base,191,irrig), composite(pixel,base,191,farm)
        self.assertGreater(new[0],old[0])
        self.assertEqual(new[1],old[1])
        self.assertLess(new[2],old[2])
        self.assertGreater(new[1]-new[0],composite(pixel,base,191,plains)[1]-composite(pixel,base,191,plains)[0])
        self.assertEqual(scaled(pixel,191,farm)[0],scaled(pixel,191,irrig)[0])

if __name__ == "__main__":
    unittest.main()
