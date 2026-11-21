"""CIV2-T011: source-level guards for faithful Save subfolder/autosave scope.

The real WASM/native browser dialogs still require compiled owner acceptance;
these checks prevent accidental separate-folder autosaves or root collisions.
"""
from pathlib import Path
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
                      "exportSaves(", "new TextEncoder()", "importPath(safe, existing)"):
            self.assertIn(token, self.web)

    def test_translation_keys_exist(self):
        keys = ("file.new_folder", "file.create_folder", "file.folder_name",
                "file.folder_invalid", "file.folder_exists", "file.folder_failed")
        for path in ("src/host/texts.h", "data/native/lang/en.txt",
                     "data/native/lang/zh-Hans.txt", "data/native/lang/zh-Hant.txt"):
            text = (ROOT / path).read_text(encoding="utf-8")
            for key in keys:
                with self.subTest(path=path, key=key):
                    if path.endswith(".h"):
                        self.assertIn('"' + key + '"', text)
                    else:
                        self.assertIn("@@openciv2." + key + "\n", text)


if __name__ == "__main__":
    unittest.main()
