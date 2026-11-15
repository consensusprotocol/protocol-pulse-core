#!/usr/bin/env python3
"""RULING 112's diagnosis driver (tests/package/hook112.py), offline: where each moment stopped on the way to the hook
job (both paths), the distinct roll-up, the near misses and the part that holds a 3 back, pp-ingest's hook pass read
from a database of the same shape, and the calibration's guards (Heimdall only, no cache, the stop)."""
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import hook112 as H  # noqa: E402


def medley_pk(why_none=None, went_on=True, hook_error=None):
    pre = {"screened": 9, "cleared": 6, "failed": {"f": ["REFERENT_OUTSIDE"]}}
    if went_on:
        pre.update(second_pass={"c": "L-v 2 FAIL", "t": "PASS", "o": "PASS", "x": "PASS", "r3": "PASS", "r4": "PASS"},
                   hook_onset={"t": "PASS", "o": "FAIL: 0 ms of genuine quiet", "x": "PASS", "r3": "PASS",
                               "r4": "PASS"},
                   trim_cut={"t": "FAIL: no trimmed cut was reached"})
    return {"unusable": {"u": "22.9 s: over the 20.0 s per source video (L-u) or unmeasured"},
            "no_role": {"n": "the render's STAND_ALONE topic rule with the pin's screen (ruling 34)"},
            "ad_read": {"a": "an ad-read marker"}, "reposted": {"p": "q"}, "prescreen": pre, "why_none": why_none,
            "hook_pool": {"error": hook_error, "ratings": {} if not went_on else {
                "r3": {"scroll": 3, "alone": 5, "setup": 4, "rating": 3, "why": "slow start"},
                "r4": {"scroll": 4, "alone": 5, "setup": 2, "rating": 2, "why": "old rule: setup counted"}}}}


def inputs(ids):
    return {"moments": [{"moment_id": i, "text": f"text {i}", "mined": {"ledger_moment_id": f"L{i}"}} for i in ids]}


POOL = ["u", "n", "a", "p", "f", "c", "t", "o", "x", "r3", "r4", "s"]


class TestTheMedleyTrace(unittest.TestCase):

    def test_each_moment_stops_where_its_record_says(self):
        tr = H.medley_trace(medley_pk(), inputs(POOL))
        got = {k: v[0] for k, v in tr.items()}
        self.assertEqual(got, {"u": 0, "n": 0, "a": 0, "p": 0, "f": 1, "c": 2, "t": 3, "o": 3, "x": 3, "r3": 5,
                               "r4": 6, "s": 1})
        self.assertIn("cannot open", tr["x"][1])                       # passed G17a, never rated: it cannot open
        self.assertEqual(tr["r3"][1], "rated 3")
        self.assertIsNone(tr["r4"][1])          # today's rule: the lower of scroll / alone (4), not the recorded 2

    def test_a_failure_is_the_stop_even_beside_a_rating(self):
        pk = medley_pk()                                   # a record package.build never writes: both, for one id
        pk["hook_pool"]["ratings"]["c"] = {"scroll": 5, "alone": 5, "setup": 5, "rating": 5, "why": "w"}
        self.assertEqual(H.medley_trace(pk, inputs(POOL))["c"][:2], (2, "L-v 2 FAIL"))

    def test_the_3_channel_rule_and_a_failed_hook_call(self):
        tr = H.medley_trace(medley_pk("6 moments cleared step A from fewer than 3 channels", went_on=False),
                            inputs(POOL))
        self.assertEqual((tr["t"][0], tr["f"][0]), (2, 1))           # cleared, then the medley ended
        self.assertIn("3-channel rule", tr["t"][1])
        tr = H.medley_trace(medley_pk(hook_error="ProviderError: no back-end"), inputs(POOL))
        self.assertEqual(tr["x"][0], 4)                                # it may open; the call failed: not rated
        self.assertIn("not rated", tr["x"][1])


class TestTheSpotlightTrace(unittest.TestCase):

    def test_free_screens_step_a_and_the_hook(self):
        pk = {"spotlight": {"pool": {"out": {"long": "35.6 s: over the 35.0 s per source video"},
                                     "snapped": {"w1": {"from": "m1"}}},
                            "moments": {"al": {"stage": 0, "out": "the ALONE scorer: 2.0 (needs 4) (ruling 109)"},
                                        "sa": {"stage": 0, "out": "step A: REFERENT_OUTSIDE"},
                                        "lv": {"stage": 1, "out": "L-v 2 / CUTTABLE: the second pass disagrees"},
                                        "co": {"stage": 2, "out": "it cannot open cold: G17a"},
                                        "w1": {"stage": 3, "out": "the hook's own job rates 3", "hook_own": 3},
                                        "h4": {"stage": 5, "out": "the visual check", "hook_own": 4}}}}
        tr = H.spotlight_trace(pk)
        self.assertEqual({k: v[0] for k, v in tr.items()},
                         {"long": 0, "al": 0, "sa": 1, "lv": 2, "co": 3, "m1": 5, "h4": 6})   # w1 is m1's span


