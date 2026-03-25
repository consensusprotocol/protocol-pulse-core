# CONSENSUS REPORT — ORACLE-FIX — CYCLE 1
Generated: 2026-03-25 14:21
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — playVid Promise Hang | CRITICAL | CRITICAL | CRITICAL | **CRITICAL** |
| Q2 — iOS Autoplay + Blob URLs | HIGH | HIGH | CRITICAL | **HIGH** |
| Q3 — Race .then()/.finally() | MEDIUM (no bug, fragile) | MEDIUM (no bug) | PASS (no bug) | **LOW / No Bug** |
| Q4 — process() Never Fires After Greeting | HIGH (secondary) | HIGH | HIGH | **HIGH** |
| Q5 — Recognition onend Empty Pending | MEDIUM (implied) | MEDIUM | MEDIUM | **MEDIUM** |
| Q6 — Busy Flag During User Speech | HIGH (implied) | HIGH | HIGH | **HIGH** |
| Q7 — iOS Mic Activation After Video | CRITICAL (no setTimeout) | HIGH | HIGH | **HIGH** |
| Q8 — Safety Timeout Adequacy | HIGH | MEDIUM | N/A | **MEDIUM** |

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — `playVid()` Promise Hangs Forever on iOS When `onended` Fails to Fire
**File:** `templates/oracle_live.html`
**Lines:** ~1413–1460 (`playVid()` function body)
**Agreement:** Gemini ✓ GPT-4o ✓ Grok ✓

**What it is:** The `playVid()` function returns a Promise that resolves *only* inside `vid.onended` or `vid.onerror`. On iOS Safari, `onended` frequently never fires for blob-URL video elements. The result: the Promise stays pending forever. `setBusy(false)` is never reached (it lives in `.finally()`), `startRec()` is never called (it lives in `.then()`), the UI is frozen in `RESPONDING` state with mic disabled, and the user cannot interact. The app is permanently hung.

**What to change:**
1. Add a `reject` parameter to the Promise constructor inside `playVid()`.
2. Modify the existing safety timeout to **both reset state AND reject/resolve the Promise** to un-hang the chain.
3. Ensure `clearTimeout(_safetyTimer)` is called inside every resolution path (`onended`, `onerror`) to prevent double-firing.

```javascript
// templates/oracle_live.html — inside playVid(), ~line 1413
function playVid(url){
  return new Promise(function(res, rej){
    setOracleState('RESPONDING');
    vid.loop = false;
    vid.src = url;
    vid.style.opacity = '1';
    if(window._matrixHide) window._matrixHide();

    var settled = false;
    function settle(resolveOrReject, value){
      if(settled) return;
      settled = true;
      clearTimeout(_safetyTimer);
      resolveOrReject(value);
    }

    var _safetyTimer = setTimeout(function(){
      if(!settled){
        console.warn('[Satomi] Safety timeout — forcing mic unlock');
        vid.style.opacity = '0';
        vid.src = '';
        if(window._thinkTimer){clearInterval(window._thinkTimer); window._thinkTimer=null;}
        setBusy(false);
        setOracleState('LISTENING');
        settle(rej, new Error('playVid safety timeout'));
      }
    }, 30000);

    vid.onended = function(){
      vid.style.opacity = '0';
      setTimeout(function(){ vid.src=''; }, 300);
      if(window._thinkTimer){clearInterval(window._thinkTimer); window._thinkTimer=null;}
      if(window._matrixShow) window._matrixShow();
      hideSub();
      settle(res);
    };

    vid.onerror = function(){
      vid.style.opacity = '0';
      vid.src = '';
      setStat('Recovering\u2026','#f4c46f',true);
      setTimeout(function(){
        setBusy(false);
        setOracleState('LISTENING');
        setStat('Ready','#334',false);
      }, 1500);
      settle(res); // resolve to continue flow even on error
    };
    // ... rest unchanged
  });
}
```

---

### U2 — `process()` Never Fires After Greeting (Downstream Consequence of U1)
**File:** `templates/oracle_live.html`
**Lines:** ~1080–1095 (`.then()` block in `playIntent()`), ~1494–1502 (`recognition.onend`)
**Agreement:** Gemini ✓ GPT-4o ✓ Grok ✓

