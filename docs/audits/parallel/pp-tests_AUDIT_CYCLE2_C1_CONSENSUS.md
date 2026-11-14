# pp-tests_cycle2 — CYCLE 1 CONSENSUS (written by the session; 2026-11-14 ~07:50 ET)

Why the session writes it: the repo tool's consensus step calls claude-sonnet-4-6, and the Anthropic account is out
of credit (HTTP 400 "credit balance is too low", request req_011Ch2pyLbZdNNB8qJSps4gb, 07:34 ET). The rule used is the
one pp-ingest's audit driver states: a finding is consensus when >= 2 reviewers raise the same file, function and root
cause, or when one reviewer's finding is verified against the code; a refuted finding is recorded with its evidence.

Reviewers of cycle 1 (the same AUDIT_PACKAGE.md, 68,770 chars, built by the repo tool from the brief and the diff):
- gemini-2.5-pro (the repo tool's own leg): 100/100, no finding, "ready for production merge".
- Heimdall qwen/qwen3.8-27b (reasoning effort none): 100/100, no finding, "READY FOR MERGE".
- Heimdall z-ai/glm-5.3-flash (reasoning effort none): 94/100, "Ready to merge", five items (below).
- gpt-4o: not reviewed (OpenAI HTTP 429 insufficient_quota). Grok: not run (the driver cannot meter xAI under the
  session's $3 audit cap).

## Items and dispositions

1. glm P1 — "add a control that the resolved qa_gates is the expected file: a same-named stranger would make the
   setter check pass vacuously" (test_f0_cpu_guard.py, the setter scan). REFUTED. The check is an EQUALITY,
   `setters == KNOWN_CUDA_SETTERS == {"qa_gates"}`: if `qa_gates` resolved to a file outside pipeline/ or segment_v1/,
   it would drop out of `found`, `setters` would be empty, and the test would FAIL, not pass. Measured: `_resolve
   ("qa_gates")` = segment_v1/qa_gates.py (there is no pipeline/qa_gates.py); `set() == KNOWN_CUDA_SETTERS` is False.
2. glm P2 — "R-10's control `startswith('whisper:')` is loose: another Whisper load could satisfy it". ROOT CAUSE
   ACCEPTED, KEY-PINNING REFUSED. The real gap was attribution: nothing tied the stop to the HOOK's transcription
   (session self-review S1 found the same before reading glm). Implemented: select's seam `_whisper_transcribe` is
   wrapped (the real function still runs; its cache check is R-10's subject) to record which source it was
   transcribing; the stop counts only when it came from the hook's call (`asked[-1:] == [HOOK_VID]`), else a control
   failure. Verified: normal run XFAIL; `--runxfail` fails on "the old transcript was used for new bytes"; a scratch
   mutation emulating R-10's fix for the hook (its stale transcript not reused) PASSES under --runxfail and shows
   XPASS(strict) in a normal run. Not done: pinning the exact key `whisper:large-v3`. A correct fix may transcribe
   with another Whisper variant; the pin's subject is that the hook's new bytes reach Whisper, not which model.
3. glm P2 — "the new test's name says 'writes nothing' but it proves only no EDL and no transcript". ACCEPTED
   (verified: the assertions were narrower than the name). Now the whole run directory is snapshotted before select
   (every file's size and mtime_ns, every directory) and must be identical after the GPU stop. Verified on the code:
   a cache hit writes nothing (select_passages._download_window returns before any write), so the snapshot holds
   today (test passes); a scratch mutation that writes one record before the stop FAILS it
   ("select changed the run directory before its GPU stop", naming the file).
4. glm P3 — ffmpeg timeout 60 s in the test vs 120 s in word_diff. NOT ACTED ON: the test's own tone is 1 s of lavfi
   sine; its timeout bounds the test's own helper call, not production's.
5. glm P3 — note in `_resolve` that a package resolves to its __init__.py. ACCEPTED (docstring; behaviour unchanged:
   such a file under pipeline/ or segment_v1/ is scanned, which is stricter, not looser).

No P0. No item loosens what a check accepts. Cycle 2 reviews the UPDATED diff (CURRENT.diff regenerated after items
2, 3 and 5) with these dispositions.
