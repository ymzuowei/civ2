# Developing OpenCiv2

How the reconstruction is organized and checked. Building and playing: [README.md](../README.md);
progress: [STATUS.md](STATUS.md).

## Layout

| Path | What |
| --- | --- |
| `src/auto/` | The game: decompiled once, now C++ edited directly, a file per subject (`city.cpp`, `unit.cpp`, `ai.cpp`, `diplomacy.cpp`, `map.cpp`, `window.cpp` …), the largest in parts named after it: `game_setup.cpp`, `game_save.cpp`, `game_events.cpp` and `game_events_editor.cpp`, `game_diffeng.cpp`, `game_cheat.cpp`, `game_status.cpp`; `network_messages.cpp`, `network_join.cpp`, `network_parley.cpp` and `network_parley_panes.cpp`; `city_window.cpp`, `city_production.cpp`, `city_advisors.cpp`, `city_view.cpp`, `city_editors.cpp`; `unit_move.cpp`, `unit_combat.cpp`, `unit_spy.cpp`, `unit_editors.cpp`; `window_dialog.cpp`, `window_menu.cpp`; `graphics_surface.cpp`, `graphics_sprite_editor.cpp`. |
| `src/game/` | Functions the decompiler could not translate, reconstructed by hand. |
| `src/data/` | The game's static data, laid out exactly as in the original: defined in `gamedata.cpp` (address order), declared by subject in `state/` (`game.h`, `city.h`, `network.h` ..., the texts in `strings.h`); records listed in `re/state_records.txt`. |
| `src/include/` | Types recovered from the binary: units, cities, civilizations, map, the game's classes. |
| `src/platform/` | The Windows API the game uses (windows, GDI, controls, files, sound, video) implemented in portable C. |
| `src/host/` | What the platform layer needs from the machine: window, input and audio over SDL2; the portable build's runtime. |
| `src/native/` | The C runtime pieces the native builds need. |
| `src/third_party/` | Bundled third-party decoders (Indeo 4 video, Ogg Vorbis). |
| `data/` | Fonts as the original renders them, and the original executable's data sections. |
| `re/` | Analysis results: function list, calling conventions, data layout, Ghidra's decompilation. |
| `harness/` | The replay scripts and the comparison with the original (`run.py`, `compare.py`, `native_suite.sh`). |
| `tests/` | The unit tests (`make test`: recorded calls of the game's functions, `tests/unit`) and small standalone tests (data layout, network records, CD music reading). |
| `hook/` | An `XDaemon.dll` proxy that makes the original deterministic under Wine. |
| `tools/` | Build, analysis and refactoring scripts. |
| `docs/` | Notes on the reconstruction and its verification; progress in `STATUS.md`. |

## Approach

1. **Inventory**: Ghidra decompiles all ~4,900 functions; names and types for every function,
   global, class and field were recovered from their use.
2. **Translation**: the decompiled code was turned into C that compiles natively, then edited
   by hand: names, types, struct access, real locals, data as ordinary variables. It is now C++
   (`docs/hand-reconstruction.md`).
3. **Platform**: the game keeps calling the Windows API; `src/platform` implements the part it
   uses on top of SDL2, so the same game code runs everywhere.
4. **Determinism**: under Wine, the `hook/` proxy DLL pins the original's random seed, gives it a
   virtual clock and replays recorded input. The native builds do the same, so a recorded
   scenario plays identically in both.
5. **Differential harness**: each scenario in `harness/scripts` (new game, turns, cities,
   diplomacy, editors, 50 turns of play …) is recorded from the original once; the native builds
   replay it and must produce the same screenshots and the same sequence of `rand()` calls.
   Changes to the code are also checked function by function against the previous version's
   machine code (`tools/cxx_compare.py`), which covers the code no scenario reaches.

## Tooling

Development runs in Docker on Linux; `tools/dk CMD` runs a command in the dev container with
the repository at `/work` and the game at `/civ2`.

| Tool | Notes |
| --- | --- |
| Docker images (`make images`) | Wine (runs the original), MinGW, g++/gcc with 32-bit support, SDL2, Python; Ghidra for the analysis. |
| wasi-sdk + wabt (`tools/fetch-toolchain.sh`) | The portable build: the game compiles to a wasm32 module (keeping the original's 32-bit data model), which wasm2c turns into C for any machine. |
| `hook/` (`make hook`) | The proxy DLL that makes the original replayable. |

Windows builds: the release (`make windows`, cross-compiled on Linux with MinGW) uses the older
C runtime (`msvcrt.dll`), with SDL2 built in; a build in an MSYS2 UCRT64 shell (README) uses the
Universal C Runtime, with `SDL2.dll` beside it. Both run on Windows 10 and later. MSYS2's
MINGW64 environment (the `mingw-w64-x86_64-` packages) still builds the game, but MSYS2 has
deprecated it.

```sh
make native          # build/civ2-linux32: gcc -m32, the same code, easier to debug
make port            # build/OpenCiv2 in the container
make ref SCRIPT=harness/scripts/turns.txt    # record the original on a scenario
make native-suite    # replay every scenario on a native build and compare (EXE=OpenCiv2, OpenCiv2.exe under Wine)
make test            # the unit tests: recorded cases of the game's functions, in seconds (no game files needed),
                     # then the source probes (tests/*_test.cpp: memory-error fixes, g++ -m32)
make test-extras     # the additions' tests: harness/extras replayed and compared with our recorded output
make test-media      # opt-in: the CD's videos and music (harness/media), where the game folder has them
make unit-record     # record those cases again from the replays (needs the game and run/ref-*)
```

The replay checker requires a nonempty, matching set of PNG screenshots (including
dimensions and pixels) and nonempty `rand.log` traces on both sides. A seed-only
trace is valid; missing or empty logs are not evidence of matching random calls.
Where the recording has a `calls.log` it must match too: the sounds the game plays
(`snd_play_effect`: effect, mode, loop) and the videos it looks for (each `.avi` path
`file_resolve_path` is given), in order, which the reference cannot play (no audio
device, no video files or Indeo codec). The hook logs them from breakpoints on the
original's two functions (`CIV2_CALL_LOG`, hook/stackprobe.c), the native builds
from the same functions (src/platform/replay.c).
A free IV41 decoder in the reference's Wine prefix does not help. ffdshow-tryouts
rev4531 (VfW codec `ff_vfw.dll`, `iv41` set to libavcodec) decodes IV41 through
`ICDecompress`, but only to RGB24/32 or YUV. The original's player calls
`ICDecompressEx` (`ICM_DECOMPRESSEX_QUERY` gets `ICERR_UNSUPPORTED`), wants 8-bit
frames and the codec's palette (`ICM_DECOMPRESS_GET_PALETTE` fails), and uses
Intel's private message 0x5001 for the heralds' drawn area. So the game closes the
codec and shows no video. The codec does change the replay: the same script loads
into a different game, with a different emissary and a different video for
the council (council0, not anarchy0), so such recordings do not match the stock ones. ffdshow's luma is
bit-identical to `src/third_party/indeo4` (FFmpeg 6.1.2) for the first 40 frames
of COUNCIL0.AVI and HRLDROM.AVI. The chroma could not be compared exactly because
ffdshow resamples 4:1:0 to 4:2:0. Only Intel's own `ir41_32` codec would play the
videos in the reference.
Both `native_suite.sh` and `diff_suite.sh` fail a scenario if its runner or BMP
conversion fails, then continue with the remaining scenarios and return failure
for the suite. A failed run is not subsequently reported as `PASS` or `SAME`.

Checker regression tests use synthetic images and a stub game runner. They need
Python 3, Pillow and a POSIX `sh` for the suite tests, but no game assets, native
build or Wine. Without `sh`, only the suite tests are skipped.

```sh
python3 tests/test_replay_harness.py -v
# Or in the development container:
tools/dk python3 tests/test_replay_harness.py -v
```

## Tests of the additions

`make test-extras` checks OpenCiv2's additions to the original (docs/EXTRAS.md: the interface
additions and the rule changes), which the original game has no recording of.  The scripts in
`harness/extras` replay them on the native build (`harness/extras_suite.py`) and are compared with
our own output, recorded once after checking its screenshots by eye: `harness/extras/expected/NAME.txt`
holds a hash of each screenshot's pixels and of the `rand()` trace, `NAME.rand.gz` the trace itself
(about 200 KB in all; no image or text of the game's).

* A script says how it is run in its first comment lines: `# test: CIV2_TEST_EXTRAS=1
  CIV2_TEST_FULL=640x480` (the variables of the run), and `# test LABEL: ...` for a further run of
  it, named `NAME-LABEL`.  `CIV2_TEST_EXTRAS` turns additions on by number (`1`: all the interface
  additions; `17,42`: those rule changes), `CIV2_TEST_SETTINGS` sets `CIV.INI` values
  (`RetirementYear=1902,Gamma=150`), `CIV2_TEST_SUPPRESS` the popups shown on the map,
  `CIV2_TEST_OPTIONS=1` puts OpenCiv2 Options in the main menu (its choices hold for the run,
  nothing is written to `CIV.INI`, downloaded or restarted: `x-options.txt`), and
  `CIV2_TEST_FULL=WxH` shows the whole game window on a WxH desktop (the interface scripts: 640x480)
  instead of the reference desktop of the replays (the rule changes' scripts).
* Each run's screenshots (PNG) and logs are in `run/extras-NAME`.  On a failure the suite names
  the screenshots that differ and the first `rand()` call that does, and writes
  `run/report-extras-NAME/index.html`: the differences from the blessed screenshots where this
  machine has them (`run/extras-blessed`, kept by the last bless), else this run's screenshots.
* An intended change of what a script shows: run `make test-extras` (or `NAMES="x-prod x-wheel"`),
  look at `run/extras-NAME/*.png`, then `make extras-bless NAMES=...`.  Blessing runs each script
  twice and refuses one whose two runs differ (`--twice` checks that without blessing).  A new
  addition gets a script and is blessed the same way.
* The replays' virtual clock (as the original's under the harness) lets 10 ms pass at each empty
  check of the message queue, and the map's drawing checks once per square, so redrawing a large
  map takes seconds of the script's time (docs/STATUS.md): wait long enough (about 12 s) after
  anything that redraws the map before a screenshot or a click.
* The tests need the game's files, like the replays, so they do not run in the release workflow
  (which has no game files and must not get them); run them locally before pushing changes to the
  additions.

## Media tests

`make test-media` (opt-in: never part of the suites above) replays the scripts in
`harness/media` on a copy of the game that has the CD's videos and music (`KINGS`, `Video`,
`Music` in the game folder; the other runners strip them, `CIV2_KEEP_MEDIA=1` keeps them) and
compares them, like the additions' tests, with our own output, checked by eye and blessed
(`make media-bless NAMES=...`, the expected results in `harness/media/expected`, each run in
`run/media-NAME`; `harness/extras_suite.py --media`).  Where the game folder lacks those folders
it says so and skips them; the HD runs (`# test hd:`, `CIV2_TEST_HD=2` with the pack in
`data/native/hd`) are skipped without the pack.  Besides the screenshots and the `rand()` trace,
`calls.log` must match (`NAME.calls`): the sounds played, the videos looked for, and the music.

* The music: in these runs the CD drive is on (`CIV2_TEST_MUSIC=1`, `src/platform/sound.c`), its
  tracks played silently on the virtual clock, each as long as its `Music\TrackNN.wav` says, so
  which track the game plays and when it ends is the same in every run; `calls.log` has a line
  for each `music play N`, `stop` and `end` with the time (`t=` ms of the script).  The game picks
  its tracks with `rand()`, so a game with music has a `rand()` trace of its own.
* `m-opening`: the opening video to its end, then the main menu.  `m-council`: the High Council
  (only with the videos: `CouncilWindow::init` gives up without them), the military advisor
  speaking, then under Anarchy.  `m-herald`: an animated herald (`KINGS`) in the diplomacy room,
  a few frames.  `m-wonder`: the Oracle's movie to its end and the map after it closes, the
  Pyramids' closed with Escape.  `m-music`: the tracks played at random and at each one's end,
  Pick Music, the Game Options' Music unticked (stop) and ticked again.  The opening, council and
  herald and the wonder's movie also with HD graphics (`-hd`): their game pixels, `rand()` traces and `calls.log` are
  those of HD off.
* The scripts first skip the opening video (Escape) but `m-opening`.

`tools/native-run.sh` stops a run that hangs after `TIMEOUT` seconds (default 600; the suites:
900): the game ignores SIGTERM, so it is killed `TIMEOUT_KILL` seconds (default 10) later.

## Unit tests

`make test` checks the game's logic in seconds (2.5 s for the cases, a few more to build):
11,119 calls of 880 of the game's functions (combat odds and strengths, movement and paths,
city food, shields, trade, happiness and
production choice, the AI's assessments and unit orders, research, diplomacy, map generation steps
...), each recorded from a replay of the reference scenarios, called again with the same arguments
and state, and compared with what it did then: its return value, every byte of the game's state it
changed and its `rand()` calls.  A change to the logic that any recorded call sees fails the test,
naming the function, the call and the first byte that differs (`cities+0x1a2`).

