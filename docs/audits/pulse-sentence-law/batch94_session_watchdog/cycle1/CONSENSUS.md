# Batch 94 cycle 1: consensus (the session watchdog, orchestrator order 05:55 ET Nov 16)

Diff: STEP.diff (75c4fd53..dad3f9ff, 1174 lines: tools/session_watchdog.py, pipeline/telegram.py send_watchdog, pipeline/test_session_watchdog.py, pipeline/test_alarm.py). Panel: qwen27b, glm (Heimdall only, as the order says), effort none. Cost $0.0038358625 (heimdall/audit.json total_cost).

| Reviewer | Verdict | Confidence | Findings |
|---|---|---|---|
| qwen27b | PASS | 0.95 | none (a bare verdict, 35 tokens) |
| glm | PASS | 0.82 | F1 (medium), F2 (medium), F3 (low); one more raised in cross-examination |

## Consensus (glm F3, low; qwen27b agrees): the status waited on, and could be lost with, the dispatch. FIXED (2c5ab704).

The reviewer's own mechanism is that a BaseException from a send (KeyboardInterrupt) escapes the per-key `except Exception`. That part is not a defect: a Ctrl-C SHOULD stop the watchdog.

The substance holds. run_pass wrote /tmp/session_watchdog_status.json only after `dispatch`. So a slow send (up to 60 s per line) delayed that pass's status, and any exception outside the per-key guard lost it. The order wants the findings written every pass.

The fix:
- The status is written before any line is sent, and again after with the outcomes.
- `dispatch` is guarded: its failure is recorded as "telegram: <error>" in the status.
- The status and state writes catch any Exception.

Test: `test_the_status_is_on_disk_before_a_line_is_sent_and_a_failing_dispatch_is_survived`. The send stub reads the status file and finds the findings already there; a failing dispatch leaves a complete status. It fails on dad3f9ff. Mutations W20 (the status written only after the dispatch) and W22 (a failing dispatch ends the pass) are both killed.

## Raised in cross-examination (glm, low), not voted: a pane with no input box was read from its last lines. FIXED (2c5ab704).

With no input box found, parse_pane took the last 6 lines as the footer, so a pane whose last lines quote 'esc to interrupt' would read as in a turn.

Now a pane with no input box is not judged: no turn, no timer and no CONTEXT, because its state is unknown. The status (`input_box: false`) and the pass line name it, so a Claude Code UI change cannot blind the watchdog silently.

Test: `test_no_input_box_is_not_judged`. It fails on dad3f9ff, and mutation W21 is killed.

## Not agreed, no change

- **glm F1 (medium):** "a stuck command that keeps printing never reads as stuck; a command whose block is followed by a spinner-only redraw is never reported." The spinner is never a block: parse_pane ends the content above it. So a running command's block stays the latest one, and the command rule (block header + first line, 45 min) catches it. `test_the_same_shell_command_still_the_latest_action_for_45_minutes` shows a command whose output grows every pass reported at 45 min. The reviewer's text corrects itself midway. Only glm voted for it.
- **glm F2 (medium):** its own conclusion is that a SPEND line Telegram explicitly REFUSES (SendRejected) is retried every pass. That is the sender's rule, the same as send_alarm's: a definite non-send is not recorded and may be retried. Held lines (the hour, the night) are not marked said, by design, so the level is said once it can be. No line is ever sent twice. Only glm voted for it.

Grok was not asked: the order says Heimdall only.