class TestTheRollUp(unittest.TestCase):

    def test_the_furthest_stage_over_builds_a_tie_keeps_the_latest_reason_and_variants_fold(self):
        b1 = (medley_pk(), inputs(POOL))
        pk2 = medley_pk()
        pk2["prescreen"]["failed"] = {"f": ["CONDITION_OUTSIDE"]}       # the same stage, a newer reason
        pk2["prescreen"]["second_pass"]["c~trim"] = "PASS"
        pk2["prescreen"]["hook_onset"]["c~trim"] = "PASS"
        pk2["hook_pool"]["ratings"]["c~trim"] = {"scroll": 2, "alone": 4, "setup": 2, "rating": 2, "why": "w"}
        fu = H.funnel([("ledger_1", *b1), ("ledger_2", pk2, inputs(POOL))])
        self.assertEqual(fu["furthest"]["f"]["why"], "step A: CONDITION_OUTSIDE")
        self.assertEqual(fu["furthest"]["c"]["stage"], "rated by the hook job")   # its ~trim variant was rated
        self.assertEqual((fu["distinct"], fu["distinct_by_stage"]["rated >= 4"]), (12, 1))
        self.assertEqual(fu["never_rated_stopped_before"]["cleared step A"],      # s: in the pool, no stage record
                         {"step A: CONDITION_OUTSIDE": 1, "the medley ended before step A": 1})


class TestTheNearMisses(unittest.TestCase):

    def test_ranked_one_per_moment_on_todays_rule_and_the_part_that_holds_a_3(self):
        rs = {("a", "q"): {"moment_id": "a", "scroll": 4, "alone": 5, "setup": 5, "rating": 4},
              ("a~trim", "q"): {"moment_id": "a~trim", "scroll": 4, "alone": 4, "setup": 4, "rating": 4},
              ("w", "q"): {"moment_id": "w", "scroll": 5, "alone": 5, "setup": 5, "rating": 5},   # a span of b
              ("b", "q"): {"moment_id": "b", "scroll": 3, "alone": 5, "setup": 3, "rating": 3},
              ("c", "q"): {"moment_id": "c", "scroll": 3, "alone": 3, "setup": 5, "rating": 3},
              ("d", "q"): {"moment_id": "d", "scroll": 2, "alone": 4, "setup": 4, "rating": 2},
              ("e", "q"): {"moment_id": "e", "scroll": 3, "alone": 4, "setup": 3, "rating": 3}}
        nm = H.near_misses(rs, n=3, fold={"w": "b"})
        self.assertEqual([r["moment_id"] for r in nm["top"]], ["w", "a", "c"])   # b's best is its span w
        self.assertEqual((nm["rated_distinct"], nm["threes"]), (5, 2))
        self.assertEqual(nm["threes_held_back_by"], {"scroll": 2, "alone": 1,      # setup is shown apart: not a part
                                                     "setup (not in the own-job rating since ruling 61)": 1})
        self.assertEqual(H.own_rating({"scroll": 4, "alone": 5, "setup": 2, "rating": 2}), 4)   # ruling 61


