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
        calls, out = self.run_build(none, sealed, never_empty=True)
        self.assertEqual((calls, out["package"], out["never_empty"]["clean_why_none"]), ([False, True], {"p": 1}, "x"))
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
