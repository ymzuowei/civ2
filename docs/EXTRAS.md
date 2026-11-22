# Interface additions

OpenCiv2 adds to the original game's interface the features of
[CIV2UIA](https://github.com/FoxAhead/Civ2-UI-Additions), the "Civilization II User Interface
Additions" launcher by FoxAhead, which patches the original executable. They are written anew
for OpenCiv2's code from CIV2UIA's description of them; no code of CIV2UIA's is used.
Thanks to FoxAhead and the CIV2UIA contributors for the ideas and for documenting them.

This file covers the additions to the interface, which change only what the player sees and
does and are on by default, and, under [Rule changes](#rule-changes), the changes to the
game's rules (with the limits CIV2UIA takes from
[civ2patch](https://github.com/vinceho/civ2patch)), which are off by default. CIV2UIA's bug
fixes are in [BUGS.md](BUGS.md).

## On and off

The additions are on by default. They are off:

- with `CIV2_CLASSIC=1` (the original game: its look, its bugs, and none of these);
- in replays and unit tests, which are compared with the original game.

They change only what this player sees and how the interface is used, never what the game
computes, so they stay on in network games (a production changed from the City Status
advisor, or specialists changed with the wheel, are the same orders as through the city
window).

Each one can be switched off in [OpenCiv2 Options](#openciv2-options) (Interface additions), in
the game's main menu, or in the `[OpenCiv2]` section of `CIV.INI` (the file the game keeps its
own settings in, in its Windows directory, where OpenCiv2 Options writes them too): its key `=0`.
A change made in OpenCiv2 Options takes effect at once; one made in `CIV.INI` the next time the
game starts.

| Key | What |
| --- | --- |
| `MouseWheel` | Use the mouse wheel and middle button. The wheel scrolls whatever list or scroll bar is under the pointer (advisors, dialogs, the city window, the Civilopedia), changes the specialist under the pointer in the city window, and moves the tax rate bars. Ctrl+wheel zooms the map and Ctrl+middle click returns to normal zoom. Middle click centres the map on that spot; dragging with the middle button pans it. |
| `UnitListScroll` | When you click a stack of more than 9 units, the list of units to activate shows all of them and scrolls, instead of stopping at 9. As in the game's own list, clicking a unit wakes it, even if you then press Cancel. |
| `UnitListKeys` | In that scrolling unit list, the arrow keys, Page Up/Down and the mouse wheel move through the list. Needs `UnitListScroll`. |
| `WorkCounter` | Your settlers and engineers show on the map how much terrain work they have done so far. |
| `GameTurn` | The status panel shows the turn number after the year. |
| `ResearchNumbers` | The Science Advisor shows the research points collected so far, the cost of the current advance, and the points gained per turn. |
| `ZeroUpkeep` | The Trade Advisor also lists buildings that cost nothing to maintain. |
| `SupportScroll` | The city window shows how many units the city supports, with a scroll bar when they don't all fit. |
| `SupportSort` | The city window's supported units are sorted: settlers and engineers first, then attack units (land, air, then sea; strongest first), then the rest. |
| `AttitudeColors` | The Attitude Advisor shows celebrating cities in yellow, and an icon after a city's name when it has a food surplus or shortage. |
| `CityAttitude` | In the city window, the text under the citizens is coloured as in the Attitude Advisor: yellow when the city celebrates, red when it is in disorder. |
| `RadioHotkeys` | Options in dialogs get a keyboard shortcut: a letter of the option's name (underlined only with `HotkeyUnderlines`). |
| `Quickinfo` | Hold Ctrl with the pointer over a map square to see details of the city and units there. |
| `ProductionCancel` | The city's Change Production dialog gets a Cancel button; Escape cancels too. |
| `ProductionCost` | The Change Production list shows what each item costs in shields, and each building's upkeep. |
| `CityStatus` | The City Status advisor shows how many cities you have and each city's production as a picture. Click a column heading (size, name, food, shields, trade, production) to sort by it; click it again for the game's usual order. Click a city's production to change it. |
| `MassSpecialists` | In the city window, Shift+wheel over a specialist changes all specialists at once, and Shift+click on one makes all the others the same type. |
| `SuppressPopups` | Simple messages that only have an OK button can be shown for a few seconds across the top of the map instead of waiting for a click. List which ones by their GAME.TXT section names in `SuppressList=`, separated by commas, for example `SuppressList=HIDDENTERRAIN,CITYSIZE`. The message that another civilization has discovered an advance isn't in GAME.TXT; list it as `ADVANCENEWS`. The list is empty by default. |
| `ColorCorrection` | Adjusts the colours of the whole screen: `Gamma=` (a percentage, 100 means no change), `Brightness=` and `Contrast=` (-100 to 100, 0 means no change). These and `SuppressList=` are also in OpenCiv2 Options (Colours and messages). |
| `ForeignGold` | The Foreign Minister shows each civilization's gold with a coin icon. |
| `ArrangeWindowsSL` | The View menu gets Arrange Windows S and Arrange Windows L, which arrange the windows with a narrower or wider side panel than Arrange Windows. |
| `PathLines` | Hold Shift with the pointer over the map to see the path the active unit would take there, based on the map as you know it (units and cities you can't see aren't counted). With a city selected (View Pieces, the cursor on it), hold Shift over the same city to see lines to the cities it has trade routes with, or over another city to see the way a road or railroad must take to give their trade routes the road bonus (the game looks for it along this way only, up to the other city or one of your cities on the way): yellow if the road is already there and gives the bonus, white if not. |
| `SentryHalftone` | Units on sentry, and aircraft at a base, are drawn in grey shades so you can still tell what they are, instead of as a flat grey shape. |
| `DefaultZoom1` | A new game (or a save without a saved window layout) starts with the map at normal 1:1 zoom, whatever the screen size. |
| `HotkeyUnderlines` | Off by default: the hotkey letters `RadioHotkeys` gives options are underlined, as in the original's Windows dialogs. Off, the letters still work, only the line under them is not drawn. |

## File dialogs

The Open and Save dialogs can list files newest first (the Sort button), and they open in the folder of the last file loaded or saved. Both are remembered in CIV.INI under `[OpenCiv2]` as `FileSort=` and `FileFolder=`.

**Save folders and autosaves (CIV2-T011).** The native-style **Save As** dialog has **New Folder**. Choose it, enter a single folder name (for example `20261121`), and press Enter or Create. The dialog enters the new folder while retaining the suggested save filename. After **successfully** manually saving the current game there, subsequent automatic saves and their backup rotation use that same folder, exactly as with the original game's directory-based save organization. Canceling or failing to save does not change the auto-save destination. Loading a saved game from a folder rebinds autosaves to that folder; starting a new game resets the auto-save destination to the game's default folder until the player saves it elsewhere. Merely browsing another folder or loading unrelated files does not silently change the active game's autosave target.

In the browser, folders live in the virtual `/civ2` filesystem; after a saved file is written they persist through IndexedDB and can be recovered on refresh. Empty folders without files are not separately persisted by the current store. **Saves → Export saves** includes the original relative nested Save paths and a small `openciv2-saves-manifest.json` metadata entry; importing that ZIP into a different browser/profile restores those folders. Original game assets are not included. Older and foreign ZIPs without the manifest retain the existing safety-first behavior of flattening unknown outer folders. No browser upload of owned files occurs except local selection via the player's browser, and no server/cloud save service is introduced.

**New-folder language compatibility:** all six labels are translated in
English, Simplified Chinese and Traditional Chinese. German, Greek,
Esperanto and Latin currently use the native English text fallback for
those six newly introduced labels; their older translated texts and
historical binary encodings remain intact. The other translations are
still required to be complete. See [TRANSLATING.md](TRANSLATING.md).

## Screen scale

The game opens in a window, maximized to fill the screen. To play full screen instead, tick Full
screen in OpenCiv2 Options (Graphics and screen), or set `FullScreen=1` in `CIV.INI`; it takes
effect the next time the game starts.

On a high-resolution screen the game is drawn larger, in whole steps, so it stays sharp: each
of the game's pixels becomes 2×2, 3×3 or 4×4 of the screen's. On Windows the step follows the
display's Scale in Settings > Display, as the original is enlarged there, to the nearest whole
step: 100% 1 (the original's look), 150% and 200% 2, 300% 3. Elsewhere it is the step that
brings the game nearest the original's 1024×768 (in area), leaving it at least 800×560: a
MacBook Air's window 3 (the game at 980×594), a 4K screen 3 (1280×720), 2560×1440 2
(1280×720), 1920×1080 1. `Scale=` in `CIV.INI` sets the step instead (0: by the screen's size); it takes
effect the next time the game starts. The game is never made smaller than 640×480.

Text is drawn with fonts that have the widths of Windows' Times New Roman, Arial and Courier
New (the Liberation fonts, `data/fonts_win.bin`), so it is laid out as the original's on
Windows.

## OpenCiv2 Options

The game's main menu has one more choice after View Credits, *OpenCiv2 Options*, where the
player chooses how to play; the choices are kept in `CIV.INI`'s `[OpenCiv2]` section (only
those changed are written).  It is the game's own dialogs, as the Game menu's options: a list of
what can be chosen, each opening a dialog of its own (OK writes the choices, Cancel leaves them):

- **Mode**: *Standard* (the original's bugs fixed, [BUGS.md](BUGS.md), and these additions) or
  *Classic* (the original game: its look, its bugs, none of these; `Mode=Classic`, as
  `CIV2_CLASSIC=1`).  In Classic the other choices but the graphics are not offered.
- **Graphics and screen**: [sharp text and interface](#sharp-text-and-interface) (`SharpText=`,
  on by default in Standard, off in Classic); [HD graphics](#hd-graphics) (`Graphics=HD`, at the
  screen's own density), the art downloaded when they are ticked where it is not installed (234 MB,
  with its progress and a Stop button; see [HD-GRAPHICS.md](HD-GRAPHICS.md)); full screen
  (`FullScreen=`).
- **Rule changes** and **Limits**: the [rule changes](#rule-changes) and the limits.
- **Interface additions**: the additions above.
- **Colours and messages**: the colour correction (`Gamma=`, `Brightness=`, `Contrast=`) and
  the messages shown on the map (`SuppressList=`).
- **Language**: the language of OpenCiv2's own texts (this dialog, the file dialog, the
  message boxes, the set-up): *Automatic* (the system's language; in the browser version the
  page's), *English*, or one of the translations in the data directory's `lang/` (German,
  Latin, Greek, Esperanto and Traditional Chinese come with it); `Language=<code>` (`Language=Auto` or none: automatic).  It takes effect when
  the game starts again (*Restart now*); `CIV2_LANG=<code>` wins over it.  A translation may
  carry the game's own texts too (all of those that come with it do: the whole game); otherwise they are those
  of the installed game.  How to translate: [TRANSLATING.md](TRANSLATING.md).

The interface additions, the rule changes and the limits take effect at once (from the game
started or loaded next).  The mode, the graphics, full screen and the language take effect when the game
starts again: the dialog offers *Restart now*, which starts the program again with the same
arguments but `--hd` and `--sharp` (in the browser version: the page is loaded again), or
*Later*.  `CIV2_CLASSIC=1`, `--hd` / `CIV2_HD` and `--sharp` / `CIV2_SHARP` win over the
choices made there, for the run they are set in (the dialog says so).

It is in the main menu in Standard and in Classic mode alike (the only thing Classic shows that
the original does not), and in the browser version (where HD graphics are offered only where
the site has their art, [BROWSER.md](BROWSER.md#hd-graphics), and full screen is the browser's).
It is not in replays and unit tests, which compare the main menu with the original's
(`CIV2_TEST_OPTIONS=1` shows it in a replay, where nothing is written to `CIV.INI`, downloaded
or restarted: `harness/extras/x-options.txt`).  Its texts are keyed (`src/host/texts.h`) and
translated with the rest ([TRANSLATING.md](TRANSLATING.md); `harness/extras/x-lang-eo.txt`
shows it in Esperanto, `x-lang-de.txt` in German, `x-lang-la.txt` in Latin, `x-lang-el.txt` in Greek, `x-lang-zh.txt` in Chinese).

These choices were made before in an opening window shown before the game started (and, before
that, in Game > OpenCiv2 Options); OpenCiv2 Options in the main menu replaces both.

## Sharp text and interface

On a high-resolution screen (a [screen scale](#screen-scale) of 2 or more) the game is shown at
the screen's full resolution: text is drawn from glyphs of the same fonts as many times as tall,
and what the platform draws itself (the menu bar and its menus, window captions and frames,
buttons, check boxes and radio buttons, scroll bars, edit boxes, list boxes, combo boxes, the
file dialog) is drawn at that resolution: its curves and diagonals (radio
buttons, check marks, the scroll bars' arrows, the combo box's arrow, the close box) drawn smooth,
its straight lines and edges as many screen pixels wide as the game's pixel is.  The game's own
pictures (terrain, units, cities, portraits, backgrounds, the icons of its dialogs) stay the
original bitmaps, enlarged as before.  It is on by default in Standard mode, off in Classic, and
can be switched in OpenCiv2 Options (Graphics and screen) or with `SharpText=1` / `=0` in
`[OpenCiv2]`; `--sharp` (or `--sharp=0`) on the command line, or `CIV2_SHARP=1` / `=0`, wins for
that run (`--sharp=N`, N from 2 to 4, sets the density, for tests).  Where the screen scale is 1
(a 1920x1080 screen, or Windows' display scale at 100%) it has nothing to do and changes nothing.  It is drawn by the HD graphics'
renderer without their art ([HD-GRAPHICS.md](HD-GRAPHICS.md#the-planes-sharp-text-and-interface));
with HD graphics on as well, the two combine.  It changes only what is shown: the game's own pixels,
which its code reads back, and its random numbers are the same with it or without.  Off in replays
and unit tests (`CIV2_TEST_SHARP=N` turns it on at density N in a replay:
`harness/extras/x-sharp.txt`, and OpenCiv2 Options' `x-options-sharp`).  In the browser version:
in OpenCiv2 Options as natively, or `?sharp=0` in the address ([BROWSER.md](BROWSER.md#hd-graphics)).

## HD graphics

`Graphics=HD` in the same `[OpenCiv2]` section (HD graphics in OpenCiv2 Options; or `--hd` on
the command line, or `CIV2_HD=1`) draws the map (and wherever the same pictures appear) with
The replacement art (openciv2-assets), once installed (by OpenCiv2 Options, or `make hd`), at the screen's
full resolution (`GraphicsDensity=`).  Off by default, with `CIV2_CLASSIC=1`, in replays and
unit tests; it changes only what is shown.  See [HD-GRAPHICS.md](HD-GRAPHICS.md).

## Rule changes

CIV2UIA's items that change the game's rules, and the limits it took from civ2patch, are off
by default: each is switched on in OpenCiv2 Options (Rule changes, Limits) or in the
same `[OpenCiv2]` section of `CIV.INI`, the item by its key `=1`, a limit by its value (`=0` or
no key: the original's). They are off with
`CIV2_CLASSIC=1`, in replays and unit tests, and in network games (as the state fixes of
[BUGS.md](BUGS.md): every player, the original game included, must compute the same game);
they stay on in hot-seat games. The changes for units apply to the human
players' units only: the computer players play by the original rules.

| Key | What |
| --- | --- |
| `WorkerHandover` | When a settler or engineer joins another already doing the same terrain work on its square, the newcomer takes over the work done so far and the first one is freed to go elsewhere. Only one worker keeps the order on each square. |
| `GotoNoZocStop` | A unit on Go To keeps going when it comes next to a foreign unit, instead of stopping (in the original, only caravans and freight do). Zones of control still apply: it stops when one blocks its way or it runs out of moves. A unit sent at an enemy will attack whatever is in its way. |
| `UnitRotation` | When you activate a unit, the other units on its square come next before any elsewhere. After that, the next unit is the one nearest to where you last activated a unit, rather than to where that unit has since moved. |
| `MassMove` | Shift+right click on a square sends the active unit there along with every unit of the same type on its square that can move and has no orders (not fortified, on sentry or working). Each goes as far as it can this turn, as with Go To. |
| `StackSentry` | `U` normally wakes the land units on sentry in a stack. If none is on sentry, `U` instead puts all the stack's land units that have no orders on sentry (on a ship: loads them). |
| `RetirementYear=` | Sets the year the game ends with retirement (1 to 9999; the original is 2020). `RetirementWarningYear=` sets the year of the warning (0 for none; by default 20 years earlier). Each happens on the first turn on or after that year. The game's own messages still say "in 20 years". |
| `PopulationLimit=` | Raises the highest population a civilization can reach, in units of 10,000 people (32000 to 3275800; the original is 32000, which is 320 million). The Hall of Fame still records at most 320 million. |
| `GoldLimit=` | Raises the most gold a treasury can hold (30000 to 1000000; the original is 30000). |
| `MapTilesLimit=` | Raises the largest custom world, as width × height in squares (10000 to 32767; the original is 10000). Each side is still 20 to 250 squares. The dialog's text still says 10,000. |

## CIV2-T011 — Owner Save dialog UI and UTF-8 filename follow-up (2026-11-21)

Owner's real Chrome HD session with the compiled T011 candidate confirmed that
**New Folder** creates the selected `20261121` directory inside the game's
virtual `Z:\\civ2` save root; manual `20261121/_b3460.sav` is present
in the matching **Load** dialog; after subsequent turns the folder contains
additional `_自动*.SAV` files. Therefore **F01 and F02 PASS** for this
scenario (including original per-folder automatic save placement); cross-
campaign and browser-refresh/ZIP coverage are still pending.

Three visible shortcomings were reproduced:

- **Save-dialog path label stale after folder creation.** The list followed
  `fd.dir`, but `refill()` only called `SetWindowTextA` on the STATIC
  label. The custom UI control does **not** automatically repaint on
  `WM_SETTEXT` (the existing `set_text()` helper intentionally calls
  `InvalidateRect` afterward). Fix: use `set_text(fd.dirlabel, label)`
  for every refill. The Load dialog in the same folder already displayed
  `Z:\\civ2\\20261121` properly, so there is no path persistence rewrite.

- **"新建文件夹" button compressed.** The original 108 logical-pixel button
  could overlap Chinese glyphs at browser scaling. Only the Save dialog
  grows from 440 to 480 logical pixels; its folder button grows to 140,
  list/directory/edit controls gain available width and Save/Cancel shift
  to preserve separate hit targets. Load dialog remains 440. No change to
  window scaling, font pipeline or HD/Classic map.

- **The leading box in the default `□_b3460.sav`.** The decompiled
  original `game_save_dialog()` used `file_name_buf[3] = 0`: with the
  filename starting at `file_name_buf + 1` this cuts the leader's name
  at **two raw bytes**. A UTF-8 Chinese character needs three bytes,
  so the source produced an invalid leading sequence and a replacement
  glyph. Fix: use the existing `u8_len_at` / `u8_decode` helpers to
  preserve **two whole characters**, or two original bytes in single-byte
  locales. Invalid UTF-8 stops before the damaged character. The original
  year/era suffix, SAV extension, manual save/load and auto-save rotation
  logic remain unchanged. Existing oddly named files are **not**
  renamed/deleted/migrated; they remain loadable.

Regression tests `tests/save_folder_contract_test.py` cover the redraw,
actual control geometry and source UTF-8 character boundary contract.
**These three fixes remain source-only until a new D:-local Windows WASM
build and owner browser re-test.** F03/F04/full F05/F06/F07/F08 are not
inferred from the current screenshots.

## CIV2-T011 — Save dialog caption ghosting follow-up (2026-11-22)

Owner Chrome re-test after the UTF-8 filename-prefix and Save dialog
width corrections confirmed **the default prefix now renders as Chinese**
(e.g. `武则_b3460.sav`), and actual Save As navigation shows the correct
folder in the file list. Existing F01/F02 folder-save/autosave evidence
remains valid. Two screenshots still expose **overprinted directory and
label glyphs** after switching Save dialog folders, even when the
internal `fd.dir` state and Load dialog paths are correct.

Source root cause: the emulated Win32 `STATIC` control in
`src/platform/controls.c::ctl_static_proc()` calls
`DrawTextA` with `TRANSPARENT` background on a **retained** top-level
window surface, but does **not** fill its old pixels first. The earlier
`set_text()` change in `src/platform/filedlg.c` invalidated the
label, yet repaint merely drew new glyphs over the old ones. Increasing
button width or invalidating again cannot erase retained glyphs.

Minimal fix: in the STATIC renderer, only when the parent window's
class is `Civ2FileDialog`, clear the control's own client rectangle
using the same `COLOR_3DFACE` background already used by the
native BUTTON renderer, **before** drawing the new caption. Other
STATIC controls retain their original transparent rendering (including
possible game artwork overlays). `set_text()` now also calls
`UpdateWindow(h)` after invalidation, so the current path is painted
before the next input is handled. The label text and filesystem are
unchanged. The observed `创建` vs `新建文件夹` button captions
are expected create-folder mode vs normal mode, **not** a new width bug.

`tests/save_folder_contract_test.py` guards the targeted paint order,
normal/create button transition, and immediate repaint, in addition to
previous UTF-8, ZIP and autosave coverage. The new native change
**requires a fresh Windows WASM build** for owner visual acceptance;
the previous screenshot does **not** verify this renderer fix.
Never rename/delete a player's existing save to test it. Avoid all HD
colour, grid, audio, private asset or other repository changes.

## CIV2-T011 — File-name caption ghosting, separate from directory header (2026-11-22)

Owner's latest screenshot after the initial STATIC background repair shows the
top `文件夹：Z:\\civ2\\20261122` caption readable, with a working
`武则_b3460.sav` default prefix. However the *separate lower-left*
caption is still visibly overlaid: old `文件夹名称：` pixels and
new `文件名：` appear together as `文件名名称：`.
**Do not close this issue merely because the top directory caption
is now correct.** This appears after switching folder-creation mode
back to ordinary filename mode; both strings use the same STATIC HWND.

The extra corrective measures are limited to the Save As dialog:
* Reserve 155 logical pixels for the longer Chinese name caption, and
  start its edit field at x=175 instead of x=130 so the label cannot
  intrude on the editor.
* Before changing the mode caption, erase the entire previous label strip
  via the **parent dialog DC**, using its `COLOR_3DFACE` background.
  This clears retained old glyphs even if a prior child paint escaped
  its clipped region; then set and immediately repaint the one STATIC.
  Never erase the adjacent edit input or any map pixels.
* Render file-dialog STATIC captions as *one line* with `DT_SINGLELINE`
  instead of `DT_WORDBREAK`, so changing Chinese captions cannot create
  clipped/ghosted wrapped lines. All non-file-dialog STATIC renderers
  keep their existing behavior.

The translation strings themselves remain correct:
`file.name = 文件名：`, `file.folder_name = 文件夹名称：`.
Source regressions now explicitly cover changing both states and the
dedicated background wipe. This newest candidate requires another
owner-local D:-only WASM/browser visual test; source tests alone do not
prove the rendered overlap has disappeared. The earlier F01/F02 and
UTF-8 filename PASS evidence remains, with F03–F08 unverified.

## CIV2-T014 — Native autosave Unicode prefix / remaining Save lifecycle contracts (2026-11-22)

After owner acceptance of T011 F01/F02 and T013 F07a/F07b/F07c,
we reviewed the remaining T011 F03, F04, F05, F06 and F08 gates.
The native `game_save_dialog()` default filename had already been
corrected to keep the leader's first two **complete UTF-8 characters**,
which the owner confirmed fixed the visible Chinese white-square
prefix. However `game_autosave()` in `src/auto/game.cpp` still
truncated the leader with `textbuf.buf[2] = 0`: two raw bytes
in UTF-8 can leave a truncated 3-byte Han character. Both the
current automatic SAV filename and its backup/rotation filename
were built from this malformed prefix. This is a **source finding**,
not a claim of newly observed or corrupted existing player saves.

**Narrow fix:** export the already-accepted
`game_save_leader_prefix_bytes()` helper from `game_save.cpp`
through `auto_common.h`, and use it when naming **both** newly
written automatic saves and backup files in `game.cpp`. In
UTF-8 mode the helper validates and preserves two complete
characters; in the legacy single-byte locales it continues to
use exactly the original first two bytes. The autosave cadence,
`(game.turn & 4U) == 0` backup condition, remove→rename→write
sequence, original suffixes, selected-folder routing and game
engine state remain unchanged.

**Compatibility:** Previously written legacy autosaves are
not deleted, renamed, migrated or rewritten. The new valid
Chinese prefix may create a *newly named* autosave alongside
previous malformed/old-name files; therefore the next actual
owner check must verify existing saves can still be loaded and
new files rotate correctly. Do not use destructive cleanup to
make file names appear consistent.

`tests/save_folder_contract_test.py` adds F03/F04/F05/F06/F08
structural regression for successful-save-only folder switching,
cancel/failed-save isolation, successful-load-only restoration,
new-game reset to root, missing destination fail-closed,
and backup renames within the temporarily selected folder.
These tests **do not** replace compiled Windows WASM or Owner
browser checks; F03, F04, full F05, F06 and F08 remain **PENDING**.
T013 F07 all owner PASS remains untouched. No Original/HD
graphics, audio, toolbar, Display, CI runner, or existing
browser-owned game content modifications.
