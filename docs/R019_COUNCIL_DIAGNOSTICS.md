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

## 2026-11-23 Owner first-click timing evidence and correction candidate

Owner reproduced with the SAME Council save/movie and `councilTrace=1`:

| | First Military click | Second Military click |
|---|---:|---:|
| `click-play-issued` | 1013867 ms | 1035397 ms |
| `audio-ended` | 1013872 ms | 1042469 ms |
| Elapsed | **5 ms** | **7072 ms** |
| End video frame | 320 | 424 |
| Expected range | 318–423 | 318–423 |
| IV41 seek decode | ~5 ms | ~4 ms |

AVI open took only ~10/27 ms and keyframe preroll on the relevant click
only 4–5 ms. This is **NOT consistent with the 29 MiB AVI reloading or
slow initial codec decode as the immediate failure**. Instead the first
wave/audio playback was incorrectly signaled complete after 5 ms.

A concrete, Web-only cause is present in `src/web/host.js`: `resumeAudio()`
invokes asynchronous `AudioContext.resume()` after a user gesture, but
`host_audio_queue()` previously returned without scheduling PCM unless
`audio.state === 'running'`; `host_audio_queued()` also reported **0**
while `audio.state === 'suspended'`. That made the waveOut implementation
mistake unplayed buffers for consumed ones; it could clear the audio-playing
status and trigger `CouncilWindow::council_on_video_end` immediately.

**Fix candidate:** accept `running` or `suspended` contexts for PCM
scheduling; WebAudio allows `AudioBufferSourceNode.start()` while suspended,
and the frozen `currentTime` retains pending PCM until `resume()` completes.
The queued-byte computation now reports unplayed audio for suspended contexts,
and only excludes `closed`/missing contexts. Browser Node tests cover 7s
mono + 44.1kHz stereo, frozen suspended clock, running depletion and closed
state. In trace mode `webaudio-queued-suspended` identifies this condition
without reading audio/video bytes. No AVI codec, asset files, native SDL
playback, save data or independent Effects/Music gain changed.

This is a **source-backed root-cause candidate**; the trace alone did not
record the first `AudioContext.state`, so the diagnosis is not yet a
confirmed exclusive causal explanation. Owner must build exact-head Web
candidate on D: and verify FIRST click, second click, and auto-response
animation with same save after a fresh reload, ideally across 3 repetitions.
Compare Council's `audio-ended` delay against expected ~7s and look for
`webaudio-queued-suspended`. A missing frame after this fix requires
additional wave-buffer status tracing, not arbitrary audio-end delays.
