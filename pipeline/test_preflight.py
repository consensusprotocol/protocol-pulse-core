#!/usr/bin/env python3
"""pipeline/preflight.py (orchestrator order 2026-11-11 '21:10'): fail fast before a run spends an hour.
unit   an exception in a check is a failed check (fail closed); any failure exits 3 with 'HOLD (preflight)';
       a foreign job on GPU0 fails (the GPU0 Ollama's own runners do not); a dirty or unpushed tree fails; secrets
       never reach the output; a disabled channel's missing avatar does not fail the asset check
wrapper scripts/pulse_check_run.sh runs preflight.py after the run lock and before run_fresh.py, and exits 3 on a
       failure without starting run_fresh
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_preflight.py"""
import io
import os
import re
import sys
import types
import unittest
from contextlib import redirect_stdout

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import preflight as P  # noqa: E402


class R:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


class TestRunner(unittest.TestCase):
    def test_an_exception_is_a_failed_check_and_any_failure_holds(self):
        def boom():
            raise RuntimeError("network down")
        res = P.run_checks([("ok", lambda: (True, "fine")), ("boom", boom)])
        self.assertEqual([(r["check"], r["ok"]) for r in res], [("ok", True), ("boom", False)])
        self.assertIn("RuntimeError", res[1]["detail"])
        self.assertNotIn("network down", res[1]["detail"])                # exception text never reported
        saved = P.CHECKS
        P.CHECKS = [("ok", lambda: (True, "fine")), ("bad", lambda: (False, "nope"))]
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                code = P.main()
        finally:
            P.CHECKS = saved
        self.assertEqual(code, 3)
        self.assertIn("HOLD (preflight): bad: nope", out.getvalue())


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.saved_run = P._run

    def tearDown(self):
        P._run = self.saved_run

    def test_a_foreign_job_on_gpu0_fails_and_our_ollama_runner_does_not(self):
        """Law L-r: a foreign compute process on GPU0 fails the check, named; so does a model resident on the shared
        Ollama that this run did not request (cycle 1 of its audit: the Ollama server is not a lease-free door); the
        Ollama listener and runners themselves are not foreign; enough room = the largest single model + margin."""
        from unittest import mock
        import gpu0
        state = {"procs": [], "used": 600, "ollama": []}
        patches = [mock.patch.object(gpu0, "processes", side_effect=lambda: list(state["procs"])),
                   mock.patch.object(gpu0, "memory", side_effect=lambda: (state["used"], 24564)),
                   mock.patch.object(gpu0, "ollama_resident", side_effect=lambda: list(state["ollama"])),
                   mock.patch.object(gpu0, "_ollama_pids", return_value={100, 101})]
        for x in patches:
            x.start()
        try:
            state["procs"] = [(101, "ollama", 500)]                    # the runner, idle: ours, nothing resident
            ok, d = P.check_gpu0()
            self.assertTrue(ok, d)
            state["procs"] = [(101, "ollama", 500), (777, "python3", 1962)]   # a foreign job on GPU0
            state["used"] = 2562
            ok, d = P.check_gpu0()
            self.assertFalse(ok)
            self.assertIn("pid 777 python3 1962 MiB", d)
            state["procs"], state["used"] = [(101, "ollama", 18900)], 19000
            state["ollama"] = [("gemma3:27b", 18900)]                 # resident, not requested by this run
            ok, d = P.check_gpu0()
            self.assertFalse(ok)
            self.assertIn("ollama model gemma3:27b (not requested by this run)", d)
        finally:
            for x in reversed(patches):
                x.stop()

    def test_a_dirty_or_unpushed_tree_fails(self):
        replies = {"status": R(" M pipeline/editorial_select.py\n")}
        P._run = lambda cmd, timeout=30: replies.get(cmd[3] if len(cmd) > 3 else "", R(""))
        ok, d = P.check_git()
        self.assertFalse(ok)
        self.assertIn("editorial_select.py", d)
        replies = {"status": R(""), "ls-files": R("pipeline/new_module.py\n")}      # an untracked pipeline module
        P._run = lambda cmd, timeout=30: replies.get(cmd[3], R("abc123\n"))
        ok, d = P.check_git()
        self.assertFalse(ok)
        self.assertIn("new_module.py", d)
        replies = {"status": R(""), "ls-files": R(""), "rev-parse": R("origin/branch\n"), "merge-base": R("", returncode=1)}
        P._run = lambda cmd, timeout=30: replies.get(cmd[3], R("abc123\n"))
        ok, d = P.check_git()
        self.assertFalse(ok)
        self.assertIn("NOT on origin/branch", d)

    def test_secrets_never_reach_the_output(self):
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "SECRET-" + name
        saved_mod, saved_get = sys.modules.get("relay"), P._get_json
        sys.modules["relay"] = relay
        seen = []

        def get(url, headers=None, timeout=15, data=None):
            seen.append(url + str(headers))
            return {"ok": True} if "telegram" in url else {"character_limit": 10000, "character_count": 100}
        P._get_json = get
        try:
            res = P.run_checks([("elevenlabs", P.check_elevenlabs), ("telegram", P.check_telegram)])
        finally:
            P._get_json = saved_get
            if saved_mod is None:
                sys.modules.pop("relay", None)
            else:
                sys.modules["relay"] = saved_mod
        self.assertTrue(all(r["ok"] for r in res), res)
        self.assertTrue(any("SECRET-" in s for s in seen))                # the key was used...
        self.assertFalse(any("SECRET" in r["detail"] for r in res))       # ...and never reported

    def test_a_failing_call_whose_error_text_carries_the_secret_never_reports_it(self):
        """claude-fable audit (batch 16) #6: the only route for a secret into the output was an exception's text
        (a URL with the bot token, a header echoed back)."""
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "SECRET-" + name
        saved_mod, saved_get = sys.modules.get("relay"), P._get_json

        def get(url, headers=None, timeout=15, data=None):
            raise ConnectionError(f"Max retries exceeded with url: {url} headers={headers}")
        P._get_json = get
        sys.modules["relay"] = relay
        try:
            res = P.run_checks([("elevenlabs", P.check_elevenlabs), ("telegram", P.check_telegram)])
        finally:
            P._get_json = saved_get
            if saved_mod is None:
                sys.modules.pop("relay", None)
            else:
                sys.modules["relay"] = saved_mod
        self.assertFalse(any(r["ok"] for r in res))
        self.assertFalse(any("SECRET" in r["detail"] for r in res), res)
        self.assertTrue(all("ConnectionError" in r["detail"] for r in res), res)

    def test_a_disabled_channel_without_an_avatar_does_not_fail_assets(self):
        import json
        reg = json.load(open(os.path.join(PIPELINE, "channels.json")))
        off = [c for c in reg if not c.get("enabled", True) and not c.get("avatar_path")]
        if not off:
            self.skipTest("no disabled channel without an avatar in the registry")
        ok, d = P.check_assets()
        self.assertTrue(ok, d)
        self.assertNotIn(off[0]["display_name"], d)


class TestWrapper(unittest.TestCase):
    def test_preflight_runs_before_run_fresh_and_a_failure_exits_3(self):
        s = open(os.path.join(REPO, "scripts", "pulse_check_run.sh")).read()
        pf, rf = s.index("python3 preflight.py"), s.index("python3 run_fresh.py")
        lock = s.index('if ! flock -n 9; then\n  echo "pulse_check_run: another run holds', s.index('LOG_DIR='))
        self.assertTrue(lock < pf < rf)
        self.assertRegex(s[pf:rf], re.compile(r'PIPESTATUS\[0\]\}" != 0 \]; then.*?exit 3', re.S))


if __name__ == "__main__":
    unittest.main()
