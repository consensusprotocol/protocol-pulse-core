# CONSENSUS REPORT — ORACLE-EXTERNAL — CYCLE 1
Generated: 2026-03-25 21:22
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — Duplicate Function Definitions | CRITICAL (hideTranscript bug) / LOW (setStat) | MEDIUM | LOW | **HIGH** (critical bug present) |
| Q2 — iOS Safari Polling Reliability | HIGH | HIGH | MEDIUM | **HIGH** |
| Q3 — Minimal Viable Architecture | MEDIUM | MEDIUM | MEDIUM | **MEDIUM** |
| Q4 — Friday Demo Failure Risk | CRITICAL | CRITICAL | HIGH | **CRITICAL** |

> Score methodology: Gemini and GPT-4o scored demo risk CRITICAL; Grok scored it HIGH but described the same failure modes. All models agree polling is the primary risk vector. Gemini uniquely caught a guaranteed ReferenceError that neither other model saw.

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

### U1 — `setStat` is Defined Twice (Monkey-Patch Pattern)

**What it is:** `setStat` is declared as a normal function at line 1595, then reassigned as a closure at line 2165 to extend it for the floating minimized-state indicator. All three models flagged this as an intentional but fragile pattern.

**File/Line:** `templates/oracle_live.html`, lines 1595 and 2165

**What to change:** Integrate the floating-icon logic directly into the original `setStat` body. Delete the monkey-patch block at lines 2164–2172. This removes the double-definition and makes `setStat` a single source of truth.

```javascript
// REPLACE lines 1595-onwards (original setStat):
function setStat(t, c, sp) {
  statEl.textContent = t;
  statEl.style.color = c || '#334';
  spinEl.style.display = sp ? 'block' : 'none';
  spinEl.style.color = c || '#334';

  // Integrated float-indicator logic (was monkey-patch at line 2165)
  var f = document.getElementById("oracle-float");
  if (f && _oracleMinimized) {
    if (t === "Speaking") f.classList.add("speaking");
    else f.classList.remove("speaking");
  }
}
// DELETE lines 2164–2172 entirely.
```

---

### U2 — iOS Safari Will Suspend the Polling Loop During Screen Lock / App Switch

**What it is:** The polling loop in `process()` uses a `setTimeout` chain (~45 iterations × 2s = 90s window). All three models independently confirmed that iOS Safari suspends JavaScript execution when the screen is locked or the user switches apps, making this polling loop unreliable for a 90-second window. This is the single biggest demo risk.

**File/Line:** `templates/oracle_live.html`, `process()` function, lines ~1255–1305

**What to change:** Replace the repeated short-poll loop with a single long-poll `fetch()` call. The OS networking layer is not suspended when Safari is backgrounded — only the JS event loop is. A single fetch with a 95-second timeout will survive backgrounding; the promise will resolve when the user returns to the app.

See the **FINAL ACTION PLAN** for the full code change.

---

### U3 — Multiple Redundant State Variables Create Desynchronization Risk

**What it is:** `busy`, `isRec`, and `ORACLE_STATE` all partially describe the same state. All three models flagged this as a source of potential desynchronization bugs. If one variable is updated and another is not, the UI and mic behavior will be out of sync with the actual system state.

**File/Line:** `templates/oracle_live.html`, global scope and `process()`, `startRec()`, `stopRec()` functions.

**What to change:** `ORACLE_STATE` should be the single authoritative state variable. `busy` and `isRec` should be derived getters or removed, with every `if(busy)` guard replaced by `if(ORACLE_STATE !== 'LISTENING')`. See **Q3 Final Action Plan** for the phased approach.

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

### M1 — Global DOM References (`vid`, `mic`, etc.) Are Accessed Without Existence Checks

**Models:** Grok + Gemini (implied via `_thinkTimer` global pollution discussion)

**What it is:** `vid`, `mic`, and other DOM elements are stored as bare globals and dereferenced throughout the file without null checks. If the DOM structure changes during a patch, these will throw `TypeError: Cannot read properties of null`.

**File/Line:** Global scope, multiple access points throughout `oracle_live.html`

