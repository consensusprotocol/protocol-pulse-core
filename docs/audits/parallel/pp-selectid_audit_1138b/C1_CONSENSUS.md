# pp-selectid audit 1138b (audit 1138's cycle-2 consensus P1, the increment): cycle 1 consensus

- **Run:**
  - grok: no finding, "SHIP: yes".
  - qwen: its P1 (sc.get on a non-dict) is retracted in its own text, because the isinstance guard covers it; "SHIP:
    yes with conditions".
  - glm: "SHIP: yes", one P1 (a missing test).
- No P0 or P1 holds against the code.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-1 / qwen (its condition): no test exercises a "scorer" that is not an object, the case the isinstance guard exists for | One more case in test_the_verdicts_file_is_used_only_when_every_check_holds: {"scorer": ["moments"], "verdicts": {}}. It yields {} and read False, the why starts "shape: AttributeError", and no scorer field is recorded. No exception escapes. |

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P2-1: the "stage: " prefix spends a few of the 160 message characters | Cosmetic. The exception type and the stage are what a reader needs. |
| G2 | glm P2-2: a recorded threshold can be a non-numeric value | The same as the "why"-chain path. It is a record, never a gate (the gate refuses it). |
| G3 | glm P2-3: the non-ASCII test checks the pin through affirmed_verdict, not separately | affirmed_verdict computes the pin's own sha256 inline (package_pin.py), and the test checks both against the same hashlib call. |
| G4 | glm P2-4: a statement inserted later between `try:` and `stage = "parse"` could be mislabelled | Informational; no such statement exists. |

## Verification

- test_medley 113 OK on the scratch copy (dev19). The increment is diffed against the cycle-2-audited state of audit
  1138 (a scratch commit), so this review sees only these lines.
