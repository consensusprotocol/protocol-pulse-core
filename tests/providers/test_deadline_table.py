#!/usr/bin/env python3
"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL (pipeline/deadline_table.py and its use in
providers.Router.effective_deadline and the ledger build). Offline: temporary record dirs and table files."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import deadline_table as DT  # noqa: E402
import providers as P  # noqa: E402

T0 = datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc)
DS, GLM, GROK = "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash", "xai:grok-4.20-0309-reasoning"


def records(d, rows):
    """rows: [(backend, role, seconds)] -> one recorded exchange each, as providers.Router._record writes them."""
    for i, (b, role, s) in enumerate(rows):
        os.makedirs(os.path.join(d, f"{i:02x}"[-2:]), exist_ok=True)
        with open(os.path.join(d, f"{i:02x}"[-2:], f"{i:064x}.json"), "w") as f:
            json.dump({"role": role, "backend": b, "seconds": s, "text": "{}"}, f)


class TestTable(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.rec = os.path.join(self.d.name, "replies")

    def tearDown(self):
        self.d.cleanup()

    def test_p90_times_one_and_a_half_inside_60_to_300_s(self):
        records(self.rec, [(DS, "context_verdict", s) for s in (100, 120, 140, 160, 180, 200, 220, 240, 260, 280)]
                + [(GLM, "context_verdict", s) for s in (5, 9, 12)]
                + [("heimdall:qwen/qwen3.8-27b", "context_verdict", s) for s in (30, 40, 50, 60)]
                + [("heimdall:slow/x", "context_verdict", s) for s in (400, 500, 600)]
                + [(GROK, "coherence_verdict", s) for s in (10, 20)])          # two answers: no row of its own
        t = DT.compute(self.rec, T0)
        r = t["rows"]
        self.assertEqual(r[f"{DS}|context_verdict"], {"n": 10, "p50": 190.0, "p90": 262.0, "deadline_s": 300.0})
        self.assertEqual(r[f"{GLM}|context_verdict"]["deadline_s"], 60.0)                  # the floor
        self.assertEqual(r["heimdall:qwen/qwen3.8-27b|context_verdict"]["deadline_s"], 85.5)   # 57 x 1.5
        self.assertEqual(r["heimdall:slow/x|context_verdict"]["deadline_s"], 300.0)          # the ceiling
        self.assertNotIn(f"{GROK}|coherence_verdict", r)                                       # under MIN_N
        self.assertEqual((t["computed_at"], DT.deadline(t, DS, "context_verdict"), DT.deadline(t, GROK, "x")),
                         ("2026-11-14T17:00:00Z", 300.0, None))

    def test_a_record_that_cannot_be_read_or_has_no_positive_time_is_skipped(self):
        records(self.rec, [(DS, "context_verdict", s) for s in (10, 20, 30)] +
                [(DS, "context_verdict", bad) for bad in (0, -5, None, "slow", True)])
        os.makedirs(os.path.join(self.rec, "zz"), exist_ok=True)
        with open(os.path.join(self.rec, "zz", "broken.json"), "w") as f:
            f.write("{ broken")
        with open(os.path.join(self.rec, "zz", "nan.json"), "w") as f:
            f.write('{"role": "context_verdict", "backend": "%s", "seconds": NaN}' % DS)
        with open(os.path.join(self.rec, "zz", "list.json"), "w") as f:
            f.write('[{"role": "context_verdict", "backend": "%s", "seconds": 5}]' % DS)   # not an object
        self.assertEqual(DT.compute(self.rec, T0)["rows"][f"{DS}|context_verdict"]["n"], 3)
        self.assertEqual(DT.deadline({"rows": {"a|b": {"deadline_s": "60"}}}, "a", "b"), None)   # no guess
        self.assertEqual(DT.deadline(None, "a", "b"), None)
        rows = {"rows": {"a|hi": {"deadline_s": 500}, "a|lo": {"deadline_s": 10}, "a|inf": {"deadline_s": float("inf")}}}
        self.assertEqual([DT.deadline(rows, "a", r) for r in ("hi", "lo", "inf")], [300.0, 60.0, None])   # 60-300 s

    def test_the_table_is_kept_a_day_then_recomputed_and_an_unreadable_one_is_recomputed(self):
        path = os.path.join(self.d.name, "TABLE.json")
        records(self.rec, [(DS, "context_verdict", s) for s in (100, 110, 120)])
        first = DT.load(path, self.rec, T0)
        self.assertTrue(os.path.exists(path))
        records(self.rec, [(DS, "context_verdict", s) for s in (10, 10, 10, 10, 10, 10, 10)])
        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=23)), first)          # within the day: kept
        again = DT.load(path, self.rec, T0 + timedelta(hours=24, seconds=1))                # a day later: the records
        self.assertNotEqual(again["rows"], first["rows"])
        self.assertEqual(again["computed_at"], "2026-11-15T17:00:01Z")
        with open(path, "w") as f:
            f.write("{ broken")
        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=25))["computed_at"], "2026-11-15T18:00:00Z")
        self.assertIn("deepseek-v4.1-flash context_verdict:", DT.text(again))
        self.assertEqual(DT.text(again, applies=lambda k: False), "")

    def test_with_no_record_dir_a_saved_table_is_never_overwritten(self):
        """glm, audit 20261114_1246 C1: a load with nothing to compute from (no record dir) gives an empty table (each
        gateway keeps its number) and leaves the saved one as it was."""
        path = os.path.join(self.d.name, "TABLE.json")
        records(self.rec, [(DS, "context_verdict", s) for s in (100, 110, 120)])
        DT.load(path, self.rec, T0)
        with open(path) as f:
            saved = f.read()
        cwd = os.getcwd()
        try:                                       # never the current directory's files (a record dir lives there)
            os.chdir(self.rec)
            records(os.path.join(self.rec, "x"), [(DS, "context_verdict", s) for s in (1, 2, 3)])
            os.chdir(os.path.join(self.rec, "x"))
            later = DT.load(path, None, T0 + timedelta(days=2))
        finally:
            os.chdir(cwd)
        self.assertEqual(later["rows"], {})
        with open(path) as f:
            self.assertEqual(f.read(), saved)


