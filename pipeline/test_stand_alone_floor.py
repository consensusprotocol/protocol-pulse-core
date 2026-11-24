#!/usr/bin/env python3
"""Ruling 119 (1)'s calibrated floor at the render's validate, without a GPU: a canned scorer stands in for the model.
stand_alone_floor.apply runs after stand_alone.check_edl in run_fresh.stage_validate, and check_pin_only refuses a
malformed mark before a render.

MUST-FAIL on the old code: the builder seals a clip on the floor (3.0 <= score < 3.5, the pin marked), and validate
HOLDs it, because check_edl reads 3.5. With the floor, all of these must hold together:
  - only the marked segments are affected;
  - only an opener the scorer refused for its score alone is lifted;
  - only under the measured scorer code and weights, and only for the pin's own seal.
Everything else is unchanged, and a malformed mark is refused.

The stage-level tests use the REAL scorer code sha (stand_alone_scorer.scorer_sha over stand_alone.py and
story_semantics.py). If either file changes, the floor stops applying and those tests fail: the calibration must then
be measured again under the new code."""
import copy
import json
import re
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import edl_rules  # noqa: E402
import editorial_gate  # noqa: E402
import run_fresh  # noqa: E402
import stand_alone as SA  # noqa: E402
import stand_alone_floor as SF  # noqa: E402
import telegram  # noqa: E402,F401  (this tree's: check_pin_only puts the main tree's pipeline first on sys.path)

BASE = os.path.join(REPO, "references", "pulse_fresh_2026-11-13", "edl.json")    # the published 0c68b589 EDL
CODE, WEIGHTS = SF.MEASURED_SCORER_SHA, SF.MEASURED_DIGEST
NOTE_119 = "a clip passed stand-alone on the calibrated bar"                      # ruling 120's words
OFF_TOPIC = "But the weather in Paris was lovely this spring, and the cafes were full every night."


def good(places=(2,)):
    return {"note": NOTE_119, "floor": 3.0, "scorer_sha": CODE, "segments": list(places), "ruling": "119"}


def edl_with(clip2=None, hook=None, trim=None, clip1=None):
    with open(BASE) as f:
        e = json.load(f)
    if clip2 is not None:
        e["clips"][1]["text"] = clip2(e["clips"][1]["text"]) if callable(clip2) else clip2
    if clip1 is not None:
        e["clips"][0]["text"] = clip1(e["clips"][0]["text"])
    if hook is not None:
        e["hook"]["text"] = hook(e["hook"]["text"])
    if trim is not None:
        e["clips"][1].setdefault("selection_lock", {})["trimmed_leading"] = {"word": trim}
    return e


BUT = lambda t: "But " + t


def rate_of(score, fault="starts_mid_thought", asked=None, broken=False):
    def rate(ps):
        if asked is not None:
            asked.append([p["pid"] for p in ps])
        if broken:
            raise RuntimeError("clip scorer reply unparseable: canned")
        return {p["pid"]: (score, "canned", fault) for p in ps}
    return rate


ABSENT = object()                                                       # no stand_alone_bar key at all


def write_record(run_dir, edl, mark=ABSENT, record_sha=None, raw=None, n=3, flags=None):
    mp = {"type": "moments", "package_sha256": edl.get("moments_package_sha256") if record_sha is None else record_sha}
    if mark is not ABSENT:
        mp["stand_alone_bar"] = mark
    if flags is not None:                                     # the never-empty seal's review_flags (ruling 136 (2))
        mp["review_flags"] = flags
    with open(os.path.join(run_dir, "PINNED_DECISION.json"), "w") as f:
        f.write(raw if raw is not None else json.dumps({"mode": "pinned", "pin": {"segments": [{}] * n,
                                                                                   "moments_package": mp}}))


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="saf_")
        self.addCleanup(shutil.rmtree, self.d)

    def check(self, edl, score, mark=ABSENT, code=CODE, weights=WEIGHTS, record=True, broken=False):
        if record:
            write_record(self.d, edl, mark=mark)
        screen, _ = run_fresh.moments_screen(edl)
        sa = SA.check_edl(edl, rate=rate_of(score, broken=broken), screen=screen, moments=True)
        return SF.apply(sa, edl, self.d, scorer_sha=lambda: code, digest=lambda: weights)

    def row(self, sa, seg):
        return next(r for r in sa["rows"] if r["segment"] == seg)


