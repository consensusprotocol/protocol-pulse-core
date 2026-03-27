# CONSENSUS REPORT — ORACLE-FORENSIC — CYCLE 1
Generated: 2026-03-25 18:32
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| iOS src-swap / video element reset | 10/10 | 8/10 | 8/10 | **9/10 — CRITICAL confirmed** |
| Blob URL playback failure | 10/10 | 7/10 | 7/10 | **8/10 — CRITICAL confirmed** |
| Recovering state mapping | 10/10 | 7/10 | 8/10 | **8/10 — CRITICAL confirmed** |
| Recovering never cleared | 9/10 | 8/10 | 9/10 | **9/10 — CRITICAL confirmed** |
| Audio/video race condition | 4/10 | 7/10 | 7/10 | **4/10 — disputed, see CONFLICTS** |
| _settled guard / thinking loop | 3/10 | 7/10 | 6/10 | **3/10 — disputed, see CONFLICTS** |
| Muted flag race | N/A | 5/10 | N/A | **2/10 — weak evidence** |
| State machine reset completeness | 8/10 | 6/10 | 9/10 | **8/10 — HIGH confirmed** |

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — `vid.src` SWAP ON ACTIVELY PLAYING VIDEO (iOS CRITICAL)
**All three models flagged this as a confirmed bug and the primary root cause of the lip-sync failure.**

- **What it is:** When `playVid()` is called, it assigns a new blob URL directly to `vid.src` while the thinking-loop video is actively playing (`vid.loop=true`). On iOS Safari, this corrupts the video element's internal decode pipeline. The video renderer freezes on the last frame of the thinking loop while the audio track of the new source plays normally — producing the exact reported symptom: audio with no lip sync.
- **File/Line:** `oracle_live.html`, `playVid()`, line ~1475
- **What to change:**

```javascript
// BEFORE (broken):
vid.loop = false;
vid.muted = false;
vid.src = url;

// AFTER (fixed):
vid.pause();
vid.removeAttribute('src');
vid.load();              // Forces the element back to EMPTY network state
vid.loop  = false;
vid.muted = false;
vid.src   = url;
```

The `pause() → removeAttribute('src') → load()` sequence is the W3C-specified way to reset a media element to a clean state before assigning a new source. This is required on iOS and harmless everywhere else.

---

### U2 — "RECOVERING" STATE IS SET BUT ROOT CAUSE IS NEVER RESOLVED
**All three models confirmed this is a real bug, though they disagree on whether it persists indefinitely (see Q4 conflict below).**

- **What it is:** `vid.onerror` at line ~1543 calls `setStat('Recovering…')`. This error fires *because* of the broken src-swap (U1). Even after the 500ms timeout calls `_finish(false)` and the `.finally()` block resets the UI to "Ready", the video element remains in a broken decode state. Every subsequent turn fails identically, producing an infinite loop: `speak → Recovering… → Ready → speak → Recovering…`
- **File/Line:** `oracle_live.html`, `vid.onerror` handler, line ~1542–1546
- **What to change:** The fix in U1 prevents `vid.onerror` from ever firing in this path. Additionally, the `onerror` handler should explicitly reset the video element state so recovery is genuine even if other errors occur:

```javascript
vid.onerror = function(e) {
  if (_settled) return;
  console.warn('[Oracle] vid.onerror — resetting element:', e);
  setStat('Recovering\u2026', '#f4c46f', true);
  // Genuinely reset the element so the next call to playVid() starts clean
  vid.pause();
  vid.removeAttribute('src');
  vid.load();
  setTimeout(function() { _finish(false); }, 500);
};
```

---

### U3 — BLOB URL PLAYBACK FAILURE IS A SYMPTOM OF U1, NOT AN INDEPENDENT BUG
**All three models confirmed this — though GPT-4o and Grok treated it as a separate issue, Gemini correctly identified it as a downstream consequence of U1.**

