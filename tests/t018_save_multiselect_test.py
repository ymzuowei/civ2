"""CIV2-T018: Save/Load multi-selection, unselectable [..] and batch Delete.

Source safety checks; Windows WASM and browser mouse/keyboard behavior
must be explicitly tested by Owner. No commercial media or game data.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeSaveMultiSelectionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = (ROOT / "src/platform/controls.c").read_text(encoding="utf-8")
        cls.dialog = (ROOT / "src/platform/filedlg.c").read_text(encoding="utf-8")
        cls.plat = (ROOT / "src/platform/plat.h").read_text(encoding="utf-8")
        cls.texts = (ROOT / "src/host/texts.h").read_text(encoding="utf-8")

    def test_only_save_load_dialog_uses_extended_listbox(self):
        self.assertIn('fd.list = control("LISTBOX", "", WS_BORDER | WS_VSCROLL | LBS_NOTIFY | LBS_EXTENDEDSEL,', self.dialog)
        self.assertIn("LB_GETSELCOUNT", self.dialog)
        self.assertIn("LB_GETSELITEMS", self.dialog)
        self.assertIn("LB_GETSEL,", self.dialog)
        self.assertIn("if (SendMessageA(fd.list, LB_GETSELCOUNT, 0, 0) > 1)", self.dialog)

    def test_windows_plain_ctrl_shift_and_ctrl_shift_range(self):
        c = self.controls
        self.assertIn("if (w->style & LBS_EXTENDEDSEL)", c)
        self.assertIn("int ctrl = GetKeyState(VK_CONTROL) < 0;", c)
        self.assertIn("int shift = GetKeyState(VK_SHIFT) < 0;", c)
        self.assertIn("lb->items[i].sel = !lb->items[i].sel;", c)
        self.assertIn("lb_select_range(w, lb, i, ctrl);", c)
        self.assertIn("lb_clear_selection(lb);", c)
        self.assertIn("lb->anchor = i;", c)
        self.assertIn("lb->anchor = -1;", c)
        self.assertIn("for (k = first; k <= last; k++)", c)
        self.assertIn("if (!lb_unselectable(w, lb, k))", c)
        self.assertIn("lb_select_range(w, lb, n, ctrl);", c)
        self.assertIn("case LB_GETSELITEMS:", c)
        self.assertIn("case LB_GETSELCOUNT:", c)

    def test_parent_row_cannot_be_selected_by_any_mouse_modifier(self):
        c, d = self.controls, self.dialog
        self.assertIn("#define CIV2_LB_UNSELECTABLE_DATA ((ULONG_PTR)-1)", self.plat)
        self.assertIn('if (row >= 0 && !strcmp(items[i].text, "[..]"))', d)
        self.assertIn("SendMessageA(fd.list, LB_SETITEMDATA, (WPARAM)row,", d)
        self.assertIn("(LPARAM)CIV2_LB_UNSELECTABLE_DATA", d)
        self.assertIn("static int lb_unselectable(Window *w, ListBox *lb, int i)", c)
        self.assertIn("lb->items[i].data == CIV2_LB_UNSELECTABLE_DATA", c)
        self.assertIn("if (lb_unselectable(w, lb, i)) {", c)
        self.assertIn("if (!lb_unselectable(w, lb, k))", c)
        self.assertIn("if (!lb_unselectable(w, lb, n))", c)
        self.assertIn("lb->items[lp].sel = !lb_unselectable(w, lb, (int)lp)", c)
        self.assertIn("if (lb->items[i].sel && !lb_unselectable(w, lb, i))", c)
        self.assertIn("return lb_unselectable(w, lb, (int)wp) ? 0 :", c)
        # Dblclick still navigates even though row has no selected bit.
        self.assertIn('if (!strcmp(item, "[..]")) {', d)
        self.assertIn('enter_dir("..");', d)
        self.assertIn('!strcmp(selected, "[..]")', d)

    def test_batch_deletion_preflight_is_whole_selection_or_refused(self):
        d = self.dialog
        self.assertIn("selected_count = (int)SendMessageA(fd.list, LB_GETSELCOUNT, 0, 0);", d)
        self.assertIn("SendMessageA(fd.list, LB_GETSELITEMS,", d)
        self.assertIn("for (j = 0; j < selected_count; j++)", d)
        self.assertIn("!safe_save_target(target, host, sizeof host)", d)
        self.assertIn("kind_of(target) != kind", d)
        self.assertIn("if (!plan_save_tree(&plan, target, 0))", d)
        self.assertIn("if (!plan_add(&plan, target, 0))", d)
        self.assertIn("goto refused;", d)
        self.assertIn('extras_text("file.delete_batch_confirm")', d)
        self.assertIn("MB_YESNO | MB_ICONWARNING", d)
        self.assertIn("MAX_DELETE_PLAN 4096", d)
        self.assertIn("MAX_DELETE_DEPTH 12", d)
        self.assertIn("if (!safe_save_target(entry->path, host, sizeof host)) break;", d)
        self.assertIn("if (i != plan.count)", d)
        self.assertIn("SetWindowTextA(fd.name, \"\");", d)
        self.assertLess(d.index("for (j = 0; j < selected_count; j++)"),
                        d.index("if (MessageBoxA(fd.dlg, prompt"))
        self.assertLess(d.index("if (MessageBoxA(fd.dlg, prompt"),
                        d.index("for (i = 0; i < plan.count; i++)"))
        self.assertLess(d.index('refused:\n    MessageBoxA'),
                        d.index('done:\n    free(plan.items);'))

    def test_legacy_empty_user_folder_is_only_single_selected_and_empty(self):
        # Reproduces Owner's 2026-11-22 empty legacy directory screenshot:
        # no marker or SAV yet, but an explicitly selected EMPTY directory
        # may be removed with Yes. A nested unknown empty directory must
        # still fail, and any actual content must not be silently deleted.
        d = self.dialog
        self.assertIn("int marked_this = 0, entries_here = 0;", d)
        self.assertIn("entries_here++;", d)
        self.assertIn("!(depth == 0 && entries_here == 0)", d)
        self.assertIn("plan->files - plan->marked == saves_before", d)
        for game_dir in ("MUSIC", "VIDEO", "KINGS", "SOUND", "SOUNDS",
                         "EREG", "SCENARIO", "DATA", "TUTORIAL"):
            with self.subTest(game_dir=game_dir):
                self.assertIn('"'+game_dir+'"', d)
        self.assertIn('!strcmp(selected, "[..]")', d)
        self.assertIn("MB_YESNO | MB_ICONWARNING", d)
        self.assertIn("rmdir(host)", d)
        self.assertIn("if (i != plan.count)", d)

    def test_batch_texts_translated_and_old_locales_unchanged(self):
        for key in ("file.delete_batch_confirm", "file.select_one"):
            self.assertIn('"' + key + '"', self.texts)
            for locale in ("en", "zh-Hans", "zh-Hant"):
                with self.subTest(key=key, locale=locale):
                    raw = (ROOT / "data/native/lang" / (locale + ".txt")).read_text(encoding="utf-8")
                    self.assertEqual(raw.count("@@openciv2." + key + "\n"), 1)

    def test_delete_only_on_list_focus_and_navigation_unchanged(self):
        d = self.dialog
        self.assertIn("(msg.wParam == VK_DELETE && msg.hwnd == fd.list)", d)
        self.assertIn("case ID_LIST:", d)
        self.assertIn("HIWORD(wp) == LBN_DBLCLK", d)
        self.assertIn("if (!strcmp(item, \"[..]\")) {", d)
        self.assertIn("fd.creating_folder || selected_count <= 0", d)
        self.assertIn("if (MessageBoxA(fd.dlg, prompt", d)
        self.assertNotIn("system(", d)
        self.assertNotIn("shutil.rmtree", d)


if __name__ == "__main__":
    unittest.main()
