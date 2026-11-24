"""RULING 160 (2b) (orchestrator 07:33 ET Nov 24): every build ends in EXACTLY ONE recorded outcome, one JSON line in
data/builds/outcomes.jsonl (tests/package/outcomes.py), written by the driver whatever ends the build; builds 152-168
backfilled from their records. And the verifier's rows 12 / 16 (FIX_VERIFICATION_2026-11-24): the build launcher and
its record scripts are in git (tests/package/record/), the launcher runs one driver with no override, the driver
refuses any other entry point and records its own; the record script reads a stopped build and a NOTHING NEW one."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import outcomes as OC  # noqa: E402

PROOF = os.path.join(HERE, "proof")
RECORD = os.path.join(HERE, "record")
NOENV = {k: v for k, v in os.environ.items() if k != "PP_SELECTID_DRIVER_UNDER_TEST"}
NOENV.update(http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9")
BAR = "the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, setup >= 3, on xai:grok-4.20 asked alone"


class TestEveryReasonOneOutcome(unittest.TestCase):
    """Each reason package.build can end on maps to exactly one of the builder's outcomes; a hard check that gave no
    answer is INDETERMINATE (ruling 160 (2a)), never a refusal."""
    CASES = [
        ("the pool spans 2 channel(s) after the free stages: a medley needs 3; no paid verdict (ruling 109)", {},
         "NO_ELIGIBLE_STORY", "pool"),
        ("1 moments cleared step A from fewer than 3 channels", {}, "HARD_REJECTED", "step A"),
        ("1 moments cleared step A from fewer than 3 channels", {"held_102": {"first": ["a" * 20], "second": []}},
         "INDETERMINATE", "step A"),
        ("no work_dir: law L-v 2's second pass cannot run, so no package can pass (fail closed)", {},
         "INDETERMINATE", "second pass + CUTTABLE"),
        (f"no hook in the pool (ruling 59 d): 2 of the 3 moments that can open pass {BAR}, and the visual check "
         f"(rulings 70 / 93) refuses each as an opener: A {'b' * 20}: ruling 93 (1 item(s)): a ticker", {},
         "HARD_REJECTED", "visual"),
        (f"no hook in the pool (ruling 59 d): 1 of the 1 moments that can open pass {BAR}, and the visual check "
         f"(rulings 70 / 93) refuses each as an opener: A {'b' * 20}: its visual check is not measured (law L-m)", {},
         "INDETERMINATE", "visual"),
        (f"no hook in the pool (ruling 59 d): none of the 1 moments that can open passes {BAR} (1 not rated: "
         f"ProviderError: coherence_verdict: every back-end unavailable); the best: x", {}, "INDETERMINATE", "hooks"),
        (f"no hook in the pool (ruling 59 d): none of the 3 moments that can open passes {BAR}; the best: x", {},
         "HARD_REJECTED", "hooks"),
        ("no hook in the pool (ruling 59 d): every hook that passed the calibrated bar failed the second vendor's "
         "step A: FAIL: STALE_TIME", {}, "HARD_REJECTED", "step A, second family"),
        ("3 cleared moments pass the second pass, CUTTABLE and step A from both vendors, from fewer than 3 channels",
         {"second_pass": {"a" * 20: "L-v 2 FAIL"}}, "HARD_REJECTED", "second pass + CUTTABLE"),
        ("3 cleared moments pass the second pass, CUTTABLE and step A from both vendors, from fewer than 3 channels",
         {"second_pass": {"a" * 20: "not measured: transcribe: every back-end unavailable"}}, "INDETERMINATE",
         "second pass + CUTTABLE"),
        ("ruling 66: the candidate is closed: clip", {}, "HARD_REJECTED", "line-ups"),
        ("ruling 66: the 8 judged line-ups were spent on candidates; no angle asked", {}, "BUDGET_STOPPED",
         "line-ups"),
        ("no readable angles: ValueError: angle 1: >= 3 channels", {}, "INDETERMINATE", "line-ups"),
        ("no readable angles: SpendLimit: the stop", {}, "BUDGET_STOPPED", "line-ups"),
        ("stopped in angle 1 of 3: the search spent 2500 s of 2400 s / $0.10 of $3.00 reported", {},
         "BUDGET_STOPPED", "line-ups"),
        (f"no angle gave a package: angle 1: ruling 70: {'c' * 20}: ruling 93 (1 item(s)): a ticker: re-lined", {},
         "HARD_REJECTED", "visual"),
        ("no angle gave a package: angle 1: ruling 68 / 72: the render's lock: not asked: --lock-precheck off", {},
         "BUDGET_STOPPED", "lock pre-check"),
        ("no angle gave a package: angle 1: ruling 68 / 72: the render's lock: no verdict in 900 s", {},
         "INDETERMINATE", "lock pre-check"),
        ("no angle gave a package: angle 1: this line-up's package spent 950 s of 900 s / $0.10 of $1.50 reported",
         {}, "BUDGET_STOPPED", "line-ups"),
        ("no angle gave a package: angle 1: 2 write(s) failed their gates (COMMENTARY, VERDICT_NO)", {},
         "HARD_REJECTED", "writes"),
        ("no angle gave a line-up to try", {}, "HARD_REJECTED", "line-ups"),
    ]

    def test_each_reason(self):
        for why, pre, kind, stage in self.CASES:
            c = OC.classify(why, pre)
            self.assertEqual((c["outcome"], c["stage"]), (kind, stage), why)
            self.assertIn(c["outcome"], OC.BUILDER_KINDS)

    def test_the_failed_model_and_clip_are_named(self):
        c = OC.classify(self.CASES[6][0])
        self.assertEqual(c["model"], "coherence_verdict")                 # never the bar's own rater
        c = OC.classify(self.CASES[16][0])
        self.assertEqual(c["clip"], "c" * 20)

    def test_every_reason_package_writes_is_known(self):
        """Every why_none package.build writes has its case above (a new one must be given its outcome here): the
        literal words each assignment starts with (after a leading count) appear in a case, and no case reads
        'unknown'."""
        import re
        src = open(os.path.join(REPO, "pipeline", "package.py")).read()
        heads = [h.strip() for h in re.findall(r'why_none"?\]?\s*=\s*\(?f?"(?:\{[^}]+\}\s*)?([^"{]+)', src)]
        heads = sorted({h for h in heads if len(h) >= 6})
        self.assertGreaterEqual(len(heads), 8, heads)
        for h in heads:
            self.assertTrue(any(h in why for why, *_ in self.CASES), h)
        self.assertNotIn("unknown", {OC.classify(why, pre)["stage"] for why, pre, *_ in self.CASES})


class TestTheBackfilledRecords(unittest.TestCase):
    """Last night's records (tests/package/proof): each gives exactly one outcome."""

    def one(self, run, n):
        return OC.outcome_of(os.path.join(PROOF, run), build_no=n, backfilled=True)

    def test_last_night(self):
        want = {"ledger_20261124_000525": ("HARD_REJECTED", "line-ups"),       # 152
                "ledger_20261124_003124": ("NO_ELIGIBLE_STORY", "inputs"),      # 153: NOTHING NEW
                "ledger_20261124_004415": ("BUDGET_STOPPED", "spend"),          # 155: free screens only
                "ledger_20261124_012843": ("INDETERMINATE", "start"),           # 156: no package.json
                "ledger_20261124_012928": ("INDETERMINATE", "hooks"),           # 157: the hook rater gave no answer
                "ledger_20261124_024358": ("NO_ELIGIBLE_STORY", "pool"),        # 162
                "ledger_20261124_025241": ("HARD_REJECTED", "second pass + CUTTABLE"),   # 164
                "ledger_20261124_032741": ("HARD_REJECTED", "visual"),          # 166
                "ledger_20261124_033614": ("SEALED", "seal")}                   # 167
        for run, (kind, stage) in want.items():
            x = self.one(run, 0)
            self.assertEqual((x["outcome"], x["stage"]), (kind, stage), run)
            self.assertEqual(x["run"], run)
            self.assertEqual([y["stage"] for y in x["yield"]], list(OC.STAGES))
        x = self.one("ledger_20261124_033614", 167)
        self.assertEqual((x["pin"], x["dollars"], x["story_id"], x["time"]),
                         ("afd8977d143e", 0.037, "S-13ad274d", "2026-11-23T22:36:14-05:00"))
        self.assertEqual(self.one("ledger_20261124_025241", 164)["clip"], "1cb1675158fd53f1033a")
        self.assertEqual(self.one("ledger_20261124_032741", 166)["clip"], "ad47eab4a19c2324a9eb")
        self.assertEqual(self.one("ledger_20261124_012928", 157)["model"], "xai:grok-4.20-0309-reasoning")   # its
        #   reason: "coherence_verdict: every back-end unavailable: [('xai:grok-4.20-0309-reasoning', 'same vendor ...')]"