- **What it is:** The blob URL is created correctly. The failure is not in blob URL construction but in the video element's inability to decode and render a new source because it was never properly reset. The blob URL's audio codec is decoded fine; only the video renderer is stuck.
- **File/Line:** Same as U1 — `playVid()`, line ~1475
- **What to change:** Covered entirely by the U1 fix. No separate fix needed for blob URL handling.
- **Consensus note:** The U1 reset resolves both Q1 and Q2 simultaneously. GPT-4o's suggestion to add `play()` promise rejection handling *is* still good defensive code and should be added as a non-critical hardening measure (see P2 below).

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

---

### M1 — EXPLICIT `play()` PROMISE REJECTION HANDLING
**GPT-4o + Grok flagged; Gemini did not explicitly address but did not contradict.**

- **What it is:** `vid.play()` returns a Promise on modern browsers. If it rejects (autoplay policy, interrupted load, etc.), the rejection is currently unhandled, which produces a console error and leaves the state machine in an ambiguous state.
- **File/Line:** `oracle_live.html`, line ~1564–1568
- **What to change:**

```javascript
var p = vid.play();
if (p && typeof p.then === 'function') {
  p.catch(function(err) {
    console.warn('[Oracle] vid.play() rejected:', err);
    // Show tap-to-play overlay if this is an autoplay policy rejection
    if (err.name === 'NotAllowedError') {
      showTapToPlayOverlay(); // surface existing tap overlay
    } else {
      // Treat as a playback error — trigger onerror path
      _finish(false);
    }
  });
}
```

---

### M2 — STATE MACHINE DOES NOT GUARANTEE A KNOWN-GOOD STATE AFTER VIDEO ERROR
**Grok + GPT-4o flagged; Gemini addressed partially via the `.finally()` analysis.**

- **What it is:** If `_finish(false)` is called from `vid.onerror` but `_settled` was already `true` (from a prior race), the `.finally()` block in `process()` may not execute correctly because the Promise was already settled. This means `setOracleState('LISTENING')` and `setStat('Ready')` are never called, and the mic remains disabled.
- **File/Line:** `oracle_live.html`, `playVid()` line ~1481–1483, `vid.onerror` line ~1542
- **What to change:** The `onerror` handler must set `_settled = false` before calling `_finish`:

```javascript
vid.onerror = function(e) {
  // Do NOT gate on _settled here — error recovery must always run
  console.warn('[Oracle] vid.onerror:', e);
  setStat('Recovering\u2026', '#f4c46f', true);
  vid.pause();
  vid.removeAttribute('src');
  vid.load();
  _settled = false;        // Allow _finish to resolve cleanly
  setTimeout(function() { _finish(false); }, 500);
};
```

---

### M3 — THINKING LOOP SETUP SHOULD PAIR `pause()` WITH EVERY `src` ASSIGNMENT
**Grok + Gemini flagged the general pattern; GPT-4o implied it in Q1.**

- **What it is:** Beyond `playVid()`, the thinking loop itself is set in at least two places (L1082–1083 in `playIntent()` and L1195–1206 in `process()`). If any prior video is playing when these lines execute, the same iOS src-swap bug can trigger.
- **File/Line:** `oracle_live.html`, lines ~1082–1083 and ~1195–1206
- **What to change:**

```javascript
// In BOTH locations where thinking loop is started:
vid.pause();
vid.removeAttribute('src');
vid.load();
vid.loop  = true;
vid.muted = true;
vid.src   = '/oracle/thinking';
var _tp = vid.play();
if (_tp && _tp.catch) _tp.catch(function(e){ console.warn('[Oracle] thinking loop play():', e); });
```

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated carefully)*

---

### UI-1 — GEMINI: `.finally()` CLEARS STATUS CORRECTLY BUT LEAVES VIDEO ELEMENT BROKEN (FUNCTIONAL LOOP)
**Source: Gemini only**

Gemini made the sharpest observation in the entire audit: the "Recovering" text *is* cleared after ~500ms (the `.finally()` block runs, calls `setOracleState('LISTENING')`, which calls `setStat('Ready')`). The bug is not that the status is stuck — it's that the *underlying video element* is left in a permanently broken decode state. Every subsequent turn fails at the same point. The user sees "Ready", speaks, gets "Recovering", gets "Ready" — forever.

