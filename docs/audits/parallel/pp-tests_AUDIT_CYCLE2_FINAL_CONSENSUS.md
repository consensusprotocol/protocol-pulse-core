# pp-tests_cycle2 — FINAL CONSENSUS (two cycles; written by the session, 2026-11-14 ~08:05 ET)

Diff audited: the fix commit after merge commit f69497b5 (tests/adversarial and docs/audits/parallel/pp-tests_* only).
Brief: pp-tests_AUDIT_CYCLE2_BRIEF.md (one "## THE LAWS" section; utils/cross_llm_audit.py sends only that section).
Why the session writes the consensus: the repo tool's consensus step calls claude-sonnet-4-6 and the Anthropic account
is out of credit (HTTP 400 at 07:34 ET). Rule: a finding is consensus when >= 2 reviewers raise the same file, function
and root cause, or when one reviewer's finding is verified against the code; refutations carry their evidence.

## Cycle 1 (the repo tool's own package): pp-tests_AUDIT_CYCLE2_C1_*.md
- gemini-2.5-pro 100/100, no finding; Heimdall qwen3.8-27b 100/100, no finding; Heimdall glm-5.3-flash 94/100, ready,
  five items. gpt-4o: OpenAI 429 insufficient_quota. Grok: not run (unmetered by this session's ledger).
- Dispositions (pp-tests_AUDIT_CYCLE2_C1_CONSENSUS.md): glm P1 (a qa_gates control) REFUTED, the check is an equality
  and fails if qa_gates drops out; glm P2 (R-10 attribution) root cause ACCEPTED and implemented, exact-key pinning
  refused; glm P2 ("writes nothing") ACCEPTED, whole-run-directory snapshot; glm P3 timeout not acted on; glm P3
  docstring done.

## Cycle 2 (the tool's own build_cycle2_prompt, on the diff AFTER the cycle-1 dispositions)
- gemini-2.5-pro (retried once after HTTP 503 "high demand"): "Production ready: Yes". Agrees with every cycle-1
  disposition (P1 refuted; the attribution and the snapshot "essential"); no new finding.
- Heimdall qwen3.8-27b: "Yes with conditions". Agrees with the cycle-1 consensus and the snapshot. New P1 "replace the
  ffmpeg tone with a pure-Python WAV": REFUTED. word_diff.Transcriber.span() runs ffmpeg on the media itself before it
  reaches the model (word_diff.py:128), so the test cannot avoid ffmpeg; the order says "synthesise audio/video with
  ffmpeg on CPU"; the suite depends on ffmpeg throughout (adv_helpers.make_media, conftest ALLOWED_PROGRAMS, test_f0's
  own ffmpeg control). Its P2 (sys.modules and conftest) is covered by the control it names.
- Heimdall glm-5.3-flash (retried once: its first reply was cut by IncompleteRead; that call is logged as an estimate):
  "Production ready: Yes". Agrees with every cycle-1 disposition, with the verifications written out (the anchored
  LeaseMissing regex, Model.__getattr__ re-entering get(), `_whisper_transcribe -> None` as the documented ordinary
  failure, the unchanged 40-xfail count). Two P2s:
  - N1, a missing ffmpeg should fail as a precondition (pytest.fail), the suite's own convention, not as an error.
    CONSENSUS (qwen raised the same dependency; glm's form verified against the suite's convention): IMPLEMENTED in
    test_f0 (`H.control(shutil.which("ffmpeg") ...)` and a control on the synthesis result). Verified: with ffmpeg off
    PATH the test fails "CONTROL (test setup, not the pinned defect): ffmpeg is on PATH ...".
  - N2, record the R-10 mutation evidence in the repo. ALREADY DONE: REQUESTS R-10 ("Checked with a scratch mutation
    that emulates the fix for the hook: XPASS(strict)"), pp-tests_AUDIT_RESPONSE.md (cycle-2 section) and these
    committed records.

## Outcome
No P0 or P1 stands. Implemented: the R-10 hook attribution, the run-directory snapshot, the `_resolve` docstring
(cycle 1), the ffmpeg precondition (cycle 2). Refuted with evidence: glm's qa_gates control, qwen's pure-Python WAV.
Nothing implemented loosens what a check accepts.
