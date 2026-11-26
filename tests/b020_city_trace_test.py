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

    def test_all_delete_paths_and_selected_tile_trace(self):
        city = (ROOT / "src/auto/city.cpp").read_text(encoding="utf-8")
        body = city.split("void __cdecl city_delete(", 1)[1].split("/* 00441a79 auto */", 1)[0]
        self.assertLess(body.index("tile_set_improvements(x2,y2,2,0,1)"),
                        body.index("CIV2_CITY_TRACE delete city-present="))
        self.assertIn("city_at(x2,y2) >= 0", body)
        self.assertIn("fflush(stderr)", body)
        status = (ROOT / "src/auto/game_status.cpp").read_text(encoding="utf-8")
        info = status.split("static void status_draw_tile_info(", 1)[1].split("static void status_draw_active_unit", 1)[0]
        self.assertLess(info.index("terrain = *tile_ptr"), info.index("CIV2_CITY_TRACE selected"))
        self.assertIn('moving_units_mode == 0 && city_trace && strcmp(city_trace,"1") == 0', info)
        self.assertIn("tile_improvements(x2,y2)", info)
        self.assertIn("actual & 0x42U", info)
        self.assertIn("(unsigned int)terrain & 0x42U", info)
        self.assertIn("last_known != (int)terrain", info)
        self.assertIn("fflush(stderr)", info)
        self.assertNotIn("tile_set_improvements", info)

    def test_detail_trace_correlates_deletion_and_special_transitions(self):
        city = (ROOT / "src/auto/city.cpp").read_text(encoding="utf-8")
        body = city.split("void __cdecl city_delete(", 1)[1].split("/* 00441a79 auto */", 1)[0]
        self.assertLess(body.index("CIV2_CITY_TRACE delete-before"), body.index("cities[city].id = 0"))
        self.assertLess(body.index("tile_set_improvements(x2,y2,2,0,1)"), body.index("CIV2_CITY_TRACE delete-after"))
        self.assertIn('getenv("CIV2_CITY_TRACE_DETAIL")', body)
        setter = (ROOT / "src/auto/map.cpp").read_text(encoding="utf-8").split("void __cdecl tile_set_improvements(", 1)[1].split("/* 005b9646 auto */", 1)[0]
        self.assertIn("((tile->improvements ^ (byte)old_value) & 0x40) != 0", setter)
        self.assertIn("CIV2_CITY_TRACE special-change tile=", setter)
        worker = (ROOT / "src/auto/unit.cpp").read_text(encoding="utf-8").split("static void unit_terrain_work_finish(", 1)[1].split("/* 004c42a0 auto */", 1)[0]
        self.assertIn("CIV2_CITY_TRACE worker-special tile=", worker)
        self.assertIn("work_before != after", worker)
        self.assertIn("game.human_players", worker)
        main = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        self.assertIn("query.get('cityTrace') === '1' && query.get('cityTraceDetail') === '1'", main)
        self.assertIn("env.CIV2_CITY_TRACE_DETAIL = '1';", main)

if __name__ == "__main__":
    unittest.main()
