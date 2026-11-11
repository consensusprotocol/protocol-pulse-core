# Batch 3 (render fix, contact sheet + visual checklist, batch-2 consensus) — dispositions

Audited diff: STEP.diff (staged, pipeline/ only, 747 lines). Cross-LLM: GPT-4o + Gemini (Grok blocked by
the xAI $1/day ceiling; its alert went nowhere because the wrapper blanks TELEGRAM_*). Heimdall:
deepseek + qwen27b, one chunk per file (12 chunks).

## Implemented (each with a test that fails on the audited code)
- Heimdall editorial_review [high]: `isinstance(index, int)` accepted JSON `true` as CLIP 1 (bool is an int
  subclass) -> `type(index) is int`. Test: test_window_review TestReviewValidatorContract boolean index.
- Heimdall run_fresh [medium]: when both fades failed and the accepted cut_in trial cleared BOTH errors, the
  cut_out loop accepted its first candidate vacuously (moved an edge that was no longer failing) -> a side
  whose error is gone is skipped. Test: test_prepare_retry ...cleared_by_the_other_edges_fix_does_not_move.
- Heimdall verify_pack [medium]: a copied run (transition options) carries the previous render's
  qa/contact_sheet_*.jpg; when the new sheet failed, the panel still read the stale one and could PASS ->
  the old sheet is removed before building, and no sheet = V1 FAIL with no vision call. The `nos` traversal
  is guarded. Test: test_visual_check TestSheetWiring.
- Heimdall visual_check [high]: a network/HTTP error in ask_vision propagated (verify_pack turned it into a
  FAIL, so no false pass, but one transient error held a good run) -> each attempt catches and retries;
  after the attempts every line is missing = HOLD. Test: test_route_errors_are_retried_then_no_answer.
- Heimdall visual_check [high]: a flat answer (`"watermark_present": "yes"`) crashed verdict -> a malformed
  line is a missing line (HOLD). Test: test_a_malformed_line_is_missing_not_a_crash.
- Heimdall visual_check [medium]: _key() raised StopIteration/FileNotFoundError and leaked the handle ->
  `with` block and a clear RuntimeError.
- Heimdall test_visual_check [medium/low]: the .env handle in skipUnless leaked -> `_has_vision_key()` with a
  `with` block. "Skip when the fixture is missing" is REJECTED: a must-fail test that skips when its evidence
  disappears hides an untested check; it now FAILS with an explicit message instead.
- Cross-LLM UI1: `_parse` used a greedy `\{.*\}` (JSON followed by text with braces broke it). The proposed
  non-greedy regex would break the nested answers object, so: scan with json.JSONDecoder.raw_decode from
  every `{` and take the first object that carries "answers". Test: trailing-braces case.
- Cross-LLM M1: `_photo_ok` boundary tests (size, w+h, ratio); the unreadable-image case (Heimdall telegram,
  raised by one model) now returns False (sent as a document) instead of crashing after the videos were sent.

## Rejected, with evidence
- Cross-LLM U1 "9.5 MB photo threshold is a bug": deliberate margin under Telegram's 10 MB sendPhoto limit;
  above it the sheet goes as a document and still arrives full size. Now a named constant with the reason.
- Cross-LLM P3-B/P3-C (partial answers, route timeouts must FAIL): already the behaviour
  (test_a_missing_answer_holds; verify_pack catches every panel exception into a FAIL row) and now tested.
- Heimdall verify_pack (one vote each): "pack complete ignores V1" (V1 is a GATE_REPORT row, and
  telegram.gate_status turns any failing row into REVIEW ONLY); "ok=True with a failing row" (ask_panel's ok
  is all(verdict ok), and verdict ok is all rows ok); "contact_sheet may return a str" (it returns a dict).
- Heimdall pulse_transitions (one vote each): negative xfade offset needs a talking head shorter than the
  6-frame dissolve (clips are seconds long and plan() bounds the dissolve by measured lead/tail); duplicate
  identical segments cannot occur (labels are unique); render_wipe's temp dir is not removed (disk only,
  options path; noted, not changed in this batch).
- Heimdall run_fresh (one vote): write_report on a non-dict row: verdict() always builds dict rows.