**What to change:** Consolidate all DOM element references into a single `DOM` object initialized once at startup, with a guard that validates all elements exist before the application starts.

```javascript
const DOM = {
  vid: document.getElementById('vid'),
  mic: document.getElementById('mic'),
  statEl: document.getElementById('stat'),
  spinEl: document.getElementById('spin'),
  // ... etc
};
// Guard:
Object.entries(DOM).forEach(([k, v]) => {
  if (!v) console.error('[Oracle] Missing DOM element:', k);
});
```

---

### M2 — State Stuck in `PROCESSING` if Polling Fails — No Auto-Recovery

**Models:** GPT-4o + Gemini

**What it is:** If the polling loop exits via timeout or network failure without receiving a valid video blob, `ORACLE_STATE` remains in `PROCESSING`, `busy` remains `true`, and the mic stays disabled. The user is permanently stuck with no visible error and no path to recovery except a page refresh.

**File/Line:** `templates/oracle_live.html`, poll failure catch block, lines ~1295–1310

**What to change:** In every poll failure path (timeout, network error, invalid blob), call a `_resetToListening()` function that:
1. Sets `ORACLE_STATE = 'LISTENING'`
2. Sets `busy = false`
3. Calls `setStat('Ready', '#334', false)`
4. Re-enables and restarts the mic
5. Displays a user-visible message: "Something went wrong — please try again."

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

### UN1 — `hideTranscript` ReferenceError in `exitOracle()` — GUARANTEED CRASH [Gemini only]

**What it is:** Gemini caught a bug that neither GPT-4o nor Grok detected. At line 2160, `exitOracle()` contains:

```javascript
hideSub(); hideTranscript && hideTX();
```

`hideTranscript` is never defined anywhere in the 2400-line file. In JavaScript, referencing an undeclared variable (not `window.hideTranscript`, just bare `hideTranscript`) throws a `ReferenceError`, not a falsy value. This means `exitOracle()` will throw every time a user attempts to exit the session. The reset logic never completes.

**Assessment: IMPLEMENT IMMEDIATELY. This is a P0 bug that is guaranteed to fire. The intent was clearly `hideTX()`.**

**Fix:**
```javascript
// Line 2160
// BEFORE:
hideSub(); hideTranscript && hideTX();
// AFTER:
hideSub(); hideTX();
```

---

### UN2 — `_thinkTimer` Pollutes Global Scope via `window._thinkTimer` [Gemini only]

**What it is:** Inside `process()`, a local `var _thinkTimer` is declared, then immediately assigned to `window._thinkTimer`. The `clearInterval` is called on `window._thinkTimer`. This is redundant global pollution — the local `var` is sufficient and the `window` assignment is unnecessary.

**Assessment: LOW priority, fix in P2 pass. Not a breaking bug but adds cognitive noise and global scope pollution.**

---

### UN3 — Long-Poll Architecture Requires Server-Side Changes [Gemini — most detailed analysis]

**What it is:** Gemini was the only model to explicitly note that switching to long-polling requires the `/oracle/job/{id}` endpoint to hold its connection open server-side, which may not currently be implemented. GPT-4o and Grok recommended long-polling but didn't flag the server-side dependency.

**Assessment: INVESTIGATE BEFORE IMPLEMENTING. Confirm whether the job endpoint can be modified to hold the connection. If not, the immediate mitigation is adding a robust retry + recovery path to the existing short-poll loop, not a client-only long-poll rewrite that will still timeout at the server.**

---

### UN4 — Page Can Be Terminated by iOS Under Memory Pressure, Losing `videoJobId` [Gemini only]

**What it is:** If a memory-intensive app is opened while polling, iOS may terminate the Safari tab. When the user returns, the page reloads from scratch, `videoJobId` is gone, and the rendered video is unrecoverable. The user sees the gate screen with no explanation.

**Assessment: INVESTIGATE. For the Friday demo, consider persisting `videoJobId` to `sessionStorage` immediately when it is received, and on page load, check `sessionStorage` for an in-progress job and attempt to resume. Medium complexity but high demo-safety value.**

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker applied)*

### C1 — Risk Level of Q1 (Duplicate Functions)