* **Recording** (`tests/unit_record.c`, `make unit-record`).  The recording build
  (`build_native.py --target linux32rec`) compiles the game and the platform layer with
  `-finstrument-functions`: every function calls the recorder on entry and exit.  While a replay runs
  (`tools/unit_record.sh`: the scenarios in `UNIT_SCRIPTS`, 43 of the 44, each run checked against
  the original's recording as by the suite), the recorder takes some calls of each game function (the 1st, 2nd, 3rd, 4th, 6th,
  9th ...; at most 6 per scenario and 16 in all): the argument words (by the signatures
  `tools/unit_sigs.py` gets from the debugging information), the state at entry (the game's data,
  `src/data/gamedata.cpp`, and the map's blocks), the return value (the function's return address is
  pointed at a trampoline that catches it) and the state at exit.  A call that reaches the platform
  layer (windows, drawing, files, the clock: anything but the `rand()` trace), allocates or frees
  memory, or changes state outside the game's data (`tools/unit_sigs.py --statics`) is not taken.
  Arguments that point into the caller's stack are recorded with the stack they point into (and what
  pointers there point to); a pointer anywhere else but the game's data and the map is not taken.
  The `rand()` generator's seed is game data, so a case replays its random numbers exactly.
* **Running** (`tests/unit_run.c`, `make test`).  The runner (`--target linux32test`,
  `build/civ2-unittest`) is the game with its initializers run and no window: for each case it sets the
  game's data and the map as they were, calls the function, and compares (crashes and hangs are
  failures, not aborts).  Both builds put the game's data at a fixed address (0x30000000), so
  pointers into it mean the same in the recording and in later builds; both are instrumented, as gcc
  passes a static function's arguments in registers unless its address is taken.  After recording,
  the runner keeps only the cases it reproduces, twice in each of three processes
  (`civ2-unittest --bless`): calls that read memory outside what is recorded (the heap: the recorder
  moves its heap away so that such pointers point to nothing) drop out there.