class TestExactlyOneLine(unittest.TestCase):
    def test_write_once_and_only_an_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data", "builds", "outcomes.jsonl")
            line = OC.outcome_of(os.path.join(PROOF, "ledger_20261124_033614"), build_no=167)
            self.assertTrue(OC.write_once(line, p))
            self.assertFalse(OC.write_once(dict(line, outcome="HARD_REJECTED"), p))   # one line a run
            self.assertEqual(len(OC.lines(p)), 1)
            with self.assertRaises(ValueError):
                OC.write_once(dict(line, run="x", outcome="MAYBE"), p)
            self.assertIn("1 SEALED", OC.yield_line("2026-11-23", p))

    def driver(self, fake):
        """proof_ledger.main with its body (_main) replaced by `fake`: the outcome line is written by main's finally."""
        import proof_ledger as PLG
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "outcomes.jsonl")
            out = os.path.join(d, "ledger_20261124_120000")
            with mock.patch.object(OC, "OUTCOMES", p), mock.patch.object(PLG, "_main", lambda a, box: fake(out, box)):
                try:
                    rc = PLG.main([])
                except RuntimeError:
                    rc = "raised"
                rc2 = None
                if os.path.isdir(out):                      # a second end of the same run never writes again
                    rc2 = OC.record_build(out, rc=0, path=p)
            return rc, OC.lines(p), rc2

    def test_every_way_a_build_ends_writes_exactly_one_line(self):
        def nothing_new(out, box):
            os.makedirs(out)
            box["out_dir"] = out
            json.dump({"same_as": "ledger_x"}, open(os.path.join(out, "NOTHING_NEW.json"), "w"))
            return 0

        def refused(out, box):
            os.makedirs(out)
            box.update(out_dir=out, refused="REFUSED (ruling 48): ... no build starts")
            return 3

        def crash(out, box):
            os.makedirs(out)
            box["out_dir"] = out
            raise RuntimeError("boom")

        def no_folder(out, box):
            return 2

        def stopped(out, box):                           # SIGTERM, turned into SystemExit(143) by main()
            os.makedirs(out)
            box["out_dir"] = out
            raise SystemExit(143)
        for fake, rc, kind, gate in ((nothing_new, 0, "NO_ELIGIBLE_STORY", "nothing new"),
                                     (refused, 3, "BUDGET_STOPPED", "no build starts"),
                                     (crash, "raised", "INDETERMINATE", "the build crashed: RuntimeError")):
            got, ls, again = self.driver(fake)
            self.assertEqual(got, rc, fake.__name__)
            self.assertEqual([x["outcome"] for x in ls], [kind], fake.__name__)
            self.assertIn(gate, ls[0]["gate"] + " " + str(ls[0]["note"]))
            self.assertIsNone(again)
        got, ls, _ = self.driver(no_folder)
        self.assertEqual((got, ls), (2, []))                 # a refusal before the record folder is no build
        with self.assertRaises(SystemExit):
            self.driver(stopped)
        import proof_ledger as PLG
        with tempfile.TemporaryDirectory() as d:
            p, out = os.path.join(d, "o.jsonl"), os.path.join(d, "ledger_20261124_120001")
            with mock.patch.object(OC, "OUTCOMES", p), \
                    mock.patch.object(PLG, "_main", lambda a, box: stopped(out, box)):
                with self.assertRaises(SystemExit):
                    PLG.main([])
            self.assertEqual([(x["outcome"], x["gate"]) for x in OC.lines(p)],
                             [("INDETERMINATE", "the build was stopped (SystemExit, exit 143)")])

    def test_the_real_driver_records_its_entry_and_its_crash(self):
        """main() run for real, up to the inputs (no model, no network): inputs.json carries the entry; a failure after
        that writes ONE line, INDETERMINATE."""
        import proof_ledger as PLG

        class Stop(Exception):
            pass
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "outcomes.jsonl")
            with mock.patch.object(OC, "OUTCOMES", p), mock.patch.object(PLG, "HERE", d), \
                    mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})), \
                    mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"refused": []})), \
                    mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: ([], {}, {})), \
                    mock.patch.object(PLG.SPOT, "next_attempt", lambda *a, **k: {}), \
                    mock.patch.object(PLG, "with_variants", lambda m, *a, **k: m), \
                    mock.patch.object(PLG, "fingerprint", mock.Mock(side_effect=Stop("after the inputs"))):
                with self.assertRaises(Stop):
                    PLG.main(["--delivered", *pins, "--build-no", "9"])
            runs = [x for x in os.listdir(os.path.join(d, "proof")) if x.startswith("ledger_")]
            self.assertEqual(len(runs), 1)
            inp = json.load(open(os.path.join(d, "proof", runs[0], "inputs.json")))
            e = inp["entry"]
            self.assertEqual((e["ok"], e["under_test"], e["driver"], inp["build_no"]),
                             (True, True, "tests/package/proof_ledger.py", 9))
            self.assertRegex(e["code"], r"^[0-9a-f]{40}$")
            ls = OC.lines(p)
            self.assertEqual([(x["outcome"], x["build"], x["run"]) for x in ls], [("INDETERMINATE", 9, runs[0])])
            self.assertEqual(ls[0]["gate"], "the build crashed: Stop")


