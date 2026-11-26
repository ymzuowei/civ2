# CIV2-H022 — HD field terrain identity (Web issue #77)

Candidate based on Native 09810c2bac80d0087ddbe47fb67ee8f38bca1fe4 (B020 opt-in diagnostics, no state change).
Owner's prior real-asset comparison showed HD irrigation/farmland cover 91.88%/94.45% of the terrain diamond at alpha >=128, versus Classic 15.99%/77.11%. Same improvement over Plains and Grassland masks the different base art.

Trial: use existing HD sprite art and blend irrigation at 166/255 (~65%) and farmland at 191/255 (~75%) only when the underlying terrain is Plains or Grassland. Existing three field draw sites, including city-neighbor field path, retain order. Normal 255 paint for all other sprites, classic and other terrain types unchanged. Scale premultiplied alpha AND RGB; do not alter the source atlas, allocate/cache new variants, or modify game flags, yield, rules, saves, audio, grid or asset pack. No additional redraw. These are initial visual tuning values, not established optimal contrast.

Static contracts and reference blend math are not proof of runtime readability. Compare both terrain types at the same improvement, zoom and lighting, including adjacent cities, roads, shields, rivers and classic graphics. Check scrolling and combat responsiveness, no visual regression in other terrain or field states. Existing guide shows original source asset composites, not the adjusted runtime blend. Owner acceptance pending. No Native main merge or public deploy.