* **Data** (`tests/unit/*.gz`, 3.1 MB).  A case's state is a delta from the previous case's,
  compressed.  No text from the game's files is recorded: where the game's data holds text (every
  `char` array and text buffer, `tools/unit_textmask.py` -> `tests/unit/textmask.tsv`) the cases have
  what the game's initializers leave there, and on the stack what looks like text is zeroed; the
  runner compares the same way.  So the tests need no game files and run anywhere the 32-bit Linux
  build does (the release workflow runs them).  `tools/unit_coverage.py` lists the functions with
  cases by file (`tests/unit/cases.tsv`).
* **When the code changes**.  Renamed functions are skipped (named in the report); a change of the
  game data's size or layout needs a new recording (`make unit-record`, about an hour), as does a
  function whose arguments change (a free function whose parameter types change but whose argument
  words mean the same, `int` -> `RECT *`, is still found by its name).  A failing case after an intended change of behaviour: check it
  against the replays (which compare with the original), then record again.

## Browser version

`make web` builds `build/web`, a static site that plays single-player games in a browser
(README "Browser version"); all of it is in `src/web` and `tools/build_web.py`, and the native
builds do not use it.

* **The module**: the portable build's `build/wasm/civ2.wasm` (the same game and platform layer,
  `tools/build_port.py module`), passed through Binaryen's `wasm-opt` (`tools/fetch-toolchain.sh
  web`, version 130) with `--fpcast-emu` and `--asyncify`, then `-O2` without the debugging
  information: 2.9 MB (1 MB gzipped).  `--fpcast-emu`: the decompiled code calls through function
  pointers of other types than their targets, which wasm traps on; the native port patches wasm2c's
  check out (tools/build_port.py), the browser cannot, so every function in the table gets a thunk
  of one common type (indirect calls are a little slower).
* **Blocking, the decision**: the game's loop blocks (`GetMessage` waits for input, `Sleep`, message
  boxes, and busy loops that only peek at their input).  Two ways were weighed: (A) asyncify, the JS
  host on the page's main thread, where the module's stack is unwound at the imports that wait and
  wound back once the page's event loop has run; (B) the module in a Web Worker blocking on
  `Atomics.wait`, frames, input, audio and message boxes passed to and from the page, which needs
  cross-origin isolation (COOP/COEP headers; on static hosting such as GitHub Pages, a
  service-worker shim).  A was built first and kept: its cost is size (the code doubles: 1.4 MB
  without asyncify, 2.9 MB with) and about 25% speed in the game's own code, against B's isolation
  headers, a second thread's plumbing for every host function, and audio and the cursor from a
  worker.  The imports that unwind are `host_wait_event`, `host_delay_ms`, `host_message_box` and
  `host_poll_event` (src/web/host.js: `blocking`): a poll yields to the page when the game has run
  25 ms without one, through a message to itself (setTimeout's nesting clamp would add 4 ms each
  time); short sleeps likewise.
* **Speed** (this machine; Chrome 156 headless, replays on the virtual clock, so all of it is the
  game's code): `harness/scripts/newgame.txt` 0.8 s, `long50.txt` (50 turns) 2.4-2.8 s, against
  0.4 s and 1.4-1.8 s for build/OpenCiv2 (wasm2c, -O2), and 0.5 s / 2.0 s for the same module
  without asyncify.  The page loads the game's files from IndexedDB in about 1 s (88 MB) and shows
  its first picture about 1.8 s after loading.
* **Host** (src/web/host.js): the desktop on a `<canvas>` of its size in desktop pixels, shown at a
  whole number of device pixels each where it fits (`image-rendering: pixelated`), else shrunk; the
  desktop follows the window (`host_open_maximized_window`, `HOST_EV_RESIZE`), its scale chosen as
  natively (`host_desktop_scale`).  The game draws its own menu bar (as on Linux: no native menu, no
  `host_menu_*`).  Keys by `KeyboardEvent` (letters by `key`, the rest by `code`, the keypad by Num
  Lock as SDL does), the wheel's fractions added up as host_sdl.c does, cursors as CSS cursors
  (the game's images scaled to the desktop), sound effects as WebAudio buffers queued one after
  another, music decoded by the browser (`decodeAudioData`: Ogg Vorbis or WAV), message boxes as
  an in-page `<dialog>`.  The `host_net_*` imports: network play through a relay (below).
* **Network play** (src/web/net.js, tools/webrelay.py): the relay bridges WebSockets to TCP, one
  WebSocket per connection made (`/connect?host=&port=`: then the connection's bytes as binary
  messages, `{"connected": true}` once it is open, the WebSocket closed with 1000 when the peer
  closed, 4000-4999 when it failed or was refused) and one per listening port
  (`/listen?port=`: `{"listening"}`, `{"accept": ID, "ip"}` per connection, its bytes as
  `[ID u32][bytes]` both ways, `{"closed": ID}`; from the page `{"close": ID}`,
  `{"unlisten": true}`, so that the players stay when the game closes its listening socket);
  `/info` gives the address the others reach it at (the game's `host_net_local_addr`).  net.js
  gives the game host_net.c's non-blocking semantics: `connect` returns at once and
  `tcp_state` is 0 until the relay says connected (-1 if refused), `recv` -1 while nothing has
  come, 0 once the peer has closed (after what it sent), -2 when lost; `send` -1 while
  connecting.  The WebSockets' events arrive while the game gives the page its turns (its loop
  polls the sockets from `PeekMessage`, which yields every 25 ms).  UDP sockets open but carry
  nothing (no LAN game lists; Internet games by address).  Python 3 standard library only
  (asyncio; RFC 6455 framing written out); its defaults keep it from being an open proxy
  (README).
* **Files** (src/web/wasi.js): WASI preview 1 over a file system in memory: the player's files at
  `/civ2` (the game's folder, `argv[1]`), the fonts at `/data` (`CIV2_DATA`, fetched gzipped and
  inflated by the page), the platform's log to `/dev/null` (`?log`: to the console).
  src/web/store.js keeps the game's folder in IndexedDB: copied in once from the folder or `.zip`
  the player chooses (src/web/main.js; src/web/zip.js reads the archive with the browser's
  `DecompressionStream`), written back as soon as the game closes, renames or removes a file (saved games,
  `CIV.INI`, `CIV2.DAT`; a file still open a second after its last write), the storage asked to
  be persistent (`navigator.storage.persist`).
* **HD graphics** (src/web/hdpack.js, host.js's `host_present_hd`): the pack is checked
  (`crypto.subtle` SHA-256 of the release's `.zip` against data/hd-pack.json, copied to the site,
  then of `data/atlas-hd.pack`, inflated by `DecompressionStream` from the `.zip` read in parts,
  against its `package.json`; the pack alone against the pin's `pack_sha256`) and kept in
  IndexedDB's `hd` store in 4 MB chunks, `info` written last.  At start, where HD graphics are
  wanted (`?hd=N`, passed as `--hd=N`, else `CIV.INI`), the page builds from the chunks a pack
  of the pictures hd.c draws (`KEEP`: 65 MB, 17 of the 60 chunks read) at `/data/hd/atlas-hd.pack`,
  where hd.c finds it as the program's data; hd.c reads it on demand with `fseek`/`fread` as
  natively, its decoded pictures within its 160 MB budget in the module's memory (no maximum set
  at link time: wasm32's 4 GB).  The frame goes on the canvas at density times the desktop's size
  by `putImageData` (about 10 ms for 2560x1600, so not WebGL), not smoothed where the canvas is
  shown at whole device pixels.  GitHub's release downloads
  have no CORS headers, so the page cannot fetch them: the player chooses the downloaded `.zip`,
  or the site has the art (`make web HD=1`: `build/web/hd`).  The game's OpenCiv2 Options
  (src/game/options.cpp) are the same in the browser: its host tells it where the art is
  (`host_hd_fetch`: kept, on the site, or neither) and its restart loads the page again
  (`host_restart`, an import asyncify waits on, as the message box), the page then getting the art
  from the site where `CIV.INI` asks for HD graphics (src/web/main.js, options.js: `hdWanted`).
* **Set-up from the CD or a disc image** (src/web/setup_run.js, setup_worker.js,
  setup/setup_web.c): the native set-up's own code, src/host/setup.c and setup_disc.c with
  unshield, zlib, libogg and libvorbis (their sources from tools/fetch-toolchain.sh, as the native
  build has them), compiled by wasi-sdk's clang into a second module, `setup.wasm` (0.8 MB;
  `tools/build_web.py`; an 8 MB stack, placed first so that running out of it traps).
  setup_web.c is the system's part (setup_os.h) for it: plain files, no CD drive, no dialogs;
  `main` runs `setup_choose_game` with `--setup SOURCE`, GameData being `/game`.  It runs in a Web
  Worker over the WASI of src/web/wasi.js, the player's files under `/src` read where they are
  (`MemFS.putSource`: `FileReaderSync` on the `File`, through a 1 MB cache), so that a 700 MB
  disc image is never in memory whole; each file it writes into `/game` is handed to the page as
  soon as it is closed or renamed (the `.part` files and the cabinet's temporary copy are not) and
  dropped from the worker's memory, and the page keeps it in IndexedDB.  The page finds the CD (a
  folder with `DATA1.CAB` and `CIV2`) or the image (a `.cue`) among the files chosen
  (`findDisc`), where they are not an installed game; it shows the set-up's progress, has a Stop
  button (the worker is ended, the store emptied), and checks that the result is a game
  (`Civ2Art.dll`, `RULES.TXT`).  A CD's music tracks cannot be read by a browser: from a mounted
  CD the game comes without music. (src/web/saves.js): the player's files are the `.SAV` files,
  `CIV.INI`, `CIV2.DAT` and `HALLFAME.DAT` in the game's folder, and the `.SCN` and `.MP` files
  the copy of the game did not have or that changed since (the store's `meta` notes the copy's
  paths and time; a copy made before that was noted: written ten minutes or more after
  `Civ2Art.dll` was copied).  Exported as a `.zip` (src/web/zip.js writes it: each file deflated
  with `CompressionStream` where that makes it smaller), imported from `.SAV` files or `.zip`
  archives (only those kinds of files; folders in front of a path that the game's folder does not
  have dropped, the case of a file already there kept) into IndexedDB and, while the game runs,
  into its files in memory.  While playing, the *Saves* button over the screen's top right corner
  opens a dialog that keeps the keys from the game.
* **By hand**: sound and music (the headless browser has no audio device), the cursors, resizing the
  window and other browsers than Chrome are checked by playing (music, the videos and loading saved
  games: played and fine, 2026-11-14; exporting saves and the set-up from the real CD: fine,
  2026-11-14): `make web`, `python3 -m http.server
  -d build/web`, open `http://localhost:8000/?setup`.