**What it is:** Because the `playVid()` Promise never settles (U1), the `.then()` block that calls `startRec()` never executes. `recognition` is never started. `recognition.onend` never fires. `process()` is therefore unreachable. This is the direct cause of the reported user-facing bug: *greeting plays, mic never activates*.

**What to change:** Fix is gated on U1. Additionally, the `.then()` block must defensively check `busy` state before calling `startRec()`, and the `.catch()` branch from the Safety Timeout rejection (U1 `rej()`) must also transition to LISTENING.

```javascript
// templates/oracle_live.html — inside playIntent(), ~line 1080
.then(function(){
  setOracleState('LISTENING');
  mic.disabled = false;
  startRec();
  setStat('Listening\u2026','#6cff9f',false);
})
.catch(function(e){
  console.warn('[Satomi] playVid chain caught:', e);
  setBusy(false);
  setOracleState('LISTENING');
  setStat('Ready','#334',false);
})
.finally(function(){
  setBusy(false);
});
```

---

### U3 — `busy` Flag Remains `true` During User Speech When Promise Hangs
**File:** `templates/oracle_live.html`
**Lines:** ~1051 (`setBusy(true)` in `playIntent()`), ~1100 (`.finally()`)
**Agreement:** Gemini ✓ GPT-4o ✓ Grok ✓

**What it is:** `setBusy(true)` is called at the start of `playIntent()`. It is only cleared in `.finally()`. Because `.finally()` never runs when the Promise hangs (see U1), `busy` stays `true`. `process()` has an early-exit guard at line 1111: `if(!text||busy) return;`. This means even if speech is somehow captured, `process()` will silently discard it.

**What to change:** The `.catch()` block added in U2 handles this. Additionally verify `setBusy(false)` is called unconditionally in all error/timeout branches of `playVid()`. The `settled` guard in U1 prevents double calls.

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

---

### M1 — iOS Autoplay Reliability: `onended` Fires Zero Times Even When Video Plays
**File:** `templates/oracle_live.html`
**Lines:** ~1438–1445 (`vid.onended` assignment)
**Agreement:** Gemini ✓ GPT-4o ✓ (Grok classified as CRITICAL but same root, same fix direction)

**What it is:** Beyond just "Promise hangs," the specific iOS mechanism is: the video may play to completion visually, yet `onended` never fires. This is a documented iOS WebKit bug with blob-URL video in WKWebView and certain Safari configurations. A `timeupdate`-based fallback is the correct mitigation.

**What to change:** Add a `timeupdate` listener that detects when `currentTime >= duration - 0.25s` and manually triggers the finish logic. Gate with a `finished` boolean to prevent double-resolution.

```javascript
// templates/oracle_live.html — inside playVid(), after vid.onended assignment
var finished = false;

function onFinish(){
  if(finished) return;
  finished = true;
  vid.removeEventListener('timeupdate', checkTimeUpdate);
  settle(res);
  vid.style.opacity = '0';
  setTimeout(function(){ vid.src=''; }, 300);
  if(window._thinkTimer){clearInterval(window._thinkTimer); window._thinkTimer=null;}
  if(window._matrixShow) window._matrixShow();
  hideSub();
}

function checkTimeUpdate(){
  if(!vid.duration || finished) return;
  if(vid.currentTime >= vid.duration - 0.25){
    console.log('[Satomi] timeupdate fallback — triggering onFinish');
    onFinish();
  }
}

vid.addEventListener('timeupdate', checkTimeUpdate);
vid.onended = onFinish;
```

---

### M2 — iOS Mic Activation Requires User Gesture Context — `setTimeout` Breaks It
**File:** `templates/oracle_live.html`
**Lines:** ~1087 (`setTimeout(function(){ startRec(); }, 400)`)
**Agreement:** Gemini ✓ Grok ✓ (GPT-4o flagged same concern)

