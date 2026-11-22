"""CIV2-T011: source-level guards for faithful Save subfolder/autosave scope.

The real WASM/native browser dialogs still require compiled owner acceptance;
these checks prevent accidental separate-folder autosaves or root collisions.
"""
from pathlib import Path
import hashlib
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SaveFolderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dialog = (ROOT / "src/platform/filedlg.c").read_text(encoding="utf-8")
        cls.game = (ROOT / "src/auto/game.cpp").read_text(encoding="utf-8")
        cls.save = (ROOT / "src/auto/game_save.cpp").read_text(encoding="utf-8")
        cls.paths = (ROOT / "src/platform/files.c").read_text(encoding="utf-8")
        cls.web = (ROOT / "src/web/saves.js").read_text(encoding="utf-8")

    def test_folder_is_a_native_save_dialog_action(self):
        for token in ("ID_NEW_FOLDER", "folder_mode(", "create_folder(",
                      "plat_mkdir(path)", "folder_name_ok(",
                      "extras_text(\"file.new_folder\")",
                      "extras_text(\"file.folder_invalid\")"):
            self.assertIn(token, self.dialog)
        self.assertIn("if (save)", self.dialog)
        self.assertIn("if (fd.creating_folder)", self.dialog)
        self.assertIn("EnableWindow(fd.list, !creating)", self.dialog)
        self.assertIn("EnableWindow(fd.sort, !creating)", self.dialog)
        self.assertIn("name[0] == '.'", self.dialog)
        self.assertIn("name[0] == ' '", self.dialog)
        self.assertIn("return mkdir(host, 0777);", self.paths)

    def test_save_dialog_redraws_folder_path_and_has_room_for_chinese_label(self):
        dialog = self.dialog
        refill = dialog[dialog.index("static void refill(void)"):
                        dialog.index("static void enter_dir(")]
        self.assertIn("set_text(fd.dirlabel, label);", refill)
        self.assertNotIn("SetWindowTextA(fd.dirlabel, label);", refill)
        self.assertIn("folder_mode(0);\n    enter_dir(name);", dialog)
        self.assertIn("int w = save ? 480 : 440, h = 396", dialog)
        self.assertIn("w - 30, 18, ID_DIR", dialog)
        self.assertIn("w - 30, 220, ID_LIST", dialog)
        self.assertIn("120, 322, 140, 28, ID_NEW_FOLDER", dialog)
        self.assertIn("save ? 275 : 240", dialog)
        self.assertIn("save ? 375 : 335", dialog)

    def test_native_dialog_static_caption_clears_old_glyphs_on_repaint(self):
        # Runtime screenshots showed a newly correct folder path overprinted
        # on the old Z:\\civ2 caption. The dialog's set_text invalidated the
        # control, but TRANSPARENT DrawTextA retained previous painted pixels.
        # Restrict the opaque cleanup to the file dialog: other STATIC text
        # may be intentionally drawn on top of the game's artwork.
        controls = (ROOT / "src/platform/controls.c").read_text(encoding="utf-8")
        static = controls[controls.index("LRESULT ctl_static_proc("):]
        button = controls[controls.index("LRESULT ctl_button_proc("):
                          controls.index("LRESULT ctl_static_proc(")]
        self.assertIn("strcmp(w->parent->cls->name, \"Civ2FileDialog\") == 0", static)
        self.assertIn("FillRect(hdc, &r, GetSysColorBrush(COLOR_3DFACE));", static)
        self.assertLess(static.index("FillRect(hdc, &r, GetSysColorBrush(COLOR_3DFACE));"),
                        static.index("DrawTextA(hdc, w->text"))
        self.assertIn("SetBkMode(hdc, TRANSPARENT);", static)
        self.assertIn("FillRect(hdc, &r, GetSysColorBrush(COLOR_3DFACE));", button)
        self.assertIn("set_text(fd.dirlabel, label);", self.dialog)
        self.assertIn('set_name_label(extras_text(', self.dialog)
        self.assertIn('set_text(fd.folderbutton, extras_text(', self.dialog)
        self.assertIn('extras_text(creating ? "file.create_folder" : "file.new_folder")', self.dialog)
        self.assertIn("InvalidateRect(h, NULL, TRUE);", self.dialog)
        self.assertIn("UpdateWindow(h);", self.dialog)
        self.assertIn("static void set_name_label(const char *text)", self.dialog)
        self.assertIn("RECT strip = {NAME_CAPTION_X, 260, NAME_EDIT_X - 2, 290};", self.dialog)
        self.assertIn("FillRect(dc, &strip, GetSysColorBrush(COLOR_3DFACE));", self.dialog)
        self.assertIn("ReleaseDC(fd.dlg, dc);", self.dialog)
        self.assertIn("set_text(fd.namelabel, text);", self.dialog)
        self.assertIn("#define NAME_CAPTION_WIDTH 155", self.dialog)
        self.assertIn("#define NAME_EDIT_X 175", self.dialog)
        self.assertIn("NAME_CAPTION_X, 264, NAME_CAPTION_WIDTH, 20", self.dialog)
        self.assertIn("NAME_EDIT_X, 260, w - NAME_EDIT_X - 20, 24", self.dialog)
        self.assertIn("DT_SINGLELINE | DT_LEFT | DT_VCENTER | DT_NOPREFIX", static)
        self.assertIn("DrawTextA(hdc, w->text, -1, &r, DT_WORDBREAK);", static)
        self.assertLess(self.dialog.index("FillRect(dc, &strip"),
                        self.dialog.index("set_text(fd.namelabel, text)"))

    def test_name_label_has_distinct_modes_without_old_chinese_suffix(self):
        # Actual screenshots: leaving folder-create mode once displayed
        # "文件名名称：" from old "文件夹名称：" pixels. The textbox must
        # have a dedicated opaque erase strip and each mode its own key.
        source = self.dialog
        mode = source[source.index("static void folder_mode(int creating)"):
                      source.index("static void create_folder(void)")]
        self.assertIn('creating ? "file.folder_name" : "file.name"', mode)
        self.assertIn("set_name_label(extras_text(", mode)
        self.assertIn("set_text(fd.folderbutton, extras_text(", mode)
        self.assertIn("EnableWindow(fd.savebutton, !creating);", mode)
        self.assertIn("if (fd.creating_folder)\n                folder_mode(0);", source)
        self.assertIn("folder_mode(0);\n    enter_dir(name);", source)
        translations = (ROOT / "data/native/lang/zh-Hans.txt").read_text(encoding="utf-8")
        self.assertIn("@@openciv2.file.name\n文件名：", translations)
        self.assertIn("@@openciv2.file.folder_name\n文件夹名称：", translations)

    def test_save_leader_prefix_preserves_complete_utf8_characters(self):
        source = self.save
        helper = source[source.index("size_t game_save_leader_prefix_bytes("):
                        source.index("/* 0047758c auto */")]
        self.assertIn('#include "../include/utf8.h"', source)
        self.assertIn("for (i = 0; i < 2 && at < n; i++)", helper)
        self.assertIn("u8_len_at(name, n, at)", helper)
        self.assertIn("if (plat_text_utf8)", helper)
        self.assertIn("u8_decode(name + at, n - at, &decoded_size) == U8_BAD", helper)
        self.assertIn("at += size;", helper)
        self.assertIn("return (size_t)at;", helper)
        self.assertIn("file_name_buf[1 + game_save_leader_prefix_bytes(file_name_buf + 1)] = 0;", source)
        self.assertNotIn("file_name_buf[3] = 0;", source)
        # Two characters in UTF-8 can be six bytes or more. The extension,
        # era suffix and original autosave naming do not change.
        self.assertEqual(len("中国".encode("utf-8")), 6)
        self.assertIn("crt_strcat(file_name_buf + 1,((i8 *)&save_name_ext_dot_str));", source)
        self.assertIn("game_save_autosave_follow(file_name_buf + 1);", source)

    def test_successful_save_and_load_choose_autosave_folder(self):
        self.assertIn("result = save_write_game((file_name_buf + 1),is_scenario);", self.save)
        self.assertIn("game_save_autosave_follow(file_name_buf + 1);", self.save)
        self.assertIn("game_save_autosave_follow(file_path);", self.save)
        self.assertIn("if (load_error == 0)", self.save)
        self.assertIn("if (result == 0)", self.save)
        self.assertIn("if (!selected_autosave_folder[0])", self.save)
        self.assertIn("return __chdir(selected_autosave_folder) == 0 ? 1 : -1;", self.save)
        self.assertIn("game_save_autosave_reset();", self.game)

    def test_original_rotation_kept_with_scoped_working_dir(self):
        start = self.game.index("void __cdecl game_autosave(int civ)")
        stop = self.game.index("/* 00489be2 auto */", start)
        code = self.game[start:stop]
        self.assertIn("game_save_autosave_enter(previous_dir", code)
        self.assertIn("game_save_autosave_leave(previous_dir)", code)
        self.assertIn("crt_remove(backup_path)", code)
        self.assertIn("crt_rename(textbuf.buf,backup_path)", code)
        self.assertIn("save_write_game((const char *)&textbuf.buf,0)", code)
        self.assertNotIn("20261121", code)  # no hardcoded dates/auto-created campaigns

    def test_t014_autosave_preserves_two_whole_utf8_leader_chars(self):
        # Manual Save As was already corrected. Autosave still cut at byte 2,
        # which splits the first CJK character. Both entry points must use
        # the identical helper for the current SAV and its rotated backup.
        header = (ROOT / "src/include/auto_common.h").read_text(encoding="utf-8")
        self.assertIn("size_t game_save_leader_prefix_bytes(const char *name);", header)
        self.assertIn("size_t game_save_leader_prefix_bytes(const char *name)", self.save)
        self.assertIn("file_name_buf[1 + game_save_leader_prefix_bytes(file_name_buf + 1)] = 0;", self.save)
        start = self.game.index("void __cdecl game_autosave(int civ)")
        stop = self.game.index("/* 00489be2 auto */", start)
        auto = self.game[start:stop]
        self.assertIn("textbuf.buf[game_save_leader_prefix_bytes(textbuf.buf)] = 0;", auto)
        self.assertNotIn("textbuf.buf[2] = 0;", auto)
        self.assertLess(auto.index("game_save_leader_prefix_bytes(textbuf.buf)"),
                        auto.index("crt_strcpy(backup_path,textbuf.buf);"))
        self.assertLess(auto.index("crt_strcpy(backup_path,textbuf.buf);"),
                        auto.index("save_write_game((const char *)&textbuf.buf,0);"))
        self.assertIn("if (plat_text_utf8)", self.save)
        self.assertIn("u8_decode(name + at, n - at, &decoded_size) == U8_BAD", self.save)
        # Non-UTF-8 mode still counts two bytes; UTF-8 mode counts whole
        # characters. Old SAVs are untouched; only new names are affected.
        self.assertIn("for (i = 0; i < 2 && at < n; i++)", self.save)
        self.assertNotIn("crt_remove(selected_autosave_folder)", self.save)

    def test_t014_f03_f04_switch_route_only_after_successful_manual_save(self):
        manual = self.save[self.save.index("void __cdecl game_save_dialog("):
                           self.save.index("/* 00477d8c auto */")]
        self.assertIn("if (result != 0) {", manual)
        self.assertIn("result = save_write_game((file_name_buf + 1),is_scenario);", manual)
        self.assertIn("if (result == 0) {\n          if (is_scenario == 0) {", manual)
        self.assertIn("game_save_autosave_follow(file_name_buf + 1);", manual)
        self.assertLess(manual.index("save_write_game((file_name_buf + 1),is_scenario)"),
                        manual.index("game_save_autosave_follow(file_name_buf + 1)"))
        self.assertIn("if (result == 0) {", manual)
        self.assertIn("else {\n          text_set_string_arg_b(", manual)
        self.assertIn("if (fd.creating_folder)\n                folder_mode(0);", self.dialog)
        self.assertIn("else\n                fd.done = 1;", self.dialog)
        self.assertIn("if (!folder_name_ok(name)", self.dialog)
        # Browsing FileFolder is not allowed to redirect autosaves.
        helper = self.save[self.save.index("static void game_save_autosave_follow("):
                           self.save.index("int game_save_autosave_enter(")]
        self.assertNotIn("FileFolder", helper)
        self.assertNotIn("setting_get(", helper)

    def test_t014_f05_load_success_restores_route_after_refresh(self):
        load = self.save[self.save.index("int __cdecl game_load_dialog("):]
        self.assertIn("load_error = save_read_game(file_path);", load)
        self.assertIn("if (load_error == 0) {\n      if (is_scenario == 0)\n        game_save_autosave_follow(file_path);", load)
        self.assertLess(load.index("save_read_game(file_path)"),
                        load.index("game_save_autosave_follow(file_path)"))
        self.assertIn("selected_autosave_folder", self.save)
        self.assertIn("return __chdir(selected_autosave_folder) == 0 ? 1 : -1;", self.save)
        self.assertIn("return; /* Missing folder: do not overwrite a root autosave instead. */", self.game)

    def test_t014_f06_new_game_clears_previous_autosave_route(self):
        fn = self.game[self.game.index("void __cdecl game_init_new(void)"):]
        self.assertIn("game_save_autosave_reset();", fn)
        self.assertIn("selected_autosave_folder[0] = 0;", self.save)
        self.assertIn("if (!selected_autosave_folder[0])", self.save)
        self.assertIn("return 0; /* No manual save yet: preserve classic root autosaves. */", self.save)
        self.assertNotIn("game_save_autosave_follow(", fn[:1700])

    def test_t014_f08_autosave_rotation_stays_in_selected_dir(self):
        start = self.game.index("void __cdecl game_autosave(int civ)")
        stop = self.game.index("/* 00489be2 auto */", start)
        code = self.game[start:stop]
        self.assertLess(code.index("game_save_autosave_enter(previous_dir"),
                        code.index("crt_remove(backup_path)"))
        self.assertLess(code.index("if (routed < 0)"),
                        code.index("crt_remove(backup_path)"))
        self.assertIn("if ((game.turn & 4U) == 0)", code)
        self.assertLess(code.index("crt_remove(backup_path)"),
                        code.index("crt_rename(textbuf.buf,backup_path)"))
        self.assertLess(code.index("crt_rename(textbuf.buf,backup_path)"),
                        code.index("save_write_game((const char *)&textbuf.buf,0);"))
        self.assertLess(code.index("save_write_game((const char *)&textbuf.buf,0);"),
                        code.index("game_save_autosave_leave(previous_dir)"))
        self.assertIn("if (routed > 0)", code)
        self.assertIn("return __chdir(selected_autosave_folder) == 0 ? 1 : -1;", self.save)
        self.assertNotIn("FileFolder", code)
        self.assertNotIn("mkdir(", code)

    def test_zip_import_keeps_only_self_exported_safe_relative_paths(self):
        for token in ("SAVE_MANIFEST", "safeSavePath(", "preservedPaths?.has(safe)",
                      "exportSaves(", "new TextEncoder()", "importPath(safe, existing)",
                      "known.get(safe.toLowerCase())",
                      "knownDirs.get(dir.toLowerCase())",
                      "preserveCase(safe)", "safe.includes('/')"):
            self.assertIn(token, self.web)

    def test_t013_import_batch_canonicalizes_case_without_touching_old_saves(self):
        # The native virtual file system is case-insensitive; IndexedDB is
        # not. Two entries from the same imported ZIP must not create both
        # Campaign/ROME.SAV and campaign/rome.sav in a fresh profile.
        code = self.web
        self.assertIn("const staged = new Map();", code)
        self.assertIn("const prior = staged.get(p.toLowerCase());", code)
        self.assertIn("const canonical = prior || p;", code)
        self.assertIn("staged.set(canonical.toLowerCase(), canonical);", code)
        self.assertIn("for (let dir = dirOf(canonical); dir; dir = dirOf(dir))", code)
        self.assertIn("if (!knownDirs.has(dir.toLowerCase()))", code)
        self.assertIn("knownDirs.set(dir.toLowerCase(), dir);", code)
        self.assertIn("out.set(canonical, data);", code)
        self.assertIn("await store.putMany(put.map(", code)
        self.assertLess(code.index("await store.putMany(put.map("),
                        code.index("if (fs)\n        for (const [k, data] of put)"))
        # No data migration or clearing of the owner's already saved keys.
        self.assertNotIn("store.clear()", code)
        self.assertNotIn("deleteDatabase", code)

    def test_translation_keys_exist(self):
        keys = ("file.new_folder", "file.create_folder", "file.folder_name",
                "file.folder_invalid", "file.folder_exists", "file.folder_failed",
                "file.delete_batch_confirm", "file.select_one")
        # The English template and actual owner-facing EN/zh-Hans/zh-Hant
        # must localize every key. The remaining four historic locales may
        # use the already-supported English runtime fallback ONLY for these
        # new keys; their original code-page bytes must not be rewritten.
        localised = {
            "src/host/texts.h": "utf-8",
            "data/native/lang/en.txt": "cp1252",
            "data/native/lang/zh-Hans.txt": "utf-8",
            "data/native/lang/zh-Hant.txt": "utf-8",
        }
        for path, codec in localised.items():
            text = (ROOT / path).read_bytes().decode(codec)
            for key in keys:
                with self.subTest(path=path, key=key):
                    if path.endswith(".h"):
                        self.assertIn('"' + key + '"', text)
                    else:
                        marker = "@@openciv2." + key + "\n"
                        self.assertEqual(text.count(marker), 1)
                        self.assertTrue(text.split(marker, 1)[1].split("\n@@", 1)[0].strip())
        source = (ROOT / "src/game/extras.cpp").read_text(encoding="utf-8")
        self.assertIn("if (lang_has(k))", source)
        self.assertIn("return lang_text(k);", source)
        self.assertIn("return i >= 0 ? texts[i].english : key;", source)
        for code, codec in (("de", "cp1252"), ("el", "utf-8"),
                            ("eo", "iso-8859-3"), ("la", "cp1252")):
            with self.subTest(locale=code):
                text = (ROOT / f"data/native/lang/{code}.txt").read_bytes().decode(codec)
                self.assertTrue(text.startswith("; OpenCiv2:"))


    def test_language_validator_allows_exact_same_legacy_fallback_keys(self):
        # The full pre-WASM language validator must not reject English
        # fallback keys allowed by this source test. No legacy locale
        # file is edited or re-encoded to satisfy this assertion.
        checker = (ROOT / "tests/lang_test.py").read_text(encoding="utf-8")
        match = re.search(r"folder_keys\\s*=\\s*\\{([^}]*)\\}", checker, re.S)
        self.assertIsNotNone(match, "language checker must define its fallback set")
        allowed = set(re.findall(r"'(file\\.[a-z_]+)'", match.group(1)))
        expected = {
            "file.new_folder", "file.create_folder", "file.folder_name",
            "file.folder_invalid", "file.folder_exists", "file.folder_failed",
            "file.delete_title", "file.delete_save_confirm",
            "file.delete_folder_confirm", "file.delete_failed", "file.delete_refused",
            "file.delete_batch_confirm", "file.select_one",
        }
        self.assertEqual(allowed, expected)
        self.assertIn("fallback_languages = {'de', 'el', 'eo', 'la'}", checker)

    def test_all_locale_keys_match_template_with_exact_legacy_fallbacks(self):
        # Source-only CI must catch a newly added English key BEFORE the
        # owner spends time on a full D:-isolated WASM build. Historic binary
        # translations stay unchanged; no transcoding or files generated.
        template = (ROOT / "data/native/lang/en.txt").read_bytes()
        def own_keys(data):
            return set(re.findall(rb"(?m)^@@openciv2\.([A-Za-z0-9_.-]+)\r?$", data))
        expected = own_keys(template)
        folder = {k.encode("ascii") for k in (
            "file.new_folder", "file.create_folder", "file.folder_name",
            "file.folder_invalid", "file.folder_exists", "file.folder_failed",
            # Historical de/el/eo/la binaries are immutable: these new five
            # keys use the English native fallback until localized separately.
            "file.delete_title", "file.delete_save_confirm",
            "file.delete_folder_confirm", "file.delete_failed", "file.delete_refused",
            "file.delete_batch_confirm", "file.select_one",
        )}
        legacy = {
            "de": "40d7f6a5eac8b7739df98f9cd19db5b5160fa4b7",
            "el": "42acbbdad178ed36c7525a1abe617a0ab784bc7e",
            "eo": "61caf027b434234e1b4fbe9824bdad789f5bd99e",
            "la": "fc926c18ca48ceeb6f0bfef02a71b544cc36ef8f",
        }
        for code in ("de", "el", "eo", "la", "zh-Hans", "zh-Hant"):
            with self.subTest(locale=code):
                raw = (ROOT / f"data/native/lang/{code}.txt").read_bytes()
                actual = own_keys(raw)
                self.assertEqual(expected - actual, folder if code in legacy else set())
                self.assertEqual(actual - expected, set())
                if code in legacy:
                    blob = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
                    self.assertEqual(hashlib.sha1(blob).hexdigest(), legacy[code],
                                     "Historical locale bytes must not be re-encoded")


if __name__ == "__main__":
    unittest.main()
