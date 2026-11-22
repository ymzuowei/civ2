/* CIV2-T006 HD map grid postpass: privately scoped to mapview.cpp / hd.c.
   Keep this separate from hd.h so the one-map-renderer optimization does
   not force a full native object rebuild on the persistent D: cache. */
#ifndef OPENCIV2_HD_GRID_BATCH_H
#define OPENCIV2_HD_GRID_BATCH_H
#ifdef __cplusplus
extern "C" {
#endif
/* Native surface clip [left,right) x [top,bottom); begin returns 0 on OOM
   or unavailable HD, leaving the game's original grid sprites untouched. */
int hd_grid_batch_begin(void *bits, int left, int top, int right, int bottom);
/* hd_map_grid_contrast() adds per-pixel coverage during the batch; end
   blends once from the finished terrain and releases the temporary mask. */
void hd_grid_batch_end(void *bits);
#ifdef __cplusplus
}
#endif
#endif
