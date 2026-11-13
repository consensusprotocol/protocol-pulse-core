#!/usr/bin/env python3
"""Ruling 28 (orchestrator 2026-11-13 '01:55'): the hook's lead decided at the cut by G17a's own measure.
real fixtures  pin #1's hook (Sjb6lUiL0m4: digital zeros of a hard edit up to ~40 ms before the first word; a gated
               source whose room tone dips to digital silence) is REFUSED before any render, with the measured reason,
               and its clips keep their cuts; the medley reference's hook (260 ms of lead) keeps its planned cut
logic          a planned cut with >= 80 ms stands; else the first legal, neighbour-clear candidate with >= 80 ms; else
               the D1 pad only where the padded head measures >= 80 ms; else refused"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import sentence_law as L  # noqa: E402

PIN1 = os.path.join(REPO, "runs", "pinned_20261113_054035")
MEDLEY = os.path.join(REPO, "references", "pulse_medley_2026-11-12")


def scratch(run):
    d = tempfile.mkdtemp(prefix="hook_lead_")
    shutil.copy(os.path.join(run, "edl.json"), d)
    for sub in ("sources", "transcripts"):
        os.symlink(os.path.join(run, sub), os.path.join(d, sub))
    return d


class TestHookLeadReal(unittest.TestCase):
    @unittest.skipUnless(os.path.isdir(os.path.join(PIN1, "sources")), "pin #1's run is not on this machine")
    def test_pin1s_hook_is_refused_before_any_render_and_its_clips_keep_their_cuts(self):
        d = scratch(PIN1)
        self.addCleanup(shutil.rmtree, d)
        old = {c["clip_id"]: c for c in json.load(open(os.path.join(PIN1, "cuts_final.json")))}
        new = {c["clip_id"]: c for c in L.write_lock_cut_table(d)}
        h = new["hook"]
        self.assertFalse(h["verified"])
        self.assertIn("hook lead (ruling 28): no legal cut in the pause keeps 80 ms", h["error"])
        self.assertIn("the D1 room-tone pad does not give it either: G17a measures 20 ms at 14.810", h["error"])
        for k in ("clip_01", "clip_02"):
            self.assertEqual((new[k]["cut_in"], new[k]["cut_out"]), (old[k]["cut_in"], old[k]["cut_out"]))

    @unittest.skipUnless(os.path.isdir(os.path.join(MEDLEY, "sources")), "the medley reference's media are not here")
    def test_the_medley_hook_keeps_its_planned_cut(self):
        d = scratch(MEDLEY)
        self.addCleanup(shutil.rmtree, d)
        old = {c["clip_id"]: c for c in json.load(open(os.path.join(MEDLEY, "cuts_final.json")))}
        h = {c["clip_id"]: c for c in L.write_lock_cut_table(d)}["hook"]
        self.assertEqual((h["cut_in"], h["lead_in_pad_s"]), (old["hook"]["cut_in"], 0.0))
        self.assertEqual(h["hook_lead"]["how"], "the planned cut keeps the hook's lead")
        self.assertGreaterEqual(h["hook_lead"]["lead_ms"], 80)


class TestHookLeadLogic(unittest.TestCase):
    PICK = {"cut_in": 1.0, "cut_out": 9.0, "fade_in_ms": 20}

    def run_with(self, leads, padded=None, clear=lambda c: True, candidates=(1.0, 0.98, 1.02)):
        def at(src, c, fade_ms=0):
            return leads[c]
        with mock.patch.object(L, "SourceAudio", lambda p: None), \
                mock.patch.object(L, "hook_lead_at", at), \
                mock.patch.object(L, "cut_candidates", lambda src, plan: {"in": list(candidates)}), \
                mock.patch.object(L, "edge_fades", lambda sa, plan, a, b: (0.02, 0.03, None)), \
                mock.patch.object(L, "neighbour_clear", lambda sa, plan, a, b, fi, fo: (clear(a), {})), \
                mock.patch.object(L, "padded_lead_ms", lambda src, c, co, fade_ms=0: (padded or {}).get(c)):
            return L.hook_lead("src.mp4", {}, dict(self.PICK))

    def test_a_planned_cut_with_80_ms_stands(self):
        r = self.run_with({1.0: (120, 0.12)})
        self.assertEqual((r["cut_in"], r["pad_s"]), (1.0, 0.0))

    def test_a_legal_neighbour_clear_candidate_with_80_ms_is_taken(self):
        r = self.run_with({1.0: (30, 0.2), 0.98: (95, 0.22), 1.02: (100, 0.18)}, clear=lambda c: c != 0.98)
        self.assertEqual((r["cut_in"], r["pad_s"], r["how"]), (1.02, 0.0, "moved inside the pause to keep 80 ms"))

    def test_the_pad_only_where_the_padded_head_measures_80_ms(self):
        leads = {1.0: (30, 0.2), 0.98: (20, 0.02), 1.02: (25, 0.03)}                # 0.98 and 1.02 genuine to the word
        r = self.run_with(leads, padded={0.98: 40, 1.02: 270})
        self.assertEqual((r["cut_in"], r["pad_s"], r["lead_ms"]), (1.02, L.LEAD_PAD_S, 270))

    def test_a_pad_whose_room_tone_cannot_be_built_is_skipped(self):        # batch 56 C1 (glm): padded None
        leads = {1.0: (30, 0.2), 0.98: (20, 0.02), 1.02: (25, 0.03)}
        r = self.run_with(leads, padded={0.98: None, 1.02: 270})
        self.assertEqual((r["cut_in"], r["pad_s"]), (1.02, L.LEAD_PAD_S))

    def test_otherwise_the_hook_is_refused(self):
        leads = {1.0: (30, 0.2), 0.98: (0, 0.0), 1.02: (20, 0.2)}                   # a cut ON sound never joins
        r = self.run_with(leads, padded={0.98: 300})
        self.assertIn("refused", r)
        self.assertNotIn("cut_in", r)


if __name__ == "__main__":
    unittest.main()
