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
        self.assertLess(region.index("map_grid_sprite"), region.index("hd_map_grid_contrast"))
        self.assertLess(region.index("city_radius_grid_sprite"), region.index("hd_map_grid_contrast"))

    def test_hd_only_revealed_tiles_and_native_coordinates(self):
        region = self.game.split("void MapView::draw_tile(int x,int y,int civ)", 1)[1].split("i32 MapView::tile_in_view", 1)[0]
        self.assertIn("hd_art && (civ < 0 || game.reveal_map != 0 || tile_visible_to(x,y,civ) != 0)", region)
        self.assertIn("(int)tile_width_u,(int)tile_height_u,near_city", region)
        self.assertNotIn("game.game_options |= OPT_MAP_GRID", region)

    def test_contrast_is_only_in_color_plane_and_cities_get_bright_line(self):
        helper = self.plane.split("void hd_map_grid_contrast(", 1)[1].split("void hd_dc_chevron(", 1)[0]
        self.assertIn("if (!hd_art ||", helper)
        self.assertIn("radius_tile ? 0xf2eee4u : 0x0b1815u", helper)
        self.assertIn("seg_dist2(", helper)
        self.assertIn("sync_rect(", helper)
        self.assertIn("commit_rect(", helper)
        self.assertIn("b->hd +", helper)
        self.assertNotRegex(helper, r"\bbmp_row\([^)]*\)\s*=")
        self.assertIn("void hd_map_grid_contrast(", self.header)
        # Both revealed tile types use one thin outline, so bright city
        # radius cannot be thicker than ordinary terrain grid. Only the
        # ordinary dark overlay is slightly deeper; city color/alpha stay.
        self.assertIn("stroke = 0.56, limit = stroke * stroke", helper)
        self.assertNotIn("stroke = radius_tile ?", helper)
        self.assertIn("strength = radius_tile ? 184u : 118u", helper)
        self.assertIn("radius_tile ? 0xf2eee4u : 0x0b1815u", helper)
        self.assertIn("best < .12 ? strength", helper)
        # Radius-only drawing may extend one pixel across a shared edge
        # for anti-alias coverage. Ordinary dark grid still obeys the
        # original tile rectangle; the bitmap is clipped by clip_rect().
        self.assertIn("l = x - (radius_tile ? 1 : 0)", helper)
        self.assertIn("t = y - (radius_tile ? 1 : 0)", helper)
        self.assertIn("r = x + w + (radius_tile ? 1 : 0)", helper)
        self.assertIn("bot = y + h + (radius_tile ? 1 : 0)", helper)

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
