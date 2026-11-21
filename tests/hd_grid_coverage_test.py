"""CIV2-T006: pixel-coverage union invariants for shared HD tile edges.

Source-only, media-free. The helper's C compositing contract is also asserted
by hd_grid_contrast_test.py; these fixtures exercise order, duplicates,
intersection priority, native clip and reentrant-reset semantics.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HD = (ROOT / "src/platform/hd.c").read_text(encoding="utf-8")


def choose(existing: int, alpha: int, pale: bool) -> int:
    """Reference for the actual 9-bit C mask decision.

    Bit 8 encodes white city-range priority. The low byte is the largest
    alpha for that colour. The output is one composite sample, not a series
    of source-over blends.
    """
    assert 0 <= alpha <= 255
    if not alpha:
        return existing
    sample = alpha | (0x100 if pale else 0)
    old_pale = bool(existing & 0x100)
    if (pale and not old_pale) or (
        old_pale == pale and alpha > (existing & 255)
    ):
        return sample
    return existing


def coverage(samples):
    value = 0
    for alpha, pale in samples:
        value = choose(value, alpha, pale)
    return value


class SharedGridCoverageTests(unittest.TestCase):
    def test_shared_edge_is_idempotent_and_order_independent(self):
        samples = [(40, False), (28, False), (40, False), (6, False)]
        self.assertEqual(coverage(samples), 40)
        self.assertEqual(coverage(reversed(samples)), 40)
        self.assertEqual(coverage([(40, False)] * 7), 40)

        whites = [(131, True), (104, True), (131, True)]
        self.assertEqual(coverage(whites), 0x100 | 131)
        self.assertEqual(coverage(reversed(whites)), 0x100 | 131)

    def test_city_white_wins_even_at_dark_to_pale_intersection(self):
        samples = [(40, False), (18, True), (30, False), (8, True)]
        expected = 0x100 | 18
        self.assertEqual(coverage(samples), expected)
        self.assertEqual(coverage(reversed(samples)), expected)
        self.assertEqual(coverage([(18, True)] + samples), expected)

    def test_coverage_value_is_not_cumulative_opacity(self):
        # Old per-tile source-over wrongly brightens a shared edge:
        # 164/255 once versus alpha=~222/255 after two draws.
        single = 164
        twice = 255 - ((255 - single) * (255 - single) // 255)
        self.assertGreater(twice, single)
        self.assertEqual(coverage([(single, True)] * 2), 0x100 | single)

    def test_partial_redraw_clips_before_union(self):
        # If native tile bounds extend beyond the dirty rectangle, their
        # physical pixels must not modify a prior completed map region.
        dirty = (4, 3, 9, 8)  # [l,r) and [t,b), native pixels
        strokes = [(5, 5, 40, False), (5, 5, 164, True),
                   (9, 5, 164, True), (4, 8, 40, False),
                   (8, 7, 104, True), (1, 1, 164, True)]
        mask = {}
        for x, y, alpha, pale in strokes:
            if dirty[0] <= x < dirty[2] and dirty[1] <= y < dirty[3]:
                mask[(x, y)] = choose(mask.get((x, y), 0), alpha, pale)
        self.assertEqual(mask, {(5, 5): 0x100 | 164,
                                (8, 7): 0x100 | 104})
        self.assertNotIn((9, 5), mask)
        self.assertNotIn((4, 8), mask)

    def test_source_uses_one_plane_blend_and_releases_mask(self):
        begin = HD.split("int hd_grid_batch_begin(", 1)[1].split(
            "void hd_grid_batch_end(", 1)[0]
        finish = HD.split("void hd_grid_batch_end(", 1)[1].split(
            "void hd_map_grid_contrast(", 1)[0]
        collect = HD.split("void hd_map_grid_contrast(", 1)[1].split(
            "void hd_dc_chevron(", 1)[0]
        self.assertIn("calloc(pw * ph, sizeof *mask)", begin)
        self.assertIn("clip_rect(b, &left, &top, &right, &bottom)", begin)
        self.assertIn("if (!g->pixels)", finish)
        self.assertEqual(finish.count("sync_rect("), 1)
        self.assertEqual(finish.count("commit_rect("), 1)
        self.assertIn("free(g->pixels)", finish)
        self.assertIn("memset(g, 0, sizeof *g)", finish)
        self.assertIn("a > (old_sample & 255u)", collect)
        self.assertIn("radius_tile && !(old_sample & 0x100u)", collect)
        self.assertNotIn("commit_rect(", collect)
        self.assertNotIn("*dst =", collect)


if __name__ == "__main__":
    unittest.main()
