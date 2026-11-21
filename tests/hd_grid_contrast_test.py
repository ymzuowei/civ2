"""CIV2-T006: existing HD grid/radius visibility and browser choice policy.

Public source only; no owned Civ II media, large asset ZIP or WASM download.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HdGridContrastContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = (ROOT / "src/auto/mapview.cpp").read_text(encoding="utf-8")
        cls.plane = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")
        cls.header = (ROOT / "src/platform/hd.h").read_text(encoding="utf-8")

    def test_preserves_original_game_grid_toggle_and_near_city(self):
        region = self.game.split("void MapView::draw_tile(int x,int y,int civ)", 1)[1].split("i32 MapView::tile_in_view", 1)[0]
        self.assertIn("game.game_options & OPT_MAP_GRID", region)
        self.assertIn("map_grid_sprite", region)
        self.assertIn("city_radius_grid_sprite", region)
        self.assertIn("map_distance_diag(x,y", region)
        self.assertLess(region.index("draw_tile_terrain("), region.index("map_grid_sprite"))
        self.assertLess(region.index("draw_tile_terrain("), region.index("city_radius_grid_sprite"))
        self.assertNotIn("hd_map_grid_contrast(", region)

    def test_hd_only_revealed_tiles_and_native_coordinates(self):
        region = self.game.split("void MapView::draw_tile(int x,int y,int civ)", 1)[1].split("i32 MapView::tile_in_view", 1)[0]
        # Ordinary map-grid Sprite alone is the intended final output.
        # There must be no extra HD dark overlay or premature pale blend.
        self.assertNotIn("hd_map_grid_contrast(", region)
        self.assertIn("map_grid_sprite", region)
        self.assertIn("city_radius_grid_sprite", region)
        self.assertIn("gfx_reset_zoom_scale();", region)
        self.assertNotIn("game.game_options |= OPT_MAP_GRID", region)

    def test_contrast_is_only_in_color_plane_and_cities_get_bright_line(self):
        helper = self.plane.split("void hd_map_grid_contrast(", 1)[1].split("void hd_dc_chevron(", 1)[0]
        self.assertIn("if (!radius_tile || !hd_art ||", helper)
        self.assertIn("unsigned color = 0xf2eee4u", helper)
        self.assertNotIn("0x0b1815u", helper)
        self.assertIn("strength = hd_radius_grid_strength(w)", helper)
        self.assertIn("seg_dist2(", helper)
        self.assertIn("sync_rect(", helper)
        self.assertIn("commit_rect(", helper)
        self.assertIn("b->hd +", helper)
        self.assertNotRegex(helper, r"\bbmp_row\([^)]*\)\s*=")
        self.assertIn("void hd_map_grid_contrast(", self.header)
        self.assertIn("stroke = 0.56, limit = stroke * stroke", helper)
        self.assertIn("best < .12 ? strength", helper)
        # Only pale city radius extends 1px for seamless AA clipping.
        self.assertIn("l = x - 1", helper)
        self.assertIn("t = y - 1", helper)
        self.assertIn("r = x + w + 1", helper)
        self.assertIn("bot = y + h + 1", helper)

    def test_city_radius_zoom_alpha_is_bounded_and_monotone(self):
        # This is native map zoom: gfx_zoom_scale(64, zoom) =
        # (zoom + 8) * 64 / 8, independent of Chrome display Fit or DPI.
        helper = self.plane.split(
            "static unsigned hd_radius_grid_strength(", 1
        )[1].split("void hd_map_grid_contrast(", 1)[0]
        self.assertIn("tile_width >= 80", helper)
        self.assertIn("return 184u", helper)
        self.assertIn("tile_width <= 0", helper)
        self.assertIn("return 120u", helper)
        self.assertIn("184u * (unsigned)tile_width / 80u", helper)
        self.assertIn("strength < 120u ? 120u : strength", helper)

        def alpha(tile_width):
            if tile_width >= 80:
                return 184
            if tile_width <= 0:
                return 120
            return max(120, 184 * tile_width // 80)

        values = [(w, alpha(w)) for w in (8, 32, 48, 56, 64, 72, 79, 80, 88)]
        self.assertEqual([a for _, a in values],
                         [120, 120, 120, 128, 147, 165, 181, 184, 184])
        self.assertTrue(all(
            values[i][1] <= values[i + 1][1]
            for i in range(len(values) - 1)
        ))
        self.assertTrue(all(120 <= value <= 184 for _, value in values))
        # Normal large-desktop zoom +2: tile 80 => original 184 intensity.
        self.assertEqual(alpha((2 + 8) * 64 // 8), 184)
        # Each smaller native zoom step diminishes only the HD accent.
        self.assertEqual(alpha((0 + 8) * 64 // 8), 147)


    def test_city_radius_postpass_follows_all_neighbor_terrain_draws(self):
        # A thin pale city boundary used to be partially overpainted by
        # later neighboring terrain or ordinary dark grid. Source-order
        # contracts protect both full redraw and movement/partial redraw.
        shared = self.game.split(
            "static bool hd_radius_tile_for_postpass(", 1
        )[1].split("void MapView::draw_tile_radius(", 1)[0]
        self.assertIn("OPT_MAP_GRID", shared)
        self.assertIn("tile_visible_to(tx,ty,civ)", shared)
        self.assertIn("cities[c].owner == civ", shared)
        self.assertIn("map_distance_diag(tx,ty,", shared)
        self.assertIn("map_in_bounds(tx,ty)", shared)
        self.assertIn("return true;", shared)
        for name, next_name in (
            ("draw_tile_radius", "draw_all_tiles"),
            ("draw_all_tiles", "blit_tile_radius"),
        ):
            region = self.game.split(
                "void MapView::" + name + "(", 1
            )[1].split("void MapView::" + next_name + "(", 1)[0]
            self.assertIn("hd_radius_tile_for_postpass(", region)
            self.assertIn("hd_map_grid_contrast((void *)this->bits", region)
            self.assertIn("tile_to_screen(&sx,&sy", region)
            self.assertIn("apply_zoom();", region)
            self.assertIn("gfx_reset_zoom_scale();", region)
            self.assertLess(region.index("draw_tile(x,"),
                            region.index("hd_radius_tile_for_postpass("))
            self.assertLess(region.index("hd_radius_tile_for_postpass("),
                            region.index("draw_city_names("))
            self.assertNotIn("game.game_options |=", region)


if __name__ == "__main__":
    unittest.main()