**Assessment: IMPLEMENT.** This is the most precise articulation of the bug. It elevates U1 from "iOS quirk" to "permanent session failure." The fix must include the `vid.load()` reset in `onerror` (already in M2), not just the `pause()/removeAttribute()` in `playVid()`.

---

### UI-2 — GROK: `pendingVideoUrl` REVOCATION RACE IF AUDIO FINISHES BEFORE VIDEO
**Source: Grok only**

Grok identified that at line ~1329–1331, if `audio.onended` fires before `video_ready`, `pendingVideoUrl` is revoked (`URL.revokeObjectURL`). If the `video_ready` event then fires a fraction of a second later, `playVid()` receives an already-revoked URL. The video element would fire `onerror` immediately, cascading into the Recovering loop.

**Assessment: INVESTIGATE FURTHER.** Gemini explicitly said this is not a deadlock and the design is intentional. However, the revocation-before-use race is a real edge case that Gemini did not fully address. Recommend adding a guard:

```javascript
// In audio.onended handler (~L1329):
var _revokeUrl = pendingVideoUrl;
pendingVideoUrl = null;      // Null first — prevents video_ready from using it
if (_revokeUrl) URL.revokeObjectURL(_revokeUrl);
```

And in the `video_ready` handler (~L1356):
```javascript
if (!pendingVideoUrl) return; // Already consumed by audio.onended race
```

**Priority: P2 — real but low-frequency edge case.**

---

### UI-3 — GPT-4o: MUTED FLAG RACE VIA ASYNC CALLBACK
**Source: GPT-4o only**

GPT-4o claimed async callbacks could re-mute the video after `playVid()` unmutes it. No specific evidence was provided and no other model corroborated.

**Assessment: SKIP.** The code sets `vid.muted = false` synchronously inside `playVid()` at line ~1475. There is no identified async path that re-mutes after this point within the same call stack. This appears to be speculative. Do not implement without a reproduction.

---

## CONFLICTS
*(Models disagree — tiebreaker applied)*

---

### C1 — AUDIO/VIDEO RACE CONDITION: IS IT A BUG?
- **GPT-4o:** BUG CONFIRMED, SEVERITY HIGH — "state machine may not handle transition correctly"
- **Grok:** BUG CONFIRMED, SEVERITY HIGH — "deadlock if setBusy(false) missed"
- **Gemini:** NOT A BUG — "This is an intentional design… does not appear to contain a deadlock"

**Tiebreaker: Gemini is correct.** Gemini performed the most thorough trace of the code path — it found that the audio `onended` handler simply cleans up, and the `video_ready` path explicitly stops the audio before starting video (`window._chatAudioEl.pause()` at ~L1354). The "race" GPT-4o and Grok describe is actually handled by the existing guard. Grok's `pendingVideoUrl` revocation concern (UI-2) is a legitimate edge case but is distinct from a deadlock. GPT-4o and Grok both confirmed the bug without tracing the actual code path, while Gemini did the trace. **Do not implement GPT-4o/Grok's "synchronization" suggestions for this specific issue** — they would likely introduce unnecessary complexity and could break the intentional fast-audio-first design.

---

### C2 — `_settled` GUARD / THINKING LOOP INTERACTION
- **GPT-4o:** BUG CONFIRMED, HIGH — `_settled` from thinking loop could block greeting video
- **Grok:** Partial concern — safety timeout at L1501 could prematurely set `_settled`
- **Gemini:** NOT A BUG — `playVid` is never called for the thinking loop; `_settled` is scoped to each `playVid` invocation via closure

**Tiebreaker: Gemini is correct.** Gemini traced that the thinking loop is set via direct `vid.src` assignment and `.play()` — never through `playVid()`. Therefore, `_settled` is never touched by the thinking loop. Each `playVid()` call creates a new closure with its own `_settled = false`. GPT-4o and Grok both assumed `playVid` was called for the thinking loop, which is factually incorrect per the code trace. **Do not add `_settled` resets for this reason** — it would introduce a real bug by allowing double-resolution of a live Promise.

