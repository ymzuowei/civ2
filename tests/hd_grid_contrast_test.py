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
        # Owner approved the overall 1440p visual composition but requested
        # softer ordinary visible-grid outlines. Keep the city-radius white
        # treatment, original game sprites and hidden-grid behavior intact.
        self.assertIn("stroke = radius_tile ? 0.84 : 0.66", helper)
        self.assertIn("strength = radius_tile ? 184u : 104u", helper)
        self.assertIn("radius_tile ? 0xf2eee4u : 0x0b1815u", helper)
        self.assertIn("best < .12 ? strength", helper)


if __name__ == "__main__":
    unittest.main()
