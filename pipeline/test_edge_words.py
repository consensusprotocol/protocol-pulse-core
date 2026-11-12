#!/usr/bin/env python3
"""Law L-b (PBX, orchestrator 2026-11-11 15:30 / 15:35): a fade never overlaps an edge word; the first and the
last word of every clip are heard whole, at full level, with their natural decay (G17c: within 1 dB of the
unfaded source). The fade shortens down to 10 ms to stay in the gap.
must-fail  the approved preview's Natalie Brunell tail: "...Bitcoin really hasn't participated in the Monday
           rally." - the 83 ms fade ending at 80.84 started inside the decay of 'rally'
must-pass  the same cut prepared with the L-b fades; every v2f edge (its own 20 / 30 ms fades) except two
           legacy edges recorded since DEC-10 (clip_01 OUT, clip_03 IN), which must keep failing
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_edge_words.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import sentence_law as L  # noqa: E402

PREVIEW = os.path.join(REPO, "references", "pulse_preview_2026-11-11")
V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")


def _natalie():
    edl = json.load(open(os.path.join(PREVIEW, "edl.json")))
    seg = next(c for c in edl["clips"] if c["channel"] == "Natalie Brunell")
    words = json.load(open(os.path.join(PREVIEW, "transcripts", f"{seg['video_id']}.json")))["words"]
    cut = next(c for c in json.load(open(os.path.join(PREVIEW, "cuts_final.json"))) if c["video_id"] == seg["video_id"])
    return seg, words, cut


@unittest.skipUnless(os.path.isdir(PREVIEW), "protected preview reference not on this machine")
class TestNatalieTail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seg, cls.words, cls.cut = _natalie()
        cls.src = os.path.join(PREVIEW, "sources", f"{cls.seg['video_id']}.mp4")
        cls.sa = L.SourceAudio(cls.src)
        lock = cls.seg["selection_lock"]
        cls.plan = L.edge_plan(cls.sa, cls.words, lock["i0"], lock["i1"])

    def test_the_sentence_is_the_one_pbx_named(self):
        tail = " ".join(w["word"] for w in self.words[self.seg["selection_lock"]["i1"] - 5:
                                                      self.seg["selection_lock"]["i1"] + 1])
        self.assertTrue(tail.endswith("participated in the Monday rally."), tail)

    def test_the_preview_clip_cuts_into_rally(self):
        ok, det = L.edge_word_fidelity(self.src, os.path.join(PREVIEW, "qa", "final_clip_01.mp4"), self.plan,
                                       self.cut["cut_in"], self.cut["cut_out"], sa=self.sa)
        self.assertFalse(det["out"]["ok"], det)
        self.assertEqual(self.cut["fade_out_ms"], 83)                   # the delivered fade

    def test_the_l_b_fade_stays_out_of_rally_and_keeps_it_whole(self):
        fi, fo, wb = L.edge_fades(self.sa, self.plan, self.cut["cut_in"], self.cut["cut_out"])
        self.assertLessEqual(self.cut["cut_out"] - fo, self.cut["cut_out"])
        self.assertGreaterEqual(round(self.cut["cut_out"] - fo, 3), round(wb["end"], 3) - 1e-9)   # fade after the word
        from run_isolated import prerender_clips
        tmp = tempfile.mkdtemp(prefix="lb_")
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "sources"))
        os.makedirs(os.path.join(tmp, "qa"))
        os.symlink(self.src, os.path.join(tmp, "sources", os.path.basename(self.src)))
        c = {**self.cut, "fade_in_ms": int(round(fi * 1000)), "fade_out_ms": int(round(fo * 1000))}
        prerender_clips(tmp, [c])
        ok, det = L.edge_word_fidelity(self.src, os.path.join(tmp, "qa", f"final_{c['clip_id']}.mp4"), self.plan,
                                       c["cut_in"], c["cut_out"], sa=self.sa)
        self.assertTrue(ok, det)


@unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
class TestV2fEdgesWhole(unittest.TestCase):
    """Every v2f edge word is at full level except two legacy edges recorded since DEC-10, which G17c rightly
    fails and must keep failing: clip_01 OUT (PBX's documented one-time exception: cut 20 ms after
    'magnitude.', the 30 ms fade reaches its decay: 2.63 dB) and clip_03 IN (v2f's clip_03 starts mid-sentence
    on 'a', pre-law: the 20 ms fade-in falls on the word: 1.93 dB)."""
    RECORDED = {("clip_01", "out"), ("clip_03", "in")}

    def test_every_v2f_edge_word_is_at_full_level(self):
        cuts = json.load(open(os.path.join(V2F, "cuts_final.json")))
        cuts = cuts if isinstance(cuts, list) else cuts["cuts"]
        bad = []
        for c in cuts:
            words = json.load(open(os.path.join(V2F, "transcripts", f"{c['video_id']}.json")))["words"]
            src = os.path.join(V2F, "sources", f"{c['video_id']}.mp4")
            sa = L.SourceAudio(src)
            mid = lambda w: (w["start"] + w["end"]) / 2
            i0 = next(i for i, w in enumerate(words) if mid(w) > c["cut_in"])
            i1 = max(i for i, w in enumerate(words) if mid(w) < c["cut_out"])
            plan = L.edge_plan(sa, words, i0, i1)
            ok, det = L.edge_word_fidelity(src, os.path.join(V2F, "qa", f"final_{c['clip_id']}.mp4"), plan,
                                           c["cut_in"], c["cut_out"], float(c.get("lead_in_pad_s") or 0), sa=sa)
            self.assertEqual(set(det), {"in", "out"}, (c["clip_id"], det))
            for side, v in det.items():
                if (c["clip_id"], side) in self.RECORDED:
                    self.assertFalse(v["ok"], (c["clip_id"], side, v))       # the legacy edge keeps failing
                elif not v["ok"]:
                    bad.append((c["clip_id"], side, v))
        self.assertEqual(bad, [])



def _f32_wav(path, x, sr=16000):
    """A 32-bit float WAV (levels far below the 16-bit floor stay representable)."""
    import subprocess
    import numpy as np
    raw = path + ".f32"
    np.asarray(x, np.float32).tofile(raw)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw, "-c:a",
                    "pcm_f32le", path], check=True)
    os.remove(raw)
    return path


class TestRuling16Floor(unittest.TestCase):
    """Ruling 16 (orchestrator 2026-11-12 '10:20'): G17c compares a frame only if the SOURCE frame is above
    max(the local gap level, -96 dBFS), the 16-bit quantisation floor below which no audio exists to clip; the
    1.0 dB bar is unchanged. Synthetic edge (gap level -177 dB like the Nov 12 clip_01 head): 0.2 s at -120 dBFS,
    then a 0.6 s word at -50 dBFS. must-fail: the word's onset 3 dB down. must-pass: differences only below -96."""

    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.tmp = tempfile.mkdtemp(prefix="r16_")
        rng = np.random.default_rng(16)
        sr, rms = 16000, lambda db: 10 ** (db / 20)
        quiet = rng.standard_normal(int(0.2 * sr)) * rms(-120)
        word = rng.standard_normal(int(0.6 * sr)) * rms(-50)
        tail = np.zeros(int(0.2 * sr))
        cls.src = _f32_wav(os.path.join(cls.tmp, "src.wav"), np.concatenate([quiet, word, tail]))
        other_quiet = rng.standard_normal(int(0.2 * sr)) * rms(-140)          # differs by ~20 dB, all below -96
        cls.below = _f32_wav(os.path.join(cls.tmp, "below.wav"), np.concatenate([other_quiet, word, tail]))
        lost = word.copy()
        lost[:int(0.3 * sr)] *= rms(-3)                                         # a real 3 dB onset loss
        cls.lost = _f32_wav(os.path.join(cls.tmp, "lost.wav"), np.concatenate([quiet, lost, tail]))
        cls.bounds = {"onset": 0.15, "end": 0.75, "lim_in": -177.0, "lim_out": -177.0}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _in(self, clip, floor=None):
        from unittest import mock
        with mock.patch.object(L, "edge_word_bounds", return_value=dict(self.bounds)), \
                mock.patch.object(L, "EDGE_WORD_FLOOR_DBFS", L.EDGE_WORD_FLOOR_DBFS if floor is None else floor):
            ok, det = L.edge_word_fidelity(self.src, clip, None, 0.0, 1.0)
        return det["in"]

    def test_differences_only_below_the_16_bit_floor_pass(self):
        self.assertEqual(L.EDGE_WORD_FLOOR_DBFS, -90.0)                       # ruling 19: AAC codec noise, measured
        self.assertEqual(L.EDGE_WORD_MAX_DB, 1.0)                                # the bar is unchanged
        self.assertTrue(self._in(self.below)["ok"], self._in(self.below))
        self.assertFalse(self._in(self.below, floor=-999.0)["ok"])              # without the floor: compared, fails

    def test_codec_noise_between_minus_96_and_minus_90_dbfs_passes(self):           # ruling 19
        import numpy as np
        rng = np.random.default_rng(19)
        x = np.concatenate([rng.standard_normal(3200) * 10 ** (-93 / 20), rng.standard_normal(9600) * 10 ** (-50 / 20),
                            np.zeros(3200)])
        y = x.copy()
        y[:3200] *= 10 ** (-1.3 / 20)                                           # 1.3 dB off at -93 dBFS, like AAC
        src = _f32_wav(os.path.join(self.tmp, "src93.wav"), x)
        clip = _f32_wav(os.path.join(self.tmp, "clip93.wav"), y)
        from unittest import mock
        with mock.patch.object(L, "edge_word_bounds", return_value=dict(self.bounds)):
            ok, det = L.edge_word_fidelity(src, clip, None, 0.0, 1.0)
        self.assertTrue(det["in"]["ok"], det)
        with mock.patch.object(L, "edge_word_bounds", return_value=dict(self.bounds)), \
                mock.patch.object(L, "EDGE_WORD_FLOOR_DBFS", -96.0):
            ok, det = L.edge_word_fidelity(src, clip, None, 0.0, 1.0)
        self.assertFalse(det["in"]["ok"], det)                                  # at the old -96 floor it failed

    def test_a_real_3_db_onset_loss_at_minus_50_dbfs_fails(self):
        d = self._in(self.lost)
        self.assertFalse(d["ok"], d)
        self.assertGreater(d["worst_db"], 2.5, d)


NOV12 = os.path.join(REPO, "runs", "pinned_20261112_135315")


@unittest.skipUnless(os.path.isdir(os.path.join(NOV12, "sources")), "the Nov 12 moments run not on this machine")
class TestRuling16Nov12(unittest.TestCase):
    def test_clip_01_in_compares_the_audible_frames_and_passes(self):
        ok, table = L.gate_g17_edges(NOV12)
        self.assertTrue(table["clip_01"]["in"]["ok"], table["clip_01"])
        self.assertLess(table["clip_01"]["in"]["worst_db"], L.EDGE_WORD_MAX_DB, table["clip_01"])   # measured 0.34
        self.assertTrue(ok, table)


if __name__ == "__main__":
    unittest.main()
