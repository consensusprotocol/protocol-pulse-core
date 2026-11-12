#!/usr/bin/env python3
"""Orchestrator note 06:20 ET: a timestamped contact sheet of the FINISHED video for every run and both formats,
and a fixed visual checklist answered FROM the sheet (unattended: a Heimdall vision panel; any "no" or missing
answer = HOLD). Must-fail: yesterday's vertical sheet (squashed thumbnail 'avatars', letterboxed talking heads).
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_visual_check.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
SHEET_NOV10 = os.path.join(REPO, "tests", "fixtures", "pulse_20261110", "video", "contact_sheet_9x16.jpg")

import visual_check as V  # noqa: E402


def _all(answer, **override):
    a = {k: {"answer": answer, "why": "w"} for k, _ in V.CHECKLIST}
    for k, v in override.items():
        a[k] = {"answer": v, "why": "w"}
    return a


class TestVerdict(unittest.TestCase):
    def test_all_yes_passes(self):
        self.assertTrue(V.verdict(_all("yes"), "9x16")[0])

    def test_any_no_holds(self):
        for k, _ in V.CHECKLIST:
            ok, rows = V.verdict(_all("yes", **{k: "no"}), "9x16")
            self.assertFalse(ok, k)
            self.assertFalse(rows[k]["ok"])

    def test_a_missing_answer_holds(self):
        a = _all("yes")
        del a["watermark_present"]
        ok, rows = V.verdict(a, "16x9")
        self.assertFalse(ok)
        self.assertEqual(rows["watermark_present"]["answer"], "missing")

    def test_na_only_where_the_question_allows_it(self):
        n16 = _all("yes", vertical_speaker_centred="n/a", no_letterbox_on_talking_heads="n/a")
        self.assertTrue(V.verdict(n16, "16x9")[0])                     # vertical-only lines on a 16:9 sheet
        self.assertFalse(V.verdict(n16, "9x16")[0])                    # never on the 9:16 sheet
        self.assertFalse(V.verdict(_all("yes", watermark_present="n/a"), "16x9")[0])

    def test_a_malformed_line_is_missing_not_a_crash(self):
        a = _all("yes")
        a["watermark_present"] = "yes"                                 # flat string instead of an object
        ok, rows = V.verdict(a, "16x9")
        self.assertFalse(ok)
        self.assertEqual(rows["watermark_present"]["answer"], "missing")

    def test_route_errors_are_retried_then_no_answer(self):
        from unittest import mock
        import urllib.error
        with mock.patch.object(V, "_key", return_value="k"), \
                mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")) as op:
            answers, raw = V.ask_vision(SHEET_NOV10, "9x16", model="m")
        self.assertEqual((answers, op.call_count), ({}, 2))
        self.assertIn("URLError", raw["unparseable"][0]["error"])
        self.assertFalse(V.verdict(answers, "9x16")[0])

    def test_unparseable_reply_is_no_answer(self):
        self.assertIsNone(V._parse("I think it looks fine"))
        self.assertIsNone(V._parse('{"answers": {"a": "yes",}'))
        self.assertEqual(V._parse('ok {"answers": {"x": {"answer": "yes"}}} done'), {"x": {"answer": "yes"}})
        self.assertEqual(V._parse('{"answers": {"x": {"answer": "no"}}}\nnote: {braces} after'),   # audit UI1
                         {"x": {"answer": "no"}})
        self.assertIsNone(V._parse('{"verdict": "yes"}'))                 # JSON, but no answers = no answer


class TestContactSheet(unittest.TestCase):
    """A synthetic 9:16 final: hook 0-4 s, clip_01 3.75-8 s (dissolve), shoutout 8-10 s."""

    def test_sheet_has_every_still_and_the_full_resolution_panels(self):
        from PIL import Image
        tmp = tempfile.mkdtemp(prefix="sheet_")
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "run", "out"))
        final = os.path.join(tmp, "run", "out", "segment_vertical.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=24:d=10",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", final], check=True)
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0},
                {"label": "clip_01", "type": "talking_head", "start": 3.75, "end": 8.0},
                {"label": "shoutout", "type": "shoutout", "start": 8.0, "end": 10.0}]
        out = os.path.join(tmp, "sheet.jpg")
        r = V.contact_sheet(final, segs, "9x16", out, os.path.join(tmp, "work"))
        self.assertTrue(os.path.exists(out))
        self.assertEqual(r["stills"], 5 + 2 * 2)                       # 0,2,4,6,8 s + (-3f, +3f) x 2 boundaries
        self.assertEqual([x.split(" ")[0] for x in r["full_res"]], ["credits", "hook", "clip_01"])
        w, h = Image.open(out).size
        self.assertGreaterEqual(h, 1920)                               # full-resolution 9:16 panels are included
        self.assertEqual((w, h), tuple(r["size"]))


class TestLetterboxPerShot(unittest.TestCase):
    """E-FAIL-022 follow-up: the letterbox line is asked ONE frame per shot; any 'yes' / no answer on a non-screen
    shot fails; a screen shot (DEC-2: letterbox by design) is not asked."""

    def check(self, answers, frames):
        from unittest import mock
        it = iter(answers)
        with mock.patch.object(V, "ask_letterbox", side_effect=lambda path, model, **kw: next(it)):
            return V.letterbox_check(frames)

    def test_rules(self):
        th = {"label": "clip_01", "shot": 0, "class": "single", "path": "f.jpg"}
        scr = {"label": "hook", "shot": 0, "class": "screen", "path": "s.jpg"}
        self.assertTrue(self.check(["no", "no"], [scr, th])[0])                 # screen never asked
        self.assertFalse(self.check(["no", "yes"], [th])[0])                    # one model says letterboxed
        self.assertFalse(self.check([None, "no"], [th])[0])                     # no clear answer
        self.assertFalse(self.check([], [{**th, "path": None}])[0])             # no frame
        ok, rows = self.check(["no", "no", "yes", "no"], [th, {**th, "shot": 1}])
        self.assertEqual((ok, [r["ok"] for r in rows]), (False, [True, False]))
        from unittest import mock
        with mock.patch.object(V, "VISION_MODELS", ()):                     # audit 4: no model = no answer
            self.assertFalse(self.check([], [th])[0])

    def test_retries_exhausted_is_no_answer_with_the_trail(self):
        """Audit 4 (cross-LLM 7): every attempt fails or is unclear -> None (= FAIL), each attempt recorded."""
        from unittest import mock
        import urllib.error
        replies = iter([urllib.error.URLError("down"), ("I think it might be", {})])

        def call(req, timeout):
            r = next(replies)
            if isinstance(r, Exception):
                raise r
            return r
        trail = []
        with mock.patch.object(V, "_request", return_value=None), mock.patch.object(V, "_call", side_effect=call):
            self.assertIsNone(V.ask_letterbox("f.jpg", "m", trail=trail))
        self.assertEqual([("error" in t, t.get("answer")) for t in trail], [(True, None), (False, "unparseable")])

    def test_one_frame_per_shot_outside_any_dissolve(self):
        tmp = tempfile.mkdtemp(prefix="shots_")
        self.addCleanup(shutil.rmtree, tmp, True)
        final = os.path.join(tmp, "v.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=24:d=10",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", final], check=True)
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0},
                {"label": "clip_01", "type": "talking_head", "start": 3.75, "end": 8.0},
                {"label": "shoutout", "type": "shoutout", "start": 8.0, "end": 10.0}]
        layout = {"hook": {"shots": [{"start": 0.0, "end": 3.5, "class": "single"},
                                     {"start": 3.5, "end": 4.25, "class": "screen"}]}}
        fr = V.shot_frames(final, segs, layout, os.path.join(tmp, "w"))
        self.assertEqual([(f["label"], f["shot"], f["class"]) for f in fr],
                         [("hook", 0, "single"), ("hook", 1, "screen"), ("clip_01", 0, "unknown")])
        self.assertEqual([f["t"] for f in fr], [1.75, round(3.75 - 1 / 24, 3), 5.875])   # mid 3.875: in the dissolve
        self.assertTrue(all(f["path"] and os.path.exists(f["path"]) for f in fr))


QWEN_REPLAY_REPLY = ("\n\n{\"answers\": {\"credits_round_and_match\": {\"answer\": \"yes\", \"why\": \"round\"}, "
                     "\"vertical_speaker_centred\": {\"answer\": \"n/a\", \"why\": \"16:9\"}, "
                     "\"no_letterbox_on_talking_heads\": {\"answer\": \"n/a\", \"why\": \"16:9\"}, "
                     "\"no_bad_boundary_frames\": {\"answer\": \"yes\", \"why\": \"ok\"}, "
                     "\"watermark_present\": {\"answer\": \"yes\", \"why\": \"ok\"}, "
                     "\"no_next_shot_before_transition\": {\"answer\": \"yes\", \"why\": \"ok\"}}")


class TestV1Robustness(unittest.TestCase):
    def test_a_reply_missing_only_its_final_brace_is_read(self):
        """Replay of run 6, 16:9: qwen gave all six answers and stopped before the last '}' (6 x 'missing')."""
        a = V._parse(QWEN_REPLAY_REPLY)
        self.assertEqual(len(a), 6)
        self.assertTrue(V.verdict(a, "16x9")[0])
        self.assertIsNone(V._parse('{"answers": {"credits_round_and_match": {"answer": "yes", "why": "cut off'))
        two = QWEN_REPLAY_REPLY[:-1]                            # two closing braces missing: still closed
        self.assertEqual(len(V._parse(two)), 6)
        part = V._parse('{"answers": {"credits_round_and_match": {"answer": "yes"')   # closed, but ONE answer:
        self.assertFalse(V.verdict(part, "16x9")[0])                                    # the rest are missing

    def test_the_channel_list_reaches_the_prompt(self):
        from unittest import mock
        seen = {}
        with mock.patch.object(V, "_request", side_effect=lambda img, text, model: seen.setdefault("text", text)), \
                mock.patch.object(V, "_call", return_value=('{"answers": {}}', {})):
            V.ask_vision("sheet.jpg", "9x16", model="m", channels_note="Channels: Yahoo Finance (hook).")
        self.assertIn("Channels: Yahoo Finance (hook).", seen["text"])

    def test_cut_rules(self):
        from unittest import mock
        p = {"boundary": "clip_02|shoutout", "before_s": 41.2, "after_s": 41.5, "path": "pair.jpg"}
        for answers, ok in ((["no", "no"], True), (["no", "yes"], False), ([None, "no"], False)):
            it = iter(answers)
            with mock.patch.object(V, "ask_boundary", side_effect=lambda path, model, trail=None: next(it)):
                self.assertEqual(V.boundary_check([p])[0], ok, answers)
        with mock.patch.object(V, "VISION_MODELS", ()):
            self.assertFalse(V.boundary_check([p])[0])                 # nobody asked = no answer
        self.assertFalse(V.boundary_check([{**p, "path": None}])[0])   # no pair image


class TestSheetWiring(unittest.TestCase):
    """Heimdall batch 3 (verify_pack): a run copied for a transition option carries the previous render's
    qa/contact_sheet_*.jpg. If the new sheet cannot be built, the panel must not read the old one: the old
    file is removed first and a missing sheet is a V1 FAIL without any vision call."""

    def test_failed_sheet_is_a_fail_and_the_stale_sheet_is_never_read(self):
        from unittest import mock
        import verify_pack
        rd = tempfile.mkdtemp(prefix="vwire_")
        self.addCleanup(shutil.rmtree, rd, True)
        os.makedirs(os.path.join(rd, "qa"))
        json.dump({"hook": {"channel": "A", "vertical_layout": {"shots": [], "flagged": False}}, "clips": []},
                  open(os.path.join(rd, "edl.json"), "w"))
        for fmt in ("16x9", "9x16"):
            json.dump({"segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0}]},
                      open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
            open(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg"), "wb").write(b"stale sheet of another render")
        json.dump({"rows": {}}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
        rep, pack = {"rows": {}}, {}
        with mock.patch.object(V, "ask_panel", side_effect=AssertionError("panel asked")) as ask, \
                mock.patch.object(V, "boundary_check", side_effect=AssertionError("cuts asked")):
            verify_pack._sheets_and_checklist(rd, rep, pack, vision=True)     # out/ finals do not exist
        ask.assert_not_called()
        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))       # V1 lands in the report ON DISK
        for fmt in ("16x9", "9x16"):
            self.assertFalse(os.path.exists(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg")))
            self.assertEqual(out["rows"][fmt]["V1_visual_checklist"], "FAIL")       # exact verdict, reason in notes
            self.assertTrue(out["notes"][fmt]["V1_visual_checklist"].startswith("no contact sheet"),
                            out["notes"][fmt]["V1_visual_checklist"])


class TestPackArtefacts(unittest.TestCase):
    def test_a_sheet_with_any_missing_frame_is_no_sheet_and_a_failed_frame_never_reuses_an_old_file(self):
        """GPT-gates F09 / F10: a partial sheet is not a sheet; a frame ffmpeg could not grab is None, even when a
        file of that name is left from an earlier render."""
        import verify_pack
        from PIL import Image
        tmp = tempfile.mkdtemp(prefix="pack_")
        self.addCleanup(shutil.rmtree, tmp, True)
        p = os.path.join(tmp, "a.jpg")
        Image.new("RGB", (64, 36)).save(p)
        self.assertIsNone(verify_pack._sheet([("a", p), ("b", None)], os.path.join(tmp, "s.jpg"), 64))
        self.assertIsNone(verify_pack._sheet([], os.path.join(tmp, "s.jpg"), 64))
        self.assertTrue(verify_pack._sheet([("a", p)], os.path.join(tmp, "s.jpg"), 64))
        stale = os.path.join(tmp, "stale.jpg")
        Image.new("RGB", (64, 36)).save(stale)
        self.assertIsNone(verify_pack._frame(os.path.join(tmp, "missing.mp4"), 1.0, stale))
        self.assertFalse(os.path.exists(stale))


class TestCutWiring(unittest.TestCase):
    """The next-shot line is answered one cut at a time; the whole-sheet answer is advisory."""

    def wire(self, sheet_next, cuts_ok, per=None, shots=None, vision=True):
        """V1 rows + notes as written into GATE_REPORT.json, with the panel / shots / cuts injected."""
        from unittest import mock
        import verify_pack
        rd = tempfile.mkdtemp(prefix="cutwire_")
        self.addCleanup(shutil.rmtree, rd, True)
        os.makedirs(os.path.join(rd, "qa"))
        json.dump({"hook": {"channel": "A", "vertical_layout": {"shots": [], "flagged": False}}, "clips": []},
                  open(os.path.join(rd, "edl.json"), "w"))
        for fmt in ("16x9", "9x16"):
            json.dump({"segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 4.0},
                                    {"label": "outro", "type": "outro", "start": 4.0, "end": 8.0}]},
                      open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
        json.dump({"rows": {}}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
        rows = {k: {"answer": "yes", "why": "w", "ok": True} for k, _ in V.CHECKLIST}
        rows[verify_pack.NEXT_SHOT] = {"answer": sheet_next, "why": "w", "ok": sheet_next == "yes"}
        per = per if per is not None else {m: {"rows": dict(rows), "raw": {}} for m in V.VISION_MODELS}
        shots = shots if shots is not None else [{"label": "hook", "shot": 0, "ok": True}]
        cut = {"boundary": "hook|outro", "ok": cuts_ok}
        rep, pack = {"rows": {}}, {}
        with mock.patch.object(V, "contact_sheet", return_value={"path": "s.jpg"}), \
                mock.patch.object(V, "ask_panel", return_value=(sheet_next == "yes", per)), \
                mock.patch.object(V, "shot_frames", return_value=[]), \
                mock.patch.object(V, "letterbox_check", return_value=(all(x["ok"] for x in shots), shots)), \
                mock.patch.object(V, "boundary_pairs", return_value=[]), \
                mock.patch.object(V, "boundary_check", return_value=(cuts_ok, [cut])):
            verify_pack._sheets_and_checklist(rd, rep, pack, vision=vision)
        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))
        return out["rows"], out.get("notes", {}), out.get("evidence", {})

    def test_the_cut_check_decides_the_next_shot_line(self):
        rows, _, ev = self.wire("no", True)
        self.assertEqual(rows["16x9"]["V1_visual_checklist"], "PASS")     # sheet answer advisory
        self.assertGreaterEqual(ev["16x9"]["V1_visual_checklist"]["samples"], 1)
        rows, notes, _ = self.wire("yes", False)
        self.assertEqual(rows["9x16"]["V1_visual_checklist"], "FAIL")
        self.assertIn("next shot before the cut: hook|outro", notes["9x16"]["V1_visual_checklist"])

    def test_an_empty_or_partial_panel_is_never_a_pass(self):
        """GPT-gates F07 / Claude-gates M1: one model missing, a model that answered nothing, a line missing,
        a truthy string for ok: each FAILS V1."""
        import verify_pack
        full = {k: {"answer": "yes", "why": "w", "ok": True} for k, _ in V.CHECKLIST}
        one = V.VISION_MODELS[0]
        cases = {"one model only": {one: {"rows": full}},
                 "a model answered nothing": {m: {"rows": full if m == one else {}} for m in V.VISION_MODELS},
                 "a line missing": {m: {"rows": {k: r for k, r in full.items() if k != "watermark_present"}}
                                    for m in V.VISION_MODELS},
                 "ok is a string": {m: {"rows": {**full, "watermark_present": {"answer": "yes", "ok": "true"}}}
                                    for m in V.VISION_MODELS},
                 "no panel": {}}
        for name, per in cases.items():
            self.assertFalse(verify_pack.panel_ok(per), name)
            rows, _, _ = self.wire("no", True, per=per)
            self.assertEqual(rows["16x9"]["V1_visual_checklist"], "FAIL", name)
        self.assertTrue(verify_pack.panel_ok({m: {"rows": full} for m in V.VISION_MODELS}))

    def test_no_shots_asked_and_vision_off_are_never_a_pass(self):
        rows, _, _ = self.wire("no", True, shots=[])                     # zero letterbox frames (Claude-gates M2)
        self.assertEqual(rows["9x16"]["V1_visual_checklist"], "FAIL")
        rows, notes, ev = self.wire("no", True, vision=False)            # GPT-gates F08: a waiver switch leaves a trace
        for fmt in ("16x9", "9x16"):
            self.assertEqual(rows[fmt]["V1_visual_checklist"], "SKIPPED")
            self.assertEqual(ev[fmt]["V1_visual_checklist"], {"executed": False, "samples": 0})


def _has_vision_key():
    env = os.path.join(REPO, ".env")
    if not os.path.exists(env):
        return False
    with open(env) as f:
        return any(l.startswith("HEIMDALL_API_KEY") for l in f)


@unittest.skipUnless(_has_vision_key(), "Heimdall vision route key not available")
class TestVisionMustFail(unittest.TestCase):
    """Yesterday's vertical: thumbnail 'avatars' with headline text squashed into circles (D4) and letterboxed
    talking heads (D5). The vision panel, reading only the sheet, must hold it on one of those two lines."""

    def test_yesterdays_vertical_sheet_holds(self):
        # a missing must-fail fixture FAILS (never skips): the check would otherwise go untested unnoticed
        self.assertTrue(os.path.exists(SHEET_NOV10), f"must-fail fixture missing: {SHEET_NOV10}")
        ok, per = V.ask_panel(SHEET_NOV10, "9x16")
        self.assertFalse(ok, json.dumps(per, default=str)[:2000])
        named = {k for d in per.values() for k, r in d["rows"].items() if r["answer"] == "no"}
        self.assertTrue(named & {"credits_round_and_match", "no_letterbox_on_talking_heads"},
                        f"held, but not for D4/D5: {json.dumps(per, default=str)[:2000]}")


    def test_yesterdays_letterboxed_talking_head_fails_and_a_reframed_one_passes(self):
        """D5 must-fail on the fixture's full-resolution clip_02 panel (Scott Melker in a band, blurred copy above
        and below); control: the same speaker cropped to fill the frame (what DEC-5's reframe produces)."""
        from PIL import Image
        self.assertTrue(os.path.exists(SHEET_NOV10), f"must-fail fixture missing: {SHEET_NOV10}")
        tmp = tempfile.mkdtemp(prefix="lbox_")
        self.addCleanup(shutil.rmtree, tmp, True)
        sheet = Image.open(SHEET_NOV10)
        W, H = sheet.size
        panel = sheet.crop((W - 1080, H - 1920, W, H))                 # the last full-res panel: clip_02
        lb, rf = os.path.join(tmp, "melker_letterbox.jpg"), os.path.join(tmp, "melker_reframed.jpg")
        panel.save(lb, quality=92)
        panel.crop((540 - 172, 655, 540 + 171, 1265)).resize((1080, 1920)).save(rf, quality=92)
        ok, rows = V.letterbox_check([{"label": "clip_02", "shot": 0, "class": "single", "path": lb}])
        self.assertFalse(ok, rows)
        ok, rows = V.letterbox_check([{"label": "clip_02", "shot": 0, "class": "single", "path": rf}])
        self.assertTrue(ok, rows)



@unittest.skipUnless(_has_vision_key(), "Heimdall vision route key not available")
class TestVisionMustPass(unittest.TestCase):
    """Addendum '22:15' item 4: V1's REAL PASSING fixture. The PBX-approved preview (references/
    pulse_preview_2026-11-11, read only) passes the whole V1 row in both formats with the current code: the sheet
    checklist from every vision model, the letterbox per shot (9:16) and the next shot per cut. Its failing
    fixtures are TestVisionMustFail; its missing-evidence answer is TestCutWiring / TestSheetWiring."""

    def test_the_approved_preview_passes_v1_in_both_formats(self):
        import verify_pack
        ref = os.path.join(REPO, "references", "pulse_preview_2026-11-11")
        self.assertTrue(os.path.isfile(os.path.join(ref, "out", "segment.mp4")), f"must-pass fixture missing: {ref}")
        rd = tempfile.mkdtemp(prefix="v1pass_")
        self.addCleanup(shutil.rmtree, rd, True)
        for sub in ("out", "qa"):
            os.makedirs(os.path.join(rd, sub))
        for rel in ("out/segment.mp4", "out/segment_vertical.mp4"):
            os.symlink(os.path.join(ref, rel), os.path.join(rd, rel))           # read only: ffmpeg reads them
        for rel in ("edl.json", "VERTICAL_LAYOUT.json", "qa/concat_manifest_16x9.json", "qa/concat_manifest_9x16.json"):
            shutil.copy(os.path.join(ref, rel), os.path.join(rd, rel))
        json.dump({"rows": {}}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
        pack = {}
        verify_pack._sheets_and_checklist(rd, {}, pack, vision=True)
        out = json.load(open(os.path.join(rd, "GATE_REPORT.json")))
        for fmt in ("16x9", "9x16"):
            self.assertEqual(out["rows"][fmt]["V1_visual_checklist"], "PASS",
                             f"{fmt}: {out.get('notes', {}).get(fmt)} | " + json.dumps(pack["visual"].get(fmt), default=str)[:3000])


if __name__ == "__main__":
    unittest.main()
