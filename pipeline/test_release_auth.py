#!/usr/bin/env python3
"""pipeline/release_auth.py: the fail-closed release contract (red-team 2026-11-11 A; GPT 'five cheapest tests' #2,
Claude 'five cheapest tests' #3). One complete passing run directory is built; every mutation of it must HOLD:
  inventory   a REQUIRED row deleted, any non-PASS verdict, a prefixed 'PASS (...)', an unknown row, a MONITORING
              row missing (it must be reported) -- while a MONITORING row that FAILS does not decide (addendum
              '22:15' item 4)
  evidence    missing, executed False, zero samples, a sample count that is not an int
  bytes       a final / manifest that is not what the gates measured; a bound file changed after the attestation;
              GATE_REPORT rows edited after the attestation
  pack        built without vision, incomplete, missing
  run         holds present (the run did not end clean), not deliverable (a replay), no / corrupt attestation
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_release_auth.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import release_auth as RA  # noqa: E402

_MEDIA = {}


def _media():
    """Two one-second black finals at the release dimensions (made once per process)."""
    if not _MEDIA:
        d = tempfile.mkdtemp(prefix="ra_media_")
        for name, (w, h) in (("segment.mp4", (1920, 1080)), ("segment_vertical.mp4", (1080, 1920))):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=24:d=1",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", os.path.join(d, name)],
                           check=True)
        _MEDIA["dir"] = d
    return _MEDIA["dir"]


def passing_rows():
    rows = {fmt: {k: "PASS" for k in RA.INVENTORY[fmt] | RA.MONITORING[fmt]} for fmt in RA.FORMATS}
    rows["9x16"]["G14_frame_similarity"] = "LIMITED"
    return rows


def make_run(parent, rows=None, attest=True, run_state=None, edl=None):
    """A complete run directory that release_auth authorises (unless the caller mutates it)."""
    from PIL import Image
    rd = tempfile.mkdtemp(prefix="fresh_", dir=parent)
    for sub in ("out", "qa", "VERIFY"):
        os.makedirs(os.path.join(rd, sub))
    for name in ("segment.mp4", "segment_vertical.mp4"):
        shutil.copy(os.path.join(_media(), name), os.path.join(rd, "out", name))
    shot = {"start": 0.0, "end": 9.4, "class": "single", "flagged": False}
    json.dump(edl or {"topic": "Bitcoin price dip", "headline": "Bitcoin price dip",
                      "hook": {"channel": "Yahoo Finance", "video_id": "YAH0000000a",
                               "selection_lock": {"text": "Bitcoin fell to 74,000 dollars today."},
                               "vertical_layout": {"shots": [shot], "flagged": False}},
                      "clips": [{"index": 1, "channel": "Natalie Brunell", "video_id": "NAT0000000b",
                                 "selection_lock": {"text": "It is a bear market rally."},
                                 "vertical_layout": {"shots": [shot], "flagged": False}}]},
              open(os.path.join(rd, "edl.json"), "w"))
    for fmt in RA.FORMATS:
        json.dump({"format": fmt, "segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 0.5},
                                               {"label": "outro", "type": "outro", "start": 0.5, "end": 1.0}]},
                  open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
        Image.new("RGB", (120, 80)).save(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg"))
    rows = rows or passing_rows()
    measured = {rel: RA.sha256(os.path.join(rd, rel)) for rel in
                ("out/segment.mp4", "out/segment_vertical.mp4", "qa/concat_manifest_16x9.json",
                 "qa/concat_manifest_9x16.json")}
    e = json.load(open(os.path.join(rd, "edl.json")))
    heard = [{"segment": lab, "heard": seg["selection_lock"]["text"]}               # G18's final-audio readings
             for lab, seg in [("hook", e["hook"])] + [(f"clip_{c['index']:02d}", c) for c in e["clips"]]]
    json.dump({"inventory_version": RA.INVENTORY_VERSION, "rows": rows,
               "evidence": {fmt: {k: {"executed": True, "samples": 3} for k in r} for fmt, r in rows.items()},
               "notes": {}, "measured_files": measured, "G18": {"16x9": heard, "9x16": heard}},
              open(os.path.join(rd, "GATE_REPORT.json"), "w"))
    json.dump({"complete": True, "vision": True, "passed": True,
               "visual": {f: {"ok": True} for f in RA.FORMATS}}, open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w"))
    if attest:
        RA.attest(rd, run_state or {"ok": True, "why": []})
    return rd


def edit_json(path, fn):
    d = json.load(open(path))
    fn(d)
    json.dump(d, open(path, "w"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ra_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def holds(self, rd, label):
        """attest from the (mutated) disk state, then authorise: both must refuse."""
        att = RA.attest(rd, {"ok": True, "why": []})
        ok, why, _ = RA.authorise(rd)
        self.assertEqual(att["verdict"], "HOLD", label)
        self.assertFalse(ok, label)
        return att


class TestPassingRun(Base):
    def test_the_complete_run_is_authorised(self):
        rd = make_run(self.tmp)
        ok, why, att = RA.authorise(rd)
        self.assertTrue(ok, why)
        self.assertEqual(att["verdict"], "ALL_PASS")
        self.assertEqual(set(att["files"]), set(RA.BOUND))


class TestInventory(Base):
    def mutate_rows(self, fn, label):
        rd = make_run(self.tmp, attest=False)
        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: fn(d["rows"]))
        return self.holds(rd, label)

    def test_every_required_row_deleted_holds(self):
        for fmt in RA.FORMATS:
            for k in sorted(RA.INVENTORY[fmt]):
                self.mutate_rows(lambda r, f=fmt, k=k: r[f].pop(k), f"{fmt} {k} deleted")

    def test_every_non_pass_verdict_and_a_prefixed_pass_hold(self):
        for v in ("FAIL", "HOLD", "SKIPPED", "LIMITED", "PASS (no fallback)", "PASS(L-c: x)", "pass", True, None, ""):
            self.mutate_rows(lambda r, v=v: r["16x9"].__setitem__("G18_word_for_word", v), f"G18 = {v!r}")

    def test_an_unknown_row_holds(self):
        self.mutate_rows(lambda r: r["9x16"].__setitem__("G11_parity(run_gates)", "NOT RUN BY run_gates"),
                         "legacy placeholder row")
        self.mutate_rows(lambda r: r["16x9"].__setitem__("G99_new", "PASS"), "unlisted row")

    def test_a_monitoring_row_must_be_reported_but_does_not_decide(self):
        for fmt in RA.FORMATS:
            for k in sorted(RA.MONITORING[fmt]):
                self.mutate_rows(lambda r, f=fmt, k=k: r[f].pop(k), f"{fmt} monitoring {k} missing")
        rows = passing_rows()
        rows["16x9"]["G1_voice"] = "FAIL"
        rows["9x16"]["G13_vo_audible"] = "SKIPPED"
        rd = make_run(self.tmp, rows=rows)
        ok, why, _ = RA.authorise(rd)
        self.assertTrue(ok, why)
        self.assertEqual(RA.monitoring_report(rows), {"16x9": {"G1_voice": "FAIL"}, "9x16": {"G13_vo_audible": "SKIPPED"}})

    def test_the_known_limitation_row_carries_only_its_verdict(self):
        self.mutate_rows(lambda r: r["9x16"].__setitem__("G14_frame_similarity", "PASS"), "LIMITED row reads PASS")
        self.mutate_rows(lambda r: r["9x16"].pop("G14_frame_similarity"), "LIMITED row missing")

    def test_a_format_missing_holds(self):
        self.mutate_rows(lambda r: r.pop("9x16"), "9x16 rows missing")


class TestEvidence(Base):
    def test_a_required_row_without_execution_evidence_holds(self):
        for bad in (None, {}, {"executed": False, "samples": 3}, {"executed": True, "samples": 0},
                    {"executed": True, "samples": "3"}, {"executed": True, "samples": True},
                    {"executed": "true", "samples": 3}):
            rd = make_run(self.tmp, attest=False)

            def fn(d, bad=bad):
                if bad is None:
                    d["evidence"]["16x9"].pop("G16_sentence_boundary")
                else:
                    d["evidence"]["16x9"]["G16_sentence_boundary"] = bad
            edit_json(os.path.join(rd, "GATE_REPORT.json"), fn)
            self.holds(rd, f"evidence {bad!r}")

    def test_a_report_with_no_or_malformed_evidence_holds(self):
        """GPT audit (batch 16) #1: the WHOLE evidence field absent, null, or a format entry that is not a mapping
        is no evidence (it used to skip the check), and never a crash."""
        for fn, label in ((lambda d: d.pop("evidence"), "evidence deleted"),
                          (lambda d: d.__setitem__("evidence", None), "evidence null"),
                          (lambda d: d.__setitem__("evidence", []), "evidence a list"),
                          (lambda d: d["evidence"].__setitem__("16x9", "yes"), "a format entry is a string")):
            rd = make_run(self.tmp, attest=False)
            edit_json(os.path.join(rd, "GATE_REPORT.json"), fn)
            self.holds(rd, label)
        import run_fresh as rf
        self.assertEqual(rf.verdict_for(passing_rows()["16x9"], "16x9", None)[0], rf.VERDICT_HOLD)

    def test_a_report_of_another_inventory_version_holds(self):
        rd = make_run(self.tmp, attest=False)
        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: d.__setitem__("inventory_version", 0))
        self.holds(rd, "old report")


class TestBytes(Base):
    def test_a_final_that_is_not_what_the_gates_measured_holds(self):
        rd = make_run(self.tmp, attest=False)
        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
            f.write(b"\0")                                # re-rendered after the gates ran
        att = self.holds(rd, "final changed between gates and attestation")
        self.assertIn("out/segment.mp4: not the bytes the gates measured", att["other_blockers"])

    def test_a_bound_file_changed_after_the_attestation_is_refused(self):
        for rel in RA.BOUND:
            rd = make_run(self.tmp)
            with open(os.path.join(rd, rel), "ab") as f:
                f.write(b" ")
            ok, why, _ = RA.authorise(rd)
            self.assertFalse(ok, rel)
            self.assertTrue(any(rel in w for w in why), (rel, why))

    def test_a_bound_file_deleted_after_the_attestation_is_refused(self):
        rd = make_run(self.tmp)
        os.remove(os.path.join(rd, "out", "segment_vertical.mp4"))
        self.assertFalse(RA.authorise(rd)[0])

    def test_check_file_before_each_send(self):
        rd = make_run(self.tmp)
        ok, _, att = RA.authorise(rd)
        self.assertTrue(ok)
        self.assertTrue(RA.check_file(rd, att, "out/segment.mp4"))
        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
            f.write(b"\0")
        self.assertFalse(RA.check_file(rd, att, "out/segment.mp4"))
        self.assertFalse(RA.check_file(rd, att, "out/not_bound.mp4"))


class TestPackAndRun(Base):
    def test_a_pack_without_vision_or_incomplete_or_missing_holds(self):
        for fn, label in ((lambda d: d.__setitem__("vision", False), "vision off"),
                          (lambda d: d.__setitem__("complete", "true"), "complete is a string"),
                          (lambda d: d.pop("complete"), "complete missing")):
            rd = make_run(self.tmp, attest=False)
            edit_json(os.path.join(rd, "VERIFY", "VERIFICATION.json"), fn)
            self.holds(rd, label)
        rd = make_run(self.tmp, attest=False)
        os.remove(os.path.join(rd, "VERIFY", "VERIFICATION.json"))
        self.holds(rd, "pack missing")

    def test_a_run_that_did_not_end_clean_is_never_authorised(self):
        rd = make_run(self.tmp, run_state={"ok": False, "why": ["provenance: FileNotFoundError"]})
        ok, why, att = RA.authorise(rd)
        self.assertEqual(att["verdict"], "HOLD")
        self.assertFalse(ok)
        rd = make_run(self.tmp, attest=False)
        RA.attest(rd, {"ok": "yes"})                     # a truthy non-bool is not ok
        self.assertFalse(RA.authorise(rd)[0])

    def test_a_replay_is_attested_but_never_deliverable(self):
        rd = make_run(self.tmp, attest=False)
        att = RA.attest(rd, {"ok": True, "why": []}, deliverable=False, why_not="replay")
        self.assertEqual(att["verdict"], "ALL_PASS")
        ok, why, _ = RA.authorise(rd)
        self.assertFalse(ok)
        self.assertTrue(any("not deliverable" in w for w in why), why)

    def test_no_or_corrupt_attestation_is_refused(self):
        rd = make_run(self.tmp, attest=False)
        self.assertFalse(RA.authorise(rd)[0])
        open(os.path.join(rd, "ATTESTATION.json"), "w").write("{not json")
        self.assertFalse(RA.authorise(rd)[0])
        rd = make_run(self.tmp)
        edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: d.__setitem__("schema", "pulse.attestation.v0"))
        self.assertFalse(RA.authorise(rd)[0])

    def test_an_attestation_edited_to_all_pass_is_refused(self):
        rows = passing_rows()
        rows["16x9"]["G3c_acoustic_tail"] = "FAIL"
        rd = make_run(self.tmp, rows=rows)
        edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: d.__setitem__("verdict", "ALL_PASS"))
        ok, why, _ = RA.authorise(rd)                   # the rows are re-checked, not the verdict trusted
        self.assertFalse(ok)
        self.assertTrue(any("G3c_acoustic_tail" in w for w in why), why)


class TestRunFreshWiring(Base):
    """run_fresh writes the attestation LAST and never gives two answers: holds anywhere => HOLD (GPT-cut F10)."""

    def run_obj(self, rd, holds=(), verdict=None, not_at_rev=()):
        import run_fresh as rf
        run = rf.Run(rd)
        run.status["verdict"] = verdict or rf.VERDICT_CANDIDATE
        run.status["holds"] = list(holds)
        run.prov["code"] = {"git_head": "abc", "pipeline_tree_clean_at_launch": True}
        run.prov["executed_code_not_at_revision"] = list(not_at_rev)
        return run

    def test_a_clean_candidate_is_attested_all_pass(self):
        import run_fresh as rf
        rd = make_run(self.tmp, attest=False)
        att = rf.attest_run(self.run_obj(rd))
        self.assertEqual(att["verdict"], "ALL_PASS", att["other_blockers"])
        self.assertTrue(RA.authorise(rd)[0])

    def test_a_hold_reason_makes_the_run_hold(self):
        import run_fresh as rf
        for kw in ({"holds": ["provenance: OSError: disk full"]}, {"not_at_rev": ["pipeline/gates.py (modified)"]}):
            rd = make_run(self.tmp, attest=False)
            run = self.run_obj(rd, **kw)
            att = rf.attest_run(run)
            self.assertEqual(att["verdict"], "HOLD", kw)
            self.assertEqual(run.status["verdict"], rf.VERDICT_HOLD, kw)
            self.assertFalse(RA.authorise(rd)[0], kw)

    def test_a_pipeline_module_loaded_from_anywhere_else_is_a_hold(self):
        """GPT audit (batch 16) #8: a first-party module NAME loaded from a directory whose path names neither
        protocol_pulse nor worktrees is still foreign code."""
        import importlib.util
        import run_fresh as rf
        d = tempfile.mkdtemp(prefix="alt_checkout_", dir=self.tmp)
        path = os.path.join(d, "backtest.py")
        open(path, "w").write("X = 1\n")
        spec = importlib.util.spec_from_file_location("backtest", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mods, why = rf.executed_code("HEAD", modules={"backtest": mod})
        self.assertEqual(mods, {})
        self.assertTrue(any("backtest from" in w and "outside this checkout" in w for w in why), why)
        mods, why = rf.executed_code("HEAD", modules={"json": json})      # the standard library is not ours
        self.assertEqual(why, [])
        # cycle-2 #7: a pipeline module from a path that LOOKS like a dependency directory is still foreign
        for part in ("site-packages", "dist-packages", "venv"):
            d = os.path.join(self.tmp, part, "x")
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, "backtest.py")
            open(path, "w").write("X = 2\n")
            spec = importlib.util.spec_from_file_location("backtest", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertTrue(rf.executed_code("HEAD", modules={"backtest": mod})[1], part)

    def test_the_verdict_follows_the_inventory_not_prefixes(self):
        import run_fresh as rf
        rows = passing_rows()
        self.assertEqual(rf.verdict_for(rows["16x9"], "16x9", RA.NO_EVIDENCE_CHECK)[0], rf.VERDICT_CANDIDATE)
        rows["16x9"]["G17_onset_tail"] = "PASS (looks fine)"
        v, bad = rf.verdict_for(rows["16x9"], "16x9", RA.NO_EVIDENCE_CHECK)
        self.assertEqual(v, rf.VERDICT_HOLD)
        self.assertIn("G17_onset_tail", bad)


ABSENT = object()


def vertical_fails():
    rows = passing_rows()
    rows["9x16"]["V1_visual_checklist"] = "FAIL"         # the 9:16 alone fails (the Blockware case, 2026-11-14)
    return rows


def sealed_run(parent, formats=ABSENT, rows=None, no_vertical=False):
    """make_run with the EDL's 'formats' set as run_fresh's pinned stage writes it (not attested)."""
    rd = make_run(parent, rows=rows, attest=False)
    if formats is not ABSENT:
        edit_json(os.path.join(rd, "edl.json"), lambda e: e.update(formats=formats))
    if no_vertical:                                      # a 16:9-only run need not have any 9:16 file at all
        for rel in RA.FORMAT_FILES["9x16"]:
            os.remove(os.path.join(rd, rel))
    return rd


class TestReleaseFormats(Base):
    """Ruling 93 as amended (orchestrator 2026-11-14 '21:10'): a clip whose source-burned captions the 9:16 crop cuts
    mid-word is 16:9-ONLY. The pin seals moments_package["formats"] = ["16x9"]; run_fresh's pinned stage writes it into
    the EDL; only the sealed formats decide, are bound and are sent. Must-fail: the same 9:16 failure with no sealed
    formats (or both sealed) HOLDS; a malformed value holds; formats changed after the attestation are refused."""

    def test_a_sealed_16x9_only_run_is_released_on_its_16x9_alone(self):
        for no_vertical in (False, True):
            rd = sealed_run(self.tmp, ["16x9"], vertical_fails(), no_vertical=no_vertical)
            att = RA.attest(rd, {"ok": True, "why": []})
            ok, why, _ = RA.authorise(rd)
            self.assertEqual(att["verdict"], "ALL_PASS", (no_vertical, att["blockers"], att["other_blockers"]))
            self.assertTrue(ok, why)
            self.assertEqual(att["formats"], ["16x9"])
            self.assertEqual(set(att["files"]), set(RA.BOUND) - set(RA.FORMAT_FILES["9x16"]))
            self.assertEqual(list(att["blockers"]), ["16x9"])

    def test_must_fail_the_same_9x16_failure_without_sealed_formats_holds(self):
        for formats in (ABSENT, ["16x9", "9x16"]):
            att = self.holds(sealed_run(self.tmp, formats, vertical_fails()), f"formats {formats}")
            self.assertIn("V1_visual_checklist", att["blockers"]["9x16"])
            self.assertEqual(att["formats"], ["16x9", "9x16"])

    def test_the_16x9_still_decides_and_binds_a_16x9_only_run(self):
        rows = vertical_fails()
        rows["16x9"]["G18_word_for_word"] = "FAIL"
        self.holds(sealed_run(self.tmp, ["16x9"], rows), "16x9 G18 FAIL")
        rd = sealed_run(self.tmp, ["16x9"], vertical_fails())
        self.assertEqual(RA.attest(rd, {"ok": True, "why": []})["verdict"], "ALL_PASS")
        with open(os.path.join(rd, "qa", "contact_sheet_16x9.jpg"), "ab") as f:
            f.write(b"x")
        self.assertFalse(RA.authorise(rd)[0])

    def test_a_malformed_formats_value_holds(self):
        for bad in (["9x16"], ["9x16", "16x9"], ["16x9", "16x9"], [], "16x9", None, {"16x9": True},
                    ["16x9", "9x16", "1x1"], [16]):
            att = self.holds(sealed_run(self.tmp, bad), repr(bad))
            self.assertTrue(any("release formats unreadable" in w for w in att["other_blockers"]), att["other_blockers"])

    def test_formats_changed_after_the_attestation_are_refused(self):
        rd = sealed_run(self.tmp, ["16x9"], vertical_fails())
        self.assertEqual(RA.attest(rd, {"ok": True, "why": []})["verdict"], "ALL_PASS")
        edit_json(os.path.join(rd, "edl.json"), lambda e: e.update(formats=["16x9", "9x16"]))
        ok, why, _ = RA.authorise(rd)
        self.assertFalse(ok)
        self.assertTrue(any("attested formats" in w for w in why), why)
        # an attestation edited to claim the 16:9 alone over an EDL that seals both
        rd = sealed_run(self.tmp, ABSENT, vertical_fails())
        RA.attest(rd, {"ok": True, "why": []})
        edit_json(os.path.join(rd, "ATTESTATION.json"),
                  lambda a: a.update(formats=["16x9"], verdict="ALL_PASS", blockers={"16x9": {}}))
        ok, why, _ = RA.authorise(rd)
        self.assertFalse(ok)
        self.assertTrue(any("attested formats" in w for w in why), why)
        self.assertTrue(any(w.startswith("9x16 V1_visual_checklist") for w in why), why)

    def test_package_formats_reads_only_the_two_sealed_sets(self):
        self.assertIsNone(RA.package_formats({"type": "moments"}))
        self.assertIsNone(RA.package_formats(None))
        self.assertEqual(RA.package_formats({"formats": ["16x9"]}), ["16x9"])
        self.assertEqual(RA.package_formats({"formats": ["16x9", "9x16"]}), ["16x9", "9x16"])
        for bad in (["9x16"], ["16x9", "16x9"], [], "16x9", None, ("16x9",), [16]):
            with self.assertRaises(ValueError, msg=repr(bad)):
                RA.package_formats({"formats": bad})


class TestRunFreshFormats(Base):
    """run_fresh: the pinned stage writes the sealed formats into the EDL (a malformed value is a rejected pin), and
    the run's verdict is decided by the released formats alone."""
    run_obj = TestRunFreshWiring.run_obj

    def pinned_stage(self, rd, mp):
        import pinned
        import run_fresh as rf
        pin = {"story_id": "s1", "label": "Blockware", "approved_by": "builder", "approved_at": "2026-11-14T22:00:00Z",
               "moments_package": mp}

        def fake_prepare(pin_path, run_dir, log=print):
            json.dump({"topic": "Blockware", "hook": {}, "clips": []}, open(os.path.join(run_dir, "edl.json"), "w"))
            return {"pin": pin, "pin_sha256": "0" * 64, "validation": {}}
        saved = pinned.prepare, rf.free_gpu0_for_whisper
        pinned.prepare, rf.free_gpu0_for_whisper = fake_prepare, (lambda run, stage, **kw: None)
        try:
            run = self.run_obj(rd)
            rf.stage_pinned(run, "pin.json")
            return run, json.load(open(os.path.join(rd, "edl.json")))
        finally:
            pinned.prepare, rf.free_gpu0_for_whisper = saved

    def test_the_pinned_stage_writes_the_sealed_formats_into_the_edl(self):
        import run_fresh as rf
        run, edl = self.pinned_stage(tempfile.mkdtemp(dir=self.tmp), {"type": "moments", "formats": ["16x9"]})
        self.assertEqual((edl["formats"], run.prov["release_formats"]), (["16x9"], ["16x9"]))
        run, edl = self.pinned_stage(tempfile.mkdtemp(dir=self.tmp), {"type": "moments"})
        self.assertNotIn("formats", edl)
        self.assertEqual(run.prov["release_formats"], ["16x9", "9x16"])
        with self.assertRaisesRegex(rf.Hold, "pinned decision rejected"):
            self.pinned_stage(tempfile.mkdtemp(dir=self.tmp), {"type": "moments", "formats": ["9x16"]})

    def test_the_run_verdict_is_decided_by_the_released_formats(self):
        import run_fresh as rf
        rows = vertical_fails()
        ev = {fmt: {k: {"executed": True, "samples": 3} for k in r} for fmt, r in rows.items()}
        for formats, want in ((["16x9"], rf.VERDICT_CANDIDATE), (ABSENT, rf.VERDICT_HOLD),
                              (["16x9", "9x16"], rf.VERDICT_HOLD), (["9x16"], rf.VERDICT_HOLD)):
            rd = sealed_run(self.tmp, formats, rows)
            run = self.run_obj(rd)
            rf.release_verdict(run, rows, ev)
            self.assertEqual(run.status["verdict"], want, formats)
            self.assertEqual(run.prov["verdicts"]["9x16"], rf.VERDICT_HOLD)     # always reported
            if want == rf.VERDICT_CANDIDATE:
                self.assertEqual(rf.attest_run(run)["verdict"], "ALL_PASS")
                self.assertTrue(RA.authorise(rd)[0])
            else:
                self.assertTrue(run.status["holds"], formats)
        rd = sealed_run(self.tmp, ["9x16"], passing_rows())                  # malformed: a hold, even all PASS
        run = self.run_obj(rd)
        rf.release_verdict(run, passing_rows(), {f: {k: {"executed": True, "samples": 3} for k in r}
                                                 for f, r in passing_rows().items()})
        self.assertEqual(run.status["verdict"], rf.VERDICT_HOLD)
        self.assertTrue(any("release formats unreadable" in h for h in run.status["holds"]), run.status["holds"])


if __name__ == "__main__":
    unittest.main()
