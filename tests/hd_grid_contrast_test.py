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

    def test_original_sprites_and_no_early_hd_overlay(self):
        region = self.game.split(
            "void MapView::draw_tile(int x,int y,int civ)", 1
        )[1].split("i32 MapView::tile_in_view", 1)[0]
        self.assertIn("game.game_options & OPT_MAP_GRID", region)
        self.assertIn("map_grid_sprite", region)
        self.assertIn("city_radius_grid_sprite", region)
        self.assertIn("map_distance_diag(x,y", region)
        self.assertLess(region.index("draw_tile_terrain("),
                        region.index("map_grid_sprite"))
        self.assertLess(region.index("draw_tile_terrain("),
                        region.index("city_radius_grid_sprite"))
        # No HD paint during the per-tile terrain pass: its overlap would
        # otherwise change apparent alpha based on traversal order.
        self.assertNotIn("hd_map_grid_contrast(", region)
        self.assertIn("gfx_reset_zoom_scale();", region)
        self.assertNotIn("game.game_options |= OPT_MAP_GRID", region)

    def test_grid_mask_unions_coverage_before_one_final_blend(self):
        code = self.plane
        header = (ROOT / "src/platform/hd_grid_batch.h").read_text(
            encoding="utf-8")
        self.assertIn("hd_grid_batch_begin(", header)
        self.assertIn("hd_grid_batch_end(", header)
        self.assertIn("hd_grid_batch_begin(", code)
        self.assertIn("hd_grid_batch_end(", code)
        self.assertIn("uint16_t *pixels;", code)
        self.assertIn("calloc(pw * ph, sizeof *mask)", code)
        self.assertIn("free(g->pixels)", code)
        self.assertIn("memset(g, 0, sizeof *g)", code)
        self.assertIn("pw > SIZE_MAX / ph", code)
        self.assertIn("pw * ph > SIZE_MAX / sizeof *mask", code)
        # Native terrain/sprites are synced only once, after collecting
        # the shared-edge coverage, then the HD plane is committed once.
        finish = code.split("void hd_grid_batch_end(", 1)[1].split(
            "void hd_map_grid_contrast(", 1)[0]
        self.assertLess(finish.index("sync_rect("),
                        finish.index("for (iy = g->miny"))
        self.assertLess(finish.index("for (iy = g->miny"),
                        finish.index("commit_rect("))
        self.assertIn("sample & 0x100u", finish)
        self.assertIn("0xf6f3ecu : 0x0b1815u", finish)
        self.assertIn("uint16_t sample = g->pixels[", finish)
        self.assertNotIn("hd_grid_batch_end(", self.game.split(
            "void MapView::draw_tile(int x,int y,int civ)", 1
        )[1].split("i32 MapView::tile_in_view", 1)[0])

    def test_grid_raster_collects_max_coverage_not_repeated_color(self):
        helper = self.plane.split("void hd_map_grid_contrast(", 1)[1].split(
            "void hd_dc_chevron(", 1)[0]
        self.assertIn("b != grid_batch.b || !grid_batch.pixels", helper)
        self.assertIn("stroke = 0.56, limit = stroke * stroke", helper)
        self.assertIn("strength = radius_tile ? hd_radius_grid_strength(w) : 40u",
                      helper)
        self.assertIn("seg_dist2(", helper)
        self.assertIn("a | (radius_tile ? 0x100u : 0u)", helper)
        self.assertIn("a > (old_sample & 255u)", helper)
        self.assertIn("radius_tile && !(old_sample & 0x100u)", helper)
        self.assertNotIn("*dst =", helper)
        self.assertNotIn("commit_rect(", helper)
        self.assertNotIn("sync_rect(", helper)
        # White city edges preserve 1 native pixel AA margin; normal
        # dark grid keeps the exact tile rectangle with no spill.
        self.assertIn("l = x - (radius_tile ? 1 : 0)", helper)
        self.assertIn("t = y - (radius_tile ? 1 : 0)", helper)
        self.assertIn("r = x + w + (radius_tile ? 1 : 0)", helper)
        self.assertIn("bot = y + h + (radius_tile ? 1 : 0)", helper)
        self.assertIn("l < grid_batch.l", helper)
        self.assertIn("r > grid_batch.r", helper)
        self.assertNotRegex(helper, r"\bbmp_row\([^)]*\)\s*=")
        self.assertIn("void hd_map_grid_contrast(", self.header)

    def test_city_radius_zoom_alpha_is_bounded_and_monotone(self):
        # This is native map zoom: gfx_zoom_scale(64, zoom) =
        # (zoom + 8) * 64 / 8, independent of Chrome display Fit or DPI.
        helper = self.plane.split(
            "static unsigned hd_radius_grid_strength(", 1
        )[1].split("void hd_map_grid_contrast(", 1)[0]
        self.assertIn("tile_width >= 80", helper)
        self.assertIn("return 164u", helper)
        self.assertIn("tile_width <= 0", helper)
        self.assertIn("return 104u", helper)
        self.assertIn("164u * (unsigned)tile_width / 80u", helper)
        self.assertIn("strength < 104u ? 104u : strength", helper)

        def alpha(tile_width):
            if tile_width >= 80:
                return 164
            if tile_width <= 0:
                return 104
            return max(104, 164 * tile_width // 80)

        values = [(w, alpha(w)) for w in (8, 32, 48, 56, 64, 72, 79, 80, 88)]
        self.assertEqual([a for _, a in values],
                         [104, 104, 104, 114, 131, 147, 161, 164, 164])
        self.assertTrue(all(
            values[i][1] <= values[i + 1][1]
            for i in range(len(values) - 1)
        ))
        self.assertTrue(all(104 <= value <= 164 for _, value in values))
        # Normal large-desktop +2 and zoomed-out 0 are both less bright
        # than the previous 184/147, while retained Sprite remains visible.
        self.assertEqual(alpha((2 + 8) * 64 // 8), 164)
        self.assertEqual(alpha((0 + 8) * 64 // 8), 131)
        self.assertLess(40, alpha((0 + 8) * 64 // 8))


    def test_city_radius_postpass_follows_all_neighbor_terrain_draws(self):
        # A thin pale city boundary used to be partially overpainted by
        # later neighboring terrain or ordinary dark grid. Source-order
        # contracts protect both full redraw and movement/partial redraw.
        shared = self.game.split(
            "static int hd_grid_tile_kind_for_postpass(", 1
        )[1].split("void MapView::draw_tile_radius(", 1)[0]
        self.assertIn("OPT_MAP_GRID", shared)
        self.assertIn("tile_visible_to(tx,ty,civ)", shared)
        self.assertIn("cities[c].owner == civ", shared)
        self.assertIn("map_distance_diag(tx,ty,", shared)
        self.assertIn("map_in_bounds(tx,ty)", shared)
        self.assertIn("return 2;", shared)
        self.assertIn("return 1;", shared)
        self.assertIn("return 0;", shared)
        for name, next_name in (
            ("draw_tile_radius", "draw_all_tiles"),
            ("draw_all_tiles", "blit_tile_radius"),
        ):
            region = self.game.split(
                "void MapView::" + name + "(", 1
            )[1].split("void MapView::" + next_name + "(", 1)[0]
            self.assertIn("hd_grid_batch_begin((void *)this->bits", region)
            self.assertIn("hd_grid_tile_kind_for_postpass(", region)
            self.assertIn("hd_map_grid_contrast((void *)this->bits", region)
            self.assertIn("hd_grid_batch_end((void *)this->bits)", region)
            self.assertIn("tile_to_screen(&sx,&sy", region)
            self.assertIn("apply_zoom();", region)
            self.assertIn("gfx_reset_zoom_scale();", region)
            self.assertLess(region.index("draw_tile(x,"),
                            region.index("hd_grid_batch_begin("))
            self.assertLess(region.index("hd_grid_batch_begin("),
                            region.index("hd_grid_tile_kind_for_postpass("))
            self.assertLess(region.index("hd_grid_tile_kind_for_postpass("),
                            region.index("hd_grid_batch_end("))
            self.assertLess(region.index("hd_grid_batch_end("),
                            region.index("draw_city_names("))
            self.assertIn("kind == 2", region)
            self.assertNotIn("game.game_options |=", region)


if __name__ == "__main__":
    unittest.main()
