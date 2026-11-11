# Batched audit a1e732e1..497d8224 (Phase 2 + Phase 3 + 4a) — dispositions (2026-11-11 ET)

Panel per the orchestrator note (05:40 ET): heimdall deepseek + qwen27b (per file), cross-LLM GPT-4o /
Gemini / Grok + Claude synthesis. NOTE: this audit's large Grok request pushed the shared xAI gateway over
its $1.00/day ceiling (data/xai_budget_alert.json, 05:49 ET) and the gateway posted an "[xAI BUDGET]" alert
to the Telegram chat: the audit wrapper had popped TELEGRAM_* but a later load_dotenv() restored them. Fixed
in the wrappers (the variables are set EMPTY; dotenv never overrides an existing variable). Grok calls are
blocked by the gateway for the rest of the day; the ceiling was not changed (not this session's to change).

## Cross-LLM (CONDITIONAL READY)
- UF-1 (unanimous) an unreadable frame silently becomes 'uncertain': IMPLEMENTED (printed warning, per-sample
  read_ok, plan unreadable_samples).
- MF-1 "credits D4 only made visible, not prevented": REJECTED, out of this range. D4 was fixed at the source
  in 3641440f (registry-only square avatars, shoutout.validate_avatar raises; no thumbnail, no placeholder;
  must-fail tests in test_pulse_20261110_mustfail.TestD4Credits). The credits card is built natively per
  format (build_shoutout) and never passes through the face reframe.
- UI-1 `_cut_frame` off-by-one: not substantiated (Gemini re-check); no change.

## Heimdall, consensus findings
- render16 / render_vertical StopIteration when a timeline has no 'shoutout': IMPLEMENTED (default).
- render_vertical "M12 fail-closed now applies to every layout": intended (a failed reframe must never put a
  16:9 clip in the 9:16 timeline); Law 22 re-render byte-identical with it in the tree.
- run_fresh "auto-only validation / layout overwrite / write_transitions break Law 22 and the frozen v2f
  path": REJECTED, false premise. The frozen v2f path is run_isolated.py, which never runs these stages
  (no TRANSITIONS.json, hand overrides untouched). Law 22 re-render (runs/v2f_20261111_103004) with all of
  Phase 2 + 3 + 4a in the tree: segment.mp4 472938134157b649.., segment_vertical.mp4 5545a261feedd8c1..
  = the reference, byte for byte. run_fresh runs are DEC-5 'auto' by decision.
- run_fresh "a mixed single+stack2 clip is 'screenshare' at clip level": by design (the per-shot G4 applies
  every shot's face rule); the comment now says so.
- run_fresh "empty shots list": unreachable (classify raises when it samples nothing).
- test_telegram_delivery "fixture has a non-PASS row": REJECTED: it is the '(run_gates)' placeholder that
  gate_status deliberately skips (the real G11 row is present). [low] waiver test now also asserts the
  waived row is named: IMPLEMENTED.
- test_transitions TestConcat needs GPU0: by design (NVENC is the production encoder); [low] failure
  message now shows the checked frames: IMPLEMENTED.
- transition_options [low] style unvalidated / failed copy blocks a retry: IMPLEMENTED (A/B/C only;
  a failed copy is renamed *_failed_<time>).
- verify_pack [high] "last" frame at a dissolve was the end of the overlap: IMPLEMENTED (A's last clean
  frame, b.start - 1/fps); [medium] a frame failure crashed the pack: IMPLEMENTED (incomplete pack);
  [low] complete ignored missing credits rows: IMPLEMENTED.
- word_diff [critical] a talking head missing from the clip map was never checked: IMPLEMENTED (FAIL);
  [high] spelled numbers joined additively ('one two' -> 3): IMPLEMENTED (only well-formed phrases);
  [medium] 'one hundred and twenty': IMPLEMENTED; [low] degenerate span guarded. [low] multi-digit
  spoken decimals and spoken millions: noted (whisper writes both as digits/words consistently; reported
  diff only if it occurs).
- pulse_check_run.sh [critical] "launcher exits 0 before the lock": the detached launcher's 0 means
  "session started" (documented now; the run's exit code is in the log); it now pre-checks the lock (75)
  and checks the tmux launch (1). [high/medium] unquoted relaunch args: IMPLEMENTED (printf %q);
  delivery failure now exits 70; a missing --pinned file is a usage error.