class TestRuling163NothingNewAfterAnOutage(unittest.TestCase):
    """RULING 163 (4) (orchestrator 08:22 ET Nov 24) on the verifier's drill (FIX_VERIFICATION_2026-11-24, end-to-end):
    its outage run (Heimdall qwen and deepseek forced down; fixture: its record ledger_20261124_044000, package.json and
    FINGERPRINT.json, copied from its scratch copy d24_c167) recorded '0 item(s) left undone' although 3 openers' vision
    checks were never measured and 2 hook ratings were never answered, and the vendors-up re-run 1 s later was refused
    NOTHING NEW. Each such check is now work left undone: the identical re-run is a build, and the outage run's outcome
    is INDETERMINATE."""
    REC = os.path.join(HERE, "fixtures", "outage_163", "ledger_20261124_044000")

    def test_the_outage_left_work_undone_and_its_rerun_is_a_build(self):
        import collections
        import proof_ledger as PLG
        pk = json.load(open(os.path.join(self.REC, "package.json")))
        self.assertEqual(json.load(open(os.path.join(self.REC, PLG.FINGERPRINT)))["open_work"], 0)   # as recorded then
        items = OC.undone(pk, pk.get("spotlight"))
        self.assertEqual(collections.Counter(x["kind"] for x in items), {"vision": 3, "hook rating": 2})
        self.assertEqual(sorted(x["id"] for x in items if x["kind"] == "vision"),
                         ["1cb1675158fd53f1033a", "96056caa002021fd9a1d", "aaf91c675142516b3b1f"])
        left = PLG.open_work(pk, pk.get("spotlight") or {})
        self.assertEqual(left, 5)
        with tempfile.TemporaryDirectory() as d:                 # the drill: the identical inputs, 1 s later
            prev = os.path.join(d, "ledger_20261124_044000")
            os.makedirs(prev)
            json.dump({"fingerprint": "F", "open_work": left, "undone": items},
                      open(os.path.join(prev, PLG.FINGERPRINT), "w"))
            self.assertIsNone(PLG.nothing_new(d, os.path.join(d, "ledger_20261124_044001"), "F"))   # a build again
        x = OC.outcome_of(self.REC)
        self.assertEqual((x["outcome"], x["stage"]), ("INDETERMINATE", "visual"))
        self.assertIn("3 vision, 2 hook rating", x["gate"])

    def test_each_kind_of_unanswered_check_is_undone(self):
        import proof_ledger as PLG
        none = {"prescreen": {}, "never_empty": {"soft_record": {"hook_pool": {"can_open": 2, "rated": 2}}}}
        self.assertEqual(PLG.open_work(none, {}), 0)
        cases = [
            ({"hook_pool": {"can_open": 3, "rated": 1, "error": "NO JUDGE ANSWERED"}}, 2),          # unrated openers
            ({"tried": [{"attempts": [{"value": {"measured": False, "why": "no verdict"}},
                                      {"value": {"measured": False, "why": "no verdict"}}]}]}, 1),   # once a record
            ({"tried": [{"attempts": [{"exclusion": {"a": {"verdict": "exclude", "measured": False}}}]}]}, 1),
            ({"lock_stop": "ruling 68 / 72: the render's lock: no verdict in 900 s"}, 1),
            ({"lock_stop": "ruling 68 / 72: the render's lock: not asked: --lock-precheck off"}, 0),   # by choice
            ({"out_edge": {"unverified": ["a", "b"]}}, 2),                                          # ruling 162 (1)
            ({"never_empty": {"soft_record": {"out_edge": {"unverified": {"c": "no answer"}}}}}, 1),
            ({"never_empty": {"soft_record": {"hook_pool": {"visual_blocked": {
                "a": "its visual check is not measured (law L-m)", "b": "ruling 93 (1 item(s)): a ticker"}}}}}, 1)]
        for rec, n in cases:
            self.assertEqual(PLG.open_work(rec, {}), n, rec)
        sealed = {"package": {"x": 1}, "never_empty": {"soft_record": {"hook_pool": {"visual_blocked": {
            "a": "its visual check is not measured (law L-m)"}}}}}
        self.assertEqual(PLG.open_work(sealed, {}), 0)      # a sealed pass counts its own sheets in "visual"


