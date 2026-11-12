#!/usr/bin/env python3
"""pipeline/moments.py + pipeline/package.py (deterministic parts): the miner's reply contract is strict and never
repaired; ranking is deterministic with contempt as a penalty; ad reads and opted-out channels are never offered; the
packager's usable() keeps L-u (<= 20 s per source video), L-v 1 / L-v 3 and novelty by overlap; the sign-off names
exactly the credit set (L-a). The line-up rules are in tests/package/test_angles.py. Offline: no model call."""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import select_by_id as SB  # noqa: E402
import trend_brief as TB  # noqa: E402
from test_eligibility import CID, HOOK_TXT, CLIP_TXT, CLIP2_TXT, NOW, REG, source  # noqa: E402


def reply(**kw):
    return json.dumps(kw)


SCORES = {"hook_first_2s": 4, "quotable": 3, "surprising_fact": 2, "stance": 3, "stakes": 2, "stands_alone": 4,
          "contempt_outrage": 0}


def mom(rng, **kw):
    d = {"range": rng, "scores": dict(SCORES), "names_person": False, "risk": [], "topics": ["price_action"],
         "reason": "a clean statement"}
    d.update(kw)
    return d


class TestMineContract(unittest.TestCase):
    def setUp(self):
        self.a = source([HOOK_TXT, CLIP_TXT], channel="DataDash", vid="A")
        self.b = source([CLIP2_TXT], channel="Natalie Brunell", vid="B")
        self.t = SB.Table([(self.a, 0, False), (self.a, 1, False), (self.b, 0, False)])

    def check(self, obj):
        return M.check_moments(obj, self.t, TB.TOPICS)

    def test_a_valid_reply_and_an_empty_one(self):
        got = self.check({"moments": [mom([1, 2]), mom([3, 3])]})
        self.assertEqual([(sp.source.video_id, sp.k0, sp.k1) for sp, _ in got], [("A", 0, 1), ("B", 0, 0)])
        self.assertEqual(self.check({"moments": []}), [])

    def test_rejected_never_repaired(self):
        bad = [({"moments": [mom([1, 3])]}, "cross-source"),
               ({"moments": [mom([1, 2]), mom([2, 2])]}, "overlaps"),
               ({"moments": [mom([9, 9])]}, "fabricated"),
               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=6))]}, "integer 0-5"),
               ({"moments": [mom([1, 1], scores=dict(SCORES, quotable=3.0))]}, "integer 0-5"),
               ({"moments": [mom([1, 1], scores={k: v for k, v in SCORES.items() if k != "stakes"})]}, "exactly"),
               ({"moments": [mom([1, 1], risk=["libel"])]}, "'risk'"),
               ({"moments": [mom([1, 1], topics=["altcoins"])]}, "'topics'"),
               ({"moments": [mom([1, 1], topics=[])]}, "'topics'"),
               ({"moments": [mom([1, 1], reason="")]}, "'reason'"),
               ({"moments": [mom([1, 1], names_person="no")]}, "'names_person'"),
               ({"moments": [dict(mom([1, 1]), headline="Bitcoin finds support")]}, "keys must be exactly"),
               ({"moments": [mom([1, 1])] * 13}, "at most 12")]
        for obj, why in bad:
            with self.assertRaises(SB.Rejected) as cm:
                self.check(obj)
            self.assertIn(why, str(cm.exception), obj)

    def test_ranking_is_deterministic_and_contempt_is_a_penalty(self):
        calm = {"scores": dict(SCORES), "risk": [], "topics": ["price_action"]}
        angry = {"scores": dict(SCORES, contempt_outrage=4), "risk": [], "topics": ["price_action"]}
        pred = {"scores": dict(SCORES), "risk": ["price_prediction"], "topics": ["price_action"]}
        self.assertGreater(M.rank_score(calm), M.rank_score(angry))
        self.assertGreater(M.rank_score(calm), M.rank_score(pred))
        self.assertEqual(M.rank_score(calm, trend={"price_action": 1.0}), M.rank_score(calm))   # SHADOW: weight 0

    def test_ad_reads_are_never_offered_and_the_optout_registry_is_honoured(self):
        ad = source(["This episode is brought to you by Swan Bitcoin, use code PULSE for a discount on Bitcoin.",
                     HOOK_TXT], channel="DataDash", vid="AD")
        self.assertNotIn(0, M.candidate_rows(ad))
        self.assertIn(1, M.candidate_rows(ad))
        ctx = E.Context(NOW, REG)
        keep, skipped = M.window_sources([self.a, self.b], ctx, optout=frozenset({CID["DataDash"]}))
        self.assertEqual([s.video_id for s in keep], ["B"])
        self.assertIn("opted out", skipped["A"])


