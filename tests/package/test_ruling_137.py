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
from datetime import datetime, timezone
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
        self.assertEqual((row["status"], row["flags"], row["replayed"]), ("FLAGGED", [                   # RULING 157:
            "Our fact-checker raised soft doubts on these clips. On this video: the opener may not be giving its own "   # one
            "sincere view."], False))                                                                     # kind
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
        for f in (["REFERENT_OUTSIDE", "STALE_TIME"], [PK.HELD + " x"], [], None, ["SPEAKER_CHANGE"], ["RETRACTION"],
                  ["AD_READ"], ["AD_READ", "REFERENT_OUTSIDE"]):
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
        self.assertIsNone(PK.soft_edges(both))                     # RULING 162 (1): the OUT edge is HARD, always
        out_only = copy.deepcopy(both)
        out_only["edges"]["in"] = {"ok": True, "why": "a sentence ends before the clip"}
        self.assertIsNone(PK.soft_edges(out_only))
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
        self.assertEqual((a["status"], "flags" in a, sorted(a["info"]["referent_outside"])), (   # RULING 155 (2): the
            "PASS", False, ["clip_01"]))           # second family's doubt with no "changes the claim": information
        yes = answer(referents=[{"word": "that", "refers_to": "the drop", "inside": False, "changes_assertion": "yes"}])
        a = PK.inventory(**self.base(ok, yes), soft=True, **kw)["context_a"]
        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [                     # the claim changes and nothing
            "Our fact-checker raised soft doubts on these clips. On this video: DataDash refers to something said "
            "earlier."]))                                                                  # resolves it: RULING 157 (2)(a)
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


class TestRuling155FlagKinds(unittest.TestCase):
    """RULING 155 (1) (orchestrator 21:06 ET Nov 23): "THE CAP COUNTS KINDS OF FLAG, NOT CLIPS: the same soft code on
    several clips is ONE flag in PBX's note, written once with the clips named ... At most 3 KINDS per package,
    standing." Build 159's MicroStrategy line-ups carried REFERENT_OUTSIDE on nearly every clip."""
    WHO = {"hook": "Natalie Brunell", "clip_01": "Strategy", "clip_02": "Yahoo Finance"}
    MERGED = ("Three clips (Natalie Brunell, Strategy, Yahoo Finance): the checker thought each points back to "
              "something said before the clip starts.")
    SINCERE3 = ("The third clip (Yahoo Finance): the checker doubted this is the speaker's own sincere view (they may "
                "be quoting someone or joking).")

    YES = [{"word": "that", "refers_to": "the drop", "inside": False, "changes_assertion": "yes"}]

    def inv(self, seg_flags, referents=None):
        b = TestTheStepARow().base()
        b["a_by"] = {lb: answer(referents=self.YES if referents is None else referents) for lb in self.WHO}
        return PK.inventory(**b, soft=True, seg_flags=seg_flags, who=self.WHO)

    def test_one_code_on_several_clips_is_one_sentence_naming_them(self):
        a = self.inv({"hook": ["REFERENT_OUTSIDE"], "clip_01": ["REFERENT_OUTSIDE"],
                      "clip_02": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]})["context_a"]
        self.assertEqual((a["status"], a["flags"]), ("FLAGGED", [                # RULING 157 (2)(a) / (5): ONE kind,
            "Our fact-checker raised soft doubts on these clips. On this video: the opener refers to something said "
            "earlier; Strategy refers to something said earlier; Yahoo Finance may not be giving its own sincere view "
            "and refers to something said earlier."]))                         # every clip named, in play order
        a = self.inv({"hook": ["REFERENT_OUTSIDE"], "clip_01": ["REFERENT_OUTSIDE"],     # RULING 155 (2): no "yes"
                      "clip_02": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]}, referents=[])["context_a"]
        self.assertEqual((a["status"], a["flags"], sorted(a["info"]["referent_outside"])), ("FLAGGED", [
            "Our fact-checker raised soft doubts on these clips. On this video: Yahoo Finance may not be giving its "
            "own sincere view."], ["clip_01", "clip_02", "hook"]))                  # the referents: on the pin only
        self.assertEqual(PK.kind_sentences([("clip_01", "EDGE_OUT"), ("clip_02", "EDGE_OUT")], self.WHO),
                         ["Two clips (Strategy, Yahoo Finance): the checker heard the sentence carry on past each "
                          "clip's last word, so each may end mid-sentence."])   # the edges keep 155's one sentence

    def test_ruling_155_2_a_referent_flags_only_when_it_changes_the_claim_and_nothing_resolves_it(self):
        """RULING 155 (2) (orchestrator 23:42 ET Nov 23, adopted): REFERENT_OUTSIDE is information on the pin, out of
        the note and the cap, unless the checker says it changes what the clip asserts AND the package's context check
        (step C, the clip in its line-up with our lines) does not find the claim entailed."""
        maybe = [dict(self.YES[0], changes_assertion="uncertain")]
        a = self.inv({"clip_01": ["REFERENT_OUTSIDE"]}, referents=maybe)["context_a"]
        self.assertEqual((a["status"], "flags" in a, sorted(a["info"]["referent_outside"])), (   # every clip's step A
            "PASS", False, ["clip_01", "clip_02", "hook"]))                       # has the "uncertain" referent
        b = TestTheStepARow().base()
        b["a_by"] = {lb: answer(referents=self.YES) for lb in self.WHO}
        b["ctx_"] = dict(b["ctx_"], segments={"clip_01": {"C": {"entails": "yes"}}, "clip_02": {"C": {"entails": "no"}}})
        a = PK.inventory(**b, soft=True, who=self.WHO)["context_a"]            # every clip: the claim changes
        self.assertEqual((a["status"], a["flags"], sorted(a["info"]["referent_outside"])), ("FLAGGED", [
            "Our fact-checker raised soft doubts on these clips. On this video: the opener refers to something said "
            "earlier; Yahoo Finance refers to something said earlier."], ["clip_01"]))   # clip_01: the line-up
        #   resolves it (step C: entailed); the hook (no step C record) and clip_02 (not entailed) stay flags

    def gates(self):
        stand = [PK.STAND_SOFT_PREFIX.format(channel=c) + f"it opens on '{w}'." for c, w in zip(self.WHO.values(),
                                                                                                ("and", "so", "but"))]
        return {"context_a": {"status": "FLAGGED", "flags": [self.MERGED, self.SINCERE3]},
                "stand_alone": {"status": "FLAGGED", "flags": stand},       # one kind, said once per clip (prefix kept)
                "medley": {"status": "FLAGGED", "flags": ["The opening clip (Natalie Brunell): the checker rated it "
                                                          "under the hook bar (stopping the scroll 2 of 5, needs 3)."]}}

    def test_the_cap_counts_kinds(self):
        g = self.gates()
        self.assertEqual(PP.content_flags(g), 4)                     # REFERENT_OUTSIDE, NOT_OWN_SINCERE, STAND_ALONE, hook
        mp = {"gates": g, "review_flags": PP.review_flags_of(g)}
        self.assertIn("4 kinds of review flag, over 3", " ".join(PP.review_problems(mp)))
        g.pop("medley")
        self.assertEqual(PP.content_flags(g), 3)
        self.assertEqual(PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)}), [])
        per_clip = {"context_a": {"status": "FLAGGED", "flags": [   # the old per-clip sentences of one code: one kind
            "The second clip (A): the checker thought it points back to something said before the clip starts.",
            "The third clip (B): the checker thought it points back to something said before the clip starts."]}}
        self.assertEqual(PP.content_flags(per_clip), 1)

    def test_the_search_counts_a_referent_only_when_it_can_be_a_flag(self):
        """Audit 20261124_0101 F (qwen F3): the search reads the same step-A record as the pin's row (a_by): a clip whose
        only code is REFERENT_OUTSIDE and whose record says no referent changes the claim adds no kind (ruling 155 (2):
        it can only end as information); with a "yes", or with no record to read, it counts (the safe side)."""
        segs = [{"moment_id": "a", "step_a_flags": ["REFERENT_OUTSIDE"]}, {"moment_id": "b"}]
        no = {"a": answer(referents=[dict(self.YES[0], changes_assertion="uncertain")])}
        self.assertEqual((PK.seg_marks(segs, no), PK.seg_marks(segs, {"a": answer(referents=self.YES)}),
                          PK.seg_marks(segs)), (0, 1, 1))
        segs[0]["step_a_flags"] = ["REFERENT_OUTSIDE", "UNCERTAIN"]
        self.assertEqual(PK.seg_marks(segs, no), 1)                     # another code: the one step-A kind

    def test_the_line_up_search_counts_kinds_too(self):
        segs = [{"step_a_flags": ["REFERENT_OUTSIDE"]}, {"step_a_flags": ["REFERENT_OUTSIDE"], "stand_soft": True},
                {"step_a_flags": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"], "stand_soft": True,
                 "edge_flags": ["EDGE_OUT"]}, {"edge_flags": ["EDGE_OUT"]}]
        self.assertEqual(PK.seg_marks(segs), 3)        # step A (ONE kind, ruling 157 (5)), EDGE_OUT, STAND_ALONE


