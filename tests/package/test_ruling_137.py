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


class TestRuling141StandAloneSoft(unittest.TestCase):
    """RULING 141 (2): STAND_ALONE SOFT in the never-empty pass (the builder's half; the integrator's render already only
    flags an opener refusal and holds on the topic rule and the medley naming Bitcoin). A moment left out ONLY by the
    render's STAND_ALONE opener rule comes back as a clip, flagged "The clip (<channel>) may not stand alone: <reason>."
    (the integrator matches that prefix); it never opens; the topic rule, the hook's row, an unmarked clip and the medley
    naming Bitcoin stay hard."""

    def m(self, text, verdict=None):
        x = {"moment_id": "q", "text": text}
        return dict(x, scorer_verdict=dict(verdict, text_sha256=PK.text_sha(text))) if verdict else x

    def test_the_reason_in_plain_words(self):
        self.assertEqual(PK.stand_plain(self.m("But Bitcoin q x.")),
                         "it opens on 'but' and the clip scorer has no verdict for it")
        self.assertEqual(PK.stand_plain(self.m("And Bitcoin q x.", {"score": 2.0, "fault": "starts_mid_thought",
                                                                     "reason": "r"})),
                         "it opens on 'and' and the clip scorer rated it 2.0 of 5 (starts mid thought)")
        self.assertIsNone(PK.stand_plain(self.m("Bitcoin q x.")))
        with mock.patch("stand_alone.opener", lambda *a, **k: (False, "clip q (2.0, fault x_y) new wording")):
            self.assertEqual(PK.stand_plain(self.m("Bitcoin q x.")), "the clip scorer does not confirm it stands alone")
        self.assertTrue(PK.STAND_SOFT_PREFIX.format(channel="X").startswith("The clip (X) may not stand alone: "))

    def test_only_marked_clips_failing_only_the_opener_are_soft(self):
        segs = [{"moment_id": "h", "stand_soft": "why h"}, {"moment_id": "a", "stand_soft": "why a"},
                {"moment_id": "b"}]                                     # a mark on the hook never softens its row
        row = lambda seg, o, t=True: {"segment": seg, "pass": o and t, "opener": {"pass": o}, "topic": {"pass": t}}
        st = {"ok": False, "rows": [row("hook", True), row("clip_01", False), row("clip_02", True)],
              "medley_names_bitcoin": {"pass": True}}
        self.assertEqual(PK.stand_soft_rows(st, segs), {"clip_01": "why a"})
        for bad in ([row("hook", False), row("clip_01", False), row("clip_02", True)],      # the hook's own row
                    [row("hook", True), row("clip_01", False, False), row("clip_02", True)],   # its topic too
                    [row("hook", True), row("clip_01", False), row("clip_02", False)]):     # an unmarked clip
            self.assertIsNone(PK.stand_soft_rows(dict(st, rows=bad), segs), bad)
        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin={"pass": False}), segs))
        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin=None), segs))   # unmeasured: hard
        self.assertIsNone(PK.stand_soft_rows(dict(st, ok=True), segs))

    def rig(self, never_empty, carry=False):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), dict(pm("z", "C", 13.0), text="But Bitcoin z x."),
              dict(pm("w", "D", 13.0), text="But nothing here at all.")]   # w: the topic rule (ruling 34) too
        ms = [dict(m, stand_soft="carried in") for m in ms] if carry else ms
        r = TM.Rig(ms, ["h", "x", "z"], [(True, [], None, TM.Rig.LINE)], [None])
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass(self):
        clean = self.rig(False)
        self.assertIsNone(clean["package"])
        self.assertIn("z", clean["no_role"])                        # the clean pass: 2 channels, no paid verdict
        out = self.rig(True)
        pk = out["package"]
        segs = {s["moment_id"]: s for s in pk["segments"]}
        self.assertEqual((set(segs), pk["segments"][0]["moment_id"]), ({"h", "x", "z"}, "h"))   # never the hook
        want = [f"The clip ({segs['z']['channel']}) may not stand alone: it opens on 'but' and the clip scorer has no "
                f"verdict for it."]
        self.assertEqual((pk["gates"]["stand_alone"]["status"], pk["gates"]["stand_alone"]["flags"]), ("FLAGGED", want))
        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
        self.assertEqual(out["soft_stand"], {"z": "it opens on 'but' and the clip scorer has no verdict for it"})
        self.assertIn("w", out["no_role"])                              # the topic rule stays HARD: never back

    def test_a_mark_carried_in_is_never_read(self):
        self.assertIsNone(self.rig(False, carry=True)["package"])

    def test_the_line_up_rules_take_a_marked_clip_and_refuse_an_unmarked_one(self):
        from test_moments import pm
        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
        z = dict(pm("z", "C", 13.0), text="But Bitcoin z x.")
        segs = [h, pm("x", "B", 14.0), z]
        self.assertEqual(PK.lineup_ok(segs), (False, "the render's STAND_ALONE"))
        self.assertEqual(PK.lineup_ok([h, segs[1], dict(z, stand_soft="it opens on 'but'")]), (True, "ok"))

    def test_the_row_flags_only_in_the_soft_pass(self):
        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
        st = {"ok": False, "rows": [], "medley_names_bitcoin": {"pass": True}, "soft_rows": {"clip_02": "why z"}}
        row = lambda soft: PK.inventory(**TestStage2a().base(t), stand=st, soft=soft, who={"clip_02": "Yahoo Finance"})[
            "stand_alone"]
        self.assertEqual((row(True)["status"], row(True)["flags"]), (
            "FLAGGED", ["The clip (Yahoo Finance) may not stand alone: why z."]))
        self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))