* **Limits**: network games only through the relay, Internet games only.  Videos play as natively (the Indeo decoder is part of the
  module).  The set-up is tested automatically on a made-up CD (below) and was tried by hand on
  the real CD (2026-11-14); the cabinet code is libunshield's, as natively, and the made-up cabinet is also read by
  unshield's own command-line tool.
* **Tests**: `make web-test` runs `src/web/test/unit.mjs` (the host's logic under node: keys, the
  wheel, the desktop's scale, pixels, the WASI file system, `.zip` reading and writing, which of
  the files are the player's and where imported ones go, the HD art's checks, store and
  pruning, whether `CIV.INI` asks for HD graphics; no browser, no game files), `src/web/test/setup.mjs` (`setup.wasm` under node on a made-up CD,
  `src/web/test/disc.mjs`: an InstallShield 5 cabinet with stored and zlib-compressed files in two
  file groups, one of them "Sound Files", an ISO 9660 file system with it and `CIV2/KINGS`,
  `CIV2/VIDEO`, and a disc image of that, `.bin` and `.cue`, the data track followed by two audio
  tracks with their pregaps: the game unpacked byte for byte, the videos copied, the music encoded
  as Ogg Vorbis of the tracks' lengths, the temporary files gone; the same CD as a folder, its
  names in another case: no music; and files that are neither), then
  `src/web/test/net.mjs` (net.js under node with the relay: joining a TCP server, partial
  reads, the peer closing, refused ports, addresses and connections; hosting with two TCP
  clients, the listener closed while they stay), then
  `src/web/test/smoke.mjs` (node and Chrome's headless shell, pinned,
  from `tools/fetch-toolchain.sh browser`; Linux x86-64) first sets the game up from the made-up
  disc image through the page (its file input, the worker, IndexedDB; the music decoded by the
  browser: 3 s and 2 s), then zips the game folder, gives it to the page
  through its file input, then plays: the menu, a new game with the default choices, a save
  (Ctrl+S) kept in IndexedDB, the saves exported from the set-up page (a download, checked to hold
  only the player's files), the saved game removed and imported from that `.zip` (on the set-up
  page, then again while the game runs), and loaded again from the menu;
  screenshots in `run/web-smoke`; then `src/web/test/hd.mjs`: the art chosen on the set-up page
  (the release's `.zip` from `tools/fetch_hd_pack.py`'s cache, else `data/native/hd/atlas-hd.pack`;
  skipped without either), checked and kept, HD graphics and a rule written to `CIV.INI`, the game
  at a device pixel ratio of 2: the canvas twice the desktop, a saved game's map in HD (41% of its
  2x2 blocks not one colour, against none for enlarged pixels), then `?hd=0`: the original
  graphics; screenshots in `run/web-hd`.  `make web-replay SCRIPT=harness/scripts/NAME.txt` replays a
  scenario in the browser as the native suite does and compares it with the original's recording
  (newgame and long50: every screenshot, the `rand()` trace and the sounds identical).
