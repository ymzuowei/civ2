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
