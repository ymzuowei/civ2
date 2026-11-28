# CIV2-R019 — Prove whether Council missing auto-reply animations are Web/WASM-specific

**Status: instrumented source candidate ONLY. No proven gameplay fix or codec migration.**
Related [civ2-web #72](https://github.com/ymzuowei/civ2-web/issues/72). The branch is
stacked on T018 native Draft #19 (not merged). Preserve all user SAV files and
both old frozen kits until separately approved final T017/T018 release.

## Already established by native source

- The original Council script has a Military City-Walls speech followed by
  conditional Trade rebuttals. An **automatic** second adviser is by design.
- `CouncilWindow::init` opens **one** `COUNCILn.AVI` for an entire era;
  each adviser speech uses a separate frame range inside that same file.
  Owner's installed `COUNCIL0.AVI` is ~28.94 MiB, loaded locally in the
  browser; it is not re-downloaded at each handoff.
- `council_on_video_end` deliberately moves the video window to the second
  adviser, appends subtitles, seeks to the next frame, shows the video,
  and starts `play_range`. Missing visible movement is therefore NOT a
  script instruction and should be diagnosed.
- The IV41 decoder and keyframe seeking run synchronously in WASM.
  The browser's WebAudio `AudioContext.currentTime` clock keeps moving
  independently while a WASM invocation or canvas compositing is busy.
  SDL native uses `SDL_GetQueuedAudioSize` for the PCM queue instead of
  the browser's `d.end - audio.currentTime` approximation. This is a
  plausible, Web-specific opportunity for audio/video desynchronization,
  **not proven causality without synchronized recordings/trace**.

## New opt-in trace, zero game-media content

For an Owner-owned game installation, build this R019 pinned candidate using
the same D:-isolated Windows workflow. Keep the existing 127.0.0.1:8000
origin, browser profile, and installed assets. In the URL append
`&councilTrace=1` (or `?councilTrace=1` if no other query).
Open DevTools Console with **Preserve log**, optionally filter
`council-trace`. Load a known Council-capable SAV, click Military *once*,
then wait for automatic Trade rebuttal. Do not repeatedly click or adjust
music sliders during the reproducible clip. Record a 10–20 sec screen video
if useful. Do **not** upload AVI, BIN or CUE; metadata-only console lines
and a short visual symptom description suffice.

`council-trace` events:
- `click`, `click-seek-start/complete`, `click-play-issued`
- `video-end`, `auto-seek-start/complete`, `auto-play-issued`
- `avi-open` (full-file read/RIFF parse in ms), `avi-seek`
  (target keyframe distance, preroll frames and synchronous decode ms),
  `audio-ended` (current/start/end video frames)
- `webaudio-queue-gap` (WebAudio clock advanced beyond the queue by >50 ms)
  and `wasm-block` (one WASM segment blocked the JS main thread for >=50 ms,
  at most 40 such messages).

**Important:** visible `auto-play-issued` is not guaranteed that a frame was
actually painted; it proves only the native Council script called play.
If `audio-ended` fires promptly for the Trade clip before any visible frame,
inspect `avi-seek` duration, WebAudio scheduling gaps and `wasm-block`
entries. If normal playback occurs on a no-HD run but not HD, suspect
HD CPU compositor. If both native SDL and Web show the same failure with
identical media, classify as a shared engine/original-port issue, not
Web-only. If only Web shows it and traces correlate with frame/decode
latency or audio queue gap, the Web hypothesis gains support.

## Benchmark decision & release constraints

Compare at least 3 repeated Council visits under Chrome HD ON and HD OFF,
then optional native SDL with the same installed legally owned media.
Collect median/p95 Click->First frame, auto Speech->First painted frame,
seek decode and audio-end lag. Distinguish *loading once* from *seeking on
every speech*. Audio/visual content, User IDs or local game file paths must
not enter CI logs or public issues. No media is transferred to CI or repo.

This is **diagnostic only**; even a native source test PASS does not prove
the missing animation is a WASM-only load-efficiency bug. Do not convert,
overwrite, or redistribute AVI media before measured results.

### Source CI gate update

First R019 pinned-source run [45040571175](https://github.com/ymzuowei/civ2-web/actions/runs/45040571175) failed before gameplay due a T017 browser unit test hardcoding the previous `!introDiagnose && !new URLSearchParams` logging condition. The new opt-in `councilTrace` parameter must be checked alongside `introDiagnose`. The browser unit now explicitly asserts both default-no-log and opt-in Council trace routing, without changing runtime playback. New exact-head source CI and Owner WASM build remain PENDING.


## B012 integration correction — retain the R019 first-click audio fix

The B012 native candidate originally advanced its upstream.lock to a native commit on a side branch that did not contain the R019 suspended-WebAudio correction. This meant a Web build could carry councilTrace=1 instrumentation while still compiling the old audioOk() === running behavior; the webaudio-queued-suspended trace would be absent. This is the missing integration that explains why the Owner could still reproduce a 5ms first-click audio completion on the B012 preview.

The B012 native branch now ports the R019 fix onto its current >2 GiB/WASM32-safe code instead of replacing the newer host file with the older R019 snapshot:
- audioContextCanSchedule() accepts running and suspended contexts.
- host_audio_queue schedules PCM during asynchronous resume and emits metadata-only webaudio-queued-suspended when councilTrace=1.
- host_audio_queued retains the pending queue while the suspended AudioContext clock is frozen.
- The B012 wasm32Bytes(memory, data, ...) PCM read remains intact; no reversion to direct signed pointer construction.
- Node tests cover suspended/running/closed states, frozen clock and queue depletion. Python source regression asserts both the suspended-queue policy and preservation of the WASM32-safe data path.

This is now a combined B012 + R019 integration candidate, not evidence of Owner runtime acceptance. Rebuild the exact updated native pin and verify at least three fresh-load first-click Military clips, second click, and the scripted automatic Trade reply. Expect a roughly full-clip audio lifetime (not 5ms); with trace enabled, confirm whether webaudio-queued-suspended appears when the initial gesture resumes the context. If it does not appear, that only means the context was already running at PCM queue time; it is not itself a failure. Keep all PRs Draft and do not merge/freeze until runtime verification.

## 2026-11-23 — First-clip regression expands across multiple Council advisors

Owner retested the combined B012/R019 pin `aeebb769d444c451319764c5cd39c93cfb8ea6bc`. The first Military click still ended in 4ms (1014028 to 1014032; end frame 320 vs range 318–423), while the second completed in about 7063ms (1046065 to 1053128; frame 424). Trade also failed on first click (1073919 to 1073925 = 6ms; end 2066 vs range 2064–2204) and completed after about 9298ms on second click (1084291 to 1093589; end frame 2204). AVI open 10ms, AVI seek 2–6ms. This disproves a suspended-AudioContext-only explanation; the previous candidate did not resolve first playback and must not be marked PASS.

**Source-confirmed arithmetic bug and deterministic numeric reproduction:** in `src/platform/sound.c::played_bytes`, the code previously computed `uint64_t queued_total - host_audio_queued(dev)` without checking for a negative result. The browser's `queuedAudioBytes` used `Math.ceil((d.end - currentTime) * freq)`; for a 22050Hz/4096-frame first buffer starting at 0.048s, IEEE-754 arithmetic can produce `4096.000000000001` and `ceil=4097`. Subtracting `4097` from submitted `4096` wraps to `2^64 - 1`. Then `sound_poll` immediately marks **all** queued waveOut headers as played, which may clear AVI's `flags & 4` and trigger `audio-ended`/video-end before animation advances. This bug is independent of whether the context is `running` or `suspended`. Actual Owner trace did not capture the queued byte values, so this is a high-confidence, falsifiable root-cause candidate rather than a proven sole explanation.

**Narrow fix candidate:** saturate `played_bytes()` at zero when remaining >= submitted before unsigned subtraction, log at most 12 metadata-only `wave-queue-overhang` entries under opt-in `CIV2_LOG_COUNCIL`; trim sub-sample floating error only in JS with `Math.ceil(left * freq - 1e-7)`; preserve prior suspended-PCM support and the signed-WASM32-safe PCM memory bridge. Node regression executes the actual fractional-clock 4096→4097 reproducer and expects 4096 corrected; native Python source regression guards the C saturating calculation. No AVI editing, game asset changes, buffer-duration hacks, random sleeps or UI mutations. Verify fresh first clicks for Military, Trade, Science and auto response, then second click per advisor; inspect exact duration/frame and ensure no errors. Do not merge/freeze until browser Owner acceptance and long-game memory stability.


## T025 Council0 browser shadow (2026-11-28)

The WebCodecs candidate is shadow-only. Native `avi_decode_frame` calls `plat_council_shadow_frame` only after a successful legacy Indeo frame, with `decode_flags == 0`, non-transparent source, and explicit `CIV2_T025_COUNCIL_SHADOW` gate. `AVIFileOpenA` scopes the host identity check to basename `COUNCIL0.AVI`; the host hashes the exact bytes. The original DIB, original AVI decode and audio queue remain authoritative. No alpha/opacity or visual replacement claim.

The browser callback is deliberately non-blocking: a single in-flight WebCodecs task processes the latest requested native frame; at most one queued frame is retained and superseded requests are counted as dropped. Width/height must match the original frame. The host reads one decoded frame to a bounded Canvas RGBA buffer, discards it after proof, and never copies it into WASM or changes the game DIB. No frame timer or audio decoder is introduced.

Memory ownership: one shared selected MP4 payload (no duplicate bridge copy); at most one pending latest-frame request; range provider caps each GOP at 16 decoded frames and 16 MiB estimated RGBA, packet data at 4 MiB, and decode timeout at 5 s. Every `VideoFrame` is closed, range close clears frame maps, compressed payload references and metadata, bridge close clears prepared RGBA and zeroes canvas dimensions, Native AVI release closes the host bridge, and `runGame` finally disposes the trial. `window.civ2Stats.councilShadow` reports scheduling/dropped/decoded counters and active/pending/prepared/clip/canvas ownership. Real browser memory/CPU and full game UAT remain required.


### T025 actual Council0 shadow receipt / stale range hint

Owner actual HD game screenshot: four opens/four closes, 245 scheduled, 60 coalesced, 185 decoded, 3 failures, active/pumping/queued zero, bridge null, shared clip 19521163 bytes. Council2 existing save correctly did not trigger the Council0-only experiment. Actual WASM/Host integration proven, clean owner counters observed, overall UAT not accepted because of failures and no long-run physical memory proof. Source review confirms play_range seeks before assigning its new end and show_frame has no new end assignment. Native decoder can also decode a visible frame beyond the prior end before callback. Previously schedule rejected any such stale end and C then disabled shadow for the AVI. Exact cause of all three failures cannot be confirmed from aggregate counters. For valid frame/geometry, normalize invalid end hint to a single verified frame, count staleEndHints separately, preserve bounds and original callbacks. lastFailure is one allowlisted scalar, no retained history/media. No C/ABI change, new media or WASM build required for this JS-only correction. Add deterministic source tests. Actual verification pending.


### T025 visible exact-frame composition candidate

R2 actual HD shadow accepted: 9 opens/9 closes, 732 scheduled, 564 decoded, 167 coalesced, 28 stale end hints, zero failures and inactive settled owner. One unclassified request, long-run memory unproven. New opt-in councilShadow=1&councilRender=1 (loopback only) prefetches one next frame and transfers only an exact matching opaque RGBA slot synchronously into bounded codec scratch. No async wait on frame path, no stale image. Native requires actual decoded original frame, no mask or transparency, no test key, and valid geometry; shared Classic palette/dither and HD smooth plane composition use modern RGB on hit, legacy otherwise. No change to original audio/end/cue or preroll, and Indeo still runs on every frame for opacity/state/fallback. This is visual parity candidate, not performance improvement. New ABI needs actual compile; source tests are not gameplay proof. Explicit close frees JS slot and decoder; codec free releases scratch. No original media prepared, no stable change. R2 overlay and media cleanup unconfirmed.


### T025 era extension / compositor work reduction

One selected Council0/1/2 pair per game session via councilEra=0/1/2, exact source hash, manifest scope and native basename; other eras and anarchy remain legacy. No extra retained clip or decoder. On exact modern opaque hit, both smooth HD source and indexed/truecolor DIB compositor branch directly to the modern RGB instead of calculating and then discarding legacy YUV conversion. Original Indeo still updates its state for every compressed frame, including hidden preroll; skipping compressed-frame decode needs a separate reference-state recovery proof (old AVI index key flags did not prove safe recovery). No claim of measured speedup, no unsafe decoder bypass. Source tests cover era binding, mismatched manifest and legacy fallback. HQ change travels with this feature batch, no dedicated media/CI run. Actual Classic and modern-era UAT and long-run memory remain pending.


### T025 state-preserving output elision experiment

Explicit loopback visible trial plus councilStateOnly=1. For a ready exact modern opaque frame and original packet with valid IV41 little-endian non-droppable P header, keep legacy picture header, buffer switch, all band decode, reference validity and dimensions. Only then, if no source transparency, no B/delayed P and exact geometry, skip legacy AVFrame allocation/output-plane copy or Haar recomposition; return distinct 2 to draw modern RGBA. If condition fails, normal legacy output; if decoder reports no picture preserve original behavior. No compressed reference frame skipped, no seek replay added. Scope reset each call, no new cache, codec close logs aggregate elided/full/no_picture (host renderHits counts successful takes, not guaranteed displayed when decode returns no picture). Source contract only; real compiled parity, output elision counts, CPU/memory measurement pending. HQ validation included in next functional UAT, not standalone. Default off.


### Combined local media pack

Owner requests one import and one gameplay UAT, not independent opening/Council pickers. Explicit mediaPack=1 with both existing opt-in flags selects one bounded binary .civ2media package (magic CIV2M01, LE header length, two embedded independent manifests, opening MP4 then selected Council MP4). Read slices, never entire package; existing SHA/source/scope/geometry/frame checks remain. Opening uses verified Blob with Play gesture, no second file picker/cache, releases the prepared reference on use or game exit. Council retains only selected era. Cancel uses originals. Original independent test routes remain for diagnostics, no ABI changes or stable default change.


### T025 all-era lazy pack V2

Owner accepted combined modern-era 7/7 and visible state elision (493/580 modern takes, elided=14 on one codec close, no errors, 2/2 opens/closes). Add schema2 CIV2M02 pack with opening plus all three Council manifests/payloads in fixed order. Browser reads prefix/header/opening only on import; retain local File handle and bounded manifest directory. Auto mode allows exact three Council basenames, selects clip by SHA256 of opened original AVI and size, verifies derived hash/config/timeline before decoding, releases active compressed clip on close, never overlaps pending reads/pump; stale completion rejected by epoch. Unknown source or busy owner uses legacy; no anarchy or masked assets enabled. No network/persistence, no new ABI; C basename gate requires actual WASM build. V1 remains compatible. Actual cross-era/long-run memory, open latency and performance pending.


### T025 throne-room transition scope

Source inspection corrects earlier AVI assumption: ThroneRoomWindow::run_upgrade uses GIF/HD still layers and three gfx_dissolve_blit transitions (640x480, 8/8/4 pixel cells), not video. Per-tile win_flush_pending_msgs in both cell setup and draw (4800/4800/19200 cells) can cause excessive message/present work; actual hotspot not yet profiled. Explicit localhost throneBatch=1, only these three calls, groups message pumps by at most 16 iterations plus phase/final boundaries, retains every tile blit and rand_range order, replay and ordinary dissolve path unchanged. Event timing may differ; measure input responsiveness, animation duration and visual progression before enabling. Aggregate mode/cell/steps/polls/elapsed log. HD choice map scratch now local 640x480 allocation/free and histogram local, no static retained owner. No video transcode, no stable changes; actual combined all-era+throne WASM build and UAT pending.


### T025 approved Wonder scope

WonderMovieWindow::play in city_view.cpp owns caption/frame, palette, fade, input and modal loop; wonder_show_movie preserves wave stop, CD music sync, localized Pedia. Extend the existing exact-frame compositor/legacy audio adapter to explicitly allowlisted WONDER00-27 in local V3 pack, not a full-screen HTML player replacement. Selected source digest and size and verified AVC manifest; additional packet-header opacity proof required. One native AVI bridge owner; nested AVI stays legacy, unrelated close cannot close current owner. Original mask checks and reference decode retained, no new host ABI, no default behavior change. V3 optional per-clip directory, bounded slice reads, V1/V2 retained. Real conversion/runtime/parity/latency/memory pending. ANARCHY/LAUNCH/WINWIN still separate scope review, heralds untouched.


Extended V3 scope review: ANARCHY0-2 uses same Council AVI/end-callback path (advisor buttons disabled), LAUNCH in spaceship.cpp retains modal input/end callback and music sync, WINWIN in reports.cpp retains movie-frame surface and caption/frame callback 0x2ab. Add exact names to existing frame bridge only, same verified source and conservative opacity gate. No replacement of native modal loops, callbacks, audio or captions; no new ABI. Actual supported files, cue/frame timing and visual parity pending. LOSER not in owner disc inventory; no scope expansion. HRLD remains excluded.
