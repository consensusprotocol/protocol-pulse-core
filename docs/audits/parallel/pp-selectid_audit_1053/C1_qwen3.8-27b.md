# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 29113 / out 1398 usd~0.108 (upper-bound price)

# Audit: pp-selectid-1053 (Ruling 56 — Pin-Stage Clip Scorer)

## P0 Findings

**None.**

The fail-closed admission path is sound. I verified the following critical invariants:

1.  **Fail-Closed on Missing/Invalid Data:** `scorer_verdicts` returns `({}, {"read": False, ...})` for missing files, malformed JSON, wrong event, wrong `scorer_sha`, or wrong threshold. `verdict_of` returns `None` if the `text_sha256` does not match the moment's current text. `no_role_on_screen` fails closed (returns a reason string) if no verdict is attached or if the verdict does not affirm. `trim_refused` blocks the variant before any vendor call if no affirmation exists.
2.  **SHA Matching Integrity:** `with_verdict` and `verdict_of` strictly compare `text_sha256` against the SHA-256 of the moment's *current* text. A trimmed variant (which has different text) will never inherit the verdict of its untrimmed parent because the hashes will differ. `affirmed_verdict` in `package_pin.py` re-computes the hash of `approved_text` (or `text`) and compares it to the sealed `scorer_verdict.text_sha256`.
3.  **Hook vs. Clip Role:** `no_role_on_screen` calls `SA.opener("clip", ...)` with the verdict score/fault, but `SA.opener("hook", ...)` without it. The render's hook rule (which rejects conjunctions/reply fragments) is never bypassed by the scorer. `placement()` explicitly marks such moments as "cannot open (never the hook)".
4.  **Pin Backward Compatibility:** `scorer_pending` remains in `SEALED_LATER` in `package_pin.py`, ensuring old pins recompute correctly. `scorer_verdict` is added to `SEALED_LATER`, so it only enters the seal hash when present. `trim_problems` now *refuses* `scorer_pending` on any segment, enforcing the retirement of Ruling 49(a).
5.  **Atomic Write:** `write_candidates` uses `.tmp` + `os.replace`, ensuring no partial reads. It only writes if the set of `(pid, text_sha256)` pairs changes, preventing unnecessary churn.

## P1 Findings

**None.**

## P2 Findings

**P2-1: `scorer_problems` in `package_pin.py` may be redundant with `trim_problems` for trimmed clips, but logic is correct.**
*   **Location:** `pipeline/package_pin.py:384-400` (`scorer_problems`) and `pipeline/package_pin.py:403-434` (`trim_problems`).
*   **Observation:** `scorer_problems` checks if a clip opens on a conjunction/reply fragment and requires an affirmation. `trim_problems` checks if a clip is trimmed and requires an affirmation. A trimmed clip that opens on a conjunction will be checked by *both*. This is not a bug (fail-closed redundancy is acceptable), but it means a single defect (missing verdict) produces two error messages in `to_pin`. This is cosmetic and does not affect correctness.

**P2-2: `RENDER_SCORER_CODE` hardcodes absolute paths.**
*   **Location:** `pipeline/package.py:21-23`.
*   **Observation:** `RENDER_SCORER_CODE` is a tuple of absolute paths (`/home/ultron/protocol_pulse/pipeline/...`). If the code is ever run in a different environment (e.g., CI, a different user, or a containerized build) where these paths do not exist, `render_scorer_sha` will return `None`, causing `scorer_verdicts` to fail closed ("the render's scorer code could not be read"). This is the correct fail-closed behavior, but it means the feature is tightly coupled to the Ultron server's filesystem layout. If the project ever moves to a more portable deployment, this will need to be parameterized. For the current scope (Ultron server), this is acceptable.

**P2-3: `SCORER_MIN` in `package_pin.py` is a separate constant from `stand_alone.CLIP_MIN_SCORE`.**
*   **Location:** `pipeline/package_pin.py:362`.
*   **Observation:** `SCORER_MIN = 3.5` is defined in `package_pin.py`, and a test (`test_the_pin_holds_the_affirmation_to_its_text`) asserts it equals `SA.CLIP_MIN_SCORE`. This is a good practice to prevent drift, but it means the pin stage has its own copy of the threshold. If `stand_alone.CLIP_MIN_SCORE` is ever changed, the test will catch it, but the pin stage will still use the old value until the test is run and the constant is updated. This is a minor maintenance risk, but the test mitigates it.

## Verification of Stated Readings

*   **K1:** Correct. The diff retires `TRIM_SCORER_PENDING` and refuses `scorer_pending` in `trim_problems`. A trimmed variant without an affirmation is blocked by `trim_refused` before any vendor call.
*   **K2:** Correct. `no_role_on_screen` only uses the verdict for the clip role. The hook role is never rescued.
*   **K3:** Correct. `scorer_pass` only submits candidates for moments that fail `no_role_on_screen` but pass `no_topic`. Moments that fail the topic rule are not submitted.
*   **K4:** Correct. `TRIMMED_PER_LINEUP_MAX` remains 1. The pin-stage verdict is not an "affirmation at validate" in the sense of Ruling 49(b), so the limit is not lifted.
*   **K5:** Correct. `render_scorer_sha` recomputes the SHA-256 of the render's code at build time. If the code changes, the SHA changes, and old verdicts are rejected.

## SHIP: Yes

The diff is well-structured, fail-closed, and correctly implements Ruling 56. The critical invariants (SHA matching, hook/clip role separation, backward compatibility, atomic writes) are all verified. The P2 findings are minor and do not block shipping.