---

### C3 — "RECOVERING" PERSISTENCE: DOES IT STAY FOREVER OR BRIEFLY?
- **GPT-4o:** Stays forever — "not cleared if error persists"
- **Grok:** Stays forever — critical severity
- **Gemini:** Clears after ~500ms via `.finally()` — the *function* fails, not the *status text*

**Tiebreaker: Gemini is correct on the mechanism but GPT-4o/Grok are correct on the user experience.** The status text does clear. The *session* does not recover. The distinction matters for the fix: the fix target is the broken video element state, not the status text lifecycle. Gemini's analysis should be used for implementation guidance; GPT-4o/Grok's severity rating (critical) is appropriate for the user-facing impact.

---

## VALIDATED STRENGTHS
*(All models agree this is already excellent — do NOT change)*

1. **Blob URL construction pipeline** — The `r.blob().then(blobURL)` pattern is correct. The URL is created properly, revoked appropriately in most paths, and the format is universally supported. Do not change this mechanism.

2. **EventSource + polling fallback architecture** — The dual-path design (EventSource for `video_ready` with a polling fallback) is sound and intentional. Gemini confirmed it is not a deadlock. Do not refactor this.

3. **Fast audio-first response pattern** — Playing audio-only while the video renders is a valid UX optimization. The interrupt-and-replace logic when video arrives is correctly implemented. Do not collapse this into a single sequential flow.

4. **`playVid()` Promise structure** — The pattern of returning a Promise from `playVid()` with a `_settled` guard and resolving via `_finish()` is clean and correct. The `.finally()` block in `process()` correctly handles both success and failure paths. Do not restructure this.

5. **`showTapToPlayOverlay()` / tap-to-play infrastructure** — The overlay mechanism already exists in the codebase. Do not rewrite it; reference it from the `play()` rejection handler.

---

## LAW COMPLIANCE CONSENSUS

| Law / Policy | Status | Determination |
|---|---|---|
| W3C Media Element Reset Spec | ❌ VIOLATED | `src` reassignment without `pause()`+`load()` reset violates the spec's recommended state machine transition for `<video>` elements |
| iOS WebKit Autoplay Policy | ❌ VIOLATED | Src swap on playing element without reset violates iOS autoplay continuation requirements |
| Promise rejection handling | ❌ VIOLATED | Unhandled `play()` rejection is a violation of the project's presumed error-handling laws |
| State machine completeness | ⚠️ PARTIAL | "Recovering" state has an exit path but leaves the video element in a broken state |
| Blob URL lifecycle management | ✅ COMPLIANT | URLs are created and revoked correctly in the primary path |
| Audio/video synchronization | ✅ COMPLIANT | Intentional fast-audio-first design is correctly implemented |

---

## SECURITY CONSENSUS

No security issues were flagged by any model. The blob URL pattern does not introduce XSS vectors (object URLs are same-origin scoped). The EventSource is a read-only server push channel. No consensus security concerns exist.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned)*

1. **No graceful degradation for repeated playback failure** *(GPT-4o + Grok)*: If `vid.onerror` fires multiple times in a session, the user receives no explanation and the session silently degrades. A world-class implementation would track consecutive failure count and surface a user-facing message ("Video unavailable — audio-only mode") after N failures rather than silently looping through Recovering→Ready.

2. **No telemetry on video element errors** *(Grok + Gemini implied)*: `vid.onerror` is a critical signal that is currently only logged to console. Production-quality systems would emit this as a trackable event (e.g., to an analytics endpoint or error monitoring service) so that iOS-specific failure rates are visible in dashboards.