class TestRouter(unittest.TestCase):
    """providers.Router.effective_deadline: where a deadline applies today (the caller's, else the role's: the gateway's
    120 s on Heimdall), a verdict pair's own row replaces it; without a row, the number that applied; where none applies
    (Grok with no caller deadline, any writer) none is added. role_deadline keeps the gateway's number."""

    def router(self, table):
        d = tempfile.mkdtemp()
        cfg = os.path.join(d, "cfg.json")
        json.dump({"schema": "pp.providers/1",
                   "backends": {DS: {"vendor": "heimdall", "model": "deepseek", "family": "deepseek",
                                     "base_url": "http://x"},
                                GLM: {"vendor": "heimdall", "model": "glm", "family": "glm", "base_url": "http://x"},
                                GROK: {"vendor": "xai", "model": "grok", "family": "grok"}},
                   "roles": {"context_verdict": {"chain": [GLM, DS, GROK]}},
                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
                               "verdict_deadline_s": {"heimdall": 120}}}, open(cfg, "w"))
        return P.Router(cfg, env_path="/nonexistent", deadlines=table)

    TABLE = {"rows": {f"{DS}|context_verdict": {"n": 33, "p50": 165, "p90": 272, "deadline_s": 300.0},
                      f"{GROK}|context_verdict": {"n": 268, "p50": 46, "p90": 80, "deadline_s": 120.7},
                      f"{DS}|angle_write": {"n": 9, "p50": 20, "p90": 30, "deadline_s": 60.0}}}

    def test_the_model_s_own_deadline_where_one_applies(self):
        r = self.router(self.TABLE)
        e = lambda role, name, dl=None: r.effective_deadline(role, r.backends[name], dl)
        self.assertEqual(e("context_verdict", DS), 300.0)                   # the role's 120 s -> its own row
        self.assertEqual(e("context_verdict", GLM), 120.0)                  # no row: the gateway's
        self.assertIsNone(e("context_verdict", GROK))                       # none applies (no caller's): none added
        self.assertEqual(e("context_verdict", GROK, 120.0), 120.7)          # the first screen's 120 s -> its own row
        self.assertEqual(e("context_verdict", GLM, 120.0), 120.0)           # no row: the caller's
        self.assertEqual(e("context_verdict", DS, 30.0), 300.0)             # a row replaces the caller's number too
        self.assertEqual(e("angle_write", DS, 300.0), 300.0)                # a writer keeps its own (not a verdict)
        self.assertIsNone(e("angle_write", DS))
        self.assertEqual(self.router(None).effective_deadline("context_verdict", r.backends[DS]), 120.0)   # no table
        self.assertEqual(r.role_deadline("context_verdict", r.backends[DS]), 120.0)   # the gateway's number, as before
        self.assertIsNone(r.role_deadline("context_verdict", r.backends[GROK]))
        table = {"rows": dict(self.TABLE["rows"], **{f"{DS}|shadow86:context_verdict": {"deadline_s": 300.0},
                                                    f"{DS}|probe87:{DS}": {"deadline_s": 300.0}})}
        r = self.router(table)                       # glm, audit 20261114_1246 C2 M2: a shadow or a probe is no verdict
        self.assertEqual(r.effective_deadline("shadow86:context_verdict", r.backends[DS], 120.0), 120.0)
        self.assertEqual(r.effective_deadline(f"probe87:{DS}", r.backends[DS], 60.0), 60.0)

    def test_a_live_call_waits_its_own_deadline_and_the_breaker_measures_against_it(self):
        """Router.call itself: the deadline the call is held to (and the breaker's miss is measured against: ruling 99)
        is effective_deadline's; a recorded reply or replay never reaches it (unchanged)."""
        r = self.router(self.TABLE)
        held = []

        def within(seconds, fn, on_abandon=None, on_late=None):
            held.append(seconds)
            return fn()
        for b in r.backends.values():
            b.complete = lambda prompt, mt, seed, system=None: ('{"ok": 1}', {"in": 1, "out": 1}, 0.1)
        with mock.patch.object(P, "_within", within):
            for chain, dl in (([DS], None), ([GROK], 120.0), ([GROK], None), ([GLM], None)):
                r.chains["context_verdict"] = chain
                r.call("context_verdict", "p", 100, 7, deadline_s=dl)
            r.chains["angle_write"] = [DS]
            r.call("angle_write", "p", 100, 7, deadline_s=300.0)
        self.assertEqual(held, [300.0, 120.7, 120.0, 300.0])               # Grok with no deadline: not held at all

    def test_the_build_router_loads_the_table_from_its_own_records(self):
        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
        import proof_ledger as PLG
        import proof_ly as PL
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "DEADLINE_TABLE.json")
            with mock.patch.object(DT, "STATE", path):
                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
            self.assertTrue(os.path.exists(path))
            self.assertEqual(r.deadlines, DT.load(path, PL.REPLIES))
        app = PLG.applied(r)
        self.assertTrue(app(f"{GROK}|context_verdict"))           # the first screen's leg under heimdall_first
        self.assertFalse(app(f"{GROK}|coherence_verdict"))        # no deadline applies: none added
        self.assertFalse(app(f"{GROK}|shadow86:context_verdict"))           # not a verdict role
        self.assertTrue(app("heimdall:deepseek/deepseek-v4.1-flash|context_verdict"))
        self.assertTrue(app("heimdall:deepseek/deepseek-v4.1-flash|coherence_verdict"))   # the gateway's 120 s
        self.assertFalse(app("heimdall:deepseek/deepseek-v4.1-flash|angle_write"))


class TestTheBuildLine(unittest.TestCase):
    def test_ruling_101_s_line_reports_the_extra_spend(self):
        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
        import proof_ledger as PLG
        self.assertEqual(PLG.ruling_101_line(None), "")
        line = PLG.ruling_101_line({"parallel": True, "n_new": 37, "leg": DS, "est_wait_s": 1200.0, "asked": 37,
                                    "verdicts": 36, "usd": 0.37, "used": 10})
        self.assertIn("would have held the build about 20 min", line)
        self.assertIn("the second screen used 10, so about $0.2700 was spent that sequential would have saved", line)
        self.assertIn("about 2.0 min on", PLG.ruling_101_line({"parallel": False, "n_new": 21, "est_wait_s": 120.0,
                                                               "leg": GLM}))
        self.assertIn("not over 20", PLG.ruling_101_line({"parallel": False, "n_new": 4, "est_wait_s": None}))


if __name__ == "__main__":
    unittest.main()