- **Gemini:** CRITICAL (due to `hideTranscript` ReferenceError)
- **Grok:** LOW (no duplicates found, override is intentional)
- **GPT-4o:** MEDIUM

**Tiebreaker — Gemini is correct.** Grok and GPT-4o both missed the `hideTranscript` ReferenceError entirely and evaluated Q1 on the `setStat` redefinition alone, which is low-risk. The correct consensus risk for Q1 is **CRITICAL** because of the guaranteed crash in `exitOracle()`. Grok's "LOW" verdict is wrong on the facts — there is a breaking bug in this category.

---

### C2 — Whether `busy` and `isRec` Should Be Eliminated Now vs. Deferred

- **Gemini:** Argues they can be fully replaced by `ORACLE_STATE` immediately
- **GPT-4o:** Recommends consolidating into a state management object
- **Grok:** Recommends phased consolidation

**Tiebreaker — Grok and GPT-4o are right to be conservative.** Eliminating `busy` and `isRec` entirely is a significant refactor with broad blast radius across dozens of call sites. For a Friday demo, a full state variable elimination is too risky. The correct approach is: (1) ensure `ORACLE_STATE` is always updated alongside `busy`/`isRec`, (2) add a sync-validation guard function, and (3) schedule the full consolidation for a post-demo refactor pass.

---

### C3 — Long-Poll vs. Short-Poll

- **Gemini + GPT-4o:** Recommend switching to long-polling
- **Grok:** Recommends retry mechanism on top of existing short-polling

**Tiebreaker — Grok's recommendation is the safer path for Friday.** Long-polling is the correct long-term architecture, but it requires server-side changes that cannot be validated in time for Friday. The immediate action is: harden the short-poll loop with retry logic, proper error recovery, and state reset on failure. Long-polling should be the P1 post-demo refactor.

---

## VALIDATED STRENGTHS
*(All models agree — do NOT change in the second pass)*

1. **The state machine topology itself** (IDLE → WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING) is logically sound and covers the right states for this use case. Do not restructure the state names or flow.

2. **The `process()` function's local variable naming convention** (underscore-prefixed `_audioFinished`, `_thinkTimer`, etc.) is good defensive practice and should be preserved and extended.

3. **The `fetchTO` wrapper** for `fetch()` with timeout is the right pattern for mobile network reliability. Keep this abstraction.

4. **The 45-attempt × 2-second polling budget** (90-second total window) is a reasonable server-side SLA assumption. The budget is correct even if the mechanism is fragile.

5. **User-visible status via `setStat()`** throughout async operations is excellent UX discipline. Every async state change has a visible indicator. Do not remove or reduce these.

---

## LAW COMPLIANCE CONSENSUS

*(Based on standard mobile web application laws and Protocol Pulse PIPELINE_LAWS)*

| Law | Status | Finding |
|---|---|---|
| No silent failure | **VIOLATED** | Poll timeout leaves user stuck in PROCESSING with no message |
| No global state pollution | **VIOLATED** | `window._thinkTimer`, bare globals `vid`, `mic`, `busy`, `isRec` |
| Single source of truth | **VIOLATED** | `busy` + `isRec` + `ORACLE_STATE` are redundant and can desync |
| Defensive DOM access | **VIOLATED** | DOM elements accessed without null checks |
| Error recovery paths | **VIOLATED** | `exitOracle()` crashes on `hideTranscript` ReferenceError |
| User feedback on async ops | **COMPLIANT** | `setStat()` is called throughout, excellent coverage |
| State machine completeness | **COMPLIANT** | All major states are defined and handled |
| Mobile network resilience | **PARTIAL** | `fetchTO` is good; polling loop is not retry-hardened |

---

## SECURITY CONSENSUS

No security issues were flagged by 2+ models in this cycle. The code is a client-side media/speech application with no visible credential handling, SQL, or eval() calls in scope. Security should be reviewed in a dedicated pass focused on the server-side endpoints (`/oracle/job/{id}`, `/oracle/submit`).

---

## WORLD-CLASS GAP CONSENSUS
*(2+ models mentioned — combined intelligence assessment)*