3. **Thinking loop → response transition lacks formalized state** *(All 3 implied)*: The transition from thinking loop to response video is currently an informal "just overwrite the src" pattern. A world-class implementation would have an explicit `TRANSITIONING` state in the state machine with defined entry/exit conditions, making the iOS reset a natural part of state entry rather than a manual patch.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add `vid.pause(); vid.removeAttribute('src'); vid.load();` before every `vid.src = url` assignment in `playVid()` | `oracle_live.html:~1473–1476` | all 3 | Primary root cause of lip-sync failure and Recovering loop on iOS |
| **P0 CRITICAL** | Add same reset sequence (`pause/removeAttribute/load`) to both thinking-loop src assignments in `playIntent()` and `process()` | `oracle_live.html:~1082–1083, ~1195–1206` | grok + gemini | Same iOS src-swap bug applies to thinking loop entry points |
| **P0 CRITICAL** | In `vid.onerror` handler: set `_settled = false` before calling `_finish(false)`, and add `vid.pause(); vid.removeAttribute('src'); vid.load();` to genuinely reset element state | `oracle_live.html:~1542–1546` | grok + gemini + GPT-4o (partial) | Without resetting the element in onerror, every subsequent turn fails — the session never recovers |
| **P1 HIGH** | Add `play()` Promise rejection handler: catch `NotAllowedError` → surface tap overlay; catch other errors → call `_finish(false)` | `oracle_live.html:~1564–1568` | GPT-4o + grok | Unhandled promise rejection leaves state machine in undefined state on autoplay policy failures |
| **P1 HIGH** | Add consecutive-failure counter: after 3 consecutive `vid.onerror` events in a session, set UI to audio-only mode with user-visible notice | `oracle_live.html: vid.onerror handler` | GPT-4o + grok (world-class gap) | Prevents infinite silent failure loop; surfaces degradation to user |
| **P2 MEDIUM** | Guard `pendingVideoUrl` revocation race: null `pendingVideoUrl` before revoking in `audio.onended`; check `if (!pendingVideoUrl) return` in `video_ready` handler | `oracle_live.html:~1329–1331, ~1356` | grok (unique) | Low-frequency but real race; already-revoked URL causes immediate `onerror` cascade |
| **P2 MEDIUM** | Add `play()` rejection logging for thinking-loop `vid.play()` calls | `oracle_live.html:~1083, ~1206` | grok + GPT-4o | Defensive; silent rejection here leaves user in voiceless thinking state |

---

## CYCLE 1 VERDICT

**The code requires targeted fixes before the second build pass — it does NOT require fundamental rework.**

The architecture is sound. The async design, state machine structure, blob URL pipeline, and audio-first response pattern are all validated. The failure is narrowly surgical: a single missing three-line reset sequence (`pause/removeAttribute/load`) that must be applied in three locations. The cascade of symptoms (lip-sync freeze → Recovering loop → infinite failure) all trace to this one root cause.

**Recommendation: Proceed to second build pass with P0 fixes as the mandatory gate. P1 items should be included in the same pass. P2 items can follow.**

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-forensic_CONSENSUS_C1.md.

This is the SECOND PASS for oracle-forensic.
The first build was reviewed by 3 independent AI models (gemini, gpt4o, grok) in 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

═══════════════════════════════════════════════════════════
PRIORITY ACTION PLAN
═══════════════════════════════════════════════════════════

P0 CRITICAL | Add vid.pause(); vid.removeAttribute('src'); vid.load(); immediately
             before every vid.src = url assignment inside playVid().
             | oracle_live.html:~1473–1476
             | models: all 3
             | Primary root cause of iOS lip-sync freeze and Recovering loop.

P0 CRITICAL | Add same pause/removeAttribute/load reset to BOTH thinking-loop
             src assignments: in playIntent() and in process().
             | oracle_live.html:~1082–1083 and ~1195–1206
             | models: grok + gemini
             | Same iOS src-swap bug applies when entering the thinking loop.

P0 CRITICAL | In vid.onerror handler: (1) set _settled = false before _finish(false),
             (2) add vid.pause(); vid.removeAttribute('src'); vid.load() to
             genuinely reset the element so the next playVid() call starts clean.
             | oracle_live.html:~1542–1546
             | models: all 3
             | Without element reset in onerror, every subsequent turn fails permanently.

P1 HIGH     | Add play() Promise rejection handler after every vid.play() call.
             Catch NotAllowedError → surface existing tap-to-play overlay.
             Catch all other errors → call _finish