FAILING = 2


class TestRuling162NoPlainLines(unittest.TestCase):
    """RULING 162 (2) (orchestrator 07:45 ET Nov 24, from PBX's review of afd8977d: "my VO, which is literally just me
    saying all the clips that were featured, which is not a value added comment at all. Let's never do that again"):
    ruling 156's plain fallback lines are WITHDRAWN and their templates deleted; ruling 150 is REVERSED (the closing
    line's value grade is a requirement again); no line passing means NO closing line, with ONE flag. ITEM 2 (orchestrator
    09:35 ET Nov 24: "One write, one judge ... no retry loop") withdraws "up to 4 writes" for the closing line."""

    def test_the_templates_and_their_soft_rows_are_gone(self):
        for name in ("fallback_fields", "fallback_subject", "fallback_vo_soft", "FALLBACK_CLOSING", "FALLBACK_FLAG",
                     "VALUE_FLAG"):
            self.assertFalse(hasattr(PK, name), name)
        self.assertFalse({"fallback_line", "takeaway_value"} & PP.SOFT_GATES)
        self.assertIn("no_closing_line", PP.SOFT_GATES)
        self.assertEqual(PK.NO_LINE_FLAG, "No closing line: our writers did not produce one that adds value.")
        self.assertFalse(PP.flagged_ok("takeaway_value", {"status": "FLAGGED", "flags": ["The closing line may mostly "
                                                                                       "restate the clips."]}))

    def test_a_refused_closing_line_is_never_written_alone(self):
        """REPLACES 'a line is written alone three times after its write' (ruling 156 (1)'s up-to-4 writes, withdrawn for
        the closing line by ITEM 2, orchestrator 09:35 ET Nov 24: "One write ... no retry loop"): the four replies
        offered for the line alone are never asked for, no prompt tells a refusal, no verdict judges one."""
        import test_medley as TM
        T = TM.TestRuling66Amended()
        texts = [f"Nobody bends these rules, and that is exactly why they keep working for everyone who holds them {w}."
                 for w in ("anywhere", "everywhere", "still", "here")]             # 18 words each: the 39 s budget
        rig, out, seen, avoid = T.run_rig([T.failing()],
                                          [{"takeaway": {"text": x, "cites": []}} for x in texts], alone_ok=(False,) * 4)
        alone = [p for r, p in rig.prompts if r == "angle_write" and "Your takeaway was refused" in p]
        self.assertEqual((alone, seen, avoid, len(rig.write_calls)), ([], [], {}, 1))
        self.assertEqual(len(rig.router.answers["angle_write"]), 4)               # all four offered: none asked for
        self.assertIsNone(out["package"])

class TestStage2aAtTheLineUp(unittest.TestCase):
    """RULING 137 stage 2a, the line-up stage (build 164, 22:11 ET Nov 23): a clip whose CUTTABLE failure is only a
    sentence edge at a word boundary stays in the never-empty pass at the line-up's own per-clip check too (flagged by
    the inventory's cuttable row), as it already did in the pool; a hard edge failure still drops it. RULING 162 (1)
    (07:45 ET Nov 24): only the IN edge: an OUT edge that fails drops the clip in every pass."""
    def run_rig(self, why, never_empty=True, edge="in"):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        edges = {"cuttable": False, "in": {"ok": True, "why": "ok"}, "out": {"ok": True, "why": "ok"}}
        edges[edge] = {"ok": False, "why": why}
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2,
                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"]},
                   truths={"x": {"ok": True, "replayed": False, "model": "scribe_v1", "edges": edges}})
        if never_empty:
            r.build_kw = {"never_empty": True}
        return r.run()

    def test_a_soft_edge_stays_flagged_and_a_hard_one_drops(self):
        out = self.run_rig(PK.EDGE_SOFT["in"] + " ('line:', 100 ms before it)")
        self.assertIsNotNone(out["package"], out.get("why_none"))
        self.assertEqual(out["package"]["gates"]["cuttable"]["status"], "FLAGGED")
        hard = self.run_rig("the recogniser has no 'bitc' within 0.6 s of the clip's start")
        self.assertIsNone(hard["package"])
        self.assertIsNone(self.run_rig(PK.EDGE_SOFT["in"], never_empty=False)["package"])   # the clean pass: HARD

    def test_an_out_edge_that_runs_on_drops_the_clip_in_every_pass(self):
        """RULING 162 (1): the sentence carrying on past the clip's last word is never a flag again (build 167's
        opener, Simply Bitcoin 1cb16751, sealed with it as one)."""
        for never_empty in (True, False):
            out = self.run_rig(PK.EDGE_SOFT["out"] + " (the recogniser's next word)", never_empty, edge="out")
            self.assertIsNone(out["package"], never_empty)


class TestContextSoftDefault(unittest.TestCase):
    """The 21:36 ET Nov 23 question's default (no answer by 21:46): in the never-empty pass a context-integrity failure
    whose every violation is a step A SOFT code on a CLIP is step A's flag kind; anything else stays as ruled."""
    LABELS = {"hook", "clip_01", "clip_02"}
    VS = [{"slot": None, "segment": "hook", "rule": "CONDITION_OUTSIDE", "detail": "Friday"},
          {"slot": None, "segment": "clip_01", "rule": "REFERENT_OUTSIDE", "detail": "He"},
          {"slot": None, "segment": "clip_01", "rule": "NOT_OWN_SINCERE", "detail": "reading_aloud"}]

    def test_only_step_a_soft_codes_on_clips_soften(self):
        cx = {"ok": False, "measured": True, "violations": [dict(v) for v in self.VS]}
        self.assertEqual(PK.context_soft(cx, self.LABELS),
                         {"hook": ["CONDITION_OUTSIDE"], "clip_01": ["REFERENT_OUTSIDE", "NOT_OWN_SINCERE"]})
        for bad in ({"slot": None, "segment": "clip_02", "rule": "NOT_ENTAILED"},          # a VO-caused failure: HARD
                    {"slot": None, "segment": "clip_02", "rule": "STALE_TIME"},            # a hard step A code
                    {"slot": "takeaway", "segment": None, "rule": "REFERENT_OUTSIDE"},     # on OUR line: rewrite
                    {"slot": None, "segment": "-", "rule": "REFERENT_OUTSIDE"}):          # not a clip of the package
            self.assertIsNone(PK.context_soft(dict(cx, violations=cx["violations"] + [bad]), self.LABELS), bad)
        self.assertIsNone(PK.context_soft(dict(cx, measured=False), self.LABELS))          # no verdict: never soft
        self.assertIsNone(PK.context_soft({k: v for k, v in cx.items() if k != "measured"}, self.LABELS))   # absent
        self.assertIsNone(PK.context_soft(dict(cx, measured=None), self.LABELS))           # audit 2240 qwen F1
        ours = {"slot": "takeaway", "segment": "clip_01", "rule": "REFERENT_OUTSIDE"}       # on OUR line, at a clip
        self.assertIsNone(PK.context_soft(dict(cx, violations=cx["violations"] + [ours]), self.LABELS))   # verifier
        self.assertIsNone(PK.context_soft(dict(cx, violations=[]), self.LABELS))


