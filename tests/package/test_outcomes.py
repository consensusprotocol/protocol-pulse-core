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

    def test_a_stop_inside_the_write_is_said_and_never_masks_the_end(self):
        """Audit L2 (qwen F3): an interrupt while the line is written is reported, and the build's own end stands."""
        import io
        import proof_ledger as PLG
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "ledger_20261124_120002")

            def fake(a, box):
                os.makedirs(out)
                box["out_dir"] = out
                return 0
            err = io.StringIO()
            with mock.patch.object(PLG, "_main", fake), \
                    mock.patch.object(OC, "record_build", mock.Mock(side_effect=KeyboardInterrupt())), \
                    mock.patch.object(sys, "stderr", err):
                self.assertEqual(PLG.main([]), 0)
            self.assertIn("the outcome line was NOT written: KeyboardInterrupt", err.getvalue())

    def test_the_real_driver_records_its_entry_and_its_crash(self):
        """main() run for real, up to the inputs (no model, no network): inputs.json carries the entry; a failure after
        that writes ONE line, INDETERMINATE."""
        import proof_ledger as PLG

        class Stop(Exception):
            pass
        PIN = {"ref": "origin/combo-letterbox-quoteonly-v2", "rev": "c" * 40, "sha256": "d" * 64,
               "version": "owner_rules 2", "live_sha256": "d" * 64}           # 10:55 ET Nov 24: the pinned revision
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "outcomes.jsonl")
            with mock.patch.object(OC, "OUTCOMES", p), mock.patch.object(PLG, "HERE", d), \
                    mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})), \
                    mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"refused": []})), \
                    mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: ([], {}, {})), \
                    mock.patch.object(PLG.SPOT, "next_attempt", lambda *a, **k: {}), \
                    mock.patch.object(PLG, "with_variants", lambda m, *a, **k: m), \
                    mock.patch.object(PLG, "fingerprint", mock.Mock(side_effect=Stop("after the inputs"))), \
                    mock.patch.object(PLG.OE, "pin", lambda: dict(PIN)):
                with self.assertRaises(Stop):
                    PLG.main(["--delivered", *pins, "--build-no", "9", "--out-dir-file", os.path.join(d, "out.txt")])
            runs = [x for x in os.listdir(os.path.join(d, "proof")) if x.startswith("ledger_")]
            self.assertEqual(len(runs), 1)
            self.assertEqual(open(os.path.join(d, "out.txt")).read().strip(), os.path.join(d, "proof", runs[0]))
            inp = json.load(open(os.path.join(d, "proof", runs[0], "inputs.json")))
            e = inp["entry"]
            self.assertEqual((e["ok"], e["under_test"], e["driver"], inp["build_no"]),
                             (True, True, "tests/package/proof_ledger.py", 9))
            self.assertRegex(e["code"], r"^[0-9a-f]{40}$")
            blob = subprocess.run(["git", "-C", REPO, "hash-object", "tests/package/proof_ledger.py"],
                                  capture_output=True, text=True).stdout.strip()
            self.assertEqual(e["driver_sha"], blob)                  # RULING 163 (5): the driver that ran, by sha
            self.assertEqual(e["owner_rules"], PIN)                  # 10:55 ET Nov 24: the release revision, recorded
            self.assertIsInstance(e["driver_committed"], bool)
            heads = {n: t["head"] for n, t in e["trees"].items()}    # the acceptance test, item 1: both commits
            self.assertEqual(sorted(heads), ["the integrator's tree", "this builder's tree"])
            for h in heads.values():
                self.assertRegex(h, r"^[0-9a-f]{40}$")
            ls = OC.lines(p)
            self.assertEqual([(x["outcome"], x["build"], x["run"]) for x in ls], [("INDETERMINATE", 9, runs[0])])
            self.assertEqual(ls[0]["gate"], "the build crashed: Stop")
            self.assertIn("pool", ls[0]["seconds"])                  # the time per stage, up to where it ended


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

    def test_item5_the_rerun_one_second_later_calls_the_models_and_is_not_nothing_new(self):
        """THE ACCEPTANCE LIST, item 5: "Test: the rerun one second later calls the models; it does not answer NOTHING
        NEW." The driver itself, run again on the outage run's inputs (the same fingerprint) one second after it: with
        the outage record's open work counted as now, it goes on to its router (the models: stopped here by a stand-in
        that raises); with the outage record's own '0 item(s) left undone' (the old count), it answers NOTHING NEW."""
        import proof_ledger as PLG

        class ModelsCalled(Exception):
            pass
        pk = json.load(open(os.path.join(self.REC, "package.json")))
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        for left, expect in ((PLG.open_work(pk, pk.get("spotlight") or {}), "models"), (0, "nothing new")):
            with tempfile.TemporaryDirectory() as d:
                prev = os.path.join(d, "proof", "ledger_20261124_044000")
                os.makedirs(prev)
                json.dump({"fingerprint": "F", "open_work": left}, open(os.path.join(prev, PLG.FINGERPRINT), "w"))
                with mock.patch.object(OC, "OUTCOMES", os.path.join(d, "o.jsonl")), mock.patch.object(PLG, "HERE", d), \
                        mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})), \
                        mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"refused": []})), \
                        mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: ([], {}, {})), \
                        mock.patch.object(PLG.SPOT, "next_attempt", lambda *a, **k: {}), \
                        mock.patch.object(PLG, "with_variants", lambda m, *a, **k: m), \
                        mock.patch.object(PLG, "fingerprint", lambda *a, **k: ("F", {})), \
                        mock.patch.object(PLG, "build_router", mock.Mock(side_effect=ModelsCalled("the router"))):
                    if expect == "models":
                        with self.assertRaises(ModelsCalled):
                            PLG.main(["--delivered", *pins])
                    else:
                        self.assertEqual(PLG.main(["--delivered", *pins]), 0)
                runs = sorted(x for x in os.listdir(os.path.join(d, "proof")) if x != "ledger_20261124_044000")
                self.assertEqual(len(runs), 1)
                self.assertEqual(os.path.exists(os.path.join(d, "proof", runs[0], PLG.NOTHING_NEW)),
                                 expect == "nothing new", (left, expect))
        self.assertGreater(PLG.open_work(pk, pk.get("spotlight") or {}), 0)

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