* **Network games, browser and native** (`tools/xdnet/webnet.py native-web|web-native [--turns N]
  [--exe OpenCiv2]`; on the docker host, after `make web` and `make port`): tools/xdnet/nettest.py's
  steps and checks, one player being the browser version (src/web/test/player.mjs: Chrome's
  headless shell driven by xdotool's key names over stdin, its XDaemon and platform logs copied
  out as they grow; src/web/test/cdp.mjs is shared with the smoke test), the other our native
  build in a civ2-dev container, the relay on the docker host (its WebSocket side on 127.0.0.1,
  games hosted by the browser listened for on the bridge's gateway).  An Internet game: the host
  sets up a new game, the other joins by address, civilizations chosen, the world built, two
  turns each (a settler moved, a city founded), both quit; checked as nettest.py checks: the
  records well formed, what each sent the other received byte for byte, both reached the turns,
  the expected messages in order, no crash (run/xd/cap/web-PAIRING/result.txt).  Not in
  `make web-test` (it needs docker and a few minutes).


## Incremental WASM builds (CIV2-T006, 2026-11-21)

`tools/build_native.py --target wasm` now preserves each generated `build/native/gen` file's modification time when the generated bytes are identical. Its objects remain in `build/native/wasm` (or the target-specific output directory) across clean pinned-source checkouts; they are recompiled only when the source or relevant headers change or the recorded recipe changes. A build recipe stamp in the ignored object directory covers compiler file metadata, C++ mode, source tool SHA-256, compile and link flags. If there is no stale object and the previously linked WASM is newer than every object, the native linker is skipped. Any source recipe change invalidates the stamp and forces a safe one-time rebuild; a failed compile/link never writes a successful new stamp. `tests/incremental_wasm_test.py` is a no-toolchain, no-commercial-game regression for write-if-changed and link reuse.

The browser build already reuses the existing `build/web/civ2.wasm` optimized output and `setup.wasm` when their dependencies have not changed. These incremental artifacts are **ignored generated files** on the local D:-only Candidate/Trusted caches, not GitHub commits. Do not delete `build`, `tools/toolchain`, `run/lang-fonts`, or the verified public HD pack to force an ordinary rebuild. A changed compiler version or global header can legitimately trigger a full rebuild once. This is not a promise that all source changes can avoid compilation, and it does not change gameplay or commercial media requirements.


## Browser module packaging regression (CIV2-T006, 2026-11-21)

A real Chrome localhost screenshot exposed `GET /graphics_choice.js 404` and an indefinitely visible `Loading ...` panel. `src/web/main.js` already statically imported `./graphics_choice.js`, and source-tree Node unit tests passed, but `tools/build_web.py` copied only its historical `PAGE` list, which had omitted the new graphics chooser module. A failing import prevents the ES module entry point from executing, so this is a **static packaging defect**, not a failing game WASM compiler or corrupt player-owned CD.

`tools/build_web.py` now includes `graphics_choice.js` in `PAGE` and checks browser relative static imports, literal dynamic imports and Worker dependencies **before** invoking `tools/build_port.py module`. The pure Python checker `tools/check_web_modules.py` and source-only `tests/web_module_manifest_test.py` reproduce a missing chooser, a missing Worker, a dynamic import and a path escape without a WASM SDK or any original game content. The separate Web public-dist verification also checks shipped `.js` dependencies; tests run only in explicitly batched source CI or manual build preflight, not on every Draft commit.

Only the browser bundler/tests/docs change on this checkpoint; the game native source, compiler recipe and upstream build object directory stay unchanged. The first new browser build may rerun wasm-opt due to the updated `build_web.py` timestamp but should reuse previously compiled WASM objects. Keep the pinned D:-local WASI/WABT/Binaryen/fonts/HD atlas and all original local saves intact. An actual owner Chrome/Edge reload and Graphics/HD UI acceptance remain separate from source-test PASS.

**Generated exception:** `src/web/i18n.js` imports `./texts.js`, which is intentionally not in `PAGE` because `write_languages()` generates `build/web/texts.js` from `src/host/texts.h`. The source-manifest audit recognizes exactly that generated module; Web public-dist verification still rejects its absence from the actual served directory. Do not add a nonexistent `src/web/texts.js` or weaken checks for other missing dependencies.


## Quiet local BYO startup: optional resources (CIV2-T006, 2026-11-21)

The owner confirmed a **working** Chinese HD Civilization II map and original gameplay controls in Chrome after the missing `graphics_choice.js` packaging fix. The remaining DevTools Console reported three nonfatal requests: `GET /game/index.json 404`, `ws://127.0.0.1:8765/info` connection refused, and `GET /favicon.ico 404`. These were optional-resource startup probes, not a native WASM or map rendering failure.

For `GAME=0` (the static, bring-your-own Civ2 build), `src/web/index.html` now declares `<meta name="openciv2-bundled-game" content="0">`. `tools/build_web.py.mark_bundled_game()` retains this in the public build, or stamps `content="1"` **only** for `GAME=1` builds that actually publish a server-side game bundle. `src/web/main.js` calls `siteBundlesGame(document)` and only fetches `game/index.json` when the source is explicitly bundled. `GAME=1` automatic install/update is preserved; no browser IndexedDB, user-owned CD or saved games are modified.

The network relay's optional `/info` WebSocket is now initialized **lazily on actual TCP multiplayer listen/connect**, not at `makeNet()` construction during a single-player game. The existing listener and peer WebSocket protocol, connection-error dialogue and relay-address updates remain unchanged. Missing relay errors are still visible when a player explicitly attempts multiplayer without running one. The document has an inline `<link rel="icon" href="data:,">` to eliminate a browser-side `/favicon.ico` request without adding an image file.

`src/web/test/unit.mjs` tests both bundled-game flags and a no-WebSocket-until-network mock; `tests/browser_optional_resources_test.py` tests the actual build-time HTML stamp and rejects a missing/duplicate marker. The Web Candidate runs these media-free checks before full WASM compilation and in explicitly batched hosted source CI, and the BYO-only public verifier rejects a missing/true bundled-game marker. There is no change to the native game source, map/grid shader, WASM build recipe or 250MB HD atlas; existing D:-local toolchain/fonts/build objects can be reused. Final owner Chrome Console and multiplayer regressions remain to be observed.


### Owner Chrome acceptance and restrained HD grid polish (2026-11-21)

The owner verified that the three optional Console errors have **all disappeared** after the BYO startup cleanup: `game/index.json` 404, the unsolicited `ws://127.0.0.1:8765/info` connection failure, and `favicon.ico` 404. They also confirmed **no visual regression**. This closes only the single-player Console noise acceptance; an actual multiplayer relay test, original AVI sound, and save/load remain separate gates.

The owner otherwise approved the Chinese HD map appearance and requested only that *revealed ordinary tile borders* be more discreet. `src/platform/hd.c::hd_map_grid_contrast` now reduces the ordinary (non-city-radius) extra HD dark-edge blend from strength 166 to 104 and stroke 0.84 to 0.66 native pixels. The city's special radius cue retains its existing 184 strength / 0.84 stroke and original pale color; the grid option, native sprites, coordinates, fog, gameplay state, HD textures, canvas, audio and browser assets are unchanged. The source-only `tests/hd_grid_contrast_test.py` locks those constraints. This is a **native HD renderer** change: it will cause a legitimate incremental object rebuild/link (do not promise a zero-object rebuild). Actual Chrome visual acceptance of the new subtle grid is **pending**. Keep the D:-local WASI, fonts, HD atlas, native objects and private game files intact.


### Final thin-outline balance requested by owner (2026-11-21)

The owner refined the HD grid requirement: **ordinary revealed-region edges** may be slightly darker than the previous soft candidate, but must stay visually restrained and as thin as the unobtrusive grid elsewhere; **city-radius edges** must keep their current pale, high-contrast hue and blend, but lose their heavy width. In `src/platform/hd.c::hd_map_grid_contrast`, both cases now use the same `stroke = 0.56` (formerly ordinary 0.66 and city 0.84). The ordinary edge keeps its dark `0x0b1815` color and gets a modest blend increase from 104 to 118; the radius keeps its original `0xf2eee4` and 184 blend. No dotted-pattern experiment, extra sprite, gameplay logic, grid toggle, map visibility, city-radius geometry, UI layout, network/Console behavior, audio or storage changes. The exact source contract is covered by `tests/hd_grid_contrast_test.py`. This is a native HD renderer edit; a focused incremental compile/link is expected, with all D:-drive toolchain/fonts/art/other build products retained. **The owner has not yet visually accepted these revised parameters.**


### City-radius thin-line seam regression: repaint after neighbors (2026-11-21)

Owner's subsequent real Chrome screenshot of the thin-grid checkpoint shows **broken/mottled pale city-radius boundary segments at tile joins**; ordinary thin dark grid and overall HD picture otherwise look correct. A close inspection and the actual renderer source establish a concrete rendering-order risk: `MapView::draw_tile()` paints each tile's city-radius enhancement immediately after its terrain, so the next tile's terrain or ordinary dark grid can paint over half of the already-thin pale shared edge. Shrinking both stroke radii to 0.56 made these overpainted seams conspicuous. Simply making the white line thicker would hide, not fix, the compositing order issue.

Source fix is scoped to `src/auto/mapview.cpp` and `src/platform/hd.c`. The existing ordinary and city-radius sprites still render during the original `draw_tile` pass. **After all neighboring terrain tiles have completed**, `MapView::draw_all_tiles` performs a bounded **radius-only HD overlay postpass**; `MapView::draw_tile_radius` repeats the equivalent pass for incremental/redraw regions. The shared `hd_radius_tile_for_postpass()` predicate preserves the original `OPT_MAP_GRID`, map bounds, visibility, city owner and `map_distance_diag < 3` conditions. The renderer gives only radius tiles one native pixel of AA sampling room beyond the tile's old rectangular clip bounds (still clipped to the bitmap); ordinary dark grid stays on its former tight bounds. City pale hue `0xf2eee4`, blend 184 and thin stroke 0.56 **remain unchanged**; ordinary grid `0x0b1815`, blend 118 and stroke 0.56 remain unchanged. No input, gameplay state, save content, HD atlas, network requests or original AVI logic change.

`tests/hd_grid_contrast_test.py` now checks full **and** partial redraw postpass placement, redraw eligibility and clip boundaries, so a future thin-grid adjustment cannot restore the same seam vulnerability. This is a native source revision; rerun the owner's D:-local incremental WASM build and inspect the same city screenshot to confirm continuity. Source-order verification alone does not prove the live pixels are fixed. Neither PR should be merged and Issues #23/#38 remain open until owner acceptance.


**Double-blend prevention:** The final `draw_tile()` enhancement now applies only to non-radius dark ordinary edges. Radius tiles still draw the game's original pale grid sprite, but their custom thin HD pale overlay is painted **exactly once** in the final full/partial postpass. This avoids over-brightening the city-radius contrast while fixing late-neighbor occlusion. The extra 1px sample allowance applies only to the pale radius, not the regular grid. Source test asserts the early radius enhancement is absent.
