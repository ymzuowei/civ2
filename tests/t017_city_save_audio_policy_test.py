"""CIV2-T017: city-name exhaustion / Save+Load Delete / dual WebAudio contracts.

These source tests run in local D:-only CI without copyrighted game media;
native WASM and real browser use require separate Owner acceptance.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CityAndSaveManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = (ROOT / "src/auto/city.cpp").read_text(encoding="utf-8")
        cls.file = (ROOT / "src/platform/filedlg.c").read_text(encoding="utf-8")
        cls.api = (ROOT / "src/web/wasi.js").read_text(encoding="utf-8")
        cls.host = (ROOT / "src/web/host.js").read_text(encoding="utf-8")
        cls.volume = (ROOT / "src/web/audio_volume.js").read_text(encoding="utf-8")
        cls.page = (ROOT / "src/web/main.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "src/web/index.html").read_text(encoding="utf-8")

    def test_all_eight_civilizations_share_noncrashing_city_fallback(self):
        body = self.city[self.city.index("void __cdecl city_assign_default_name(int city)"):
                         self.city.index("/* 0043f7a7 auto */")]
        self.assertIn("civ = cities[city].owner;", body)
        self.assertIn("leaders[civs[civ].tribe].city_name_index >= 120", body)
        self.assertNotIn("leaders[civs[civ].tribe].city_name_index = 0;", body)
        self.assertIn("leaders[civs[civ].tribe].city_name_index < 0 ||", body)
        self.assertIn("leaders[civs[civ].tribe].city_name_index >= 120)", body)
        self.assertLess(body.index("city_name_index < 0 ||"), body.index("city_name_index++;"))
        self.assertIn("return;", body[body.index("city_name_index < 0 ||"):body.index("city_name_index++;")])
        self.assertIn("skip_count = (uint)(unsigned char)", body)
        self.assertNotIn("city_name_index = '\\0';", body)
        self.assertIn("No EXTRA section: generate the next unique slot name.", body)
        self.assertIn('snprintf(cities[city].name, sizeof cities[city].name, "City %03d", city + 1);', body)
        self.assertIn("if (!cities[city].name[0])", body)
        self.assertIn("text_open_section(0,(const char *)&str_extra);", body)
        self.assertNotIn("game.human_players", body)
        self.assertIn("if (0xfe < game.num_cities)", self.city)
        self.assertIn("return 0xffffffff;", self.city)

    def test_delete_only_from_save_load_dialog_selected_list_with_confirmation(self):
        self.assertIn("WINBOOL plat_file_dialog(OPENFILENAMEA *ofn, int save)", self.file)
        self.assertIn("(msg.wParam == VK_DELETE && msg.hwnd == fd.list)", self.file)
        self.assertIn("delete_selected_save();", self.file)
        self.assertIn("LB_GETCURSEL", self.file)
        self.assertIn('!strcasecmp(name + len - 4, ".SAV")', self.file)
        self.assertIn("MessageBoxA(fd.dlg, prompt", self.file)
        self.assertIn("MB_YESNO | MB_ICONWARNING", self.file)
        self.assertIn("if (!safe_save_target(entry->path, host, sizeof host)) break;", self.file)
        self.assertIn('!strcmp(selected, "[..]")', self.file)
        self.assertIn("CIV2_LB_UNSELECTABLE_DATA", self.file)
        self.assertIn("plan_save_tree", self.file)
        self.assertIn("MAX_DELETE_DEPTH 12", self.file)
        self.assertIn("MAX_DELETE_PLAN 4096", self.file)
        self.assertIn("SAVE_FOLDER_MARKER", self.file)
        self.assertIn("rmdir(host)", self.file)
        self.assertIn("remove(host)", self.file)
        self.assertIn("refill();\n    SetFocus(fd.list);", self.file)
        self.assertNotIn("shutil.rmtree", self.file)

    def test_protect_imported_game_media_root_and_external_folders(self):
        for token in ("plat_game_dir", "S_ISLNK", "lstat(", "host[root] != '/'",
                      "S_ISREG(st.st_mode)", "S_ISDIR(st.st_mode)",
                      'strcasecmp(base + 1, "MUSIC")',
                      'strcasecmp(base + 1, "VIDEO")',
                      'strcasecmp(base + 1, "KINGS")',
                      "if (!marked_this && plan->files - plan->marked == saves_before)",
                      "int saves_before = plan->files - plan->marked;",
                      "marked_this = 1;",
                      "if (!plan_save_tree(&plan, target, 0))"):
            self.assertIn(token, self.file)
        self.assertIn("path_unlink_file(dirfd, path, len)", self.api)
        self.assertIn("fs.changed(p, true);", self.api)
        self.assertIn("path_remove_directory(dirfd, path, len)", self.api)
        self.assertIn("if (fs.list(p).length)", self.api)

    def test_legacy_pre_marker_save_folders_are_delete_eligible_only_with_savs(self):
        # T011 folders predated the T017 marker; reject unsafe unmarked
        # empty/mixed/game-resource trees, accept save-only legacy trees.
        self.assertIn("int saves_before = plan->files - plan->marked;", self.file)
        self.assertIn("if (!marked_this && plan->files - plan->marked == saves_before)",
                      self.file)
        self.assertIn("else if (is_save_file(f.cFileName))", self.file)
        self.assertIn("Non-save content: never destroy native game assets.", self.file)
        self.assertIn('!strcmp(selected, "[..]")', self.file)
        self.assertIn("CIV2_LB_UNSELECTABLE_DATA", self.file)
        self.assertIn("MB_YESNO | MB_ICONWARNING", self.file)

    def test_dual_audio_and_compact_ui_do_not_intercept_game_keys(self):
        self.assertIn("src.connect(audioDestination('music'));", self.host)
        self.assertIn("src.connect(audioDestination('effects'));", self.host)
        self.assertIn("masterGain = audio.createGain();", self.host)
        self.assertIn("musicGain = audio.createGain();", self.host)
        self.assertIn("effectsGain = audio.createGain();", self.host)
        self.assertIn("masterGain.connect(audio.destination);", self.host)
        self.assertIn("setMusicLevel(next)", self.volume)
        self.assertIn("setEffectsLevel(next)", self.volume)
        self.assertIn("openciv2.browser-audio.v1", self.volume)
        self.assertIn("browserAudio.setMusicLevel(", self.page)
        self.assertIn("browserAudio.setEffectsLevel(", self.page)
        self.assertIn("const mixerCompatible = typeof browserAudio.setMusicLevel === 'function'", self.page)
        self.assertIn("musicSlider.disabled = true;", self.page)
        self.assertIn("effectsSlider.disabled = true;", self.page)
        self.assertIn("audioPanel.hidden = !shown;", self.page)
        self.assertIn("controls.addEventListener('keydown', (e) => e.stopPropagation());", self.page)
        for ident in ('id="audio-music"', 'id="audio-effects"',
                      'id="audio-mixer-toggle"', 'id="audio-mixer-panel"'):
            self.assertIn(ident, self.html)
        self.assertNotIn("new AudioContext", self.volume)


if __name__ == "__main__":
    unittest.main()