class TestRuling159NothingRaisesTheCap(unittest.TestCase):
    """RULING 159 (3)(a) (orchestrator 23:42 ET Nov 23): the cap is 3 KINDS of flag on every pin and nothing raises it:
    the per-package kinds_cap row (Nov 23) and ruling 144's exception row with ruling 147's cap of 5 are removed."""
    def gates(self, n):
        return {f"g{i}": {"status": "FLAGGED", "flags": [f"Kind {i}."]} for i in range(n)}

    def problems(self, g):
        return PP.review_problems({"gates": g, "review_flags": PP.review_flags_of(g)})

    def test_a_cap_row_raises_nothing(self):
        self.assertEqual(self.problems(self.gates(3)), [])
        row = {"status": "PASS", "cap": 5, "why": "the orchestrator's default", "replayed": False, "n": 1}
        for g in (self.gates(5), dict(self.gates(5), kinds_cap=row)):
            self.assertEqual(PP.flags_cap(g), 3)
            self.assertIn("5 kinds of review flag, over 3", " ".join(self.problems(g)))

    def test_an_exception_row_is_refused_and_counts_as_a_kind(self):
        exc = {"status": "FLAGGED", "flags": ["PBX exception Nov 18: these clips are older than 12 hours"],
               "by": "ruling 144", "replayed": False, "n": 3}
        g = dict(self.gates(3), pbx_exception=exc)
        self.assertEqual([p for p in PP.gate_problems(g, required=()) if p.startswith("pbx_exception:")],
                         ["pbx_exception: FLAGGED without a soft gate and its plain flags (ruling 137)"])
        self.assertIn("4 kinds of review flag, over 3", " ".join(self.problems(g)))
        self.assertEqual(PP.review_flags_of(dict({"pbx_exception": exc}, **self.gates(1))),
                         [exc["flags"][0], "Kind 0."])                       # gate order: no row jumps the queue
        self.assertEqual(PP.review_flags_of(dict(self.gates(1), pbx_exception=exc)), ["Kind 0.", exc["flags"][0]])


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
        own = PK.hook_own(self.hm(2, 5, 5, backend="heimdall:qwen", mark=True))   # RULING 154 (2) (was hard under
        self.assertEqual((own["passes"], own["flagged"], own["unrated"]), (       # 137 2b): rated OFF the bar opens,
            True, "a stand-in model rated it, not the hook bar's own rater", True))   # flagged, in the never-empty pass
        own = PK.hook_own(self.hm(2, 5, 5, backend="heimdall:qwen"))
        self.assertEqual((own["passes"], "flagged" in own), (False, False))         # unmarked (the clean pass): hard
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

    def test_an_original_comes_back_beside_its_trim_variant(self):
        """Build 147 (09:05 ET Nov 18): the trim variant of Natalie Brunell feb4b72f failed ruling 33's trimmed cut and
        the original, which needs no trim, had been kept out by it. The come-back no longer reads the trims at all."""
        from test_moments import pm
        ms = [dict(pm("a", "N", 9.6), text="And Bitcoin a x."), dict(pm("b", "Y", 9.6), text="But nothing here.")]
        no_role = {"a": "opener", "b": "opener; topic"}
        got = PK.stand_soft_back(ms, no_role, True)
        self.assertEqual(list(got), ["a"])                        # the topic refusal (b) stays out
        self.assertEqual(PK.stand_soft_back(ms, no_role, False), {})
        import inspect
        self.assertNotIn("trims", inspect.signature(PK.stand_soft_back).parameters)

    def test_in_a_build_an_original_comes_back_when_its_trim_variant_fails_its_cut(self):
        """RULING 159 (3)(a), the verifier's row 3: the come-back at BUILD level. z opens on 'But' (the opener rule keeps
        it out); its 'But'-trimmed variant is affirmed by the clip scorer but fails ruling 33's trimmed cut (HARD). The
        never-empty pass brings the original back, flagged, and seals on it; the old bug (an affirmed variant kept its
        original out) leaves two channels and no package."""
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), dict(pm("z", "C", 13.0), text="But Bitcoin z x.")]
        v = dict(ms[2], moment_id="z~trim", text="Bitcoin z x.", trimmed_leading="But", untrimmed_start=0.0,
                 trimmed_from="z")
        with mock.patch.object(PK, "trim_variant", lambda m, sources: v if m["moment_id"] == "z" else None):
            r = TM.Rig(ms, ["h", "x", "z"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, trim_fail={"z~trim"},
                       verdicts={"z~trim": TM.fv("Bitcoin z x.", 4.0)})   # ruling 56: the scorer affirms the trim
            r.build_kw = {"never_empty": True}
            out = r.run()
        self.assertEqual(out["trimmed"], {"z": "z~trim"})
        self.assertTrue(out["prescreen"]["trim_cut"]["z~trim"].startswith("FAIL: the trimmed word"))
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([s["moment_id"] for s in pk["segments"]][0], "h")
        self.assertEqual({s["moment_id"] for s in pk["segments"]}, {"h", "x", "z"})        # the original, not z~trim
        self.assertEqual(pk["gates"]["stand_alone"]["flags"], [
            "The clip (C) may not stand alone: it opens on 'but' and the clip scorer has no verdict for it."])
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])

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
                                       dict(self.Y, edge_flags=["EDGE_IN"], stand_soft="why")]), 3)   # 157 (5)

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


class TestRuling154UnratedOpener(unittest.TestCase):
    """RULING 154 (2) (orchestrator 20:36 ET Nov 23): in the never-empty pass the hook bar is soft; an UNRATED opener
    opens, flagged (build 157 and the verifier's Nov 23 drill: three openers 'NOT RATED: same vendor as the text it
    judges', no hook, no package). The clean pass: no hook, no package, as before."""
    SAME = ("ProviderError: coherence_verdict: every back-end unavailable: [('xai:grok-4.20-0309-reasoning', 'same "
            "vendor as the text it judges (xai): skipped')]")

    def run_rig(self, never_empty, err=SAME, hooks=None):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, hook_err=err, hooks=hooks)
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_an_unrated_opener_opens_flagged_only_in_the_never_empty_pass(self):
        self.assertIsNone(self.run_rig(False)["package"])
        out = self.run_rig(True)
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(pk["segments"][0]["moment_id"], "h")
        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", [
            "The opening clip (A): no checker rated it on the hook bar (its only rater wrote our lines)."]))
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
        self.assertEqual(PP.review_problems({"gates": pk["gates"], "review_flags": PP.review_flags_of(pk["gates"])}), [])
        soft = out["never_empty"]["soft_record"]["prescreen"]["soft_hook_bar"]
        self.assertEqual(len(soft), 2)                                    # HOOK_SOFT_MAX openers at most
        down = self.run_rig(True, err="ProviderError: coherence_verdict: every back-end unavailable: HTTP 503")
        self.assertIn("(its rater did not answer).", down["package"]["gates"]["medley"]["flags"][0])

    def test_a_hook_under_the_bar_by_its_own_rater_still_goes_first(self):
        out = self.run_rig(True, err=None, hooks={"h": (2, 2, 2), "x": (2, 2, 2), "y": (2, 2, 2)})
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertIn("the checker rated it under the hook bar", pk["gates"]["medley"]["flags"][0])


class TestAcceptanceItem5SelfRating(unittest.TestCase):
    """THE ACCEPTANCE TEST, ITEM 5 (orchestrator 08:50 ET Nov 24; the verifier's row 10): "The opener rating: when the
    same vendor wrote the angle, the rating is marked and never clears the bar silently." With every Heimdall family
    down, Grok writes the angle AND is the hook bar's only rater: ruling 154 (1)'s stand-in step 3 is Grok itself. Its
    rating carries the stand-in mark, is never cached as an ordinary rating, never opens in the clean pass, and opens
    only FLAGGED in the never-empty pass."""
    SELF = {"step": 3, "judge": "xai:grok", "why": "same vendor as the text it judges (xai): skipped"}

    def run_rig(self, never_empty, marked=True):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2)
        rate = r.rate_hooks
        r.rate_hooks = lambda *a, **k: ({mid: dict(v, **({"lx_soft": dict(self.SELF)} if marked else {}))
                                         for mid, v in rate(*a, **k)[0].items()}, None)
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_it_never_clears_the_bar_silently(self):
        self.assertIsNotNone(self.run_rig(False, marked=False)["package"])     # control: the bar's own rater, unmarked
        self.assertIsNone(self.run_rig(False)["package"])                      # the clean pass: never opens
        out = self.run_rig(True)
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))                          # the never-empty pass: opens, FLAGGED
        self.assertEqual(pk["gates"]["medley"]["status"], "FLAGGED")
        self.assertIn("standing in for itself", pk["gates"]["medley"]["flags"][0])
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])

    def test_the_rating_is_marked_and_never_cached(self):
        import json as J
        import tempfile
        import types

        class R:
            backends = {"xai:grok": types.SimpleNamespace(vendor="xai", family="grok")}

            def chain(self, role, kind=None):
                return ["xai:grok"]

            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                r = types.SimpleNamespace(text=J.dumps({"hooks": {"h": {"scroll": 5, "alone": 5, "setup": 5,
                                                                         "why": "w"}}}),
                                          backend="xai:grok", replayed=False, lx_soft=dict(TestAcceptanceItem5SelfRating.SELF))
                return r

            def reject(self, r, why=""):
                return False
        from test_moments import pm
        m = pm("h", "A", 12.0)
        with tempfile.TemporaryDirectory() as d:
            cache = d + "/HOOK_CACHE.json"
            import test_medley as TM
            got, err = PK.hook_ratings(R(), [m], TM.ctx(), {"heimdall"}, {"qwen"}, cache=cache)
            self.assertIsNone(err)
            self.assertEqual(got["h"]["lx_soft"]["step"], 3)                   # marked
            stored = J.load(open(cache)) if __import__("os").path.exists(cache) else {}
            self.assertEqual(stored, {})                                       # never cached as an ordinary rating
        marked = dict(m, hook_rating=got["h"])
        self.assertFalse(PK.hook_own(marked)["passes"])                        # the clean pass: never on the bar
        soft = dict(marked, hook_bar_soft=True)
        own = PK.hook_own(soft)
        self.assertEqual((own["passes"], own.get("unrated")), (True, True))    # the never-empty pass: flagged
        self.assertIn("standing in for itself", own["flagged"])
        plain = dict(m, hook_rating={k: v for k, v in got["h"].items() if k != "lx_soft"})
        self.assertTrue(PK.hook_own(plain)["passes"])                          # the same rating unmarked: on the bar


