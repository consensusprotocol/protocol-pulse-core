#!/usr/bin/env python3
"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE (pipeline/heimdall_health.py and its use in
providers.Router). Offline: a temporary state file, the test's own clock, fake back-ends."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import heimdall_health as HH  # noqa: E402
import providers as P  # noqa: E402
from test_providers import Fake  # noqa: E402

T0 = datetime(2026, 11, 14, 2, 0, tzinfo=timezone.utc)


class TestHealth(unittest.TestCase):
    def setUp(self):
        HH._SEEN.clear()
        self.d = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.d.name, "HEALTH.json")
        self.ev = os.path.join(self.d.name, "DEADLINES.jsonl")
        self.md = os.path.join(self.d.name, "STATE.md")
        with open(self.md, "w") as f:
            f.write("21:00 ET: line one as it was.\n\n## a section\n")

    def tearDown(self):
        self.d.cleanup()

    def kw(self, t):
        return {"path": self.state, "now": t, "evidence": self.ev, "state_md": self.md}

    def test_fifteen_minutes_with_no_family_answering_is_plan_b_and_every_switch_is_on_record(self):
        self.assertEqual(HH.note(False, **self.kw(T0)), "heimdall_first")
        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=14, seconds=59))), "heimdall_first")
        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=15))), "plan_b")
        st = json.load(open(self.state))
        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b"])
        with open(self.ev) as f:
            self.assertEqual([json.loads(x)["kind"] for x in f], ["switch"])
        first = open(self.md).read().split("\n")[0]
        self.assertTrue(first.endswith("| 21:00 ET: line one as it was."), first)     # one physical line, prepended
        self.assertIn("ET: SWITCHED TO PLAN B (NO ANSWER OF ANY KIND (NO CALL AND NO PROBE ANSWERED) FOR 15 MINUTES",
                      first)

    def test_one_answer_stops_the_clock(self):
        HH.note(False, **self.kw(T0))
        HH.note(True, **self.kw(T0 + timedelta(minutes=10)))           # any family answering: not down
        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=20))), "heimdall_first")
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=34))), "heimdall_first")
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=35))), "plan_b")   # idle: the clock still runs

    def test_ruling_87_amended_an_answered_probe_resets_the_clock(self):
        """RULING 87 AMENDED (10:06 Nov 14), the false outage of 09:16-09:22 replayed: one 502 at 14:01:08Z, then probes
        answering every 2 minutes and no real call. 'Down' is no answer of ANY kind for 15 minutes."""
        k = lambda m: self.kw(T0 + timedelta(minutes=m))
        HH.note(False, **k(0))                                           # one failed call starts the clock
        for m in range(2, 22, 2):
            self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=m)) or m > 2)
            self.assertEqual(HH.probe_result(True, **k(m)), "heimdall_first")
            self.assertEqual(HH.mode(**k(m + 1)), "heimdall_first")
        st = json.load(open(self.state))
        self.assertIsNone(st["failing_since_utc"])                       # reset by the first good probe
        self.assertEqual(st["last_answer_utc"], "2026-11-14T02:20:00Z")   # an answer of any kind
        self.assertEqual(st["switches"], [])
        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=30)))     # no clock: no probe
        self.assertEqual(open(self.md).read().split("\n")[0], "21:00 ET: line one as it was.")   # no switch line

    def test_one_failed_call_then_one_good_probe_then_silence_is_never_down(self):
        HH.note(False, **self.kw(T0))
        self.assertEqual(HH.probe_result(True, **self.kw(T0 + timedelta(minutes=2))), "heimdall_first")
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(hours=3))), "heimdall_first")

    def test_failing_probes_leave_the_clock_running_and_a_failed_probe_never_starts_it(self):
        self.assertEqual(HH.probe_result(False, **self.kw(T0)), "heimdall_first")
        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # only note(False) starts the clock
        HH.note(False, **self.kw(T0))
        for m in range(2, 16, 2):
            self.assertEqual(HH.probe_result(False, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=15))), "plan_b")   # zero answers for 15 minutes
        self.assertIn("NO ANSWER OF ANY KIND", open(self.md).read().split("\n")[0])

    def test_a_late_probe_report_does_not_reset_a_newer_clock(self):
        """pp-ingest reports a probe at its next tick with the probe's own time (up to PROBE_EVERY_S late): an answer
        timed before the failure that started the clock proves nothing about after it."""
        HH.note(False, **self.kw(T0 + timedelta(minutes=10)))
        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=9)))       # answered at 9, reported after the 10 failure
        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:10:00Z")
        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=10)))      # answered AT the failure's second: not
        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # before it, so it resets (audit 1008 C1)
        HH.note(False, **self.kw(T0 + timedelta(minutes=10)))
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=25))), "plan_b")
        HH.note(False, **self.kw(T0 + timedelta(minutes=40)))
        HH.probe_result(True, **self.kw(T0 + timedelta(minutes=41)))      # in plan_b: one answer is a streak of 1,
        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=42))), "plan_b")   # back only after 3 (as before)

    def test_in_plan_b_an_answered_probe_resets_the_clock_and_plan_b_still_needs_3_in_a_row(self):
        """pp-ingest's ruling-98 route opens on plan_b AND failing_since_utc 20 minutes old (read as 'no answer of any
        kind'): a probe answer at minute 17 of plan_b restarts that clock; closing plan_b stays at 3 answers in a row."""
        k = lambda m: self.kw(T0 + timedelta(minutes=m))
        HH.note(False, **k(0))
        self.assertEqual(HH.mode(**k(15)), "plan_b")
        HH.note(False, **k(16))                                          # still failing inside plan_b
        self.assertEqual(HH.probe_result(True, **k(17)), "plan_b")
        st = json.load(open(self.state))
        self.assertEqual((st["failing_since_utc"], st["last_answer_utc"], st["probe_streak"]),
                         (None, "2026-11-14T02:17:00Z", 1))
        self.assertEqual(HH.probe_result(False, **k(19)), "plan_b")      # a miss: the streak is 0, the clock stays off
        self.assertIsNone(json.load(open(self.state))["failing_since_utc"])   # (a failed probe never starts it)
        HH.note(False, **k(20))                                           # a failed call starts it again
        self.assertEqual(json.load(open(self.state))["failing_since_utc"], "2026-11-14T02:20:00Z")
        self.assertEqual([HH.probe_result(True, **k(m)) for m in (21, 23, 25)], ["plan_b", "plan_b", "heimdall_first"])

    def test_the_probe_asks_the_family_that_failed(self):
        """RULING 87 AMENDED: a probe is a real model call on the family that failed. The builder's probe asks deepseek,
        glm and qwen; pp-ingest's asks qwen, glm and muse. While the clock runs, a prober that can ask none of the
        failed families leaves the slot to the one that can; in plan_b any prober claims (plan_b can always close)."""
        at = lambda m: T0 + timedelta(minutes=m)
        mine, theirs = ["deepseek", "glm", "qwen"], ["glm", "muse", "qwen"]
        HH.note(False, family="muse", **self.kw(at(0)))                  # pp-ingest's muse 502
        self.assertEqual(json.load(open(self.state))["failing_families"], ["muse"])
        self.assertFalse(HH.probe_due(self.state, at(2), who="pp-selectid", families=mine))   # cannot ask muse
        self.assertTrue(HH.probe_due(self.state, at(2), who="pp-ingest", families=theirs))
        HH.note(False, family="deepseek", **self.kw(at(3)))              # then the builder's deepseek fails too
        self.assertEqual(json.load(open(self.state))["failing_families"], ["deepseek", "muse"])
        self.assertTrue(HH.probe_due(self.state, at(4), who="pp-selectid", families=mine))    # it can ask one
        HH.probe_result(True, **self.kw(at(4)))                          # any answer: the clock and the families reset
        st = json.load(open(self.state))
        self.assertEqual((st["failing_since_utc"], st["failing_families"]), (None, []))
        self.assertFalse(HH.probe_due(self.state, at(8), families=mine))  # no clock: no probe
        HH.note(False, family="muse", **self.kw(at(10)))
        self.assertTrue(HH.probe_due(self.state, at(12)))                # families not named: claims as before
        HH.note(False, family="muse", **self.kw(at(25)))                 # nobody answered for 15 minutes: plan_b
        self.assertEqual(HH.mode(**self.kw(at(25))), "plan_b")
        self.assertTrue(HH.probe_due(self.state, at(26), who="pp-selectid", families=mine))   # plan_b: any prober
        st = json.load(open(self.state))
        st["mode"], st["failing_families"], st["failing_since_utc"] = "heimdall_first", "muse", "2026-11-14T02:30:00Z"
        json.dump(st, open(self.state, "w"))                             # a malformed field keeps no prober out
        self.assertTrue(HH.probe_due(self.state, at(31), families=mine))

    def test_a_clock_with_no_family_recorded_lets_a_named_prober_claim(self):
        """pp-ingest's current calls name no family: a clock they start records none, and then any prober claims,
        families named or not (audit 1008 C2, glm N4)."""
        HH.note(False, **self.kw(T0))
        self.assertEqual(json.load(open(self.state))["failing_families"], [])
        self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=2), families=["deepseek", "glm", "qwen"]))

    def test_the_probe_every_2_minutes_and_back_after_3_answers_in_a_row(self):
        k = lambda m: self.kw(T0 + timedelta(minutes=m))
        self.assertFalse(HH.probe_due(self.state, T0))                  # healthy: no probe
        HH.note(False, **k(0))
        self.assertTrue(HH.probe_due(self.state, T0))
        HH.note(False, **k(15))                                          # down
        self.assertEqual(HH.probe_result(True, **k(16)), "plan_b")
        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=17)))      # 2 minutes apart
        self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=18)))
        self.assertEqual(HH.probe_result(False, **k(18)), "plan_b")      # a miss resets the streak
        self.assertEqual(HH.probe_result(True, **k(20)), "plan_b")
        self.assertEqual(HH.probe_result(True, **k(22)), "plan_b")
        self.assertEqual(HH.probe_result(True, **k(24)), "heimdall_first")
        st = json.load(open(self.state))
        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b", "heimdall_first"])
        self.assertIsNone(st["failing_since_utc"])
        self.assertIn("BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW)",
                      open(self.md).read().split("\n")[0])

    def test_two_probers_share_one_probe_per_slot(self):
        """pp-ingest REQUESTS R12 (02:3x ET Nov 14): this router's probe and pp-ingest's watcher probe the same state;
        a due probe is CLAIMED, so one slot gives one probe and 3 in a row is 3 slots."""
        k = lambda m: self.kw(T0 + timedelta(minutes=m))
        HH.note(False, **k(0))
        HH.note(False, **k(15))                                          # down: plan_b
        at = lambda m: T0 + timedelta(minutes=m)
        self.assertEqual([HH.probe_due(self.state, at(16), who=w) for w in ("pp-selectid", "pp-ingest")],
                         [True, False])                                  # the second prober finds the slot taken
        self.assertEqual(json.load(open(self.state))["last_probe_by"], "pp-selectid")
        HH.probe_result(True, **k(16))
        self.assertEqual([HH.probe_due(self.state, at(17), who=w) for w in ("pp-selectid", "pp-ingest")],
                         [False, False])
        rounds = 1
        for m in (18, 20):
            claims = [HH.probe_due(self.state, at(m), who=w) for w in ("pp-ingest", "pp-selectid")]
            self.assertEqual(claims, [True, False])
            rounds += 1
            mode = HH.probe_result(True, **k(m))
            self.assertEqual(json.load(open(self.state))["last_probe_by"], "pp-ingest")   # the claimer, kept by the
            #   report (probe_result never writes last_probe_by) (audit 0230 C2: glm, grok)
        self.assertEqual((rounds, mode), (3, "heimdall_first"))         # three slots, three answers

    def test_a_drill_is_recorded_never_counted_and_answers_write_once_per_heartbeat(self):
        HH._SEEN.clear()
        for m in range(0, 40, 5):                                        # 40 minutes of drill failures
            self.assertEqual(HH.note(False, drill=True, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
        st = json.load(open(self.state))
        self.assertEqual((st["drills"], st["failing_since_utc"], st["notes"]), (8, None, 0))
        HH.note(True, **self.kw(T0))
        HH.note(True, **self.kw(T0 + timedelta(seconds=5)))              # inside the heartbeat: not written
        self.assertEqual(json.load(open(self.state))["notes"], 1)
        HH.note(False, **self.kw(T0 + timedelta(seconds=6)))             # a failure is always written
        HH.note(True, **self.kw(T0 + timedelta(seconds=7)))              # and the next answer too
        st = json.load(open(self.state))
        self.assertEqual((st["notes"], st["failing_since_utc"]), (3, None))
        HH._SEEN.clear()

    def test_an_unreadable_state_is_never_guessed(self):
        with open(self.state, "w") as f:
            f.write("{ broken")
        for fn in (lambda: HH.note(True, **self.kw(T0)), lambda: HH.mode(**self.kw(T0))):
            with self.assertRaises(HH.HealthUnreadable):
                fn()
        self.assertEqual(open(self.state).read(), "{ broken")
        r = P.Router.__new__(P.Router)                                     # the router: no verdict, never a crash
        r.health, r.deadline_log, r.state_md, r.routing = self.state, None, None, "heimdall_first"
        with self.assertRaises(P.ProviderError):                           # (audit 0108 C1, glm)
            r.mode()


class TestRouterPlanB(unittest.TestCase):
    """providers.Router: a Heimdall verdict or writer call's outcome is noted; in plan_b the roles of plan_b_chains run
    on them at once (Grok first)."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.cfg = os.path.join(self.d.name, "cfg.json")
        json.dump({"schema": "pp.providers/1",
                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek",
                                                      "family": "deepseek"}},
                   "roles": {"coherence_verdict": {"chain": ["heimdall:deepseek", "xai:grok"]},
                             "mine": {"chain": ["heimdall:deepseek"]}},
                   "routing": {"mode": "today", "verdict_roles": ["coherence_verdict"]}}, open(self.cfg, "w"))
        self.state = os.path.join(self.d.name, "HEALTH.json")

    def tearDown(self):
        self.d.cleanup()

    def router(self):
        r = P.Router(self.cfg, env_path="/nonexistent", health=self.state,
                     plan_b_chains={"coherence_verdict": ["xai:grok"]})
        h = P.HeimdallBackend("heimdall:deepseek", {"model": "deepseek", "family": "deepseek"}, "/nonexistent")
        h.complete = lambda *a, **k: ("d", {"in": 1, "out": 1}, 0.01)
        r.backends = {"xai:grok": Fake("xai:grok", "xai", answer="x", family="grok"), "heimdall:deepseek": h}
        r.start_probe = lambda *a, **k: None                              # no thread in a unit test
        return r

    def test_outcomes_are_noted_and_plan_b_takes_the_chain(self):
        r = self.router()
        self.assertEqual(r.call("coherence_verdict", "p").backend, "heimdall:deepseek")
        st = json.load(open(self.state))
        self.assertIsNotNone(st["last_answer_utc"])
        self.assertEqual(st["notes"], 1)
        r.call("mine", "p")                                               # not a verdict or a write: not noted
        self.assertEqual(json.load(open(self.state))["notes"], 1)
        HH.note(False, self.state, now=datetime.now(timezone.utc) - timedelta(minutes=16))
        HH.note(False, self.state)                                        # 16 minutes with no answer: plan_b
        self.assertEqual(r.mode(), "plan_b")
        self.assertEqual(r.chain("coherence_verdict"), ["xai:grok"])
        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")   # the whole pin stage, at once
        self.assertEqual(r.chain("mine"), ["heimdall:deepseek"])          # a role Plan B does not name: as is

    def test_a_probe_round_reaches_a_family_marked_down_and_restores_the_mark_when_it_fails(self):
        r = self.router()
        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
        self.assertTrue(r.probe_once(["heimdall:deepseek"]))             # it answers now: the mark is lifted
        self.assertNotIn("heimdall:deepseek", r.down)

        def down(*a, **k):
            raise P.Unavailable("HTTP 503")
        r.backends["heimdall:deepseek"].complete = down
        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
        self.assertFalse(r.probe_once(["heimdall:deepseek"]))
        self.assertIn("heimdall:deepseek", r.down)                       # still down: marked as before
        self.assertFalse(os.path.exists(os.path.join(self.d.name, "rec")))   # a probe is never recorded

    def test_the_probe_thread_names_its_families_to_the_slot_claim(self):
        """RULING 87 AMENDED: the builder's probe asks its own Heimdall families, and says which to probe_due."""
        import time as _t
        from unittest import mock
        r, seen = self.router(), []

        def due(path, now=None, who="", families=None):
            seen.append((who, families))
            return False
        with mock.patch.object(HH, "probe_due", due):
            P.Router.start_probe(r, every_s=3600.0)       # one look, then an hour asleep (a daemon thread)
            for _ in range(200):
                if seen:
                    break
                _t.sleep(0.01)
        self.assertEqual(seen, [("pp-selectid probe", ["deepseek"])])

    def test_a_failing_heimdall_call_is_noted_as_not_answered(self):
        r = self.router()

        def down(*a, **k):
            raise P.Unavailable("HTTP 503")
        r.backends["heimdall:deepseek"].complete = down
        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")    # ruling 82's chain moved on
        st = json.load(open(self.state))
        self.assertIsNotNone(st["failing_since_utc"])
        self.assertIsNone(st["last_answer_utc"])
        self.assertEqual(st["failing_families"], ["deepseek"])          # ruling 87 amended: the family to probe



class TestLocalJudge(unittest.TestCase):
    """RULING 87: the integrator's GPU0 judge (Plan B, one outside family): a request file in this worktree, the answer
    read from its results; an error or no answer in time is no verdict; the wait outlasts ruling 82's 120 s."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.req, self.res = os.path.join(self.d.name, "req"), os.path.join(self.d.name, "res")
        os.makedirs(self.res)
        self.b = P.LocalJudgeBackend("local_judge:gemma3:27b", {"model": "gemma3:27b", "family": "gemma",
                                                                "deadline_floor_s": 2400}, "/nonexistent")
        self.b.REQUESTS, self.b.RESULTS, self.b.POLL_S = self.req, self.res, 0.05

    def tearDown(self):
        self.d.cleanup()

    def answer_when_asked(self, body):
        import threading
        import time as _t

        def run():                                   # answers the one request that has no answer yet
            for _ in range(500):
                for n in sorted(os.listdir(self.req)) if os.path.isdir(self.req) else []:
                    if not n.endswith(".json"):
                        continue
                    rid = n[:-len(".json")]
                    rq = json.load(open(os.path.join(self.req, n)))
                    import hashlib                       # the integrator's prompt_id
                    pid = hashlib.sha256(json.dumps([rq["prompt"], rq["max_tokens"], rq["seed"]]).encode()) \
                        .hexdigest()[:20]
                    out = os.path.join(self.res, f"{rid}.{pid}.json")
                    if not os.path.exists(out):
                        with open(out, "w") as f:
                            json.dump(dict(body, request_id=rid, prompt_id=pid), f)
                        return
                _t.sleep(0.02)
        threading.Thread(target=run, daemon=True).start()

    def test_a_request_is_written_and_its_answer_read(self):
        self.answer_when_asked({"family": "step_a", "text": '{"excerpts": []}', "error": None})
        text, usage, secs = self.b.complete("the step A prompt", 4000, 7)
        self.assertEqual((text, usage["in"], usage["out"]), ('{"excerpts": []}', 0, 0))
        stray = os.path.join(self.res, "pp-selectid.x.0000.json")         # another answer's file is never read
        json.dump({"request_id": "other", "text": "{}"}, open(stray, "w"))
        (name,) = os.listdir(self.req)
        rq = json.load(open(os.path.join(self.req, name)))
        self.assertEqual({k: rq[k] for k in ("family", "prompt", "max_tokens", "seed")},
                         {"family": "step_a", "prompt": "the step A prompt", "max_tokens": 4000, "seed": 7})
        self.assertTrue(self.b.free())

    def test_an_error_or_no_answer_is_no_verdict(self):
        self.answer_when_asked({"family": "step_a", "text": "", "error": "GPU0 busy"})
        with self.assertRaises(P.RequestRejected):
            self.b.complete("p", 100, 7)
        self.b.WAIT_S = 0.2
        with self.assertRaises(P.Unavailable):
            self.b.complete("q", 100, 7)
        with self.assertRaises(P.RequestRejected):
            self.b.complete("q", 100, 7, system="no system message")

    def test_a_torn_answer_file_is_read_again_never_final(self):
        """Audit 0108 C1 (glm): an answer file read while it is being written is polled again until the deadline."""
        import threading
        import time as _t

        def run():
            for _ in range(500):
                for n in sorted(os.listdir(self.req)) if os.path.isdir(self.req) else []:
                    if not n.endswith(".json"):
                        continue
                    rid = n[:-len(".json")]
                    rq = json.load(open(os.path.join(self.req, n)))
                    import hashlib
                    pid = hashlib.sha256(json.dumps([rq["prompt"], rq["max_tokens"], rq["seed"]]).encode()) \
                        .hexdigest()[:20]
                    out = os.path.join(self.res, f"{rid}.{pid}.json")
                    with open(out, "w") as f:
                        f.write('{"request_id": "' + rid)                   # half written
                    _t.sleep(0.2)
                    with open(out, "w") as f:
                        json.dump({"request_id": rid, "prompt_id": pid, "text": "{}", "error": None}, f)
                    return
                _t.sleep(0.02)
        threading.Thread(target=run, daemon=True).start()
        self.assertEqual(self.b.complete("torn", 100, 7)[0], "{}")

    def test_the_wait_outlasts_the_120_s_deadline_and_state_line_1_says_so_once(self):
        cfg = os.path.join(self.d.name, "cfg.json")
        json.dump({"schema": "pp.providers/1",
                   "backends": {"local_judge:gemma3:27b": {"vendor": "local_judge", "model": "gemma3:27b",
                                                           "family": "gemma", "deadline_floor_s": 2400}},
                   "roles": {"context_verdict": {"chain": ["local_judge:gemma3:27b"]}}}, open(cfg, "w"))
        md = os.path.join(self.d.name, "STATE.md")
        open(md, "w").write("21:50 ET: line one.\n")
        r = P.Router(cfg, env_path="/nonexistent", state_md=md)
        r.backends["local_judge:gemma3:27b"] = self.b
        seen = {}
        orig = P._within

        def spy(seconds, fn, **kw):
            seen["deadline"] = seconds
            return orig(seconds, fn, **kw)
        P._within = spy
        try:
            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
            r.call("context_verdict", "p", 100, 7, deadline_s=120.0)
            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
            r.call("context_verdict", "p2", 100, 7, deadline_s=120.0)
        finally:
            P._within = orig
        self.assertEqual(seen["deadline"], 2400.0)
        first = open(md).read().split("\n")[0]
        self.assertEqual(first.count("PLAN B WITH ONE OUTSIDE FAMILY"), 1)
        self.assertTrue(first.endswith("| 21:50 ET: line one."))

if __name__ == "__main__":
    unittest.main()