class TestRuling141LineUpChain(unittest.TestCase):
    """RULING 141 (3), THE LINE-UP CHAIN, PHASE A, in the never-empty pass: a line-up refused ONLY by soft line-up gates
    (clip ratings under the clips-alone floor, joins past the one bridge, the question hook's first join) is KEPT, the
    search goes on (a clean line-up first), and when it runs out the best kept one is retried once ACCEPTING: its soft
    failures, and its clip ratings under coherence's own floor, become plain flags within the cap of 3. The through-line,
    the hook's own bar and every other L-y check stay HARD; the writes and the value verdict are untouched."""
    H = {"moment_id": "h", "text": "Bitcoin h x.", "hook_rating": {"scroll": 5, "alone": 5, "setup": 5, "backend": "xai:grok"}}
    X, Y = {"moment_id": "x", "text": "Bitcoin x x."}, {"moment_id": "y", "text": "Bitcoin y x."}

    def med(self, ratings=None, flagged=(), line="Nobody can change the rules of Bitcoin.", measured=True):
        labs = PK.labels(3)
        return {"measured": measured, "through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
                "flagged": [j for j in PK.joins(labs) if j in flagged], "floors": {"clip": 3}}

    def test_what_a_clips_alone_verdict_keeps(self):
        segs = [self.H, self.X, self.Y]
        self.assertEqual(PK.lineup_soft(segs, self.med({"clip_02": 2})),
                         {"weak": {"clip_02": 2}, "floor": 3, "soft_joins": [], "n": 1})
        two = self.med(flagged=("hook -> clip_01", "clip_01 -> clip_02"))
        self.assertEqual(PK.lineup_soft(segs, two)["soft_joins"], ["clip_01 -> clip_02"])     # the first keeps a bridge
        q = [dict(self.H, text="Is Bitcoin h x?"), self.X, self.Y]
        self.assertEqual(PK.lineup_soft(q, self.med(flagged=("hook -> clip_01",)))["soft_joins"], ["hook -> clip_01"])
        for bad in (self.med({"clip_02": 2}, line="none"), self.med({"clip_02": 2}, measured=False), self.med()):
            self.assertIsNone(PK.lineup_soft(segs, bad), bad)                  # the through-line stays hard
        under = dict(self.H, hook_rating=dict(self.H["hook_rating"], scroll=2))
        self.assertIsNone(PK.lineup_soft([under, self.X, self.Y], self.med({"clip_02": 2})))   # the hook's own bar
        self.assertIsNone(PK.lineup_soft(segs, dict(self.med(), clips={"hook": 5, "clip_01": 5})))   # unmeasured clip
        self.assertEqual(PK.seg_marks([dict(self.H), dict(self.X, step_a_flags=["REFERENT_OUTSIDE", "UNCERTAIN"]),
                                       dict(self.Y, edge_flags=["EDGE_IN"], stand_soft="why")]), 4)

    def test_what_coherence_accepts(self):
        segs = [self.H, self.X, self.Y]
        coh = {"measured": True, "hook_own": {"passes": True}, "through_line": "Nobody can change the rules of Bitcoin.",
               "clips": {"hook": 5, "clip_01": 2, "clip_02": 2}, "vo_point": 4, "floors": {"clip": 3, "vo_point": 3}}
        self.assertEqual(PK.coherence_soft(coh, segs, ("clip_02",)),
                         {"weak": {"clip_01": 2, "clip_02": 2}, "floor": 3, "n": 1})   # clip_02 is flagged already
        for bad in (dict(coh, vo_point=2), dict(coh, through_line="none"), dict(coh, measured=False),
                    dict(coh, hook_own={"passes": False}), dict(coh, clips={"hook": 5, "clip_01": 4, "clip_02": 4})):
            self.assertIsNone(PK.coherence_soft(bad, segs), bad)
        ans = lambda tl, vo: {"through_line": tl, "vo_point": vo}
        panel = lambda *a: dict(coh, panel={"answers": list(a)})
        self.assertIsNotNone(PK.coherence_soft(panel(ans("Nobody can change the rules here.", 4),
                                                     ans("Nobody can change the rules here.", 3), ans("none", 4)), segs))
        self.assertIsNone(PK.coherence_soft(panel(ans("none", 4), ans("none", 4),
                                                  ans("Nobody can change the rules here.", 4)), segs))   # no majority

    def rig(self, medleys, writes, never_empty=True, **kw):
        import test_medley as TM                            # the never-empty pass asks the angle writer again
        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], medleys, writes,
                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]}, **kw)
        r.build_kw = {"never_empty": never_empty}
        return r, r.run()

    WEAK = (False, [], {"clip_02": 2}, "Nobody can change the rules of Bitcoin.")

    def test_a_weak_clip_seals_flagged_only_in_the_never_empty_pass(self):
        _, clean = self.rig([self.WEAK] * 2, [], never_empty=False)
        self.assertIsNone(clean["package"])
        r, out = self.rig([self.WEAK] * 4, [None])
        pk = out["package"]
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])      # the best kept: retried
        ch = {s["label"]: s["channel"] for s in pk["segments"]}
        want = [f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
                f"needs 3."]
        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
                         (want, []))
        self.assertEqual(len(r.medley_calls), 4)                           # the retry read its cached verdict

    LINE = "Nobody can change the rules of Bitcoin."
    J2 = (False, ["hook -> clip_01", "clip_01 -> clip_02"], None, LINE)
    B = {"text": "First, why the rules hold.", "cites": ["x"], "why": "the next speaker's 'it' has no referent"}

    def test_joins_past_the_one_bridge_flag_and_the_first_keeps_its_bridge(self):
        _, out = self.rig([self.J2] * 8, [self.B])          # each pass: 2 line-ups and ruling 63's reorders
        pk = out["package"]
        ch = {s["label"]: s["channel"] for s in pk["segments"]}
        want = [f"Between the second clip ({ch['clip_01']}) and the third clip ({ch['clip_02']}): the checker could "
                f"not follow the jump."]
        self.assertEqual(pk["bridge"]["join"], "hook -> clip_01")            # the first flagged join: bridged
        self.assertEqual({g: (pk["gates"][g]["status"], pk["gates"][g].get("flags")) for g in ("medley", "ly_shape")},
                         {"medley": ("FLAGGED", want), "ly_shape": ("FLAGGED", want)})
        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
                         (want, []))                                         # one doubt, flagged once

    THREE = (False, ["hook -> clip_01", "clip_01 -> clip_02"], {"clip_01": 2, "clip_02": 2}, LINE)

    def test_three_flags_are_kept_and_a_fourth_never(self):
        _, out = self.rig([self.THREE] * 8, [self.B])
        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # 2 clips + 1 join: the cap
        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # + the hook under the bar: 4
        _, out = self.rig([self.THREE] * 8, [self.B], hooks=under)
        self.assertIsNone(out["package"])
        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])

    def test_a_clean_line_up_found_later_wins(self):
        ok = (True, [], None, self.LINE)
        r, out = self.rig([self.WEAK, self.WEAK, self.WEAK, ok], [None])
        pk = out["package"]
        self.assertEqual(([s["moment_id"] for s in pk["segments"]], pk["gates"]["medley"]["status"]),
                         (["h", "x", "z"], "PASS"))
        self.assertEqual(PP.review_flags_of(pk["gates"]), [])
        self.assertTrue([t for t in out["tried"] if t.get("kept")])          # kept, never needed

    def test_coherence_ratings_flag_only_for_the_accepted_candidate(self):
        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 5)])
        pk = out["package"]
        ch = {s["label"]: s["channel"] for s in pk["segments"]}
        alone = (f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
                 f"needs 3.")
        coh = (f"The second clip ({ch['clip_01']}): with the narration, the checker rated how much it supports the "
               f"point 2 of 5, needs 3.")
        self.assertEqual((pk["gates"]["coherence"]["status"], sorted(pk["gates"]["coherence"]["flags"])),
                         ("FLAGGED", sorted([coh, alone])))
        self.assertEqual(sorted(PP.review_flags_of(pk["gates"])), sorted([alone, coh]))   # clip_02 flagged once
        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 2)])   # the VO point too: today's path
        self.assertIsNone(out["package"])

    def test_a_question_hook_join_flags_with_no_bridge_at_the_question(self):
        import test_medley as TM
        ms = [dict(m, text="Is Bitcoin h x?") if m["moment_id"] == "h" else m for m in TM.TestBuildLoop.MS]
        q = (True, ["hook -> clip_01"], None, self.LINE)          # one flagged join: ruling 37 refuses it today
        r = TM.Rig(ms, ["h", "x", "y", "z"], [q] * 8, [None],
                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
        r.build_kw = {"never_empty": True}
        pk = r.run()["package"]
        ch = {s["label"]: s["channel"] for s in pk["segments"]}
        want = [f"Between the opening clip ({ch['hook']}) and the second clip ({ch['clip_01']}): the checker could not "
                f"follow the jump."]
        self.assertEqual((pk.get("bridge"), r.write_calls[-1][1]), (None, None))   # nothing written after the question
        self.assertEqual((pk["gates"]["ly_shape"]["status"], PP.review_flags_of(pk["gates"])), ("FLAGGED", want))

    def test_coherence_counts_one_doubt_per_clip_against_the_cap(self):
        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}     # the hook's flag: 1
        _, out = self.rig([self.WEAK] * 8, [None], hooks=under, coherences=[(False, 2, 5)])
        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # hook + clip_02 + clip_01: 3, not 4
        _, out = self.rig([self.J2] * 8, [self.B], hooks=under, coherences=[(False, 2, 5)])
        self.assertIsNone(out["package"])                  # hook + a join + 2 new weak clips: 4, over the cap

    def test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too(self):
        two = (False, [], {"clip_01": 2, "clip_02": 2}, self.LINE)   # [h, x, y]: y weak (1 flag), then [h, x, z]:
        r, out = self.rig([self.WEAK, two, self.WEAK, two], [None])  # x and z weak (2 flags); both kept
        self.assertEqual(sum(bool(t.get("kept")) for t in out["never_empty"]["soft_record"]["tried"]
                             if t.get("kept")) if not out.get("package") else len([t for t in out["tried"]
                                                                                  if t.get("kept")]), 2)
        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "y"])   # 1 flag, not 2
        import test_medley as TM
        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [self.WEAK] * 2, [None],
                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
        r.build_kw = {"never_empty": True, "lineups": 1}  # one judged line-up a pass: the budget ends first
        self.assertEqual([s["moment_id"] for s in r.run()["package"]["segments"]], ["h", "x", "y"])

    def test_the_rows_flag_only_in_the_soft_pass_and_only_on_a_passing_shape(self):
        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
        soft_med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": ["clip_01 -> clip_02"],
                    "hook_own": {"passes": True}, "soft": {"weak": {}, "floor": 3, "soft_joins": ["clip_01 -> clip_02"],
                                                           "n": 1}}
        coh = {"backend": "b", "replayed": False, "measured": True, "soft": {"weak": {"clip_01": 2}, "floor": 3, "n": 1}}
        who = {"hook": "A", "clip_01": "B", "clip_02": "C"}
        inv = lambda soft, shape: PK.inventory(**dict(TestStage2a().base(t), coh=coh), medley=(True, soft_med),
                                               shape=shape, soft=soft, who=who)
        g = inv(True, (True, []))
        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["FLAGGED"] * 3)
        g = inv(False, (True, []))
        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["PASS"] * 3)
        self.assertEqual(inv(True, (False, ["3 bridges"]))["ly_shape"]["status"], "FAIL")   # a hard L-y failure

    def test_no_through_line_is_never_kept(self):
        none = (False, [], {"clip_02": 2}, "none")
        _, out = self.rig([none] * 4, [None])
        self.assertIsNone(out["package"])
        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])