class TestTheFloor(Base):

    def test_without_a_mark_a_floor_score_holds_as_before(self):
        sa = self.check(edl_with(clip2=BUT), 3.0)
        self.assertFalse(sa["ok"])
        self.assertIn("does not affirm it stands alone (3.0", self.row(sa, "clip_02")["opener"]["why"])
        self.assertNotIn("calibrated_floor", sa)

    def test_ruling_119_a_marked_clip_on_the_floor_is_affirmed_under_the_measured_scorer(self):
        for score in (3.0, 3.4):
            with self.subTest(score=score):
                sa = self.check(edl_with(clip2=BUT), score, mark=good([2]))
                self.assertTrue(sa["ok"], [r["opener"]["why"] for r in sa["rows"]])
                self.assertEqual(sa["calibrated_floor"]["applied"], ["clip_02"])
                self.assertEqual(sa["calibrated_floor"]["segments"], ["clip_02"])
                self.assertNotIn("not_applied", sa["calibrated_floor"])
                why = self.row(sa, "clip_02")["opener"]["why"]
                self.assertIn("calibrated floor (3.0)", why)
                self.assertIn(f"({score}, fault starts_mid_thought)", why)          # the scorer's own verdict kept

    def test_under_the_floor_it_holds_and_at_the_bar_it_needs_no_floor(self):
        for score, ok in ((2.0, False), (2.99, False), (1.0, False), (3.5, True), (4.0, True), (5.0, True)):
            with self.subTest(score=score):
                sa = self.check(edl_with(clip2=BUT), score, mark=good([2]))
                self.assertIs(sa["ok"], ok)
                self.assertEqual(sa["calibrated_floor"]["applied"], [])

    def test_only_the_marked_segments(self):
        both = edl_with(clip2=BUT, clip1=BUT)                            # clip_01 and clip_02 both asked
        for places, lifted in (([1], ["clip_01"]), ([2], ["clip_02"]), ([1, 2], ["clip_01", "clip_02"]), ([0], [])):
            with self.subTest(places=places):
                sa = self.check(copy.deepcopy(both), 3.0, mark=good(places))
                self.assertEqual(sa["calibrated_floor"]["applied"], lifted)
                self.assertIs(sa["ok"], lifted == ["clip_01", "clip_02"])
                for seg in ("clip_01", "clip_02"):
                    self.assertIs(self.row(sa, seg)["pass"], seg in lifted, seg)

    def test_only_under_the_measured_scorer_code_and_weights(self):
        for code, weights in ((CODE[:12], WEIGHTS), ("0" * 64, WEIGHTS), (None, WEIGHTS), (CODE, WEIGHTS[:12]),
                              (CODE, "f" * 64), (CODE, None), (CODE.upper(), WEIGHTS)):
            with self.subTest(code=str(code)[:14], weights=str(weights)[:14]):
                sa = self.check(edl_with(clip2=BUT), 3.0, mark=good([2]), code=code, weights=weights)
                self.assertFalse(sa["ok"])
                self.assertEqual(sa["calibrated_floor"]["applied"], [])
                self.assertIn("not the measured one", sa["calibrated_floor"]["not_applied"])
                self.assertIn("does not affirm", self.row(sa, "clip_02")["opener"]["why"])

    def test_a_failure_that_is_not_the_score_is_never_lifted(self):
        asked = []
        e = edl_with(hook=BUT)                                           # a hook on a conjunction: no scorer asked
        screen, _ = run_fresh.moments_screen(e)
        write_record(self.d, e, mark=good([0]))
        sa = SF.apply(SA.check_edl(e, rate=rate_of(3.0, asked=asked), screen=screen, moments=True), e, self.d,
                      scorer_sha=lambda: CODE, digest=lambda: WEIGHTS)
        self.assertFalse(sa["ok"])
        self.assertIn("nothing is heard before a hook", self.row(sa, "hook")["opener"]["why"])
        sa = self.check(edl_with(clip2=OFF_TOPIC), 3.0, mark=good([2]))     # the topic test is never touched
        self.assertFalse(sa["ok"])
        self.assertFalse(self.row(sa, "clip_02")["pass"])
        self.assertFalse(self.row(sa, "clip_02")["topic"]["pass"])
        sa = self.check(edl_with(clip2=BUT), 3.0, mark=good([2]), broken=True)   # no verdict at all: fail closed
        self.assertFalse(sa["ok"])
        self.assertTrue(sa["rate_error"])
        self.assertEqual(sa["calibrated_floor"]["applied"], [])

    def test_a_segment_refused_for_its_word_is_never_lifted_though_the_scorer_rated_it(self):
        """A trimmed segment is always put to the scorer, so a verdict in the floor's range exists. The opener still
        refuses it for its word (a hook on a conjunction) or its emptiness, not its score, and it stays refused."""
        so = edl_with(hook=lambda t: "So " + t)
        so["hook"].setdefault("selection_lock", {})["trimmed_leading"] = {"word": "And"}
        sa = self.check(so, 3.0, mark=good([0]))
        self.assertEqual(self.row(sa, "hook")["scorer"]["score"], 3.0)          # asked, and rated in the range
        self.assertIn("nothing is heard before a hook", self.row(sa, "hook")["opener"]["why"])
        self.assertFalse(self.row(sa, "hook")["opener"]["pass"])
        self.assertEqual(sa["calibrated_floor"]["applied"], [])
        self.assertFalse(sa["ok"])
        sa = self.check(edl_with(clip2="", trim="But"), 3.0, mark=good([2]))
        self.assertEqual(self.row(sa, "clip_02")["scorer"]["score"], 3.0)
        self.assertEqual(self.row(sa, "clip_02")["opener"], {"pass": False, "why": "empty segment"})
        self.assertEqual(sa["calibrated_floor"]["applied"], [])
        self.assertFalse(sa["ok"])

    def test_a_hook_on_a_third_person_pronoun_and_a_trimmed_clip(self):
        it = edl_with(hook=lambda t: "It is simple. " + t)               # ruling 94 (b): the scorer judges it
        sa = self.check(it, 3.0, mark=good([0]))
        self.assertTrue(sa["ok"], self.row(sa, "hook")["opener"]["why"])
        self.assertEqual(sa["calibrated_floor"]["applied"], ["hook"])
        for mark, ok in ((good([2]), True), (ABSENT, False)):            # ruling 33 part 2: a trimmed clip
            with self.subTest(marked=mark is not ABSENT):
                sa = self.check(edl_with(trim="But"), 3.0, mark=mark)
                self.assertIs(sa["ok"], ok, self.row(sa, "clip_02")["opener"]["why"])
                self.assertIn("trimmed", self.row(sa, "clip_02")["opener"]["why"])

    def test_a_malformed_mark_is_refused_never_read_in_part(self):
        g = good([2])
        bad = [dict(g, note="stand-alone affirmed"), dict(g, note=NOTE_119.upper()), dict(g, floor=2.5),
               dict(g, floor=True), dict(g, floor="3.0"), dict(g, floor=3.5), dict(g, scorer_sha=CODE[:12]),
               dict(g, scorer_sha="0" * 64), dict(g, ruling="118"), dict(g, ruling=119), dict(g, segments=[]),
               dict(g, segments=[3]), dict(g, segments=[-1]), dict(g, segments=[True]), dict(g, segments=[2, 2]),
               dict(g, segments="2"), dict(g, segments=[2.0]), dict(g, digest=WEIGHTS),
               {k: v for k, v in g.items() if k != "floor"}, None, [], NOTE_119, {}]
        for m in bad:
            with self.subTest(mark=m):
                write_record(self.d, edl_with(clip2=BUT), mark=m)
                with self.assertRaisesRegex(ValueError, "stand_alone_bar"):
                    self.check(edl_with(clip2=BUT), 3.0, record=False)
                with self.assertRaisesRegex(ValueError, "stand_alone_bar"):
                    SF.mark({"stand_alone_bar": m}, 3)

    def test_a_mark_on_another_package_or_an_unreadable_record_is_refused(self):
        for sha in ("cd" * 32, "", None):
            with self.subTest(record_sha=sha):
                e = edl_with(clip2=BUT)
                write_record(self.d, e, mark=good([2]))
                with open(os.path.join(self.d, "PINNED_DECISION.json")) as f:
                    rec = json.load(f)
                rec["pin"]["moments_package"]["package_sha256"] = sha
                with open(os.path.join(self.d, "PINNED_DECISION.json"), "w") as f:
                    json.dump(rec, f)
                with self.assertRaisesRegex(ValueError, "not the EDL's"):
                    self.check(e, 3.0, record=False)
        for raw in ("{not json", '{"mode": "pinned"}', '{"pin": []}', '{"pin": null}', "[]",
                    json.dumps({"pin": {"moments_package": {"stand_alone_bar": good([2])}, "segments": None}})):
            with self.subTest(raw=raw):
                write_record(self.d, edl_with(clip2=BUT), raw=raw)
                with self.assertRaisesRegex(ValueError, "cannot say"):
                    self.check(edl_with(clip2=BUT), 3.0, record=False)

    def test_no_pin_record_or_no_mark_changes_nothing(self):
        e = edl_with(clip2=BUT)
        screen, _ = run_fresh.moments_screen(e)
        sa = SA.check_edl(e, rate=rate_of(3.0), screen=screen, moments=True)
        before = copy.deepcopy(sa)
        self.assertEqual(SF.apply(sa, e, self.d, scorer_sha=lambda: CODE, digest=lambda: WEIGHTS), before)
        write_record(self.d, e)                                          # a record, no mark
        self.assertEqual(SF.apply(copy.deepcopy(before), e, self.d, scorer_sha=lambda: CODE,
                                  digest=lambda: WEIGHTS), before)
        for pin in ({"moments_package": {"type": "moments"}}, {"segments": "x"}, {}):   # no mark: nothing else read
            with self.subTest(pin=pin):
                write_record(self.d, e, raw=json.dumps({"mode": "pinned", "pin": pin}))
                self.assertEqual(SF.apply(copy.deepcopy(before), e, self.d, scorer_sha=lambda: CODE,
                                          digest=lambda: WEIGHTS), before)
        write_record(self.d, e, raw=json.dumps({"pin": {"moments_package": {"stand_alone_bar": good([2])}}}))
        with self.assertRaisesRegex(ValueError, "cannot say"):          # marked, but no segments to place it in
            SF.apply(copy.deepcopy(before), e, self.d, scorer_sha=lambda: CODE, digest=lambda: WEIGHTS)

    def test_the_medley_must_still_name_bitcoin(self):
        e = edl_with(hook=lambda t: "The halving cut new issuance in half again this year, and miners felt it.",
                     clip1=lambda t: "Sats are the unit people actually use when they save a little every week.",
                     clip2="But the hash rate keeps climbing to new records every single month.")
        sa = self.check(e, 3.0, mark=good([2]))
        self.assertEqual(sa["calibrated_floor"]["applied"], ["clip_02"])
        self.assertTrue(all(r["pass"] for r in sa["rows"]), [r["topic"]["why"] for r in sa["rows"]])
        self.assertFalse(sa["medley_names_bitcoin"]["pass"])                # ruling 34's medley rule still holds
        self.assertFalse(sa["ok"])


