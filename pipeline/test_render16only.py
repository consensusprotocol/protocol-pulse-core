#!/usr/bin/env python3
"""Ruling 93 as amended (orchestrator 2026-11-14 '21:10'): "the integrator renders and delivers that format alone".
A run whose EDL seals formats ['16x9'] RENDERS, GATES and VERIFIES the 16:9 alone: no 9:16 shoutout, render,
postflight, loudness mux, gate, sheet or row. Every renderer and gate is stubbed at its seam (no GPU, no network);
the stubs record which final each one was given. Must-fail: the same run with no sealed formats renders and gates
both (today's behaviour), and finals that do not match the sealed formats are a Hold.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_render16only.py"""
import contextlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import run_fresh as rf  # noqa: E402

ABSENT = object()
SEG = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 1.0},
       {"label": "shoutout", "type": "shoutout", "start": 1.0, "end": 2.0}]


def run_dir(parent, formats=ABSENT):
    rd = tempfile.mkdtemp(prefix="r16_", dir=parent)
    for sub in ("out", "qa", "VERIFY"):
        os.makedirs(os.path.join(rd, sub))
    edl = {"topic": "t", "hook": {"channel": "Blockware Solutions", "selection_lock": {"text": "I sold my stocks."}},
           "clips": []}
    if formats is not ABSENT:
        edl["formats"] = formats
    for name, obj in (("edl.json", edl), ("VERTICAL_LAYOUT.json", {}), ("CLIP_CONTRACT.json", [{"clip_id": "hook"}]),
                      ("cuts_final.json", [{"clip_id": "hook", "video_id": "AAAAAAAAAAA", "cut_in": 0.0,
                                            "cut_out": 1.0}])):
        json.dump(obj, open(os.path.join(rd, name), "w"))
    return rd