def pm(mid, channel, dur, rank=10.0, hook=True, clip=True, risk=(), topics=("price_action",), vid=None):
    return {"moment_id": mid, "channel_id": channel, "channel_name": channel, "video_id": vid or f"v{mid}",
            "duration_s": dur, "rank_score": rank, "scores": dict(SCORES), "risk": list(risk), "topics": list(topics),
            "eligibility": {"hook": {"ok": hook}, "clip": {"ok": clip}}, "on_screen_ok": True, "excluded": [],
            "published_at": (NOW - timedelta(hours=6)).isoformat(), "speaker": {"turn_change_inside": None},
            "text": "Bitcoin x.", "sentences": [0, 0], "words": [0, 1], "start": 0.0, "end": dur,
            "transcript_sha256": "s"}


class TestPackageUsable(unittest.TestCase):
    def test_over_20_s_unmeasured_excluded_and_stale_time_words_are_unusable(self):
        ctx = E.Context(NOW, REG)
        long_ = pm("l", "A", 21.0)
        unmeasured = dict(pm("u", "B", 10.0), duration_s=None)
        stale = dict(pm("s", "C", 12.0, risk=("time_sensitive",)), published_at=(NOW - timedelta(hours=30)).isoformat())
        fresh = pm("f", "D", 12.0, risk=("time_sensitive",))
        excluded = dict(pm("x", "E", 12.0), excluded=["accusation"])
        changed = dict(pm("t", "F", 12.0), speaker={"turn_change_inside": True})
        ok, why = PK.usable([long_, unmeasured, stale, fresh, excluded, changed], ctx)
        self.assertEqual([m["moment_id"] for m in ok], ["f"])     # an UNMEASURED speaker (None) is a candidate only:
        self.assertIn("20.0 s", why["l"])                          # L-v 2 measures it at packaging and the pin refuses
        self.assertIn("L-v 3", why["s"])                           # an unmeasured second pass (audit p2 M11)
        self.assertIn("accusation", why["x"])
        self.assertIn("L-v 1", why["t"])

    def test_novelty_by_overlap_not_by_id(self):
        ctx = E.Context(NOW, REG)
        m = dict(pm("new-id", "A", 10.0, vid="V"), start=100.0, end=110.0)
        ok, why = PK.usable([m], ctx, delivered=[{"video_id": "V", "start": 105.0, "end": 115.0}])
        self.assertEqual(ok, [])
        self.assertIn("delivered", why["new-id"])
        ok, _ = PK.usable([m], ctx, delivered=[{"video_id": "V", "start": 111.0, "end": 115.0}, "other-id"])
        self.assertEqual([x["moment_id"] for x in ok], ["new-id"])

    def test_the_signoff_names_exactly_the_credit_set_hook_first(self):
        ctx = E.Context(NOW, REG)
        segs = [pm("h", CID["DataDash"], 10.0), pm("c1", CID["Natalie Brunell"], 15.0),
                pm("c2", CID["Yahoo Finance"], 15.0)]
        self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
                                                "Go follow them for more. Links are below.")

    def test_the_plain_title_never_cuts_a_name(self):
        ctx = E.Context(NOW, REG)
        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
        title = PK.plain_vo(segs, ctx)[2]["text"]
        self.assertLessEqual(len(title), 70)
        self.assertTrue(title.endswith(("and others", "Two", "One")), title)


if __name__ == "__main__":
    unittest.main()
