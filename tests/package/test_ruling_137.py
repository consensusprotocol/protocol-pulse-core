#!/usr/bin/env python3
"""RULINGS 136 / 137 (orchestrator 11:00 / 11:05 ET Nov 17), STAGE 1: NEVER EMPTY for step A. A clean package first;
when the clean pass seals nothing, a second pass lets back the moments step A refused for SOFT codes only, each flagged
in plain words; the pin's step-A row says FLAGGED with them and moments_package carries them as review_flags (at most
3); a hard code, a held moment, a FLAGGED row on a hard gate never pass. Offline."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(REPO, "pipeline"), HERE]
import package as PK  # noqa: E402
import package_pin as PP  # noqa: E402
import proof_ledger as PLG  # noqa: E402

SINCERE = PK.flag_sentence("hook", "Scott Melker", "NOT_OWN_SINCERE")


def answer(**kw):
    a = {"backend": "b", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [],
         "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
    a.update(kw)
    return a


class TestTheNeverEmptyPool(unittest.TestCase):
    def test_soft_codes_come_back_flagged_and_nothing_else_does(self):
        ms = [{"moment_id": k} for k in ("s", "h", "x", "n", "c")]
        a_by = {"s": {}, "h": {}, "x": {}, "c": {}}                       # 'n' has no step-A answer on file
        fails = {"s": ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"], "h": ["REFERENT_OUTSIDE", "STALE_TIME"],
                 "x": [PK.HELD + " no verdict"], "n": ["NOT_OWN_SINCERE"], "c": []}
        clean, back = PK.cleared_pool(ms, a_by, fails)
        self.assertEqual((sorted(clean), back), (["c"], {}))              # the clean pass: as before
        both, back = PK.cleared_pool(ms, a_by, fails, soft=True)
        self.assertEqual(sorted(both), ["c", "s"])
        self.assertEqual(back["s"]["step_a_flags"], ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
        self.assertNotIn("step_a_flags", ms[0])                           # a copy: the pool's moment is untouched


class TestTheStepARow(unittest.TestCase):
    def base(self, **a):
        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"hook": answer(**a)},
                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
                    truth={"m": {"ok": True, "model": "s", "replayed": False, "edges": {"cuttable": True}}},
                    coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})

    def test_soft_codes_flag_only_in_the_never_empty_pass_and_a_hard_code_still_fails(self):
        self.assertEqual(PK.inventory(**self.base(), soft=True)["context_a"]["status"], "PASS")      # clean: PASS
        quoted = self.base(view="quoting_someone_else")
        self.assertEqual(PK.inventory(**quoted)["context_a"]["status"], "FAIL")                     # the clean pass
        row = PK.inventory(**quoted, soft=True, who={"hook": "Scott Melker"})["context_a"]
        self.assertEqual((row["status"], row["flags"], row["replayed"]), ("FLAGGED", [SINCERE], False))
        self.assertEqual(SINCERE, "The opening clip (Scott Melker): the checker doubted this is the speaker's own "
                                  "sincere view (they may be quoting someone or joking).")   # ruling 138 (3): no code
        stale = self.base(view="quoting_someone_else", time_ok="no")                               # a hard code too
        self.assertEqual(PK.inventory(**stale, soft=True)["context_a"]["status"], "FAIL")


class TestThePin(unittest.TestCase):
    def pk(self, **gates):
        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in PP.REQUIRED_GATES}
        g.update(gates)
        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
                              "speaker": {"name": "unknown", "role": None, "line": None, "basis": None, "why": "t",
                                          "people": [], "measured": True},
                              "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}

    def flagged(self, flags, gate="context_a", replayed=False):
        return {gate: {"status": "FLAGGED", "by": "x", "replayed": replayed, "n": 1, "flags": flags}}

    def test_a_flagged_soft_row_seals_with_its_review_flags(self):
        pin = PP.to_pin(self.pk(**self.flagged([SINCERE])), "r")
        mp = pin["moments_package"]
        self.assertEqual((mp["review_flags"], PP.review_problems(mp)), ([SINCERE], []))
        self.assertEqual(mp["package_sha256"], PP.pin_seal(pin))                     # the flags are sealed with the gates
        self.assertNotEqual(mp["package_sha256"], PP.to_pin(self.pk(), "r")["moments_package"]["package_sha256"])
        self.assertTrue(PP.review_problems(dict(mp, review_flags=["something else"])))   # not the sealed flags
        self.assertNotIn("review_flags", PP.to_pin(self.pk(), "r")["moments_package"])   # clean: absent

    def test_what_never_seals(self):
        for bad in (self.flagged([SINCERE], gate="exclusion"),                         # FLAGGED on a HARD gate
                    self.flagged([]), self.flagged([""]), self.flagged("not a list"),
                    self.flagged([SINCERE], replayed=True),
                    self.flagged(["one", "two", "three", "four"])):                    # over 3 (ruling 136 (2))
            with self.assertRaises(PP.PinRefused, msg=str(bad)):
                PP.to_pin(self.pk(**bad), "r")


class TestTheTwoPasses(unittest.TestCase):
    def run_build(self, clean_out, soft_out, **kw):
        calls = []

        def fake(*a, **k):
            calls.append(bool(k.get("soft")))
            return dict(soft_out if k.get("soft") else clean_out)
        with mock.patch.object(PK, "_build", side_effect=fake):
            out = PK.build("router", [], {}, None, log=lambda m: None, **kw)
        return calls, out

    def test_clean_first_then_the_never_empty_pass_within_the_day_limit(self):
        none, sealed = {"package": None, "why_none": "x"}, {"package": {"p": 1}}
        calls, out = self.run_build(sealed, sealed, never_empty=True)
        self.assertEqual((calls, "never_empty" in out), ([False], False))            # a clean package: one pass
        calls, out = self.run_build(none, dict(sealed, prescreen={"soft_back": {}}), never_empty=True)
        self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
        self.assertEqual(out["never_empty"]["soft_record"]["prescreen"], {"soft_back": {}})   # the soft pass's record
        calls, out = self.run_build(none, dict(none, why_none="y"), never_empty=True)
        self.assertEqual((calls, out["package"], out["never_empty"]["soft_why_none"]), ([False, True], None, "y"))
        self.assertEqual(self.run_build(none, sealed)[0], [False])                   # never_empty off: as before
        self.assertEqual(self.run_build(none, sealed, never_empty=True, soft=True)[0], [False, True])   # audit 1135
        #   C1 (qwen P2): a caller's soft never reaches the clean pass
        self.assertEqual(self.run_build(none, sealed, never_empty=True, flagged_today=PK.FLAGGED_DAY_MAX)[0], [False])


    def test_the_wrapper_forwards_only_what_the_search_takes(self):
        """audit 1135 C2 (gpt-oss, refuted): never_empty and flagged_today are the wrapper's keyword-only parameters,
        never forwarded; with _build's REAL signature (autospec) an unknown keyword would raise TypeError."""
        calls = []
        with mock.patch.object(PK, "_build", autospec=True,
                               side_effect=lambda *a, **k: calls.append(sorted(k)) or {"package": None}):
            PK.build("router", [], {}, None, log=lambda m: None, never_empty=True, flagged_today=1, lineups=3)
        self.assertEqual(calls, [["lineups", "log"], ["lineups", "log", "soft"]])