1. **Polling architecture is not production-grade for mobile** [All 3 models]: A world-class mobile oracle feature uses WebSockets or SSE for push-based video-ready notification, not a polling loop. The current approach is a prototype pattern scaled into a production demo.

2. **State management is fragile and will accumulate bugs** [All 3 models]: A world-class implementation uses a single authoritative state machine with enforced transitions (like XState or a simple home-rolled FSM) rather than multiple boolean flags. Every state transition should be a named, logged event.

3. **No recovery UX for the user** [GPT-4o + Gemini]: A world-class product tells the user when something went wrong and gives them a clear action ("Tap to try again"). The current failure modes are invisible to the user.

4. **No persistence of in-flight job IDs** [Gemini]: A world-class mobile app persists job state to `sessionStorage` so that a page reload or tab-kill doesn't permanently lose a completed server render.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

```
P0 CRITICAL | Fix hideTranscript ReferenceError in exitOracle()
            | file: templates/oracle_live.html, line 2160
            | models: gemini (unique catch — but guaranteed crash)
            | why: exitOracle() throws ReferenceError every invocation;
            |      session reset is impossible without a page refresh.
            | change: replace `hideTranscript && hideTX();` with `hideTX();`

P0 CRITICAL | Add state reset + user message on ALL poll failure paths
            | file: templates/oracle_live.html, process() ~line 1295-1310
            | models: gpt4o + gemini (majority)
            | why: polling failure currently leaves ORACLE_STATE='PROCESSING'
            |      permanently; mic stays disabled; demo is dead.
            | change: implement _resetToListening() called in every catch/
            |         timeout path; show "Something went wrong, please retry"

P1 HIGH     | Merge setStat monkey-patch into original function definition
            | file: templates/oracle_live.html, lines 1595 and 2165-2172
            | models: all 3 (unanimous)
            | why: double-definition is fragile; load order change would
            |      silently break floating indicator sync.
            | change: integrate float logic into line-1595 body; delete 2164-2172

P1 HIGH     | Harden short-poll loop with retry + network error detection
            | file: templates/oracle_live.html, process() ~lines 1255-1305
            | models: all 3 (unanimous on risk, grok on specific solution)
            | why: iOS Safari suspends setTimeout chains on lock/background;
            |      unretried network errors silently exhaust attempt budget.
            | change: catch fetch errors per-attempt and retry that attempt;
            |         extend attempt count from 45 to 60 to absorb suspension
            |         latency; add setStat update on each retry.

P1 HIGH     | Validate all DOM elements exist at startup with console.error
            | file: templates/oracle_live.html, initialization block
            | models: grok + gemini (majority)
            | why: null DOM refs cause TypeError cascades that are hard to
            |      diagnose in a live demo environment.
            | change: add DOM validation object and startup guard loop

P2 MEDIUM   | Persist videoJobId to sessionStorage on receipt
            | file: templates/oracle_live.html, where videoJobId is first set
            | models: gemini (unique — high value for demo safety)
            | why: iOS tab termination under memory pressure loses job ID;
            |      persisting allows resume on reload.
            | change: sessionStorage.setItem('oracleJobId', videoJobId)
            |         on receipt; check on page load and resume if present.

P2 MEDIUM   | Remove window._thinkTimer global pollution
            | file: templates/oracle_live.html, process() ~lines 1191-1203
            | models: gemini (unique)
            | why: unnecessary global scope pollution; confusing double-
            |      assignment to both local var and window property.
            | change: remove window._thinkTimer assignments; use local var only

P2 MEDIUM   | Add state consistency guard: sync busy/isRec with ORACLE_STATE
            | file: templates/oracle_live.html, setOracleState() function
            | models: all 3 (unanimous on problem; grok+gpt4o on conservative fix)
            | why: three variables describing same state will desync under
            |      error conditions; Friday demo prep only — full refactor post-demo.
            | change: inside setOracleState(), derive and set busy and isRec
            |         from the new state value to enforce consistency:
            |         busy = (state === 'PROCESSING' || state === 'RESPONDING')
            |         isRec = (state === 'LISTENING')

P2 MEDIUM   | Post-demo: evaluate long-polling or WebSocket for video-ready signal
            | file: templates/oracle_live.html + server /oracle/job/{id}
            | models: gemini + gpt4o (majority)
            | why: correct long-term architecture; not safe to implement before
            |      Friday without server-side validation.
            | change: spike long-poll support in /oracle/job/{id}; replace
            |         client poll loop with single 95s fetch after demo.
```