class TestRuling154OneJudgeFlag(unittest.TestCase):
    """RULING 154 (1) / 152 (2): every check of the package a stand-in judge made (its verdict marked "lx_soft" by the
    router or by the coherence panel's extra seats) is named in ONE flag (one kind); none: no row."""
    LX = {"step": 1, "judge": "heimdall:deepseek", "why": "same vendor as the text it judges"}

    def test_one_flag_naming_every_stand_in_check(self):
        base = TestTheStepARow().base()
        self.assertNotIn("judge", PK.inventory(**base, soft=True))
        base["fid"] = dict(base["fid"], lx_soft=self.LX)
        base["ctx_"] = dict(base["ctx_"], lx_soft={"C": self.LX})
        base["coh"] = dict(base["coh"], lx_soft=self.LX)
        base["a_by"] = {"hook": dict(base["a_by"]["hook"], lx_soft=self.LX)}
        g = PK.inventory(**base, soft=True, who={"hook": "Simply Bitcoin"})
        self.assertEqual((g["judge"]["status"], g["judge"]["flags"]), ("FLAGGED", [
            "Some checks were made by a stand-in model, because the usual checker wrote our lines or did not answer: "
            "the fact check of our lines; the context check; the coherence check; step A's check of the opening clip "
            "(Simply Bitcoin)."]))
        self.assertEqual(PP.flagged_ok("judge", g["judge"]), True)                 # a soft gate: the pin takes it
        self.assertEqual(PP.content_flags({"judge": g["judge"]}), 1)               # ONE kind

    def panel(self, answers, lx):
        import providers as P
        import test_medley as TM
        M = TM.TestRuling130CoherencePanel.M
        DS, GE, GL, X = ("heimdall:deepseek/deepseek-v4.1-flash", "heimdall:google/gemma-4-31b-it",
                         "heimdall:z-ai/glm-5.3-flash", "xai:grok-4.20-0309-reasoning")
        FAM = dict(TM.TestRuling130CoherencePanel.FAM, **{DS: "deepseek", GE: "gemma", GL: "glm", X: "grok"})
        calls = []

        class R:
            config = {"roles": {"coherence_panel": {"chain": M, "seeds": [7, 8], "min_members": 3, "deadline_s": 900}}}
            backends = {n: type("B", (), {"vendor": ("heimdall/" if n != X else "") + FAM[n], "family": FAM[n],
                                          "gateway": "heimdall" if n != X else "xai"})() for n in FAM}
            chains = {"angle_write": [M[0], DS, M[2], GE, M[1], GL, X]}
            down = {}
            lx_soft = lx

            def chain(self, role, kind=None):
                return list(self.chains.get(f"{role}:{kind}") or (M if role == "coherence_panel" else []))

            def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
                     avoid_family=None, deadline_s=None, kind=None):
                left = [n for n in self.chain(role, kind) if FAM[n] not in set(avoid_family or ())]
                if not left:
                    raise P.ProviderError(f"{role}: every back-end unavailable")
                calls.append(left[0])
                a = (answers.get(left[0]) or {}).get(seed)
                if a is None:
                    raise P.ProviderError(f"{left[0]}: no answer")
                return P.Reply(json.dumps(a), left[0], "heimdall")
        ok, v = PK.coherence(R(), TM.TestCoherenceHookRatedOnce.PK_, {"xai"}, writer_family={"qwen"},
                             hook=TM.TestCoherenceHookRatedOnce.HOOK)
        return ok, v, calls, (M, DS, GE)

    def test_the_panel_fills_the_seat_the_writer_emptied_only_in_the_never_empty_pass(self):
        import test_medley as TM
        G = TM.TestRuling130CoherencePanel.GOOD
        every = {n: {7: G, 8: G} for n in TM.TestRuling130CoherencePanel.M + ["heimdall:deepseek/deepseek-v4.1-flash",
                                                                                "heimdall:google/gemma-4-31b-it"]}
        ok, v, calls, (M, DS, GE) = self.panel(every, False)
        self.assertFalse(ok)
        self.assertIn("no verdict", v["error"])                       # two members off the writer: as ruled 118 (2)
        ok, v, calls, (M, DS, GE) = self.panel(every, True)
        self.assertTrue(ok, v)
        self.assertEqual((v["panel"]["stand_in"], v["lx_soft"]["judge"]), ([DS], DS))   # the next family, by name
        self.assertNotIn(GE, calls)                                   # only until enough members answered
        self.assertNotIn(M[0], calls)                                 # never the writer's family
        missing = {n: a for n, a in every.items() if n != DS}
        ok, v, calls, _ = self.panel(missing, True)                   # deepseek does not answer: gemma sits
        self.assertEqual(v["panel"]["stand_in"], [GE])


class TestRuling154TheMarkReachesTheRecords(unittest.TestCase):
    """RULING 154 (1): a stand-in judge's mark (Reply.lx_soft) reaches the verdict records the pin's one flag reads:
    the fact check of our lines (vo_fidelity.check) and step A (context_integrity.step_a)."""
    LX = {"step": 2, "judge": "heimdall:qwen", "why": "same vendor as the text it judges"}

    def test_the_fact_check_and_step_a_keep_the_mark(self):
        import providers as P
        import vo_fidelity as VF
        import context_integrity as CI
        import test_gates as TG
        import test_ruling_102 as T102
        lx = self.LX

        class Marked(TG.Canned):
            def call(self, *a, **k):
                r = TG.Canned.call(self, *a, **k)
                r.lx_soft = dict(lx)
                return r
        TF = TG.TestFidelityVerdict()
        claims = [TF.claim("intro", TF.LINES[0]["text"], "attribution", support=[
            {"segment": "m1", "words": "found support at its 200-day moving average"}])]
        for marked in (True, False):
            r = (Marked if marked else TG.Canned)(fidelity_verdict=[{"claims": claims}])
            res = VF.check(r, TF.SEGS, TF.LINES, writer_vendor="openai", writer_family="gpt")
            self.assertEqual(res.get("lx_soft"), lx if marked else None)

        class R:
            def __init__(self, marked):
                self.marked = marked

            def call(self, role, prompt, *a, **k):
                return P.Reply(T102.answer(prompt), "heimdall:qwen", "heimdall/qwen",
                               **({"lx_soft": dict(lx)} if self.marked else {}))
        ctxs = {"hook": {"text": "Bitcoin held its 200-day average, he said.", "channel": "A"}}
        for marked in (True, False):
            a_by, _ = CI.step_a(R(marked), ctxs, {"xai"})
            self.assertEqual(a_by["hook"].get("lx_soft"), lx if marked else None)

    def test_the_coherence_and_value_verdicts_keep_the_mark(self):
        import test_gates as TG
        import test_medley as TM
        lx = self.LX

        def canned(marked, **answers):
            r = TG.Canned(**answers)
            inner = r.call

            def call(*a, **k):
                out = inner(*a, **k)
                if marked:
                    out.lx_soft = dict(lx)
                return out
            r.call = call
            return r
        C = TM.TestCoherenceHookRatedOnce
        V = TM.TestTakeawayValueVerdict
        for marked in (True, False):
            _, v = PK.coherence(canned(marked, coherence_verdict=[C().reply()]), C.PK_, {"xai"}, hook=C.HOOK)
            self.assertEqual(v.get("lx_soft"), lx if marked else None)
            val = PK.takeaway_value(canned(marked, coherence_verdict=[V.YES]), V.SEGS, TM.ctx(), V.LINE, {"xai"},
                                    {"grok"})
            self.assertEqual(val.get("lx_soft"), lx if marked else None)


class TestRuling107UnmeasuredIsUndone(unittest.TestCase):
    """The verifier's other finding (Nov 23): its drill measured no word check (every download blocked), recorded '0
    items left undone', and the identical re-run was refused as NOTHING NEW. A build whose L-v 2 checks, hook onsets or
    trimmed cuts were NOT MEASURED left that work undone (ruling 107 (1)), in either pass."""
    def test_an_unmeasured_check_is_work_left_undone(self):
        clean = {"prescreen": {"second_pass": {"a": "PASS", "b": "L-v 2 FAIL"}, "hook_onset": {"a": "PASS"}}}
        self.assertEqual(PLG.open_work(clean, {}), 0)
        for k, v in (("second_pass", "NOT MEASURED: no audio"), ("hook_onset", "NOT MEASURED: no word timing"),
                     ("trim_cut", "NOT MEASURED: no trimmed-cut record")):
            self.assertEqual(PLG.open_work({"prescreen": {k: {"a": v}}}, {}), 1, k)
        soft = {"prescreen": {}, "never_empty": {"soft_record": {"prescreen": {"second_pass": {"c": "NOT MEASURED: x"}}}}}
        self.assertEqual(PLG.open_work(soft, {}), 1)
        for bad in ({"prescreen": {"second_pass": "x"}}, {"never_empty": "x"}, {"never_empty": {"soft_record": 3}},
                    {"prescreen": {}, "never_empty": {"soft_record": {"prescreen": ["x"]}}}):
            self.assertEqual(PLG.open_work(bad, {}), 0, bad)                     # audit H (qwen F1): never a crash