**What it is:** iOS Safari requires `SpeechRecognition.start()` to be called within the synchronous execution of a user gesture handler (tap, click). Wrapping `startRec()` inside a `setTimeout(..., 400)` breaks this user gesture context chain. The call happens asynchronously 400ms later — iOS has already cleared the gesture context. The recognition either silently fails to start or triggers a permission prompt that itself fails.

**What to change:** Remove the `setTimeout` wrapper. Call `startRec()` synchronously within the `.then()` block (which executes in the resolved-Promise microtask queue, which is closer to the gesture origin than a 400ms macrotask). Alternatively, ensure the initial `playVid()` call itself originates from a tap handler (which it does via the UI flow), making the whole chain a "user-gesture-initiated async sequence."

```javascript
// templates/oracle_live.html — .then() block in playIntent(), ~line 1087
// BEFORE:
.then(function(){
  setTimeout(function(){
    if(!busy && !isRec && mic){
      mic.disabled = false;
      startRec();
      setStat('Listening\u2026','#6cff9f',false);
    }
  }, 400);
})

// AFTER (see U2 fix above — no setTimeout):
.then(function(){
  setOracleState('LISTENING');
  mic.disabled = false;
  startRec();
  setStat('Listening\u2026','#6cff9f',false);
})
```

---

### M3 — `recognition.onend` With Empty `pending` — Silent No-Op, No Recovery
**File:** `templates/oracle_live.html`
**Lines:** ~1494–1502 (`recognition.onend`)
**Agreement:** GPT-4o ✓ Grok ✓

**What it is:** If the user is silent or recognition returns no final results, `pending` is empty when `recognition.onend` fires. The current code checks `if(pending.trim())` but does nothing in the `else` branch — it doesn't restart recognition, doesn't show feedback, and leaves the UI in a pseudo-listening state (`isRec=false`, mic enabled, but recognition not running). User must manually re-tap.

**What to change:** Add auto-restart logic when `pending` is empty and system is not busy.

```javascript
// templates/oracle_live.html — recognition.onend, ~line 1494
recognition.onend = function(){
  setRec(false);
  var _pend = pending.trim();
  if(_pend && !busy){
    setStat('Processing\u2026','#f4c46f',true);
    setTimeout(function(){ process(_pend); pending=''; }, 100);
  } else if(!_pend && !busy && isListeningState()){
    // Auto-restart on silence — user does not need to re-tap
    console.log('[Satomi] Empty recognition result — auto-restarting');
    setTimeout(function(){ startRec(); }, 300);
  }
};
```

---

### M4 — Safety Timeout Duration Is Fixed at 30s Regardless of Video Length
**File:** `templates/oracle_live.html`
**Lines:** ~1419 (`setTimeout(..., 30000)`)
**Agreement:** Gemini ✓ GPT-4o ✓

**What it is:** A greeting video might be 4 seconds long. If `onended` fails, the user waits 30 seconds in a frozen state before recovery. Conversely, a 45-second response video would be cut off by a 30s timer. The timeout should be dynamic, based on actual video duration.

**What to change:** Set the safety timeout after `vid.loadedmetadata` fires, using `vid.duration` as the basis. Minimum of 5s extra padding.

```javascript
// templates/oracle_live.html — inside playVid(), replace static timeout
vid.addEventListener('loadedmetadata', function(){
  var safeDuration = Math.max((vid.duration || 15) * 1000 + 5000, 15000);
  _safetyTimer = setTimeout(function(){
    if(!settled){
      console.warn('[Satomi] Safety timeout after', safeDuration, 'ms');
      // ... same reset logic as U1
      settle(rej, new Error('playVid safety timeout'));
    }
  }, safeDuration);
}, { once: true });
```

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

---

### UI1 — Gemini: `setBusy(false)` Called Inside `playVid()` AND in `.finally()` — Double State Reset
**Model:** Gemini only
**File:** `templates/oracle_live.html`
**Lines:** `playVid()` onerror handler (~1448) AND `.finally()` (~1100)
**Assessment:** **IMPLEMENT**

`setBusy(false)` is called in two places for some code paths: inside `onerror` within `playVid()`, and again in the `.finally()` block of `playIntent()`. This is harmless today but creates fragile coupling — any future state-dependent logic inside `setBusy()` could be double-triggered. The `settled` flag and unified `onFinish()` function from U1/M1 mitigate this, but an explicit audit of all `setBusy` callsites to ensure single-ownership is warranted.

