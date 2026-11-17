# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 87.8 s, $0.002, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT — r121 (pp-ingest DIFF ONLY)

**Branch:** `pp-ingest` @ `5c9ce2b6` | **Files:** `pipeline/ingest/fetch.py`, `tests/ingest/test_r121.py` | **Ruling:** 107(2) — DIFF only

---

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

Honestly: very little was missed in Cycle 1 — both reviewers converged on the same verdict. What the other models articulated more clearly than I did:

*   **Qwen's explicit benign-race analysis:** I noted "no new race" but Qwen spelled out the idempotent double-increment case (`tries=0` read twice → both write `tries=1`, `next_at=now+3600`). I should have stated that explicitly. It's not a defect, but it's the right level of diligence for a queue audit.
*   **Qwen's SPEND FREEZE framing as cost-saving:** I marked SPEND FREEZE COMPLIANT; Qwen correctly added that capping at 6 tries *reduces* yt-dlp calls vs. infinite `PROBE_RETRY`. I under-sold the positive.
*   **Muse's `duration <=0` cross-reference:** I flagged `any(j.get(k))` treating `duration=0` as stub as "not a blocker." Muse correctly closed the loop: `fetch.process` already rejects `duration <=0` as "no duration measured" → same terminal outcome (no mining) either way. My note was accurate but incomplete without that citation.

Neither reviewer found a P0/P1 I missed. The consensus summary is correct: nothing to fix.

### 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Agree? | Why |
|---------|--------|-----|
| **Stub detection `not any(j.get(k) for k in FACT_KEYS)` is correct** — both reviewers | **Agree** | 5 orthogonal keys (live_status, duration, timestamp, release_timestamp, upload_date) — a real VOD has 3, a real upcoming has 2. All-None only occurs on yt-dlp stub. Truthiness vs `is not None` is immaterial here (see below). |
| **State transition: hourly retry, 6-try cap, `10**9` sentinel → UNAVAILABLE** — both | **Agree** | Matches spec verbatim. `NO_METADATA_RETRY_S=3600` equals old `PROBE_RETRY_S` ceiling. `final = tries+1 >=6` is correct off-by-one handling. |
| **Stall exclusion by construction (UNAVAILABLE ∉ stall.WAITING)** — both | **Agree** | Verified by `test_a_stub_is_never_counted_as_waiting` asserting `waiting==[] and stalled is False`. No code change to `stall.py` needed. |
| **Non-stub passthrough preserves old path** — both | **Agree** | `test_r121.py:38-44` covers `is_upcoming` + `release_timestamp` → UPCOMING and VOD + `upload_date` → PROBE_RETRY. |
| **Muse: `duration=0` edge is not a defect** | **Agree — and stronger** | I called it "not a blocker"; Muse proves it's *not even a divergent outcome*. `process()` already gates `duration <=0`. Whether classified as stub or not, video never reaches mining. No fix needed. |
| **Qwen: log line on give-up is recorded via queue state event** | **Agree** | `reason="no metadata: {detail}"` + `next_at=now+10**9` is the audit trail. No separate log line required. |
| **Qwen: race is benign/idempotent** | **Agree** | Single `q.set_state` UPDATE; double-schedule just re-queues same hour. No corruption. |
| **Qwen: SPEND FREEZE compliant and cost-saving** | **Agree** | See §1. |

**Disagreements: none.** Both Cycle 1 reviews are sound.

### 3. NEW FINDINGS FROM THIS REVIEW

Combined analysis reveals no new defects. Two observations worth recording for completeness (neither is a defect, neither requires a change):

1.  **FACT_KEYS fragility is bounded, not open-ended.** I noted in Cycle 1 that a future yt-dlp field removal could cause false negatives. Re-reading with both reviews: the 5 keys span 3 independent YouTube subsystems (live, VOD duration, timestamps). YouTube would need to simultaneously null all 5 for a real video to be misclassified. The alternative (title prefix `"youtube video #"`) is strictly more brittle (localization, A/B). Current choice is optimal. **No change.**

2.  **Test coverage is minimal but sufficient for diff scope.** 3 tests cover the 3 invariants; 434 ingest tests pass; M44-M47 killed. A 4th test for the `final` boundary (`tries=5 → 10**9`) would be nice-to-have but is already covered by `test_a_stub_is_never_counted_as_waiting` looping to 6. **No change required.**

No security, secrets, or law-compliance issues surfaced in cross-review.

### 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness** | 10/10 | **10/10** | No change. Muse's `duration<=0` note strengthens the case; no new defect. |
| **Law Compliance (BUILD, L-x, L-l, L-h/k, L-u/v, Secrets, Spend Freeze)** | 10/10 | **10/10** | No change. Qwen's cost-saving observation is additive, not corrective. |
| **Security** | 10/10 | **10/10** | No change. URL from internal `video_id`, timeout present, no injection surface. |
| **Test Coverage** | 9/10 | **9/10** | No change. 3 focused tests + 434 suite + 4/4 mutations killed is appropriate for a 15-line diff. |
| **Overall** | **Ship as-is** | **Ship as-is** | Unchanged. |

### 5. FINAL PRIORITY LIST

**P0 CRITICAL:** *None.*

**P1 HIGH:** *None.*

**P2 MEDIUM:** *None.* Two recorded non-defects for future maintainers (no action now):
*   `fetch.py:141` — `any(j.get(k))` truthiness check: intentional; `duration=0` converges to same outcome via existing `duration <=0` guard. If YouTube ever emits `duration=0` for valid content, revisit to `is not None`.
*   `fetch.py:38` — `FACT_KEYS` set: if yt-dlp deprecates any of the 5 keys, add replacement (e.g., `availability`) to keep stub detection robust.

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ship it — the highest-leverage change is no change; this diff correctly prevents stall false-positives with zero regression risk.**

### 7. PRODUCTION READY?

**Yes — unconditionally.**

Conditions: none. The diff is 15 lines, preserves retry cadence, caps retries, excludes stubs from stall, and is verified by 3 invariant tests + 434 existing tests + 4/4 mutations killed. Both independent reviewers reached the same conclusion.