class TestRuling159NoExceptionSwitch(unittest.TestCase):
    """RULING 159 (3)(a): ruling 144's one-build exception switch is removed: the driver has no --pbx-exception, refuses
    --hours over 12 before it reads anything, and asks pp-ingest's adapter on the render clock with its --hours."""
    PINS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
            for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]

    def test_no_switch_and_no_wider_window(self):
        saved = PP.WINDOW_H
        with mock.patch("sys.stderr"), mock.patch.object(PLG, "delivered_pins", side_effect=AssertionError("read")):
            for h in ("26", "30", "12.5"):
                self.assertEqual(PLG.main(["--delivered", *self.PINS, "--hours", h]), 2, h)
            with self.assertRaises(SystemExit) as cm:                       # argparse: no such option
                PLG.main(["--delivered", *self.PINS, "--hours", "26", "--pbx-exception", "PBX exception x"])
            self.assertEqual(cm.exception.code, 2)
        self.assertEqual(PP.WINDOW_H, saved)

    def test_the_adapter_is_asked_on_the_render_clock(self):
        seen = []

        class Past(Exception):
            pass

        def rows(since, now, horizon_h=None, **k):
            seen.append((now, horizon_h))
            raise Past()
        for extra, want_h in (([], 12.0), (["--hours", "6"], 6.0)):
            with tempfile.TemporaryDirectory() as d:              # one folder a run: a run's folder is never reused
                os.makedirs(os.path.join(d, "proof"))
                with mock.patch.object(PLG, "HERE", d), \
                        mock.patch.object(PLG, "REGISTRY", os.path.join(d, "proof", "CANDIDATES.json")), \
                        mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []), \
                        mock.patch.object(PLG.LB, "rows", rows), mock.patch("sys.stdout"):
                    t0 = datetime.now(timezone.utc)
                    with self.assertRaises(Past):
                        PLG.main(["--delivered", *self.PINS, *extra])
            now, h = seen[-1]
            self.assertAlmostEqual((now - t0).total_seconds(), 0.0, delta=60)
            self.assertEqual(h, want_h)
        self.assertEqual(PP.WINDOW_H, 12.0)


class TestRuling150ValueSoft(unittest.TestCase):
    """RULING 150 REVERSED by RULING 162 (2) (07:45 ET Nov 24): the closing line's value grade is a requirement again,
    in every pass, never a flag. A loss is told to the next write; after the four writes, no line (here no no-voice
    line-up exists: 39 s of clips and nothing to add, so no package). TICKER: the show's own ticker (ruling 146 (1))."""
    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
              "covers_speaker": False}

    def run_rig(self, measured=True, never_empty=True, ticker=True):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        lost = {"adds": "yes", "no_restate": "no", "why": "it restates the clips"} if measured else {"measured": False}
        kw = {"visuals": {"x": {"burned_in": [dict(self.TICKER)]}}} if ticker else {}
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
                   values=[dict(lost) for _ in range(6)], follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]},
                   lines=TM.TestRuling91MedleyHalf.ALONE, **kw)
        if never_empty:
            r.build_kw = {"never_empty": True}
        return r, r.run()["package"]

    def test_a_measured_loss_is_never_a_flag(self):
        r, pk = self.run_rig()
        self.assertIsNone(pk)                                      # losses: no line; no no-voice line-up exists
        self.assertTrue(r.value_calls)                             # the value grade was asked, and never flagged

    def test_the_clean_pass_never_takes_it(self):
        _, pk = self.run_rig(never_empty=False, ticker=False)      # reaches the value gate: HARD
        self.assertIsNone(pk)

    def test_no_verdict_stays_hard(self):
        _, pk = self.run_rig(measured=False)
        self.assertIsNone(pk)


