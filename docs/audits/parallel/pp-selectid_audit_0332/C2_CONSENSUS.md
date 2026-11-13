# pp-selectid audit 0332 (ruling 32: snap outward to whole sentences): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the FIXED diff against the cycle-1 reviews and C1_CONSENSUS.md. Verdicts:
- grok: no P0, no P1, "yes with conditions";
- glm: no P0, no P1, "yes with conditions (test additions, not code changes)";
- qwen: no P0, one "P1" (the lazy import), "yes with conditions".

## Implemented after cycle 2

| # | finding (reviewers) | disposition |
|---|---|---|
| F1 | snap_risk imported vo_fidelity lazily. An ImportError there would escape make()'s (KeyError, TypeError, ValueError) catch (qwen P1-NEW-2, grok condition a) | IMPLEMENTED: `import vo_fidelity as VF` at module level in ledger_build. vo_fidelity imports only json, re and canon, so there is no cycle. A missing module now fails at import, before any row is read. |
| F2 | The 1.0 s marker boundary is untested; the ruling's "within 1.0 s" and the code's strict inequality need pinning (glm N1) | TESTED: a marker at exactly a + 1.0 or b - 1.0 is not inside; at a + 1.01 it is. |
| F3 | snap_risk is unit-tested only in isolation (glm N2) | TESTED through build_inputs: a row that snaps over "Bitcoin will hit 250,000 by 2030" carries "price_prediction" in the moment's risk, which package.lineup_for's per-video cap (L-u) reads. The same sentence unsnapped keeps the miner's own flags. |

## Kept

- **grok condition b (pin the funnel regex to a constant shared with the reason):** KEPT as test infrastructure. The tool's stage-0 grouping strips numbers from any reason, so a reworded reason still groups. Only the per-row list of snapped rows reads the before/after counts. (glm N4 agrees: "test-infra only; acceptable".)
- **glm N3:** a failed caption read is cached per sha, so that transcript's rows are unmeasured at the snap. It fails closed through L-v 2 (C1 K3); the reason is in the report's no_caption_context for window rows.
- **glm N5:** the word record's speaker labels are not read at the snap. The window records from the word-pass worker carry none; the decisive single-speaker measurement is L-v 2's diarisation (C1 K3).
- **qwen P1-NEW-1, P1-NEW-3, P1-NEW-4:**
  - lstrip() covers every Unicode space, so a non-breaking space before ">>" still matches;
  - caption_source catches its read and parse errors (OSError, ValueError, KeyError, TypeError, AttributeError) and returns (None, why); anything else aborts the build, which fails closed;
  - the 72-word test asserts its own > 20 s premise first.

## Verification

- test_ledger_build 34 OK.
- The other suites and regression_test.sh are run before the commit (in the commit message).
