# CIV2-T018 — Save/Load multi-selection & safe batch deletion

Status: **source candidate; Windows WASM and Owner browser acceptance PENDING**.
Stacks on native T017 Draft #18 at `e8ae7bf48b014be65c4ca1ed7da6396f93410095`.
Owner requirement: [civ2-web Issue #70](https://github.com/ymzuowei/civ2-web/issues/70).

## Controls and selection

The **Save** and **Load** native file-dialog lists now use `LBS_EXTENDEDSEL`.
A normal left-click selects exactly one row; Ctrl+left-click toggles a file
or a directory; Shift+left-click selects an anchored contiguous range;
Ctrl+Shift+left-click adds a range. Selected entries stay highlighted.
Mouse double-click opens a folder / loads a single file as before. Open
and Save still accept ONE file, not a multi-file array.

**The `[..]` row is special navigation and can NEVER be selected:**
- On list refill `LB_SETITEMDATA` tags that row with
  `CIV2_LB_UNSELECTABLE_DATA`. No other rows are tagged.
- The native LISTBOX selection core excludes that row during plain click,
  Ctrl+click, Shift ranges, Ctrl+Shift ranges, keyboard selection and
  `LB_SETSEL`; GETSEL/GETSELCOUNT/GETSELITEMS never report it.
- Plain-clicking `[..]` clears stale selection but does not add `[..]`;
  Ctrl/Shift click on it does not modify the selected set. A focus caret is
  not a selection. Double-clicking `[..]` still returns to parent.
- Delete independently refuses any suspicious `[..]` entry if it somehow
  reaches the batch parser; no fallback to traversal.

## Delete safety

Delete is only intercepted when the native file LIST has focus, not when
typing a filename. Selected `.SAV` files and user-created directories
are resolved and bounded-preflighted **as a whole** before one translated
confirmation with item/file/folder counts. An unsafe selected row blocks the
entire operation; it is not silently omitted. Never recursively delete an
unmarked empty directory, unknown contents, links, game media or anything
outside the game-root SAVE subtree. Folder validation preserves T017
marker-supported empty user folders and legacy unmarked folders holding
only SAV content. Limits: 2048 visible rows, 4096 deletion-plan elements,
12 nested directory levels. Recheck every path before its unlink/rmdir.

Deletion is irreversible. The individual file APIs are not transactional;
a runtime I/O failure *during* deletion may leave some entries removed,
and the existing failure notice is shown. Owner should export ZIP before
destructive testing. No prior SAV, IndexedDB, or original media are
changed merely by deploying these controls.

## Acceptance plan

- F01: normal click selects a SAV; Ctrl+click toggles several SAVs and folders.
- F02: Shift+click range and Ctrl+Shift+click add range across scrolling.
- F03: `[..]` remains unselected on **all four mouse interactions**;
  Shift range crossing `[..]` cannot highlight/count it; double-click
  still navigates to parent, without deleting anything.
- F04: batch Delete prompts **once**, counts are correct; No leaves all
  selections and files intact. Filename editor Delete remains text editing.
- F05: mixed selected SAVs + eligible user folders delete with one Yes,
  and stay removed after browser reload on the same 127.0.0.1:8000 origin.
- F06: a selected media/foreign folder, or a forged parent selection,
  blocks the **entire** batch; no valid save is removed in the refusal case.
- F07: Save/Load single file, double-click folder, sort/reload/autosave,
  Chinese translations, controls outside the Save/Load dialog regressions.
- F08: exact D:-isolated Windows WASM candidate, Chrome/Edge real gestures;
  copyright-safe GAME=0 HD=0 build, no public/proprietary media bundling.

**No new freeze, retirement of the old B011/T016 kits, PR merge or
deployment until T017+T018 Owner gameplay acceptance.**

## 2026-11-22 Owner Windows build language-validator finding

Owner reported `CIV2_LEGACY_LANGUAGE_CODEPAGES=PASS`, `CIV2_ZH_HANS_TRANSLATION_TEST=PASS`, full CJK font coverage, then eight `FAIL data/native/lang/{de,el,eo,la}.txt: missing file.delete_batch_confirm/file.select_one` findings in the later `tests/lang_test.py` full-template check. Those two T018 strings are already in native `src/host/texts.h` and translated EN/zh-Hans/zh-Hant; the historical four non-UTF-8 language packs intentionally rely on `extras_text()`'s English fallback and are protected by exact Git blob SHA tests. The fix is to extend **only** the strict validator's legacy fallback allowlist by those two keys, plus cross-check that the validator and save-folder source policy allow the same 13 exact keys and only de/el/eo/la. No historical locale bytes or font files changed. Earlier screenshot/CI source PASS is not a new Owner WASM/browser PASS; rebuild from a new exact Web upstream pin.

## 2026-11-22 follow-up: escaped source-regex test correction

The subsequent Owner build reached `CIV2_T018_MULTISELECT_PARENT_BATCH=PASS` but its 17-test Save Folder Contract suite failed at `test_language_validator_allows_exact_same_legacy_fallback_keys`. The test mistakenly used doubled backslashes in two *raw Python regexes* (matching literal `\\s` and `\\.`, rather than whitespace and a literal dot), so `match` was None even though `tests/lang_test.py` correctly defined the 13-key `folder_keys` set. Correct both raw regex literals only. Checked the corrected expressions against the exact 13-entry set. No native UI functionality, original language bytes, saves or font files changed. A fresh exact-head source/WASM/Owner run is needed for PASS.