class TestRuling161SponsorOnlySeenIsInformation(unittest.TestCase):
    """RULING 161 (orchestrator 07:36 ET Nov 24, from PBX 07:28; it replaces ruling 158 (2)): a clip whose frames only
    SHOW sponsor material (the Kraken banner, filed by the check as a 'ticker') plays in any pass and any format, with
    no flag: the pin names it as information on the segment ("visible_sponsor_graphics", sealed); a plain price ticker
    in the same place is ruled as before (16:9 only, flagged: ruling 146 (1)). HARD as always: the clip's OWN WORDS
    in an ad ('this episode is sponsored by'), and a clip that is part of an ad read (Natalie Brunell 6e79ceaa, the
    first line of The Bitcoin Way's read)."""
    KRAKEN = {"kind": "ticker", "text": "TRADE CRYPTOS & STOCKS IN 190+ COUNTRIES KRAKEN $25 SIGN UP BONUS",
              "whole_in_16x9": True, "in_9x16": "whole", "covers_speaker": False}
    LISTED = [{"text": "TRADE CRYPTOS & STOCKS IN 190+ COUNTRIES - KRAKEN - $25 SIGN UP BONUS",   # question 5's own
               "what": "Kraken crypto exchange ($25 sign-up bonus offer)"}]                      # listing (DAN, Nov 23)
    BRUNELL = ("If your Bitcoin can be frozen or monitored by an exchange, a custodial provider, or anyone else, it's "
               "not yours.")                                    # 6e79ceaa8e76f34f4117 (RsCi56hEriU, 1590.9-1597.2 s)

    def run_rig(self, item, never_empty=True, listed=None, flags=None):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None] * 2,
                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]},
                   visuals={"x": {"burned_in": [dict(item)], **({"advertising": listed} if listed else {}),
                                  **({"flags": flags} if flags else {})}})
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_a_sponsor_banner_plays_named_where_a_plain_ticker_flags(self):
        import package_pin
        import test_medley as TM
        for never_empty in (False, True):                       # the clean pass too: no refusal, no flag
            out = self.run_rig(self.KRAKEN, never_empty, self.LISTED)
            pk = out["package"]
            self.assertIsNotNone(pk, out.get("why_none"))
            x = next(sg for sg in pk["segments"] if sg["moment_id"] == "x")
            self.assertIn("Kraken crypto exchange", x["visible_sponsor_graphics"])
            self.assertNotIn("graphics", pk["gates"])           # never ruling 146 (1)'s flag, never 16:9 only
            self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
            self.assertTrue(all("Kraken" not in f and "SIGN UP" not in f
                                for f in package_pin.review_flags_of(pk["gates"])))
            self.assertEqual([sg.get("visible_sponsor_graphics") for sg in pk["segments"] if sg["moment_id"] != "x"],
                             [None, None])
        stale = self.run_rig(dict(self.KRAKEN), True, self.LISTED,
                             flags=[{"kind": "burned_in", "text": self.KRAKEN["text"], "item": "ticker",
                                     "in_9x16": "whole"}])["package"]      # a record that carries an older rule's flag
        xs = next(sg for sg in stale["segments"] if sg["moment_id"] == "x")
        self.assertEqual(xs["visual"]["flags"], [])                        # sealed under today's rules (C2 F4)
        self.assertEqual(stale["gates"]["visual"]["flags"], [])
        pin = package_pin.to_pin(TM.spk(pk), "test")              # sealed on the pin's segment
        seg = next(sg for sg in pin["segments"] if sg["video_id"] == x["video_id"] and sg["start"] == x["start"])
        self.assertIn("Kraken crypto exchange", seg["visible_sponsor_graphics"])
        mp = pin["moments_package"]
        self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"],
                                          mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
        bare = [{k: v for k, v in sg.items() if k != "visible_sponsor_graphics"} for sg in pin["segments"]]
        self.assertNotEqual(package_pin.seal(bare, mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
                                             mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
        pk = self.run_rig(TestRuling150ValueSoft.TICKER)["package"]
        self.assertIsNotNone(pk)
        self.assertEqual(pk["gates"]["graphics"]["status"], "FLAGGED")      # the show's own graphics: 16:9 only

    def test_the_inventory_passes_and_names_it(self):
        import visual_pin as VP
        clean = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [], "on_screen_text": [],
                 "lower_third": {"name": None, "text": None}, "advertising": [], "backend": "b", "replayed": False}
        base = TestTheStepARow().base()
        row = PK.inventory(**base, visual=[clean, clean])["visual"]
        self.assertEqual((row["status"], row.get("sponsor_info")), ("PASS", None))
        ad = dict(clean, burned_in=[dict(self.KRAKEN)], advertising=self.LISTED)
        row = PK.inventory(**base, visual=[clean, ad], soft=True)["visual"]
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(len(row["sponsor_info"]), 1)
        self.assertIn("clip_01: visible sponsor graphics: Kraken crypto exchange", row["sponsor_info"][0])

    def test_sponsor_words_in_the_clip_and_an_ad_read_still_refuse(self):
        import context_integrity as CI
        keep = {"risks": [], "about_bitcoin": "yes", "why": "x"}
        for soft in (False, True):
            v, calls = TestRuling146SponsorBefore().verdict(
                "This episode is sponsored by BitKey, the simplest way to hold your own Bitcoin.", "", soft, keep)
            self.assertEqual((v["verdict"], v["backend"], v["risks"], calls), ("exclude", "deterministic",
                                                                                 ["ad_read"], []), soft)
        ad = {"risks": ["ad_read"], "about_bitcoin": "yes", "why": "the opening line of The Bitcoin Way's read"}
        v, _ = TestRuling146SponsorBefore().verdict(self.BRUNELL, TestRuling146SponsorBefore.BEFORE, True, ad)
        self.assertEqual(v["verdict"], "exclude")                                 # the exclusion model: HARD
        x = {"view": "ad_read", "own_sincere": False, "excerpt": self.BRUNELL}
        self.assertIn("AD_READ", CI.a_failures(x))                                # step A: HARD, never soft
        self.assertIsNone(PK.soft_codes(CI.a_failures(x)))


class TestRuling159NoPlainLinesForARefusedLineUp(unittest.TestCase):
    """Found building RULING 158 (2) (00:4x ET Nov 24), a bug in ruling 156 (2)'s code: the plain fallback lines came
    whenever the write count was spent in the never-empty pass, and a line-up the render's lock HOLDS, whose frames the
    visual check refuses, or that got NO lock verdict is re-lined by setting that count with no write made: the plain
    lines then sealed the refused line-up. Now they come only after real writes failed."""

    def run_rig(self, lock=None, visuals=None):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, lock_check=lock,
                   visuals=visuals, follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
        r.build_kw = {"never_empty": True}
        return r.run()

    def test_a_lock_hold_no_lock_verdict_or_refused_frames_never_seal(self):
        import test_medley as TM
        self.assertIsNotNone(self.run_rig(lock=TM.lock_stub())["package"])            # control: the lock passes
        for kw in ({"lock": TM.lock_stub({"x": ("hold", None)})}, {"lock": TM.lock_stub(error=True)},
                   {"visuals": {"x": {"measured": False, "why": "no contact sheet"}}}):
            out = self.run_rig(**kw)
            self.assertIsNone(out["package"], kw)                                    # x is the third channel
            soft = (out.get("never_empty") or {}).get("soft_record") or {}
            self.assertFalse([t for t in soft.get("tried") or [] if t.get("fallback_line")], kw)   # never built


class TestRuling159AdReadIsHard(unittest.TestCase):
    """RULING 159 (3)(a) (orchestrator 23:42 ET Nov 23): "a clip that is the first line of an ad read (Natalie Brunell
    6e79ceaa) must be REFUSED, not softened to 'may not be sincere': step A calling the surrounding read an ad read is
    HARD for the clip." Fixture: Grok's recorded step-A answer of Nov 13 on the BitKey read ('Bitkey is a self-custody
    hardware wallet ...'), two clips of it 'ad_read'."""
    REPLY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures/replies/2e/2e30fa9200a5120e497bee643af8a2370039600a6411e3ca4648fbcb0a9a1807.json")

    def test_the_recorded_ad_read_is_a_hard_code(self):
        import context_integrity as CI
        with open(self.REPLY) as f:
            items = json.loads(json.load(f)["text"])["excerpts"]
        ads = [x for x in items if x.get("view") == "ad_read"]
        self.assertEqual(len(ads), 2)
        for x in ads:
            f = CI.a_failures(x)
            self.assertIn("AD_READ", f)
            self.assertNotIn("NOT_OWN_SINCERE", f)
            self.assertIsNone(PK.soft_codes(f))                               # never back in the never-empty pass
        quoted = dict(ads[0], view="attributed")
        self.assertIn("NOT_OWN_SINCERE", CI.a_failures(quoted))              # another view: soft, as before

    def run_rig(self, codes):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2,
                   a_fail={("xai", "y"): codes})
        r.build_kw = {"never_empty": True}
        return r.run()

    def test_in_a_build_an_ad_read_clip_never_comes_back(self):
        self.assertIsNotNone(self.run_rig(["NOT_OWN_SINCERE"])["package"])     # soft: back, flagged
        out = self.run_rig(["AD_READ"])
        self.assertIsNone(out["package"])                                       # HARD: y stays out (third channel)
        self.assertNotIn("y", (out.get("never_empty") or {}).get("soft_back") or {})


class TestRuling143AtSelection(unittest.TestCase):
    """RULING 159 (3)(a) (orchestrator 23:42 ET Nov 23): "your selection-side word check takes ruling 143 so it agrees
    with the render's lock". A moment whose ONLY L-v 2 failure is a word the transcript and the second recogniser read
    differently (Simply Bitcoin 513842ff: "$15,000 and a half thousand" against "15,500", Nov 23) stays in the pool for
    its line-up's lock pre-check: the lock's pass or adopt settles it (the pin's row says so), a hold drops it; with no
    lock, a speaker change or an unmeasured record: as before (refused)."""
    WORDS = {"ok": False, "transcript_ok": False, "replayed": False, "model": "scribe_v1",
             "disagree": {"numbers": ["15000", "15500"], "negations": [], "names": []},
             "speakers": {"turn_change_inside": False}, "edges": {"cuttable": True}}

    def run_rig(self, lock, truth=None, never_empty=False):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, lock_check=lock,
                   truths={"x": dict(truth or self.WORDS)})
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_the_lock_settles_a_words_only_disagreement(self):
        import test_medley as TM
        out = self.run_rig(TM.lock_stub())                                    # the lock passes x's span
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(pk["gates"]["second_pass"]["status"], "PASS")
        self.assertEqual(out["prescreen"]["words_pending_lock"], {"x": self.WORDS["disagree"]})
        self.assertIsNotNone(self.run_rig(TM.lock_stub(), never_empty=True)["package"])   # both passes

    def test_a_hold_no_lock_a_speaker_change_or_no_measure_still_refuse(self):
        import test_medley as TM
        self.assertIsNone(self.run_rig(TM.lock_stub({"x": ("hold", None)}))["package"])
        none = self.run_rig(None)                                              # no lock: refused at the pool, as
        self.assertEqual((none["package"], none["prescreen"]["second_pass"]["x"], "words_pending_lock" in   # before
                          none["prescreen"]), (None, "L-v 2 FAIL", False))   # (never a line-up's paid verdict)
        turn = dict(self.WORDS, speakers={"turn_change_inside": True})
        self.assertIsNone(self.run_rig(TM.lock_stub(), truth=turn)["package"])
        err = {"ok": False, "error": "no audio"}
        self.assertIsNone(self.run_rig(TM.lock_stub(), truth=err)["package"])

    def test_simply_bitcoin_513842ff_is_a_words_only_disagreement(self):
        """The real record (fixtures/lv2_513842ff.json: L-v 2 replayed offline from the recorded Scribe reading): the
        transcript's "$15,000 and a half thousand" against Scribe's "$15,500", one speaker inside. The render's lock
        adopted it on Nov 23; selection now agrees."""
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "lv2_513842ff.json")) as f:
            t = json.load(f)["record"]
        self.assertEqual((t["ok"], t["disagree"]["numbers"]), (False, ["15000500", "15500"]))
        self.assertTrue(PK.words_only(t))
        self.assertEqual(PK.lv2_settled(t, "adopt")["ok"], True)
        self.assertIs(PK.lv2_settled(t, "hold"), t)

    def test_the_settled_record(self):
        t = PK.lv2_settled(self.WORDS, "adopt")
        self.assertEqual((t["ok"], t["word_check"]), (True, "settled by the render's lock (ruling 143): adopt"))
        for v in ("hold", "error", None, "pending"):                           # audit F (qwen F2): "pending" is the
            self.assertIs(PK.lv2_settled(self.WORDS, v), self.WORDS)            # prescreen's alone (lv2_pending)
        self.assertEqual(PK.lv2_pending(self.WORDS, True)["word_check"], "pending the render's lock (ruling 143)")
        self.assertIs(PK.lv2_pending(self.WORDS, False), self.WORDS)
        for pre, segs in (({}, []), ({"segments": None}, []), ({"segments": [{"verdict": "pass"}]}, []),
                          ({"error": "x", "segments": [{"verdict": "pass"}]}, [{"moment_id": "x"}])):
            self.assertEqual(PK.lock_verdicts(pre, segs), {}, pre)               # audit F (qwen, cycle 2): never raises
        self.assertEqual(PK.lock_verdicts({"segments": [{"verdict": "adopt"}]}, [{"moment_id": "x"}]), {"x": "adopt"})
        ok = dict(self.WORDS, ok=True, transcript_ok=True)
        self.assertIs(PK.lv2_settled(ok, "adopt"), ok)                         # nothing to settle