class TestAcceptanceItem1BothTreesClean(unittest.TestCase):
    """THE ACCEPTANCE TEST, item 1 (orchestrator 08:50 ET Nov 24): "The build refuses to start if either tree is dirty,
    and the record names the commit it ran." Either tree: this builder's and the integrator's (the build reads code
    from it). Dirty: a tracked code file changed or staged, or an untracked .py in the code folders; data, caches,
    proof records, logs and lock files are not code."""

    def repo(self, d):
        r = os.path.join(d, "t")
        os.makedirs(os.path.join(r, "pipeline"))
        os.makedirs(os.path.join(r, "data"))
        subprocess.run(["git", "init", "-q", r], check=True)
        open(os.path.join(r, "pipeline", "a.py"), "w").write("A = 1\n")
        open(os.path.join(r, "data", "cache.json"), "w").write("{}\n")
        TestOneEntryOneLauncher.git(r, "add", "-A")
        TestOneEntryOneLauncher.git(r, "commit", "-q", "-m", "c1")
        return r

    def test_what_makes_a_tree_dirty(self):
        import proof_ledger as PLG
        with tempfile.TemporaryDirectory() as d:
            r = self.repo(d)
            st = PLG.tree_state(r, ("pipeline",))
            self.assertEqual(st["dirty"], [])
            self.assertRegex(st["head"], r"^[0-9a-f]{40}$")
            open(os.path.join(r, "data", "cache.json"), "w").write('{"x": 1}\n')        # data: never code
            open(os.path.join(r, "pipeline", "x.log"), "w").write("log\n")
            open(os.path.join(r, "pipeline", "y.json.lock"), "w").write("")
            self.assertEqual(PLG.tree_state(r, ("pipeline", "data"))["dirty"], [])
            open(os.path.join(r, "pipeline", "a.py"), "a").write("B = 2\n")
            self.assertEqual(PLG.tree_state(r, ("pipeline",))["dirty"], ["pipeline/a.py (changed, not committed)"])
            TestOneEntryOneLauncher.git(r, "add", "pipeline/a.py")                     # the integrator's usual case
            self.assertEqual(PLG.tree_state(r, ("pipeline",))["dirty"], ["pipeline/a.py (staged, not committed)"])
            open(os.path.join(r, "pipeline", "new.py"), "w").write("N = 1\n")
            self.assertIn("pipeline/new.py (not committed, not tracked)", PLG.tree_state(r, ("pipeline",))["dirty"])
            gone = PLG.tree_state(os.path.join(d, "nowhere"), ("pipeline",))
            self.assertTrue(gone["dirty"])                                              # unreadable: never clean

    def test_the_refusal_is_one_plain_line_naming_the_files(self):
        import proof_ledger as PLG
        clean = {"root": "/a", "head": "1" * 40, "dirty": []}
        self.assertIsNone(PLG.dirty_refusal([("this builder's tree", clean), ("the integrator's tree", clean)]))
        line = PLG.dirty_refusal([("this builder's tree", clean), ("the integrator's tree", dict(
            clean, root="/home/ultron/protocol_pulse", dirty=["pipeline/edl_rules.py (staged, not committed)"]))])
        self.assertTrue(line.startswith("REFUSED: the build did not start because code was changed and not committed"))
        self.assertIn("in the integrator's tree (/home/ultron/protocol_pulse): pipeline/edl_rules.py (staged", line)
        self.assertNotIn("\n", line)

    def test_a_dirty_tree_refuses_the_build_before_any_record(self):
        """The driver's real path (its entry taken as its own file run as __main__, not a test), with the integrator's
        tree staged: exit 2, the one line on stderr, no record folder."""
        import io
        import proof_ledger as PLG
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        real = dict(PLG.entry_of(), ok=True, why=None, under_test=False)
        dirty = [("this builder's tree", {"root": REPO, "head": "1" * 40, "dirty": []}),
                 ("the integrator's tree", {"root": "/home/ultron/protocol_pulse", "head": "2" * 40,
                                            "dirty": ["pipeline/owner_rules.py (staged, not committed)"]})]
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with mock.patch.object(PLG, "entry_of", lambda: real), mock.patch.object(PLG, "trees_state", lambda: dirty), \
                    mock.patch.object(PLG, "HERE", d), mock.patch.object(PLG.signal, "signal", lambda *a: None), \
                    mock.patch.object(OC, "OUTCOMES", os.path.join(d, "o.jsonl")), mock.patch.object(sys, "stderr", err):
                self.assertEqual(PLG.main(["--delivered", *pins]), 2)
            self.assertIn("pipeline/owner_rules.py (staged, not committed)", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "proof")))                  # no record folder
            self.assertEqual(OC.lines(os.path.join(d, "o.jsonl")), [])                  # and no outcome line: no build

    def test_an_owner_rules_mismatch_refuses_the_build_before_any_record(self):
        """ORCHESTRATOR 10:55 ET Nov 24: the integrator's owner_rules come from the pushed release revision; the live
        copy differing from it (out_edge.pin raises) aborts the real driver: exit 2, the line on stderr, no record
        folder, no outcome line, so no model call."""
        import io
        import out_edge as OE
        import proof_ledger as PLG
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        real = dict(PLG.entry_of(), ok=True, why=None, under_test=False)
        clean = [("this builder's tree", {"root": REPO, "head": "1" * 40, "dirty": []}),
                 ("the integrator's tree", {"root": "/home/ultron/protocol_pulse", "head": "2" * 40, "dirty": []})]

        def mismatch():
            raise OSError("owner_rules mismatch: the live /x/pipeline/owner_rules.py (sha 92324ae0e44f) is not the "
                          "pushed release revision 2c50bad756ab's pipeline/owner_rules.py (sha b263139ade7c): no build")
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with mock.patch.object(PLG, "entry_of", lambda: real), mock.patch.object(PLG, "trees_state", lambda: clean), \
                    mock.patch.object(OE, "pin", mismatch), \
                    mock.patch.object(PLG, "HERE", d), mock.patch.object(PLG.signal, "signal", lambda *a: None), \
                    mock.patch.object(OC, "OUTCOMES", os.path.join(d, "o.jsonl")), mock.patch.object(sys, "stderr", err), \
                    mock.patch("urllib.request.urlopen", side_effect=AssertionError("a refused run reached the network")):
                self.assertEqual(PLG.main(["--delivered", *pins]), 2)
            self.assertIn("REFUSED: owner_rules mismatch", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "proof")))                  # no record folder
            self.assertEqual(OC.lines(os.path.join(d, "o.jsonl")), [])                  # and no outcome line: no build

    def test_a_run_that_only_claims_a_test_writes_no_real_record(self):
        """Audit L2 (qwen, cycle 2): a wrapper can set the test variable and import pytest; its run is then refused
        before it can write into the real build records."""
        import io
        import proof_ledger as PLG
        pins = [os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")]
        before = set(os.listdir(PROOF))
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err), \
                mock.patch("os.makedirs", side_effect=AssertionError("a refused run went on to write a record")), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("a refused run reached the network")):
            self.assertEqual(PLG.main(["--delivered", *pins]), 2)                       # HERE is the real folder
        self.assertIn("never writes into the real build records", err.getvalue())
        self.assertEqual(set(os.listdir(PROOF)), before)


