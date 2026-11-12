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
    def test_the_runtime_counts_the_signoff_once(self):
        segs = [{"duration_s": 10.0}, {"duration_s": 20.0}]
        self.assertAlmostEqual(PK.runtime(segs, (40 + 18) / PK.WPS), 30.0 + 58 / 2.6 + PK.FIXED_S, places=2)
        self.assertAlmostEqual(PK.FIXED_S + 18 / PK.WPS, E.TAIL_S, places=1)     # the tail = fixed + one sign-off

    def test_the_moments_r4_on_tonights_numbers(self):
        def pk(vo1, vo2, vo3):
            p = {"segments": [{"duration_s": 8.38, "channel": "A"}, {"duration_s": 11.24, "channel": "B"},
                              {"duration_s": 10.29, "channel": "C"}],
                 "vo": {"intro": vo1, "bridges": [vo2, vo3], "bridges_after_clip": [1, 2]}}
            p["runtime_s_estimate"] = PK.runtime(p["segments"], (sum(len(x.split()) for x in (vo1, vo2, vo3)) + 19) / PK.WPS)
            return p
        w = lambda n: " ".join(["word"] * n)
        ok, why = PK.r4(pk(w(27), w(18), w(18)))                                  # 05:35-06:00's 63 words
        self.assertFalse(ok)
        self.assertIn("41.0%", why)
        ok, why = PK.r4(pk(w(13), w(18), w(11)))                                  # the rendered 42 words
        self.assertTrue(ok, why)
        self.assertIn("32.6%", why)
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

    def test_a_second_pass_without_diarisation_is_not_ok(self):
        class R:
            def transcribe(self, role, wav):
                return {"text": "Bitcoin is money.", "segments": [], "words": [
                    {"text": "Bitcoin", "start": 1.6, "end": 1.9}, {"text": "is", "start": 2.0, "end": 2.1},
                    {"text": "money.", "start": 2.2, "end": 2.6}]}, type("Rep", (), {"backend": "s", "replayed": False})()
        t = TT.verify_segment(R(), "v", 1.6, 2.6, "Bitcoin is money.", "/nonexistent", wav="w.wav", wav_start=0.0)
        self.assertIsNone(t["speakers"]["turn_change_inside"])
        self.assertFalse(t["ok"])


if __name__ == "__main__":
    unittest.main()