class TestItem1RealClips(unittest.TestCase):
    """ITEM 1 (orchestrator 09:50 ET Nov 24) on three REAL clips, each asked the build's way (ad_read_out ->
    ad_before_soft -> exclusion_for on the clip's own word record and caption context) with the checker's real replies
    FROZEN (recorded 09:55 ET Nov 24 from the in-house checker, minimax; replayed here: nothing is asked):
      ad47eab4 (Digital Asset News, the news read after 'link in the description'): PASSES, the judgment recorded;
      6e79ceaa (Natalie Brunell, the first line of The Bitcoin Way's read, no magic word): REFUSED (ad_read);
      41e3bcce ('no one has made it easier than our friends over at Bitkey'): REFUSED (ad_read).
    A dead checker (no recorded reply) HOLDS: never a pass, never a flag."""
    D = os.path.join(HERE, "fixtures", "item1_sponsor")

    def setUp(self):
        import ledger_build as LB
        import eligibility as E
        self.LB, self.ctx = LB, E.Context(datetime(2026, 11, 24, 15, 0, tzinfo=timezone.utc), {})
        self.cases = json.load(open(os.path.join(self.D, "cases.json")))["cases"]

    def source(self, c):
        m, store = c["moment"], os.path.join(self.D, "store")
        if m.get("source_key"):
            src, _, why = self.LB.window_source(m, c["word_pass"], self.ctx, store)
            self.assertIsNotNone(src, why)
            src.context_source, why = self.LB.caption_source(dict(m, transcript_sha256=c["caption_sha256"]), self.ctx,
                                                             store, os.path.join(self.D, "ledger"))
            self.assertIsNotNone(src.context_source, why)
        else:
            src, _, why = self.LB.word_source(m, self.ctx, store)
            self.assertIsNotNone(src, why)
        return {m.get("source_key") or m["video_id"]: src}

    def judge(self, c, replies):
        import proof_ly as PL
        import providers as P
        ch = PL.chains("heimdall_first")
        ch["exclusion_verdict"] = ["heimdall:google/gemma-4-31b-it", "heimdall:minimax/minimax-m3.1-flash"]
        r = P.Router(chains=ch, routing="heimdall_first", record_dir=replies, replay=True)
        m = dict(c["moment"])
        sources = self.source(c)
        ad_read = PK.ad_read_out([m], sources)
        PK.ad_before_soft([m], ad_read, False)               # the clean pass: ITEM 1 reads the same in both passes
        if m["moment_id"] in ad_read and not m.get("ad_before"):
            return m, {"verdict": "exclude", "backend": "deterministic", "measured": True}
        return m, PK.exclusion_for(r, m, sources, {})

    def test_the_news_read_passes_recorded_and_both_ad_reads_refuse(self):
        got = {}
        for c in self.cases:
            m, v = self.judge(c, os.path.join(self.D, "replies"))
            got[m["moment_id"][:8]] = (v["verdict"], v.get("risks"), v["measured"], v.get("replayed"),
                                       bool(m.get("ad_before")))
        self.assertEqual(got, {
            "ad47eab4": ("keep", [], True, True, True),            # (c) a sponsor sentence before, editorial words
            "6e79ceaa": ("exclude", ["ad_read"], True, True, True),   # (b) part of the ad read: its first line
            "41e3bcce": ("exclude", ["ad_read"], True, True, False)})   # the BitKey read in its own words

    def test_a_dead_checker_holds_the_clip(self):
        import providers as P
        with tempfile.TemporaryDirectory() as empty, \
                mock.patch.object(P, "ReplayMiss", P.ProviderError):   # no reply recorded: the checker never answers
            for c in self.cases:                                       # (the replay's miss as a live outage raises it)
                m, v = self.judge(c, empty)
                self.assertEqual((v["verdict"], v["measured"], v.get("ad_before")), ("exclude", False, None),
                                 m["moment_id"])

