# pp-selectid audit of G17a at the pin stage (+ the two live-build fixes): cycle 2 dispositions (synthesis by the pp-selectid session, 02:04 ET Nov 13)

**Run.** Cycle 2 cross-reviews the fixed diff. Its scope was widened to ledger_build.py, proof_ledger.py and
test_ledger_build.py for the two defects the first FRESH build found. No P0. The only P1s are glm's, and glm marks
both of them answerable.
- grok-4.20-0309-reasoning (xAI): two P2s.
- qwen/qwen3.8-27b (Heimdall, effort none): it confirms every cycle-1 disposition; two P2s.
- z-ai/glm-5.3-flash (Heimdall, effort none): P1-1 (pin the margin), P1-2 (confirm the disk cache); four P2s.

All reviewers: SHIP yes with conditions.

## Consensus: implemented

| finding (reviewers) | disposition |
|---|---|
| the hook-onset measurements ran in a thread pool sharing one cache; is transcript_truth.audio_window thread-safe? (grok P2-1, qwen P2-1, glm N1) | IMPLEMENTED: the measurements run in turn. Each is a CPU decode of a second-pass window already on disk (seconds for a build), so the thread pool bought nothing and the question goes away |

## Unique findings: implemented or answered (each verified)

- **glm P1-1 (pin the margin):** IMPLEMENTED. test_hook_onset asserts MARGIN_MS == 10 and HEAD_LEAD_MIN_S == 0.080, so
  the 90 ms defense cannot drift silently.
- **glm P1-2 / grok P2-1 (does the cache freeze a transient failure?):** ANSWERED.
  - transcript_truth.audio_window returns the window's WAV from disk when it exists (`if os.path.exists(wav): return
    wav, a`).
  - Every moment measured here has already passed the second pass, which wrote that window.
  - So the read is deterministic, and a failure is recorded, never a pass.
- **glm N3 (same-words copies in both stores: main's wins):** ANSWERED. Source takes the record's tokens,
  transcript_method and duration. The channel and identity come from the ledger row. One video has one duration, so
  the tie-break cannot change the context.
- **grok P2-2 (float edges in the word filter):** KEPT. The second-pass window is [start - 1.5 s, end + 1.5 s], so the
  clip's first and last words lie well inside it. All three of pin #1's real clips measured; a miss is "not measured",
  never a pass.
- **qwen P2-2 (log a missing hook_onset row):** KEPT. It cannot happen: the hook is segments[0], drawn from a line-up
  of `cleared` moments, which all carry hook_onset.

## The live FRESH build on this code (02:01 ET, ledger_20261113_070124; 10 h window, the worker's fresh cycle)

- All 6 window records found their caption record (the ledger-store fix).
- 74 adapter rows gave 11 moments, because 63 rows did not re-anchor. With ONE window per video, only the rows inside
  the best-ranked row's window anchor, while the worker writes a window for every moment.
- Then: 5 usable, 3 cleared step A, 1 passed L-v 2 + CUTTABLE, 0 can open a medley (G17a). No package.
- The next change is one window per MOMENT: a per-moment source key in the packager.

## Verification

- 11 offline suites, 233 tests OK. regression_test.sh: 26 PASS | 0 FAIL | 5 WARN.
