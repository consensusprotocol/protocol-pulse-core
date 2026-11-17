# Batch 106 (ruling 138 (3) flag sentences; ruling 137 (2): V1's credits row and malformed SOFT evidence HARD): consensus

Heimdall only, one seat per invocation, at medium.

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (checks H1-H6) | FAIL: F1, F2, both REAL, fixed | FAIL: F1, judged NOT a defect |
| 2 (break-it T1-T4) | PASS (0.72) | FAIL: F1, judged NOT a defect |
| 3 (the fix alone, C1-C3) | PASS (0.95), 15.7k characters of reasoning, traced each reader | PASS (1.0), 71.9k characters of reasoning |

## Cycle 1 qwen F1 / F2: REAL, fixed (a397444a)
- **The defect:** attest / authorise raised AttributeError or TypeError on a malformed but digest-valid GATE_REPORT detail:
  - V1[fmt]["boundaries"] or ["letterbox_per_shot"] a truthy non-dict;
  - a model's "rows" a non-dict;
  - G9[fmt] a non-dict.
- **Found while fixing:** seg_name() crashed when the EDL's "clips" was not a list.
- **The fix:** every reader is guarded with isinstance.
- **Must-fail (MUST_FAIL_C1_FIX.log):** on f8719d56, 4 crash subtests and the EDL test fail. The pre-fix code IS the guard-removed mutation.

## Cycle 1 gpt-oss F1: NOT a defect
- **The claim:** "flags() does not filter out hard rows".
- **Why not:** the quoted loop (`for k, v in rows.items()`) is not in the code. flags() iterates `sorted(SOFT.get(fmt, frozenset()) & INVENTORY.get(fmt, frozenset()))`, so it never sees a HARD row.

## Cycle 2 gpt-oss F1: NOT a defect
- **The claim:** "block whenever V1 fails".
- **Why not:** that would make all of V1 HARD. Rulings 136 / 137 make V1's non-credit rows SOFT; V1 refused 3f481f5a, the Blockware case PBX approved, on its watermark row. Only the credits row is speaker credit (HARD), and it holds on a model's "no", a missing answer, or no V1 answer at all.

## Consensus
Two real defects found and fixed, then verified by cycle 3. No open finding.

## Own evidence
- **MUST_FAIL_OLD_CODE.log:** 39 failing results on 45d29746 (the live batch 105), the red-team F3 / F4 cases included.
- **MUTATIONS.log:** 14 of 14 killed (control: 379 passed).
- **The merged tree:** the full suite list by exit code, regression_test.sh and pipeline/regression.sh. Records in the DoD entry.