def finals(rd, fmts):
    """The renders' outputs as the stubs (and a real render) leave them: each format's final and manifest."""
    out = {}
    for fmt, name in (("16x9", "segment.mp4"), ("9x16", "segment_vertical.mp4")):
        if fmt in fmts:
            open(os.path.join(rd, "out", name), "wb").write(fmt.encode())
            json.dump({"segments": SEG}, open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
            out[fmt] = (os.path.join(rd, "out", name), os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"))
        else:
            out[fmt] = (None, None)
    return out


def run_obj(rd):
    run = rf.Run(rd)
    run.machine_cuts = False
    return run


class TestRenderStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="r16t_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def render(self, rd):
        import loudness
        import render16
        import render_vertical
        import run_isolated
        import shoutout
        calls = []

        def r16(d, qa, name, alimiter_dbfs=None):
            finals(d, ("16x9",))
            calls.append("render_16x9")

        def r9(d, qa, name, alimiter_dbfs=None):
            finals(d, ("9x16",))
            open(os.path.join(d, "qa", "vert_hook.mp4"), "wb").write(b"v")     # the reframed clip it leaves
            calls.append("render_9x16")
        with contextlib.ExitStack() as st:
            for obj, attr, fn in (
                    (shoutout, "build_shoutout", lambda d, q, fmt="16x9": calls.append(f"shoutout {fmt}")),
                    (render16, "render_16x9", r16), (render_vertical, "render_9x16", r9),
                    (run_isolated, "preflight_check", lambda d: None),
                    (run_isolated, "postflight_check", lambda p, t, a, log_output="": calls.append(f"postflight {a}")),
                    (loudness, "correct_finals", lambda f16, f9=None: calls.append(
                        f"loudness {os.path.basename(f16)} {f9 and os.path.basename(f9)}") or {"action": "stub"}),
                    (rf, "write_transitions", lambda run, style: None),
                    (rf, "media_summary", lambda p: {"width": 1080, "height": 1920})):
                st.enter_context(mock.patch.object(obj, attr, fn))
            run = run_obj(rd)
            return rf.stage_render(run), calls, run

    def test_a_16x9_only_run_renders_the_16x9_alone(self):
        rd = run_dir(self.tmp, ["16x9"])
        (f16, m16, f9, m9), calls, run = self.render(rd)
        self.assertEqual((os.path.basename(f16), f9, m9), ("segment.mp4", None, None))
        self.assertEqual(calls, ["shoutout 16x9", "render_16x9", "postflight 16x9", "loudness segment.mp4 None"])
        self.assertFalse(os.path.exists(os.path.join(rd, "out", "segment_vertical.mp4")))
        fb = run.prov["vertical_fallback_check"]
        self.assertEqual((fb["formats"], fb["checked"], fb["fallback_occurred"]), (["16x9"], [], False))
        self.assertNotIn("outro_conform_fallback_9x16", fb)

    def test_must_fail_no_sealed_formats_renders_both(self):
        rd = run_dir(self.tmp)
        (f16, m16, f9, m9), calls, run = self.render(rd)
        self.assertEqual(os.path.basename(f9), "segment_vertical.mp4")
        self.assertEqual(calls, ["shoutout 16x9", "shoutout 9x16", "render_16x9", "postflight 16x9", "render_9x16",
                                 "postflight 9x16", "loudness segment.mp4 segment_vertical.mp4"])
        self.assertEqual(run.prov["vertical_fallback_check"]["checked"], ["hook"])

    def test_unreadable_formats_hold_before_anything_renders(self):
        rd = run_dir(self.tmp, ["9x16"])
        with self.assertRaisesRegex(rf.Hold, "release formats unreadable"):
            self.render(rd)
        self.assertEqual(os.listdir(os.path.join(rd, "out")), [])


class TestGateStage(unittest.TestCase):
    """stage_gates with every gate stubbed: each stub records the final it measured."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="r16g_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def gates(self, rd, f16, m16, f9, m9):
        import config
        import credit_rings
        import edge_shots
        import gates as G
        import qa_gates
        import sentence_law as L
        import vertical_layout as V
        import word_diff as WD
        seen = []
        outro = os.path.join(self.tmp, "outro.mp4")
        open(outro, "wb").write(b"outro")

        def rec(name, ret):
            def f(*a, **k):
                seen.append((name, next((os.path.basename(x) for x in list(a) + list(k.values())
                                         if isinstance(x, str) and x.endswith(".mp4")), None)))
                return ret
            return f
        res = {"G3b_cut_out_clean": {"pass": True, "table": []}, "G3c_acoustic_tail": {"pass": True, "table": []},
               "G5_tech": {"pass": True, "data": [1]}, "G8_sharpness": {"pass": True, "table": [1]},
               "G9_tail": {"pass": True, "data": {"x": 1}}}
        with contextlib.ExitStack() as st:
            for obj, attr, fn in (
                    (rf, "free_gpu0_for_whisper", lambda run, stage, **k: None),
                    (G, "run_gates", rec("run_gates", (True, res))),
                    (G, "g14_run_speech", lambda d, cuts: {"hook": []}),
                    (G, "gate_g14", rec("G14", (True, [{"status": "PASS"}]))),
                    (G, "gate_g14c", rec("G14c", (True, [1]))),
                    (G, "gate_g15", rec("G15", (True, [1]))),
                    (G, "gate_g20", rec("G20", (True, [1]))),
                    (qa_gates, "gate_g11", rec("G11", (True, [1]))),
                    (qa_gates, "gate_g8", rec("G8", (True, [{"segment": "hook", "ratio": 1.0}]))),
                    (qa_gates, "gate_g4", rec("G4", (True, [1]))),
                    (credit_rings, "credit_channels", lambda edl: ["Blockware Solutions"]),
                    (config, "conform_outro", lambda fmt: outro),
                    (config, "OUTRO_MASTER_16x9", outro), (config, "OUTRO_MASTER_9x16", outro),
                    (V, "per_shot_manifest", lambda sgs, plans: []),
                    (V, "gate_g4s", lambda plans, prepared, vert_final=None, vert_segments=None:
                     seen.append(("G4s", vert_final and os.path.basename(vert_final))) or (True, [1])),
                    (L, "gate_g16", lambda d: (True, [1])),
                    (L, "gate_g17_prepared", lambda clips: (True, [1])),
                    (L, "gate_g17_output", rec("G17", (True, [1]))),
                    (L, "gate_g17_edges", lambda d: (True, [1])),
                    (WD, "Transcriber", lambda: object()),
                    (WD, "gate_g18", rec("G18", (True, [1]))),
                    (edge_shots, "gate_g19", rec("G19", (True, [1])))):
                st.enter_context(mock.patch.object(obj, attr, fn))
            run = run_obj(rd)
            run.prov["vertical_fallback_check"] = {"outro_conform_fallback_16x9": False,
                                                   "outro_conform_fallback_9x16": False,
                                                   "fallback_occurred": False, "checked": ["hook"]}
            rows, _, _ = rf.stage_gates(run, f16, m16, f9, m9)
            return rows, seen, json.load(open(os.path.join(rd, "GATE_REPORT.json")))

    def test_a_16x9_only_run_gates_the_16x9_alone(self):
        rd = run_dir(self.tmp, ["16x9"])
        f = finals(rd, ("16x9",))
        rows, seen, rep = self.gates(rd, *f["16x9"], *f["9x16"])
        self.assertEqual(list(rows), ["16x9"])
        self.assertEqual(list(rep["rows"]), ["16x9"])
        self.assertEqual(rep["formats"], ["16x9"])
        self.assertEqual(set(rep["measured_files"]), {"out/segment.mp4", "qa/concat_manifest_16x9.json"})
        self.assertNotIn("segment_vertical.mp4", {x for _, x in seen})
        self.assertFalse({"G11", "G14c"} & {n for n, _ in seen}, seen)
        self.assertEqual({n for n, x in seen if x == "segment.mp4"},
                         {"run_gates", "G14", "G15", "G20", "G8", "G4", "G17", "G18", "G19"})
        for k in ("G16_sentence_boundary", "G17_onset_tail", "G18_word_for_word", "G19_edge_shots", "G15_credits",
                  "G20_signoff_names_all", "G14_av_alignment", "G4s_layout_truth"):
            self.assertIn(k, rows["16x9"])

    def test_must_fail_no_sealed_formats_gates_both(self):
        rd = run_dir(self.tmp)
        f = finals(rd, ("16x9", "9x16"))
        rows, seen, rep = self.gates(rd, *f["16x9"], *f["9x16"])
        self.assertEqual(list(rows), ["16x9", "9x16"])
        self.assertTrue({"G11", "G14c"} <= {n for n, _ in seen}, seen)
        self.assertIn("vertical_silent_fallback", rows["9x16"])
        self.assertEqual({n for n, x in seen if x == "segment_vertical.mp4"},
                         {"run_gates", "G11", "G14", "G15", "G20", "G4", "G4s", "G17", "G18", "G19"})

    def test_finals_that_do_not_match_the_sealed_formats_hold(self):
        rd = run_dir(self.tmp, ["16x9"])                    # sealed 16:9 alone, a 9:16 handed in
        f = finals(rd, ("16x9", "9x16"))
        with self.assertRaisesRegex(rf.Hold, "do not match the run's formats"):
            self.gates(rd, *f["16x9"], *f["9x16"])
        rd = run_dir(self.tmp)                              # both sealed, no 9:16 rendered
        f = finals(rd, ("16x9",))
        with self.assertRaisesRegex(rf.Hold, "do not match the run's formats"):
            self.gates(rd, *f["16x9"], *f["9x16"])


class TestVerifyPack(unittest.TestCase):
    """verify_pack.build (vision off: V1 SKIPPED) covers the run's formats alone; its 'complete' needs only them."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="r16v_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def build(self, rd, fmts):
        import verify_pack as VP
        import visual_check as VC
        finals(rd, fmts)
        rep = {"G18": {f: [{"segment": "hook"}] for f in fmts},
               "rows": {f: {"G12_credits": "PASS"} for f in fmts}, **{f"G15_{f}": [1] for f in fmts}}
        json.dump(rep, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
        asked = []

        def frame(final, t, out):
            asked.append(os.path.basename(final))
            open(out, "wb").write(b"jpg")
            return out

        def sheet(items, out, tile):
            open(out, "wb").write(b"jpg")
            return out

        def contact(final, segs, fmt, out, work):
            asked.append(os.path.basename(final))
            open(out, "wb").write(b"jpg")
            return {"path": out}
        with mock.patch.object(VP, "_frame", frame), mock.patch.object(VP, "_sheet", sheet), \
                mock.patch.object(VC, "contact_sheet", contact):
            return VP.build(rd, vision=False), asked

    def test_a_16x9_only_pack_is_complete_on_the_16x9_alone(self):
        rd = run_dir(self.tmp, ["16x9"])
        pack, asked = self.build(rd, ("16x9",))
        self.assertTrue(pack["complete"], pack)
        self.assertEqual(pack["formats"], ["16x9"])
        self.assertEqual(set(asked), {"segment.mp4"})
        self.assertEqual(list(pack["joins"]), ["16x9"])
        rep = json.load(open(os.path.join(rd, "GATE_REPORT.json")))
        self.assertEqual(list(rep["rows"]), ["16x9"])                    # V1 written for the 16:9 alone

    def test_must_fail_no_sealed_formats_needs_the_9x16_too(self):
        rd = run_dir(self.tmp)
        with self.assertRaises((FileNotFoundError, OSError)):          # no 9:16 manifest: the pack cannot be built
            self.build(rd, ("16x9",))
        rd = run_dir(self.tmp)
        pack, asked = self.build(rd, ("16x9", "9x16"))
        self.assertEqual(set(asked), {"segment.mp4", "segment_vertical.mp4"})
        self.assertTrue(pack["complete"], pack)


if __name__ == "__main__":
    unittest.main()