---

## CYCLE 1 VERDICT

**The code is NOT ready for a second build pass without the P0 fixes.**

The `hideTranscript` ReferenceError is a guaranteed crash that will fire every time a user exits a session — this alone blocks a production demo. The polling reliability issues are HIGH probability failures on a real mobile device. The good news: the state machine topology is sound, the UX feedback patterns are excellent, and the overall architecture is fixable without structural rework. The P0 and P1 items are all surgical changes. Estimate: 2–3 hours of focused work to get to demo-safe. The code warrants a second build pass immediately after P0/P1 items are resolved.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-external_CONSENSUS_C1.md.

This is the SECOND PASS for oracle-external.
The first build was reviewed by 3 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Fix hideTranscript ReferenceError in exitOracle()
            | file: templates/oracle_live.html, line 2160
            | models: gemini (unique — guaranteed crash)
            | change: replace `hideTranscript && hideTX();` with `hideTX();`

P0 CRITICAL | Add state reset + user message on ALL poll failure paths
            | file: templates/oracle_live.html, process() ~lines 1295-1310
            | models: gpt4o + gemini
            | change: implement _resetToListening() called in every catch/timeout
            |         path; display "Something went wrong, please retry" to user;
            |         ensure ORACLE_STATE='LISTENING', busy=false, mic re-enabled.

P1 HIGH     | Merge setStat monkey-patch into original function definition
            | file: templates/oracle_live.html, lines 1595 and 2165-2172
            | models: all 3
            | change: integrate float-indicator logic into line-1595 setStat body;
            |         delete monkey-patch block at lines 2164-2172 entirely.

P1 HIGH     | Harden short-poll loop with per-attempt retry + attempt budget increase
            | file: templates/oracle_live.html, process() ~lines 1255-1305
            | models: all 3 on risk; grok on solution
            | change: catch fetch errors per-attempt and retry that attempt (max 2
            |         retries per attempt); increase total attempts from 45 to 60;
            |         call setStat('Still rendering...', '#f4c46f', true) on retry.

P1 HIGH     | Validate all DOM elements exist at startup
            | file: templates/oracle_live.html, initialization block
            | models: grok + gemini
            | change: create DOM validation object; add startup guard that calls
            |         console.error('[Oracle] Missing DOM element:', key) for any
            |         null reference; do not block startup, only warn.

P2 MEDIUM   | Persist videoJobId to sessionStorage on receipt; attempt resume on load
            | file: templates/oracle_live.html
            | models: gemini
            | change: sessionStorage.setItem('oracleJobId', videoJobId) when first
            |         assigned; on DOMContentLoaded check for existing key and if
            |         ORACLE_STATE is IDLE, attempt to resume poll.

P2 MEDIUM   | Remove window._thinkTimer global pollution in process()
            | file: templates/oracle_live.html, ~lines 1191-1203
            | models: gemini
            | change: remove all window._thinkTimer assignments; use local var only.

P2 MEDIUM   | Add state consistency enforcement in setOracleState()
            | file: templates/oracle_live.html, setOracleState()
            | models: all 3 on problem; conservative fix only for this pass
            | change: inside setOracleState(state), add:
            |         busy = (state === 'PROCESSING' || state === 'RESPONDING');
            |         isRec = (state === 'LISTENING');
            |         Do NOT remove busy or isRec variables yet — full refactor
            |         is post-demo work only.

VALIDATED — do NOT touch these (all 3 models confirmed excellent):
- The state machine topology: IDLE → WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING
- The fetchTO() wrapper abstraction for network calls with timeout
- The 45-attempt × 2-second polling budget (increase to 60 attempts, keep 2s interval)
- The setStat() call pattern throughout all async operations — do not reduce coverage
- The underscore-prefix naming convention for local variables inside process