class TestTimePerStage(unittest.TestCase):
    """The orchestrator, 09:55 ET Nov 24: "Record wall-clock time PER STAGE in the build record ... pool, step A, second
    ear, out-edge question, hooks, vision, line-ups, writes, gates, seal, render call"."""

    def test_the_clock_gives_each_line_s_time_to_its_stage(self):
        import proof_ledger as PLG
        t = [100.0]
        with mock.patch.object(PLG.time, "time", lambda: t[0]):
            c = PLG.StageClock(100.0)
            for dt, line in ((2, "  adapter: 287 rows"), (5, "  RULING 137 NEVER EMPTY (stage 1): 5 moment(s) step A refused"),
                             (3, "  4 of them pass the second recognition pass and CUTTABLE (2 s)"),
                             (4, "  out edge (ruling 162 (1)): 2 asked"), (1, "  visual (ruling 70): 3 hook(s) seen"),
                             (2, "  hooks (ruling 59): 3 can open"), (6, "  3 angles from heimdall:qwen (3 s)"),
                             (7, "  angle 1 line-up 1 write 1 (heimdall:qwen, takeaway 14 words): cheap PASS"),
                             (8, "    fidelity PASS (takeaway PASS), context PASS"), (1, "an unnamed line"),
                             (2, "PACKAGE (37.6 s) pin x")):
                t[0] += dt
                c.mark(line)
        self.assertEqual(c.totals(), {"pool": 2.0, "step A": 5.0, "second ear": 3.0, "out-edge question": 4.0,
                                      "hooks": 2.0, "vision": 1.0, "line-ups": 6.0, "writes": 7.0, "gates": 9.0,
                                      "seal": 2.0})
        self.assertEqual(list(c.totals()), [s for s in PLG.STAGES_TIMED if s in c.totals()])   # in the build's order

    def test_the_render_call_s_time_is_on_the_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.jsonl")
            line = dict(OC.outcome_of(os.path.join(PROOF, "ledger_20261124_033614"), build_no=167),
                        seconds={"pool": 1.0})
            OC.write_once(line, p)
            got = OC.amend_render("ledger_20261124_033614", 0, "", pin="x.json", path=p, seconds=12.34)
            self.assertEqual((got["outcome"], got["seconds"]), ("SEALED", {"pool": 1.0, "render call": 12.3}))
            self.assertEqual(len(OC.lines(p)), 1)


