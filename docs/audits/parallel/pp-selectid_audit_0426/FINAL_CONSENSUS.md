# pp-selectid audit 0426 (ruling 34's pin side): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the FIXED diff against the cycle-1 reviews and C1_CONSENSUS.md. All three reviewers:
P0 none, P1 none.
- grok: "SHIP: yes";
- qwen: "Yes" (it withdrew its cycle-1 P0s against the consensus evidence);
- glm: "SHIP: yes". The coupling of the judged and sealed screen is now checked at to_pin and proven by the 7- vs
  6-argument digest test.

## Implemented after cycle 2

| # | finding | disposition |
|---|---|---|
| F1 | When a moment fails BOTH the opener rule and the topic rule, only the first reason was recorded (glm P2-2, condition 1, observability) | IMPLEMENTED: out["no_role"] joins both reasons. Tested with "But gold is the oldest money." |

## Recorded (no code change)

- **glm P2-1 (condition 2):** the medley's "names Bitcoin" test is the render's own `\b(bitcoin|btc)\b` (stand_alone.BITCOIN). That is singular and stricter than the retired T11 `\b(bitcoins?|btcs?)\b`, so "bitcoins" alone does not satisfy the medley rule. It is sanctioned by the ruling's wording ("bitcoin / btc"), and the pin stage and the render run the same code, so they agree.
- **glm condition 3:** this deploys together with the integrator's 7-argument check_pin_only. They updated it at 04:20 ET and re-ran it READY on the three frozen pins (their message). A stale 6-argument call would fail every new pin loudly.
- **glm P1-1 (C2):** a gate inventory without a stand_alone row has no judged screen, and screen_problems refuses it (fail closed). It is also refused by MEDLEY_GATES.

## Verification

- All 11 offline suites OK (test_medley 57, test_eligibility 30); regression_test.sh 26 PASS | 0 FAIL | 5 WARN; py_compile.