class TestStageValidate(unittest.TestCase):
    """run_fresh.stage_validate with its stand-alone check reached for real: the EDL rules, ruling 91 and the editorial
    gate stubbed to pass, the model a canned scorer, the weights' digest stubbed; the scorer code sha is the real one.
    No vertical_overrides.json is written, so reaching the layout step (FileNotFoundError on it) means the stand-alone
    check passed."""

    def run_stage(self, edl, mark=ABSENT, digest=WEIGHTS, score=3.0, rules=(True, []),
                  gate=None, rate=None, pin_flags=None):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "edl.json"), "w") as f:
                json.dump(edl, f)
            write_record(d, edl, mark=mark, flags=pin_flags)
            run = types.SimpleNamespace(dir=d, prov={})
            with mock.patch.object(edl_rules, "validate_edl", return_value=rules), \
                    mock.patch.object(edl_rules, "takeaway_value", return_value=(True, "stub")), \
                    mock.patch.object(run_fresh, "out_edges", return_value=[]), \
                    mock.patch.object(run_fresh, "our_line_faults", return_value=[]), \
                    mock.patch.object(editorial_gate, "run_gate", return_value=gate or {"verdict": "READY_FOR_RENDER",
                                                                                       "laws": {}}), \
                    mock.patch.object(SA, "clip_scorer", return_value=rate or rate_of(score)), \
                    mock.patch.object(SF, "running_digest", return_value=digest):
                try:
                    run_fresh.stage_validate(run)
                except run_fresh.Hold as h:
                    return f"HOLD: {h}", run.prov
                except FileNotFoundError as e:
                    if "vertical_overrides.json" in str(e):
                        return "passed the stand-alone check", run.prov
                    raise
            return "returned", run.prov

    def test_ruling_136_a_soft_edl_rule_flags_a_hard_or_unknown_one_holds(self):
        def rules(*failing):
            return False, [{"rule": r, "pass": False, "reason": f"{r} failed"} for r in failing]
        got, prov = self.run_stage(edl_with(), rules=rules("rule_r11", "rule_r9"))
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["There is more voiceover than allowed (one closing line and at most one bridge).",
                          "A clip might not end cleanly at the end of a sentence."])
        for hard in ("rule_r6", "rule_r2", "rule_r5", "rule_r7", "rule_r99"):        # credit, a passage twice, length,
            with self.subTest(rule=hard):                                           # layout, a rule no list names
                got, _ = self.run_stage(edl_with(), rules=rules(hard, "rule_r11"))
                self.assertTrue(got.startswith(f"HOLD: EDL rejected by edl_rules: {hard}"), got)

    def test_ruling_137_a_medley_not_about_bitcoin_still_holds_at_validate(self):      # HARD: the show's scope
        e = edl_with(hook=lambda t: "The halving cut new issuance in half again this year, and miners felt it.",
                     clip1=lambda t: "Sats are the unit people actually use when they save a little every week.",
                     clip2="But the hash rate keeps climbing to new records every single month.")
        got, prov = self.run_stage(e, mark=good([2]))
        self.assertTrue(got.startswith("HOLD: stand-alone/topic: medley"), got)
        self.assertNotIn("review_flags", prov)

    def test_ruling_138_a_rule_flag_names_its_clip_never_a_non_hook(self):
        got, prov = self.run_stage(edl_with(), rules=(False, [
            {"rule": "rule_r9", "pass": False,
             "reason": "R9 FAIL: clip_02: last word 'x' at 3.00s is not sentence-ending (no . ? !)"},
            {"rule": "rule_r1", "pass": False,
             "reason": "R1 FAIL (ruling 37): a question ending is refused for every non-hook clip: ['clip_1']"}]))
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["Clip 2 (Scott Melker) might not end cleanly at the end of a sentence.",
                          "Clip 1 (CNBC Television) ends on a question rather than a statement."])

    def test_ruling_138_no_stage_flag_carries_a_code(self):
        code = re.compile(r"\w_\w|\b[A-Z]{1,2}\d|ruling|\bL-[a-z]")
        e = edl_with()
        for t in [run_fresh.sentence(x, e, "clip_02") for x in run_fresh.EDL_SOFT.values()] + \
                list(run_fresh.LAW_TEXT.values()):
            self.assertIsNone(code.search(t), t)

    def test_ruling_141_the_flag_gives_the_scorers_reason_in_plain_words(self):
        said = lambda ps: {p["pid"]: (2.0, "Starts with 'But', implying a previous statement.", "starts_mid_thought")
                           for p in ps}
        got, prov = self.run_stage(edl_with(clip2=BUT), rate=said)
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["The clip (Scott Melker) may not stand alone: the clip scorer rated it 2 of 5 (Starts with "
                          "'But', implying a previous statement)."])

    def test_ruling_141_no_verdict_is_said(self):
        got, prov = self.run_stage(edl_with(clip2=BUT), rate=rate_of(3.0, broken=True))
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["The clip (Scott Melker) may not stand alone: the clip scorer did not answer."])

    def test_ruling_141_a_clip_the_pin_already_flags_is_said_once(self):
        e = dict(edl_with(clip2=BUT), moments_package_sha256="ab" * 32)
        pin = ["The clip (Scott Melker) may not stand alone: the clip scorer rated it 2 of 5, starts mid-thought"]
        got, prov = self.run_stage(e, pin_flags=pin)
        self.assertEqual(got, "passed the stand-alone check")
        self.assertNotIn("review_flags", prov)                        # the pin's sentence is the one PBX reads
        got, prov = self.run_stage(e, pin_flags=["The clip (CNBC Television) may not stand alone: rated 2 of 5"])
        self.assertEqual([f["flag"] for f in prov["review_flags"]],      # another clip's flag does not silence it
                         ["The clip (Scott Melker) may not stand alone: the clip scorer rated it 3 of 5 (canned)."])

    def test_ruling_141_the_opener_screens_own_words_carry_no_code(self):
        r = {"opener": {"why": "'but' trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)"}}
        self.assertEqual(run_fresh.alone_reason(r), "'but' trimmed and no clip-scorer verdict on the trimmed text")
        r = {"scorer": {"score": 2.0, "reason": "", "fault": "starts_mid_thought"}}
        self.assertEqual(run_fresh.alone_reason(r), "the clip scorer rated it 2 of 5 (starts mid thought)")
        r = {"scorer": {"score": 3.0, "reason": "Fault starts_mid_thought: opens on 'Now'.", "fault": "starts_mid_thought"}}
        self.assertEqual(run_fresh.alone_reason(r), "the clip scorer rated it 3 of 5 (Fault starts mid thought: opens on "
                                                    "'Now')")                  # Heimdall batch 107 c1 F2: its echo of a label

    def test_ruling_143_many_unsettled_small_words_add_one_flag(self):
        e = edl_with()
        e["clips"][1]["selection_lock"] = {"text": "x", "small_words_unsettled": 4}
        got, prov = self.run_stage(e)
        self.assertEqual(got, "passed the stand-alone check")
        self.assertIn("The clip (Scott Melker): the transcript and the audio readers differ on a few small words.",
                      [f["flag"] for f in prov.get("review_flags", [])])
        e["clips"][1]["selection_lock"]["small_words_unsettled"] = 3      # three: no flag
        got, prov = self.run_stage(e)
        self.assertFalse(any("audio readers differ" in f["flag"] for f in prov.get("review_flags", [])))

    def test_ruling_136_the_editorial_laws_flag(self):
        got, prov = self.run_stage(edl_with(), gate={"verdict": "HOLD", "laws": {
            "LAW_1_NEW_INFORMATION": {"pass": False}, "LAW_2_VO_HAS_A_JOB": {"pass": True}}})
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["The editorial check doubted that every clip adds something new."])

    def test_unmarked_a_floor_score_is_flagged_at_validate(self):            # rulings 136 / 137: SOFT (it held)
        got, prov = self.run_stage(edl_with(clip2=BUT))
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["The clip (Scott Melker) may not stand alone: the clip scorer rated it 3 of 5 (canned)."])

    def test_ruling_119_marked_it_passes_validate_with_the_record_in_provenance(self):
        got, prov = self.run_stage(edl_with(clip2=BUT), mark=good([2]))
        self.assertEqual(got, "passed the stand-alone check")
        self.assertEqual(prov["stand_alone"]["calibrated_floor"]["applied"], ["clip_02"])
        self.assertEqual(prov["stand_alone"]["calibrated_floor"]["scorer_sha"], CODE)   # the code on disk is measured

    def test_other_weights_flag_and_a_malformed_mark_holds(self):        # rulings 136 / 137: the floor not applied
        got, prov = self.run_stage(edl_with(clip2=BUT), mark=good([2]), digest="f" * 64)   # is a flag; a broken mark
        self.assertEqual(got, "passed the stand-alone check")                              # is a broken record: HARD
        self.assertEqual([f["flag"] for f in prov["review_flags"]],
                         ["The clip (Scott Melker) may not stand alone: the clip scorer rated it 3 of 5 (canned)."])
        self.assertIn("not the measured one", prov["stand_alone"]["calibrated_floor"]["not_applied"])
        got, prov = self.run_stage(edl_with(clip2=BUT), mark=dict(good([2]), floor=2.5))
        self.assertTrue(got.startswith("HOLD: stand-alone calibrated floor (ruling 119 (1)): stand_alone_bar"), got)
        got, prov = self.run_stage(edl_with(), mark=dict(good([2]), floor=2.5))     # refused even when unneeded
        self.assertTrue(got.startswith("HOLD: stand-alone calibrated floor (ruling 119 (1))"), got)