class TestRuling146SponsorBefore(unittest.TestCase):
    """ITEM 1 (orchestrator 09:50 ET Nov 24, PBX's rule: sponsor material is fine "so long as it is not actually an ad
    that the entire segment is being cut from", and a sponsor is never "mentioned verbally" in the clip), IN BOTH
    PASSES: (a) sponsor words or an offer in the clip's own words refuse (deterministic, no model); (b) a clip the
    checker judges PART OF the ad read (its first line included: Natalie Brunell 6e79ceaa, the opening line of The
    Bitcoin Way's read) refuses; (c) a sponsor sentence BEFORE the clip refuses nothing by itself when the checker
    judges the clip's own words editorial: it passes with the judgment recorded on the exclusion row, never a flag;
    (d) no answer is UNVERIFIED and holds the clip, never a pass and never a flag. Ruling 146 (3)'s soft flag is gone."""
    BEFORE = "Use my promo code stories to get 10% off. This episode is sponsored by BitKey."
    CLIP = "If your Bitcoin can be frozen or monitored by an exchange, it's not yours."
    SPONSOR = "ad-read marker 'sponsored' in the sentence before it"

    def verdict(self, text, before, soft, reply):
        import json
        import types
        import moments as M
        import providers as P
        calls = []

        def fake(router, role, prompt, parse, n, seed, avoid_model=None):
            calls.append(role)
            if isinstance(reply, Exception):
                raise reply
            return types.SimpleNamespace(backend="heimdall:deepseek", replayed=False), parse(json.dumps(reply))
        with mock.patch.object(P, "call_parsed", fake):
            return M.exclusion_verdict(None, text, before, "", before_marker_soft=soft), calls

    def test_the_model_decides_a_marker_in_the_sentence_before(self):
        keep = {"risks": [], "about_bitcoin": "yes", "why": "her own view on custody"}
        v, calls = self.verdict(self.CLIP, self.BEFORE, True, keep)
        self.assertEqual((v["verdict"], v.get("ad_before"), calls), ("keep", self.SPONSOR, ["exclusion_verdict"]))
        ad = {"risks": ["ad_read"], "about_bitcoin": "yes", "why": "the opening line of the next ad read"}
        v, _ = self.verdict(self.CLIP, self.BEFORE, True, ad)
        self.assertEqual((v["verdict"], v.get("ad_before")), ("exclude", None))           # (b) the clip IS the ad

    def test_a_dead_checker_holds_never_a_pass_never_a_flag(self):
        import providers as P
        v, calls = self.verdict(self.CLIP, self.BEFORE, True, P.ProviderError("every exclusion model is down"))
        self.assertEqual((v["verdict"], v["measured"], v.get("ad_before"), calls),
                         ("exclude", False, None, ["exclusion_verdict"]))                # (d) UNVERIFIED: held

    def test_a_marker_in_the_clips_own_words_refuses_with_no_model(self):
        keep = {"risks": [], "about_bitcoin": "yes", "why": "x"}
        for text, before in ((self.CLIP + " Use my promo code stories.", ""),
                             (self.CLIP + " Use my promo code stories.", self.BEFORE)):
            v, calls = self.verdict(text, before, True, keep)
            self.assertEqual((v["verdict"], v["backend"], calls), ("exclude", "deterministic", []), text)   # (a)

    def test_both_passes_mark_and_the_cache_key_is_its_own(self):
        ms = [{"moment_id": "a", "ad_before": "stale"}, {"moment_id": "b"}]
        ad_read = {"a": self.SPONSOR, "b": "ad-read marker 'promo code' in the moment"}
        for soft in (False, True):                                    # ITEM 1: the clean pass asks the checker too
            ms[0]["ad_before"] = "stale"
            self.assertEqual(PK.ad_before_soft(ms, ad_read, soft), {"a": self.SPONSOR}, soft)
            self.assertEqual((ms[0].get("ad_before"), ms[1].get("ad_before")), (self.SPONSOR, None))
        seen, cache = [], {}
        with mock.patch.object(PK, "src_of", lambda m, s: "src"), \
                mock.patch.object(PK.CI, "context_around", lambda *a: (self.BEFORE, "")):
            import moments as M
            with mock.patch.object(M, "exclusion_verdict", lambda *a, **k: seen.append(k) or {"verdict": "keep"}):
                PK.exclusion_for(None, dict(ms[0], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
                PK.exclusion_for(None, dict(ms[1], text=self.CLIP, sentences=[1, 1], words=[0, 3]), {}, cache)
        self.assertEqual([k["before_marker_soft"] for k in seen], [True, False])
        self.assertEqual(sorted(map(str, cache)), sorted(map(str, [("a", 7, "ad_before"), "b"])))

    def run_rig(self, never_empty, excluded=()):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
                   excluded=excluded, follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
        r.build_kw = {"never_empty": never_empty}
        with mock.patch.object(PK, "ad_read_out", lambda ms, sources: {"x": self.SPONSOR}):
            return r.run()["package"]

    def test_a_clip_after_a_sponsor_sentence_judged_editorial_passes_in_both_passes_recorded(self):
        for never_empty in (False, True):
            pk = self.run_rig(never_empty)
            self.assertIsNotNone(pk, never_empty)
            self.assertNotIn("sponsor", pk["gates"])                                      # never a flag
            self.assertEqual(pk["gates"]["exclusion"]["status"], "PASS")
            self.assertEqual(pk["gates"]["exclusion"]["sponsor_before"]["x"]["marker"], self.SPONSOR)
            self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
            self.assertIsNone(self.run_rig(never_empty, excluded={"x"}), never_empty)     # judged the ad: refused

    def test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags(self):
        pk = self.run_rig(True)
        req = PP.required_gates(pk)
        self.assertNotIn("sponsor", PP.SOFT_GATES)                     # ITEM 1: the sponsor flag row is gone
        made_up = {"status": "FLAGGED", "flags": ["A plain sentence."], "replayed": False}
        self.assertEqual(PP.gate_problems(dict(pk["gates"], made_up=made_up), req),
                         ["made_up: FLAGGED without a soft gate and its plain flags (ruling 137)"])
        self.assertEqual(PP.gate_problems(dict(pk["gates"], sponsor=made_up), req),
                         ["sponsor: FLAGGED without a soft gate and its plain flags (ruling 137)"])

class TestRuling148RuntimeFloor(unittest.TestCase):
    """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
    medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
    its runtime gate row FLAGGED 'This video runs NN seconds, shorter than usual.' (NN the factory's estimate). Under
    30 s nothing seals; the clean pass is unchanged."""

    def run_rig(self, ms, never_empty):
        import test_medley as TM
        ids = [m["moment_id"] for m in ms]
        r = TM.Rig(ms, ids, [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
                   follow_up={"angles": [TM.angle(ids, ids[0])]})
        r.build_kw = {"never_empty": never_empty}
        return r.run()

    def test_a_short_lineup_seals_flagged_in_the_never_empty_pass_only(self):
        from test_moments import pm
        ms = [pm("h", "A", 11.0), pm("x", "B", 11.5), pm("y", "C", 11.4)]          # 33.9 s: under 36.7, over 30
        self.assertIsNone(self.run_rig(ms, False)["package"])                       # the clean pass: unchanged
        pk = self.run_rig(ms, True)["package"]
        self.assertIsNotNone(pk)
        est = pk["runtime_s_estimate"]
        self.assertLess(est, PK.RUNTIME_S[0])
        self.assertEqual((pk["gates"]["runtime"]["status"], pk["gates"]["runtime"]["flags"]),
                         ("FLAGGED", [f"This video runs {int(round(est))} seconds, shorter than usual."]))
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
        self.assertIsNone(PK._FLOOR)                                                # cleared after the pass

    def test_under_the_floor_nothing_seals(self):
        from test_moments import pm
        ms = [pm("h", "A", 9.0), pm("x", "B", 9.5), pm("y", "C", 9.4)]              # 27.9 s
        self.assertIsNone(self.run_rig(ms, True)["package"])

    def test_the_takeaway_budget_and_the_sentence(self):
        b40 = PK.takeaway_budget(40.0)
        self.assertIsNone(PK.takeaway_budget(33.9))                                 # outside the pass: no length
        pk = {"shape": "medley", "runtime_s_estimate": 57.19, "segments": [{"duration_s": 20.0}, {"duration_s": 13.9}]}
        self.assertIsNone(PK.runtime_short(pk))                                     # the clean pass: no sentence
        with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):
            lo, hi = PK.takeaway_budget(33.9)
            self.assertEqual((hi, lo), (PK.LY_TAKEAWAY_MAX_WORDS, PK.LY_TAKEAWAY_MAX_WORDS - PK.LY_SHORT_SPAN_WORDS))
            self.assertIsNone(PK.takeaway_budget(29.0))                             # under the floor
            self.assertEqual(PK.takeaway_budget(40.0), b40)                          # a full line-up: unchanged
            self.assertEqual(PK.runtime_short(pk), "This video runs 57 seconds, shorter than usual.")
            for bad in (dict(pk, runtime_s_estimate=60.0), dict(pk, shape="vo"),
                        dict(pk, segments=[{"duration_s": 29.9}])):
                self.assertIsNone(PK.runtime_short(bad), bad)


class TestRuling146(unittest.TestCase):
    """RULING 146 (orchestrator 07:55 ET Nov 18), the never-empty pass: (1) the source's own on-screen graphics (a ticker,
    a lower third, a bug) are SOFT in a package sealed 16:9 only, flagged in the ruling's words; (2) G17a's quiet before
    the hook's first word is SOFT (a measured shortfall only), flagged 'The opening clip may start abruptly.'"""
    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
              "covers_speaker": False}
    QUIET = "70 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame)"

    def rec(self, **kw):
        import visual_pin as VP
        r = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [dict(self.TICKER)],
             "third_person": {"shown": False, "how": "none", "words_negative": False}}
        return dict(r, **kw)

    def test_the_shows_own_graphics_and_what_stays_hard(self):
        import visual_pin as VP
        self.assertEqual(VP.graphics_only(self.rec()), ["ticker"])
        for bad in (self.rec(measured=False), self.rec(version="old"), self.rec(burned_in=None), self.rec(burned_in=[])):
            self.assertIsNone(VP.graphics_only(bad))
        with mock.patch.object(VP, "hook_block", lambda r: "a third person"):
            self.assertIsNone(VP.graphics_only(self.rec()))              # ruling 70's third person: not graphics
        m = {"moment_id": "x", "visual": self.rec()}
        self.assertTrue(PK.soft_graphics(m))
        self.assertEqual((m["visual"]["formats"], m["visual"]["graphics_16x9"]), (["16x9"], ["ticker"]))
        self.assertFalse(PK.soft_graphics({"moment_id": "y", "visual": self.rec(burned_in=[])}))

    def rig(self, ms, never_empty, **kw):
        import test_medley as TM
        r = TM.Rig(ms, [m["moment_id"] for m in ms], [(True, [], None, TM.Rig.LINE)], [None], **kw)
        r.build_kw = {"never_empty": never_empty}
        return r

    def test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged(self):
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        import test_medley as TM
        clean = self.rig(ms, False, visuals={"x": {"burned_in": [dict(self.TICKER)]}}).run()
        self.assertIsNone(clean["package"])
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
                   visuals={"x": {"burned_in": [dict(self.TICKER)]}},
                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})   # the clean pass reached its line-up
        r.build_kw = {"never_empty": True}
        pk = r.run()["package"]
        self.assertEqual(PP.formats_of(pk["segments"]), ["16x9"])
        ch = next(s["channel"] for s in pk["segments"] if s["moment_id"] == "x")
        self.assertEqual((pk["gates"]["graphics"]["status"], pk["gates"]["graphics"]["flags"]), (
            "FLAGGED", [f"The clip ({ch}) shows the show's own ticker; this package is 16:9 only."]))
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])

    def test_a_hook_with_a_quiet_shortfall_opens_flagged(self):
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        quiet = self.QUIET

        def make(ne):
            r = self.rig(ms, ne)
            base = r.onset
            r.onset = lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 70, "why": quiet}
                                          if m["moment_id"] == "h" else base(m, *a, **k))
            return r
        self.assertIsNone(make(False).run()["package"])
        pk = make(True).run()["package"]
        self.assertEqual(pk["segments"][0]["moment_id"], "h")
        self.assertEqual((pk["gates"]["hook_onset"]["status"], pk["gates"]["hook_onset"]["flags"]),
                         ("FLAGGED", ["The opening clip may start abruptly."]))
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])

    def test_an_unmeasured_or_other_onset_failure_stays_hard(self):
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        for rec in ({"pass": False, "measured": False, "why": "not measured"},
                    {"pass": False, "measured": True, "why": "the cut lands inside a word"}):
            r = self.rig(ms, True)
            base = r.onset
            r.onset = lambda m, *a, _rec=rec, **k: dict(_rec) if m["moment_id"] == "h" else base(m, *a, **k)
            out = r.run()
            self.assertTrue(out["package"] is None or out["package"]["segments"][0]["moment_id"] != "h", rec)


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