class TestAcceptanceItem2bPlainNotes(unittest.TestCase):
    """THE ACCEPTANCE TEST, item 2 (b): every outcome's note is "a reason PBX can read in one sentence": plain words,
    no ruling numbers, no ids; the technical reason is the line's detail."""
    BAD = __import__("re").compile(r"\bruling\b|\b[0-9a-f]{20}\b|\bS-[0-9a-f]{8}\b|\d|_")

    def plain(self, note, ctx):
        self.assertTrue(note and note.endswith(".") and ". " not in note.strip(".") and "\n" not in note, (note, ctx))
        self.assertIsNone(self.BAD.search(note), (note, ctx))

    def test_every_note(self):
        for o in OC.KINDS:
            self.plain(OC.plain_note(o, "nowhere"), o)
        for (o, st), n in OC.NOTES.items():
            self.plain(n, (o, st))
        self.plain(OC.NOTE_LOCK_OFF, "lock off")
        for why, pre, *_ in TestEveryReasonOneOutcome.CASES:
            c = OC.classify(why, pre)
            self.plain(OC.plain_note(c["outcome"], c["stage"], c["gate"]), why)
        for run in ("ledger_20261124_000525", "ledger_20261124_003124", "ledger_20261124_004415",
                    "ledger_20261124_012843", "ledger_20261124_012928", "ledger_20261124_032741",
                    "ledger_20261124_033614"):
            x = OC.outcome_of(os.path.join(PROOF, run))
            self.plain(x["note"], run)
            self.assertNotEqual(x["note"], x["detail"])
        for x in OC.lines(os.path.join(REPO, "data", "builds", "outcomes.jsonl")):     # the backfilled lines
            self.plain(x["note"], x["run"])


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

    STUB_DRIVER = """import json, os, sys
if __name__ == "__main__":
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.environ["STUB_CALLS"], "a").write(" ".join(a) + "\\n")
    seal = os.environ.get("STUB_SEAL") == "1"
    out = os.path.join(here, "proof", "ledger_2099010" + os.environ["STUB_RUN"] + "_000000")
    os.makedirs(out)
    open(get("--out-dir-file"), "w").write(out + "\\n")
    json.dump({"argv": a}, open(os.path.join(out, "inputs.json"), "w"))
    json.dump({"package": {"x": 1} if seal else None, "usable": 0, "prescreen": {},
               "why_none": None if seal else "no angle gave a line-up to try",
               "spend_ruling_48": {"before": 0.0, "after": 0.0}}, open(os.path.join(out, "package.json"), "w"))
    if seal:
        json.dump({"story_id": "moments-x", "moments_package": {"package_sha256": "a" * 64}},
                  open(os.path.join(out, "MOMENTS_PIN_LEDGER.json"), "w"))
    sys.path.insert(0, here)
    import outcomes as OC
    line = OC.outcome_of(out, build_no=int(get("--build-no")))
    OC.write_once(line)
    print("RULING 160 (2b): outcome %s at %s: x" % (line["outcome"], line["stage"]))
"""

    def sandbox(self, d):
        """A repository of its own: the committed launcher, its record scripts, the outcome module, a stand-in driver
        (it records its arguments and makes a record, sealing when STUB_SEAL=1) and stand-ins for the spend and
        scorer probes; committed and pushed to a bare remote."""
        import shutil
        repo, bare = os.path.join(d, "repo"), os.path.join(d, "bare.git")
        rec = os.path.join(repo, "tests", "package", "record")
        os.makedirs(rec)
        os.makedirs(os.path.join(repo, "pipeline"))
        os.makedirs(os.path.join(repo, "docs", "audits", "parallel"))
        for f in ("build_and_record.sh", "state_line.py", "attempt_summary.py"):
            shutil.copy(os.path.join(RECORD, f), rec)
        shutil.copy(os.path.join(HERE, "outcomes.py"), os.path.join(repo, "tests", "package"))
        open(os.path.join(rec, "day_spent.py"), "w").write("print('0.000000 SPEND_D20261124.json')\n")
        open(os.path.join(rec, "day118.py"), "w").write("print('TODAY: stand-in')\n")
        open(os.path.join(rec, "scorer_stale.py"), "w").write("")
        open(os.path.join(repo, "tests", "package", "proof_ledger.py"), "w").write(self.STUB_DRIVER)
        open(os.path.join(repo, "pipeline", "m.py"), "w").write("X = 1\n")
        open(os.path.join(repo, "docs", "audits", "parallel", "pp-selectid_STATE.md"), "w").write("line\n")
        open(os.path.join(d, "only.json"), "w").write('{"ids": [], "why": "test"}\n')
        render = os.path.join(d, "render.sh")
        open(render, "w").write('#!/bin/bash\necho "$@" >> "$STUB_RENDER_CALLS"\n'
                                '[ -n "${STUB_RENDER_SAYS:-}" ] && echo "$STUB_RENDER_SAYS" >&2\n'
                                'exit "${STUB_RENDER_EXIT:-0}"\n')
        os.chmod(render, 0o755)
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", "c1")
        self.git(repo, "remote", "add", "origin", bare)
        self.git(repo, "push", "-q", "-u", "origin", "HEAD")
        return repo

    def launch(self, repo, d, run, env=None, n="7"):
        e = dict(NOENV, STUB_CALLS=os.path.join(d, "driver_calls.log"), STUB_RENDER_CALLS=os.path.join(d, "render.log"),
                 PP_RENDER_SCRIPT=os.path.join(d, "render.sh"), STUB_RUN=str(run), GIT_AUTHOR_NAME="t",
                 GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", **(env or {}))
        r = subprocess.run(["bash", os.path.join(repo, "tests", "package", "record", "build_and_record.sh"), n, "test",
                            "--only", os.path.join(d, "only.json")], env=e, capture_output=True, text=True,
                           timeout=180)
        if r.returncode == 3:
            self.skipTest(f"the launcher's own guard: {r.stdout.strip()[:200]}")   # a render or build running
        return r

    @staticmethod
    def read(p):
        return open(p).read() if os.path.exists(p) else ""

    def test_item9_build_168s_start_line_refuses_before_any_model_call(self):
        """THE ACCEPTANCE LIST, item 9: "start it the way build 168 was started; it refuses". Build 168 was started
        `DRIVER=$S/by_hand_155.py bash build_and_record.sh 168 "..." --only FILE --stop-usd 1.20` with LOCK=on; the
        committed launcher, given exactly that, refuses before any python runs (a stand-in python3 logs every call)."""
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "calls.log")
            fake = os.path.join(d, "bin", "python3")
            os.makedirs(os.path.dirname(fake))
            open(fake, "w").write(f'#!/bin/bash\necho "$@" >> {log}\nexec {sys.executable} "$@"\n')
            os.chmod(fake, 0o755)
            wrapper = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/" \
                      "scratchpad/by_hand_155.py"
            existing = os.path.join(d, "by_hand_155.py")
            open(existing, "w").write("print('by hand')\n")
            for drv in (wrapper, existing):
                env = dict(NOENV, PATH=os.path.dirname(fake) + os.pathsep + os.environ.get("PATH", ""), LOCK="on",
                           DRIVER=drv)
                r = subprocess.run(["bash", os.path.join(RECORD, "build_and_record.sh"), "168",
                                    "RULING 158 (3): 'Bitcoin hits two-year low, then bounces off the bottom' "
                                    "(S-13ad274d) without Digital Asset News (on-screen ads: OUT)", "--only",
                                    os.path.join(PROOF, "ledger_20261124_043726", "ONLY.json"), "--stop-usd", "1.20"],
                                   env=env, capture_output=True, text=True, timeout=60, cwd=REPO)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn(f"REFUSED: DRIVER={drv} names another driver", r.stdout)
                self.assertEqual(self.read(log), "")                 # no python at all: no model call, no record

    def test_the_launcher_runs_the_committed_driver_and_hands_the_sealed_pin_to_the_render(self):
        """Amendment C and item 9, on a repository of its own: the driver gets the lock pre-check ON, a unique build id
        and a file for its own record folder; the record committed is THIS run's; a sealed pin goes to the render
        script as exactly `--pinned <this run's pin>` and its exit is on the build's one outcome line (0: SEALED; the
        readiness check's refusal: HARD_REJECTED at the render; any other: RENDER_FAILED); nothing sealed, no render
        call. A changed driver, changed code or an unpushed commit refuses before the driver runs."""
        with tempfile.TemporaryDirectory() as d:
            repo = self.sandbox(d)
            out_lines = lambda: [json.loads(x) for x in self.read(os.path.join(repo, "data", "builds",
                                                                                "outcomes.jsonl")).splitlines()]
            r = self.launch(repo, d, 1, {"STUB_SEAL": "1"})
            self.assertEqual(r.returncode, 0, r.stdout[-800:] + r.stderr[-800:])
            calls = self.read(os.path.join(d, "driver_calls.log")).split()
            self.assertEqual(calls[calls.index("--lock-precheck") + 1], "on")
            self.assertRegex(calls[calls.index("--build-id") + 1], r"^b7-\d{8}T\d{6}Z-\d+$")
            pin = os.path.join(repo, "tests", "package", "proof", "ledger_20990101_000000", "MOMENTS_PIN_LEDGER.json")
            self.assertEqual(self.read(os.path.join(d, "render.log")).split(), ["--pinned", pin])
            self.assertEqual([(x["outcome"], (x.get("render") or {}).get("exit")) for x in out_lines()],
                             [("SEALED", 0)])
            self.assertIn("render call", out_lines()[0]["seconds"])      # the render call's own time
            self.assertIn("ledger_20990101_000000/MOMENTS_PIN_LEDGER.json", self.git(repo, "show", "--stat", "HEAD~1"))
            for run, rx, says, kind in ((2, "3", "pulse_check_run: the pin is not READY (check_pin_only): refused",
                                         "HARD_REJECTED"), (3, "75", "another run holds the lock", "RENDER_FAILED")):
                r = self.launch(repo, d, run, {"STUB_SEAL": "1", "STUB_RENDER_EXIT": rx, "STUB_RENDER_SAYS": says})
                self.assertEqual(r.returncode, 0, r.stdout[-800:])
                last = out_lines()[-1]
                self.assertEqual((last["outcome"], last["stage"], last["render"]["exit"]), (kind, "render", int(rx)))
            os.remove(os.path.join(d, "render.log"))
            r = self.launch(repo, d, 4)                                  # nothing sealed: no render call
            self.assertEqual(r.returncode, 0, r.stdout[-800:])
            self.assertFalse(os.path.exists(os.path.join(d, "render.log")))
            self.assertEqual(out_lines()[-1]["outcome"], "HARD_REJECTED")
            drv = os.path.join(repo, "tests", "package", "proof_ledger.py")
            mod = os.path.join(repo, "pipeline", "m.py")
            for change, path, words in ((lambda: open(drv, "a").write("# by hand\n"), drv,
                                         "differs from the committed one"),
                                        (lambda: open(mod, "a").write("X = 2\n"), mod, "code changed and not committed")):
                open(os.path.join(d, "driver_calls.log"), "w").close()
                change()
                r = self.launch(repo, d, 5)
                self.assertEqual(r.returncode, 6, r.stdout[-400:])
                self.assertIn(words, r.stdout)
                self.assertEqual(self.read(os.path.join(d, "driver_calls.log")), "")    # the driver never ran
                self.git(repo, "checkout", "-q", "--", path)
            open(mod, "a").write("X = 3\n")
            self.git(repo, "commit", "-q", "-am", "not pushed")
            r = self.launch(repo, d, 6)
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
            for bad in ("/tmp/claude-1000", "scratchpad", "/home/ultron/worktrees/pp-selectid"):
                self.assertNotIn(bad, src, f)
        src = open(os.path.join(RECORD, "build_and_record.sh")).read()   # amendment C's defects, gone
        for bad in ("DRIVER=${DRIVER:-", "SPEND_B4", "PIN IT TO THE INTEGRATOR", "ls -td", "by_hand", "LOCK:-off"):
            self.assertNotIn(bad, src)


if __name__ == "__main__":
    unittest.main()
