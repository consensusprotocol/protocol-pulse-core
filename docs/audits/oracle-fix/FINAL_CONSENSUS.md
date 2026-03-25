# CONSENSUS REPORT — ORACLE-FIX — CYCLE 2
Generated: 2026-03-25 14:24
Models: grok, gemini (+1 failed: gpt4o — TPM rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — `playVid` Promise Hang | CRITICAL | CRITICAL (C1) | CRITICAL | **CRITICAL** |
| Q2 — iOS Autoplay + Blob URLs | HIGH | HIGH (C1) | HIGH | **HIGH** |
| Q3 — Race `.then()`/`.finally()` | LOW / Not a Bug | MEDIUM (C1) | LOW | **LOW / Not a Bug** |
| Q4 — `process()` Never Fires | HIGH | HIGH (C1) | MEDIUM | **HIGH** |
| Q5 — Recognition `onend` Empty Pending | Merged into Q4 | MEDIUM (C1) | MEDIUM | **MEDIUM** |
| Q6 — Busy Flag During User Speech | N/A | HIGH (C1) | MEDIUM | **MEDIUM** |
| Q7 — iOS Mic Activation After Video | MEDIUM | HIGH (C1) | HIGH | **HIGH** |
| Q8 — Safety Timeout Adequacy | CRITICAL | MEDIUM (C1) | HIGH | **HIGH** |
| NEW — Resolution Path Race / `settled` Flag | CRITICAL | N/A | Not raised | **CRITICAL** |

*Note: GPT-4o scores are carried forward from Cycle 1 outputs as C2 call failed. They inform but do not hold full weight in Cycle 2 consensus.*

---

## UNANIMOUS FINDINGS
*(Both active Cycle 2 models agree — implement unconditionally)*

### U1 — `playVid()` Promise Hangs Forever on iOS Safari
**File:** `templates/oracle_live.html` ~Line 1412–1478
**What it is:** The `playVid()` function returns a Promise that resolves exclusively inside `vid.onended` or `vid.onerror`. On iOS Safari, `onended` routinely fails to fire for blob URLs, particularly under autoplay policy restrictions. The Promise remains permanently `pending`. Because `.then()` and `.finally()` only execute after a Promise settles, the entire application freezes:
- `busy` stays `true`
- `ORACLE_STATE` stays `'RESPONDING'`
- Mic button stays disabled
- `startRec()` is never called
- The user cannot interact with the app again

**What to change:** Rewrite `playVid()` so that all three exit paths (`onended`, `onerror`, safety timer) can settle the Promise. Add a `settled` flag (see U2 below) to prevent double-settlement. The safety timer must call `res()` or `rej()` — not merely reset UI state.

```javascript
// templates/oracle_live.html — replace playVid() from ~line 1412
function playVid(url){
  return new Promise(function(res, rej){
    setOracleState('RESPONDING');
    vid.loop = false;
    vid.src = url;
    vid.style.opacity = '1';
    if(window._matrixHide) window._matrixHide();

    var settled = false;
    function settle(isSuccess, value){
      if(settled) return;
      settled = true;
      clearTimeout(_safetyTimer);
      vid.onended = null;
      vid.onerror = null;
      if(isSuccess) res(value);
      else rej(value);
    }

    var _safetyTimer = setTimeout(function(){
      console.warn('[Satomi] Safety timeout — forcing state transition after 30s');
      vid.style.opacity = '0';
      vid.src = '';
      setBusy(false);
      if(window._thinkTimer){ clearInterval(window._thinkTimer); window._thinkTimer=null; }
      setOracleState('LISTENING');
      setStat('Ready', '#6cff9f', false); // User feedback on recovery
      settle(false, new Error('playVid safety timeout'));
    }, 30000);

    vid.onended = function(){
      vid.style.opacity = '0';
      if(window._thinkTimer){ clearInterval(window._thinkTimer); window._thinkTimer=null; }
      settle(true);
    };

    vid.onerror = function(e){
      console.warn('[Satomi] vid.onerror — settling promise to unblock chain', e);
      vid.style.opacity = '0';
      settle(true); // Resolve (not reject) so the chain continues normally
    };

    try{ if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*'); }catch(e){}
    vid.muted = true;
    vid.play().then(function(){
      setStat('Speaking', '#6cff9f', false);
      vid.muted = false;
    }).catch(function(err){
      console.warn('[Satomi] vid.play() rejected (autoplay policy):', err);
      showTapOverlay();
    });
  });
}
```

---

### U2 — Resolution Path Race Condition (Non-Idempotent Settlement)
**File:** `templates/oracle_live.html` ~Line 1412–1478
**What it is:** Even with a corrected safety timer, `playVid()` has three asynchronous exit paths that can all potentially fire: `onended`, `onerror`, and `_safetyTimer`. Without a guard, multiple paths could settle the Promise sequentially, triggering state-cleanup logic twice and causing unpredictable behavior (double `setBusy(false)`, double `setOracleState()`, etc.). This is a latent bug that naive fixes introduce.

**What to change:** The `settled` flag pattern shown in U1 is the mandatory implementation. Every settlement path checks `if(settled) return` before acting, and nullifies the other handlers after settling. This is not optional — it is architecturally required for any correct fix to Q1/Q8.

---

### U3 — Safety Timeout Does Not Settle the Promise
**File:** `templates/oracle_live.html` ~Line 1419–1426
**What it is:** In the original code, the safety timer resets UI state (`setBusy(false)`, `setOracleState('LISTENING')`) but never calls `res()` or `rej()`. A pending Promise with UI state forcibly reset is the worst of both worlds — the UI appears ready but the Promise chain is still hanging, meaning any downstream `.then()` logic (including `startRec()`) still never executes.

**What to change:** The safety timer must call `settle()` as shown in U1. This is an extension of U1 but warranted as a standalone finding given both models flagged it independently.

---

## MAJORITY FINDINGS
*(2 of 2 active models agree — implement unless compelling reason not to)*

### M1 — iOS Mic Activation Fragility (Q7)
**File:** `templates/oracle_live.html` ~Line 1087–1091
**Gemini:** MEDIUM | **Grok:** HIGH
**What it is:** `startRec()` is called inside a `setTimeout(..., 400)` after the video ends. On iOS, `SpeechRecognition.start()` must be called within a gesture-trusted event chain. A 400ms async gap may break this trust chain depending on iOS version and browser state.

**What to change:** Remove the `setTimeout` wrapper where possible. Call `startRec()` directly within the `.then()` resolution handler. If a brief yield is truly needed for UI paint, use `requestAnimationFrame` instead of an arbitrary 400ms timeout.

```javascript
// In playIntent() .then() block, ~line 1087
.then(function(){
  if(!busy){
    startRec(); // Call directly — no setTimeout
  }
})
```

---

### M2 — `recognition.onend` Dead-End on Silence (Q4/Q5)
**File:** `templates/oracle_live.html` ~Line 1494
**Gemini:** HIGH | **Grok:** MEDIUM
**What it is:** When the user says nothing (or speech recognition times out), `recognition.onend` fires with `pending` empty or whitespace. The current handler does nothing in this case — it neither restarts listening nor gives user feedback. The conversational loop is broken silently.

**What to change:** Add a restart branch for the empty-pending case:

```javascript
// templates/oracle_live.html ~line 1494
recognition.onend = function(){
  setRec(false);
  var _pend = pending.trim();
  pending = '';
  if(_pend && !busy){
    setStat('Processing…', '#f4c46f', true);
    setTimeout(function(){ process(_pend); }, 100);
  } else if(!busy && oracleState === 'LISTENING'){
    // Silence timeout — restart listening gracefully
    console.log('[Satomi] Recognition ended with no input — restarting listener');
    setStat('Listening…', '#6cff9f', false);
    setTimeout(function(){ startRec(); }, 300);
  }
};
```

---

## UNIQUE INSIGHTS
*(Only 1 active Cycle 2 model raised these — evaluated individually)*

### UNIQUE-1 — User Feedback Gap During Safety Timeout Recovery
**Source:** Grok only
**What it is:** When the 30-second safety timer fires and forces a state reset, no user-visible message is shown. The app silently transitions to 'LISTENING' state, leaving the user with no explanation for the apparent freeze and recovery.

**Assessment: IMPLEMENT** — This is low-effort, high-empathy UX hardening. A single `setStat('Ready', '#6cff9f', false)` or equivalent message call inside the safety timer handler costs nothing and meaningfully reduces user confusion during error recovery. Already incorporated into the U1 fix above.

---

### UNIQUE-2 — `timeupdate` Event as Proactive `onended` Fallback
**Source:** Gemini (referencing GPT-4o's C1 analysis as inspiration)
**What it is:** Rather than waiting for the full 30-second safety timer, `vid.timeupdate` could be used to detect when `currentTime` approaches `duration`, allowing the Promise to be resolved proactively seconds before the timeout would fire. This prevents the user from waiting 30s in a frozen state.

**Assessment: INVESTIGATE FURTHER** — This is architecturally sound and significantly better UX than the 30s fallback. However, `timeupdate` granularity varies across iOS versions, and checking `currentTime >= duration - 0.5` may misfire on short videos or seek events. Recommend implementing as a secondary defense layer with a threshold guard:

```javascript
vid.ontimeupdate = function(){
  if(!settled && vid.duration && vid.currentTime >= vid.duration - 0.3){
    console.log('[Satomi] timeupdate near-end fallback triggered');
    settle(true);
  }
};
```

Add this inside `playVid()` after the `onended` handler. It should fire the `settle()` call before `onended` on iOS if `onended` fires late; the `settled` flag prevents double execution. **Recommend implementing as P1.**

---

### UNIQUE-3 — Tap-to-Play Overlay Should Have Its Own Timeout
**Source:** Grok only
**What it is:** The tap-to-play overlay shown on autoplay failure has no timeout. If a user walks away and never taps, the app is stuck indefinitely in a waiting state that bypasses even the safety timer.

**Assessment: IMPLEMENT** — Add a secondary timeout (suggested: 60 seconds) inside `showTapOverlay()` that auto-dismisses the overlay and calls `settle(false, ...)` to un-hang the Promise chain:

```javascript
function showTapOverlay(){
  var ov = document.getElementById('tap-to-play');
  if(ov){
    ov.style.display = 'flex';
    var abandonTimer = setTimeout(function(){
      ov.style.display = 'none';
      console.warn('[Satomi] Tap-to-play abandoned — forcing state reset');
      // The safety timer in playVid() handles the Promise settlement
    }, 60000);
    ov.onclick = function(){
      clearTimeout(abandonTimer);
      vid.play().then(function(){
        ov.style.display = 'none';
        setStat('Speaking', '#6cff9f', false);
      }).catch(function(e){
        clearTimeout(abandonTimer);
        console.warn('[Satomi] tap-to-play retry failed:', e);
        vid.style.opacity = '0';
        setStat('Ready', '#334', false);
      });
    };
  }
}
```

---

## CONFLICTS
*(Where models gave contradictory recommendations)*

### CONFLICT-1 — Q3: Is the `.then()`/`.finally()` Order a Bug?
**GPT-4o (C1):** Rated MEDIUM — suggested moving `setBusy(false)` to a shared function.
**Gemini (C2):** Rated LOW / Not a Bug — correctly notes Promise spec guarantees `.finally()` runs after `.then()` settles.
**Grok (C2):** Rated LOW — agrees with Gemini.

**Tiebreaker: Gemini and Grok are correct.** The Promise specification (ECMA-262) guarantees that `.finally()` executes only after the preceding `.then()` chain has settled. There is no race condition here. GPT-4o's Cycle 1 concern was based on a misreading of execution order. The real issue is that *neither block executes at all* due to the hung Promise (Q1). Once Q1 is fixed, Q3 requires no changes. **Do not refactor `setBusy()` calls on this basis.**

---

### CONFLICT-2 — Q6: Severity of Busy Flag During User Speech
**GPT-4o (C1):** HIGH — `busy=true` prevents `process()` from executing during user speech.
**Grok (C2):** MEDIUM — rates it as secondary to Q1.
**Gemini (C2):** Did not raise as standalone issue.

**Tiebreaker: Grok's MEDIUM framing is more accurate for Cycle 2.** This issue is entirely caused by Q1 (the Promise never settling means `busy` never resets). It is not an independent bug — it is a downstream symptom. Fixing Q1 eliminates this issue. No separate fix needed beyond U1.

---

### CONFLICT-3 — Q8/Safety Timer: `reject()` vs `resolve()` on Timeout
**Gemini (C1/C2):** Suggests `rej(new Error('playVid safety timeout'))` — reject the Promise on timeout.
**Grok (C1):** Suggests calling `res()` — resolve the Promise on timeout.

**Tiebreaker: Use `rej()` for semantic correctness, but handle it in `.catch()`.** The safety timer firing is genuinely an error condition. Rejecting preserves semantic integrity and allows a dedicated `.catch()` block to handle the error path (e.g., showing an error state before re-enabling the mic). However, the `onerror` handler should call `settle(true)` (resolve), because a video decode error is not fatal to the conversation — we want the chain to continue normally after a bad video. The combined pattern from U1 correctly distinguishes these two cases.

---

## VALIDATED STRENGTHS
*(Both models confirmed these areas are sound — do NOT change in the second pass)*

1. **Promise Chain Structure in `playIntent()`** — The overall `.then().catch().finally()` architecture is correctly designed. The bug is inside `playVid()`, not in how `playIntent()` consumes it. Do not restructure the outer chain.

2. **`setBusy()` / `setOracleState()` State Machine** — The centralized state management functions are well-implemented. The state transitions themselves are correct. The bug is that they're never called due to the hung Promise, not that they're broken.

3. **Mute-then-Unmute Autoplay Strategy** — Starting with `vid.muted=true` and unmuting on `canplay` is the correct iOS autoplay bypass pattern. Do not change this approach.

4. **`tap-to-play` Overlay Concept** — The existence of a user-gesture fallback overlay is architecturally correct. It needs hardening (timeout, see UNIQUE-3) but the pattern itself is right.

5. **`fetch` Timeout (`fetchTO`) Handling** — Both models found no issues with the fetch timeout logic in `playIntent()`. This area is solid.

---

## LAW COMPLIANCE CONSENSUS

*Note: `PIPELINE_LAWS.md` was not provided directly. Compliance is assessed from context clues in the audit outputs.*

| Law / Principle | Status | Determination |
|---|---|---|
| Promises must always settle | **VIOLATED** | `playVid()` Promise hangs indefinitely on iOS — critical violation |
| State transitions must be deterministic | **VIOLATED** | Multiple unsynchronized settlement paths create non-determinism |
| User actions must always produce feedback | **VIOLATED** | Frozen UI with no feedback after video ends on iOS |
| Error paths must be handled | **VIOLATED** | Safety timer resets UI but does not settle Promise or show error message |
| Idempotent state cleanup | **VIOLATED** | No `settled` flag means cleanup logic can execute multiple times |
| Graceful degradation | **PARTIAL** | `tap-to-play` overlay exists but has no timeout/abandonment handling |
| Speech recognition loop must be continuous | **VIOLATED** | Empty `pending` in `onend` creates a silent dead-end |

**Overall compliance: FAILING on 6 of 7 assessed laws. Not shippable without P0 fixes.**

---

## SECURITY CONSENSUS

Both models' analyses did not surface direct security vulnerabilities. The following observations are relevant:

1. **Blob URL Handling** — Blob URLs are generated from server responses at line ~1455. If the server response is not validated before being fed into a blob URL and assigned to `vid.src`, this could be an XSS vector. **Investigate:** Confirm server response is a valid video MIME type before creating the blob. Neither model flagged this as a confirmed issue, but it warrants review.

2. **`postMessage` Broadcast** — Line ~1415 sends `{type:'oracle:speaking'}` to `window.parent` without origin validation. This is low-risk for read-only telemetry messages but should use an explicit target origin rather than `'*'`.

3. **No authentication tokens in client-side JS** — Not observed. No credentials appear hardcoded.

**Security priority: LOW overall. Blob URL validation is the only item worth a second look.**

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly world-class product)*

### GAP-1 — No Progressive Recovery UX (Both models)
A world-class voice interface handles failure gracefully and visibly. The current implementation goes silent for up to 30 seconds with no user feedback, then snaps back to 'LISTENING' without explanation. Users interpret this as a crash. World-class behavior: show a spinner with "Still thinking…" at 5s, "Taking a moment…" at 15s, and a clear "Ready to listen" confirmation on recovery.

### GAP-2 — No Conversation Loop Resilience on Silence (Both models)
A world-class oracle does not silently die when a user pauses or says nothing. The current silence dead-end (Q4/Q5) means a single missed recognition event breaks the entire session. World-class behavior: automatic restart with configurable max-retry count, escalating to a gentle prompt ("I'm listening — take your time").

### GAP-3 — iOS-Specific Test Coverage (Both models, implicitly)
All identified bugs are iOS-specific and appear to have been missed in testing. A world-class product includes automated BrowserStack or Sauce Labs tests on iOS Safari 16/17 for the full video-to-mic activation flow. The absence of this coverage allowed a CRITICAL bug to reach audit stage.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Rewrite `playVid()` with `settled` flag — all three exit paths (`onended`, `onerror`, `_safetyTimer`) must call `settle()`. Promise must resolve or reject on each path. | `templates/oracle_live.html` ~L1412–1478 | Both (unanimous) | Core bug: Promise hangs forever on iOS, freezing entire app. Without this, app is non-functional on iOS Safari. |
| **P0 CRITICAL** | Safety timer must call `settle(false, error)` — not just reset UI state | `templates/oracle_live.html` ~L1419–1426 | Both (unanimous) | Current timer resets UI but leaves Promise pending — worst of both worlds. |
| **P0 CRITICAL** | Add `setStat()` user feedback call inside safety timer before `settle()` | `templates/oracle_live.html` ~L1419 | Grok | Without this, users see a silent freeze-and-snap. Trivial to add, high UX value. |
| **P1 HIGH** | Add `vid.ontimeupdate` near-end fallback using `currentTime >= duration - 0.3` | `templates/oracle_live.html` ~L1435 | Gemini-inspired | Prevents 30s user-facing freeze. Fires `settle(true)` proactively before iOS drops `onended`. |
| **P1 HIGH** | Fix `recognition.onend` empty-pending dead-end — restart listening if `!busy && oracleState === 'LISTENING'` | `templates/oracle_live.html` ~L1494 | Both | Silence kills the conversation loop. Core UX break. |
| **P1 HIGH** | Remove 400ms `setTimeout` around `startRec()` — call directly in `.then()` | `templates/oracle_live.html` ~L1087–1091 | Both | iOS gesture-trust chain may not survive 400ms async gap. `requestAnimationFrame` if yield needed. |
| **P1 HIGH** | Add abandonment timeout (60s) to `tap-to-play` overlay | `templates/oracle_live.html` ~`showTapOverlay()` | Grok | Without this, an untapped overlay creates a second infinite-hang path bypassing the safety timer. |
| **P2 MEDIUM** | Validate server response MIME type before creating blob URL for `vid.src` | `templates/oracle_live.html` ~L1455 | Synthesis | Low-risk but closes a potential XSS surface area. |
| **P2 MEDIUM** | Replace `window.parent.postMessage({...}, '*')` with explicit target origin | `templates/oracle_live.html` ~L1415 | Synthesis | Security hygiene — `'*'` is acceptable for telemetry but explicit is better. |
| **P2 MEDIUM** | Add progressive user feedback during long response wait (5s/15s milestones) | `templates/oracle_live.html` — `setStat()` calls | Both (GAP-1) | World-class UX gap. Not a bug but significantly improves perceived reliability. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

The code has one show-stopping CRITICAL bug (the `playVid()` Promise hang) and one critical architectural gap that any fix attempt will introduce without careful implementation (the non-idempotent settlement race). Both models reached this verdict independently and unanimously.

**Absolute final blocker:** On iOS Safari — the primary target device for a voice oracle — the app freezes permanently after the greeting video. The mic never activates. The user cannot interact. There is no recovery. This is a complete functional failure on the platform the feature is designed for.

The remaining issues (mic restart on silence, iOS mic activation timing, tap-to-play abandonment) are high-impact but would be acceptable as fast-follow if the P0 were somehow shipped around. They are not blocking on their own.

**After implementing P0 and P1 items:** The code will be functionally production-ready. The P2 items represent quality hardening and should be addressed in the same PR if time permits, or queued immediately after.

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles by correctly identifying not only *that* the `.finally()` block never executes on a pending Promise but articulating *why* — a fundamental Promise behavior that made the bug's severity undeniable and that neither Grok nor GPT-4o captured with equal precision. Its Cycle 2 output demonstrated genuine self-correction at depth, independently surfacing the `settled` flag race condition, the `timeupdate`-based fallback as a superior alternative to blunt safety timeouts, and the `recognition.onend` dead-end — findings that directly shaped the consensus report's CRITICAL-tier items.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive implementation order based on severity, dependency chain, and consensus weight.

---

## TIER 1 — CRITICAL (Implement First / Blocking)

### P1 — Rewrite `playVid()` with a `settled` Guard and Three Exit Paths
**File:** `templates/oracle_live.html` ~Line 1412–1478
**Why first:** Everything downstream — `startRec()`, mic activation, `busy` reset — is gated on this Promise settling. Nothing else matters until this is fixed.

```javascript
function playVid(url) {
  return new Promise(function (resolve, reject) {
    var settled = false;

    function settle(fn, arg) {
      if (settled) return;
      settled = true;
      clearTimeout(_safetyTimer);
      fn(arg);
    }

    var _safetyTimer = setTimeout(function () {
      console.warn('[Satomi] Safety timeout — forcing playVid resolve');
      settle(resolve, 'timeout');
    }, 12000); // tune to your longest expected video

    vid.onended = function () { settle(resolve, 'ended'); };
    vid.onerror = function (e) { settle(reject, e); };

    // P2 fallback lives here — see below
    vid.ontimeupdate = function () {
      if (!settled && vid.duration > 0 &&
          (vid.currentTime / vid.duration) >= 0.97) {
        console.warn('[Satomi] timeupdate near-end fallback fired');
        settle(resolve, 'timeupdate');
      }
    };

    setOracleState('RESPONDING');
    vid.src = url;
    vid.load();
    vid.play().catch(function (err) {
      console.error('[Satomi] vid.play() rejected:', err);
      settle(reject, err);
    });
  });
}
```

**Covers:** U1 (Promise hang) + NEW CRITICAL (resolution path race)

---

### P2 — Replace Blunt Safety Timeout with `timeupdate` Near-End Fallback
**File:** Same block as P1 (embedded above)
**Why second:** The 30-second safety timeout causes an unacceptable UX freeze before the app recovers. The `timeupdate` event fires continuously during playback; checking for ≥97% completion catches iOS `onended` suppression within milliseconds of the real end. This is already wired into P1 above — no separate file change needed. Confirm the threshold empirically on device.

---

## TIER 2 — HIGH (Implement Before QA / Functionally Blocking on iOS)

### P3 — Gate `vid.play()` on Confirmed User Gesture
**File:** `templates/oracle_live.html` — `showTapOverlay()` / tap handler
**Why:** iOS Safari's autoplay policy for blob URLs requires a user gesture in the same call stack. If `vid.play()` is called outside a gesture context, the video never starts, `onended` never fires, and even P1's fallbacks are working around a preventable failure. The correct fix is to not need the fallbacks in the first place.

```javascript
// In your tap/start handler — ensure play() is called synchronously
// inside the event callback, not deferred via fetch or setTimeout
tapButton.addEventListener('click', function () {
  // Prime the video element with a silent play() to unlock autoplay
  vid.muted = true;
  vid.play().then(function () {
    vid.pause();
    vid.muted = false;
    // Now safe to proceed with intent flow
    playIntent('GREETING');
  }).catch(function (e) {
    console.error('[Satomi] Autoplay unlock failed:', e);
  });
});
```

**Covers:** Q2 (iOS autoplay + blob URLs), Q7 (mic activation after video)

---

### P4 — Fix `process()` Never Firing When `startRec()` Is Finally Reached
**File:** `templates/oracle_live.html` — `startRec()` / `recognition.onresult` handler ~line range per Q4
**Why:** Even after P1 unblocks the Promise chain and `startRec()` is called, if the `recognition.onresult` → `process()` path has a logic gap (empty `pending`, wrong state guard), the conversation loop breaks silently. This is the next hard blocker after P1.

```javascript
recognition.onend = function () {
  if (pending && pending.trim().length > 0) {
    process(pending);
    pending = '';
  } else {
    // Recognition ended with no usable input — return to LISTENING
    console.warn('[Satomi] recognition.onend: empty pending, resetting to LISTENING');
    setOracleState('LISTENING');
    setBusy(false);
  }
};
```

**Covers:** Q4 (`process()` never fires), Q5 (`recognition.onend` empty pending dead-end)

---

### P5 — Audit and Correct `busy` Flag Scope During User Speech Phase
**File:** `templates/oracle_live.html` — `setBusy()` calls surrounding `startRec()`
**Why:** If `busy` is still `true` when `startRec()` is eventually called (post-P1 fix), the mic may be gated off at the UI layer even though the recognition engine is technically running. Verify that `setBusy(false)` is called — and that the mic button's `disabled` binding respects this — before `recognition.start()`.

```javascript
// Confirm this sequence in the .then() block after playVid resolves:
setBusy(false);              // ← must precede startRec()
setOracleState('LISTENING');
startRec();
```

**Covers:** Q6 (busy flag during user speech), Q7 (mic activation)

---

## TIER 3 — MEDIUM (Implement Before Release / Defensive Hardening)

### P6 — Add Explicit `.catch()` on the `playIntent()` Promise Chain
**File:** `templates/oracle_live.html` — `playIntent()` ~Line 1050–1104
**Why:** If `playVid()` rejects (via `vid.onerror` or `vid.play()` rejection), there is currently no `.catch()` handler on the outer chain. An unhandled rejection leaves `busy=true` and the state machine frozen — the same symptom as the original bug, just via a different path.

```javascript
playIntent('GREETING')
  .catch(function (err) {
    console.error('[Satomi] playIntent failed:', err);
    setBusy(false);
    setOracleState('IDLE');
  });
```

---

### P7 — Revoke Blob URLs After Playback
**File:** `templates/oracle_live.html` — inside `playVid()` settle path
**Why:** Each call to `playVid()` creates a blob URL via `URL.createObjectURL()`. If `URL.revokeObjectURL()` is never called, memory leaks accumulate across the session — critical for long Oracle sessions.

```javascript
// Inside the settle() wrapper, after vid.src operations:
function settle(fn, arg) {
  if (settled) return;
  settled = true;
  clearTimeout(_safetyTimer);
  URL.revokeObjectURL(url); // ← add this
  fn(arg);
}
```

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Tier | Covers |
|---|