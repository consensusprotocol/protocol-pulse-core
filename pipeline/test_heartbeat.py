"""Ruling 133 R16: the services' heartbeats (pipeline/heartbeat.py), their writers and the watchdog's reading."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import heartbeat  # noqa: E402
import session_watchdog as W  # noqa: E402
import telegram  # noqa: E402

DAY = datetime(2026, 11, 23, 18, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()   # 18:00 ET: lines are sent


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="hb_test_")
        self.addCleanup(shutil.rmtree, self.d, True)
        p = mock.patch.object(heartbeat, "DIR", os.path.join(self.d, "hb"))
        p.start()
        self.addCleanup(p.stop)
        heartbeat._state.clear()
        self.addCleanup(heartbeat._state.clear)

    def rec(self, name):
        with open(os.path.join(self.d, "hb", f"{name}.json")) as f:
            return json.load(f)


class TestHeartbeat(Base):
    def test_mark_pass_writes_the_pass(self):
        heartbeat.mark_pass("svc", now=100.0, served=2)
        heartbeat.mark_pass("svc", now=160.0, served=0)
        r = self.rec("svc")
        self.assertEqual((r["service"], r["pid"], r["at"], r["pass_at"], r["passes"], r["info"]),
                         ("svc", os.getpid(), 160.0, 160.0, 2, {"served": 0}))
        self.assertEqual(heartbeat.read("svc")["passes"], 2)
        self.assertIsNone(heartbeat.read("nothing"))

    def test_start_beats_without_a_pass(self):
        import threading
        stop = threading.Event()
        self.addCleanup(stop.set)
        heartbeat.start("svc", beat_s=0.05, stop=stop)
        first = self.rec("svc")["at"]
        time.sleep(0.3)
        r = self.rec("svc")
        self.assertGreater(r["at"], first)                       # the thread refreshes it
        self.assertIsNone(r["pass_at"])                           # no pass was finished

    def test_a_failed_write_never_stops_the_service(self):
        with open(os.path.join(self.d, "hb"), "w") as f:          # DIR is a file: every write fails
            f.write("x")
        rec = heartbeat.mark_pass("svc", served=1)                # no exception
        self.assertEqual(rec["passes"], 1)


class TestServiceWriters(Base):
    def test_lock_precheck_marks_every_once_pass(self):
        import lock_precheck as LP
        with mock.patch.object(LP, "serve_once", return_value=3), mock.patch.object(LP, "ROOT", self.d):
            self.assertEqual(LP.main(["once"]), 0)
        r = self.rec("lock_precheck")
        self.assertEqual((r["passes"], r["info"]), (1, {"served": 3}))

    def test_scorer_serve_beats_and_marks(self):
        import stand_alone_scorer as S

        class Stop(Exception):
            pass
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), \
                mock.patch.object(S, "ROOT", self.d), mock.patch.object(S, "serve_once", return_value=0), \
                mock.patch.object(S, "pending", return_value=[]), \
                mock.patch.object(heartbeat, "start") as start, \
                mock.patch.object(S.time, "sleep", side_effect=Stop):
            with self.assertRaises(Stop):
                S.main(["serve"])
        start.assert_called_once_with("scorer")
        self.assertEqual((self.rec("scorer")["passes"], self.rec("scorer")["info"]), (1, {"served": 0}))

    def test_scorer_once_writes_no_heartbeat(self):
        import stand_alone_scorer as S
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), \
                mock.patch.object(S, "ROOT", self.d), mock.patch.object(S, "serve_once", return_value=0), \
                mock.patch.object(S, "pending", return_value=[]):
            self.assertEqual(S.main(["once"]), 0)
        self.assertIsNone(heartbeat.read("scorer"))

    def test_word_pass_beats_and_marks_each_cycle(self):
        import word_pass_worker as WP

        class Stop(Exception):
            pass
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "1"}), \
                mock.patch.object(WP, "cycle", return_value={"picked": 0, "blocked": None}), \
                mock.patch.object(heartbeat, "start") as start, \
                mock.patch.object(WP.time, "sleep", side_effect=Stop):
            with self.assertRaises(Stop):
                WP.main([])
        start.assert_called_once_with("word_pass")
        self.assertEqual(self.rec("word_pass")["info"], {"picked": 0, "blocked": None})

    def test_judge_launcher_marks_each_serve_once_and_leaves_local_judge_unchanged(self):
        import judge_serve as J
        import local_judge as LJ
        sha = LJ.judge_sha()
        orig = LJ.serve_once

        def fake_main(argv):
            self.assertEqual(argv, ["serve"])
            LJ.serve_once(log=print)                              # what main() does each pass
            return 0
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), \
                mock.patch.object(J, "_serve_once", return_value=2), \
                mock.patch.object(LJ, "main", side_effect=fake_main), \
                mock.patch.object(heartbeat, "start") as start:
            try:
                self.assertEqual(J.main(), 0)
            finally:
                LJ.serve_once = orig
        start.assert_called_once_with("judge")
        self.assertEqual((self.rec("judge")["passes"], self.rec("judge")["info"]), (1, {"served": 2}))
        self.assertEqual(LJ.judge_sha(), sha)

    def test_the_real_local_judge_main_calls_the_wrapped_serve_once(self):
        import judge_serve as J
        import local_judge as LJ
        orig = LJ.serve_once

        class Stop(Exception):
            pass
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}), mock.patch.object(LJ, "ROOT", self.d), \
                mock.patch.object(J, "_serve_once", return_value=0), mock.patch.object(heartbeat, "start"), \
                mock.patch.object(LJ.time, "sleep", side_effect=Stop):
            try:
                with self.assertRaises(Stop):                     # main's idle sleep after its first pass
                    J.main()
            finally:
                LJ.serve_once = orig
        self.assertEqual((self.rec("judge")["passes"], self.rec("judge")["info"]), (1, {"served": 0}))

    def test_judge_launcher_refuses_off_gpu0_before_any_heartbeat(self):
        import judge_serve as J
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}):
            with self.assertRaises(SystemExit):
                J.main()
        self.assertIsNone(heartbeat.read("judge"))


class TestWatchdogReads(Base):
    def setUp(self):
        super().setUp()
        self.paths = {"log": os.path.join(self.d, "wd.log"), "status": os.path.join(self.d, "status.json"),
                      "state": os.path.join(self.d, "state.json"), "moment_ledger": os.path.join(self.d, "ml"),
                      "builds": os.path.join(self.d, "ledger_*"), "spend": os.path.join(self.d, "spend.json"),
                      "wordpass_log": os.path.join(self.d, "wp.log"), "heartbeats": os.path.join(self.d, "hb"),
                      "transcript_log": os.path.join(self.d, "ti.log")}
        open(self.paths["transcript_log"], "w").close()
        os.utime(self.paths["transcript_log"], (DAY - 60, DAY - 60))

    def write(self, name, at, pass_at=None, pid=None):
        os.makedirs(self.paths["heartbeats"], exist_ok=True)
        with open(os.path.join(self.paths["heartbeats"], f"{name}.json"), "w") as f:
            json.dump({"service": name, "pid": pid or os.getpid(), "at": at, "pass_at": pass_at, "passes": 1,
                       "info": {}}, f)

    def all_fresh(self):
        for name, _ in W.HEARTBEATS:
            self.write(name, DAY - 60, DAY - 60)

    def test_fresh_heartbeats_say_nothing(self):
        self.all_fresh()
        f, view = W.heartbeat_findings({}, DAY, self.paths)
        self.assertEqual(f, [])
        self.assertEqual(sorted(view), sorted([n for n, _ in W.HEARTBEATS] + [W.TRANSCRIPT_KEY]))

    def test_a_heartbeat_older_than_20_minutes_is_a_finding(self):
        self.all_fresh()
        self.write("scorer", DAY - 21 * 60, DAY - 21 * 60, pid=2 ** 22 + 7)   # a pid that does not exist
        f, _ = W.heartbeat_findings({}, DAY, self.paths)
        self.assertEqual([(x["session"], x["kind"]) for x in f], [("pipeline_pp_scorer", "HEARTBEAT")])
        self.assertIn("gone", f[0]["what"])
        self.write("scorer", DAY - 19 * 60, DAY - 19 * 60)
        self.assertEqual(W.heartbeat_findings({}, DAY, self.paths)[0], [])

    def test_alive_with_no_finished_pass_is_a_finding(self):
        self.all_fresh()
        self.write("word_pass", DAY - 30, DAY - 91 * 60)
        f, _ = W.heartbeat_findings({}, DAY, self.paths)
        self.assertEqual([(x["session"], x["kind"]) for x in f], [("pipeline_pp_wordpass", "HEARTBEAT")])
        self.assertIn("no finished pass", f[0]["what"])

    def test_a_missing_heartbeat_is_a_finding_after_20_minutes(self):
        self.all_fresh()
        os.remove(os.path.join(self.paths["heartbeats"], "judge.json"))
        st = {}
        self.assertEqual(W.heartbeat_findings(st, DAY, self.paths)[0], [])
        for name, _ in W.HEARTBEATS:
            if name != "judge":
                self.write(name, DAY + 20 * 60, DAY + 20 * 60)
        os.utime(self.paths["transcript_log"], (DAY + 20 * 60, DAY + 20 * 60))
        self.assertEqual(W.heartbeat_findings(st, DAY + 19 * 60, self.paths)[0], [])
        f, _ = W.heartbeat_findings(st, DAY + 21 * 60, self.paths)
        self.assertEqual([(x["session"], x["what"]) for x in f],
                         [("pipeline_pp_judge", "judge: no heartbeat written")])

    def test_an_unreadable_record_reads_as_missing_and_never_ends_the_check(self):
        self.all_fresh()
        for name, body in (("scorer", '{"at": "x"}'), ("judge", '[1, 2]'), ("word_pass", '{"at": 1, "pass_at": "y"}'),
                           ("lock_precheck", '{"at": NaN, "pass_at": Infinity}')):
            with open(os.path.join(self.paths["heartbeats"], f"{name}.json"), "w") as f:
                f.write(body)
        st = {}
        self.assertEqual(W.heartbeat_findings(st, DAY, self.paths)[0], [])        # the grace starts
        self.assertEqual(sorted(st["heartbeat_missing"]), ["judge", "lock_precheck", "scorer", "word_pass"])
        with open(os.path.join(self.paths["heartbeats"], "scorer.json"), "w") as f:
            f.write('{"at": %r, "pass_at": 1e300}' % (DAY - 60))
        self.assertEqual(W.heartbeat_findings(st, DAY, self.paths)[0], [])        # out of range: missing too

    def test_the_transcript_run_is_read_by_its_log(self):
        self.all_fresh()
        os.utime(self.paths["transcript_log"], (DAY - 66 * 60, DAY - 66 * 60))
        f, _ = W.heartbeat_findings({}, DAY, self.paths)
        self.assertEqual([(x["session"], x["kind"]) for x in f], [(W.TRANSCRIPT_KEY, "HEARTBEAT")])

    def test_a_pass_sends_one_heartbeat_line_through_the_watchdog_sender(self):
        self.all_fresh()
        self.write("scorer", DAY - 25 * 60, DAY - 25 * 60, pid=2 ** 22 + 7)
        sent = []
        log = os.path.join(self.d, "watchdog_lines.jsonl")

        def send(key, kinds, line, now):                         # the real sender, with Telegram stubbed
            return telegram.send_watchdog(key, kinds, line, send=lambda s: sent.append(s) or 99, now=now,
                                          log_path=log)
        with mock.patch.object(W, "list_sessions", return_value={}), \
                mock.patch.object(W, "idle_with_work", return_value=[]):
            status = W.run_pass({}, now=DAY, paths=self.paths, send=send)
        self.assertEqual([f["kind"] for f in status["findings"]], ["HEARTBEAT"])
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].startswith("WATCHDOG pipeline_pp_scorer: HEARTBEAT: scorer: no heartbeat since"))
        self.assertEqual(status["heartbeats"]["scorer"]["alive"], False)

    def test_a_heartbeat_line_waits_for_07_00_et(self):
        night = datetime(2026, 11, 23, 3, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()
        with self.assertRaises(telegram.WatchdogRefused):
            telegram.send_watchdog("pipeline_pp_scorer", ["HEARTBEAT"], "pipeline_pp_scorer: x", send=lambda s: 1,
                                   now=night, log_path=os.path.join(self.d, "l.jsonl"))


if __name__ == "__main__":
    unittest.main()
