# heimdall_qwen (qwen/qwen3.8-27b, 176.2 s, $0.008, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-ingest (Ruling 92)
# Reviewer: heimdall_qwen (qwen/qwen3.8-27b)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the `>>` marker edge case as a P1 verification point but failed to definitively resolve it because I did not have access to the `canon` module's implementation details. I also missed the specific nuance regarding the `--rerun` command's interaction with the live service loop (TOCTOU), which `muse` identified as a low-severity race condition.

Most importantly, I missed the **consensus refutation** provided by the orchestrator's measurement. The orchestrator explicitly stated that `canon.canon_tokens(heads=True)` *does* drop the `>>` marker. My Cycle 1 output speculated that it *might* be safe if `canon` was robust, but I did not confirm it. The other models (GLM and Muse) also flagged this as "unverifiable from the diff," but the orchestrator's Cycle 1 consensus section provides the ground truth: **it is verified safe.**

I also missed the specific implementation detail that `dropped_s` (duration analysis) is now correctly separated from opener drops, which `muse` highlighted as intentional and correct.

## 2. WHERE DO YOU AGREE OR DISAGREE?

### GLM (z-ai/glm-5.3-flash)
*   **Agree:** GLM correctly identified that the `>>` marker issue is "probably correct, unverifiable from the provided code." This was the right stance for a code-only review.
*   **Agree:** GLM's analysis of the `--rerun` idempotency guard (`hook_note IS NULL OR hook_note <> 're-run: ...'`) is accurate.
*   **Disagree (Minor):** GLM suggested adding `episode` to `carry_forward`. I agree with the orchestrator's "BY DESIGN" ruling: `build_line` always sets `episode` fresh, so `carry_forward` (which merges flags from *earlier* lines) does not need to copy `episode` because the new line already has the correct, current measure for that video. Copying it would be redundant, not harmful, but unnecessary.

### MUSE (meta-models/muse-spark-open-816b-a42b)
*   **Agree:** Muse correctly identified the TOCTOU race in `--rerun` (CLI resets `hook_ts` while service is mining). I missed this in Cycle 1.
*   **Agree:** Muse correctly noted that `episode_measure` returning `minutes: 0.0` for missing timing is "misleading" but handled via `turns_per_min: None`. The orchestrator's fix (`measured_from: "no segments"`, `minutes: None`) addresses this.
*   **Disagree:** Muse suggested that `bad_opener` returning `"empty"` is a bug. It is not. An empty text hook is invalid and should be dropped. The reason string `"empty"` is distinct and useful for reporting.

### QWEN (Myself, Cycle 1)
*   **Self-Correction:** I was overly cautious on the `>>` marker. The orchestrator's measurement proves `canon` handles it. I should have trusted the "strictness of the rest of the code" more, but the lack of `canon` source in the diff made it a valid P1 verification point at the time.
*   **Self-Correction:** I missed the `--rerun` race condition entirely.

## 3. NEW FINDINGS FROM THIS REVIEW

**Finding N1: The `--rerun` TOCTOU is mitigated by design, not just luck.**
While `muse` flagged the race, the orchestrator's "IMPLEMENTED" section notes: *"the help says... it is run while no hook pass is in flight."* The CLI help text now explicitly warns the user to run `--rerun` when the service is idle. This is a **P2** operational risk, not a code bug, because the service is single-process and the CLI is a manual tool. The code does not lock against the service, but the documentation mitigates the risk.

**Finding N2: `episode` field is additive and safe for the ledger.**
The `ledger.line_problems` function checks `REQUIRED` keys. `episode` is not in `REQUIRED`. Therefore, adding it to new lines does not break validation of old lines. `carry_forward` does not copy it, but `build_line` always generates it. This is safe.

**Finding N3: The `bad_opener` filter is a "second net."**
The prompt instructs the model to avoid bad openers. The `bad_opener` function is a deterministic post-filter. If the model fails the prompt instruction, the filter catches it. This is a robust defense-in-depth pattern. The filter uses `canon.canon_tokens`, which is the same tokenizer the builder uses. This ensures consistency.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Correctness** | 8/10 | 9/10 | The `>>` marker P1 is resolved by measurement. The `--rerun` race is documented as an operational constraint. |
| **Law Compliance** | 9/10 | 9/10 | No changes. L-x, L-l, L-m are respected. |
| **Robustness** | 8/10 | 9/10 | The `episode` measure is fail-soft (returns `None` for missing data) and does not crash the pipeline. |
| **Maintainability** | 9/10 | 9/10 | The code is verbose but clear. The separation of `dropped_s` and opener drops is well-documented. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None. (The `>>` marker issue is refuted by measurement).

**P2 MEDIUM:**
1.  **`tools/ingest_watch.py` line 157:** The `--rerun` command does not check if the service is currently running a hook pass. The help text warns the user, but a programmatic check (e.g., reading a lock file or querying the service's state) would be safer. *Mitigation:* The service is single-process, and the CLI is manual. The risk is low.
2.  **`pipeline/ingest/mine.py` line 248:** `episode_measure` uses `segs[-1].get("end")`. If the last segment has no `end` time, `mins` becomes 0.0. The orchestrator's fix (`measured_from: "no segments"`) addresses the empty case, but the partial timing case still results in `minutes: 0.0`. This is acceptable as `turns_per_min` is `None`, but `minutes` should ideally be `None` if timing is incomplete. *Mitigation:* The field is informational.

**P3 LOW:**
1.  **`pipeline/ingest/ledger.py` line 187:** `carry_forward` does not copy `episode`. This is by design, but a comment explaining why would prevent future confusion.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the `episode` measure to every ledger line is the highest-leverage change. It allows the builder to filter for "conversation" vs. "solo" content without re-parsing captions, directly implementing Ruling 92's requirement to favor conversations. This data is now available for ranking and selection, enabling the "spotlight" logic to be applied downstream.

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `canon` module must be verified to strip `>>` markers (confirmed by orchestrator measurement).
2.  The `--rerun` command must be used only when the service is idle (documented in help text).
3.  The `episode` field must be ignored by any legacy ledger readers that do not expect it (confirmed: `line_problems` does not require it).

The code is defensive, fail-closed, and compliant with the Laws. The Ruling 92 changes are correctly implemented and tested.