class TestTheHookPass(unittest.TestCase):

    def db(self, d):
        p = os.path.join(d, "queue.sqlite")
        db = sqlite3.connect(p)
        db.executescript("CREATE TABLE events (id INTEGER, at TEXT, ts REAL, video_id TEXT, channel_id TEXT, kind TEXT, "
                         "detail TEXT); CREATE TABLE videos (video_id TEXT, title TEXT, moments INTEGER); "
                         "CREATE TABLE channels (channel_id TEXT, display_name TEXT);")
        db.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "2026-11-15T13:24:51", 100.0, "bl", "cb", "hooks", json.dumps({"rows": 0, "windows": 4, "cost": 0.0,
                                                                               "seconds_hook": 0.1})),
            (2, "2026-11-15T15:05:56", 200.0, "v1", "cm", "hooks", json.dumps({"rows": 2, "windows": 18, "cost": 0.004,
                                                                               "seconds_hook": 9.0})),
            (3, "2026-11-15T15:06:00", 210.0, "v2", "cm", "hooks", json.dumps({"rows": 0, "windows": 3, "cost": 0.001,
                                                                               "seconds_hook": 4.0})),
            (4, "2026-11-13T00:00:00", 1.0, "old", "cb", "hooks", json.dumps({"rows": 0}))])
        db.executemany("INSERT INTO channels VALUES (?, ?)", [("cb", "Bloomberg Television"), ("cm", "Magazine")])
        db.executemany("INSERT INTO videos VALUES (?, ?, ?)", [("bl", "IPO", 0), ("v1", "BTC", 29), ("v2", "BTC2", 3)])
        db.commit()
        db.close()
        return p

    def test_classes_the_given_videos_and_whether_their_hook_rows_reached_the_job(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "ledger.jsonl")
            with open(led, "w") as f:
                for mid, ps in (("h1", "hook"), ("h2", "hook"), ("m1", "moment"), ("h3", "hook"), (None, "hook")):
                    f.write(json.dumps({"moment_id": mid, "video_id": "v1", "mined": {"pass": ps}}) + "\n")
            hp = H.hook_pass(self.db(d), 50.0, ["v1"], led, rated_ids={"h1", "m1"},
                             furthest={"h2": {"stage": "cleared step A", "why": "not cuttable"}},
                             inputs_report={"word_pass": {"refused": ["h3"]}})
        self.assertEqual(hp["classes"], {"0 rows, no model call": 1, "wrote rows, a model called": 1,
                                         "0 rows, a model called": 1})        # the old event is outside the window
        self.assertEqual(hp["per_channel"]["Bloomberg Television"], {"0 rows, no model call": 1})
        self.assertEqual([e["video_id"] for e in hp["today"]], ["v1"])
        self.assertEqual((hp["hook_rows"], hp["hook_rows_rated"]), ({"v1": 3}, {"v1": ["h1"]}))
        self.assertEqual(hp["hook_rows_furthest"]["v1"]["h2"]["why"], "not cuttable")
        self.assertIn("refused by the word pass", hp["hook_rows_furthest"]["v1"]["h3"]["why"])

    def test_the_hook_pass_own_calls_decide_whether_a_model_was_called(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.db(d)
            db = sqlite3.connect(p)
            db.execute("CREATE TABLE calls (id INTEGER, ts REAL, video_id TEXT, role TEXT, kind TEXT)")
            db.executemany("INSERT INTO calls VALUES (?, ?, ?, ?, ?)", [(1, 90.0, "bl", "hook", "ok"),   # bl: asked
                                                                        (2, 205.0, "v2", "mine", "ok")])  # not a hook
            db.commit()
            db.close()
            hp = H.hook_pass(p, 50.0, [], os.path.join(d, "none.jsonl"))
        self.assertEqual(hp["classes"], {"0 rows, a model called": 1, "wrote rows, no model call": 1,
                                         "0 rows, no model call": 1})    # its calls, not the event's cost or time

    def test_a_read_only_database_file_serves(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.db(d)
            os.chmod(p, 0o444)                        # a writer would fail to open a read-only file for writing
            try:
                self.assertEqual(H.hook_pass(p, 0.0, [], os.path.join(d, "none.jsonl"))["events"], 4)
            finally:
                os.chmod(p, 0o644)


class TestTheLedgerIds(unittest.TestCase):

    def test_a_span_a_variant_and_a_moment_resolve_to_the_ledger_row(self):
        pk = {"spotlight": {"pool": {"snapped": {"w1": {"from": "m1~trim"}, "w2": {"from": "m2"}}}}}
        inp = {"moments": [{"moment_id": "m1", "mined": {"ledger_moment_id": "L1"}},
                           {"moment_id": "m2", "mined": {"ledger_moment_id": "L2"}}]}
        lmap = H.ledger_of([("ledger_1", pk, inp)])
        self.assertEqual([H.ledger_id(i, lmap) for i in ("w1", "w2", "m1", "m1~trim", "zz")],
                         ["L1", "L2", "L1", "L1", "zz"])


class B:
    def __init__(self, vendor):
        self.vendor, self.family = vendor, vendor


class FakeRouter:
    def __init__(self, chain, spent=0.0):
        self._chain, self._spent, self.down, self.chains = chain, spent, set(), {}
        self.backends = {"heimdall:qwen": B("heimdall/qwen"), "heimdall:glm": B("heimdall/glm"), "xai:grok": B("xai"),
                         "openai:gpt": B("openai")}          # the vendors as providers.HeimdallBackend gives them

    def chain(self, role, kind=None):
        return list(self.chains.get(f"{role}:{kind}") or (["openai:gpt"] if role == "angle_write" else self._chain))

    def spent(self):
        return self._spent


class TestTheCalibration(unittest.TestCase):

    def test_the_drivers_router_asks_the_hook_job_on_heimdall_only(self):
        with tempfile.TemporaryDirectory() as d:
            r = H.build_router(spend_path=os.path.join(d, "SPEND.json"))
        chain = r.chain("coherence_verdict", "hook")
        self.assertTrue(chain and all(r.backends[n].vendor.split("/")[0] == "heimdall" for n in chain), chain)
        self.assertNotIn("xai:grok-4.20-0309-reasoning", chain)
        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 88's order, Grok removed
        self.assertEqual((r.limit_usd, r.limit_basis), (H.LIMIT_USD, "reported"))

    def test_heimdall_only_and_refused_without_one(self):
        self.assertEqual(H.heimdall_hook_chain(FakeRouter(["heimdall:qwen", "xai:grok", "heimdall:glm"])),
                         ["heimdall:qwen", "heimdall:glm"])
        with self.assertRaises(RuntimeError):
            H.heimdall_hook_chain(FakeRouter(["xai:grok"]))

    def test_production_writers_no_cache_every_seed_and_the_stop(self):
        asked = []

        def rate(router, ms, ctx, wv, wf, cache="unset", seed=None):
            asked.append((cache, seed, sorted(wv)))
            return {m["moment_id"]: {"rating": 4} for m in ms}, None
        refs = [{"moment_id": "ref-a", "text": "t"}]
        runs = H.calibrate(FakeRouter(["heimdall:qwen"]), refs, None, seeds=(7, 8), stop_usd=0.25, rate=rate)
        self.assertEqual(asked, [(None, 7, ["openai"]), (None, 8, ["openai"])])   # no cache; the writers' vendor
        self.assertEqual([r["seed"] for r in runs], [7, 8])
        asked.clear()
        runs = H.calibrate(FakeRouter(["heimdall:qwen"], spent=0.25), refs, None, seeds=(7,), stop_usd=0.25,
                           rate=rate)
        self.assertEqual((asked, runs[0]["ratings"]), ([], {}))                  # at the stop: no call
        self.assertIn("stopped", runs[0]["error"])

    def test_a_missing_reference_is_recorded_and_the_rest_are_kept(self):
        refs = H.ref_moments([("gone", "a reference that is not there", "/nonexistent/PIN.json")] + H.REFS[:1])
        self.assertEqual((refs[0]["moment_id"], "error" in refs[0], refs[1]["moment_id"]),
                         ("ref-gone", True, "ref-preview"))
        self.assertTrue(refs[1]["text"])

    def test_the_approved_hooks_get_ids_no_production_cache_entry_can_answer(self):
        refs = H.ref_moments()
        self.assertEqual([r["moment_id"] for r in refs], [f"ref-{k}" for k, _, _ in H.REFS])
        cache = json.load(open(os.path.join(H.PROOF, "HOOK_CACHE.json")))
        self.assertFalse(any(k.split(":")[0].startswith("ref-") for k in cache))
        self.assertTrue(all(r["text"] for r in refs))


class TestTheDriverEndToEnd(unittest.TestCase):
    """main() itself, with the calibration on: the run of 11:52 ET Nov 15 died at an import its tests never reached
    (proof_saved_runs, another test folder's module). The router and the one paid call are stubbed; everything else is
    the driver's own path, writing into a temporary folder."""

    def test_main_runs_the_calibration_and_writes_every_part(self):
        from unittest import mock
        import package as PK
        asked = []

        def rate(router, ms, ctx, wv, wf, cache="unset", seed=None):
            asked.append((len(ms), cache, seed, ctx.channel("no-such-channel") is None))
            return {m["moment_id"]: {"scroll": 4, "alone": 4, "setup": 4, "rating": 4, "why": "w",
                                     "backend": "heimdall:qwen"} for m in ms}, None
        with tempfile.TemporaryDirectory() as d:
            proof, out = os.path.join(d, "proof"), os.path.join(d, "proof", "hook112")
            os.makedirs(proof)
            with open(os.path.join(proof, "HOOK_CACHE.json"), "w") as f:
                json.dump({}, f)
            db = TestTheHookPass().db(d)
            with mock.patch.object(H, "PROOF", proof), mock.patch.object(H, "OUT", out), \
                    mock.patch.object(H, "QUEUE_DB", db), mock.patch.object(H, "LEDGER", os.path.join(d, "none")), \
                    mock.patch.object(H, "build_router", lambda *a, **k: FakeRouter(["heimdall:qwen"])), \
                    mock.patch.object(PK, "hook_ratings", rate), mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(H.main(["--since", "2026-11-13T16:15:00+00:00"]), 0)
            cal = json.load(open(os.path.join(out, "CALIBRATION.json")))
            self.assertEqual(sorted(os.listdir(out)), ["CALIBRATION.json", "FUNNEL.json", "HOOK_PASS.json",
                                                       "NEAR_MISSES.json", "REPORT.md"])
        self.assertEqual(asked, [(len(H.REFS), None, s, True) for s in H.SEEDS])   # every seed, no cache, a context
        self.assertEqual([r["seed"] for r in cal["runs"]], list(H.SEEDS))
        self.assertEqual(len(cal["refs"]), len(H.REFS))


if __name__ == "__main__":
    unittest.main()