class TestOneEntryOneLauncher(unittest.TestCase):
    """Verifier rows 12 / 16: builds 166-168 ran by-hand wrappers (an import of the driver and a call of main())
    through the launcher's DRIVER= override, and the record script was outside git."""

    def run_py(self, args, cwd=REPO):
        return subprocess.run([sys.executable, "-B", *args], cwd=cwd, env=NOENV, capture_output=True, text=True,
                              timeout=300)

    def test_a_wrapper_is_refused_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            w = os.path.join(d, "by_hand_x.py")
            with open(w, "w") as f:
                f.write(f"import sys\nsys.path.insert(0, {HERE!r})\nimport proof_ledger as PLG\n"
                        f"sys.exit(PLG.main(['--delivered', 'x.json']))\n")
            before = set(os.listdir(PROOF))
            for args in ([w], ["-c", f"import sys; sys.path.insert(0, {HERE!r}); import proof_ledger as P; "
                                     f"sys.exit(P.main(['--delivered', 'x.json']))"],
                         ["-c", f"import sys; sys.path.insert(0, {HERE!r}); import proof_ledger as P; "
                                f"sys.exit(P._main(['--delivered', 'x.json'], {{}}))"]):   # the body, directly
                r = self.run_py(args)
                self.assertEqual(r.returncode, 2, r.stderr[-400:])
                self.assertIn("REFUSED: this build was entered through", r.stderr)
            self.assertEqual(set(os.listdir(PROOF)), before)      # no record folder
        r = self.run_py(["tests/package/proof_ledger.py", "--delivered", "x.json", "--hours", "99"])
        self.assertEqual(r.returncode, 2)                         # its own file: past the entry, refused on --hours
        self.assertIn("REFUSED (ruling 76)", r.stderr)
        self.assertNotIn("entered through", r.stderr)

    @staticmethod
    def git(repo, *args):
        return subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              capture_output=True, text=True, timeout=60, check=True).stdout

    def launch(self, repo, d, log, extra_env=None):
        fake = os.path.join(d, "bin", "python3")
        os.makedirs(os.path.dirname(fake), exist_ok=True)
        with open(fake, "w") as f:
            f.write("#!/bin/bash\necho \"$@\" >> \"$FAKE_LOG\"\nfor a in \"$@\"; do case \"$a\" in\n"
                    "  *day_spent.py) echo '0.500000 SPEND_D20261124.json'; exit 0;;\n"
                    "  *proof_ledger.py|*by_hand*) echo 'REFUSED: stand-in'; exit 2;;\n"
                    f"esac; done\nexec {sys.executable} \"$@\"\n")
        os.chmod(fake, 0o755)
        env = dict(NOENV, PATH=os.path.dirname(fake) + os.pathsep + os.environ.get("PATH", ""), FAKE_LOG=log,
                   **(extra_env or {}))
        r = subprocess.run(["bash", os.path.join(repo, "tests", "package", "record", "build_and_record.sh"), "7",
                            "test", "--only", os.devnull, "--stop-usd", "0.6"], env=env, capture_output=True,
                           text=True, timeout=120)
        if r.returncode == 3:
            self.skipTest(f"the launcher's own guard: {r.stdout.strip()[:200]}")   # a render or build running
        return r

    def test_the_launcher_runs_only_the_committed_driver(self):
        """RULING 163 (5) and the verifier's row 16, on a repository of its own (the launcher and a stand-in driver,
        committed and pushed to a bare remote), with a stand-in python3 that answers the spend probe and logs every
        call: with DRIVER= set to a wrapper it runs tests/package/proof_ledger.py, passing the build number; with the
        driver changed and not committed, a code file changed under pipeline/, or a commit not pushed, it REFUSES
        before any python runs the build. The stand-in driver refuses, so nothing is recorded or committed."""
        import shutil
        with tempfile.TemporaryDirectory() as d:
            repo, bare, log = os.path.join(d, "repo"), os.path.join(d, "bare.git"), os.path.join(d, "calls.log")
            os.makedirs(os.path.join(repo, "tests", "package", "record"))
            os.makedirs(os.path.join(repo, "pipeline"))
            shutil.copy(os.path.join(RECORD, "build_and_record.sh"), os.path.join(repo, "tests", "package", "record"))
            drv, mod = os.path.join(repo, "tests", "package", "proof_ledger.py"), os.path.join(repo, "pipeline", "m.py")
            open(drv, "w").write("print('the committed driver')\n")
            open(mod, "w").write("X = 1\n")
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
            self.git(repo, "add", "-A")
            self.git(repo, "commit", "-q", "-m", "c1")
            self.git(repo, "remote", "add", "origin", bare)
            self.git(repo, "push", "-q", "-u", "origin", "HEAD")
            r = self.launch(repo, d, log, {"DRIVER": os.path.join(d, "by_hand_166.py")})
            self.assertEqual(r.returncode, 5, r.stdout[-500:] + r.stderr[-500:])     # the stand-in driver refused
            calls = open(log).read()
            self.assertIn("tests/package/proof_ledger.py --build-no 7 ", calls)
            self.assertNotIn("by_hand", calls)
            for change, path, words in ((lambda: open(drv, "a").write("print('by hand')\n"), drv,
                                         "differs from the committed one"),
                                        (lambda: open(mod, "a").write("X = 2\n"), mod, "code changed and not committed")):
                if os.path.exists(log):
                    os.remove(log)
                change()
                r = self.launch(repo, d, log)
                self.assertEqual(r.returncode, 6, r.stdout[-400:])
                self.assertIn(words, r.stdout)
                self.assertFalse(os.path.exists(log) and "proof_ledger.py --build-no" in open(log).read())
                self.git(repo, "checkout", "-q", "--", path)
            open(mod, "a").write("X = 3\n")
            self.git(repo, "commit", "-q", "-am", "c2 (not pushed)")
            r = self.launch(repo, d, log)
            self.assertEqual(r.returncode, 6, r.stdout[-400:])
            self.assertIn("commits not pushed: 1", r.stdout)

    def test_the_record_script_reads_a_stopped_and_a_nothing_new_build(self):
        with tempfile.TemporaryDirectory() as d:
            json.dump({"inputs": {}}, open(os.path.join(d, "inputs.json"), "w"))
            r = self.run_py([os.path.join(RECORD, "attempt_summary.py"), d])
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("the build stopped before writing package.json", r.stdout)
        r = self.run_py([os.path.join(RECORD, "attempt_summary.py"), os.path.join(PROOF, "ledger_20261124_003124")])
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertIn("NOTHING NEW (ruling 107 (1))", r.stdout)
        r = self.run_py([os.path.join(RECORD, "attempt_summary.py"), os.path.join(PROOF, "ledger_20261124_033614")])
        self.assertIn("PIN WRITTEN: MOMENTS_PIN_LEDGER.json", r.stdout)

    def test_the_record_scripts_name_no_scratch_or_other_tree(self):
        for f in sorted(x for x in os.listdir(RECORD) if os.path.isfile(os.path.join(RECORD, x))):
            src = open(os.path.join(RECORD, f)).read()
            for bad in ("/tmp/claude-1000", "scratchpad", "/home/ultron/worktrees/pp-selectid", "DRIVER=${"):
                self.assertNotIn(bad, src, f)


if __name__ == "__main__":
    unittest.main()
