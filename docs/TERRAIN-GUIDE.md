# H021 Terrain Guide

The compact browser toolbar adds a Terrain guide/地形指南 help dialog. It reads classic TERRAIN1/TERRAIN2 from the user's already-imported game in IndexedDB and HD PNG art from the locally cached/pruned atlas-hd.pack, only after click. No original game art is copied to this public repo, no 250MB download is performed, and no saves, rules, engine or art are modified.

Three tabs compare: 11 terrain types and coastline example; 22 special resources (A/B for each terrain); Plains/Grassland in unimproved, first I irrigation, second I farmland states. Crop keys: base TERRAIN1 x=1,y=1+33*n; special A x=131 and B x=196 at same y (n=0..10); irrigation (456,100), farmland (456,133); size 64x32. HD keys use crop/file/terrain1/x,y,64,32. The cards are representative image composites and not exact neighbor-aware game screenshots.

The owner's source report is in the civ2-web repo: docs/guide/CIV2-TERRAIN-REFERENCE.md (branch feature/CIV2-H021-terrain-guide). Fixed HD pack release v2026.11.08.1 SHA256 9e1ec3b46b32f9926cac43e314ca0cd6a0115195bf474e8986a402323c42d007. Irrigation classic/HD visible coverage: 15.99%/91.88%; farmland 77.11%/94.45%. HD Grassland A/B PNGs are identical despite differing original art; neither observation changes gameplay yields. H021 remains a Draft Owner acceptance candidate.