**Action:** After implementing U1, audit all `setBusy(false)` calls in `playVid()` and `playIntent()`. Consolidate so that `setBusy(false)` is called exactly once per code path, owned by the `.finally()` block of `playIntent()`.

---

### UI2 — Grok: Tap-to-Play Overlay Has No Fallback Timeout — Another Permanent Hang Vector
**Model:** Grok only
**File:** `templates/oracle_live.html`
**Lines:** ~1472–1476 (tap-to-play catch block)
**Assessment:** **IMPLEMENT**

When autoplay fails entirely (iOS policy violation, not just `onended` miss), the code shows a tap-to-play overlay. If the user dismisses or ignores it, the Promise still never resolves. Grok correctly identifies this as a second independent hang vector. The fix from U1 (safety timeout now rejects the Promise) partially covers this, but a dedicated timeout on the overlay itself provides defense-in-depth and better UX.

**Action:** Add a 15-second timeout inside the tap-to-play catch handler that calls `settle(rej, ...)` if the user has not interacted.

---

### UI3 — Gemini: The `startRec()` Call Must Be In Synchronous Promise Microtask to Preserve iOS Gesture Context
**Model:** Gemini only (clearest articulation — GPT-4o/Grok touched it but less precisely)
**File:** `templates/oracle_live.html`
**Lines:** ~1087
**Assessment:** **IMPLEMENT** (already captured in M2, but the reasoning is important)

Gemini uniquely articulated that the entire `playIntent()` call chain must originate from a user tap, and that `startRec()` must be invoked in the `.then()` microtask (not a `setTimeout` macrotask) to stay within iOS's gesture context window. This is a correctness argument, not just a timing optimization. Microtasks execute synchronously after the current task completes — they preserve gesture context. `setTimeout` callbacks are scheduled tasks — iOS clears gesture context between them.

**Action:** Already addressed in M2. Document this as a code comment for future maintainers.

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker applied)*

---

### C1 — Should the Safety Timeout Call `res()` or `rej()`?
- **Grok** says: call `res()` (resolve) from the safety timeout
- **Gemini** says: call `rej()` (reject) from the safety timeout, handle in `.catch()`
- **GPT-4o** says: call `setBusy(false)` and `setOracleState('LISTENING')` but doesn't specify resolve/reject

**Tiebreaker — Gemini is correct.**

