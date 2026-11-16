#!/usr/bin/env python3
"""The session watchdog (orchestrator order 05:55 ET Nov 16) on CANNED pane texts, shaped as the claude panes read on
Nov 16 (spinner '✽ Bunning… (13m 6s · ↓ 60.8k tokens · thinking)', the input box between two rules, the footer
'... · esc to interrupt · ↓ to manage'). No tmux, no network, no model: tmux and Telegram are stubbed.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_session_watchdog.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))     # the tool lives in tools/, its tests here
import session_watchdog as W  # noqa: E402

ET = ZoneInfo("America/New_York")
RULE = "─" * 120
BUSY = "✽ Bunning… (13m 6s · ↓ 60.8k tokens · thinking)"
DAY = datetime(2026, 11, 16, 10, 0, tzinfo=ET).timestamp()        # 10:00 ET: lines may go
NIGHT = datetime(2026, 11, 16, 3, 0, tzinfo=ET).timestamp()       # 03:00 ET: only (4) and (6)


def pane(content, spinner=None, busy=None, notice=True, below=()):
    """A claude pane as capture-pane prints it: content, the spinner (+ a tip) while a turn runs, the update notice,
    the input box, the footer (busy = 'esc to interrupt' in it), trailing blank lines."""
    busy = bool(spinner) if busy is None else busy
    lines = list(content) + [""]
    if spinner:
        lines += [spinner, "  ⎿  Tip: Running multiple Claude sessions? Press ← on an empty prompt to see them all"]
    if notice:
        lines.append(" " * 90 + "✔ Update installed")
    lines += [RULE, "❯ ", RULE, "  ⏵⏵ bypass permissions on · gh auth login for PR status · 4 shells"
              + (" · esc to interrupt · ↓ to manage" if busy else "")] + list(below)
    return lines + ["", "", ""]


def block(head, cmd=None, out=("done",), result=True):
    b = [f"● {head}"]
    if cmd is not None:
        b.append(f"  ⎿  $ {cmd}")
        b += [f"     {x}" for x in out]
    elif result:
        b.append(f"  ⎿  {out[0]}")
    return b + [""]


def turn(*blocks_, prompt="❯ do the work"):
    lines = [prompt] if prompt else []
    for b in blocks_:
        lines += b
    return lines


class TestParse(unittest.TestCase):
    def test_a_turn_in_progress_and_its_own_timer(self):
        p = W.parse_pane(pane(turn(block("Reading the log", "tail -n 5 x.log")), spinner=BUSY))
        self.assertTrue(p["in_turn"])
        self.assertEqual(p["timer_s"], 13 * 60 + 6)
        self.assertEqual(p["turn"][0], "● Reading the log")
        self.assertNotIn(BUSY, p["content"])                          # the spinner is never content
        self.assertFalse(any("Update installed" in x or "Tip:" in x for x in p["content"]))

    def test_timer_forms(self):
        for spin, want in (("✢ Coalescing… (1m 12s · ↓ 6.5k tokens · thought for 5s)", 72),
                           ("✶ Warping… (2h 31m 5s · ↓ 44.0k tokens · thinking some more)", 2 * 3600 + 31 * 60 + 5),
                           ("· Thinking… (45s · esc to interrupt)", 45), ("✻ Brewing… (1h 2m · ↓ 3k tokens)", 3720)):
            with self.subTest(spin=spin):
                self.assertEqual(W.parse_pane(pane(["❯ go"], spinner=spin))["timer_s"], want)

    def test_an_idle_pane(self):
        p = W.parse_pane(pane(turn(block("Done", result=False)) + ["✻ Baked for 18s · done 11:11 PM"]))
        self.assertFalse(p["in_turn"])
        self.assertIsNone(p["timer_s"])

    def test_words_quoted_in_the_conversation_are_never_read_as_the_pane_state(self):
        # the order itself, pasted into a pane: its text names every marker
        quoted = ["❯ ORCHESTRATOR ORDER: (1) STUCK: the pane shows a turn in progress ('esc to interrupt') ...",
                  "  (5) CONTEXT: a pane showing 'until auto-compact' at 3 % or less, or 'Context low'.",
                  "  Context left until auto-compact: 1%", "  Context low (2% remaining)",
                  "✽ Bunning… (3h 1m 6s · ↓ 1k tokens · thinking)"]
        p = W.parse_pane(pane(quoted + block("Read it", result=False)))
        self.assertFalse(p["in_turn"])
        self.assertIsNone(p["timer_s"])                               # an idle pane has no spinner
        f, _ = W.claude_findings("pipeline_x", pane(quoted + block("Read it", result=False)), {}, DAY)
        self.assertEqual(f, [])

    def test_no_input_box_falls_back_to_the_last_lines(self):
        p = W.parse_pane(["some output", "more", "  ⏵⏵ bypass permissions on · esc to interrupt"])
        self.assertTrue(p["in_turn"])


class TestLoop(unittest.TestCase):
    def find(self, lines, st=None):
        f, _ = W.claude_findings("pipeline_x", pane(lines, spinner=BUSY), st if st is not None else {}, DAY)
        return [x for x in f if x["kind"] == "LOOP"]

    def test_the_same_command_in_five_blocks_is_a_loop_four_is_not(self):
        five = turn(*[block("Checking the status", "git status", out=("On branch main",)) for _ in range(5)])
        four = turn(*[block("Checking the status", "git status", out=("On branch main",)) for _ in range(4)])
        got = self.find(five)
        self.assertEqual(len(got), 1)
        self.assertIn("the same command 5 times in this turn: 'git status On branch main'", got[0]["what"])
        self.assertEqual(self.find(four), [])

    def test_the_same_error_line_in_five_blocks_is_a_loop(self):
        bs = [block(f"Try {i}", f"python3 run.py --try {i}", out=("ModuleNotFoundError: No module named 'x'",))
              for i in range(5)]
        got = self.find(turn(*bs))
        self.assertEqual([x["what"] for x in got],
                         ["the same error line 5 times in this turn: 'ModuleNotFoundError: No module named 'x''"])

    def test_one_output_repeating_an_error_counts_once(self):
        bs = [block("Tail the log", "tail -n 6 x.log", out=["RuntimeError: the lease is held by y"] * 6)]
        self.assertEqual(self.find(turn(*bs)), [])

    def test_the_generic_exit_code_header_is_not_an_error_line(self):
        bs = [[f"● Grep {i}", "  ⎿  Error: Exit code 1", ""] for i in range(6)]
        self.assertEqual(self.find(turn(*bs)), [])

    def test_two_heredocs_sharing_a_first_line_are_different_commands(self):
        bs = [[f"● Script {i}", "  ⎿  $ python3 - <<'EOF'", f"     print({i})", "     EOF", ""] for i in range(6)]
        self.assertEqual(self.find(turn(*bs)), [])

    def test_a_repeated_tool_action_line_is_a_loop(self):
        bs = [block("Reading the backfill helper", result=True, out=("Read 47 lines",)) for _ in range(5)]
        self.assertEqual(len(self.find(turn(*bs))), 1)

    def test_an_idle_pane_has_no_loop(self):
        five = turn(*[block("Checking", "git status") for _ in range(5)])
        f, _ = W.claude_findings("pipeline_x", pane(five), {}, DAY)
        self.assertEqual(f, [])


class TestTurnAcrossPasses(unittest.TestCase):
    """A claude pane keeps no scrollback: the turn is gathered pass by pass."""

    def test_a_loop_split_over_two_screens_is_found_and_an_unchanged_screen_counts_once(self):
        st = {}
        reps = [block(f"Checking {i}", "git status", out=()) for i in range(5)]
        first = turn(*reps[:3])                                       # the prompt and 3 repetitions
        second = [x for b in reps[1:] for x in b]                     # scrolled: the prompt is off screen
        f1, _ = W.claude_findings("s", pane(first, spinner=BUSY), st, DAY)
        f1b, _ = W.claude_findings("s", pane(first, spinner=BUSY), st, DAY + 300)    # the same screen again
        self.assertEqual([x for x in f1 + f1b if x["kind"] == "LOOP"], [])
        self.assertEqual(sum("$ git status" in x for x in st["turn"]["lines"]), 3)  # never counted twice
        f2, _ = W.claude_findings("s", pane(second, spinner=BUSY), st, DAY + 600)
        self.assertEqual([x["what"] for x in f2 if x["kind"] == "LOOP"], ["the same command 5 times in this turn: 'git status'"])

    def test_no_overlap_starts_over_and_an_idle_pane_clears_the_turn(self):
        self.assertEqual(W.join(["a", "b", "c", "d"], ["x", "y", "z"]), ["x", "y", "z"])
        self.assertEqual(W.join(["a", "b", "c", "d"], []), ["a", "b", "c", "d"])
        self.assertEqual(W.join(["a", "b", "c", "d"], ["b", "c", "d", "e"]), ["a", "b", "c", "d", "e"])
        self.assertEqual(W.join(["a", "b", "c", "OLD"], ["a", "b", "c", "NEW", "e"]), ["a", "b", "c", "NEW", "e"])
        st = {}
        W.claude_findings("s", pane(turn(block("x", "ls")), spinner=BUSY), st, DAY)
        self.assertIn("turn", st)
        W.claude_findings("s", pane(turn(block("x", "ls"))), st, DAY + 300)
        self.assertNotIn("turn", st)

    def test_a_new_prompt_is_a_new_turn(self):
        st = {}
        W.claude_findings("s", pane(turn(*[block("c", "git status")] * 3), spinner=BUSY), st, DAY)
        W.claude_findings("s", pane(turn(*[block("c", "git status")] * 3, prompt="❯ next"), spinner=BUSY), st, DAY + 300)
        self.assertEqual(sum("$ git status" in x for x in st["turn"]["lines"]), 3)


class TestStuckLongContext(unittest.TestCase):
    def test_stuck_after_45_minutes_unchanged_in_a_turn(self):
        st, screen = {}, pane(turn(block("Waiting", "sleep 9999", out=("Running…",))), spinner=BUSY)
        for dt_s, want in ((0, 0), (44 * 60, 0), (45 * 60, 1)):
            f, _ = W.claude_findings("s", screen, st, DAY + dt_s)
            self.assertEqual(len([x for x in f if x["kind"] == "STUCK"]), want, dt_s)
        self.assertEqual([x["since"] for x in f if x["kind"] == "STUCK"], [DAY])

    def test_the_timer_and_token_count_moving_is_not_progress(self):
        st = {}
        W.claude_findings("s", pane(turn(block("W", "make")), spinner="✽ Bunning… (1m 2s · ↓ 1.0k tokens)"), st, DAY)
        f, _ = W.claude_findings("s", pane(turn(block("W", "make")), spinner="✽ Bunning… (46m 2s · ↓ 9.9k tokens)"),
                                 st, DAY + 45 * 60)
        self.assertEqual([x["kind"] for x in f], ["STUCK"])

    def test_a_changing_screen_or_an_idle_pane_is_not_stuck(self):
        st = {}
        W.claude_findings("s", pane(turn(block("A", "ls")), spinner=BUSY), st, DAY)
        f, _ = W.claude_findings("s", pane(turn(block("A", "ls"), block("B", "pwd")), spinner=BUSY), st, DAY + 46 * 60)
        self.assertEqual(f, [])
        st = {}
        W.claude_findings("s", pane(turn(block("A", "ls"))), st, DAY)
        f, _ = W.claude_findings("s", pane(turn(block("A", "ls"))), st, DAY + 3 * 3600)
        self.assertEqual(f, [])

    def test_the_same_shell_command_still_the_latest_action_for_45_minutes(self):
        st = {}
        for k in range(10):                                            # its output grows: the screen changes
            out = tuple(f"line {i}" for i in range(k + 1))[-3:]
            f, _ = W.claude_findings("s", pane(turn(block("Build", "make all", out=out)), spinner=BUSY), st,
                                     DAY + k * 300)
        self.assertEqual([x["kind"] for x in f], ["STUCK"])
        self.assertIn("the same shell command for 45 min: 'make all", f[0]["what"])

    def test_a_long_turn_by_its_own_timer(self):
        for spin, n in (("✶ Warping… (2h 30m 1s · ↓ 4k tokens)", 1), ("✶ Warping… (2h 29m 59s · ↓ 4k tokens)", 0)):
            f, _ = W.claude_findings("s", pane(["❯ go", "● working"], spinner=spin), {}, DAY)
            self.assertEqual(len([x for x in f if x["kind"] == "LONG_TURN"]), n, spin)
        f, _ = W.claude_findings("s", pane(["❯ go"], spinner="✶ Warping… (2h 31m 5s · ↓ 4k tokens)"), {}, DAY)
        self.assertEqual(f[0]["what"], "one turn at 2 h 31 min by its own timer")
        self.assertEqual(f[0]["since"], round(DAY - (2 * 3600 + 31 * 60 + 5), 1))

    def test_context_low_shown_by_the_pane(self):
        cases = ((["  Context left until auto-compact: 3%"], 1), (["  Context left until auto-compact: 4%"], 0),
                 (["  Context low (8% remaining) · Run /compact to compact & continue"], 1), ((), 0))
        for below, n in cases:
            f, _ = W.claude_findings("s", pane(["❯ go"], below=below), {}, DAY)
            self.assertEqual(len([x for x in f if x["kind"] == "CONTEXT"]), n, below)


class Paths(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="watchdog_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.paths = {"log": os.path.join(self.d, "logs", "session_watchdog.log"),
                      "status": os.path.join(self.d, "status.json"), "state": os.path.join(self.d, "state.json"),
                      "moment_ledger": os.path.join(self.d, "moment_ledger.jsonl"),
                      "builds": os.path.join(self.d, "proof", "ledger_*"),
                      "spend": os.path.join(self.d, "proof", "BATCH*_LEDGER.json"),
                      "wordpass_log": os.path.join(self.d, "word_pass_worker.log")}
        os.makedirs(os.path.join(self.d, "proof"))

    def touch(self, path, t):
        if not os.path.exists(path):
            os.makedirs(path) if path.endswith(("_1", "_2")) else open(path, "w").close()
        os.utime(path, (t, t))

    def batch(self, usd, frm="2026-11-15T21:10 ET", to="2026-11-16T21:10 ET", capped="outside vendors (Heimdall not "
              "capped)", name="BATCH4_LEDGER.json"):
        with open(os.path.join(self.d, "proof", name), "w") as f:
            json.dump({"from": frm, "to": to, "all_in": usd, "capped": capped, "cap": 8.0}, f)


class TestIdleWithWork(Paths):
    def all_present(self):
        return {"pipeline_pp_wordpass", "pipeline_pp_ingest_watch", "pipeline_pp_selectid"}

    def test_a_missing_word_pass_or_ingest_watcher(self):
        self.touch(self.paths["wordpass_log"], DAY)
        st = {}
        f = W.idle_with_work({"pipeline_pp_selectid"}, {}, st, DAY, self.paths, waiting=lambda now: (0, None))
        self.assertEqual(sorted(x["session"] for x in f), ["pipeline_pp_ingest_watch", "pipeline_pp_wordpass"])
        f = W.idle_with_work(self.all_present(), {}, st, DAY + 300, self.paths, waiting=lambda now: (0, None))
        self.assertEqual(f, [])

    def test_the_builder_idle_on_a_ledger_changed_41_min_ago_with_no_build_after(self):
        self.touch(self.paths["wordpass_log"], DAY)
        idle = {"in_turn": False}
        self.touch(self.paths["moment_ledger"], DAY - 41 * 60)
        self.touch(os.path.join(self.d, "proof", "ledger_1"), DAY - 50 * 60)       # the last build: before it
        f = W.idle_with_work(self.all_present(), {"pipeline_pp_selectid": idle}, {}, DAY, self.paths,
                             waiting=lambda now: (0, None))
        self.assertEqual([(x["session"], x["kind"]) for x in f], [("pipeline_pp_selectid", "IDLE_WITH_WORK")])
        self.assertIn("idle at its prompt; the moments ledger changed at", f[0]["what"])
        for builds_at, ledger_at, pane_ in ((DAY - 30 * 60, DAY - 41 * 60, idle),        # a build followed
                                            (DAY - 50 * 60, DAY - 39 * 60, idle),        # changed 39 min ago
                                            (DAY - 50 * 60, DAY - 41 * 60, {"in_turn": True})):   # at work
            self.touch(os.path.join(self.d, "proof", "ledger_1"), builds_at)
            self.touch(self.paths["moment_ledger"], ledger_at)
            f = W.idle_with_work(self.all_present(), {"pipeline_pp_selectid": pane_}, {}, DAY, self.paths,
                                 waiting=lambda now: (0, None))
            self.assertEqual(f, [], (builds_at, ledger_at, pane_))

    def test_the_word_pass_silent_30_min_with_rows_waiting(self):
        asked = []

        def waiting(n):
            def f(now):
                asked.append(now)
                return n
            return f
        self.touch(self.paths["wordpass_log"], DAY - 29 * 60)
        self.assertEqual(W.idle_with_work(self.all_present(), {}, {}, DAY, self.paths, waiting((3, None))), [])
        self.assertEqual(asked, [])                                   # a live log: the ledger is not even read
        self.touch(self.paths["wordpass_log"], DAY - 31 * 60)
        f = W.idle_with_work(self.all_present(), {}, {}, DAY, self.paths, waiting((3, None)))
        self.assertEqual([x["what"] for x in f], ["3 rows waiting, no word-pass cycle since 09:29 ET"])
        self.assertEqual(W.idle_with_work(self.all_present(), {}, {}, DAY, self.paths, waiting((0, None))), [])
        f = W.idle_with_work(self.all_present(), {}, {}, DAY, self.paths, waiting((None, "RuntimeError: x")))
        self.assertIn("rows waiting unknown (RuntimeError: x)", f[0]["what"])


class TestSpend(Paths):
    def test_80_and_100_percent_once_each_per_day_window(self):
        st, send = {}, mock.Mock(return_value=7)
        self.batch(0.79)
        self.assertEqual(W.spend_findings(st, DAY, self.paths)[0], [])
        self.batch(0.80)
        f, view = W.spend_findings(st, DAY, self.paths)
        self.assertEqual([(x["key"], x["level"]) for x in f], [("spend:80%", 0.8)])
        self.assertEqual(view["usd"], 0.8)
        W.dispatch(f, st, DAY, send)
        self.assertEqual(W.spend_findings(st, DAY + 300, self.paths)[0], [])        # said once
        self.batch(1.02)
        f, _ = W.spend_findings(st, DAY + 600, self.paths)
        self.assertEqual([x["key"] for x in f], ["spend:100%"])
        self.assertIn("$1.02, at 100% of ruling 118's $1.00 day cap", f[0]["what"])
        W.dispatch(f, st, DAY + 600, send)
        self.assertEqual(W.spend_findings(st, DAY + 900, self.paths)[0], [])
        self.assertEqual(send.call_count, 2)

    def test_straight_to_100_says_100_only(self):
        self.batch(1.30)
        f, _ = W.spend_findings({}, DAY, self.paths)
        self.assertEqual([x["level"] for x in f], [1.0])

    def test_only_a_one_day_outside_vendor_window_that_holds_now(self):
        for kw in ({"frm": "2026-11-14T21:10 ET", "to": "2026-11-15T21:10 ET"},       # yesterday's window
                   {"frm": "2026-11-15T21:10 ET", "to": "2026-11-18T21:10 ET"},       # a three-day batch
                   {"capped": "everything"},                                         # not an outside-vendor cap
                   {"frm": "2026-11-15 21:10"}):                                     # not an ET stamp
            with self.subTest(kw=kw):
                self.batch(5.0, **kw)
                f, view = W.spend_findings({}, DAY, self.paths)
                self.assertEqual(f, [])
                self.assertFalse(view["readable"])
                self.assertIn("no batch ledger", view["why"])


class TestDispatch(unittest.TestCase):
    def f(self, session, kind, key=None, **kw):
        return W.finding(session, kind, f"{kind.lower()} detail", DAY - 600, key=key, **kw)

    def test_one_line_per_session_by_day_only_4_and_6_at_night(self):
        sent = []

        def send(key, kinds, line, now):
            sent.append((key, kinds, line))
            return len(sent)
        fs = [self.f("pipeline_a", "LOOP"), self.f("pipeline_a", "LONG_TURN"), self.f("pipeline_b", "CONTEXT"),
              self.f("pipeline_pp_wordpass", "IDLE_WITH_WORK"),
              self.f("pipeline_pp_selectid", "SPEND", key="spend:80%", level=0.8)]
        st = {}
        out = W.dispatch(fs, st, DAY, send)
        self.assertEqual([k for k, _, _ in sent], ["pipeline_a", "pipeline_b", "pipeline_pp_wordpass", "spend:80%"])
        self.assertEqual(sent[0][2], "pipeline_a: LOOP: loop detail (since 09:50 ET); LONG TURN: long_turn detail "
                                     "(since 09:50 ET)")
        self.assertEqual(st["spend"]["said"], 0.8)
        self.assertEqual(len(out), 4)
        sent.clear()
        W.dispatch(fs, {}, NIGHT, send)
        self.assertEqual([k for k, _, _ in sent], ["pipeline_pp_wordpass", "spend:80%"])

    def test_a_held_or_refused_line_is_not_said_an_unknown_one_is(self):
        sys.path.insert(0, HERE)
        import telegram as T
        fs = [self.f("pipeline_pp_selectid", "SPEND", key="spend:80%", level=0.8)]
        for exc, how, said in ((T.WatchdogRefused("hour"), "held", None), (T.SendRejected("400"), "refused", None),
                               (RuntimeError("timeout"), "unknown", 0.8)):
            st = {}
            out = W.dispatch(fs, st, DAY, mock.Mock(side_effect=exc))
            self.assertIn(how, out[0])
            self.assertEqual(st.get("spend", {}).get("said"), said)


class TestPass(Paths):
    """A whole pass: read only, a missing session survived, every finding logged, the status written."""

    def run_with(self, sessions, screens, now=DAY, send=None, capture_fail=()):
        def capture(name):
            if name in capture_fail:
                raise LookupError(f"can't find session: {name}")
            return screens[name]
        st = {}
        with mock.patch.object(W, "list_sessions", return_value=sessions), mock.patch.object(W, "capture", capture):
            status = W.run_pass(st, now=now, paths=self.paths, send=send or mock.Mock(return_value=1),
                                waiting=lambda n: (0, None))
        return st, status

    def test_a_pass_reads_finds_logs_and_writes_its_status(self):
        self.touch(self.paths["wordpass_log"], DAY)
        loop = pane(turn(*[block("Checking", "git status") for _ in range(5)]), spinner=BUSY)
        sessions = {"pipeline_pp_selectid": "claude", "pipeline_pp_wordpass": "python3", "pipeline_gone": "claude",
                    "pipeline_pp_ingest_watch": "sh"}
        send = mock.Mock(return_value=41)
        st, status = self.run_with(sessions, {"pipeline_pp_selectid": loop}, send=send, capture_fail=("pipeline_gone",))
        self.assertEqual([(f["session"], f["kind"]) for f in status["findings"]], [("pipeline_pp_selectid", "LOOP")])
        self.assertEqual(status["errors"], ["pipeline_gone: LookupError: can't find session: pipeline_gone"])
        self.assertEqual(send.call_args[0][0], "pipeline_pp_selectid")
        self.assertEqual(status["telegram"][0]["sent"], 41)
        on_disk = json.load(open(self.paths["status"]))
        self.assertEqual(on_disk["findings"][0]["kind"], "LOOP")
        self.assertTrue(on_disk["sessions"]["pipeline_pp_selectid"]["in_turn"])
        log = open(self.paths["log"]).read()
        self.assertIn("pipeline_pp_selectid LOOP: the same command 5 times in this turn", log)
        self.assertIn("ERROR pipeline_gone: LookupError", log)
        self.assertIn("pass 1: 4 sessions, 1 findings, 1 lines sent", log)

    def test_a_failing_check_and_a_dead_tmux_are_survived(self):
        with mock.patch.object(W, "list_sessions", side_effect=FileNotFoundError("tmux")):
            status = W.run_pass({}, now=DAY, paths=self.paths, send=mock.Mock(), waiting=lambda n: (0, None))
        self.assertEqual(status["errors"][0], "tmux list-panes: FileNotFoundError: tmux")
        self.assertEqual(status["findings"], [])                      # tmux unknown: nobody is called missing
        with mock.patch.object(W, "list_sessions", return_value={}), \
                mock.patch.object(W, "idle_with_work", side_effect=ZeroDivisionError("bug")):
            status = W.run_pass({}, now=DAY, paths=self.paths, send=mock.Mock(), waiting=lambda n: (0, None))
        self.assertEqual(status["errors"], ["idle with work: ZeroDivisionError: bug"])
        self.assertTrue(os.path.exists(self.paths["status"]))

    def test_tmux_runs_only_list_panes_and_capture_pane(self):
        for args in (("send-keys", "-t", "x", "q"), ("kill-session", "-t", "x"), ("kill-server",), ()):
            with mock.patch.object(subprocess, "run") as run, self.assertRaises(PermissionError):
                W.tmux(*args)
            run.assert_not_called()
        calls = []

        def fake_run(argv, **kw):
            calls.append(argv[1])
            out = ("pipeline_a\t1\t1\tclaude\npipeline_b\t1\t1\tpython3\nother\t1\t1\tclaude\n"
                   if argv[1] == "list-panes" else "\n".join(pane(["❯ go"])))
            return subprocess.CompletedProcess(argv, 0, out, "")
        with mock.patch.object(subprocess, "run", fake_run):
            status = W.run_pass({}, now=DAY, paths=self.paths, send=mock.Mock(), waiting=lambda n: (0, None))
        self.assertEqual(sorted(set(calls)), ["capture-pane", "list-panes"])
        self.assertEqual(sorted(status["sessions"]), ["pipeline_a", "pipeline_b"])

    def test_main_once_survives_its_own_error(self):
        with mock.patch.dict(W.PATHS, self.paths), mock.patch.object(W, "run_pass", side_effect=KeyError("boom")):
            self.assertEqual(W.main(["--once", "--dry-run"]), 0)
        self.assertIn("ERROR pass: KeyError", open(self.paths["log"]).read())
        self.assertTrue(os.path.exists(self.paths["state"]))


if __name__ == "__main__":
    unittest.main()
