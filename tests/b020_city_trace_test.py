"""Media-free source contracts for B020 diagnostic-only candidate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CityTraceTests(unittest.TestCase):
    def test_trace_follows_deletion_and_redraw(self):
        combat = (ROOT / "src/auto/unit_combat.cpp").read_text(encoding="utf-8")
        branch = combat.split("cities[city].size--;", 1)[1].split("city2 = civ_check_destroyed", 1)[0]
        markers = ("city_delete(city,0)", "tile_update_known(x,y,view_civ2)",
                   "map_redraw_neighbors_all_views(x,y)", 'getenv("CIV2_CITY_TRACE")',
                   'strcmp(city_trace,"1") == 0', "CIV2_CITY_TRACE combat-delete")
        offsets = [branch.index(m) for m in markers]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("city_at(x,y) >= 0", branch)
        self.assertIn("tile_city_owner(x,y) >= 0", branch)
        self.assertIn("impr & 0x42U", branch)
        self.assertNotIn("map_redraw_all_views", branch)

    def test_improvement_mask_distinguishes_fortress_and_airbase(self):
        city = (ROOT / "src/auto/city.cpp").read_text(encoding="utf-8")
        body = city.split("void __cdecl city_delete(", 1)[1].split("/* 00441a79 auto */", 1)[0]
        self.assertIn("tile_set_improvements(x2,y2,2,0,1)", body)
        view = (ROOT / "src/auto/mapview.cpp").read_text(encoding="utf-8")
        self.assertIn("improvements2 & 0x42) == 0x40", view)
        self.assertIn("improvements2 & 0x42) == 0x42", view)
        for before, after in [(0x02, 0), (0x42, 0x40), (0x12, 0)]:
            self.assertEqual((before & ~0x02) & 0x42, after)

    def test_explicit_browser_opt_in_and_stderr_route(self):
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        self.assertIn("if (query.get('cityTrace') === '1')\n        env.CIV2_CITY_TRACE = '1';", main)
        wasi = (ROOT / "src/web/wasi.js").read_text(encoding="utf-8")
        self.assertIn("fd === 2 ? console.warn : console.log", wasi)

if __name__ == "__main__":
    unittest.main()