class TestCheckPinOnly(unittest.TestCase):
    """check_pin_only refuses a malformed stand-alone mark before a render, first and on its own (the builder's gates
    are not asked), and a good one changes nothing but the READY line, which names it. The mark sits outside the seal,
    so a sealed pin stays sealed with one added."""
    PUBLISHED = os.path.join(REPO, "references", "pulse_fresh_2026-11-13", "PIN.json")      # tracked; 3 segments
    SPOTLIGHT = "/home/ultron/protocol_pulse/data/moments_pins/SPOTLIGHT_PIN_230148.json"     # the frozen READY pin

    def check(self, path, mark):
        sys.path.insert(0, os.path.join(REPO, "scripts", "integrator"))
        import check_pin_only
        with open(path) as f:
            pin = json.load(f)
        if mark is not None:
            pin["moments_package"]["stand_alone_bar"] = mark
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "PIN.json")
            with open(p, "w") as f:
                json.dump(pin, f)
            return check_pin_only.main(p)

    def test_a_malformed_mark_is_refused_first(self):
        for m in (dict(good([2]), floor=2.5), good([3]), dict(good([2]), scorer_sha=CODE[:12]), dict(good([2]), x=1),
                  dict(good([2]), note="stand-alone affirmed"), None):
            with self.subTest(mark=m):
                ok, why = self.check(self.PUBLISHED, m if m is not None else "not a mark")
                self.assertFalse(ok)
                self.assertTrue(why.startswith("stand-alone calibrated floor mark: stand_alone_bar"), why)
        ok, why = self.check(self.PUBLISHED, good([2]))                # a good mark: the builder's verdict, unchanged
        self.assertEqual((ok, why), self.check(self.PUBLISHED, None))

    def test_a_good_mark_is_named_on_the_ready_line(self):
        base_ok, base = self.check(self.SPOTLIGHT, None)
        ok, why = self.check(self.SPOTLIGHT, good([0]))
        self.assertEqual(ok, base_ok)
        if base_ok:                                                     # READY under the builder's gates today
            self.assertIn(f"calibrated bars (rulings 115 (2) / 116 / 119): {NOTE_119}", why)
            self.assertNotIn(NOTE_119, base)
        else:                                                           # not READY: the mark changes nothing
            self.assertEqual(why, base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
