#!/usr/bin/env python3
"""Tests for PINNED mode (pinned.py + run_fresh.py --pinned).

Pinned mode is a thin entry point: validate the human decision, write the canonical EDL, hand off
to the shared factory. These tests prove it never changes a range, fails closed on bad input,
produces the same EDL shape AUTO produces, and that run_fresh's cut stage uses the exact pinned
table with the SAME acceptance check (never the acoustic cutter).

Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_pinned.py
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)

import pinned  # noqa: E402

PINS = os.path.join(REPO, "references", "pinned")
REF = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
HAVE_REF = os.path.isdir(os.path.join(REF, "sources"))
REG = json.load(open(os.path.join(PIPELINE, "channels.json")))
APPROVED = next(c["display_name"] for c in REG if c.get("layout_status") == "approved" and c.get("channel_id"))
PENDING = next(c["display_name"] for c in REG if c.get("layout_status") != "approved" and c.get("channel_id"))


def _make_media(path, seconds=40):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-f", "lavfi", "-i", f"color=c=black:s=320x240:d={seconds}", "-shortest",
                    "-c:v", "libx264", "-c:a", "aac", path], check=True)


def _words(t0, t1, step=0.5):
    out, t, i = [], t0, 0
    while t + 0.4 <= t1:
        out.append({"word": f"Word{i}." if i % 6 == 5 else f"word{i}", "start": round(t, 3), "end": round(t + 0.4, 3)})
        t += step
        i += 1
    return out


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pin_test_")
        self.run_dir = os.path.join(self.tmp, "run")
        for sub in ("sources", "transcripts", "qa", "out", "vo_audio"):
            os.makedirs(os.path.join(self.run_dir, sub))
        self.src = {}
        for vid in ("AAAAAAAAAA1", "BBBBBBBBBB2"):
            mp4 = os.path.join(self.tmp, f"{vid}.mp4")
            _make_media(mp4)
            tr = os.path.join(self.tmp, f"{vid}.json")
            json.dump({"words": _words(1.0, 30.0)}, open(tr, "w"))       # speech only in 1-30 s
            self.src[vid] = {"kind": "local_file", "path": mp4, "sha256": pinned._sha256(mp4),
                             "transcript_path": tr, "transcript_sha256": pinned._sha256(tr)}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def pin(self, **kw):
        p = {"schema": pinned.SCHEMA, "story_id": "t1", "label": "test label", "approved_by": "PBX",
             "approved_at": "2026-11-06T21:00:00-05:00",
             "segments": [
                 {"role": "hook", "video_id": "AAAAAAAAAA1", "channel": APPROVED, "start": 2.03, "end": 11.71,
                  "time_coords": "source_file", "source": self.src["AAAAAAAAAA1"]},
                 {"role": "clip", "video_id": "BBBBBBBBBB2", "channel": PENDING, "start": 3.17, "end": 17.49,
                  "time_coords": "source_file", "source": self.src["BBBBBBBBBB2"]},
                 {"role": "clip", "video_id": "AAAAAAAAAA1", "channel": APPROVED, "start": 14.02, "end": 27.88,
                  "time_coords": "source_file", "source": self.src["AAAAAAAAAA1"]}]}
        p.update(kw)
        return p

    def write(self, p):
        path = os.path.join(self.tmp, "pin.json")
        json.dump(p, open(path, "w"))
        return path


class TestSchema(Fixture):
    def bad(self, mutate):
        p = self.pin()
        mutate(p)
        with self.assertRaises(pinned.PinError):
            pinned.validate_schema(p, REG)

    def test_valid_pin_passes(self):
        pinned.validate_schema(self.pin(), REG)

    def test_rejections(self):
        cases = [
            lambda p: p.update(schema="v0"),
            lambda p: p.update(approved_by=""),
            lambda p: p.update(story_id=None),
            lambda p: p["segments"].pop(0),                                  # no hook
            lambda p: p["segments"][1].update(role="hook"),                  # two hooks
            lambda p: p["segments"].reverse(),                               # hook not first
            lambda p: p.update(segments=p["segments"][:1]),                  # no clip
            lambda p: p["segments"][1].update(role="bridge"),
            lambda p: p["segments"][1].update(channel="Not A Channel"),
            lambda p: p["segments"][1].update(video_id="short"),
            lambda p: p["segments"][1].update(start=10.0, end=10.0),
            lambda p: p["segments"][1].update(start=-1.0),
            lambda p: p["segments"][1].update(end="17"),
            lambda p: p["segments"][1].update(time_coords="youtube"),        # local file needs source_file
            lambda p: p["segments"][1].update(source={"kind": "youtube"}),   # youtube needs youtube coords
            lambda p: p["segments"][1]["source"].pop("sha256"),
            lambda p: p["segments"][2].update(start=11.0),                   # overlaps the hook (same video)
        ]
        for i, m in enumerate(cases):
            with self.subTest(case=i):
                self.bad(m)


class TestNeverModified(Fixture):
    def test_edl_and_cut_table_use_exact_ranges(self):
        p = self.pin()
        rec = pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        segs = [edl["hook"]] + edl["clips"]
        for s, inp in zip(segs, p["segments"]):
            self.assertEqual((s["pinned"]["start"], s["pinned"]["end"]), (inp["start"], inp["end"]))
            self.assertEqual(s["cut_out"], inp["end"])
        cuts = pinned.write_pinned_cut_table(self.run_dir)
        self.assertEqual([(c["cut_in"], c["cut_out"]) for c in cuts], [(s["start"], s["end"]) for s in p["segments"]])
        self.assertTrue(all(c["pinned"] and c["fade_in_ms"] == 20 and c["fade_out_ms"] == 30 for c in cuts))
        # the text is only what the transcript says inside the range — no neighbouring sentence
        tr = json.load(open(self.src["BBBBBBBBBB2"]["transcript_path"]))["words"]
        inside = [w["word"] for w in tr if w["start"] >= 3.17 and w["end"] <= 17.49]
        self.assertEqual(edl["clips"][0]["text"], " ".join(inside))
        # a word in the boundary tail (11.5-11.9 against end 11.71) is never an expected edge word
        self.assertEqual(edl["hook"]["last_word"], "word20")
        self.assertEqual(rec["pin"], p)

    def test_approved_text_sets_edge_words_and_must_match_transcript(self):
        p = self.pin()
        tr = json.load(open(self.src["BBBBBBBBBB2"]["transcript_path"]))["words"]
        words = [w["word"] for w in tr if w["end"] > 3.17 and w["start"] < 17.49]
        p["segments"][1]["approved_text"] = " ".join(words)
        pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        self.assertEqual((edl["clips"][0]["first_word"], edl["clips"][0]["last_word"]), (words[0], words[-1]))
        self.assertEqual(edl["clips"][0]["pinned"]["start"], 3.17)             # range itself unchanged
        p["segments"][1]["approved_text"] = "the federal reserve raised rates again in a surprise move today"
        with self.assertRaises(pinned.PinError) as cm:
            pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        self.assertIn("does not correspond", str(cm.exception))

    def test_out_of_source_range_rejected(self):
        p = self.pin()
        p["segments"][1].update(start=30.0, end=45.0)                        # file is 40 s
        with self.assertRaises(pinned.PinError):
            pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)

    def test_range_without_speech_rejected(self):
        p = self.pin()
        p["segments"][1].update(start=31.0, end=39.0)                        # silence in transcript
        with self.assertRaises(pinned.PinError) as cm:
            pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        self.assertIn("word(s) inside the range", str(cm.exception))

    def test_sha_mismatch_rejected(self):
        p = self.pin()
        p["segments"][1]["source"] = dict(p["segments"][1]["source"], sha256="0" * 64)
        with self.assertRaises(pinned.PinError) as cm:
            pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        self.assertIn("sha256 mismatch", str(cm.exception))


class TestCanonicalShape(Fixture):
    AUTO_KEYS = {"video_id", "channel", "handle", "video_title", "text", "first_word", "last_word",
                 "word_start", "word_end", "duration", "time_coords", "source_window_offset_s"}

    def test_same_edl_shape_overrides_and_vo_as_auto(self):
        import select_passages as sp
        import edl_rules
        p = self.pin()
        pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        for s in [edl["hook"]] + edl["clips"]:
            self.assertTrue(self.AUTO_KEYS <= set(s), self.AUTO_KEYS - set(s))
            self.assertEqual(s["time_coords"], "source_file")
        self.assertEqual([c["index"] for c in edl["clips"]], [1, 2])
        self.assertEqual(edl["vo"], sp._generate_vo_script(p["label"], edl["hook"]["text"], edl["clips"],
                                                           sorted({APPROVED, PENDING})))
        ov = json.load(open(os.path.join(self.run_dir, "vertical_overrides.json")))
        # DEC-5: speaker-centred reframe ('auto') for every segment, approved or pending channel
        self.assertEqual(ov, {"hook": {"layout": "auto"}, "clip_01": {"layout": "auto"},
                              "clip_02": {"layout": "auto"}})
        ok, res = edl_rules.validate_edl(edl, channels_registry=REG)
        self.assertTrue(ok, [r for r in res if not r["pass"]])

    def test_vertical_overrides_are_auto_for_every_channel_status(self):
        # DEC-5 (2026-11-11) retires M21's letterbox-by-registry-status default: the Nov 10 cut fell to
        # letterbox only because its channels were 'pending' (D5). No status yields crop or letterbox.
        import select_passages as sp
        hook = {"channel": APPROVED}
        clips = [{"channel": PENDING, "index": 1}, {"channel": APPROVED, "index": 2}, {"channel": "Unknown", "index": 3}]
        self.assertEqual(sp.build_vertical_overrides(hook, clips),
                         {"hook": {"layout": "auto"}, "clip_01": {"layout": "auto"},
                          "clip_02": {"layout": "auto"}, "clip_03": {"layout": "auto"}})


class TestRunFreshUsesSharedCutAcceptance(Fixture):
    def test_pinned_cut_stage_writes_exact_table_and_runs_the_same_acceptance(self):
        import run_fresh as rf
        import cut
        import cut_accept
        p = self.pin()
        pinned.prepare(self.write(p), self.run_dir, log=lambda s: None)
        for vid in self.src:
            shutil.copyfile(self.src[vid]["path"], os.path.join(self.run_dir, "sources", f"{vid}.mp4"))
        calls = []
        orig_cut, orig_acc = cut.compute_all_cuts, cut_accept.check_cut_acoustics
        cut.compute_all_cuts = lambda *a, **k: (_ for _ in ()).throw(AssertionError("acoustic cutter must not run"))
        cut_accept.check_cut_acoustics = lambda src, a, b: (calls.append((os.path.basename(src), a, b)) or
                                                             (True, {"in": {"pass": True}, "out": {"pass": True}}))
        try:
            run = rf.Run(self.run_dir)
            run.mode = "pinned"
            cuts = rf.stage_cut(run)
            self.assertEqual(calls, [(f"{s['video_id']}.mp4", s["start"], s["end"]) for s in p["segments"]])
            self.assertEqual([(c["cut_in"], c["cut_out"]) for c in cuts], [(s["start"], s["end"]) for s in p["segments"]])
            # acceptance rejection still holds the run (no auto-widen)
            cut_accept.check_cut_acoustics = lambda src, a, b: (False, {"in": {"pass": True}, "out": {"pass": False},
                                                                          "reason": "test"})
            with self.assertRaises(rf.Hold):
                rf.stage_cut(run)
        finally:
            cut.compute_all_cuts, cut_accept.check_cut_acoustics = orig_cut, orig_acc

    def test_auto_mode_places_cuts_from_the_selection_locks(self):
        # 2026-11-11 sentence law: AUTO cuts come from the locked sentences' pauses
        # (sentence_law.write_lock_cut_table); the free acoustic cutter is never used by run_fresh.
        import run_fresh as rf
        import cut
        import sentence_law
        orig_cut, orig_lock = cut.compute_all_cuts, sentence_law.write_lock_cut_table
        cut.compute_all_cuts = lambda *a, **k: (_ for _ in ()).throw(AssertionError("free acoustic cutter used"))
        sentence_law.write_lock_cut_table = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("lock placement"))
        try:
            run = rf.Run(self.run_dir)
            self.assertEqual(run.mode, "auto")
            with self.assertRaisesRegex(RuntimeError, "lock placement"):
                rf.stage_cut(run)
        finally:
            cut.compute_all_cuts, sentence_law.write_lock_cut_table = orig_cut, orig_lock

    def test_v2f_material_guard_only_lifted_by_explicit_pin_flag(self):
        import run_fresh as rf
        run = rf.Run(self.run_dir)
        self.assertFalse(run.allow_v2f_material)
        src = open(rf.__file__).read()
        self.assertIn("run.allow_v2f_material = bool(pin.get(\"reuses_v2f_material\"))", src)
        self.assertEqual(rf.RELEASE_STATE, "HOLD_FOR_HUMAN_APPROVAL")


class TestMomentsPackage(Fixture):
    """pp-selectid REQUESTS R7 item 1 (laws L-q, L-t): a moments-first package rides the pinned path: its VO (intro, a
    bridge after each clip but the last), its ONE title and caption, its sha256 and gate verdicts enter the EDL; a
    package whose VO-fidelity and context-integrity gates did not both pass, or a bridge the renderer cannot place, is
    refused; a pin without a package is unchanged (no body VO)."""

    def mp(self, segs=None, **kw):
        segs = segs or self.pin()["segments"]
        m = {"title": "T", "caption": "C", "package_sha256": "ab" * 32,
             "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True},
             "edl_vo": {"intro": "Intro line.", "bridges": [{"text": "Bridge one.", "after_clip": 1}]},
             "sources_30s_before": [f"https://www.youtube.com/watch?v={s['video_id']}&t=0s" for s in segs]}
        m.update(kw)
        return m

    def test_the_package_vo_title_and_caption_enter_the_edl(self):
        pinned.prepare(self.write(self.pin(moments_package=self.mp())), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        self.assertEqual(edl["vo"], {"intro": "Intro line.", "bridges": [{"text": "Bridge one.", "after_clip": 1}]})
        self.assertEqual((edl["title"], edl["caption"], edl["moments_package_sha256"]), ("T", "C", "ab" * 32))
        self.assertEqual(edl["moments_checks"], {"vo_fidelity_ok": True, "context_integrity_ok": True})
        self.assertRegex(edl["moments_package_pin_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(len(edl["moments_sources_30s_before"]), 3)

    def test_a_moments_package_may_close_on_a_takeaway_after_the_last_clip(self):
        """Law L-q (orchestrator 2026-11-12 '06:00'): type 'moments' only: a line after the LAST clip has a slot
        (render16 / render_vertical play it before the shout-out); any other type keeps 1..last-1; a line with no slot,
        or two on one slot, is refused."""
        segs = self.pin()["segments"]
        clips = [{"index": 1}, {"index": 2}]

        def br(*items):
            return {"intro": "Intro.", "bridges": [dict(text="x", after_clip=a) for a in items]}
        got = pinned.moments_vo(self.mp(type="moments", edl_vo=br(1, 2)), clips, segs)
        self.assertEqual([b["after_clip"] for b in got["bridges"]], [1, 2])
        for typ, items in (("story", (2,)), (None, (2,)), ("Moments", (2,)), ("moments", (3,)), ("moments", (2, 2)),
                           ("moments", (0,)), ("moments", (2, 1))):
            mp = self.mp(edl_vo=br(*items), **({"type": typ} if typ is not None else {}))
            with self.assertRaisesRegex(pinned.PinError, "after_clip must be", msg=(typ, items)):
                pinned.moments_vo(mp, clips, segs)
        pinned.prepare(self.write(self.pin(moments_package=self.mp(type="moments", edl_vo=br(1, 2)))), self.run_dir,
                       log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        self.assertEqual((edl["package_type"], [b["after_clip"] for b in edl["vo"]["bridges"]]), ("moments", [1, 2]))
        import edl_rules                                       # end to end: build_edl's shape is what R4 (moments) reads
        ok, why = edl_rules.rule_r4(edl)
        self.assertIn("(moments)", why)
        for shape in ("without a validated moments package", "is not a measured positive number", "clip indexes",
                      "has no slot", "is empty"):
            self.assertNotIn(shape, why)

    def test_a_pin_without_a_package_is_unchanged(self):
        pinned.prepare(self.write(self.pin()), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        self.assertEqual(edl["vo"], {"intro": None, "bridges": []})
        for k in ("title", "caption", "moments_package_sha256", "moments_checks"):
            self.assertNotIn(k, edl)

    def test_refused_packages(self):
        """Every shape the renderer cannot place, every verdict that is not exactly true, every malformed field: a
        PinError naming it (cycle 1 of the R7 audit), never a KeyError / AttributeError / TypeError, never ignored."""
        def br(*items):
            return {"intro": None, "bridges": [dict(text="x", after_clip=a) for a in items]}
        cases = [("gates not both passed", self.mp(checks={"vo_fidelity_ok": True}), "did not both pass"),
                 ("a verdict that is truthy but not true", self.mp(checks={"vo_fidelity_ok": "false",
                                                                          "context_integrity_ok": True}), "did not both pass"),
                 ("checks null", self.mp(checks=None), "did not both pass"),
                 ("checks a list", self.mp(checks=[True]), "did not both pass"),
                 ("another check failed", self.mp(checks={"vo_fidelity_ok": True, "context_integrity_ok": True,
                                                          "title_ok": False}), "checks not passed"),
                 ("bridge after the last clip", self.mp(edl_vo=br(2)), "after_clip must be"),
                 ("bridge after no clip", self.mp(edl_vo=br(7)), "after_clip must be"),
                 ("bridge after the hook", self.mp(edl_vo=br(0)), "after_clip must be"),
                 ("bool index", self.mp(edl_vo=br(True)), "after_clip must be"),
                 ("float index", self.mp(edl_vo=br(1.0)), "after_clip must be"),
                 ("string index", self.mp(edl_vo=br("1")), "after_clip must be"),
                 ("unhashable index", self.mp(edl_vo=br([1])), "after_clip must be"),
                 ("empty bridge", self.mp(edl_vo={"intro": None, "bridges": [{"text": " ", "after_clip": 1}]}), "text"),
                 ("non-string bridge text", self.mp(edl_vo={"intro": None, "bridges": [{"text": 5, "after_clip": 1}]}), "text"),
                 ("bridges not a list", self.mp(edl_vo={"intro": None, "bridges": 5}), "must be a list"),
                 ("edl_vo not an object", self.mp(edl_vo=[1]), "edl_vo must be"),
                 ("edl_vo missing", {k: v for k, v in self.mp().items() if k != "edl_vo"}, "edl_vo must be"),
                 ("empty intro", self.mp(edl_vo={"intro": "  ", "bridges": []}), "intro must be"),
                 ("non-string intro", self.mp(edl_vo={"intro": 123, "bridges": []}), "intro must be"),
                 ("title missing", {k: v for k, v in self.mp().items() if k != "title"}, "title must be"),
                 ("caption empty", self.mp(caption=" "), "caption must be"),
                 ("sha not hex", self.mp(package_sha256="zz"), "package_sha256"),
                 ("package not an object", "not a package", "not an object"),
                 ("package null", None, "not an object"),
                 ("package a list", [], "not an object"),
                 ("package false", False, "not an object"),
                 ("package empty object", {}, "sources_30s_before"),
                 ("bridges key missing", self.mp(edl_vo={"intro": None}), "must state both"),
                 ("intro key missing", self.mp(edl_vo={"bridges": []}), "must state both"),
                 ("edl_vo empty", self.mp(edl_vo={}), "must state both"),
                 ("non-object bridge", self.mp(edl_vo={"intro": None, "bridges": ["x"]}), "needs non-empty text"),
                 ("null bridge", self.mp(edl_vo={"intro": None, "bridges": [None]}), "needs non-empty text"),
                 ("after_clip missing", self.mp(edl_vo={"intro": None, "bridges": [{"text": "x"}]}), "after_clip must be"),
                 ("negative after_clip", self.mp(edl_vo={"intro": None, "bridges": [{"text": "x", "after_clip": -1}]}),
                  "after_clip must be"),
                 ("verdict 1, not true", self.mp(checks={"vo_fidelity_ok": 1, "context_integrity_ok": True}),
                  "did not both pass"),
                 ("sha upper case", self.mp(package_sha256="AB" * 32), "package_sha256"),
                 ("sha 63 characters", self.mp(package_sha256="a" * 63), "package_sha256"),
                 ("sha missing", {k: v for k, v in self.mp().items() if k != "package_sha256"}, "package_sha256"),
                 ("links for other videos", self.mp(sources_30s_before=["https://www.youtube.com/watch?v=ZZZ"] * 3),
                  "sources_30s_before"),
                 ("one link short", self.mp(sources_30s_before=self.mp()["sources_30s_before"][:2]), "sources_30s_before"),
                 ("hook first words of another sentence", self.mp(hook_first_words="Something else entirely"),
                  "hook_first_words")]
        for name, m, why in cases:
            with self.subTest(name):
                edl_path = os.path.join(self.run_dir, "edl.json")
                if os.path.exists(edl_path):
                    os.remove(edl_path)
                with self.assertRaisesRegex(pinned.PinError, why):
                    pinned.prepare(self.write(self.pin(moments_package=m)), self.run_dir, log=lambda s: None)
                self.assertFalse(os.path.exists(edl_path))                   # nothing built from a refused package

    def test_duplicate_or_reordered_bridges_are_refused_with_three_clips(self):
        segs = self.pin()["segments"] + [{"role": "clip", "video_id": "BBBBBBBBBB2", "channel": PENDING, "start": 18.5,
                                          "end": 28.9, "time_coords": "source_file", "source": self.src["BBBBBBBBBB2"]}]
        for name, bridges in (("duplicate", [1, 1]), ("reordered", [2, 1])):
            with self.subTest(name):
                m = self.mp(segs, edl_vo={"intro": None, "bridges": [{"text": "x", "after_clip": a} for a in bridges]})
                with self.assertRaisesRegex(pinned.PinError, "strictly increasing"):
                    pinned.prepare(self.write(self.pin(segments=segs, moments_package=m)), self.run_dir,
                                   log=lambda s: None)
        m = self.mp(segs, edl_vo={"intro": "I.", "bridges": [{"text": "a", "after_clip": 1}, {"text": "b", "after_clip": 2}]})
        pinned.prepare(self.write(self.pin(segments=segs, moments_package=m)), self.run_dir, log=lambda s: None)
        edl = json.load(open(os.path.join(self.run_dir, "edl.json")))
        self.assertEqual([b["after_clip"] for b in edl["vo"]["bridges"]], [1, 2])


class TestPinnedStageFreesGpu0First(Fixture):
    """E-FAIL-052: pinned.acquire transcribes every downloaded source with Whisper on GPU0, so the editorial model the
    preflight's Ollama check loaded is released first, as before every other Whisper stage (runs/pinned_20261112_064032:
    gemma3:27b held 20548 of 24564 MiB and Whisper ran out of memory)."""

    def test_the_release_comes_before_the_pin_is_acquired_and_a_failed_release_holds(self):
        import run_fresh as rf
        events = []
        orig_free, orig_prep = rf.free_gpu0_for_whisper, pinned.prepare

        def release(run, stage, **kw):
            events.append(("release", stage))

        def prep(*a, **k):
            events.append("prepare")
            raise pinned.PinError("stopped once the order is seen")

        def refuse(run, stage, **kw):
            events.append(("release", stage))
            raise rf.Hold(f"infrastructure: {stage}: GPU0 release not proven")
        try:
            rf.free_gpu0_for_whisper, pinned.prepare = release, prep
            run = rf.Run(self.run_dir)
            with self.assertRaisesRegex(rf.Hold, "pinned decision rejected"):
                rf.stage_pinned(run, self.write(self.pin()))
            self.assertEqual(events, [("release", "pinned"), "prepare"])
            events.clear()
            rf.free_gpu0_for_whisper = refuse
            with self.assertRaisesRegex(rf.Hold, "^infrastructure: pinned") as cm:    # anchored (fable audit of 456a440f)
                rf.stage_pinned(run, self.write(self.pin()))
            self.assertNotIn("pinned decision rejected", str(cm.exception))
            self.assertEqual(events, [("release", "pinned")])        # nothing downloaded or transcribed after it
        finally:
            rf.free_gpu0_for_whisper, pinned.prepare = orig_free, orig_prep


@unittest.skipUnless(HAVE_REF, "v2f reference sources not present")
class TestV2fProofPins(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pin_v2f_")
        for sub in ("sources", "transcripts"):
            os.makedirs(os.path.join(self.tmp, sub))
        # ruling 17: the v2f proof pins predate it, and their third range's approved text covers a different word
        # range than its lock (3 words before it, 11 fewer at its end). These are cut-acceptance tests: they inject a
        # second recogniser that reads the approved text over the lock's span, so the lock adopts it and the cut
        # checks run as before (the adjudication itself: test_ruling17_lock). No paid call (conftest guard).
        orig = pinned.adjudicate_lock

        def reads_approved(lock, src, words, recognise=None, log=print):
            t0, t1 = float(words[lock["i0"]]["start"]), float(words[lock["i1"]]["end"])
            ws = lock["selected_text"].split()
            step = (t1 - t0) / max(len(ws), 1)
            fake = [{"word": w, "start": t0 + k * step, "end": t0 + (k + 0.8) * step} for k, w in enumerate(ws)]
            return orig(lock, src, words, recognise=lambda s: (fake, 0.0), log=log)
        patcher = mock.patch.object(pinned, "adjudicate_lock", reads_approved)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_proof_pin_validates_exactly_and_passes_shared_acceptance(self):
        from cut_accept import check_cut_acoustics
        path = os.path.join(PINS, "v2f_integration_proof.pin.json")
        pinned.prepare(path, self.tmp, log=lambda s: None)
        cuts = pinned.write_pinned_cut_table(self.tmp)
        self.assertEqual([(c["cut_in"], c["cut_out"]) for c in cuts], [(0.0, 9.52), (624.63, 636.72), (998.0, 1011.8)])
        # expected edge words are the approved v2f words, not the next word in the silent tail
        self.assertEqual([(c["first_word_expected"], c["last_word_expected"]) for c in cuts],
                         [("The", "thinks."), ("One", "dollars."), ("a", "have.")])
        for c in cuts:
            ok, d = check_cut_acoustics(os.path.join(self.tmp, "sources", f"{c['video_id']}.mp4"), c["cut_in"], c["cut_out"])
            self.assertTrue(ok, (c["clip_id"], d))

    def test_full_four_range_pin_fails_closed_at_shared_acceptance(self):
        from cut_accept import check_cut_acoustics
        path = os.path.join(PINS, "v2f_full_4seg_mustfail.pin.json")
        pinned.prepare(path, self.tmp, log=lambda s: None)
        cuts = pinned.write_pinned_cut_table(self.tmp)
        res = {c["clip_id"]: check_cut_acoustics(os.path.join(self.tmp, "sources", f"{c['video_id']}.mp4"),
                                                 c["cut_in"], c["cut_out"])[0] for c in cuts}
        self.assertFalse(res["clip_01"], "249.63 needs run_isolated's one-time exception; the factory must refuse it")
        self.assertTrue(all(v for k, v in res.items() if k != "clip_01"), res)

    def test_example_schema_validates(self):
        pinned.validate_schema(json.load(open(os.path.join(PINS, "example_youtube.pin.json"))), REG)


if __name__ == "__main__":
    unittest.main()