class TestRuling144TheOneException(unittest.TestCase):
    """RULING 144 (PBX 07:05 ET Nov 18): ONE build's 12 h window waived, named and logged. Its row is FLAGGED with the
    plain words, they open the review flags (the note's top line), and they never count toward the cap of 3."""
    EXC = "PBX exception Nov 18: these clips are older than 12 hours (allowed for this one video only)"

    def gates(self, n_content):
        g = {f"g{i}": {"status": "FLAGGED", "flags": [f"doubt {i}"], "by": "x", "replayed": False, "n": 1}
             for i in range(n_content)}
        g[PP.EXCEPTION_GATE] = {"status": "FLAGGED", "flags": [self.EXC], "by": "ruling 144", "replayed": False, "n": 3}
        return g

    def test_the_exception_reads_first_and_is_not_a_doubt(self):
        g = self.gates(3)
        self.assertEqual(PP.review_flags_of(g), [self.EXC, "doubt 0", "doubt 1", "doubt 2"])
        self.assertEqual(PP.content_flags(g), 3)
        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
        self.assertEqual(len(PP.review_problems({"gates": self.gates(4), "review_flags": PP.review_flags_of(
            self.gates(4))})), 1)                                           # a 4th DOUBT still refuses
        self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)

    def test_the_driver_takes_it_only_named_and_only_in_this_process(self):
        import proof_ledger as PLG
        pins = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
                for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]

        class Past(Exception):
            pass

        def stop(*a, **k):
            raise Past()
        saved = PP.WINDOW_H
        try:
            with mock.patch("sys.stderr"):
                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26"]), 2)            # 12 h as ever
                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "please"]), 2)
                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", "31", "--pbx-exception",
                                           "PBX exception x"]), 2)                                  # 30 h at most
            self.assertEqual(PP.WINDOW_H, saved)                               # nothing changed by a refusal
            with mock.patch.object(PLG, "delivered_pins", stop):
                with self.assertRaises(Past):
                    PLG.main(["--delivered", *pins, "--hours", "26", "--pbx-exception", "PBX exception x"])
            self.assertEqual(PP.WINDOW_H, 26.0)                                # this process: every 12 h check reads it
        finally:
            PP.WINDOW_H = saved


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
