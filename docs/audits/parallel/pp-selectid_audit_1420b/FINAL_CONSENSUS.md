# pp-selectid audit 1420b (the increment: audit 1420's cycle-2 consensus): FINAL consensus (cycle 2)

- **Cycle 2:**
  - grok: "Yes with conditions": a test for the build-raise path, and the registry flag.
  - qwen: "Yes with conditions": P1, the registry flag.
  - glm: "Yes, with one condition: relocate (or truth-ify) the res["registry"] = True flag".
- No P0. The registry flag (glm C1 P1-1) is now consensus: all three. It is applied.

## Applied

| # | finding | the change |
|---|---|---|
| C1 | The record claimed "registry": true even when the guarded registry save then failed (glm P1-1; grok and qwen agree in cycle 2) | tests/package/proof_ledger.py: the guarded registry update (the --from-candidate outcome, CA.seed of this record, the atomic save) now runs BEFORE package.json is written. "registry": true is set only after os.replace succeeds. On a failure: "registry": false and "registry_error", logged, and package.json is still written. A later run's CA.seed then applies the record's own outcome; that is its legacy branch, for a record not flagged as registered. The seed of this record is made with registry=True, so a saved registry never applies the --from-candidate outcome twice. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | grok: a test for the candidate build raising (the minimal record) | The path is two statements: try_one returns "budget" with every line-up left charged, and the minimal dict when no try left an out. Single-model. |
| G2 | qwen P1-NEW-1: --from-candidate's candidate_tries is not clamped | That path tries ONE candidate, with no shared budget. Its judged count is the build's own search count, recorded as reported (informational). |

## Verification

- All 13 suites OK on dev24 (test_ledger_build 35, with the refusal test; test_candidates 9). They are re-run in the
  worktree with regression_test.sh before commit.