Reasoning: `rej()` is semantically correct because a timeout represents an abnormal termination, not successful completion. More importantly, using `rej()` means the `.then()` block does NOT execute — which is correct, because the video did not complete normally and we should not proceed as if it did. The `.catch()` block in `playIntent()` then handles recovery cleanly, calling `setOracleState('LISTENING')` and `setBusy(false)`. Using `res()` (Grok's approach) would cause the `.then()` block to execute, potentially calling `startRec()` in an unpredictable state after a 30-second timeout. The Grok approach also requires the safety timer to manually call `setBusy(false)` and `setOracleState` before resolving, whereas the `rej()` approach delegates that responsibility cleanly to `.catch()`.

**Verdict:** Use `rej(new Error('playVid safety timeout'))`. Add a `.catch()` block in `playIntent()` that transitions to LISTENING state.

---

### C2 — Q3 Race Condition: Is it a Bug or Not?
- **GPT-4o** says: BUG CONFIRMED, SEVERITY MEDIUM
- **Gemini** says: No bug confirmed, but code is fragile (MEDIUM concern)
- **Grok** says: No bug confirmed, N/A

**Tiebreaker — Gemini and Grok are correct; GPT-4o overstates.**

The Promise specification guarantees that `.finally()` runs after all chained `.then()` blocks have completed or after `.catch()` has run. There is no race condition between `.then()` and `.finally()` in the JavaScript Promise model. GPT-4o's confusion likely stems from the 400ms `setTimeout` inside `.then()` — the `.finally()` does indeed run before that timer fires, but that is expected behavior, not a bug. However, the structural fragility Gemini notes (that `busy=false` happens before `startRec()` is actually called due to the setTimeout) is a real concern worth fixing — which M2 addresses by removing the `setTimeout`.

**Verdict:** Not a bug. The `setTimeout` removal in M2 makes this a non-issue.

---

### C3 — Q2 Severity: CRITICAL (Grok) vs HIGH (Gemini, GPT-4o)
- **Grok**: CRITICAL
- **Gemini**: HIGH
- **GPT-4o**: HIGH

**Tiebreaker — Gemini/GPT-4o (HIGH) is more precise.**

Q2 (iOS autoplay + blob URL unreliability) is a contributing factor to Q1 (Promise hang), not an independent critical failure. Q1 is the root cause and deserves CRITICAL. Q2 is the iOS-specific mechanism that triggers Q1. Correctly classified as HIGH. The `timeupdate` fallback (M1) directly addresses Q2.

---

## VALIDATED STRENGTHS
*(All models confirmed these are already correct — do NOT modify)*

---

1. **`vid.muted = true` before `.play()`** — Correct approach for iOS autoplay policy compliance. Muted autoplay is permitted; this is the right first step.

2. **`vid.loop = false`** — Correct. Prevents the video from looping infinitely and never firing `onended`.

3. **The `busy` flag architecture** — The concept of a `busy` flag to prevent overlapping requests is architecturally correct. The problem is not the flag's existence but its failure to be cleared on hang.

4. **Blob URL revocation pattern** — Setting `vid.src = ''` after playback to release memory is correct.

5. **`recognition.onresult` accumulating into `pending`** — The pattern of accumulating final speech recognition results into a `pending` variable before processing is sound.

6. **`postMessage` to parent frame for `oracle:speaking` / `oracle:idle`** — The try/catch wrapper around cross-frame communication is correct defensive coding.

7. **`setBusy(true)` at the start of `playIntent()`** — Correct to lock the UI during the async chain. The problem is the unlock path, not the lock.

---

## LAW COMPLIANCE CONSENSUS

*(Based on PIPELINE_LAWS.md principles as referenced by the audit context)*

| Law Area | Status | Detail |
|---|---|---|
| **No silent failure** | ❌ VIOLATED | `onended` failing produces zero console output, no user feedback, permanent hang |
| **Every async must have error handling** | ❌ VIOLATED | `playVid()` Promise has no `.catch()` in `playIntent()` (pre-fix) |
| **State machine must always reach terminal state** | ❌ VIOLATED | `busy=true` with no path to `busy=false` when Promise hangs |
| **iOS platform constraints respected** | ❌ VIOLATED | `setTimeout` breaks gesture context; `onended` used without fallback |
| **User must never see frozen UI without recovery path** | ❌ VIOLATED | 30s frozen state with no user-visible feedback |
| **Timeouts must be proportional to operation** | ❌ VIOLATED | Fixed 30s regardless of video duration |
| **Logging at all failure boundaries** | ⚠️ PARTIAL | Safety timeout has a `console.warn`; `onended` miss has none |
| **Resource cleanup** | ✅ COMPLIANT | `vid.src=''` after playback; `clearInterval` for think timer |
| **User gesture → media** | ✅ COMPLIANT (partially) | Initial flow is gesture-triggered; degraded by `setTimeout` |

**Laws violated:** 6 of ~8 checked. The code requires the P0 fixes to become compliant.

---

## SECURITY CONSENSUS

All three models focused on functional bugs rather than security vulnerabilities. No security-specific issues were flagged by 2+ models. Single-model observations:

1. **Blob URL origin**: Blob URLs are created from server-fetched content. If the `/oracle/speak` endpoint is compromised, arbitrary video content could be played. **Assessment:** Out of scope for this audit pass; belongs in API security review.

2. **`postMessage` with `'*'` wildcard** (~line 1433): `window.parent.postMessage({type:'oracle:speaking'}, '*')` sends to any origin. If the parent frame is from an untrusted origin, this leaks oracle state. **Assessment:** LOW risk for this use case (internal embedding), but should be changed to a specific origin in production.

**Priority:** Neither issue is P0 for this audit. Document postMessage wildcard as a P3 