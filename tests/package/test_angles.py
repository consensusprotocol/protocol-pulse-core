#!/usr/bin/env python3
"""pipeline/package.py (angle first), pipeline/package_pin.py and pipeline/transcript_truth.py, deterministic parts:
the angle contract; the line-up per angle (one segment per channel, at most one price prediction, a short clip only as
the punchline, the length the runtime AND the moments R4 allow); DUPLICATE against every clip; PRICE_NOW against the
universe's current levels; the moments R4 mirror on tonight's real numbers; the pin refuses anything not exactly PASS
and is sealed; the second recognition pass compares both ways. Offline."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
import eligibility as E  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import transcript_truth as TT  # noqa: E402
import vo_fidelity as VF  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402
from test_moments import pm  # noqa: E402


def angle(ms, hook, text="Nobody controls Bitcoin."):
    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}


class TestAngles(unittest.TestCase):
    def setUp(self):
        self.by = {m["moment_id"]: m for m in (pm("a", "A", 10.0), pm("b", "B", 14.0), pm("c", "C", 13.0),
                                                pm("d", "D", 6.0), pm("e", "A", 14.0))}

    def test_the_angle_contract_is_strict_and_never_drops_an_id(self):
        self.assertEqual(len(PK.check_angles({"angles": [angle(["a", "b", "c"], "a")]}, self.by)), 1)
        for bad, why in (({"angles": [angle(["a", "b"], "a")]}, "3-8"),
                         ({"angles": [angle(["a", "b", "c", "zz"], "a")]}, "ids not offered ['zz']"),
                         ({"angles": [angle(["a", "e", "b"], "a")]}, ">= 3 channels"),
                         ({"angles": [angle(["a", "b", "c"], "d")]}, "the hook one of its moments"),
                         ({"angles": [dict(angle(["a", "b", "c"], "a"), title="x")]}, "keys must be exactly"),
                         ({"angles": []}, "1-3 items")):
            with self.assertRaises(ValueError) as cm:
                PK.check_angles(bad, self.by)
            self.assertIn(why, str(cm.exception))

    def test_a_lineup_keeps_one_segment_per_channel_and_the_length_rules(self):
        seg = PK.lineup_for(angle(["a", "b", "c", "e"], "a"), self.by)
        self.assertEqual([m["moment_id"] for m in seg], ["a", "b", "c"])           # the proposer's hook first
        self.assertEqual(len({m["channel_id"] for m in seg}), 3)                   # L-u: one per channel
        lo, hi = PK.content_range(2)
        self.assertTrue(lo <= 37.0 <= hi)

    def test_a_short_clip_only_as_the_punchline(self):
        by = {m["moment_id"]: m for m in (pm("a", "A", 10.0), pm("d", "D", 6.0), pm("b", "B", 14.0), pm("c", "C", 13.0))}
        seg = PK.lineup_for(angle(["a", "d", "b", "c"], "a"), by)
        self.assertIsNotNone(seg)
        self.assertNotIn("d", [m["moment_id"] for m in seg[1:-1]])                # 6 s: never in the middle
        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 16.0), pm("d", "D", 6.0))}
        seg2 = PK.lineup_for(angle(["a", "b", "d"], "a"), by2)
        self.assertEqual([m["moment_id"] for m in seg2], ["a", "b", "d"])         # allowed as the last (the punchline)

    def test_at_most_one_price_prediction_per_video(self):
        two = {m["moment_id"]: m for m in (pm("h", "A", 10.0, risk=("price_prediction",)),
                                           pm("c1", "B", 14.0, risk=("price_prediction",)), pm("c2", "C", 13.0))}
        self.assertIsNone(PK.lineup_for(angle(["h", "c1", "c2"], "h"), two))      # the only line-up has two
        one = dict(two, c1=dict(two["c1"], risk=[]))
        self.assertIsNotNone(PK.lineup_for(angle(["h", "c1", "c2"], "h"), one))   # one is fine

    def test_a_clip_must_add_something_against_every_line(self):
        pk = {"segments": [{"label": "hook", "text": "Bitcoin ran from 16K to 126K. That move is about an 8x."},
                           {"label": "clip_01", "text": "Nobody can take your Bitcoin without your keys, that is the point."},
                           {"label": "clip_02", "text": "The hacks hit the exchanges and the intermediaries, never Bitcoin itself."}],
              "lines": [{"slot": "intro", "text": "Bitcoin ran from 16K to 126K."},
                        {"slot": "bridge_1", "text": "Watch what the hacks hit: the exchanges and the intermediaries, never Bitcoin itself."},
                        {"slot": "title", "text": "Who controls Bitcoin?"},
                        {"slot": "caption", "text": "Nobody can take your Bitcoin without your keys."}]}
        self.assertEqual({(x["slot"], x["detail"]) for x in PK.duplicates(pk)},
                         {("intro", "repeats the words of hook"), ("bridge_1", "repeats the words of clip_02"),
                          ("caption", "repeats the words of clip_01")})

    def test_price_now_against_the_current_levels(self):
        src = source(["Bitcoin is trading at seventy three thousand dollars right now.",
                      "Back in 2022 Bitcoin was at sixteen thousand dollars.",
                      "I think Bitcoin is going to two hundred fifty thousand dollars."], age_h=3.0)
        levels = PK.current_levels([src], E.Context(NOW, REG))
        self.assertEqual(levels, [73000.0])                                      # history and forecasts never current
        self.assertEqual(VF.price_now("Bitcoin ran from 16K to 126K", levels), [16000.0, 126000.0])
        self.assertEqual(VF.price_now("Bitcoin holds $73,000", levels), [])
        self.assertEqual(VF.price_now("From the 2022 low, Bitcoin ran from 16K to 126K", levels), [])


class TestLengthAndR4(unittest.TestCase):
    def test_the_runtime_is_the_factorys_own_estimate(self):
        segs = [{"duration_s": 10.0}, {"duration_s": 20.0}]
        # edl_rules._r4_moments: word spans + each VO line at 2.5 w/s + 1 s pre-roll + the 14.30 s tail (sign-off inside)
        self.assertAlmostEqual(PK.runtime(segs, ["w " * 10, "w " * 15]), 30.0 + 10 / 2.5 + 1 + 15 / 2.5 + 1 + 14.30,
                               places=2)
        self.assertAlmostEqual(PK.FINAL_TAIL_S, 14.30, places=2)

    def test_the_moments_r4_on_tonights_numbers(self):
        def pk(vo1, vo2, vo3):
            p = {"segments": [{"duration_s": 8.38, "channel": "A"}, {"duration_s": 11.24, "channel": "B"},
                              {"duration_s": 10.29, "channel": "C"}],
                 "vo": {"intro": vo1, "bridges": [vo2, vo3], "bridges_after_clip": [1, 2]}}
            p["runtime_s_estimate"] = PK.runtime(p["segments"], [vo1, vo2, vo3])
            return p
        w = lambda n: " ".join(["word"] * n)
        p63 = pk(w(27), w(18), w(18))                                              # 05:35-06:00's 63 words
        ok, why = PK.r4(p63)                  # the factory's denominator: 28.2 s of VO = 38.9 % of 72.41 s (share ok)
        self.assertTrue(ok, why)
        self.assertIn("38.9%", why)
        self.assertAlmostEqual(p63["runtime_s_estimate"], 72.41, places=2)       # ... but over 70 s: the runtime gate
        self.assertFalse(PK.RUNTIME_S[0] <= p63["runtime_s_estimate"] <= PK.RUNTIME_S[1])
        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # 06:22's 42 words
        self.assertTrue(ok, why)
        self.assertFalse(PK.r4(dict(pk(w(13), w(18), w(11)), vo={"intro": w(13), "bridges": [w(5), w(5)],
                                                                  "bridges_after_clip": [1, 1]}))[0])
        self.assertLessEqual(PK.min_vo_words(29.91), PK.r4_max_vo_words(29.91, 3))


class TestPinAndTruth(unittest.TestCase):
    def pk(self, **gates):
        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.REQUIRED_GATES}
        g.update(gates)
        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
                              "transcript_sha256": "t", "url_30s_before": "u"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}

    def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
        pin = package_pin.to_pin(self.pk(), "r")
        mp = pin["moments_package"]
        self.assertEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"],
                                                                 mp["title"], mp["caption"], mp["gates"]))
        mp2 = dict(mp, title="changed after the gates")
        self.assertNotEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp2["edl_vo"], mp2["signoff_expected"],
                                                                    mp2["title"], mp2["caption"], mp2["gates"]))
        for bad in ({"second_pass": {"status": "NOT RUN", "by": None, "replayed": False, "n": 0}},
                    {"coherence": {"status": "FAIL", "by": "x", "replayed": False, "n": 1}},
                    {"context_b": {"status": "PASS", "by": "x", "replayed": True, "n": 1}},
                    {"exclusion": {"status": "pass", "by": "x", "replayed": False, "n": 1}}):
            with self.assertRaises(package_pin.PinRefused):
                package_pin.to_pin(self.pk(**bad), "r")
        p = self.pk()
        p.pop("gates")
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(p, "r")
        p = self.pk()
        p["caption"] = "a caption the gates never saw"                         # the shipped line != the gated one
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(p, "r")
        p = self.pk(context_b={"status": "PASS", "by": "x", "replayed": None, "n": 1})   # replayed not stated
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(p, "r")

    def test_the_second_pass_compares_both_ways_inside_the_clip_only(self):
        self.assertFalse(TT.compare("Bitcoin is going to zero.", "Bitcoin is not going to zero.")["ok"])   # a dropped not
        self.assertFalse(TT.compare("Bitcoin is not going to zero.", "Bitcoin is going to zero.")["ok"])
        self.assertFalse(TT.compare("It hit 126,000.", "It hit 126,000 and 126,000.")["ok"])               # counts
        self.assertTrue(TT.compare("Bitcoin ran from 16K to 126K.", "Bitcoin ran from 16k to 126k.")["ok"])
        sec = {"segments": [], "words": [{"text": w, "start": i, "end": i + 0.9, "speaker": "s0"}
                                         for i, w in enumerate("Your friends are not here Bitcoin is money".split())]}
        self.assertEqual(TT.span_text(sec, 5.0, 8.0), "Bitcoin is money")
        self.assertIs(TT.speaker_turns(sec, 5.0, 8.0)["turn_change_inside"], False)
        self.assertIsNone(TT.speaker_turns({"segments": [], "words": []}, 0, 1)["turn_change_inside"])   # not measured


class TestInventory(unittest.TestCase):
    """audit p2 C2 K11: the inventory never emits PASS for an unmeasured, failed, replayed, unstated or empty input."""

    def base(self):
        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True},
               "verdict": {"ok": True}, "backend": "b", "replayed": False, "measured": True}
        ctx = {"ok": True, "violations": [], "backends": {"B": "b", "C": "b"}, "replayed": False, "measured": True}
        a = {"hook": {"backend": "b", "replayed": False, **{k: v for k, v in (("speaker_changes_inside", "no"),
             ("view", "own_sincere"), ("referents", []), ("conditions", []), ("retraction", "none"), ("time_ok", "yes"),
             ("certainty", "certain"))}}}
        exc = {"m": {"verdict": "keep", "backend": "b", "replayed": False, "measured": True}}
        tru = {"m": {"ok": True, "model": "s", "replayed": False, "edges": {"cuttable": True}}}
        coh = {"backend": "b", "replayed": False, "measured": True}
        return dict(fid=fid, dup=[], rt_ok=True, r4_res=(True, "ok"), ctx_=ctx, a_by=a, exc=exc, truth=tru,
                    coh_ok=True, coh=coh)

    def test_a_clean_inventory_passes_and_every_failure_is_not_pass(self):
        g = PK.inventory(**self.base())
        self.assertEqual({r["status"] for r in g.values()}, {"PASS"})
        self.assertEqual(set(g), set(package_pin.REQUIRED_GATES))
        cases = [("vo_fidelity_verdict", lambda b: b["fid"].update(measured=False)),
                 ("vo_fidelity_verdict", lambda b: b["fid"].update(replayed=True)),
                 ("price_now", lambda b: b["fid"]["deterministic"].update(price_now_measured=False)),
                 ("context_b", lambda b: b["ctx_"].update(measured=False, ok=False)),
                 ("context_a", lambda b: b["a_by"]["hook"].update(replayed=None)),
                 ("exclusion", lambda b: b["exc"]["m"].update(measured=False)),
                 ("second_pass", lambda b: b["truth"]["m"].update(ok=False)),
                 ("second_pass", lambda b: b["truth"]["m"].update(error="x")),
                 ("cuttable", lambda b: b["truth"]["m"].update(edges={"cuttable": False})),
                 ("cuttable", lambda b: b["truth"]["m"].pop("edges")),
                 ("coherence", lambda b: b["coh"].update(measured=False)),
                 ("exclusion", lambda b: b["exc"].clear())]
        for row, mutate in cases:
            b = self.base()
            mutate(b)
            g = PK.inventory(**b)
            self.assertTrue(g[row]["status"] != "PASS" or g[row]["replayed"] is not False, (row, g[row]))
            self.assertTrue(package_pin.gate_problems(g), row)

    def test_a_leading_self_repair_is_part_of_the_sentence_and_nothing_else_is(self):
        """Ruling 8 (08:29): 'path.' | 'Bit-' 'bitcoin imposes ...' (the same speaker's truncated repetition of the
        clip's first word) is CUTTABLE at the IN and no L-v 2 disagreement. Another speaker, a fragment that is not a
        prefix, no dash, a full repetition, two fragments, or no sentence end before it: not a self-repair."""
        text = "Bitcoin imposes a global free market for the first time ever."

        def words(rep=("Bit-",), rep_sp="s0", before="path."):
            ws = [{"text": before, "start": 0.4, "end": 0.8, "speaker": "s0"}]
            ws += [{"text": r, "start": 1.30 - 0.2 * (len(rep) - 1 - k), "end": 1.42 - 0.2 * (len(rep) - 1 - k),
                    "speaker": rep_sp} for k, r in enumerate(rep)]
            ws += [{"text": t, "start": 1.72 + 0.3 * k, "end": 1.95 + 0.3 * k, "speaker": "s0"}
                   for k, t in enumerate(text.lower().split())]
            return ws + [{"text": "Okay,", "start": 6.0, "end": 6.2, "speaker": "s1"}]

        class R:
            def __init__(self, ws):
                self.ws = ws

            def transcribe(self, role, wav):
                return {"text": " ".join(w["text"] for w in self.ws), "segments": [], "words": self.ws}, \
                    type("Rep", (), {"backend": "s", "replayed": False})()
        run = lambda ws: TT.verify_segment(R(ws), "v", 1.5, 5.25, text, "/nonexistent", wav="w.wav", wav_start=0.0)
        t = run(words())
        self.assertTrue(t["edges"]["cuttable"], t["edges"])
        self.assertEqual((t["edges"]["in"]["before"], t["edges"]["in"]["self_repair"]), ("path.", "Bit-"))
        self.assertEqual(t["self_repair"], "Bit-")
        self.assertTrue(t["ok"], t)
        self.assertTrue(run(words(rep=()))["edges"]["cuttable"])                 # no false start: unchanged
        for kw in ({"rep_sp": "s1"}, {"rep": ("Bo-",)}, {"rep": ("Bit",)}):             # not a self-repair at all
            t = run(words(**kw))
            self.assertFalse(t["edges"]["cuttable"], kw)
            self.assertIsNone(t["edges"]["in"].get("self_repair"), kw)
        for kw, before in (({"rep": ("B-", "Bit-")}, "B-"), ({"before": "and"}, "and")):   # exactly ONE token, and only
            t = run(words(**kw))                                                           # at a sentence start
            self.assertFalse(t["edges"]["cuttable"], kw)
            self.assertEqual(t["edges"]["in"]["before"], before, kw)
        # a FULL repetition is not truncated, so not a self-repair: the IN's first-word match (4 letters, unchanged
        # before ruling 8) reads 'Bitcoin-' as the first word, and L-v 2 still counts it as a disagreement
        t = run(words(rep=("Bitcoin-",)))
        self.assertIsNone(t["self_repair"])
        self.assertIsNone(t["edges"]["in"].get("self_repair"))
        self.assertFalse(t["ok"])
        self.assertIn("Bitcoin-", t["disagree"]["names"])

    def test_the_moments_r4_share_is_45_percent(self):
        """Ruling 9 (08:29): 45 % of the TOTAL runtime; 45.1 % is refused; the word caps are unchanged."""
        def pk(a, b, c, segs=(8.38, 9.62, 3.50)):
            w = lambda n: " ".join(["word"] * n)
            p = {"segments": [{"duration_s": d} for d in segs],
                 "vo": {"intro": w(a), "bridges": [w(b), w(c)], "bridges_after_clip": [1, 2]}}
            p["runtime_s_estimate"] = PK.runtime(p["segments"], [w(a), w(b), w(c)])
            return p
        self.assertEqual(PK.R4_MOMENTS_SHARE, 0.45)
        ok, why = PK.r4(pk(30, 18, 18))                                           # 29.4 s of 65.2 s = 45.09 %
        self.assertFalse(ok)
        self.assertIn("VO=45.1% of the runtime (max 45%)", why)
        ok, why = PK.r4(pk(29, 18, 18))                                           # 29.0 s of 64.8 s = 44.75 %
        self.assertTrue(ok, why)
        ok, why = PK.r4(pk(13, 18, 24))                                           # 08:29's VO 3: 24 words
        self.assertTrue(ok, why)                                                  # a takeaway (ruling 10, cap 30)

    def test_the_takeaway_after_the_last_clip_is_capped_at_30_and_bridges_at_20(self):
        """Ruling 10 (08:40): 31 words after the LAST clip are refused, 30 pass; a 21-word bridge BETWEEN clips is
        still refused."""
        def pk(a, b, c, after=(1, 2), segs=(8.38, 9.62, 8.0)):
            w = lambda n: " ".join(["word"] * n)
            p = {"segments": [{"duration_s": d} for d in segs],
                 "vo": {"intro": w(a), "bridges": [w(b), w(c)], "bridges_after_clip": list(after)}}
            p["runtime_s_estimate"] = PK.runtime(p["segments"], [w(a), w(b), w(c)])
            return p
        self.assertEqual(PK.MOMENTS_TAKEAWAY_WORD_CAP, 30)
        ok, why = PK.r4(pk(10, 12, 31))
        self.assertFalse(ok)
        self.assertIn("takeaway 2 31 words (max 30)", why)
        self.assertTrue(PK.r4(pk(10, 12, 30))[0])
        ok, why = PK.r4(pk(10, 21, 12))
        self.assertFalse(ok)
        self.assertIn("bridge 1 21 words (max 20)", why)

    def test_a_second_pass_without_diarisation_is_not_ok(self):
        class R:
            def transcribe(self, role, wav):
                return {"text": "Bitcoin is money.", "segments": [], "words": [
                    {"text": "Bitcoin", "start": 1.6, "end": 1.9}, {"text": "is", "start": 2.0, "end": 2.1},
                    {"text": "money.", "start": 2.2, "end": 2.6}]}, type("Rep", (), {"backend": "s", "replayed": False})()
        t = TT.verify_segment(R(), "v", 1.6, 2.6, "Bitcoin is money.", "/nonexistent", wav="w.wav", wav_start=0.0)
        self.assertIsNone(t["speakers"]["turn_change_inside"])
        self.assertFalse(t["ok"])


class TestMajorityOnce(unittest.TestCase):
    def test_once_then_the_majority_only_when_the_first_run_fails(self):
        """08:18 item 4 / 08:29: a model verdict that passes its first run runs once; one that does not gets the
        three-run majority once; an unmeasured pass is a fail vote; the record keeps every run and an honest
        replayed tri-state."""
        calls = []

        def run_of(results):
            def run(sd):
                calls.append(sd)
                return results[sd]
            return run
        ok = lambda r: r.get("ok") is True and r.get("measured", True) is True
        passed, res, votes = PK.once_then_majority(run_of({7: {"ok": True}}), ok)
        self.assertEqual((passed, votes, calls), (True, ["pass"], [7]))
        self.assertNotIn("majority", PK.with_votes(res, votes, passed))
        calls.clear()
        passed, res, votes = PK.once_then_majority(run_of({7: {"ok": False}, 8: {"ok": True}, 9: {"ok": True}}), ok)
        self.assertEqual((passed, votes, calls), (True, ["fail", "pass", "pass"], [7, 8, 9]))
        rec = PK.with_votes(res, votes, passed)
        self.assertTrue(rec["ok"])
        self.assertEqual((rec["majority"]["votes"], rec["majority"]["seeds"]), (["fail", "pass", "pass"], [7, 8, 9]))
        calls.clear()
        passed, res, votes = PK.once_then_majority(
            run_of({7: {"ok": False}, 8: {"ok": True}, 9: {"ok": True, "measured": False}}), ok)
        self.assertEqual((passed, votes), (False, ["fail", "pass", "fail"]))
        self.assertFalse(PK.with_votes(res, votes, passed)["ok"])
        res = [{"ok": False, "replayed": False}, {"ok": True, "replayed": None}, {"ok": True, "replayed": False}]
        self.assertIsNone(PK.with_votes(res, ["fail", "pass", "pass"], True)["replayed"])

    def test_content_range_is_in_seconds_and_meets_both_bounds(self):
        """Audit 0742 C2 (qwen P1-2, glm N1): VO_S is seconds (package.py: 'the VO's seconds'). The upper bound is the
        content at which the least VO (VO_S[0] seconds of speech + one pre-roll per line) lands exactly 70 s; at the
        lower bound some VO lands 60 s inside the share, and 0.1 s less content cannot (unless the bound is the
        search's 20.0 s floor). content_range counts n_clips VO lines; the takeaway after the last clip (ruling 4)
        is not in that count: an open item of the angle-first build path, not used by a given package."""
        for n_clips in (2, 3, 4):
            lo, hi = PK.content_range(n_clips)
            self.assertAlmostEqual(hi + PK.VO_S[0] + PK.R4_PREROLL_S * n_clips + PK.FINAL_TAIL_S, PK.RUNTIME_S[1],
                                   places=6)
            self.assertLessEqual(PK.min_vo_words(lo, n_clips), PK.r4_max_vo_words(lo, n_clips))
            if lo > 20.0:                       # 20.0 s is the search's floor: under the 45 % share it binds
                self.assertGreater(PK.min_vo_words(lo - 0.1, n_clips), PK.r4_max_vo_words(lo - 0.1, n_clips))

    def test_the_r4_word_bounds_invert_runtime_and_the_share_exactly(self):
        """Audit 0742 C1 (grok P1): r4_max_vo_words / min_vo_words invert runtime() and the share on every content
        length 15-50 s and 1-4 VO lines: the bound passes, one word more (or less) does not."""
        for c10 in range(150, 501, 7):
            c = c10 / 10
            for n in range(1, 5):
                vo = lambda w: w / PK.R4_WPS + PK.R4_PREROLL_S * n
                share = lambda w: vo(w) / (c + vo(w) + PK.FINAL_TAIL_S)
                rt = lambda w: c + vo(w) + PK.FINAL_TAIL_S
                hi, lo = PK.r4_max_vo_words(c, n), PK.min_vo_words(c, n)
                if hi > 0:
                    self.assertLessEqual(share(hi), PK.R4_MOMENTS_SHARE + 1e-9, (c, n))
                self.assertGreater(share(hi + 1), PK.R4_MOMENTS_SHARE - 1e-9, (c, n))
                if lo > 0:
                    self.assertGreaterEqual(rt(lo), PK.RUNTIME_S[0] - 1e-9, (c, n))
                    self.assertLess(rt(lo - 1), PK.RUNTIME_S[0], (c, n))


if __name__ == "__main__":
    unittest.main()