class TestStage2a(unittest.TestCase):
    """RULING 137 STAGE 2a: the second family's soft step-A refusals, and the re-screen's after the writes, flag like the
    first's (soft_codes); CUTTABLE's sentence-edge part flags (line 1 12:12 ET, default SOFT) while L-v 2's word check
    and every other edge failure stay hard. DataDash 8dbc30ee's real record (replayed 12:1x ET): IN runs on from
    'line:', 100 ms, the words match."""
    DATADASH = {"ok": True, "model": "elevenlabs_stt:scribe_v1", "replayed": False,
                "edges": {"in": {"ok": False, "word": "Bitcoin", "before": "line:", "pause_ms": 100,
                                 "why": "the recogniser runs on into the clip ('line:', 100 ms before it)"},
                          "out": {"ok": True, "word": "holdings.", "after": "The",
                                  "why": "a sentence ends at the clip's last word"}, "cuttable": False}}

    def test_soft_codes_and_the_second_family(self):
        self.assertEqual(PK.soft_codes(["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]), ["NOT_OWN_SINCERE", "REFERENT_OUTSIDE"])
        for f in (["REFERENT_OUTSIDE", "STALE_TIME"], [PK.HELD + " x"], [], None, ["SPEAKER_CHANGE"], ["RETRACTION"]):
            self.assertIsNone(PK.soft_codes(f), f)
        cleared = {"a": {"moment_id": "a"}, "b": {"moment_id": "b"}, "c": {"moment_id": "c"}, "d": {"moment_id": "d"}}
        got = PK.soft_second(cleared, {"a": [{}]}, {"b": ["REFERENT_OUTSIDE"], "c": ["STALE_TIME"], "d": [PK.HELD]})
        self.assertEqual(got, {"b": ["REFERENT_OUTSIDE"]})
        self.assertEqual((cleared["b"].get("step_a_flags"), "step_a_flags" in cleared["c"]), (["REFERENT_OUTSIDE"], False))

    def test_only_a_sentence_running_on_at_a_word_boundary_is_soft(self):
        import copy
        self.assertEqual(PK.soft_edges(self.DATADASH), ["EDGE_IN"])
        both = copy.deepcopy(self.DATADASH)
        both["edges"]["out"] = {"ok": False, "word": "x", "after": "y", "why": "the recogniser's sentence continues past the clip"}
        self.assertEqual(PK.soft_edges(both), ["EDGE_IN", "EDGE_OUT"])
        for why_in in ("the recogniser has no 'bitc' within 0.6 s of the clip's start", "no word timing from the recogniser",
                       "the window starts at the clip: no word before it",
                       "the recogniser does not hear the trimmed word 'And' right before the clip (ruling 33 part 2)"):
            t = copy.deepcopy(self.DATADASH)
            t["edges"]["in"]["why"] = why_in
            self.assertIsNone(PK.soft_edges(t), why_in)
        end = copy.deepcopy(self.DATADASH)
        end["edges"]["out"] = {"ok": False, "why": "the window ends at the clip: no word after it"}
        self.assertIsNone(PK.soft_edges(end))
        for bad in (dict(self.DATADASH, ok=False), dict(self.DATADASH, error="x"), dict(self.DATADASH, edges=None)):
            self.assertIsNone(PK.soft_edges(bad))

    def base(self, truth, a=None):
        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by={"clip_01": a or answer()},
                    exc={"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}},
                    truth={"m": truth}, coh_ok=True, coh={"backend": "b", "replayed": False, "measured": True})

    def test_the_rows_flag_with_the_clip_named(self):
        kw = dict(who={"clip_01": "DataDash"}, mids={"m": "clip_01"})
        self.assertEqual(PK.inventory(**self.base(self.DATADASH), **kw)["cuttable"]["status"], "FAIL")   # clean pass
        row = PK.inventory(**self.base(self.DATADASH), soft=True, **kw)["cuttable"]
        self.assertEqual((row["status"], row["flags"]), ("FLAGGED", [
            "The second clip (DataDash): the checker heard the sentence run on into the clip's first word, so it may "
            "start mid-sentence."]))
        hard = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], **{"in": {"ok": False, "why": "no word timing from the recogniser"}}))
        self.assertEqual(PK.inventory(**self.base(hard), soft=True, **kw)["cuttable"]["status"], "FAIL")
        ok = dict(self.DATADASH, edges=dict(self.DATADASH["edges"], cuttable=True, **{"in": {"ok": True, "why": "ok"}}))
        a = PK.inventory(**self.base(ok), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]}, **kw)["context_a"]
        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [                     # the second family's doubt
            "The second clip (DataDash): the checker thought it points back to something said before the clip starts."]))
        stale = PK.inventory(**self.base(ok, answer(time_ok="no")), soft=True, seg_flags={"clip_01": ["REFERENT_OUTSIDE"]},
                             **kw)["context_a"]
        self.assertEqual(stale["status"], "FAIL")                                   # a hard code still fails

    def test_the_pin_takes_a_flagged_sentence_edge_never_a_flagged_word_check(self):
        pk = TestThePin().pk(cuttable={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1, "flags": ["The second "
                                       "clip (DataDash): the checker heard the sentence run on."]})
        self.assertEqual(len(PP.to_pin(pk, "r")["moments_package"]["review_flags"]), 1)
        with self.assertRaises(PP.PinRefused):
            PP.to_pin(TestThePin().pk(second_pass={"status": "FLAGGED", "by": "x", "replayed": False, "n": 1,
                                                   "flags": ["a word differs"]}), "r")


