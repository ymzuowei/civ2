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

    def test_zip_import_keeps_only_self_exported_safe_relative_paths(self):
        for token in ("SAVE_MANIFEST", "safeSavePath(", "preservedPaths?.has(safe)",
                      "exportSaves(", "new TextEncoder()", "importPath(safe, existing)",
                      "known.get(safe.toLowerCase())",
                      "knownDirs.get(dir.toLowerCase())",
                      "preserveCase(safe)", "safe.includes('/')"):
            self.assertIn(token, self.web)

    def test_translation_keys_exist(self):
        keys = ("file.new_folder", "file.create_folder", "file.folder_name",
                "file.folder_invalid", "file.folder_exists", "file.folder_failed")
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


    def test_all_locale_keys_match_template_except_exact_six_native_fallbacks(self):
        # Source-only CI must catch a newly added English key BEFORE the
        # owner spends time on a full D:-isolated WASM build. Historic binary
        # translations stay unchanged; no transcoding or files generated.
        template = (ROOT / "data/native/lang/en.txt").read_bytes()
        def own_keys(data):
            return set(re.findall(rb"(?m)^@@openciv2\\.([A-Za-z0-9_.-]+)\\r?$", data))
        expected = own_keys(template)
        folder = {k.encode("ascii") for k in (
            "file.new_folder", "file.create_folder", "file.folder_name",
            "file.folder_invalid", "file.folder_exists", "file.folder_failed",
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
                    blob = b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw
                    self.assertEqual(hashlib.sha1(blob).hexdigest(), legacy[code],
                                     "Historical locale bytes must not be re-encoded")


if __name__ == "__main__":
    unittest.main()
