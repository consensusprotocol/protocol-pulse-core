# THE CALIBRATION REUSE AT A RESTART, cycle 2: consensus

Reviewers (Heimdall): glm-5.3-flash (245 s, $0.005): "Yes" (P0 / P1 none; conditions P2/P3); muse-spark-open (285 s,
$0.029): "Yes" (P0 / P1 none); qwen3.8-27b (320 s, $0.009): "Yes" (P0 / P1 none); minimax-m3.1-flash (361 s,
$0.010): "Yes, with conditions" (P0 / P1 none). Cycle 2: $0.054 (both cycles $0.104). Diff reviewed: the working
tree at the cycle 1 commit against c4f733db.

## Agreed by all four (verified)
- Every gate fails closed to a live calibration; the once-guard, the outage retry and the daily schedule are
  untouched; the cycle 1 fixes (the refusal reason; the fake-clock test pinning "a day after the LIVE one") hold.

## Conditions taken (each with a test that fails without it: mutation-checked)
- C2-1 (minimax, its condition 1): the stored record now says WHAT was measured: prompts_sha =
  flagcheck.calibration_sha(), a sha256 of every calibration prompt (definitions, questions, quotes) with its expected
  answer; the reuse gate requires it equal to today's, and a record without it is REFUSED (never trusted: the record
  the live watcher wrote at 08:5x ET carries none, so the next start asks live once). minimax's `"live": true` is
  already carried by asked_at: only a live calibration writes it (F1); a record without one is refused. Tests: a
  changed hash and a missing hash are each refused with the reason "measured on other prompts, or before they were
  recorded"; calibration_sha moves with a quote, an expected answer or the wording, and only then.
- C2-2 (glm P2-1): _reuse_calibration's docstring records the coupling: only a PASSED calibration is reused, which
  is why the wait is reset to the daily one; relaxing the "one passed" gate would skip an outage calibration's
  shorter retry.

## Recorded
- minimax's operational note: the reuse removes the start's 32 calls only when the previous calibration passed; an
  outage calibration is asked again live at the next start, by F1's design. Design 16 says so.
- glm P3: the refusal reason could carry the counts (a quote-set change vs nobody passed): the prompts gate now
  separates the first; not taken further.
- qwen P2: watch.py's Shorts by URL and the cache's reuse for frozen back-ends: outside this change, as in cycle 1.

Suite: tests/ingest 332 passed (with the builder's amended module 3cf4c42f at its path; the signal tests adapted in their own commit). Verdict: four of four "Yes"; live at the next watcher restart (A36, A19 and this
together).
