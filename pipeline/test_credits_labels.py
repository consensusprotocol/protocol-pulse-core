#!/usr/bin/env python3
"""Credits labels never touch (orchestrator list 2026-11-12, order '20:30' (d)): on the 16:9 credits card of the review
video 'Saifedean Ammous' ran into 'What Bitcoin Did' (drawn ink overlap 7 px). scene_shoutout.fit_label_sizes keeps
neighbouring labels at least LABEL_MIN_GAP (12 px, the tightest gap PBX approved: the v2f card) apart and every
label LABEL_MARGIN inside the frame; a card below that is resized, names and handles together, for LABEL_FIT_GAP (40 px).
Must-fail: the delivered card at the old size overlaps, a card that would need labels under 60 % is refused. Must-pass:
the delivered card fits after the shrink; the protected references (v2f, the Nov 11 preview) keep 46 / 32 px exactly."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "segment_v1"))
import scene_shoutout as S  # noqa: E402
from PIL import ImageFont  # noqa: E402

BOLD, REG = S._find_font(S.FONT_BOLD_PATHS), S._find_font(S.FONT_REG_PATHS)


def row_xs(n, w=1920, avatar=260, spacing=200):
    """render_shoutout's 16:9 node centres (scale 1.0)."""
    start_x = (w - (n * avatar + (n - 1) * spacing)) // 2 + avatar // 2
    return [start_x + i * (avatar + spacing) for i in range(n)]


def gaps(names, xs, size):
    f = ImageFont.truetype(BOLD, size)
    ex = [S._ink(f, t, x) for t, x in zip(names, xs)]
    return [b[0] - a[1] for a, b in zip(ex, ex[1:])], ex


@unittest.skipUnless(BOLD and REG, "the credits fonts are not on this machine")
class TestCreditsLabels(unittest.TestCase):
    MOMENTS = (["Saifedean Ammous", "What Bitcoin Did", "Natalie Brunell"], ["@saifedean", "@WBDPodcast", "@nataliebrunell"])

    def test_the_delivered_card_overlapped_and_now_fits(self):
        names, handles = self.MOMENTS
        xs = row_xs(3)
        g, _ = gaps(names, xs, 46)
        self.assertLess(g[0], 0, g)                                   # must-fail: as delivered, the labels overlap
        ns, hs = S.fit_label_sizes(names, handles, xs, 1920, 46, 32, BOLD, REG)
        self.assertLess(ns, 46)
        self.assertGreaterEqual(ns, 28)
        g, ex = gaps(names, xs, ns)
        self.assertTrue(all(x >= S.LABEL_FIT_GAP for x in g), (ns, g))   # a changed card gets a clear gap
        self.assertTrue(ex[0][0] >= S.LABEL_MARGIN and ex[-1][1] <= 1920 - S.LABEL_MARGIN, ex)
        self.assertEqual(hs, round(32 * ns / 46))

    def test_the_protected_references_keep_their_sizes(self):
        """Law 22 / L-d: v2f's tightest pair is exactly the minimum gap; neither card changes."""
        for names, handles in ((["The Bitcoin Layer", "Bitcoin Magazine", "BTC Sessions"], ["", "@BitcoinMagazine", "@BTCSessions"]),
                               (["DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"],
                                ["@DataDash", "@nataliebrunell", "@YahooFinance", "@BitcoinMagazine"])):
            self.assertEqual(S.fit_label_sizes(names, handles, row_xs(len(names)), 1920, 46, 32, BOLD, REG), (46, 32), names)
        g, _ = gaps(["The Bitcoin Layer", "Bitcoin Magazine", "BTC Sessions"], row_xs(3), 46)
        self.assertEqual(min(g), S.LABEL_MIN_GAP)

    def test_a_gap_one_pixel_under_the_minimum_shrinks(self):
        names, handles = ["The Bitcoin Layer", "Bitcoin Magazine", "BTC Sessions"], ["", "", ""]
        xs = row_xs(3)
        xs = [xs[0] + 1] + xs[1:]                                     # the v2f pair 1 px closer: 11 px
        self.assertEqual(min(gaps(names, xs, 46)[0]), S.LABEL_MIN_GAP - 1)
        ns, _ = S.fit_label_sizes(names, handles, xs, 1920, 46, 32, BOLD, REG)
        self.assertLess(ns, 46)
        self.assertGreaterEqual(min(gaps(names, xs, ns)[0]), S.LABEL_FIT_GAP)

    def test_a_label_leaving_the_frame_shrinks_in_both_formats(self):
        wide = "W" * 24                                                # about 1.1x the 9:16 width at 46 px
        ns, _ = S.fit_label_sizes([wide], [""], [540], 1080, 46, 32, BOLD, REG, row=False)      # 9:16 stack
        _, ex = gaps([wide], [540], ns)
        self.assertLess(ns, 46)
        self.assertTrue(ex[0][0] >= S.LABEL_MARGIN and ex[0][1] <= 1080 - S.LABEL_MARGIN, ex)
        self.assertEqual(S.fit_label_sizes(self.MOMENTS[0], self.MOMENTS[1], [540] * 3, 1080, 46, 32, BOLD, REG,
                                           row=False), (46, 32))      # the 9:16 card was never affected

    def test_a_card_that_needs_labels_under_60_percent_is_refused(self):
        names = ["MARA Holdings (Marathon Digital)", "Marty Bent (Rabbit Hole Recap)", "The Investors Podcast Network",
                 "Strategy (MicroStrategy)"]
        with self.assertRaisesRegex(RuntimeError, "do not fit without touching"):
            S.fit_label_sizes(names, [""] * 4, row_xs(4), 1920, 46, 32, BOLD, REG)

    def test_handles_are_checked_too(self):
        names = ["A", "B", "C"]
        handles = ["@" + "h" * 30, "@" + "h" * 30, "@c"]
        ns, hs = S.fit_label_sizes(names, handles, row_xs(3), 1920, 46, 32, BOLD, REG)
        f = ImageFont.truetype(REG, hs)
        ex = [S._ink(f, t, x) for t, x in zip(handles, row_xs(3))]
        self.assertLess(hs, 32)
        self.assertGreaterEqual(ex[1][0] - ex[0][1], S.LABEL_FIT_GAP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
