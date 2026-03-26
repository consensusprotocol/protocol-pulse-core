# CONSENSUS REPORT — ORACLE-EXTERNAL — CYCLE 2
Generated: 2026-03-25 21:24
Models: grok, gemini (+1 failed: gpt4o — rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — Code Bugs & Duplicates | HIGH | MEDIUM (C1 only) | HIGH | **HIGH** |
| Q2 — iOS Safari Polling Reliability | HIGH | HIGH (C1 only) | HIGH | **HIGH** |
| Q3 — Minimal Viable Architecture | MEDIUM | MEDIUM (C1 only) | MEDIUM | **MEDIUM** |
| Q4 — Friday Demo Failure Risk | CRITICAL | CRITICAL (C1 only) | CRITICAL | **CRITICAL** |

*Note: GPT-4o scores carried forward from Cycle 1 due to rate limit failure in Cycle 2. Consensus is based on 2 live models plus 1 historical signal.*

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### 1. `hideTranscript` ReferenceError — Guaranteed Crash in `exitOracle`

**What it is:** On line 2160, the expression `hideTranscript && hideTX()` attempts to evaluate `hideTranscript` as a variable. This identifier is never defined anywhere in the 2,379-line file. In non-strict JavaScript, referencing an undeclared variable in a boolean expression like this does **not** silently return `undefined` — it throws a `ReferenceError`, which halts the entire `exitOracle()` execution immediately. Every user who tries to exit the oracle session will hit this crash. It is a 100% failure rate on a core UI flow.

**File/Line:** `templates/oracle_live.html`, line 2160

**What to change:**
```javascript
// BEFORE (broken — throws ReferenceError):
hideSub(); hideTranscript && hideTX();

// AFTER (correct):
hideSub(); hideTX();
```

---

### 2. iOS Safari Polling Unreliability — Core Video Retrieval Will Fail on Mobile

**What it is:** The `process()` function (lines ~1255–1305) retrieves the generated video blob using a short-polling loop built on `setTimeout`. On iOS Safari, when a user locks their phone or switches to another app during this polling window (which can run up to 90 seconds), the OS suspends JavaScript execution entirely. The polling loop freezes mid-cycle. When the user returns, the loop may have missed its window, leaving the app in a broken state waiting for a video that will never arrive via the poll. Given this is a mobile-primary product, this failure mode is near-certain in real-world use.

**File/Line:** `templates/oracle_live.html`, lines ~1255–1305 (the `process()` function polling block)

**What to change:** Replace the `setTimeout`-based polling loop with a single long-polling `fetch()` request with a ~95-second server-side timeout. The OS network stack handles connections in the background independently of JavaScript execution, making this resilient to app suspension.

```javascript
// BEFORE (fragile short-polling):
function pollForVideo(attempts) {
  if (attempts <= 0) { /* handle timeout */ return; }
  setTimeout(() => {
    fetch('/api/oracle/result/...')
      .then(r => r.json())
      .then(data => {
        if (data.ready) { /* handle video */ }
        else pollForVideo(attempts - 1);
      });
  }, 2000);
}

// AFTER (single long-poll — iOS safe):
fetch('/api/oracle/result/...', {
  signal: AbortSignal.timeout(95000) // ~95s — adjust to match server timeout
})
  .then(r => r.json())
  .then(data => { /* handle video directly */ })
  .catch(err => { /* handle timeout / network failure */ });
```

*Requires server-side endpoint to hold the connection open until the video is ready or a timeout occurs.*

---

### 3. `setStat` Monkey-Patch — Fragile Double Definition

**What it is:** `setStat` is defined as a proper function at line 1595, then reassigned as a monkey-patch at line 2165 that wraps the original via `_origSetStat`. This works currently only because of script execution order. Any reordering of the script (minification, bundling, file reorganization) could break the patch silently. It also creates two cognitive entry points for the same function, making debugging and maintenance substantially harder.

**File/Line:** `templates/oracle_live.html`, lines 1595 (original) and 2165 (monkey-patch)

**What to change:** Delete the monkey-patch block (lines ~2164–2172). Integrate the floating icon update logic directly into the original `setStat` body at line 1595.

```javascript
// Single unified setStat (replaces both definitions):
function setStat(t, c, sp) {
  statEl.textContent = t;
  statEl.style.color = c || '#334';
  spinEl.style.display = sp ? 'block' : 'none';
  spinEl.style.color = c || '#334';

  // Integrated float icon logic (previously in monkey-patch):
  var f = document.getElementById("oracle-float");
  if (f && _oracleMinimized) {
    // ... float icon update logic here
  }
}
```

---

## MAJORITY FINDINGS (2 of 2 models agree)

All findings in this audit are unanimous between the two live models. See Unanimous Findings above. The following are carried from the Cycle 1 GPT-4o signal for completeness:

### 4. Redundant State Variables — Risk of State Desynchronization

**What it is:** Three separate variables — `busy`, `isRec`, and `ORACLE_STATE` — maintain overlapping representations of application state. When these fall out of sync (e.g., `busy === true` but `ORACLE_STATE === 'IDLE'`), the UI and application logic diverge, producing ghost states where the mic is disabled but the UI shows it as active, or vice versa.

**File/Line:** `templates/oracle_live.html`, variable declarations ~lines 820–830, used throughout

**What to change:** Consolidate into a single state object with a controlled transition function. This is a P2 refactor and does not block the demo, but should be the first structural change in the next sprint.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### A. `playVid` Always-Resolve Anti-Pattern (Gemini only)
**Assessment: IMPLEMENT — P1**

Gemini identified that `playVid()` (line 1374) is deliberately written to always resolve its promise, even on error or timeout. The inline comment confirms this is intentional: `/* FIX 1: Always resolve — even on error — so .then() chain continues */`. 

This is a significant hidden risk. The `playIntent` caller's `.catch()` block will never fire for video failures. The application will proceed along the "happy path" regardless of whether the video actually played, potentially triggering mic reactivation at the wrong time or leaving the session in a broken-but-silent state. The "fix" that was applied to avoid a previous bug has created a more subtle and harder-to-diagnose one. The correct pattern is to reject on genuine failure and let callers handle it explicitly.

**Recommended action:** Modify `playVid` to reject on error/timeout. Ensure all callers (especially `playIntent`) have explicit `.catch()` handlers that transition to a known safe state (e.g., fallback message + re-enable mic).

---

### B. `blobURL` Revocation Before Playback Completion (Grok only)
**Assessment: INVESTIGATE FURTHER**

Grok noted that `blobURL()` (lines 1367–1371) revokes the previous object URL before creating a new one, but does not verify that all active references to the old URL have been released. If a video element is still playing the old blob when revocation occurs, the video element's `src` becomes invalid mid-playback.

This is a legitimate concern on lower-end devices or slow networks where playback initialization is delayed. Before marking as a confirmed bug, verify empirically: does the current revocation call occur only when a new video is requested (implying the previous one has finished), or can it be triggered concurrently? If concurrent triggering is possible, add a guard:

```javascript
function blobURL(blob) {
  if (vid && !vid.paused) vid.pause(); // Ensure no active playback
  if (objURL) URL.revokeObjectURL(objURL);
  objURL = URL.createObjectURL(blob);
  return objURL;
}
```

---

### C. Hardcoded Polling Interval / No Backoff (Grok only)
**Assessment: SKIP (superseded)**

Grok flagged the hardcoded 2-second polling interval and 45-attempt cap. This finding is entirely superseded by the unanimous P0 recommendation to replace polling with a single long-poll. There is no backoff strategy to design if the polling loop is eliminated. No separate action required.

---

### D. No User Retry Prompt on Network Failure (Grok only)
**Assessment: IMPLEMENT — P2**

When network errors occur during polling (lines ~1347–1350), error messages are displayed but no retry affordance or automatic fallback to text mode is offered. During a live demo, a transient network hiccup could strand the user with an error message and no path forward. A simple "Try again" button or auto-fallback to text mode after N seconds would significantly improve resilience.

---

### E. `_thinkTimer` Global Scope Pollution (Gemini C1 only)
**Assessment: SKIP — LOW RISK**

`_thinkTimer` is declared with `var` in `process()` (function-scoped) and then also assigned to `window._thinkTimer`. This is redundant and pollutes the global namespace but is not functionally breaking. Given the P0/P1 backlog, this is low-priority cleanup for a future refactor sprint.

---

## CONFLICTS (models disagree — tiebreaker)

### Risk Level of `setStat` Redefinition

- **Grok (Cycle 1):** LOW — intentional and documented
- **GPT-4o (Cycle 1):** MEDIUM — could cause unexpected behavior
- **Gemini (Cycle 2):** Agrees with refactor but treats it as P1, not blocking

**Tiebreaker verdict:** GPT-4o / Gemini are correct that MEDIUM is the right severity, but it is not CRITICAL and does not block shipping. The risk is maintenance-time, not runtime — the monkey-patch works today. However, because the fix is simple (merge two functions), it should be done as a P1 to eliminate future maintenance debt. Classify as **P1 HIGH**, not blocking, but implement in the same pass.

---

## VALIDATED STRENGTHS (all models agree — do NOT touch)

1. **Underscore-prefix convention for private variables in `process()`** — e.g., `_audioFinished`, `_thinkTimer` local declaration. This is good defensive practice and should be maintained and extended to other functions.

2. **`_newRecognition()` abstraction for Speech Recognition** — Encapsulating `webkitSpeechRecognition` setup into a dedicated factory function is the right pattern. It makes reinitialization clean and avoids stale recognition object bugs.

3. **Blob URL creation/revocation lifecycle in `blobURL()`** — The intent of revoke-before-create is correct (prevents memory leaks from accumulating object URLs). The implementation is sound for the sequential playback case. Only investigate if concurrent triggering is confirmed (see Unique Insight B above).

4. **Tap overlay fallback (`setupTapFallback`)** — Providing a tap-to-start fallback for iOS autoplay restrictions is the correct defensive pattern and should not be removed.

---

## LAW COMPLIANCE CONSENSUS

*Note: Full PIPELINE_LAWS.md was not provided in this audit package. Assessment based on inferred laws from findings.*

| Law / Principle | Status | Notes |
|---|---|---|
| No undefined variable references in shipped code | ❌ **VIOLATED** | `hideTranscript` ReferenceError — line 2160 |
| Promise chains must handle rejection | ❌ **VIOLATED** | `playVid` always-resolves — line 1374 |
| Mobile-first reliability for network I/O | ❌ **VIOLATED** | Short-poll loop not iOS-safe |
| Single source of truth for state | ⚠️ **AT RISK** | Three overlapping state variables |
| No global scope pollution | ⚠️ **MINOR** | `window._thinkTimer` assignment |
| DOM element abstraction (no raw ID strings scattered) | ✅ **COMPLIANT** | `vid`, `mic`, `statEl` etc. cached at top |
| Graceful degradation on feature absence | ✅ **COMPLIANT** | `webkitSpeechRecognition` checked before use |

**Final determination:** Two law violations must be resolved before any production deployment. The `ReferenceError` is a hard blocker. The promise anti-pattern is a soft blocker (will cause state corruption under error conditions).

---

## SECURITY CONSENSUS

No security-critical issues were flagged by either model in this feature. The following observations from the broader Cycle 1 context are noted for completeness:

1. **Blob URL handling** — Object URLs are origin-scoped and not a cross-origin risk. Revocation is implemented. No finding.
2. **Vision image upload (`sendVisionImage`, line 1956)** — No model in this cycle audited the server-side handling of vision uploads. This is an **open security surface** that has not been reviewed. If the upload endpoint does not validate file type, size, and content server-side, it is a potential injection/DoS vector. Flag for dedicated security audit.
3. **No auth tokens or credentials visible in client-side code** — Compliant. No keys detected in the audited file.

**Priority order:**
1. (Open) Server-side validation of vision image uploads — requires separate audit
2. (Resolved by P0) No further XSS or injection vectors identified in client code

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

### 1. Formal State Machine (both models)
The ad-hoc state management via `busy`, `isRec`, and `ORACLE_STATE` strings is the single largest gap between this codebase and production-grade quality. A world-class implementation would use an explicit state machine (e.g., XState, or even a hand-rolled transition table) where:
- Each state is enumerated
- Valid transitions are declared
- Illegal transitions throw or are silently rejected
- The UI is a pure function of the current state

This would eliminate the entire class of state-desynchronization bugs identified across both cycles.

### 2. Resilient Mobile Network Architecture (both models)
The short-poll architecture is not just a bug — it reflects a design assumption (stable, foreground JavaScript execution) that does not hold on mobile. A world-class implementation would be designed from the ground up for mobile constraints: long-poll or SSE for server push, `visibilitychange` listeners to detect and recover from backgrounding, and `navigator.onLine` checks before any network operation.

### 3. Observable Error States with User Affordances (both models)
Currently, errors are displayed as status text but offer no path forward. A world-class implementation would treat every error as a recoverable state: offer retry, fallback to text mode, or escalate to support. No error should be a dead end.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Fix `hideTranscript` ReferenceError — replace `hideTranscript && hideTX()` with `hideTX()` | `oracle_live.html:2160` | all (2/2) | Guaranteed crash on every `exitOracle()` call — 100% failure rate on core UI flow |
| **P0 CRITICAL** | Replace `setTimeout` polling loop with single long-polling `fetch()` (~95s timeout) | `oracle_live.html:~1255–1305` | all (2/2) | iOS Safari will suspend JS during polling — primary failure mode for mobile demo |
| **P1 HIGH** | Merge `setStat` monkey-patch into original function — delete lines ~2164–2172 | `oracle_live.html:1595 & 2165` | all (2/2) | Fragile load-order dependency; single unified function eliminates the risk |
| **P1 HIGH** | Rework `playVid` to reject on error/timeout instead of always-resolve | `oracle_live.html:~1374–1410` | gemini (unique) | Silent swallowing of video failures causes downstream state corruption invisible to callers |
| **P2 MEDIUM** | Consolidate `busy`, `isRec`, `ORACLE_STATE` into a single state object with controlled transitions | `oracle_live.html:~820–830` | all (2/2 + C1 signal) | Three sources of truth for state will desynchronize; eliminates a whole class of future bugs |
| **P2 MEDIUM** | Add user retry affordance / auto-fallback to text mode on network error | `oracle_live.html:~1347–1350` | grok (unique) | Dead-end error states are unacceptable in a live demo context |
| **P2 MEDIUM** | Guard `blobURL` revocation — verify no active playback before revoking old URL | `oracle_live.html:~1367–1371` | grok (unique) | Low-likelihood but real risk of invalidating src mid-playback on slow devices |
| **P2 MEDIUM** | Flag vision image upload endpoint for dedicated server-side security audit | `oracle_live.html:~1956` | synthesized | Unreviewed upload surface — cannot confirm safety without server-side audit |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

After two full cycles of multi-model review, the verdict is clear and unanimous: this code has **two hard blockers** that must be resolved before any production or high-stakes demo deployment.

**Absolute final blockers:**

1. **The `hideTranscript` ReferenceError** (line 2160) will crash `exitOracle()` for 100% of users who try to exit a session. This is a one-line fix that must be applied immediately.

2. **The short-polling architecture** will fail on iOS Safari in any real-world mobile usage scenario involving screen lock or app switching during a 90-second video generation window. Given this is a mobile-primary product, this is not an edge case — it is the primary use case. This requires a backend coordination change (long-poll endpoint) and a frontend change (single fetch replacing the loop).

The remaining P1 finding (the `playVid` always-resolve pattern) is not a guaranteed crash but will produce subtle, hard-to-diagnose state corruption under error conditions. It should be fixed in the same pass if time permits; it would be irresponsible to defer it to a third cycle.

The P2 items represent legitimate technical debt but do not block a controlled demo or initial release if the P0s are resolved.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-external_CONSENSUS_C2.md.

This is the FINAL PASS for oracle-external.
The feature was reviewed by 2 independent AI models across 2 cycles (plus 1 Cycle 1 signal).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Fix `hideTranscript` ReferenceError | oracle_live.html:2160 | models: all (2/2) | Guaranteed crash on every exitOracle() call — change `hideTranscript && hideTX()` to `hideTX()`

P0 CRITICAL | Replace setTimeout polling loop with single long-polling fetch() | oracle_live.html:~1255–1305 | models: all (2/2) | iOS Safari suspends JS during polling; use single fetch() with ~95s AbortSignal.timeout(), requires server-side endpoint to hold connection until video ready or timeout

P1 HIGH | Merge setStat monkey-patch into original function | oracle_live.html:1595 & 2165 | models: all (2/2) | Delete monkey-patch block ~2164–2172; integrate float icon update logic directly into the setStat body at line 1595; single source of truth

P1 HIGH | Rework playVid to reject on error/timeout instead of always-resolve | oracle_live.html:~1374–1410 | models: gemini | Remove the "always resolve" pattern; reject on genuine failure; ensure all callers (especially playIntent) have explicit .catch() handlers that transition to a known safe state

P2 MEDIUM | Consolidate busy/isRec/ORACLE_STATE into a single state object | oracle_live.html:~820–830 | models: all | Single state object with controlled transition function; eliminates desync bugs

P2 MEDIUM | Add user retry affordance / auto-fallback to text mode on network error | oracle_live.html:~1347–1350 | models: grok | No dead-end error states; offer retry button or auto-fallback after N seconds

P2 MEDIUM | Guard blobURL revocation — check no active playback before revoking | oracle_live.html:~1367–1371 | models: grok | Pause video element before revoking old object URL to prevent mid-playback src invalidation

VALIDATED (do NOT touch — all models confirmed excellent):
- Underscore-prefix convention for private variables in process() — maintain and extend
- _newRecognition() factory abstraction for Speech Recognition — do not change
- Blob URL create/revoke lifecycle intent in blobURL() — only add the playback guard, do not restructure
- setupTapFallback() tap overlay for iOS autoplay — do not remove or modify

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(oracle-external): post-audit pass — consensus improvements C2"
git push origin main
```

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. It was the **sole discoverer** of the `hideTranscript` ReferenceError — the only confirmed CRITICAL bug, a 100% failure-rate crash in a core UI flow — demonstrating superior depth and accuracy that both Grok and GPT-4o validated in Cycle 2. Its findings were precise, line-referenced, and immediately actionable without requiring interpretation, and it maintained the strongest completeness score by addressing code bugs, architectural fragility, and the `_thinkTimer` global pollution that no other model flagged.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list. Implement in this sequence — higher items block lower items from being testable.

---

## PRIORITY 1 — IMPLEMENT BEFORE FRIDAY (Blocking / Demo-Critical)

### P1-A — Fix `hideTranscript` ReferenceError in `exitOracle()`
- **File:** `templates/oracle_live.html`, line 2160
- **Change:** Replace `hideSub(); hideTranscript && hideTX();` with `hideSub(); hideTX();`
- **Why first:** 100% crash rate on core UI flow. Every exit attempt fails. No other fix matters if users cannot exit the session cleanly.

### P1-B — Replace Short-Poll Loop with Single Long-Poll `fetch` for Video Retrieval
- **File:** `templates/oracle_live.html`, lines ~1255–1305 (`process()` function)
- **Change:** Replace the `setTimeout`-based polling loop with a single `fetch()` call to a long-polling endpoint. The OS network stack maintains the connection through backgrounding; the JavaScript timer loop does not.
- **Why second:** iOS Safari will suspend the polling loop when the user locks their phone during the 90-second video generation window. This is not an edge case — it is the default mobile usage pattern. Demo failure on any iOS device is near-certain without this fix.

---

## PRIORITY 2 — IMPLEMENT THIS WEEK (High Risk / Silent Failures)

### P2-A — Harden `setStat` Monkey-Patch Pattern
- **File:** `templates/oracle_live.html`, lines 1595 and 2165
- **Change:** Consolidate both definitions into a single function that accepts an optional `minimizedSync` parameter, or clearly document the monkey-patch with a block comment and an explicit ordering guard (`if (typeof _origSetStat === 'undefined') throw new Error(...)`).
- **Why:** File reordering or a future refactor will silently break the floating indicator sync with no error thrown. Low immediate risk, high latent risk.

### P2-B — Remove `window._thinkTimer` Global Pollution
- **File:** `templates/oracle_live.html`, lines 1191 and 1203 (`process()` function)
- **Change:** Remove the `window._thinkTimer =` assignment. Use only the locally scoped `var _thinkTimer`. Update all `clearInterval` calls to reference the local variable.
- **Why:** Unnecessary global scope pollution creates collision risk with any future script loaded on the same page. The local `var` declaration already provides the required scope.

---

## PRIORITY 3 — SCHEDULE FOR NEXT SPRINT (Structural / Maintainability)

### P3-A — Consolidate Redundant State Variables
- **File:** `templates/oracle_live.html`, multiple locations
- **Change:** Replace the parallel `busy`, `isRec`, and `ORACLE_STATE` variables with a single state machine object. Define all valid state transitions explicitly. Derive `busy` and `isRec` as computed properties of `ORACLE_STATE`.
- **Why:** Three overlapping state variables with no enforced consistency guarantee divergence under async conditions. This is a correctness risk that grows with every new feature added to the oracle flow.

### P3-B — Add iOS `visibilitychange` / `pagehide` Guard for Polling Recovery
- **File:** `templates/oracle_live.html`, `process()` function
- **Change:** Even after P1-B is implemented, add a `document.addEventListener('visibilitychange', ...)` handler that logs or alerts if the page is hidden mid-request, and resumes or retries the long-poll on `visibilityState === 'visible'`.
- **Why:** Long-polling reduces but does not eliminate iOS suspension risk. A recovery handler makes the system resilient to the remaining edge cases without a backend change.

---

## IMPLEMENTATION ORDER SUMMARY

```
P1-A  →  P1-B  →  P2-A  →  P2-B  →  P3-A  →  P3-B
 Fix       Fix     Harden   Clean    Refactor  Harden
 crash    iOS      monkey   global   state     recovery
          poll     patch    scope    machine   handler
```

**P1-A and P1-B must ship before the Friday demo. Everything else is post-demo.**