class TestStage2bHookBar(unittest.TestCase):
    """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
    own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
    another rater or an unmeasured part stay hard, and the clean pass never opens it. The rigs' bar (conftest):
    scroll 3, alone 4, setup 3, rated by "xai:grok"."""

    def hm(self, sc, al, se, backend="xai:grok", mark=False):
        m = {"moment_id": "h1", "hook_rating": {"scroll": sc, "alone": al, "setup": se, "backend": backend}}
        return dict(m, hook_bar_soft=True) if mark else m

    def test_under_the_bar_in_plain_words_and_what_stays_hard(self):
        self.assertEqual(PK.hook_bar_under(self.hm(2, 5, 5)), "stopping the scroll 2 of 5, needs 3")
        self.assertEqual(PK.hook_bar_under(self.hm(2, 3, 2)), "stopping the scroll 2 of 5, needs 3; making sense on "
                         "its own 3 of 5, needs 4; setting up what follows 2 of 5, needs 3")
        for m in (self.hm(3, 4, 3), self.hm(2, 5, 5, backend="heimdall:qwen"), self.hm(None, 5, 5),
                  self.hm(True, 5, 5), {}, None):
            self.assertIsNone(PK.hook_bar_under(m), m)
        with mock.patch.object(PK, "_live_bar", lambda: (None, "no valid hook calibration")):
            self.assertIsNone(PK.hook_bar_under(self.hm(2, 5, 5)))

    def test_only_the_soft_pass_mark_opens_it(self):
        own = PK.hook_own(self.hm(2, 5, 5))
        self.assertEqual((own["passes"], "flagged" in own), (False, False))
        own = PK.hook_own(self.hm(2, 5, 5, mark=True))
        self.assertEqual((own["passes"], own["flagged"]), (True, "stopping the scroll 2 of 5, needs 3"))
        own = PK.hook_own(self.hm(2, 5, 5, backend="heimdall:qwen", mark=True))
        self.assertEqual((own["passes"], "flagged" in own), (False, False))         # another rater: hard
        own = PK.hook_own(self.hm(3, 4, 3, mark=True))
        self.assertEqual((own["passes"], "flagged" in own), (True, False))          # a pass is never flagged

    def rig(self, hooks, never_empty):
        import test_medley as TM
        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=hooks)
        r.build_kw = {"never_empty": never_empty}
        return r, r.run()

    UNDER = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # h: the best hook, under the bar

    def test_a_hook_under_the_bar_seals_flagged_only_in_the_never_empty_pass(self):
        _, clean = self.rig(self.UNDER, False)
        self.assertIsNone(clean["package"])
        self.assertIn("no hook in the pool", clean["why_none"])
        r, out = self.rig(self.UNDER, True)
        pk = out["package"]
        self.assertEqual([s["moment_id"] for s in pk["segments"]][0], "h")
        ch = pk["segments"][0].get("channel")
        want = [f"The opening clip ({ch}): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
                f"needs 3)."]
        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
        self.assertEqual(pk["gates"]["coherence"]["status"], "PASS")                 # flagged once, on its own row
        self.assertEqual(out["never_empty"]["stage"], "2b")
        self.assertEqual(list(out["prescreen"]["soft_hook_bar"])[0], "h")

    def test_a_mark_carried_in_is_never_read(self):
        import test_medley as TM
        ms = [dict(m, hook_bar_soft=True) for m in TM.TestBuildLoop.MS]      # the clean pass pops it with the rating
        r = TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=self.UNDER)
        r.build_kw = {"never_empty": False}
        self.assertIsNone(r.run()["package"])

    def test_the_medley_row_flags_only_in_the_soft_pass_and_only_on_a_passing_verdict(self):
        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
        med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": [],
               "hook_own": {"passes": True, "flagged": "stopping the scroll 2 of 5, needs 3"}}
        row = lambda ok, soft: PK.inventory(**TestStage2a().base(t), medley=(ok, med), soft=soft,
                                            who={"hook": "Scott Melker"})["medley"]
        self.assertEqual((row(True, True)["status"], row(True, True)["flags"]), ("FLAGGED", [
            "The opening clip (Scott Melker): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
            "needs 3)."]))
        self.assertEqual((row(True, False)["status"], "flags" in row(True, False)), ("PASS", False))
        self.assertEqual(row(False, True)["status"], "FAIL")

    def test_at_most_the_best_two_under_the_bar_open(self):
        r, out = self.rig({"h": (2, 5, 5), "x": (2, 5, 4), "y": (1, 5, 5), "z": (2, 5, 3)}, True)
        rec = out.get("prescreen") if out.get("package") else out["never_empty"]["soft_record"]["prescreen"]
        rated = (out.get("hook_pool") or out["never_empty"]["soft_record"]["hook_pool"])["ratings"]
        under = [m for m in ("h", "x", "z", "y") if m in rated]                       # hook_order: rating, then sum
        self.assertEqual(list(rec["soft_hook_bar"]), under[:PK.HOOK_SOFT_MAX])
        self.assertEqual(PK.HOOK_SOFT_MAX, 2)


class TestTheDayCount(unittest.TestCase):
    def test_counted_per_day_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "FLAGGED_DAY.json")
            self.assertEqual(PLG.flagged_today(p, day="D1"), 0)
            pin = {"story_id": "s1", "moments_package": {"review_flags": [SINCERE]}}
            PLG.record_flagged(pin, p, day="D1")
            PLG.record_flagged(dict(pin, story_id="s2"), p, day="D1")
            self.assertEqual((PLG.flagged_today(p, day="D1"), PLG.flagged_today(p, day="D2")), (2, 0))
            PLG.record_flagged(pin, p, day="D2")                                       # a new day starts afresh
            self.assertEqual(json.load(open(p))["pins"], [{"story_id": "s1", "review_flags": [SINCERE]}])


if __name__ == "__main__":
    unittest.main()
