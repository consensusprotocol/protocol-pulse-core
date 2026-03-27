# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: friday-demo
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### PROTOCOL PULSE CODE AUDIT — FRIDAY DEMO READINESS REVIEW

As part of the pre-merge quality gate for the Friday demo, I have conducted a thorough audit of the provided files (`oracle_live.html` and `merch.html`) with a focus on potential failure modes, user experience issues, and demo readiness. Below are my detailed responses to the 8 brutal questions, identifying specific issues, their severity, and actionable fixes. My goal is to ensure the demo does not embarrass the team in front of a live audience of 10+ people.

---

### Q1 — MOST LIKELY FAILURE MODE DURING LIVE DEMO
- **FAILURE MODE**: Microphone permission denial or failure to unlock audio context on mobile devices, leading to the app being stuck at the gate screen with no clear recovery path.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:977-986`
- **FIX**: Enhance error messaging to provide a more prominent retry mechanism and a fallback for users who can't grant mic access. Add a visible "Retry Mic Access" button directly in the error message (line 978) with styling to stand out (e.g., `style="background:#ff3b5f;color:#fff;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;"`). Additionally, implement a timeout fallback after 10 seconds of no mic access to suggest a text input mode if available.
- **DEMO IMPACT**: The audience sees the app stuck at the gate screen with an error like "Microphone blocked," causing confusion and halting the demo. Without a clear retry or bypass, the presenter must awkwardly explain or reload the page, breaking flow.

---

### Q2 — PERCEIVED BROKENNESS
- **FAILURE MODE**: Lack of feedback during long processing delays (e.g., video rendering or network latency) makes the app appear broken. The "thinking" video plays, but if it fails to load, users see a black screen or static avatar with no status update.
- **SEVERITY**: HIGH
- **FILE:LINE**: `oracle_live.html:1096-1103`
- **FIX**: Strengthen the fallback mechanism for the thinking video. If `vid.onerror` triggers (line 1097), immediately update the status text to "Loading response... please wait" (via `setStat` call) to reassure users. Add a secondary timeout check at line 1101 to revert to static avatar with a message if playback doesn't start within 3 seconds.
- **DEMO IMPACT**: Audience perceives the app as broken due to a black screen or no visible progress for 10-15 seconds during processing. They may think the app crashed, leading to presenter intervention and loss of trust.

---

### Q3 — MOBILE-SPECIFIC FAILURE MODES
- **FAILURE MODE**: iOS Safari autoplay restrictions prevent the thinking video or response video from playing without user interaction, resulting in a static avatar or black screen. Additionally, touch targets for buttons like the mic (line 480) are too small on smaller screens.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:1100-1101` (autoplay issue), `oracle_live.html:480-483` (touch target)
- **FIX**: For autoplay, add a user-interaction fallback at line 1101: if `vid.play()` fails with a `NotAllowedError`, display a one-time overlay with a "Tap to Play" button over the video area (new DOM element at line 681). For touch targets, increase the minimum size of interactive elements like `#mic` to 48x48px (already set at line 481, but ensure it’s enforced with `min-width` and `min-height` in CSS for all buttons).
- **DEMO IMPACT**: On mobile, the audience sees a non-responsive app if videos don’t play, requiring the presenter to tap manually (if they notice). Small touch targets cause missed taps, making the demo look unpolished and frustrating the presenter.

---

### Q4 — GPU CONTENTION
- **FAILURE MODE**: Not directly addressed in the provided HTML files since `avatar_server.py` is not included. However, based on the frontend code, if the GPU is busy rendering for another user, fetch requests to `/oracle/chat` or `/oracle/job` (line 1118, 1219) could timeout or return errors, leaving the user with a "thinking" loop or static avatar indefinitely.
- **SEVERITY**: HIGH
- **FILE:LINE**: `oracle_live.html:1118-1121`
- **FIX**: Implement a server-side queue status check before initiating a render request. At line 1118, before calling `/oracle/chat`, add a pre-check to `/oracle/status` to see if the GPU is available. If not, display a message like "High demand — waiting for render slot..." via `setStat` and retry after a delay. Add a client-side timeout of 90s (already set, but reinforce with a user-facing message at line 1121).
- **DEMO IMPACT**: Audience sees the app stuck in a "thinking" state for an extended period (or timeout error if fetch fails), making the demo appear slow or broken. The presenter may need to apologize or restart, disrupting the flow.

---

### Q5 — WORST UX MOMENT
- **FAILURE MODE**: The transition from user speaking to processing feels abrupt and lacks clear feedback. After stopping recording (line 1431-1436), the app shows the thinking video, but if it fails or delays, there’s no 

## GEMINI — CYCLE 1 OUTPUT
Here is a ruthless audit of the provided code, focusing on readiness for a live demo.

---

### Q1 — MOST LIKELY FAILURE MODE DURING LIVE DEMO

*   **FAILURE MODE:** The initial microphone permission request fails or is silently blocked by the browser/OS, preventing the demo from starting at all. The host clicks "Speak to Satomi," and either nothing happens or a complex, technical error message appears.
*   **SEVERITY:** CRITICAL
*   **FILE:LINE:** `templates/oracle_live.html:931-987`
*   **FIX:** The current error handling is good for a developer but terrible for a live demo. It requires the host to debug their browser settings in front of an audience. A fallback mechanism is essential. If `getUserMedia` fails, the UI should not just show an error, but also present a "Continue with Text Input" button. This guarantees the demo can proceed, even with a mic issue.
    ```javascript
    // In the .catch block at line 971
    .catch(function(err){
        // ... existing error message logic ...
        // ADD THIS:
        gErr.innerHTML += '<br><button id="text-fallback-btn" style="...">Continue with Text</button>';
        document.getElementById('text-fallback-btn').onclick = function() {
            // Logic to switch to a text input-based flow
            go_with_text_input(); 
        };
    });
    ```
*   **DEMO IMPACT:** Without this fix, the demo has a significant chance of being a non-starter. The host clicks the main call-to-action, and it fails. The audience sees the host fumbling with the browser's address bar, trying to find the permission settings. Total loss of momentum and credibility from the first click.

---

### Q2 — PERCEIVED BROKENNESS

*   **FAILURE MODE:** The audio-first response creates a jarring disconnect. The user hears Satomi's voice playing while the avatar is either static or stuck in the "thinking" animation, as the lip-synced video is not yet ready. It breaks the illusion of a live, speaking intelligence and makes it feel like a cheap voice-over.
*   **SEVERITY:** HIGH
*   **FILE:LINE:** `templates/oracle_live.html:1178-1211` (audio plays) vs. `templates/oracle_live.html:1213-1300` (video is fetched/polled for later).
*   **FIX:** Prioritize a cohesive experience over raw speed for the demo. Do not play the audio stream until the video stream is also ready. The user is more patient with a slightly longer "thinking" phase than they are with a disjointed audio/visual experience.

    Change the logic to wait for *both* streams. Alternatively, a less invasive fix is to improve the status text to manage expectations:
    ```javascript
    // At line 1183
    // setStat('Speaking','#6cff9f',false);
    // INSTEAD:
    setStat('Speaking... (rendering video)','#6cff9f',false);

    // And in playVid, at line 1383
    setStat('Speaking','#6cff9f',false); // Set the final "Speaking" state only when video plays
    ```
*   **DEMO IMPACT:** The audience hears a disembodied voice while the avatar isn't moving its lips correctly. It immediately exposes the underlying tech in an unflattering way, making it feel less like magic and more like "playing an audio file while a video loads."

---

### Q3 — MOBILE-SPECIFIC FAILURE MODES

*   **FAILURE MODE:** On iOS Safari, subsequent video playback will be blocked if it's not triggered by a direct user gesture. The initial tap on "Speak to Satomi" unlocks the audio/video context, but the response video, which plays after server processing, is not tied to a new gesture. The `vid.play()` promise at line 1388 will likely be rejected.
*   **SEVERITY:** CRITICAL
*   **FILE:LINE:** `templates/oracle_live.html:1388-1394`
*   **FIX:** The `catch` block for the video play promise needs to provide a user-facing recovery mechanism. If autoplay fails, an overlay with a large "Tap to Play" icon should appear over the video. This allows the user to manually trigger the playback and salvage the experience.
    ```javascript
    // At line 1390
    p.then(function(){}).catch(function(){
      // OLD: setStat('Tap to play',...); // This is too subtle
      // NEW:
      var playOverlay = document.createElement('div');
      playOverlay.style = 'position:absolute; inset:0; background:rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; cursor:pointer; z-index:99;';
      playOverlay.innerHTML = '<svg ... style="width:64px; height:64px; fill:white;"><path d="...play icon..."/></svg>';
      playOverlay.onclick = function() {
        vid.muted = false;
        vid.play();
        this.remove();
      };
      vid.parentElement.appendChild(playOverlay);
    });
    ```
*   **DEMO IMPACT:** The oracle processes the request, the "thinking" animation stops, and... nothing. The host is left with a static image of the avatar, while the audio may or may not play. The demo grinds to a halt on what is arguably the most important platform.

---

### Q4 — GPU CONTENTION

*   **FAILURE MODE:** The server-side Python code (not provided, but inferred) has no

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — FRIDAY-DEMO — CYCLE 1
Generated: 2026-03-25 11:00
Models: grok, gemini (+1 failed — GPT-4o: TPM rate limit exceeded)

---

## SCORES

*Note: Neither model provided explicit numerical scores. Scores below are synthesized from severity ratings and issue density across the 8 audit questions. GPT-4o failed — marked N/A.*

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Mic / Permission Gate | 4/10 (CRITICAL) | N/A | 4/10 (CRITICAL) | **4/10** |
| Video Playback / Autoplay | 5/10 (HIGH) | N/A | 5/10 (CRITICAL) | **5/10** |
| Mobile / iOS Safari | 4/10 (CRITICAL) | N/A | 5/10 (CRITICAL) | **4/10** |
| GPU / Server Queue | 6/10 (HIGH) | N/A | 6/10 (HIGH) | **6/10** |
| UX Feedback / State Transitions | 6/10 (MEDIUM) | N/A | 5/10 (HIGH) | **5/10** |
| Error Handling / Network Failure | 6/10 (implied) | N/A | 4/10 (CRITICAL) | **5/10** |
| Visual Polish / UI Consistency | 7/10 (implied) | N/A | 6/10 (MEDIUM) | **6/10** |
| Audio/Video Sync | 4/10 (HIGH) | N/A | 6/10 (implied) | **5/10** |
| **Overall Demo Readiness** | **5/10** | **N/A** | **5/10** | **5/10** |

**Interpretation:** 5/10 overall. The app has a solid aesthetic foundation but carries multiple CRITICAL-severity failure modes that have a high probability of triggering during a live audience demo. It is **not yet demo-safe** without targeted fixes.

---

## UNANIMOUS FINDINGS
*(Both models flagged these — implement unconditionally)*

---

### UNANIMOUS-1 — Microphone Permission Failure Has No Demo-Safe Recovery

**What it is:** If `getUserMedia` fails (browser block, OS denial, HTTPS issue, device conflict), the app displays a developer-facing error message and stops. There is no path forward for the presenter or audience. The demo dies at the very first interaction.

**File:Line:** `templates/oracle_live.html:931–987` (Gemini) / `oracle_live.html:977–986` (Grok)

**What to change:**
- In the `.catch` block of `getUserMedia`, after existing error text is rendered, inject a styled **"Continue with Text Input"** button that activates a text-based fallback flow
- The fallback flow should bypass `getUserMedia` entirely and allow typed queries to proceed through the full oracle pipeline
- Error container must be styled to match the cyberpunk design language (dark background, neon border, monospace font) — not raw unstyled HTML
- Add a visible **"Retry Mic Access"** button as a secondary option before the text fallback

---

### UNANIMOUS-2 — iOS Safari Autoplay Blocks Response Video Playback

**What it is:** iOS Safari blocks video `.play()` calls that are not synchronously triggered by a direct user gesture. The response video — which plays after server-side processing completes — is not tied to any new user gesture. The `vid.play()` promise at the `playVid` function will be rejected silently or with a `NotAllowedError`, leaving the avatar static while audio may or may not play.

**File:Line:** `templates/oracle_live.html:1388–1394` (Gemini) / `oracle

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/oracle_live.html (2137 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover,interactive-widget=resizes-content">
   6 | <meta name="theme-color" content="#000">
   7 | <meta name="apple-mobile-web-app-capable" content="yes">
   8 | <meta name="apple-mobile-web-app-status-bar-style" content="black">
   9 | <meta http-equiv="Permissions-Policy" content="microphone=*, camera=*">
  10 | <title>Satomi · Protocol Pulse</title>
  11 | <link rel="preconnect" href="https://fonts.googleapis.com">
  12 | <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  13 | <link rel="preload" href="/oracle/thinking" as="video" type="video/mp4">
  14 | <style>
  15 | *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  16 | html,body{height:100%;width:100%;background:#000;overflow:hidden;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
  17 | 
  18 | /* ─── KEYFRAMES ─────────────────────────────────────────── */
  19 | @keyframes orbit{to{transform:rotate(360deg)}}
  20 | @keyframes orbit-rev{to{transform:rotate(-360deg)}}
  21 | @keyframes breathe{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.04)}}
  22 | @keyframes scan{0%{top:-4px}100%{top:100%}}
  23 | @keyframes live-blink{0%,100%{opacity:1}49%{opacity:1}50%,99%{opacity:.15}}
  24 | @keyframes fade-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  25 | @keyframes mic-pulse{0%{box-shadow:0 0 0 0 rgba(255,59,95,.6)}70%{box-shadow:0 0 0 22px rgba(255,59,95,0)}100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}}
  26 | @keyframes mic-idle-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}50%{box-shadow:0 0 0 14px rgba(255,59,95,.22),0 0 18px 4px rgba(255,59,95,.12)}}
  27 | @keyframes spin{to{transform:rotate(360deg)}}
  28 | @keyframes card-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  29 | @keyframes hex-glow{0%,100%{filter:drop-shadow(0 0 8px rgba(255,59,95,.4))}50%{filter:drop-shadow(0 0 22px rgba(255,59,95,.9))}}
  30 | 
  31 | /* ─── ROOT ──────────────────────────────────────────────── */
  32 | #root{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
  33 | 
  34 | /* ─── BACKGROUND GRID ───────────────────────────────────── */
  35 | #root::before{
  36 |   content:'';position:absolute;inset:0;
  37 |   background-image:linear-gradient(rgba(255,59,95,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,59,95,.04) 1px,transparent 1px);
  38 |   background-size:40px 40px;
  39 |   mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,black 40%,transparent 100%);
  40 |   pointer-events:none;
  41 | }
  42 | 
  43 | /* ═══════════════════════════════════════════════════════════
  44 |    GATE SCREEN
  45 | ═══════════════════════════════════════════════════════════ */
  46 | #gate{
  47 |   display:flex;flex-direction:column;align-items:center;
  48 |   gap:clamp(18px,4vw,28px);
  49 |   padding:clamp(24px,5vw,48px) clamp(24px,5vw,48px);
  50 |   width:100%;max-width:520px;
  51 |   transition:opacity .35s ease;
  52 | }
  53 | 
  54 | /* Satomi sigil */
  55 | .sigil-wrap{
  56 |   position:relative;
  57 |   width:clamp(140px,38vw,200px);
  58 |   height:clamp(140px,38vw,200px);
  59 |   flex-shrink:0;
  60 | }
  61 | /* Rotating rings */
  62 | .ring{
  63 |   position:absolute;inset:0;
  64 |   border-radius:50%;
  65 |   border:1px solid rgba(255,59,95,.25);
  66 | }
  67 | .ring-1{animation:orbit 12s linear infinite}
  68 | .ring-1::before{
  69 |   content:'';position:absolute;
  70 |   width:6px;height:6px;background:#ff3b5f;border-radius:50%;
  71 |   top:-3px;left:50%;transform:translateX(-50%);
  72 |   box-shadow:0 0 8px #ff3b5f;
  73 | }
  74 | .ring-2{
  75 |   inset:12%;border-color:rgba(255,180,50,.2);
  76 |   animation:orbit-rev 8s linear infinite;
  77 | }
  78 | .ring-2::before{
  79 |   content:'';position:absolute;
  80 |   width:4px;height:4px;background:#f8c15c;border-radius:50%;
  81 |   bottom:-2px;left:50%;transform:translateX(-50%);
  82 |   box-shadow:0 0 6px #f8c15c;
  83 | }
  84 | /* Avatar in center */
  85 | .sigil-avatar{
  86 |   position:absolute;
  87 |   inset:18%;
  88 |   border-radius:50%;
  89 |   overflow:hidden;
  90 |   background:radial-gradient(circle,#1a0608 0%,#050203 100%);
  91 |   border:1px solid rgba(255,59,95,.3);
  92 |   animation:breathe 3.5s ease-in-out infinite;
  93 | }
  94 | .sigil-avatar img{width:100%;height:100%;object-fit:cover;display:block;border-radius:50%}
  95 | .sigil-fallback{
  96 |   width:100%;height:100%;border-radius:50%;
  97 |   display:flex;align-items:center;justify-content:center;
  98 |   font-size:clamp(28px,8vw,44px);
  99 |   background:radial-gradient(circle,#2a0810 0%,#080205 100%);
 100 | }
 101 | /* Scan line */
 102 | .sigil-scan{
 103 |   position:absolute;inset:18%;border-radius:50%;overflow:hidden;pointer-events:none;
 104 | }
 105 | .sigil-scan::after{
 106 |   content:'';position:absolute;left:0;right:0;height:2px;
 107 |   background:linear-gradient(90deg,transparent,rgba(255,59,95,.6),transparent);
 108 |   animation:scan 2.5s ease-in-out infinite;
 109 | }
 110 | 
 111 | /* Wordmark */
 112 | .gate-brand{
 113 |   font-size:10px;font-weight:700;
 114 |   letter-spacing:.4em;color:rgba(255,59,95,.7);
 115 |   text-transform:uppercase;
 116 | }
 117 | 
 118 | /* Title */
 119 | .gate-title{
 120 |   font-size:clamp(32px,9vw,52px);
 121 |   font-weight:900;color:#fff;
 122 |   letter-spacing:-.03em;line-height:1;
 123 |   text-align:center;
 124 | }
 125 | .gate-title span{color:#ff3b5f}
 126 | 
 127 | /* Sub */
 128 | .gate-sub{
 129 |   font-size:clamp(13px,3.5vw,15px);
 130 |   color:#556;
 131 |   text-align:center;line-height:1.6;
 132 |   max-width:300px;
 133 |   font-weight:400;
 134 | }
 135 | 
 136 | /* ─── THE BUTTON ─────────────────────────────────────────── */
 137 | #gate-btn{
 138 |   position:relative;
 139 |   background:transparent;
 140 |   border:none;cursor:pointer;
 141 |   padding:0;
 142 |   width:clamp(200px,55vw,280px);
 143 |   -webkit-appearance:none;
 144 |   touch-action:manipulation;
 145 | }
 146 | #gate-btn:disabled{opacity:.4;cursor:not-allowed}
 147 | #gate-btn:active .btn-inner{transform:scale(.97)}
 148 | 
 149 | .btn-inner{
 150 |   position:relative;overflow:hidden;
 151 |   background:linear-gradient(135deg,#1a0508 0%,#0d0203 100%);
 152 |   border:1px solid rgba(255,59,95,.5);
 153 |   border-radius:4px;
 154 |   padding:clamp(14px,4vw,18px) clamp(20px,5vw,32px);
 155 |   transition:transform .1s,border-color .2s;
 156 |   display:flex;flex-direction:column;align-items:center;gap:6px;
 157 | }
 158 | #gate-btn:not(:disabled):hover .btn-inner{border-color:rgba(255,59,95,.9)}
 159 | 
 160 | /* Top label */
 161 | .btn-label{
 162 |   font-family:'JetBrains Mono',monospace;
 163 |   font-size:9px;letter-spacing:.35em;
 164 |   color:rgba(255,59,95,.6);text-transform:uppercase;
 165 | }
 166 | /* Main text */
 167 | .btn-text{
 168 |   font-size:clamp(13px,4vw,16px);font-weight:700;
 169 |   color:#fff;letter-spacing:.05em;text-transform:uppercase;
 170 |   display:flex;align-items:center;gap:10px;
 171 | }
 172 | .btn-mic-icon{
 173 |   width:16px;height:16px;flex-shrink:0;
 174 |   opacity:.9;
 175 | }
 176 | /* Corner accents */
 177 | .btn-inner::before,.btn-inner::after{
 178 |   content:'';position:absolute;width:8px;height:8px;
 179 |   border-color:rgba(255,59,95,.6);border-style:solid;
 180 | }
 181 | .btn-inner::before{top:4px;left:4px;border-width:1px 0 0 1px}
 182 | .btn-inner::after{bottom:4px;right:4px;border-width:0 1px 1px 0}
 183 | /* Glow sweep on hover */
 184 | .btn-sweep{
 185 |   position:absolute;inset:0;
 186 |   background:linear-gradient(105deg,transparent 40%,rgba(255,59,95,.06) 50%,transparent 60%);
 187 |   transform:translateX(-100%);
 188 |   transition:transform .5s ease;
 189 | }
 190 | #gate-btn:not(:disabled):hover .btn-sweep{transform:translateX(100%)}
 191 | 
 192 | /* Status line below btn */
 193 | #gate-status{
 194 |   font-family:'JetBrains Mono',monospace;
 195 |   font-size:11px;color:#334;letter-spacing:.08em;
 196 |   min-height:16px;text-align:center;
 197 | }
 198 | #gate-error{
 199 |   display:none;font-size:12px;color:#ff3b5f;
 200 |   text-align:center;line-height:1.5;max-width:280px;
 201 |   background:rgba(255,59,95,.06);border:1px solid rgba(255,59,95,.15);
 202 |   border-radius:4px;padding:8px 12px;
 203 | }
 204 | 
 205 | /* ═══════════════════════════════════════════════════════════
 206 |    LIVE STAGE
 207 | ═══════════════════════════════════════════════════════════ */
 208 | #stage{
 209 |   display:none;flex-direction:column;align-items:center;
 210 |   position:relative;
 211 |   width:100%;height:100%;
 212 |   padding:clamp(8px,2.5vw,14px) clamp(12px,3.5vw,20px) clamp(10px,3vw,16px);
 213 |   gap:clamp(6px,1.5vw,10px);
 214 |   overflow-y:auto;-webkit-overflow-scrolling:touch;
 215 |   animation:fade-up .4s ease;
 216 | }
 217 | 
 218 | /* Top bar */
 219 | .topbar{
 220 |   width:100%;display:flex;align-items:center;
 221 |   justify-content:space-between;flex-shrink:0;
 222 | }
 223 | /* Exit and minimize buttons */
 224 | .stage-controls{display:flex;align-items:center;gap:8px}
 225 | #minimize-btn,#exit-btn{
 226 |   width:28px;height:28px;border-radius:50%;
 227 |   background:transparent;border:1px solid #1e2235;
 228 |   cursor:pointer;display:flex;align-items:center;justify-content:center;
 229 |   transition:border-color .15s,background .15s;
 230 |   -webkit-appearance:none;touch-action:manipulation;flex-shrink:0;
 231 |   opacity:0.5;
 232 | }
 233 | #minimize-btn:hover,#exit-btn:hover{opacity:1;border-color:#556;background:#0f1117}
 234 | #exit-btn:hover{border-color:rgba(255,59,95,.5)}
 235 | 
 236 | /* ── FLOATING MINI MODE ─────────────────────────────────────────── */
 237 | @keyframes mini-in{from{opacity:0;transform:scale(.6) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}
 238 | @keyframes mini-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,.4)}70%{box-shadow:0 0 0 8px rgba(255,59,95,0)}}
 239 | 
 240 | #oracle-float{
 241 |   position:fixed;bottom:24px;right:24px;
 242 |   width:72px;height:72px;border-radius:50%;
 243 |   background:#0a0b0f;border:2px solid rgba(255,59,95,.6);
 244 |   cursor:pointer;z-index:9999;
 245 |   display:none;align-items:center;justify-content:center;
 246 |   animation:mini-in .3s ease, mini-pulse 2s ease-in-out infinite;
 247 |   box-shadow:0 4px 20px rgba(0,0,0,.6);
 248 |   overflow:hidden;transition:transform .15s;
 249 | }
 250 | #oracle-float:hover{transform:scale(1.08)}
 251 | #oracle-float:active{transform:scale(.95)}
 252 | #oracle-float img{width:100%;height:100%;object-fit:cover;border-radius:50%}
 253 | #oracle-float-fallback{font-size:28px}
 254 | /* Speaking ring on float */
 255 | #oracle-float.speaking{border-color:#6cff9f;animation:mini-pulse 0.8s ease-in-out infinite}
 256 | /* Tooltip */
 257 | #oracle-float::after{
 258 |   content:"Talk to Satomi";
 259 |   position:absolute;right:80px;
 260 |   background:#0f1117;border:1px solid #1e2235;border-radius:4px;
 261 |   padding:4px 8px;font-family:'JetBrains Mono',monospace;font-size:10px;
 262 |   color:#b8c2d9;white-space:nowrap;pointer-events:none;
 263 |   opacity:0;transition:opacity .2s;
 264 | }
 265 | #oracle-float:hover::after{opacity:1}
 266 | .topbar-brand{
 267 |   font-family:'JetBrains Mono',monospace;
 268 |   font-size:10px;font-weight:500;
 269 |   letter-spacing:.3em;color:rgba(255,59,95,.7);text-transform:uppercase;
 270 | }
 271 | .live-pill{
 272 |   display:flex;align-items:center;gap:5px;
 273 |   background:rgba(74,222,128,.06);
 274 |   border:1px solid rgba(74,222,128,.2);
 275 |   border-radius:20px;padding:3px 8px;
 276 | }
 277 | .live-dot{
 278 |   width:5px;height:5px;border-radius:50%;background:#4ade80;
 279 |   animation:live-blink 2s step-end infinite;
 280 | }
 281 | .live-text{
 282 |   font-family:'JetBrains Mono',monospace;
 283 |   font-size:9px;font-weight:500;color:#4ade80;letter-spacing:.15em;
 284 | }
 285 | 
 286 | /* Video */
 287 | .video-wrap{
 288 |   position:relative;
 289 |   width:100%;
 290 |   max-width:min(440px,calc(100vw - 24px));
 291 |   aspect-ratio:1/1;
 292 |   border-radius:8px;overflow:hidden;
 293 |   background: #050508;
 294 |   overflow: hidden;
 295 |   flex-shrink:0;
 296 |   min-height: min(440px, calc(100vw - 24px));
 297 | }
 298 | /* Corner brackets */
 299 | .video-wrap::before,.video-wrap::after{
 300 |   content:'';position:absolute;width:16px;height:16px;
 301 |   border-color:rgba(255,59,95,.4);border-style:solid;z-index:2;
 302 | }
 303 | .video-wrap::before{top:6px;left:6px;border-width:1px 0 0 1px}
 304 | .video-wrap::after{bottom:6px;right:6px;border-width:0 1px 1px 0}
 305 | 
 306 | #vid{width:100%;height:100%;object-fit:cover;object-position:center top;display:block}
 307 | /* Subtitle */
 308 | #subtitle{
 309 |   width:100%;
 310 |   font-family:'JetBrains Mono',monospace;
 311 |   font-size:clamp(11px,3vw,13px);color:#f8c15c;
 312 |   line-height:1.55;text-align:center;
 313 |   min-height:34px;
 314 |   opacity:0;transition:opacity .3s;
 315 |   display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
 316 |   overflow:hidden;padding:0 4px;
 317 | }
 318 | #subtitle.on{opacity:1}
 319 | 
 320 | /* Status */
 321 | #stat{
 322 |   font-family:'JetBrains Mono',monospace;
 323 |   font-size:clamp(10px,2.8vw,12px);
 324 |   color:#334;display:flex;align-items:center;gap:6px;
 325 |   height:18px;transition:color .2s;flex-shrink:0;
 326 | }
 327 | .spin{width:12px;height:12px;border:1.5px solid currentColor;border-top-color:transparent;border-radius:50%;display:none;animation:spin .6s linear infinite;flex-shrink:0}
 328 | 
 329 | /* Transcript */
 330 | #tx{
 331 |   font-family:'JetBrains Mono',monospace;
 332 |   font-size:clamp(10px,2.8vw,11px);color:#445;font-style:italic;
 333 |   min-height:16px;text-align:center;
 334 |   opacity:0;transition:opacity .2s;
 335 |   width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;
 336 | }
 337 | #tx.on{opacity:1}
 338 | 
 339 | /* Mic */
 340 | .mic-area{display:flex;flex-direction:column;align-items:center;gap:7px;flex-shrink:0}
 341 | #mic{
 342 |   width:clamp(60px,15vw,72px);height:clamp(60px,15vw,72px);
 343 |   border-radius:50%;
 344 |   background:#0a0c12;
 345 |   border:1.5px solid #ff3b5f;
 346 |   cursor:pointer;
 347 |   display:flex;align-items:center;justify-content:center;
 348 |   transition:background .15s,transform .1s;
 349 |   -webkit-appearance:none;touch-action:manipulation;
 350 |   flex-shrink:0;
 351 | }
 352 | #mic:active:not(:disabled){transform:scale(.92)}
 353 | #mic:disabled{opacity:.2;cursor:not-allowed}
 354 | #mic.rec{background:#ff3b5f;animation:mic-pulse 1s ease-out infinite}
 355 | #mic.idle-pulse{border-color:#ff3b5f;border-width:2px;animation:mic-idle-pulse 1.8s ease-in-out 3}
 356 | .mic-hint{font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.12em;text-transform:uppercase}
 357 | #cam-btn{
 358 |   width:42px;height:42px;border-radius:50%;background:#0a0c12;
 359 |   border:1.5px solid #334;cursor:pointer;
 360 |   display:flex;align-items:center;justify-content:center;
 361 |   transition:border-color .15s;-webkit-appearance:none;touch-action:manipulation;
 362 |   flex-shrink:0;
 363 | }
 364 | #cam-btn:hover{border-color:#f8c15c}
 365 | #cam-btn.active{border-color:#f8c15c;background:#1a1500}
 366 | #cam-input{display:none}
 367 | #vision-status{
 368 |   font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;
 369 |   text-align:center;opacity:0;transition:opacity .3s;min-height:14px;
 370 | }
 371 | #vision-status.on{opacity:1}
 372 | 
 373 | /* Sovereignty cards */
 374 | #cards{display:none;grid-template-columns:1fr 1fr;gap:8px;width:100%;animation:card-up .35s ease;position:relative;z-index:0}
 375 | #cards.on{display:grid}
 376 | .card{
 377 |   background:#080a0f;
 378 |   border:1px solid #141824;
 379 |   border-radius:6px;
 380 |   padding:clamp(10px,2.5vw,13px);
 381 |   cursor:pointer;
 382 |   transition:border-color .15s,background .15s;
 383 |   display:flex;flex-direction:column;gap:5px;
 384 |   touch-action:manipulation;
 385 | }
 386 | .card:active{background:#100610;border-color:rgba(255,59,95,.5)}
 387 | .card-title{font-size:clamp(11px,3.2vw,13px);font-weight:600;color:#ccd;line-height:1.3}
 388 | .card-link{font-family:'JetBrains Mono',monospace;font-size:clamp(9px,2.5vw,10px);color:rgba(255,59,95,.7);text-decoration:none;letter-spacing:.03em}
 389 | 
 390 | /* ═══════════════════════════════════════════════════════════
 391 |    MOBILE — max-width 640px
 392 | ═══════════════════════════════════════════════════════════ */
 393 | /* ═══════════════════════════════════════════════════════════
 394 |    TABLET — max-width 768px
 395 | ═══════════════════════════════════════════════════════════ */
 396 | @media(max-width:768px){
 397 |   body{padding-top:48px}
 398 |   .video-wrap{
 399 |     max-width:100%;
 400 |     margin:0 auto;
 401 |   }
 402 |   #vid{
 403 |     width:100%;
 404 |     max-width:100%;
 405 |     display:block;
 406 |     margin:0 auto;
 407 |   }
 408 |   #cards{grid-template-columns:1fr 1fr}
 409 |   .card{min-height:48px}
 410 |   #mic{min-width:48px;min-height:48px}
 411 |   #cam-btn{min-width:48px;min-height:48px}
 412 |   #gate-btn{min-height:48px}
 413 |   #root{padding-bottom:80px}
 414 | }
 415 | 
 416 | @media(max-width:640px){
 417 |   body{position:fixed;width:100%;overflow:hidden}
 418 |   #root{position:relative;height:100dvh}
 419 |   /* Stage: full viewport, vertical stack, no overflow leak */
 420 |   #stage{
 421 |     height:100vh;height:100dvh;
 422 |     padding:8px 10px 0;
 423 |     gap:6px;
 424 |     overflow:hidden;
 425 |     display:none;flex-direction:column;
 426 |   }
 427 | 
 428 |   /* Topbar: compact for 375px screens */
 429 |   .topbar{
 430 |     padding:0;
 431 |     min-height:28px;
 432 |     flex-shrink:0;
 433 |   }
 434 |   .topbar-brand{font-size:9px;letter-spacing:.25em}
 435 |   .live-pill{padding:2px 6px}
 436 |   .live-text{font-size:8px}
 437 |   .stage-controls{gap:4px}
 438 |   #minimize-btn,#exit-btn{width:26px;height:26px}
 439 | 
 440 |   /* Video: constrain to 60vh max, centered */
 441 |   .video-wrap{
 442 |     max-height:60vh;
 443 |     max-width:calc(100vw - 20px);
 444 |     width:100%;
 445 |     aspect-ratio:1/1;
 446 |     margin:0 auto;
 447 |     flex-shrink:1;
 448 |     min-height:0;
 449 |   }
 450 |   #vid{
 451 |     width:100%;
 452 |     height:100%;
 453 |     max-width:340px;
 454 |     margin:0 auto;
 455 |     display:block;
 456 |     border-radius:8px;
 457 |     object-fit:cover;
 458 |   }
 459 | 
 460 |   /* Subtitle: tighter */
 461 |   #subtitle{
 462 |     font-size:11px;
 463 |     min-height:28px;
 464 |     padding:0 2px;
 465 |     flex-shrink:0;
 466 |   }
 467 | 
 468 |   /* Status + transcript: compact */
 469 |   #stat{font-size:10px;height:16px;flex-shrink:0}
 470 |   #tx{font-size:10px;min-height:14px;flex-shrink:0}
 471 | 
 472 |   /* Mic area + input controls: sticky to bottom, full width, tap-friendly */
 473 |   .mic-area{
 474 |     width:100%;
 475 |     flex-shrink:0;
 476 |     padding-bottom:env(safe-area-inset-bottom,8px);
 477 |     margin-top:auto;
 478 |   }
 479 |   #mic{
 480 |     width:60px;height:60px;
 481 |     min-width:48px;min-height:48px;
 482 |   }
 483 |   .mic-hint{font-size:9px}
 484 | 
 485 |   /* Camera button: 48px touch target */
 486 |   #cam-btn{
 487 |     width:48px;height:48px;
 488 |     min-width:48px;min-height:48px;
 489 |   }
 490 | 
 491 |   /* Vision status */
 492 |   #vision-status{font-size:9px;min-height:12px}
 493 | 
 494 |   /* Cards grid: 1 column on mobile */
 495 |   #cards{grid-template-columns:1fr}
 496 |   #cards.on{
 497 |     display:grid;
 498 |     max-height:30vh;
 499 |     overflow-y:auto;
 500 |     -webkit-overflow-scrolling:touch;
 501 |   }
 502 |   .card{
 503 |     padding:10px;
 504 |     min-height:48px;
 505 |     display:flex;flex-direction:row;align-items:center;
 506 |     gap:8px;
 507 |   }
 508 |   .card-title{font-size:13px}
 509 |   .card-link{font-size:10px}
 510 | 
 511 |   /* Gate: ensure it fits small screens */
 512 |   #gate{
 513 |     padding:20px 16px;
 514 |     gap:16px;
 515 |   }
 516 |   .sigil-wrap{width:130px;height:130px}
 517 |   .gate-title{font-size:32px}
 518 |   .gate-sub{font-size:13px;max-width:260px}
 519 |   #gate-btn{width:220px}
 520 |   .btn-inner{padding:14px 20px}
 521 |   #gate-status{font-size:10px}
 522 |   #gate-error{font-size:11px;max-width:260px}
 523 | 
 524 |   /* Float bubble: smaller on mobile */
 525 |   #oracle-float{
 526 |     width:56px;height:56px;
 527 |     bottom:16px;right:16px;
 528 |   }
 529 | }
 530 | 
 531 | /* ── STUDIO TREATMENT (oracle-live only) ─────────── */
 532 | .video-wrap {
 533 |   border: 2px solid rgba(220,38,38,0.4);
 534 |   box-shadow: 0 0 40px rgba(220,38,38,0.15);
 535 | }
 536 | #oracle-matrix { pointer-events: none; }
 537 | 
 538 | /* ── VISION TRANSCRIPT ─────────────────────────── */
 539 | .vision-entry {
 540 |   padding: 10px 14px;
 541 |   border-bottom: 1px solid rgba(255,255,255,.04);
 542 |   cursor: pointer;
 543 | }
 544 | .vision-entry:hover { background: rgba(255,255,255,.03); }
 545 | .vision-entry:last-child { border-bottom: none; }
 546 | .vision-entry-device {
 547 |   font-family: monospace;
 548 |   font-size: 10px;
 549 |   letter-spacing: .1em;
 550 |   color: rgba(255,59,95,.7);
 551 |   text-transform: uppercase;
 552 |   margin-bottom: 4px;
 553 | }
 554 | .vision-entry-step {
 555 |   font-size: 0.8rem;
 556 |   color: rgba(255,255,255,.7);
 557 |   line-height: 1.5;
 558 |   margin: 2px 0;
 559 | }
 560 | .vision-entry-time {
 561 |   font-family: monospace;
 562 |   font-size: 9px;
 563 |   color: rgba(255,255,255,.2);
 564 |   margin-top: 4px;
 565 | }
 566 | </style>
 567 | </head>
 568 | <body>
 569 | <div id="vision-security-overlay" style="display:none;position:fixed;inset:0;
 570 | z-index:99999;background:rgba(180,0,0,0.97);flex-direction:column;
 571 | align-items:center;justify-content:center;padding:32px;text-align:center;">
 572 |   <div style="font-size:64px;margin-bottom:16px;">⚠️</div>
 573 |   <div style="font-family:monospace;font-size:13px;letter-spacing:.12em;
 574 | color:rgba(255,255,255,.6);margin-bottom:8px;text-transform:uppercase;">
 575 | SECURITY ALERT</div>
 576 |   <div id="vision-security-msg" style="font-size:1.2rem;font-weight:700;
 577 | color:#fff;margin-bottom:32px;line-height:1.5;max-width:340px;"></div>
 578 |   <button id="vision-security-dismiss"
 579 |     style="background:#fff;color:#b40000;font-family:monospace;font-weight:800;
 580 | font-size:14px;letter-spacing:.1em;border:none;border-radius:8px;
 581 | padding:16px 32px;cursor:pointer;text-transform:uppercase;
 582 | min-height:56px;width:100%;max-width:320px;">
 583 |     ✓ GOT IT — COVER NOW
 584 |   </button>
 585 |   <div id="vision-recovery-panel" style="display:none;width:100%;
 586 | max-width:340px;margin-top:24px;">
 587 |     <div style="font-family:monospace;font-size:11px;letter-spacing:.12em;
 588 | color:rgba(255,255,255,.5);margin-bottom:12px;text-transform:uppercase;">
 589 | YOUR FUNDS MAY BE AT RISK — ACT NOW</div>
 590 |     <div id="vision-recovery-step-label" style="font-family:monospace;
 591 | font-size:11px;color:rgba(255,200,0,.8);letter-spacing:.1em;
 592 | margin-bottom:8px;text-transform:uppercase;">STEP 1 OF 3</div>
 593 |     <div id="vision-recovery-step-text" style="font-size:1rem;
 594 | font-weight:600;color:#fff;line-height:1.6;margin-bottom:24px;"></div>
 595 |     <button id="vision-recovery-next"
 596 |       style="background:rgba(255,255,255,.15);color:#fff;
 597 | font-family:monospace;font-weight:700;font-size:13px;
 598 | letter-spacing:.08em;border:2px solid rgba(255,255,255,.3);
 599 | border-radius:8px;padding:14px 24px;cursor:pointer;
 600 | text-transform:uppercase;min-height:52px;width:100%;">
 601 |       NEXT STEP →
 602 |     </button>
 603 |     <button id="vision-recovery-help"
 604 |       style="display:none;background:#fff;color:#b40000;
 605 | font-family:monospace;font-weight:800;font-size:13px;
 606 | letter-spacing:.08em;border:none;border-radius:8px;
 607 | padding:14px 24px;cursor:pointer;text-transform:uppercase;
 608 | min-height:52px;width:100%;margin-top:8px;">
 609 |       HELP ME SET UP NEW WALLET
 610 |     </button>
 611 |     <button id="vision-recovery-close"
 612 |       style="display:none;background:none;color:rgba(255,255,255,.4);
 613 | font-family:monospace;font-size:11px;letter-spacing:.08em;
 614 | border:none;padding:12px;cursor:pointer;text-transform:uppercase;
 615 | width:100%;margin-top:4px;">
 616 |       I UNDERSTAND THE RISK — CLOSE
 617 |     </button>
 618 |   </div>
 619 | </div>
 620 | <div id="mobile-nav-bar" style="display:none;position:fixed;top:0;left:0;right:0;z-index:9998;background:rgba(4,5,10,.95);padding:10px 16px;border-bottom:1px solid rgba(255,59,95,.15);align-items:center;gap:12px;">
 621 |   <button onclick="window.history.back()" style="background:none;border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.6);padding:6px 14px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;letter-spacing:.08em;">&larr; BACK</button>
 622 |   <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,59,95,.8);letter-spacing:.15em;">ORACLE &mdash; PROTOCOL PULSE</span>
 623 | </div>
 624 | <div id="root">
 625 | 
 626 | <!-- ══ GATE ══ -->
 627 | <div id="gate">
 628 |   <div class="gate-brand">Protocol Pulse</div>
 629 | 
 630 |   <div class="sigil-wrap">
 631 |     <div class="ring ring-1"></div>
 632 |     <div class="ring ring-2"></div>
 633 |     <div class="sigil-avatar" style="position:relative;">
 634 |       <img src="/static/oracle_avatar.png" alt="Satomi" id="avatar-fallback" style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:0;border-radius:inherit;opacity:1;"  />
 635 |       <img src="/static/oracle_avatar.png" alt="Satomi"
 636 |            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 637 |       <div class="sigil-fallback" style="display:none">⚡</div>
 638 |     </div>
 639 |     <div class="sigil-scan"></div>
 640 |   </div>
 641 | 
 642 |   <h1 class="gate-title">THE <span>SATOMI</span></h1>
 643 |   <p class="gate-sub">Sovereign Bitcoin intelligence.<br>Ask anything, in real time.</p>
 644 | 
 645 |   <button id="gate-btn" onclick="requestMic()">
 646 |     <div class="btn-sweep"></div>
 647 |     <div class="btn-inner">
 648 |       <div class="btn-label">Protocol Pulse Intelligence</div>
 649 |       <div class="btn-text">
 650 |         <svg class="btn-mic-icon" viewBox="0 0 24 24" fill="none">
 651 |           <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 652 |           <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 653 |           <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 654 |         </svg>
 655 |         Speak to Satomi
 656 |       </div>
 657 |     </div>
 658 |   </button>
 659 | 
 660 |   <div id="gate-status">— tap to activate —</div>
 661 |   <div id="gate-error"></div>
 662 | </div>
 663 | 
 664 | <!-- ══ LIVE STAGE ══ -->
 665 | <div id="stage">
 666 | 
 667 |   <div class="topbar">
 668 |     <span class="topbar-brand">Satomi</span>
 669 |     <div class="live-pill"><div class="live-dot"></div><span class="live-text">LIVE</span></div>
 670 |     <a href="/" style="margin-left:auto;color:rgba(255,255,255,0.3);font-size:22px;text-decoration:none;padding:4px 10px;line-height:1;transition:color 0.2s;" onmouseover="this.style.color='rgba(255,255,255,0.8)'" onmouseout="this.style.color='rgba(255,255,255,0.3)'" aria-label="Exit Satomi" title="Go to homepage">&times;</a>
 671 |   </div>
 672 | 
 673 |   <canvas id="bg-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;will-change:transform;"></canvas>
 674 | 
 675 |   <div class="video-wrap" style="position:relative;z-index:1;">
 676 |     <!-- P0-1: Static avatar always visible behind video — never black screen -->
 677 |     <img id="avatar-idle" src="/static/oracle_avatar.png" alt="Satomi"
 678 |          style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;border-radius:8px;"
 679 |          onerror="this.style.background='radial-gradient(circle,#1a0608,#050203)'">
 680 |     <canvas id="oracle-matrix" style="position:absolute;inset:0;width:100%;height:100%;z-index:1;opacity:1;transition:opacity 0.5s;"></canvas>
 681 |     <video id="vid" playsinline webkit-playsinline x-webkit-airplay="allow" preload="auto" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;z-index:2;"></video>
 682 |   </div>
 683 | 
 684 |   <div id="subtitle"></div>
 685 |   <div id="oracle-action-card" style="display:none;margin-top:12px;max-width:min(440px,calc(100vw - 24px));width:100%;"></div>
 686 | 
 687 |   <div id="stat">
 688 |     <span class="spin" id="spin"></span>
 689 |     <span id="stat-text">Ready</span>
 690 |   </div>
 691 | 
 692 |   <div id="tx"></div>
 693 | 
 694 |   <div class="mic-area">
 695 |     <button id="mic" disabled onclick="toggleMic()">
 696 |       <svg id="i-mic" width="24" height="24" viewBox="0 0 24 24" fill="none">
 697 |         <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 698 |         <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 699 |         <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 700 |         <line x1="9" y1="22" x2="15" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 701 |       </svg>
 702 |       <svg id="i-stop" width="24" height="24" viewBox="0 0 24 24" fill="none" style="display:none">
 703 |         <rect x="6" y="6" width="12" height="12" rx="2" fill="#fff"/>
 704 |       </svg>
 705 |     </button>
 706 |     <span class="mic-hint" id="mic-hint">tap to speak</span>
 707 |   </div>
 708 | 
 709 |   <!-- Vision status + Camera button -->
 710 |   <div id="vision-status"></div>
 711 |   <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
 712 |     <button id="cam-btn" onclick="triggerCamera()" title="Show Satomi your screen — she will guide you step by step">
 713 |       <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
 714 |         <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="#556" stroke-width="1.5" stroke-linecap="round"/>
 715 |         <circle cx="12" cy="13" r="4" stroke="#556" stroke-width="1.5"/>
 716 |       </svg>
 717 |     </button>
 718 |     <span id="cam-btn-label" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.08em">ANALYZE HARDWARE</span>
 719 |   </div>
 720 |   <div id="vision-transcript-panel" style="display:none;
 721 |   width:100%;max-width:min(440px,calc(100vw - 24px));
 722 |   margin:12px auto 0;background:rgba(6,7,14,.9);
 723 |   border:1px solid rgba(255,59,95,.15);border-radius:8px;
 724 |   overflow:hidden;">
 725 |     <div style="display:flex;align-items:center;justify-content:space-between;
 726 |   padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);">
 727 |       <span style="font-family:monospace;font-size:10px;letter-spacing:.12em;
 728 |   color:rgba(255,59,95,.8);text-transform:uppercase;">SESSION LOG</span>
 729 |       <button id="vision-transcript-clear"
 730 |         style="background:none;border:none;color:rgba(255,255,255,.3);
 731 |   font-family:monospace;font-size:9px;letter-spacing:.08em;
 732 |   cursor:pointer;text-transform:uppercase;padding:2px 6px;">
 733 |         CLEAR
 734 |       </button>
 735 |     </div>
 736 |     <div id="vision-transcript-entries" style="max-height:280px;
 737 |   overflow-y:auto;padding:8px 0;"></div>
 738 |   </div>
 739 | 
 740 |   <input type="file" id="cam-input" accept="image/*" capture="environment" onchange="handleVisionUpload(event)">
 741 | 
 742 |   <div id="cards">
 743 |     <div class="card" onclick="si('SOVEREIGNTY_COLD_WALLET')">
 744 |       <div class="card-title">&#128272; Self-Custody</div>
 745 |       <a class="card-link" href="https://coldcard.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">coldcard.com &#8594;</a>
 746 |     </div>
 747 |     <div class="card" onclick="si('SOVEREIGNTY_NODE')">
 748 |       <div class="card-title">&#9889; Run a Node</div>
 749 |       <a class="card-link" href="https://getumbrel.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">getumbrel.com &#8594;</a>
 750 |     </div>
 751 |     <div class="card" onclick="si('SOVEREIGNTY_BITAXE')">
 752 |       <div class="card-title">&#9935; Solo Mining</div>
 753 |       <a class="card-link" href="https://curatedmining.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">curatedmining.com &#8594;</a>
 754 |     </div>
 755 |     <div class="card" onclick="si('SOVEREIGNTY_LIFE_INSURANCE')">
 756 |       <div class="card-title">&#128737; BTC Insurance</div>
 757 |       <a class="card-link" href="https://application.meanwhile.bm/start?referralCode=KKM73K" target="_blank" rel="noopener" onclick="event.stopPropagation()">meanwhile.bm &#8594;</a>
 758 |     </div>
 759 |   </div>
 760 | 
 761 | </div><!-- /stage -->
 762 | </div><!-- /root -->
 763 | 
 764 | <script>
 765 | 'use strict';
 766 | /* ── iOS zoom prevention ── */
 767 | document.addEventListener('gesturestart',function(e){e.preventDefault();},{passive:false});
 768 | document.addEventListener('touchmove',function(e){if(e.touches.length>1)e.preventDefault();},{passive:false});
 769 | var A='https://avatar.protocolpulse.io';
 770 | var S={
 771 |   GREETING:"Hey. I'm Satomi — your Protocol Pulse intelligence anchor. On-chain, macro, geopolitical. What can I help you with?",
 772 |   SOVEREIGNTY_INTRO:"Your sovereignty score is a snapshot of how free you actually are — how much of your financial life you've pulled out of legacy systems.",
 773 |   SOVEREIGNTY_ASSESSMENT:"Four pillars: self-custody of your Bitcoin, your own node, private comms, and no KYC on your income. Where are you today?",
 774 |   SOVEREIGNTY_COLD_WALLET:"If your Bitcoin is on an exchange, it's not yours — it's an IOU. A hardware wallet fixes that. I can walk you through it.",
 775 |   SOVEREIGNTY_NODE:"Running your own node means you verify your own transactions. You don't trust, you verify. Umbrel on a Pi is the easiest path.",
 776 |   SOVEREIGNTY_BITAXE:"Bitaxe is a solo miner you can run at home. A Bitcoin lottery ticket. Curated Mining also does white-glove setup.",
 777 |   SOVEREIGNTY_LIFE_INSURANCE:"If you die with Bitcoin in cold storage and nobody knows the seed phrase, it's gone. Meanwhile offers life insurance that actually understands Bitcoin.",
 778 |   SOVEREIGNTY_RESIDENCY:"Digital residency through Palau via RNS.ID gives you a second legal identity outside your home country. Real tax and privacy implications.",
 779 |   DAILY_BRIEF_INTRO:"Here's what's moving in Bitcoin right now. Pulling the latest from our intelligence layer...",
 780 |   DAILY_BRIEF_LIVE:"Here's today's Bitcoin intelligence brief.",
 781 |   UNKNOWN_QUESTION:"I'm researching that now. One moment.",
 782 |   GOODBYE:"Stack sats, verify everything, and come back anytime."
 783 | };
 784 | 
 785 | var busy=false,isRec=false,pending='',objURL=null,recognition=null;
 786 | var _greeted=false;
 787 | 
 788 | /* ── ORACLE STATE MACHINE ──
 789 |    States: WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING
 790 |    Every state shows the avatar face (never black screen).
 791 |    LISTENING: mic active, avatar static idle visible, status "Ready"
 792 |    PROCESSING: mic off, spinner, avatar idle visible
 793 |    RESPONDING: video playing over idle bg, mic off
 794 | */
 795 | var ORACLE_STATE = 'IDLE'; /* IDLE, WELCOME, LISTENING, PROCESSING, RESPONDING */
 796 | function setOracleState(state){
 797 |   ORACLE_STATE = state;
 798 |   console.log('[Satomi] State →', state);
 799 |   switch(state){
 800 |     case 'LISTENING':
 801 |       mic.disabled=false;
 802 |       setStat('Ready','#334',false);
 803 |       /* Ensure avatar idle is visible (video-wrap bg shows through when vid is transparent) */
 804 |       vid.style.opacity='0';
 805 |       break;
 806 |     case 'PROCESSING':
 807 |       mic.disabled=true;
 808 |       if(isRec) stopRec();
 809 |       break;
 810 |     case 'RESPONDING':
 811 |       mic.disabled=true;
 812 |       if(isRec) stopRec();
 813 |       break;
 814 |     case 'WELCOME':
 815 |       mic.disabled=true;
 816 |       break;
 817 |   }
 818 | }
 819 | 
 820 | var VISION_SPONSOR_MAP = {
 821 |   'trezor':   { category:'amazon', title:'Trezor Hardware Wallet', id:'vision_trezor',
 822 |     description:'The original Bitcoin hardware wallet. Battle-tested since 2014.',
 823 |     url:'https://amzn.to/trezor', cta:'View on Amazon' },
 824 |   'coldcard': { category:'affiliate', title:'Coldcard Mk4', id:'vision_coldcard',
 825 |     description:'The most secure Bitcoin signing device. Air-gapped by default.',
 826 |     url:'https://coldcard.com', cta:'Get Coldcard' },
 827 |   'ledger':   { category:'amazon', title:'Ledger Hardware Wallet', id:'vision_ledger',
 828 |     description:'Secure your Bitcoin with industry-leading hardware security.',
 829 |     url:'https://amzn.to/ledger', cta:'View on Amazon' },
 830 |   'bitaxe':   { category:'affiliate', title:'BitAxe Solo Miner', id:'vision_bitaxe',
 831 |     description:'Open-source Bitcoin miner. Stack sats from your home.',
 832 |     url:'https://bitaxe.org', cta:'Get BitAxe' },
 833 |   'umbrel':   { category:'affiliate', title:'Umbrel Home Server', id:'vision_umbrel',
 834 |     description:'Run your own Bitcoin node. Your keys, your coins.',
 835 |     url:'https://umbrel.com', cta:'Run Umbrel' },
 836 |   'start9':   { category:'affiliate', title:'Start9 Embassy', id:'vision_start9',
 837 |     description:'Sovereign computing for the sovereign individual.',
 838 |     url:'https://start9.com', cta:'Get Embassy' },
 839 |   'seedsigner':{ category:'affiliate', title:'SeedSigner', id:'vision_seedsigner',
 840 |     description:'Air-gapped signing device. Build your own or buy assembled.',
 841 |     url:'https://seedsigner.com', cta:'Learn More' },
 842 |   'passport': { category:'affiliate', title:'Foundation Passport', id:'vision_passport',
 843 |     description:'Open-source, air-gapped Bitcoin hardware wallet.',
 844 |     url:'https://foundationdevices.com', cta:'Get Passport' },
 845 |   'jade':     { category:'affiliate', title:'Blockstream Jade', id:'vision_jade',
 846 |     description:'Open-source hardware wallet with air-gapped signing.',
 847 |     url:'https://store.blockstream.com', cta:'Get Jade' }
 848 | };
 849 | 
 850 | function pulseMic(){
 851 |   if(!mic||mic.disabled||isRec)return;
 852 |   mic.classList.remove('idle-pulse');
 853 |   void mic.offsetWidth;
 854 |   mic.classList.add('idle-pulse');
 855 |   setStat('Tap mic to respond','#ff3b5f',false);
 856 |   setTimeout(function(){mic.classList.remove('idle-pulse');setStat('Ready','#334',false);},6000);
 857 | }
 858 | 
 859 | // ── VISITOR FINGERPRINT ───────────────────────────────────
 860 | // Generates a stable browser fingerprint — no cookies, no login
 861 | // Used server-side to recognize returning visitors
 862 | (function() {
 863 |   try {
 864 |     var fp = '';
 865 |     // Canvas fingerprint
 866 |     var canvas = document.createElement('canvas');
 867 |     var ctx = canvas.getContext('2d');
 868 |     ctx.textBaseline = 'top';
 869 |     ctx.font = '14px Arial';
 870 |     ctx.fillText('Satomi fp', 2, 2);
 871 |     fp += canvas.toDataURL().slice(-20);
 872 |     // Screen + timezone
 873 |     fp += screen.width + 'x' + screen.height + Intl.DateTimeFormat().resolvedOptions().timeZone;
 874 |     // Hash it (simple djb2)
 875 |     var hash = 5381;
 876 |     for (var i = 0; i < fp.length; i++) {
 877 |       hash = ((hash << 5) + hash) + fp.charCodeAt(i);
 878 |       hash = hash & hash; // 32-bit int
 879 |     }
 880 |     window._visitorToken = Math.abs(hash).toString(36);
 881 |   } catch(e) {
 882 |     window._visitorToken = 'anon';
 883 |   }
 884 | })();
 885 | 
 886 | // Read session_id and page context from URL params (injected by widget)
 887 | var _urlParams = new URLSearchParams(window.location.search);
 888 | var SESSION_ID = _urlParams.get('session_id') || ('sess_'+Date.now()+'_'+Math.random().toString(36).slice(2,8));
 889 | window.ORACLE_FINGERPRINT_MATCH = false;
 890 | var PAGE_CONTEXT = {
 891 |   type: _urlParams.get('page_type') || 'general',
 892 |   path: _urlParams.get('page_path') || window.location.pathname,
 893 |   content: null,
 894 |   url: document.referrer || window.location.href,
 895 | };
 896 | 
 897 | // Receive richer context from parent widget via postMessage
 898 | window.addEventListener('message', function(e) {
 899 |   if (!e.data || typeof e.data !== 'object') return;
 900 |   var d = e.data;
 901 |   if (d.type === 'oracle:context') {
 902 |     // Parent widget sent full page context
 903 |     if (d.sessionId) SESSION_ID = d.sessionId;
 904 |     if (d.pageContext) PAGE_CONTEXT = d.pageContext;
 905 |   }
 906 | });
 907 | 
 908 | // Tell parent we want context (in case we loaded before message was sent)
 909 | setTimeout(function(){
 910 |   try{ if(window.parent!==window) window.parent.postMessage({type:'oracle:context_request'},'*'); }catch(e){}
 911 | },300);
 912 | 
 913 | /* DOM */
 914 | var gate=document.getElementById('gate');
 915 | var stage=document.getElementById('stage');
 916 | var gBtn=document.getElementById('gate-btn');
 917 | var gStatus=document.getElementById('gate-status');
 918 | var gErr=document.getElementById('gate-error');
 919 | var vid=document.getElementById('vid');
 920 | var sub=document.getElementById('subtitle');
 921 | var statEl=document.getElementById('stat-text');
 922 | var spinEl=document.getElementById('spin');
 923 | var txEl=document.getElementById('tx');
 924 | var mic=document.getElementById('mic');
 925 | var micHint=document.getElementById('mic-hint');
 926 | var iMic=document.getElementById('i-mic');
 927 | var iStop=document.getElementById('i-stop');
 928 | var cards=document.getElementById('cards');
 929 | 
 930 | /* ── MIC REQUEST ── */
 931 | function requestMic(){
 932 |   gBtn.disabled=true;
 933 |   gStatus.textContent='Requesting microphone...';
 934 |   gErr.style.display='none';
 935 | 
 936 |   /* CRITICAL: unlock audio context immediately on this user gesture */
 937 |   try{
 938 |     var _unlockAc=new(window.AudioContext||window.webkitAudioContext)();
 939 |     var _unlockBuf=_unlockAc.createBuffer(1,1,22050);
 940 |     var _unlockSrc=_unlockAc.createBufferSource();
 941 |     _unlockSrc.buffer=_unlockBuf;_unlockSrc.connect(_unlockAc.destination);_unlockSrc.start(0);
 942 |     setTimeout(function(){try{_unlockAc.close();}catch(e){}},300);
 943 |   }catch(e){}
 944 | 
 945 |   try{
 946 |     var ac=new(window.AudioContext||window.webkitAudioContext)();
 947 |     var buf=ac.createBuffer(1,1,22050);
 948 |     var src=ac.createBufferSource();
 949 |     src.buffer=buf;src.connect(ac.destination);src.start(0);
 950 |     setTimeout(function(){try{ac.close();}catch(e){}},500);
 951 |   }catch(e){}
 952 | 
 953 |   /* Also "unlock" video element immediately */
 954 |   vid.muted=true;
 955 |   vid.play().catch(function(){});
 956 | 
 957 |   /* Pre-unlock Audio element for PATH B (chat responses) */
 958 |   window._audioUnlocked = new Audio();
 959 |   window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
 960 |   window._audioUnlocked.volume = 0.001;
 961 |   window._audioUnlocked.play().catch(function(){});
 962 | 
 963 |   window._chatAudioPlaying = false;
 964 | 
 965 |   navigator.mediaDevices.getUserMedia({audio:true,video:false})
 966 |     .then(function(stream){
 967 |       stream.getTracks().forEach(function(t){t.stop();}); /* don't need stream, just the gesture */
 968 |       gStatus.textContent='';
 969 |       go();
 970 |     })
 971 |     .catch(function(err){
 972 |       console.warn('[Satomi mic error]', err);
 973 |       gBtn.disabled=false;
 974 |       gStatus.textContent='';
 975 |       gErr.style.display='block';
 976 |       var name = err && err.name ? err.name : '';
 977 |       if(name === 'NotAllowedError' || name === 'PermissionDeniedError'){
 978 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone blocked. Click the camera/mic icon in your browser address bar and allow access, then <a href="javascript:location.reload()" style="color:#ff3b5f;text-decoration:underline;">reload</a>.';
 979 |       } else if(name === 'NotReadableError' || name === 'TrackStartError'){
 980 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone is in use by another app. Close other tabs or apps using the mic, then <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">try again</button>.';
 981 |       } else if(name === 'NotFoundError'){
 982 |         gErr.innerHTML='&#9888;&#xFE0F; No microphone found. Connect a microphone and <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">try again</button>.';
 983 |       } else {
 984 |         gErr.innerHTML='&#9888;&#xFE0F; Microphone unavailable ('+name+'). Try clicking <button onclick="requestMic()" style="background:none;border:none;color:#ff3b5f;text-decoration:underline;cursor:pointer;padding:0;font-size:inherit;">here to retry</button> or check browser settings.';
 985 |       }
 986 |     });
 987 | }
 988 | 
 989 | /* ── TRANSITION ── */
 990 | function go(){
 991 |   gate.style.opacity='0';
 992 |   setTimeout(function(){
 993 |     gate.style.display='none';
 994 |     stage.style.display='flex';
 995 |     stage.style.opacity='0';
 996 |     setTimeout(function(){
 997 |       stage.style.transition='opacity .45s';
 998 |       stage.style.opacity='1';
 999 |       initSR();
1000 |       setOracleState('WELCOME');
1001 |       playIntent('GREETING');
1002 |     },30);
1003 |   },350);
1004 | }
1005 | 
1006 | /* ── PLAY CACHED INTENT ── */
1007 | function playIntent(intent){
1008 |   if(busy&&intent!=='GREETING')return;
1009 |   if(intent.indexOf('DAILY_BRIEF')===0&&window._briefFetched)return;
1010 |   setBusy(true);
1011 |   setStat('Satomi loading...','#f4c46f',true);
1012 |   // Progress messages so user knows it's working, not broken
1013 |   var _loadMsgs = ['Initializing...','Rendering response...','Almost ready...'];
1014 |   var _loadIdx = 0;
1015 |   var _loadTimer = setInterval(function(){
1016 |     _loadIdx++;
1017 |     if(_loadIdx < _loadMsgs.length) setStat(_loadMsgs[_loadIdx],'#f4c46f',true);
1018 |     else clearInterval(_loadTimer);
1019 |   }, 6000);
1020 |   var _clearTimer = function(){ clearInterval(_loadTimer); };
1021 |   fetchTO(A+'/oracle/speak',{
1022 |     method:'POST',
1023 |     headers:{'Content-Type':'application/json'},
1024 |     body:JSON.stringify({intent:intent})
1025 |   },30000)
1026 |   .then(function(r){
1027 |     if(!r.ok)throw new Error('HTTP '+r.status);
1028 |     var ct=r.headers.get('content-type')||'';
1029 |     if(ct.indexOf('video')>=0)return r.blob().then(blobURL);
1030 |     return r.json().then(function(j){
1031 |       return fetchTO(A+j.video_url,{},20000).then(function(r2){return r2.blob().then(blobURL);});
1032 |     });
1033 |   })
1034 |   .then(function(url){ if(typeof _clearTimer=='function') _clearTimer(); return playVid(url);})
1035 |   .then(function(){
1036 |     if(intent==='SOVEREIGNTY_ASSESSMENT')showCards();
1037 |     if(intent==='GREETING'){
1038 |       window._briefFetched=false;
1039 |       _greeted=true;
1040 |       /* State machine: welcome done → LISTENING. Always activate mic. */
1041 |       setOracleState('LISTENING');
1042 |       setTimeout(function(){
1043 |         if(!busy&&!isRec&&mic){
1044 |           mic.disabled=false;
1045 |           startRec();
1046 |           setStat('Listening…','#6cff9f',false);
1047 |         }
1048 |       },400);
1049 |     }
1050 |   })
1051 |   .catch(function(e){
1052 |     if(e&&e.message&&e.message.indexOf('HTTP')>=0)
1053 |       setStat('Satomi error — try again.','#ff3b5f',false);
1054 |   })
1055 |   .finally(function(){
1056 |     setBusy(false);
1057 |     setOracleState('LISTENING');
1058 |     setTimeout(pulseMic,500);
1059 |   });
1060 | }
1061 | 
1062 | function si(intent){if(busy)return;hideCards();playIntent(intent);}
1063 | 
1064 | /* ── PROCESS SPEECH (two-phase: audio-first + async video) ── */
1065 | function process(text){
1066 |   if(!text.trim()||busy)return;
1067 |   // Guard: mark brief as fetched to prevent double-play with DAILY_BRIEF_INTRO
1068 |   if(/daily\s*brief/i.test(text)) window._briefFetched=true;
1069 |   setOracleState('PROCESSING');
1070 |   setBusy(true);hideCards();hideActionCard();showTX(text);
1071 | 
1072 |   // P0-3: Elapsed time counter — show "Satomi is thinking... Xs" with live counter
1073 |   var _thinkStart=Date.now();
1074 |   var _thinkReassured=false;
1075 |   setStat('Satomi is thinking\u2026 0s','#f4c46f',true);
1076 |   var _thinkTimer=setInterval(function(){
1077 |     var elapsed=Math.floor((Date.now()-_thinkStart)/1000);
1078 |     // P0-4: Reassurance message after 15s
1079 |     if(elapsed>=15&&!_thinkReassured){
1080 |       _thinkReassured=true;
1081 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1082 |     } else if(!_thinkReassured){
1083 |       setStat('Satomi is thinking\u2026 '+elapsed+'s','#f4c46f',true);
1084 |     } else {
1085 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1086 |     }
1087 |   },1000);
1088 |   window._thinkTimer=_thinkTimer;
1089 | 
1090 |   // Phase 2 T1.4: Play thinking loop immediately for instant visual feedback
1091 |   // P0-2: Add onerror fallback — if thinking video fails, show static avatar
1092 |   vid.muted=true;
1093 |   vid.loop=true;
1094 |   vid.src=A+'/oracle/thinking';
1095 |   vid.style.opacity='1';
1096 |   vid.onerror=function(){
1097 |     console.warn('[Satomi] thinking video failed — showing static avatar');
1098 |     vid.style.opacity='0'; /* static avatar image underneath is always visible */
1099 |   };
1100 |   vid.play().catch(function(e){
1101 |     console.warn('[Satomi] thinking autoplay blocked:',e);
1102 |     vid.style.opacity='0'; /* fallback to static avatar */
1103 |   });
1104 | 
1105 |   // Re-unlock audio context on every user interaction
1106 |   try{
1107 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1108 |     if(_ac.state==='suspended') _ac.resume();
1109 |     var _buf=_ac.createBuffer(1,1,22050);
1110 |     var _src=_ac.createBufferSource();
1111 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1112 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1113 |   }catch(e){}
1114 | 
1115 |   var pendingVideoUrl=null;
1116 |   var _audioFinished=false;
1117 | 
1118 |   fetchTO(A+'/oracle/chat',{
1119 |     method:'POST',headers:{'Content-Type':'application/json'},
1120 |     body:JSON.stringify({text:text,session_id:SESSION_ID,visitor_token:window._visitorToken||'anon',use_cache_for_intents:true,page_context:PAGE_CONTEXT,audio_first:true,avatar_source:"oracle_studio"})
1121 |   },90000)
1122 |   .then(function(r){
1123 |     if(!r.ok) throw new Error('HTTP '+r.status);
1124 |     var ct=r.headers.get('content-type')||'';
1125 |     if(ct.indexOf('video')>=0){
1126 |       // Cache hit — video came back immediately
1127 |       return r.blob().then(blobURL).then(function(url){ return playVid(url); });
1128 |     }
1129 |     // Audio-first JSON response
1130 |     return r.json().then(function(j){
1131 |       var responseText=j.text;
1132 |       var videoJobId=j.job_id;
1133 |       var _pendingCard = j.action_card || null;
1134 | 
1135 |       // Play audio: try cached job audio first (no duplicate Kokoro), fallback to /oracle/voice
1136 |       var audioFetch;
1137 |       if(videoJobId){
1138 |         audioFetch=fetchTO(A+'/oracle/job/'+videoJobId+'/audio',{},35000)
1139 |           .then(function(ar){
1140 |             if(!ar.ok) throw new Error('no cached audio');
1141 |             return ar.blob();
1142 |           })
1143 |           .catch(function(){
1144 |             return fetchTO(A+'/oracle/voice',{
1145 |               method:'POST',headers:{'Content-Type':'application/json'},
1146 |               body:JSON.stringify({text:responseText})
1147 |             },35000).then(function(ar){
1148 |               if(!ar.ok) throw new Error('audio failed');
1149 |               return ar.blob();
1150 |             });
1151 |           });
1152 |       } else {
1153 |         audioFetch=fetchTO(A+'/oracle/voice',{
1154 |           method:'POST',headers:{'Content-Type':'application/json'},
1155 |           body:JSON.stringify({text:responseText})
1156 |         },35000).then(function(ar){
1157 |           if(!ar.ok) throw new Error('audio failed');
1158 |           return ar.blob();
1159 |         });
1160 |       }
1161 |       return audioFetch
1162 |       .then(function(b){
1163 |         return new Blob([b], {type: b.type || 'audio/wav'});
1164 |       })
1165 |       .then(function(audioBlob){
1166 |         var audioUrl=URL.createObjectURL(audioBlob);
1167 |         var audio;
1168 |         if(window._audioUnlocked){
1169 |           audio=window._audioUnlocked;
1170 |           window._audioUnlocked=null;
1171 |           audio.src=audioUrl;
1172 |           audio.volume=1.0;
1173 |           audio.muted=false;
1174 |         } else {
1175 |           audio=new Audio(audioUrl);
1176 |           audio.volume=1.0;
1177 |         }
1178 |         window._chatAudioPlaying=true;
1179 |         var playPromise = audio.play();
1180 |         if(playPromise !== undefined){
1181 |           playPromise.then(function(){
1182 |             if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1183 |             setStat('Speaking','#6cff9f',false);
1184 |           }).catch(function(err){
1185 |             console.warn('[Satomi] audio.play() rejected:', err.name);
1186 |             // On mobile, audio may be blocked — set volume via user gesture retry
1187 |             audio.muted = false;
1188 |             audio.volume = 1.0;
1189 |             setTimeout(function(){
1190 |               audio.play().catch(function(e2){
1191 |                 console.warn('[Satomi] retry failed:', e2.name);
1192 |                 if(audio.onended) audio.onended();
1193 |               });
1194 |             }, 100);
1195 |           });
1196 |         }
1197 | 
1198 |         return new Promise(function(resolve){
1199 |           audio.onended=function(){
1200 |             _audioFinished=true;
1201 |             if(_pendingCard){ showActionCard(_pendingCard); _pendingCard=null; }
1202 |             window._chatAudioPlaying=false;
1203 |             URL.revokeObjectURL(audioUrl);
1204 |             // Audio finished — unmute video if it's playing lip sync
1205 |             try{ if(!vid.paused){ vid.muted=false; vid.volume=1.0; } }catch(e){}
1206 |             // Don't replay lip-sync video after audio already finished — just resolve
1207 |             if(pendingVideoUrl){
1208 |               try { URL.revokeObjectURL(pendingVideoUrl); } catch(e) {}
1209 |             }
1210 |             resolve();
1211 |           };
1212 | 
1213 |           // Phase 2 T2.1: SSE push replaces polling (with polling fallback)
1214 |           if(videoJobId){
1215 |             var _videoHandled=false;
1216 |             function _handleVideoReady(){
1217 |               if(_videoHandled) return;
1218 |               _videoHandled=true;
1219 |               fetch(A+'/oracle/job/'+videoJobId)
1220 |                 .then(function(vr){
1221 |                   if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1222 |                     return vr.blob();
1223 |                   }
1224 |                   return null;
1225 |                 })
1226 |                 .then(function(vb){
1227 |                   if(vb){
1228 |                     pendingVideoUrl=blobURL(vb);
1229 |                     if(_audioFinished){
1230 |                       // Cross-fade: thinking loop → lip-sync video
1231 |                       vid.style.opacity='0';
1232 |                       setTimeout(function(){
1233 |                         vid.loop=false;
1234 |                         vid.muted=false;
1235 |                         vid.src=pendingVideoUrl;
1236 |                         vid.style.opacity='1';
1237 |                         playVid(pendingVideoUrl);
1238 |                       },300);
1239 |                     }
1240 |                   }
1241 |                 })
1242 |                 .catch(function(e){console.warn('[Satomi] video fetch error:',e);});
1243 |             }
1244 | 
1245 |             if(window.EventSource){
1246 |               // SSE push — sub-100ms notification
1247 |               var evtSource=new EventSource(A+'/oracle/job/'+videoJobId+'/stream');
1248 |               evtSource.addEventListener('audio_ready',function(){
1249 |                 // Audio already being fetched above — this is informational
1250 |               });
1251 |               evtSource.addEventListener('video_ready',function(){
1252 |                 evtSource.close();
1253 |                 _handleVideoReady();
1254 |               });
1255 |               evtSource.addEventListener('error',function(e){
1256 |                 evtSource.close();
1257 |                 // P1-1: SSE error — stop thinking loop but keep static avatar visible
1258 |                 vid.loop=false;
1259 |                 vid.style.opacity='0'; /* static avatar img underneath remains visible */
1260 |                 setStat('Connection issue — retrying\u2026','#f4c46f',true);
1261 |               });
1262 |               evtSource.onerror=function(){
1263 |                 // Connection lost — fall back to polling
1264 |                 evtSource.close();
1265 |                 if(!_videoHandled) _startPollFallback();
1266 |               };
1267 |             } else {
1268 |               _startPollFallback();
1269 |             }
1270 | 
1271 |             function _startPollFallback(){
1272 |               var pollAttempts=0,maxPollAttempts=60;
1273 |               var pollVideo=setInterval(function(){
1274 |                 pollAttempts++;
1275 |                 fetch(A+'/oracle/job/'+videoJobId)
1276 |                   .then(function(vr){
1277 |                     if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1278 |                       return vr.blob();
1279 |                     }
1280 |                     return null;
1281 |                   })
1282 |                   .then(function(vb){
1283 |                     if(vb){
1284 |                       clearInterval(pollVideo);
1285 |                       _videoHandled=true;
1286 |                       pendingVideoUrl=blobURL(vb);
1287 |                       if(_audioFinished){
1288 |                         vid.style.opacity='1';
1289 |                         playVid(pendingVideoUrl);
1290 |                       }
1291 |                     }
1292 |                   })
1293 |                   .catch(function(){});
1294 |                 if(pollAttempts>=maxPollAttempts){
1295 |                   clearInterval(pollVideo);
1296 |                   setBusy(false);mic.disabled=false;
1297 |                 }
1298 |               },2000);
1299 |             }
1300 |           }
1301 |         });
1302 |       });
1303 |     });
1304 |   })
1305 |   .then(function(){
1306 |     setTimeout(pulseMic,500);
1307 |   })
1308 |   .catch(function(e){
1309 |     console.error('process error:',e);
1310 |     if(e&&(e.message||'').indexOf('timeout')>=0){
1311 |       setStat('','#334',false);
1312 |     } else if(e&&e.message&&e.message.indexOf('HTTP')>=0){
1313 |       setStat('Satomi error — try again.','#ff3b5f',false);
1314 |     }
1315 |   })
1316 |   .finally(function(){
1317 |     if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1318 |     setBusy(false);hideTX();
1319 |     setOracleState('LISTENING');
1320 |   });
1321 | }
1322 | 
1323 | function blobURL(b){
1324 |   if(objURL)try{URL.revokeObjectURL(objURL);}catch(e){}
1325 |   objURL=URL.createObjectURL(b);
1326 |   return objURL;
1327 | }
1328 | 
1329 | /* ── PLAY VIDEO ── */
1330 | function playVid(url){
1331 |   return new Promise(function(res){
1332 |     setOracleState('RESPONDING');
1333 |     vid.loop=false;
1334 |     vid.src=url;
1335 |     vid.style.opacity='1';
1336 |     if(window._matrixHide) window._matrixHide();
1337 |     var _safetyTimer = setTimeout(function(){
1338 |       if(busy){
1339 |         console.warn('[Satomi] Safety timeout — forcing mic unlock after 30s');
1340 |         setBusy(false);
1341 |         if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1342 |         setOracleState('LISTENING');
1343 |       }
1344 |     }, 30000);
1345 |     try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
1346 |     vid.onended=function(){
1347 |       clearTimeout(_safetyTimer);
1348 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1349 |       /* P1-3: Fade out first, then clear src — avoids flash. Static avatar underneath stays visible. */
1350 |       vid.style.opacity='0';
1351 |       setTimeout(function(){ vid.src=''; },300);
1352 |       if(window._matrixShow) window._matrixShow();
1353 |       hideSub();
1354 |       setBusy(false);
1355 |       setOracleState('LISTENING');
1356 |       res();
1357 |       try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
1358 |     };
1359 |     vid.onerror=function(){
1360 |       clearTimeout(_safetyTimer);
1361 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1362 |       // P0-2: On video error, fade to static avatar (always visible behind vid)
1363 |       vid.style.opacity='0';
1364 |       vid.src='';
1365 |       setStat('Recovering\u2026','#f4c46f',true);
1366 |       setTimeout(function(){
1367 |         setBusy(false);
1368 |         setOracleState('LISTENING');
1369 |         setStat('Ready','#334',false);
1370 |         res();
1371 |       }, 1500);
1372 |     };
1373 |     vid.muted=true;
1374 |     vid.volume=1.0;
1375 |     var unmuted=false;
1376 |     function tryUnmute(){
1377 |       if(unmuted)return; unmuted=true;
1378 |       vid.muted=false;
1379 |       vid.volume=1.0;
1380 |     }
1381 |     vid.addEventListener('canplay',function oncp(){
1382 |       vid.removeEventListener('canplay',oncp);
1383 |       setStat('Speaking','#6cff9f',false);
1384 |       if(!window._chatAudioPlaying){
1385 |         tryUnmute();
1386 |       }
1387 |     },{once:true});
1388 |     var p=vid.play();
1389 |     if(p){
1390 |       p.then(function(){}).catch(function(){
1391 |         setStat('Tap to play','#f4c46f',false);
1392 |         vid.addEventListener('click',function(){vid.muted=false;vid.play();},{once:true});
1393 |       });
1394 |     }
1395 |   });
1396 | }
1397 | 
1398 | /* ── SPEECH RECOGNITION ── */
1399 | function initSR(){
1400 |   var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
1401 |   if(!SR){micHint.textContent='no speech api';return;}
1402 |   recognition=new SR();
1403 |   recognition.continuous=true;recognition.interimResults=true;recognition.lang='en-US';recognition.maxAlternatives=1;
1404 |   recognition.onresult=function(e){
1405 |     var fin='',int='';
1406 |     for(var i=0;i<e.results.length;i++){
1407 |       if(e.results[i].isFinal)fin+=e.results[i][0].transcript;
1408 |       else int+=e.results[i][0].transcript;
1409 |     }
1410 |     showTX(fin||int);if(fin)pending=fin;
1411 |   };
1412 |   recognition.onend=function(){
1413 |     setRec(false);
1414 |     // Auto-submit on silence — no tap required
1415 |     var _pend = pending;
1416 |     setTimeout(function(){ if(_pend.trim()&&!busy){process(_pend);pending='';}}, 300);
1417 |   };
1418 |   recognition.onerror=function(e){console.warn(e.error);setRec(false);};
1419 | }
1420 | 
1421 | function toggleMic(){if(busy)return;isRec?stopRec():startRec();}
1422 | function startRec(){
1423 |   if(!recognition){setStat('No speech API','#ff3b5f',false);return;}
1424 |   pending='';isRec=true;setRec(true);setStat('\ud83c\udf99 Listening...','#66d9ff',false);
1425 |   try{recognition.start();}catch(e){console.warn(e);}
1426 | }
1427 | function stopRec(){
1428 |   var _hadRec=isRec;  // save flag BEFORE clearing — onend checks isRec
1429 |   isRec=false;setRec(false);
1430 |   // Show thinking video immediately on mobile to eliminate visual gap
1431 |   if(vid && !busy){
1432 |     try{vid.muted=true;vid.loop=true;vid.src=A+'/oracle/thinking';vid.style.opacity='1';vid.play().catch(function(){vid.style.opacity='0';});}catch(e){}
1433 |   }
1434 |   if(recognition)try{recognition.stop();}catch(e){}
1435 |   // onend will fire after recognition.stop() and handle process() automatically
1436 | }
1437 | function setRec(on){
1438 |   mic.classList.toggle('rec',on);
1439 |   iMic.style.display=on?'none':'block';
1440 |   iStop.style.display=on?'block':'none';
1441 |   micHint.textContent=on?'tap to send':'tap to speak';
1442 | }
1443 | 
1444 | /* ── HELPERS ── */
1445 | function setStat(t,c,sp){statEl.textContent=t;statEl.style.color=c||'#334';spinEl.style.display=sp?'block':'none';spinEl.style.color=c||'#334';}
1446 | function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}}
1447 | function showSub(t){sub.textContent=t;sub.classList.add('on');}
1448 | function hideSub(){sub.classList.remove('on');}
1449 | function showTX(t){txEl.textContent=t;txEl.classList.add('on');}
1450 | function hideTX(){txEl.classList.remove('on');}
1451 | function showCards(){cards.classList.add('on');}
1452 | function hideCards(){cards.classList.remove('on');}
1453 | /* ── GEMINI VISION ── */
1454 | var _visionSessionId = null;
1455 | 
1456 | function updateCameraButtonState() {
1457 |   var lbl = document.getElementById('cam-btn-label');
1458 |   if (!lbl) return;
1459 |   lbl.textContent = _visionSessionId
1460 |     ? 'FOLLOW-UP PHOTO'
1461 |     : 'ANALYZE HARDWARE';
1462 | }
1463 | 
1464 | function triggerCamera(){
1465 |   document.getElementById("cam-input").click();
1466 | }
1467 | 
1468 | function handleVisionUpload(evt){
1469 |   var file = evt.target.files[0];
1470 |   if(!file) return;
1471 |   if (busy) {
1472 |     showVisionStatus('Satomi is speaking — wait a moment');
1473 |     setTimeout(hideVisionStatus, 2000);
1474 |     evt.target.value = "";
1475 |     return;
1476 |   }
1477 |   evt.target.value = "";
1478 |   
1479 |   var reader = new FileReader();
1480 |   reader.onload = function(e){
1481 |     var b64 = e.target.result.split(",")[1];
1482 |     var mime = file.type || "image/jpeg";
1483 |     sendVisionImage(b64, mime);
1484 |   };
1485 |   reader.readAsDataURL(file);
1486 | }
1487 | 
1488 | var SEED_RECOVERY_STEPS = [
1489 |   {
1490 |     label: 'STEP 1 OF 3 — STOP IMMEDIATELY',
1491 |     text: 'Do NOT send any Bitcoin from this wallet until you have moved your funds. Anyone who saw this seed phrase can access your Bitcoin right now.',
1492 |     speak: 'Stop. Do not send any Bitcoin from this wallet. Anyone who saw this seed phrase can steal your funds right now.'
1493 |   },
1494 |   {
1495 |     label: 'STEP 2 OF 3 — MOVE YOUR FUNDS',
1496 |     text: 'On a different device, create a brand new wallet. Generate a NEW seed phrase — write it down on paper only, never photograph it. Transfer ALL funds to the new wallet address immediately.',
1497 |     speak: 'On a different device, create a new wallet with a new seed phrase. Write it on paper only. Transfer all your funds to the new wallet immediately.'
1498 |   },
1499 |   {
1500 |     label: 'STEP 3 OF 3 — SECURE THE NEW WALLET',
1501 |     text: 'Once funds are transferred, the old wallet is abandoned. Store your new seed phrase in a metal backup, split across two secure locations. Never store seed phrases digitally.',
1502 |     speak: 'Once funds are moved, abandon the old wallet. Store your new seed phrase in metal, split across two secure locations. Never store seed phrases digitally.'
1503 |   }
1504 | ];
1505 | 
1506 | function showSecurityAlert(msg, onDismiss) {
1507 |   var overlay = document.getElementById('vision-security-overlay');
1508 |   var msgEl = document.getElementById('vision-security-msg');
1509 |   var dismissBtn = document.getElementById('vision-security-dismiss');
1510 |   var recoveryPanel = document.getElementById('vision-recovery-panel');
1511 |   if (!overlay || !msgEl) return;
1512 | 
1513 |   msgEl.textContent = msg;
1514 |   overlay.style.display = 'flex';
1515 | 
1516 |   // Speak the initial alert urgently
1517 |   function speakText(text) {
1518 |     fetchTO(A+'/oracle/voice', {
1519 |       method: 'POST',
1520 |       headers: {'Content-Type': 'application/json'},
1521 |       body: JSON.stringify({text: text})
1522 |     }, 20000).then(function(r) {
1523 |       if (!r.ok) return;
1524 |       return r.blob();
1525 |     }).then(function(blob) {
1526 |       if (!blob) return;
1527 |       var alertAudio = new Audio(URL.createObjectURL(blob));
1528 |       alertAudio.volume = 1.0;
1529 |       alertAudio.play().catch(function(){});
1530 |     }).catch(function(){});
1531 |   }
1532 | 
1533 |   speakText('SECURITY ALERT. ' + msg +
1534 |     ' Your seed phrase may be compromised. Do not send Bitcoin until you hear the recovery steps.');
1535 | 
1536 |   // Dismiss transitions to recovery steps
1537 |   dismissBtn.onclick = function() {
1538 |     dismissBtn.style.display = 'none';
1539 |     msgEl.style.fontSize = '0.9rem';
1540 |     msgEl.style.opacity = '0.7';
1541 |     recoveryPanel.style.display = 'block';
1542 |     _showRecoveryStep(0, speakText);
1543 |   };
1544 | }
1545 | 
1546 | function _showRecoveryStep(idx, speakFn) {
1547 |   var steps = SEED_RECOVERY_STEPS;
1548 |   var stepLabel = document.getElementById('vision-recovery-step-label');
1549 |   var stepText = document.getElementById('vision-recovery-step-text');
1550 |   var nextBtn = document.getElementById('vision-recovery-next');
1551 |   var helpBtn = document.getElementById('vision-recovery-help');
1552 |   var closeBtn = document.getElementById('vision-recovery-close');
1553 | 
1554 |   if (!stepLabel || !stepText) return;
1555 | 
1556 |   stepLabel.textContent = steps[idx].label;
1557 |   stepText.textContent = steps[idx].text;
1558 |   speakFn(steps[idx].speak);
1559 | 
1560 |   var isLast = (idx === steps.length - 1);
1561 |   nextBtn.style.display = isLast ? 'none' : 'block';
1562 |   helpBtn.style.display = isLast ? 'block' : 'none';
1563 |   closeBtn.style.display = isLast ? 'block' : 'none';
1564 | 
1565 |   nextBtn.onclick = function() {
1566 |     if (idx < steps.length - 1) _showRecoveryStep(idx + 1, speakFn);
1567 |   };
1568 | 
1569 |   helpBtn.onclick = function() {
1570 |     // Close overlay and trigger Satomi to help set up new wallet
1571 |     var overlay = document.getElementById('vision-security-overlay');
1572 |     if (overlay) overlay.style.display = 'none';
1573 |     // Inject a vision guidance request for new wallet setup
1574 |     sendVisionImage(null, null, 'help me set up a new hardware wallet safely');
1575 |   };
1576 | 
1577 |   closeBtn.onclick = function() {
1578 |     var overlay = document.getElementById('vision-security-overlay');
1579 |     if (overlay) overlay.style.display = 'none';
1580 |   };
1581 | }
1582 | 
1583 | function _speakVisionGuidance(d) {
1584 |   var raw = d.guidance_text || d.guidance || d.analysis || d.response
1585 |     || "I can see your hardware. Let me walk you through the next step.";
1586 |   // Hard 30-word cap for TTS speed
1587 |   var words = raw.split(/\s+/);
1588 |   var guideText = words.length > 30 ? words.slice(0,30).join(" ") : raw;
1589 | 
1590 |   // Urgent spoken prefix for transaction verdicts
1591 |   if (d.verdict === 'DO NOT SIGN') {
1592 |     guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1593 |   } else if (d.verdict === 'REVIEW CAREFULLY' && d.red_flags && d.red_flags.length) {
1594 |     guideText = 'REVIEW CAREFULLY. ' + guideText;
1595 |   }
1596 | 
1597 |   showVisionStatus("Speaking...");
1598 |   showSub(guideText);
1599 | 
1600 |   // Transaction review verdict card
1601 |   if (d.category === 'transaction' && d.verdict) {
1602 |     var verdictColor = d.verdict === 'SAFE TO SIGN'
1603 |       ? '#00d4aa'
1604 |       : d.verdict === 'DO NOT SIGN'
1605 |       ? '#ff3b5f'
1606 |       : '#f5a623';
1607 | 
1608 |     var verdictHtml = '<div style="background:rgba(0,0,0,.4);' +
1609 |       'border:2px solid ' + verdictColor + ';border-radius:8px;' +
1610 |       'padding:12px 16px;margin-bottom:12px;">' +
1611 |       '<div style="font-family:monospace;font-size:10px;' +
1612 |       'letter-spacing:.12em;color:' + verdictColor + ';' +
1613 |       'text-transform:uppercase;margin-bottom:6px;">' +
1614 |       '\u26A1 TRANSACTION ANALYSIS</div>' +
1615 |       '<div style="font-size:1.1rem;font-weight:800;' +
1616 |       'color:' + verdictColor + ';margin-bottom:8px;">' +
1617 |       d.verdict + '</div>';
1618 | 
1619 |     if (d.recipient_address) {
1620 |       verdictHtml += '<div style="font-family:monospace;font-size:10px;' +
1621 |         'color:rgba(255,255,255,.5);word-break:break-all;">' +
1622 |         'TO: ' + d.recipient_address + '</div>';
1623 |     }
1624 |     if (d.amount_btc) {
1625 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1626 |         'color:rgba(255,255,255,.7);margin-top:4px;">' +
1627 |         'AMOUNT: ' + d.amount_btc + ' BTC</div>';
1628 |     }
1629 |     if (d.fee_sats) {
1630 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1631 |         'color:rgba(255,255,255,.6);">' +
1632 |         'FEE: ' + d.fee_sats + ' sats</div>';
1633 |     }
1634 |     if (d.red_flags && d.red_flags.length) {
1635 |       verdictHtml += '<div style="margin-top:8px;">';
1636 |       d.red_flags.forEach(function(flag) {
1637 |         verdictHtml += '<div style="font-family:monospace;font-size:9px;' +
1638 |           'color:#f5a623;letter-spacing:.06em;">\u26A0 ' + flag + '</div>';
1639 |       });
1640 |       verdictHtml += '</div>';
1641 |     }
1642 |     verdictHtml += '</div>';
1643 | 
1644 |     var vsEl = document.getElementById('vision-status');
1645 |     if (vsEl) {
1646 |       vsEl.innerHTML = verdictHtml + (vsEl.innerHTML || '');
1647 |       vsEl.classList.add('on');
1648 |     }
1649 |   }
1650 | 
1651 |   // Show steps in vision-status area if present
1652 |   if(d.steps && d.steps.length){
1653 |     var stepsHtml = d.steps.map(function(s,i){ return (i+1)+". "+s; }).join("<br>");
1654 |     var el=document.getElementById("vision-status");
1655 |     el.innerHTML = (d.device_name && d.device_name!=="unknown" ? "<b>"+d.device_name+"</b><br>" : "") + stepsHtml;
1656 |     el.classList.add("on");
1657 |   }
1658 | 
1659 |   // Add to session transcript
1660 |   _addVisionEntry(d.device_name, d.steps || [], guideText);
1661 | 
1662 |   // VOICE-ONLY: /oracle/voice is ElevenLabs-only, no GPU, ~400ms vs 14s
1663 |   fetchTO(A+"/oracle/voice",{method:"POST",
1664 |     headers:{"Content-Type":"application/json"},
1665 |     body:JSON.stringify({text:guideText})},15000)
1666 |   .then(function(ar){
1667 |     if(!ar.ok) throw new Error("voice "+ar.status);
1668 |     return ar.blob();
1669 |   })
1670 |   .then(function(audioBlob){
1671 |     hideVisionStatus();
1672 |     var audioURL = URL.createObjectURL(audioBlob);
1673 |     var audio;
1674 |     if(window._audioUnlocked){
1675 |       audio=window._audioUnlocked;
1676 |       window._audioUnlocked=null;
1677 |       audio.src=audioURL;
1678 |       audio.volume=1.0;
1679 |       audio.muted=false;
1680 |     } else {
1681 |       audio = new Audio(audioURL);
1682 |       audio.volume = 1.0;
1683 |     }
1684 |     return new Promise(function(res){
1685 |       audio.onended = function(){
1686 |         URL.revokeObjectURL(audioURL);
1687 |         setStat("Ready","#334",false);
1688 |         hideSub();
1689 |         if(d.device_name){
1690 |           setTimeout(function(){ showVisionSponsor(d.device_name); },800);
1691 |         }
1692 |         // Prompt for follow-up photo if session is active
1693 |         if (_visionSessionId) {
1694 |           showVisionStatus('Tap camera to show next screen \u2192');
1695 |           setTimeout(function() {
1696 |             hideVisionStatus();
1697 |           }, 4000);
1698 |         }
1699 |         res();
1700 |       };
1701 |       audio.onerror = function(){ URL.revokeObjectURL(audioURL); res(); };
1702 |       var vp = audio.play();
1703 |       if(vp !== undefined){
1704 |         vp.then(function(){ setStat("Speaking","#6cff9f",false); }).catch(function(){ res(); });
1705 |       }
1706 |     });
1707 |   })
1708 |   .catch(function(){
1709 |     showVisionStatus("Ready");
1710 |     setBusy(false);
1711 |     mic.disabled = false;
1712 |   });
1713 | }
1714 | 
1715 | function sendVisionImage(b64, mimeType, textOverride){
1716 |   // Text-only mode: no image, just a guided question
1717 |   if (!b64 && textOverride) {
1718 |     setBusy(true);
1719 |     showVisionStatus('Preparing guidance...');
1720 |     _speakVisionGuidance({
1721 |       guidance_text: 'I can guide you through setting up a new hardware wallet securely. First, choose a wallet: Coldcard for maximum security, Trezor for ease of use, or SeedSigner for open-source air-gapped signing. Which would you like help with?',
1722 |       device_name: 'new_wallet_setup',
1723 |       steps: [
1724 |         'Choose your hardware wallet: Coldcard, Trezor, or SeedSigner',
1725 |         'Purchase only from official manufacturer websites — never third party',
1726 |         'On first boot, generate a new seed phrase on the device itself',
1727 |         'Write seed phrase on paper only — never photograph or type it',
1728 |         'Test recovery before sending any funds'
1729 |       ]
1730 |     });
1731 |     setBusy(false);
1732 |     return;
1733 |   }
1734 | 
1735 |   setBusy(true);
1736 |   showVisionStatus("Analyzing your screen...");
1737 | 
1738 |   var endpoint = _visionSessionId ? A+"/vision/guide" : A+"/vision/analyze";
1739 |   var body = {image_base64:b64, mime_type:mimeType,
1740 |     context:"User needs Bitcoin hardware setup guidance"};
1741 |   if(_visionSessionId){
1742 |     body.session_id = _visionSessionId;
1743 |     body.question = "What step am I at and what should I do next?";
1744 |     body.last_context = _visionTranscript.length > 0
1745 |       ? _visionTranscript[_visionTranscript.length - 1].steps.join('; ')
1746 |       : '';
1747 |   }
1748 | 
1749 |   fetchTO(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
1750 |     body:JSON.stringify(body)},20000)
1751 |   .then(function(r){
1752 |     if(!r.ok) throw new Error("vision "+r.status);
1753 |     return r.json();
1754 |   })
1755 |   .then(function(d){
1756 |     _visionSessionId = d.session_id || _visionSessionId;
1757 |     updateCameraButtonState();
1758 | 
1759 |     // Security alert takes absolute priority — recovery flow keeps overlay open
1760 |     if (d.security_alert) {
1761 |       showSecurityAlert(d.security_alert);
1762 |       return;
1763 |     }
1764 |     _speakVisionGuidance(d);
1765 |   })
1766 |   .catch(function(e){
1767 |     console.error("Vision error:", e);
1768 |     showVisionStatus("Vision error — try again.");
1769 |     setTimeout(hideVisionStatus, 3000);
1770 |   })
1771 |   .finally(function(){ setBusy(false); mic.disabled=false; });
1772 | }
1773 | 
1774 | function showVisionStatus(msg){ 
1775 |   var el=document.getElementById("vision-status");
1776 |   el.textContent=msg; el.classList.add("on");
1777 | }
1778 | function hideVisionStatus(){
1779 |   var el=document.getElementById("vision-status");
1780 |   el.classList.remove("on");
1781 | }
1782 | 
1783 | /* ── VISION SESSION TRANSCRIPT ── */
1784 | var _visionTranscript = [];
1785 | 
1786 | function _addVisionEntry(deviceName, steps, guidanceText) {
1787 |   var panel = document.getElementById('vision-transcript-panel');
1788 |   var entries = document.getElementById('vision-transcript-entries');
1789 |   if (!entries) return;
1790 | 
1791 |   if (panel && _visionTranscript.length === 0) {
1792 |     panel.style.display = 'block';
1793 |   }
1794 | 
1795 |   var entry = {
1796 |     device: deviceName || 'Unknown Device',
1797 |     steps: steps || [],
1798 |     guidance: guidanceText || '',
1799 |     time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
1800 |   };
1801 |   _visionTranscript.push(entry);
1802 | 
1803 |   var el = document.createElement('div');
1804 |   el.className = 'vision-entry';
1805 | 
1806 |   var deviceEl = document.createElement('div');
1807 |   deviceEl.className = 'vision-entry-device';
1808 |   deviceEl.textContent = entry.device.toUpperCase();
1809 |   el.appendChild(deviceEl);
1810 | 
1811 |   if (entry.steps.length) {
1812 |     entry.steps.forEach(function(s, i) {
1813 |       var stepEl = document.createElement('div');
1814 |       stepEl.className = 'vision-entry-step';
1815 |       stepEl.textContent = (i+1) + '. ' + s;
1816 |       el.appendChild(stepEl);
1817 |     });
1818 |   } else if (entry.guidance) {
1819 |     var guidEl = document.createElement('div');
1820 |     guidEl.className = 'vision-entry-step';
1821 |     guidEl.textContent = entry.guidance.substring(0, 120) +
1822 |       (entry.guidance.length > 120 ? '…' : '');
1823 |     el.appendChild(guidEl);
1824 |   }
1825 | 
1826 |   var timeEl = document.createElement('div');
1827 |   timeEl.className = 'vision-entry-time';
1828 |   timeEl.textContent = entry.time + ' — tap to re-read';
1829 |   el.appendChild(timeEl);
1830 | 
1831 |   el.onclick = function() {
1832 |     var text = entry.steps.length
1833 |       ? entry.device + '. ' + entry.steps.join('. ')
1834 |       : entry.guidance;
1835 |     fetchTO(A+'/oracle/voice', {
1836 |       method: 'POST',
1837 |       headers: {'Content-Type': 'application/json'},
1838 |       body: JSON.stringify({text: text.substring(0, 200)})
1839 |     }, 20000).then(function(r) {
1840 |       return r.ok ? r.blob() : null;
1841 |     }).then(function(blob) {
1842 |       if (!blob) return;
1843 |       var a = new Audio(URL.createObjectURL(blob));
1844 |       a.volume = 1.0;
1845 |       a.play().catch(function(){});
1846 |     }).catch(function(){});
1847 |   };
1848 | 
1849 |   entries.appendChild(el);
1850 |   entries.scrollTop = entries.scrollHeight;
1851 | }
1852 | 
1853 | document.addEventListener('DOMContentLoaded', function() {
1854 |   var clearBtn = document.getElementById('vision-transcript-clear');
1855 |   if (clearBtn) {
1856 |     clearBtn.onclick = function() {
1857 |       _visionTranscript = [];
1858 |       var entries = document.getElementById('vision-transcript-entries');
1859 |       if (entries) entries.innerHTML = '';
1860 |       var panel = document.getElementById('vision-transcript-panel');
1861 |       if (panel) panel.style.display = 'none';
1862 |       _visionSessionId = null;
1863 |       updateCameraButtonState();
1864 |     };
1865 |   }
1866 | });
1867 | 
1868 | /* ── MINIMIZE / EXIT / FLOAT ── */
1869 | var _oracleMinimized = false;
1870 | 
1871 | function minimizeOracle(){
1872 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
1873 |   if(inIframe){
1874 |     try{ window.parent.postMessage({type:'oracle:minimize'},'*'); }catch(e){}
1875 |     return;
1876 |   }
1877 |   // Standalone: shrink to float bubble
1878 |   _oracleMinimized = true;
1879 |   document.getElementById("oracle-root").style.display = "none";
1880 |   var f = document.getElementById("oracle-float");
1881 |   if(f){ f.style.display = "flex"; if(busy) f.classList.add("speaking"); }
1882 | }
1883 | 
1884 | function restoreOracle(){
1885 |   _oracleMinimized = false;
1886 |   document.getElementById("oracle-float").style.display = "none";
1887 |   document.getElementById("oracle-root").style.display = "flex";
1888 |   document.getElementById("oracle-float").classList.remove("speaking");
1889 | }
1890 | 
1891 | function exitOracle(){
1892 |   // If running inside widget iframe — tell parent to close
1893 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
1894 |   if(inIframe){
1895 |     try{ window.parent.postMessage({type:'oracle:close'},'*'); }catch(e){}
1896 |     return;
1897 |   }
1898 |   // Standalone page — return to gate screen
1899 |   _oracleMinimized = false;
1900 |   // Stop any playing audio/video
1901 |   vid.pause(); vid.src="";
1902 |   if(isRec) stopRec();
1903 |   // Reset session on server
1904 |   fetch(A+"/oracle/session/reset",{method:"POST",
1905 |     headers:{"Content-Type":"application/json"},
1906 |     body:JSON.stringify({session_id:SESSION_ID})}).catch(function(){});
1907 |   // Hide everything
1908 |   document.getElementById("oracle-float").style.display = "none";
1909 |   document.getElementById("live-stage").style.display = "none";
1910 |   document.getElementById("oracle-root").style.display = "flex";
1911 |   // Show gate again
1912 |   var g = document.getElementById("gate");
1913 |   g.style.display = "flex";
1914 |   g.style.opacity = "1";
1915 |   g.style.transition = "opacity .3s";
1916 |   // Reset state
1917 |   busy = false; window._briefFetched = false;
1918 |   setStat("Ready","#334",false);
1919 |   hideSub(); hideTranscript && hideTX();
1920 | }
1921 | 
1922 | // Keep float speaking indicator in sync
1923 | var _origSetStat = setStat;
1924 | setStat = function(msg, color, spin){
1925 |   _origSetStat(msg, color, spin);
1926 |   var f = document.getElementById("oracle-float");
1927 |   if(f && _oracleMinimized){
1928 |     if(msg === "Speaking") f.classList.add("speaking");
1929 |     else f.classList.remove("speaking");
1930 |   }
1931 | };
1932 | 
1933 | /* ── ORACLE IDLE MATRIX ANIMATION ── */
1934 | (function(){
1935 |   var canvas = document.getElementById('oracle-matrix');
1936 |   if (!canvas) return;
1937 |   var ctx = canvas.getContext('2d');
1938 |   var chars = '01₿⚡∆Ω█▓░10₿Ξ∞◆'.split('');
1939 |   var cols, drops;
1940 | 
1941 |   function resize() {
1942 |     canvas.width = canvas.offsetWidth;
1943 |     canvas.height = canvas.offsetHeight;
1944 |     cols = Math.floor(canvas.width / 14);
1945 |     drops = Array(cols).fill(1);
1946 |   }
1947 |   resize();
1948 |   window.addEventListener('resize', resize);
1949 | 
1950 |   function draw() {
1951 |     ctx.fillStyle = 'rgba(4,5,8,0.05)';
1952 |     ctx.fillRect(0, 0, canvas.width, canvas.height);
1953 |     ctx.font = '11px monospace';
1954 |     for (var i = 0; i < drops.length; i++) {
1955 |       var char = chars[Math.floor(Math.random() * chars.length)];
1956 |       var alpha = Math.random() * 0.4 + 0.05;
1957 |       var cx = canvas.width / 2;
1958 |       var dist = Math.abs(i * 14 - cx) / cx;
1959 |       var r = Math.floor(180 + (1 - dist) * 75);
1960 |       var g = Math.floor(20 + (1 - dist) * 30);
1961 |       var b = Math.floor(40 + (1 - dist) * 20);
1962 |       ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
1963 |       ctx.fillText(char, i * 14, drops[i] * 14);
1964 |       if (drops[i] * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
1965 |       drops[i]++;
1966 |     }
1967 |   }
1968 | 
1969 |   var _matrixInterval = setInterval(draw, 50);
1970 | 
1971 |   window._matrixHide = function() {
1972 |     canvas.style.opacity = '0';
1973 |   };
1974 |   window._matrixShow = function() {
1975 |     canvas.style.opacity = '1';
1976 |   };
1977 | })();
1978 | 
1979 | /* ── CYBERPUNK MATRIX BACKGROUND ── */
1980 | (function(){
1981 |   var cvs=document.getElementById('bg-canvas');
1982 |   if(!cvs)return;
1983 |   var ctx=cvs.getContext('2d');
1984 |   var W,H,cols,drops,hexFrags=[];
1985 |   var matrixChars='0123456789ABCDEFabcdef₿⚡∆Ω█▓░▒╔╗╚╝║═';
1986 |   var fontSize=14;
1987 |   var scanY=-2,scanDir=1,scanTimer=0,scanInterval=15000;
1988 | 
1989 |   function resize(){
1990 |     W=cvs.width=cvs.offsetWidth;
1991 |     H=cvs.height=cvs.offsetHeight;
1992 |     cols=Math.floor(W/fontSize);
1993 |     drops=new Array(cols);
1994 |     for(var i=0;i<cols;i++) drops[i]=Math.random()*(-H/fontSize);
1995 |   }
1996 |   resize();
1997 |   window.addEventListener('resize',resize);
1998 | 
1999 |   // Hex fragments: random hex strings that fade in/out
2000 |   function spawnHex(){
2001 |     if(hexFrags.length>6) return;
2002 |     hexFrags.push({
2003 |       x:Math.random()*W,
2004 |       y:Math.random()*H,
2005 |       text:'0x'+Math.random().toString(16).substr(2,6).toUpperCase(),
2006 |       alpha:0,phase:0, // 0=fade in, 1=hold, 2=fade out
2007 |       speed:0.003+Math.random()*0.005,
2008 |       holdTime:2000+Math.random()*3000,
2009 |       holdStart:0
2010 |     });
2011 |   }
2012 | 
2013 |   var lastTime=0;
2014 |   function frame(ts){
2015 |     requestAnimationFrame(frame);
2016 |     if(!lastTime) lastTime=ts;
2017 |     var dt=ts-lastTime;
2018 |     lastTime=ts;
2019 | 
2020 |     ctx.clearRect(0,0,W,H);
2021 | 
2022 |     // 1. Falling matrix characters (sparse)
2023 |     ctx.font=fontSize+'px JetBrains Mono,monospace';
2024 |     for(var i=0;i<cols;i++){
2025 |       if(Math.random()>0.06) { // sparse: only 6% of columns draw per frame
2026 |         if(drops[i]>0){
2027 |           ctx.fillStyle='rgba(255,59,95,0.15)';
2028 |           var ch=matrixChars[Math.floor(Math.random()*matrixChars.length)];
2029 |           ctx.fillText(ch,i*fontSize,drops[i]*fontSize);
2030 |         }
2031 |       }
2032 |       drops[i]+=0.3;
2033 |       if(drops[i]*fontSize>H && Math.random()>0.98){
2034 |         drops[i]=0;
2035 |       }
2036 |     }
2037 | 
2038 |     // 2. Scan line sweep every 15s
2039 |     scanTimer+=dt;
2040 |     if(scanTimer>=scanInterval){
2041 |       scanTimer=0;
2042 |       scanY=-2;
2043 |       scanDir=1;
2044 |     }
2045 |     if(scanY>=0 && scanY<=H){
2046 |       var grad=ctx.createLinearGradient(0,scanY-8,0,scanY+8);
2047 |       grad.addColorStop(0,'rgba(255,59,95,0)');
2048 |       grad.addColorStop(0.5,'rgba(255,59,95,0.12)');
2049 |       grad.addColorStop(1,'rgba(255,59,95,0)');
2050 |       ctx.fillStyle=grad;
2051 |       ctx.fillRect(0,scanY-8,W,16);
2052 |     }
2053 |     if(scanY>=-2 && scanY<=H+10) scanY+=2;
2054 | 
2055 |     // 3. Hex fragments fade in/out
2056 |     if(Math.random()<0.008) spawnHex();
2057 |     for(var h=hexFrags.length-1;h>=0;h--){
2058 |       var frag=hexFrags[h];
2059 |       if(frag.phase===0){
2060 |         frag.alpha+=frag.speed*dt;
2061 |         if(frag.alpha>=0.2){frag.alpha=0.2;frag.phase=1;frag.holdStart=ts;}
2062 |       } else if(frag.phase===1){
2063 |         if(ts-frag.holdStart>frag.holdTime) frag.phase=2;
2064 |       } else {
2065 |         frag.alpha-=frag.speed*dt;
2066 |         if(frag.alpha<=0){hexFrags.splice(h,1);continue;}
2067 |       }
2068 |       ctx.fillStyle='rgba(255,59,95,'+frag.alpha.toFixed(3)+')';
2069 |       ctx.font='10px JetBrains Mono,monospace';
2070 |       ctx.fillText(frag.text,frag.x,frag.y);
2071 |     }
2072 |   }
2073 |   requestAnimationFrame(frame);
2074 | })();
2075 | 
2076 | function fetchTO(url,opts,ms){
2077 |   var ctrl=new AbortController();
2078 |   var id=setTimeout(function(){ctrl.abort();},ms);
2079 |   var o=opts||{};o.signal=ctrl.signal;
2080 |   return fetch(url,o).finally(function(){clearTimeout(id);})
2081 |     .catch(function(e){if(e.name==='AbortError')throw new Error('timeout');throw e;});
2082 | }
2083 | /* ── ACTION CARDS ── */
2084 | function showActionCard(card){
2085 |   var el=document.getElementById('oracle-action-card');
2086 |   var catColor = card.category==='amazon' ? '#FF9900' : card.category==='internal' ? '#6cff9f' : '#ff3b5f';
2087 |   el.innerHTML='<a href="'+card.url+'" target="_blank" rel="noopener" onclick="trackCardClick(\''+card.id+'\')" style="display:block;background:#0d0f14;border:1px solid '+catColor+';border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color 0.2s;">'
2088 |     +'<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;letter-spacing:.1em;color:'+catColor+';margin-bottom:4px;">'+card.category.toUpperCase()+'</div>'
2089 |     +'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;">'+card.title+'</div>'
2090 |     +'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-bottom:10px;">'+card.description+'</div>'
2091 |     +'<div style="font-size:11px;font-weight:600;color:'+catColor+';">'+card.cta+'</div>'
2092 |     +'</a>';
2093 |   el.style.display='block';
2094 |   el.style.opacity='0';
2095 |   setTimeout(function(){el.style.transition='opacity 0.4s';el.style.opacity='1';},100);
2096 |   setTimeout(function(){hideActionCard();},45000);
2097 | }
2098 | function showVisionSponsor(deviceName){
2099 |   if(!deviceName || deviceName==='unknown') return;
2100 |   var key=deviceName.toLowerCase();
2101 |   var match=null;
2102 |   Object.keys(VISION_SPONSOR_MAP).forEach(function(k){
2103 |     if(!match && key.indexOf(k)>=0) match=VISION_SPONSOR_MAP[k];
2104 |   });
2105 |   if(!match) return;
2106 |   showActionCard(match);
2107 | }
2108 | function hideActionCard(){
2109 |   var el=document.getElementById('oracle-action-card');
2110 |   el.style.opacity='0';
2111 |   setTimeout(function(){el.style.display='none';el.innerHTML='';},400);
2112 | }
2113 | function trackCardClick(id){
2114 |   fetch('/api/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'oracle_card_clicked',properties:{card_id:id,fingerprint:window._visitorToken||'anon'}})}).catch(function(){});
2115 | }
2116 | 
2117 | /* ── MOBILE NAV BAR ── */
2118 | (function(){
2119 |   var isMobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2120 |   if(isMobile){
2121 |     var nb=document.getElementById('mobile-nav-bar');
2122 |     if(nb) nb.style.display='flex';
2123 |   }
2124 | })();
2125 | 
2126 | window.addEventListener('beforeunload',function(){
2127 |   try{
2128 |     var xhr=new XMLHttpRequest();
2129 |     xhr.open('POST',A+'/oracle/session/save',false);
2130 |     xhr.setRequestHeader('Content-Type','application/json');
2131 |     xhr.send(JSON.stringify({session_id:SESSION_ID}));
2132 |   }catch(e){}
2133 | });
2134 | </script>
2135 | </body>
2136 | </html>
2137 | 
```

### File: templates/merch.html (1680 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Merch Store - Protocol Pulse{% endblock %}
   4 | 
   5 | {% block head %}
   6 | <!-- Open Graph -->
   7 | <meta property="og:title" content="Merch — Protocol Pulse">
   8 | <meta property="og:description" content="Gear for sovereign individuals. Bitcoin-themed apparel and accessories.">
   9 | <meta property="og:type" content="website">
  10 | <meta property="og:site_name" content="Protocol Pulse">
  11 | <meta property="og:image" content="{{ url_for('static', filename='images/protocol-pulse-logo-transparent.png', _external=True) }}">
  12 | <meta property="og:url" content="{{ request.url }}">
  13 | <meta name="twitter:card" content="summary_large_image">
  14 | <meta name="twitter:site" content="@ProtocolPulse">
  15 | <meta name="twitter:title" content="Merch — Protocol Pulse">
  16 | <meta name="twitter:description" content="Gear for sovereign individuals. Bitcoin-themed apparel and accessories.">
  17 | 
  18 | <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=JetBrains+Mono:wght@400;700&family=Uncut+Sans:wght@300;500;700&display=swap" rel="stylesheet">
  19 | 
  20 | <style>
  21 |     :root {
  22 |         --glass: rgba(255, 255, 255, 0.03);
  23 |         --glass-border: rgba(255, 255, 255, 0.08);
  24 |         --accent-red: #dc2626;
  25 |         --pure-white: #ffffff;
  26 |         --deep-black: #050505;
  27 |     }
  28 | 
  29 |     .merch-page {
  30 |         font-family: 'Uncut Sans', sans-serif;
  31 |         background-color: var(--deep-black);
  32 |         color: var(--pure-white);
  33 |         min-height: 100vh;
  34 |     }
  35 | 
  36 |     /* Cinematic Hero - Cyberpunk Edition */
  37 |     .hero-merch {
  38 |         padding: 0;
  39 |         padding-top: 60px;
  40 |         background: #030303;
  41 |         text-align: left;
  42 |         position: relative;
  43 |         overflow: hidden;
  44 |         min-height: 100vh;
  45 |         display: flex;
  46 |         align-items: center;
  47 |     }
  48 |     
  49 |     /* Cyberpunk Grid Floor */
  50 |     .cyber-grid {
  51 |         position: absolute;
  52 |         bottom: 0;
  53 |         left: 0;
  54 |         right: 0;
  55 |         height: 60%;
  56 |         background: 
  57 |             linear-gradient(transparent 0%, rgba(220, 38, 38, 0.03) 100%),
  58 |             repeating-linear-gradient(90deg, transparent, transparent 80px, rgba(220, 38, 38, 0.1) 80px, rgba(220, 38, 38, 0.1) 81px),
  59 |             repeating-linear-gradient(0deg, transparent, transparent 80px, rgba(220, 38, 38, 0.1) 80px, rgba(220, 38, 38, 0.1) 81px);
  60 |         transform: perspective(500px) rotateX(60deg);
  61 |         transform-origin: bottom center;
  62 |         animation: gridPulse 4s ease-in-out infinite;
  63 |     }
  64 |     
  65 |     @keyframes gridPulse {
  66 |         0%, 100% { opacity: 0.6; }
  67 |         50% { opacity: 1; }
  68 |     }
  69 |     
  70 |     /* Ambient Glow Orbs */
  71 |     .glow-orb {
  72 |         position: absolute;
  73 |         border-radius: 50%;
  74 |         filter: blur(80px);
  75 |         pointer-events: none;
  76 |     }
  77 |     
  78 |     .glow-orb-1 {
  79 |         width: 400px;
  80 |         height: 400px;
  81 |         background: radial-gradient(circle, rgba(220, 38, 38, 0.4) 0%, transparent 70%);
  82 |         top: 20%;
  83 |         right: 10%;
  84 |         animation: orbFloat1 8s ease-in-out infinite;
  85 |     }
  86 |     
  87 |     .glow-orb-2 {
  88 |         width: 300px;
  89 |         height: 300px;
  90 |         background: radial-gradient(circle, rgba(255, 100, 100, 0.2) 0%, transparent 70%);
  91 |         bottom: 20%;
  92 |         left: 5%;
  93 |         animation: orbFloat2 10s ease-in-out infinite;
  94 |     }
  95 |     
  96 |     @keyframes orbFloat1 {
  97 |         0%, 100% { transform: translate(0, 0) scale(1); }
  98 |         50% { transform: translate(-30px, 20px) scale(1.1); }
  99 |     }
 100 |     
 101 |     @keyframes orbFloat2 {
 102 |         0%, 100% { transform: translate(0, 0) scale(1); }
 103 |         50% { transform: translate(20px, -30px) scale(0.9); }
 104 |     }
 105 |     
 106 |     /* Main Canvas for Effects */
 107 |     #cyber-canvas {
 108 |         position: absolute;
 109 |         inset: 0;
 110 |         pointer-events: none;
 111 |         z-index: 1;
 112 |     }
 113 |     
 114 |     /* Holographic Showcase Container */
 115 |     .holo-showcase {
 116 |         position: relative;
 117 |         width: 100%;
 118 |         max-width: 500px;
 119 |         height: 500px;
 120 |         perspective: 1200px;
 121 |         z-index: 5;
 122 |     }
 123 |     
 124 |     /* 3D Rotating Prism */
 125 |     .prism-container {
 126 |         position: absolute;
 127 |         left: 50%;
 128 |         top: 50%;
 129 |         transform: translate(-50%, -50%);
 130 |         width: 280px;
 131 |         height: 280px;
 132 |         transform-style: preserve-3d;
 133 |         animation: prismRotate 20s linear infinite;
 134 |     }
 135 |     
 136 |     .prism-face {
 137 |         position: absolute;
 138 |         width: 100%;
 139 |         height: 100%;
 140 |         border: 1px solid rgba(220, 38, 38, 0.3);
 141 |         background: linear-gradient(135deg, rgba(220, 38, 38, 0.05) 0%, transparent 50%, rgba(220, 38, 38, 0.08) 100%);
 142 |         backdrop-filter: blur(2px);
 143 |     }
 144 |     
 145 |     .prism-face:nth-child(1) { transform: rotateY(0deg) translateZ(140px); }
 146 |     .prism-face:nth-child(2) { transform: rotateY(60deg) translateZ(140px); }
 147 |     .prism-face:nth-child(3) { transform: rotateY(120deg) translateZ(140px); }
 148 |     .prism-face:nth-child(4) { transform: rotateY(180deg) translateZ(140px); }
 149 |     .prism-face:nth-child(5) { transform: rotateY(240deg) translateZ(140px); }
 150 |     .prism-face:nth-child(6) { transform: rotateY(300deg) translateZ(140px); }
 151 |     
 152 |     @keyframes prismRotate {
 153 |         from { transform: translate(-50%, -50%) rotateY(0deg) rotateX(15deg); }
 154 |         to { transform: translate(-50%, -50%) rotateY(360deg) rotateX(15deg); }
 155 |     }
 156 |     
 157 |     /* Central Product Display */
 158 |     .product-core {
 159 |         position: absolute;
 160 |         left: 50%;
 161 |         top: 50%;
 162 |         transform: translate(-50%, -50%);
 163 |         z-index: 10;
 164 |         text-align: center;
 165 |     }
 166 |     
 167 |     .product-image-container {
 168 |         position: relative;
 169 |         width: 220px;
 170 |         height: 220px;
 171 |         margin: 0 auto;
 172 |         animation: coreFloat 4s ease-in-out infinite;
 173 |     }
 174 |     
 175 |     .product-image-container::before {
 176 |         content: '';
 177 |         position: absolute;
 178 |         inset: -20px;
 179 |         border: 2px solid transparent;
 180 |         border-radius: 50%;
 181 |         background: linear-gradient(45deg, rgba(220, 38, 38, 0.5), transparent, rgba(220, 38, 38, 0.5)) border-box;
 182 |         mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
 183 |         mask-composite: exclude;
 184 |         animation: ringPulse 2s ease-in-out infinite;
 185 |     }
 186 |     
 187 |     .product-image-container::after {
 188 |         content: '';
 189 |         position: absolute;
 190 |         inset: -40px;
 191 |         border: 1px solid rgba(220, 38, 38, 0.2);
 192 |         border-radius: 50%;
 193 |         animation: ringPulse 2s ease-in-out infinite 0.5s;
 194 |     }
 195 |     
 196 |     @keyframes ringPulse {
 197 |         0%, 100% { transform: scale(1); opacity: 0.5; }
 198 |         50% { transform: scale(1.05); opacity: 1; }
 199 |     }
 200 |     
 201 |     @keyframes coreFloat {
 202 |         0%, 100% { transform: translate(-50%, -50%) translateY(0); }
 203 |         50% { transform: translate(-50%, -50%) translateY(-20px); }
 204 |     }
 205 |     
 206 |     .product-core img {
 207 |         width: 200px;
 208 |         height: 200px;
 209 |         object-fit: contain;
 210 |         filter: drop-shadow(0 0 40px rgba(220, 38, 38, 0.6)) drop-shadow(0 20px 40px rgba(0,0,0,0.5));
 211 |         animation: productGlow 3s ease-in-out infinite;
 212 |         transition: all 0.5s ease;
 213 |     }
 214 |     
 215 |     @keyframes productGlow {
 216 |         0%, 100% { filter: drop-shadow(0 0 40px rgba(220, 38, 38, 0.6)) drop-shadow(0 20px 40px rgba(0,0,0,0.5)); }
 217 |         50% { filter: drop-shadow(0 0 60px rgba(220, 38, 38, 0.8)) drop-shadow(0 20px 40px rgba(0,0,0,0.5)); }
 218 |     }
 219 |     
 220 |     /* Glitch Effect on Product */
 221 |     .glitch-wrapper {
 222 |         position: relative;
 223 |     }
 224 |     
 225 |     .glitch-wrapper::before,
 226 |     .glitch-wrapper::after {
 227 |         content: '';
 228 |         position: absolute;
 229 |         inset: 0;
 230 |         background: inherit;
 231 |         opacity: 0;
 232 |     }
 233 |     
 234 |     .glitch-wrapper:hover::before {
 235 |         animation: glitch1 0.3s infinite;
 236 |         opacity: 0.8;
 237 |         clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
 238 |         transform: translate(-5px, 0);
 239 |         filter: hue-rotate(90deg);
 240 |     }
 241 |     
 242 |     .glitch-wrapper:hover::after {
 243 |         animation: glitch2 0.3s infinite;
 244 |         opacity: 0.8;
 245 |         clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
 246 |         transform: translate(5px, 0);
 247 |         filter: hue-rotate(-90deg);
 248 |     }
 249 |     
 250 |     @keyframes glitch1 {
 251 |         0%, 100% { transform: translate(-5px, 0); }
 252 |         25% { transform: translate(5px, 2px); }
 253 |         50% { transform: translate(-3px, -2px); }
 254 |         75% { transform: translate(3px, 1px); }
 255 |     }
 256 |     
 257 |     @keyframes glitch2 {
 258 |         0%, 100% { transform: translate(5px, 0); }
 259 |         25% { transform: translate(-5px, -2px); }
 260 |         50% { transform: translate(3px, 2px); }
 261 |         75% { transform: translate(-3px, -1px); }
 262 |     }
 263 |     
 264 |     /* Energy Beam */
 265 |     .energy-beam {
 266 |         position: absolute;
 267 |         left: 50%;
 268 |         bottom: 0;
 269 |         width: 4px;
 270 |         height: 100%;
 271 |         background: linear-gradient(to top, rgba(220, 38, 38, 0.8), rgba(220, 38, 38, 0.3) 30%, transparent 70%);
 272 |         transform: translateX(-50%);
 273 |         filter: blur(2px);
 274 |         animation: beamPulse 2s ease-in-out infinite;
 275 |     }
 276 |     
 277 |     .energy-beam::before {
 278 |         content: '';
 279 |         position: absolute;
 280 |         left: 50%;
 281 |         transform: translateX(-50%);
 282 |         width: 40px;
 283 |         height: 100%;
 284 |         background: linear-gradient(to top, rgba(220, 38, 38, 0.2), transparent 50%);
 285 |         filter: blur(10px);
 286 |     }
 287 |     
 288 |     @keyframes beamPulse {
 289 |         0%, 100% { opacity: 0.6; }
 290 |         50% { opacity: 1; }
 291 |     }
 292 |     
 293 |     /* HUD Elements */
 294 |     .hud-frame {
 295 |         position: absolute;
 296 |         pointer-events: none;
 297 |     }
 298 |     
 299 |     .hud-corner {
 300 |         position: absolute;
 301 |         width: 60px;
 302 |         height: 60px;
 303 |         border: 2px solid rgba(220, 38, 38, 0.4);
 304 |     }
 305 |     
 306 |     .hud-corner.tl { top: 0; left: 0; border-right: none; border-bottom: none; }
 307 |     .hud-corner.tr { top: 0; right: 0; border-left: none; border-bottom: none; }
 308 |     .hud-corner.bl { bottom: 0; left: 0; border-right: none; border-top: none; }
 309 |     .hud-corner.br { bottom: 0; right: 0; border-left: none; border-top: none; }
 310 |     
 311 |     .hud-label {
 312 |         position: absolute;
 313 |         font-family: 'JetBrains Mono', monospace;
 314 |         font-size: 0.65rem;
 315 |         color: rgba(220, 38, 38, 0.7);
 316 |         text-transform: uppercase;
 317 |         letter-spacing: 2px;
 318 |         white-space: nowrap;
 319 |     }
 320 |     
 321 |     .hud-label.top { top: -25px; left: 50%; transform: translateX(-50%); }
 322 |     .hud-label.bottom { bottom: -25px; left: 50%; transform: translateX(-50%); }
 323 |     .hud-label.left { left: -10px; top: 50%; transform: translateY(-50%) rotate(-90deg); }
 324 |     .hud-label.right { right: -10px; top: 50%; transform: translateY(-50%) rotate(90deg); }
 325 |     
 326 |     /* Scanlines Overlay */
 327 |     .scanlines {
 328 |         position: absolute;
 329 |         inset: 0;
 330 |         background: repeating-linear-gradient(
 331 |             0deg,
 332 |             transparent,
 333 |             transparent 2px,
 334 |             rgba(0, 0, 0, 0.1) 2px,
 335 |             rgba(0, 0, 0, 0.1) 4px
 336 |         );
 337 |         pointer-events: none;
 338 |         z-index: 20;
 339 |         opacity: 0.3;
 340 |     }
 341 |     
 342 |     /* Data Stream */
 343 |     .data-stream {
 344 |         position: absolute;
 345 |         font-family: 'JetBrains Mono', monospace;
 346 |         font-size: 10px;
 347 |         color: rgba(220, 38, 38, 0.4);
 348 |         writing-mode: vertical-rl;
 349 |         animation: streamFlow 8s linear infinite;
 350 |         opacity: 0.6;
 351 |     }
 352 |     
 353 |     @keyframes streamFlow {
 354 |         0% { transform: translateY(-100%); opacity: 0; }
 355 |         10% { opacity: 0.6; }
 356 |         90% { opacity: 0.6; }
 357 |         100% { transform: translateY(100vh); opacity: 0; }
 358 |     }
 359 |     
 360 |     /* Product Info Badge - Glassmorphism Sovereign Style */
 361 |     .product-badge {
 362 |         margin-top: 30px;
 363 |         padding: 12px 24px;
 364 |         background: rgba(10, 10, 10, 0.85);
 365 |         backdrop-filter: blur(12px);
 366 |         -webkit-backdrop-filter: blur(12px);
 367 |         border: 1px solid rgba(220, 38, 38, 0.2);
 368 |         border-radius: 8px;
 369 |         display: inline-block;
 370 |         font-family: 'JetBrains Mono', monospace;
 371 |         font-size: 0.75rem;
 372 |         color: var(--accent-red);
 373 |         text-transform: uppercase;
 374 |         letter-spacing: 3px;
 375 |         box-shadow: 
 376 |             inset 0 0 15px rgba(220, 38, 38, 0.05),
 377 |             0 10px 30px rgba(0, 0, 0, 0.5);
 378 |         transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
 379 |     }
 380 |     
 381 |     .product-badge:hover {
 382 |         border-color: rgba(220, 38, 38, 0.8);
 383 |         box-shadow: 
 384 |             0 0 25px rgba(220, 38, 38, 0.2),
 385 |             inset 0 0 20px rgba(220, 38, 38, 0.1);
 386 |         transform: translateY(-2px);
 387 |     }
 388 |     
 389 |     .hero-row {
 390 |         display: flex;
 391 |         align-items: center;
 392 |         gap: 4rem;
 393 |         position: relative;
 394 |         z-index: 10;
 395 |     }
 396 |     
 397 |     .hero-text {
 398 |         flex: 1;
 399 |         max-width: 500px;
 400 |     }
 401 |     
 402 |     .hero-visual {
 403 |         flex: 1.2;
 404 |         display: flex;
 405 |         justify-content: center;
 406 |         position: relative;
 407 |     }
 408 | 
 409 |     .hero-merch h1 {
 410 |         font-family: 'Uncut Sans', sans-serif;
 411 |         font-size: clamp(2.5rem, 6vw, 4.5rem);
 412 |         font-weight: 700;
 413 |         letter-spacing: -2px;
 414 |         line-height: 0.95;
 415 |         text-transform: uppercase;
 416 |         margin-bottom: 1rem;
 417 |         color: var(--pure-white);
 418 |     }
 419 | 
 420 |     .hero-merch .accent-text {
 421 |         color: var(--accent-red);
 422 |         font-family: 'JetBrains Mono', monospace;
 423 |         font-size: 0.85rem;
 424 |         text-transform: uppercase;
 425 |         letter-spacing: 4px;
 426 |         display: block;
 427 |         margin-bottom: 1rem;
 428 |     }
 429 | 
 430 |     .hero-subtitle {
 431 |         font-size: 1.15rem;
 432 |         font-weight: 300;
 433 |         color: rgba(255,255,255,0.7);
 434 |         max-width: 500px;
 435 |     }
 436 | 
 437 |     /* Bento Grid Store */
 438 |     .store-section {
 439 |         padding: 4rem 0;
 440 |         background: var(--deep-black);
 441 |     }
 442 | 
 443 |     .section-label {
 444 |         color: var(--accent-red);
 445 |         font-family: 'JetBrains Mono', monospace;
 446 |         font-size: 0.8rem;
 447 |         text-transform: uppercase;
 448 |         letter-spacing: 4px;
 449 |         margin-bottom: 2rem;
 450 |         display: block;
 451 |     }
 452 | 
 453 |     .products-grid {
 454 |         display: grid;
 455 |         grid-template-columns: repeat(4, 1fr);
 456 |         gap: 1.5rem;
 457 |     }
 458 | 
 459 |     .product-card {
 460 |         background: var(--glass);
 461 |         backdrop-filter: blur(12px);
 462 |         -webkit-backdrop-filter: blur(12px);
 463 |         border: 1px solid var(--glass-border);
 464 |         border-radius: 24px;
 465 |         overflow: hidden;
 466 |         transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
 467 |         position: relative;
 468 |     }
 469 | 
 470 |     .product-card:hover {
 471 |         border-color: var(--accent-red);
 472 |         transform: scale(1.03) translateY(-8px);
 473 |         box-shadow: 0 30px 60px rgba(220, 38, 38, 0.2), 0 0 40px rgba(220, 38, 38, 0.1);
 474 |     }
 475 | 
 476 |     .product-image-wrapper {
 477 |         position: relative;
 478 |         height: 280px;
 479 |         background: linear-gradient(180deg, #0a0a0a 0%, #151515 100%);
 480 |         display: flex;
 481 |         align-items: center;
 482 |         justify-content: center;
 483 |         overflow: hidden;
 484 |     }
 485 | 
 486 |     .product-image-wrapper::before {
 487 |         content: '';
 488 |         position: absolute;
 489 |         inset: 0;
 490 |         background: radial-gradient(ellipse at 50% 0%, rgba(220, 38, 38, 0.08) 0%, transparent 60%);
 491 |         pointer-events: none;
 492 |         z-index: 1;
 493 |     }
 494 | 
 495 |     .product-image-wrapper img {
 496 |         max-height: 240px;
 497 |         max-width: 90%;
 498 |         object-fit: contain;
 499 |         transition: transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
 500 |         filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.6));
 501 |     }
 502 | 
 503 |     .product-card:hover .product-image-wrapper img {
 504 |         transform: scale(1.1) rotate(-2deg);
 505 |     }
 506 | 
 507 |     .product-body {
 508 |         padding: 1.5rem;
 509 |     }
 510 | 
 511 |     .product-name {
 512 |         font-family: 'Crimson Pro', serif;
 513 |         font-size: 1.2rem;
 514 |         font-weight: 600;
 515 |         margin-bottom: 0.5rem;
 516 |         line-height: 1.3;
 517 |         color: var(--pure-white);
 518 |     }
 519 | 
 520 |     .product-price {
 521 |         font-family: 'JetBrains Mono', monospace;
 522 |         font-size: 1.1rem;
 523 |         font-weight: 700;
 524 |         color: var(--accent-red);
 525 |         margin-bottom: 1rem;
 526 |     }
 527 | 
 528 |     .product-variants {
 529 |         font-size: 0.75rem;
 530 |         color: rgba(255,255,255,0.5);
 531 |         margin-bottom: 1rem;
 532 |         font-family: 'JetBrains Mono', monospace;
 533 |     }
 534 | 
 535 |     .btn-buy {
 536 |         background: transparent;
 537 |         border: 1px solid var(--glass-border);
 538 |         color: var(--pure-white);
 539 |         padding: 0.85rem 1.5rem;
 540 |         border-radius: 50px;
 541 |         font-weight: 600;
 542 |         font-size: 0.85rem;
 543 |         text-decoration: none;
 544 |         display: flex;
 545 |         align-items: center;
 546 |         justify-content: center;
 547 |         gap: 0.5rem;
 548 |         transition: all 0.3s ease;
 549 |         width: 100%;
 550 |         cursor: pointer;
 551 |     }
 552 | 
 553 |     .btn-buy:hover {
 554 |         background: var(--accent-red);
 555 |         color: var(--pure-white);
 556 |         border-color: var(--accent-red);
 557 |         box-shadow: 0 0 20px rgba(220, 38, 38, 0.4);
 558 |     }
 559 | 
 560 |     /* Empty State */
 561 |     .empty-state {
 562 |         text-align: center;
 563 |         padding: 6rem 2rem;
 564 |         background: var(--glass);
 565 |         border: 1px solid var(--glass-border);
 566 |         border-radius: 32px;
 567 |     }
 568 | 
 569 |     .empty-state i {
 570 |         font-size: 4rem;
 571 |         color: var(--accent-red);
 572 |         margin-bottom: 1.5rem;
 573 |     }
 574 | 
 575 |     .empty-state h2 {
 576 |         font-family: 'Uncut Sans', sans-serif;
 577 |         font-size: 2rem;
 578 |         font-weight: 700;
 579 |         margin-bottom: 1rem;
 580 |     }
 581 | 
 582 |     .empty-state p {
 583 |         color: rgba(255,255,255,0.6);
 584 |         max-width: 500px;
 585 |         margin: 0 auto 2rem;
 586 |     }
 587 | 
 588 |     /* Product Modal */
 589 |     .product-modal {
 590 |         position: fixed;
 591 |         inset: 0;
 592 |         background: rgba(5,5,5,0.95);
 593 |         z-index: 9999;
 594 |         display: none;
 595 |         padding: 2rem;
 596 |         backdrop-filter: blur(20px);
 597 |         overflow-y: auto;
 598 |     }
 599 | 
 600 |     .product-modal.active {
 601 |         display: flex;
 602 |         align-items: center;
 603 |         justify-content: center;
 604 |     }
 605 | 
 606 |     .modal-content {
 607 |         background: linear-gradient(145deg, rgba(15,15,15,1) 0%, rgba(25,25,25,1) 100%);
 608 |         border: 1px solid var(--glass-border);
 609 |         border-radius: 32px;
 610 |         max-width: 900px;
 611 |         width: 100%;
 612 |         display: grid;
 613 |         grid-template-columns: 1fr 1fr;
 614 |         overflow: hidden;
 615 |     }
 616 | 
 617 |     .modal-image {
 618 |         background: linear-gradient(180deg, #0a0a0a 0%, #151515 100%);
 619 |         display: flex;
 620 |         align-items: center;
 621 |         justify-content: center;
 622 |         padding: 3rem;
 623 |         min-height: 400px;
 624 |     }
 625 | 
 626 |     .modal-image img {
 627 |         max-width: 100%;
 628 |         max-height: 350px;
 629 |         object-fit: contain;
 630 |         filter: drop-shadow(0 30px 50px rgba(0, 0, 0, 0.8));
 631 |     }
 632 | 
 633 |     .modal-details {
 634 |         padding: 3rem;
 635 |         display: flex;
 636 |         flex-direction: column;
 637 |     }
 638 | 
 639 |     .modal-close {
 640 |         position: absolute;
 641 |         top: 2rem;
 642 |         right: 2rem;
 643 |         background: none;
 644 |         border: none;
 645 |         color: rgba(255,255,255,0.5);
 646 |         font-size: 2rem;
 647 |         cursor: pointer;
 648 |         transition: color 0.3s ease;
 649 |     }
 650 | 
 651 |     .modal-close:hover {
 652 |         color: var(--pure-white);
 653 |     }
 654 | 
 655 |     .modal-name {
 656 |         font-family: 'Crimson Pro', serif;
 657 |         font-size: 2rem;
 658 |         font-weight: 700;
 659 |         margin-bottom: 0.5rem;
 660 |     }
 661 | 
 662 |     .modal-price {
 663 |         font-family: 'JetBrains Mono', monospace;
 664 |         font-size: 1.5rem;
 665 |         font-weight: 700;
 666 |         color: var(--accent-red);
 667 |         margin-bottom: 1.5rem;
 668 |     }
 669 | 
 670 |     .modal-description {
 671 |         color: rgba(255,255,255,0.7);
 672 |         line-height: 1.7;
 673 |         margin-bottom: 2rem;
 674 |         flex-grow: 1;
 675 |     }
 676 | 
 677 |     .variant-selector {
 678 |         margin-bottom: 2rem;
 679 |     }
 680 | 
 681 |     .variant-selector label {
 682 |         font-family: 'JetBrains Mono', monospace;
 683 |         font-size: 0.75rem;
 684 |         text-transform: uppercase;
 685 |         letter-spacing: 2px;
 686 |         color: rgba(255,255,255,0.5);
 687 |         display: block;
 688 |         margin-bottom: 0.75rem;
 689 |     }
 690 | 
 691 |     .variant-options {
 692 |         display: flex;
 693 |         flex-wrap: wrap;
 694 |         gap: 0.5rem;
 695 |     }
 696 | 
 697 |     .variant-btn {
 698 |         background: var(--glass);
 699 |         border: 1px solid var(--glass-border);
 700 |         color: var(--pure-white);
 701 |         padding: 0.5rem 1rem;
 702 |         border-radius: 8px;
 703 |         font-size: 0.85rem;
 704 |         cursor: pointer;
 705 |         transition: all 0.3s ease;
 706 |     }
 707 | 
 708 |     .variant-btn:hover, .variant-btn.active {
 709 |         border-color: var(--accent-red);
 710 |         background: rgba(220, 38, 38, 0.15);
 711 |     }
 712 | 
 713 |     .btn-purchase {
 714 |         background: var(--accent-red);
 715 |         border: none;
 716 |         color: var(--pure-white);
 717 |         padding: 1rem 2rem;
 718 |         border-radius: 50px;
 719 |         font-weight: 700;
 720 |         font-size: 1rem;
 721 |         cursor: pointer;
 722 |         transition: all 0.3s ease;
 723 |         display: flex;
 724 |         align-items: center;
 725 |         justify-content: center;
 726 |         gap: 0.75rem;
 727 |     }
 728 | 
 729 |     .btn-purchase:hover {
 730 |         background: #b91c1c;
 731 |         box-shadow: 0 0 30px rgba(220, 38, 38, 0.5);
 732 |         transform: translateY(-2px);
 733 |     }
 734 | 
 735 |     /* Responsive */
 736 |     @media (max-width: 1200px) {
 737 |         .products-grid {
 738 |             grid-template-columns: repeat(3, 1fr);
 739 |         }
 740 |     }
 741 | 
 742 |     @media (max-width: 992px) {
 743 |         .products-grid {
 744 |             grid-template-columns: repeat(2, 1fr);
 745 |         }
 746 |         
 747 |         .modal-content {
 748 |             grid-template-columns: 1fr;
 749 |         }
 750 |         
 751 |         .modal-image {
 752 |             min-height: 300px;
 753 |         }
 754 |     }
 755 | 
 756 |     /* Hero Stats */
 757 |     .hero-stats {
 758 |         display: flex;
 759 |         gap: 2rem;
 760 |         margin-top: 2rem;
 761 |     }
 762 |     
 763 |     .stat-item {
 764 |         text-align: center;
 765 |     }
 766 |     
 767 |     .stat-value {
 768 |         display: block;
 769 |         font-family: 'JetBrains Mono', monospace;
 770 |         font-size: 1.5rem;
 771 |         font-weight: 700;
 772 |         color: var(--accent-red);
 773 |         text-shadow: 0 0 20px rgba(220, 38, 38, 0.5);
 774 |     }
 775 |     
 776 |     .stat-label {
 777 |         font-size: 0.7rem;
 778 |         text-transform: uppercase;
 779 |         letter-spacing: 2px;
 780 |         color: rgba(255, 255, 255, 0.5);
 781 |     }
 782 |     
 783 |     /* Typing Animation */
 784 |     .typing-text {
 785 |         border-right: 2px solid var(--accent-red);
 786 |         animation: blink 0.7s step-end infinite;
 787 |     }
 788 |     
 789 |     @keyframes blink {
 790 |         50% { border-color: transparent; }
 791 |     }
 792 | 
 793 |     @media (max-width: 992px) {
 794 |         .hero-row {
 795 |             flex-direction: column;
 796 |             text-align: center;
 797 |         }
 798 |         
 799 |         .hero-visual {
 800 |             order: -1;
 801 |             margin-bottom: 2rem;
 802 |         }
 803 |         
 804 |         .hero-subtitle {
 805 |             margin: 0 auto;
 806 |         }
 807 |         
 808 |         .hero-stats {
 809 |             justify-content: center;
 810 |         }
 811 |         
 812 |         .holo-showcase {
 813 |             height: 400px;
 814 |             max-width: 400px;
 815 |         }
 816 |         
 817 |         .prism-container {
 818 |             width: 220px;
 819 |             height: 220px;
 820 |         }
 821 |         
 822 |         .prism-face:nth-child(1) { transform: rotateY(0deg) translateZ(110px); }
 823 |         .prism-face:nth-child(2) { transform: rotateY(60deg) translateZ(110px); }
 824 |         .prism-face:nth-child(3) { transform: rotateY(120deg) translateZ(110px); }
 825 |         .prism-face:nth-child(4) { transform: rotateY(180deg) translateZ(110px); }
 826 |         .prism-face:nth-child(5) { transform: rotateY(240deg) translateZ(110px); }
 827 |         .prism-face:nth-child(6) { transform: rotateY(300deg) translateZ(110px); }
 828 |         
 829 |         .product-core img {
 830 |             width: 160px;
 831 |             height: 160px;
 832 |         }
 833 |         
 834 |         .product-image-container {
 835 |             width: 180px;
 836 |             height: 180px;
 837 |         }
 838 |     }
 839 | 
 840 |     @media (max-width: 768px) {
 841 |         .hero-merch {
 842 |             padding-top: 70px;
 843 |             min-height: auto;
 844 |             padding-bottom: 2rem;
 845 |         }
 846 |         
 847 |         .hero-merch h1 {
 848 |             font-size: 2rem;
 849 |             letter-spacing: -1px;
 850 |         }
 851 |         
 852 |         .products-grid {
 853 |             grid-template-columns: 1fr;
 854 |         }
 855 |         
 856 |         .product-image-wrapper {
 857 |             height: 220px;
 858 |         }
 859 |         
 860 |         .holo-showcase {
 861 |             height: 200px;
 862 |             max-width: 200px;
 863 |             margin: 0 auto;
 864 |         }
 865 |         
 866 |         .prism-container {
 867 |             width: 110px;
 868 |             height: 110px;
 869 |         }
 870 |         
 871 |         .prism-face:nth-child(1) { transform: rotateY(0deg) translateZ(55px); }
 872 |         .prism-face:nth-child(2) { transform: rotateY(60deg) translateZ(55px); }
 873 |         .prism-face:nth-child(3) { transform: rotateY(120deg) translateZ(55px); }
 874 |         .prism-face:nth-child(4) { transform: rotateY(180deg) translateZ(55px); }
 875 |         .prism-face:nth-child(5) { transform: rotateY(240deg) translateZ(55px); }
 876 |         .prism-face:nth-child(6) { transform: rotateY(300deg) translateZ(55px); }
 877 |         
 878 |         .product-core img {
 879 |             width: 72px;
 880 |             height: 72px;
 881 |         }
 882 |         
 883 |         .product-image-container {
 884 |             width: 85px;
 885 |             height: 85px;
 886 |         }
 887 |         
 888 |         .hud-label, .data-stream {
 889 |             display: none;
 890 |         }
 891 |         
 892 |         .hero-stats {
 893 |             gap: 1rem;
 894 |         }
 895 |         
 896 |         .stat-value {
 897 |             font-size: 1.2rem;
 898 |         }
 899 |         
 900 |         .glow-orb-1, .glow-orb-2 {
 901 |             width: 200px;
 902 |             height: 200px;
 903 |         }
 904 |     }
 905 | 
 906 |     /* ============================================
 907 |        RTSA - Real-Time Sovereign Apparel Section
 908 |        ============================================ */
 909 |     .rtsa-section {
 910 |         padding: 4rem 0;
 911 |         background: linear-gradient(180deg, rgba(220, 38, 38, 0.03) 0%, var(--deep-black) 100%);
 912 |         border-top: 1px solid rgba(220, 38, 38, 0.2);
 913 |         position: relative;
 914 |         overflow: hidden;
 915 |     }
 916 | 
 917 |     .rtsa-section::before {
 918 |         content: '';
 919 |         position: absolute;
 920 |         top: 0;
 921 |         left: 0;
 922 |         right: 0;
 923 |         height: 2px;
 924 |         background: linear-gradient(90deg, transparent, var(--accent-red), transparent);
 925 |         animation: scanLine 3s linear infinite;
 926 |     }
 927 | 
 928 |     @keyframes scanLine {
 929 |         0% { transform: translateX(-100%); }
 930 |         100% { transform: translateX(100%); }
 931 |     }
 932 | 
 933 |     .rtsa-header {
 934 |         display: flex;
 935 |         align-items: center;
 936 |         justify-content: space-between;
 937 |         margin-bottom: 2rem;
 938 |     }
 939 | 
 940 |     .rtsa-label {
 941 |         display: flex;
 942 |         align-items: center;
 943 |         gap: 0.75rem;
 944 |     }
 945 | 
 946 |     .rtsa-label span {
 947 |         color: var(--accent-red);
 948 |         font-family: 'JetBrains Mono', monospace;
 949 |         font-size: 0.8rem;
 950 |         text-transform: uppercase;
 951 |         letter-spacing: 4px;
 952 |     }
 953 | 
 954 |     .rtsa-pulse {
 955 |         width: 8px;
 956 |         height: 8px;
 957 |         background: var(--accent-red);
 958 |         border-radius: 50%;
 959 |         animation: rtsaPulse 1.5s ease-in-out infinite;
 960 |     }
 961 | 
 962 |     @keyframes rtsaPulse {
 963 |         0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--accent-red); }
 964 |         50% { opacity: 0.3; box-shadow: 0 0 5px var(--accent-red); }
 965 |     }
 966 | 
 967 |     .rtsa-grid {
 968 |         display: grid;
 969 |         grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
 970 |         gap: 1.5rem;
 971 |     }
 972 | 
 973 |     .rtsa-card {
 974 |         background: rgba(0, 0, 0, 0.6);
 975 |         border: 1px solid rgba(220, 38, 38, 0.3);
 976 |         border-radius: 12px;
 977 |         padding: 1.5rem;
 978 |         position: relative;
 979 |         overflow: hidden;
 980 |         transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
 981 |     }
 982 | 
 983 |     .rtsa-card.hot {
 984 |         animation: hotFlicker 0.15s ease-in-out infinite alternate;
 985 |     }
 986 | 
 987 |     @keyframes hotFlicker {
 988 |         0% { 
 989 |             border-color: rgba(220, 38, 38, 0.4);
 990 |             box-shadow: 0 0 15px rgba(220, 38, 38, 0.2);
 991 |         }
 992 |         100% { 
 993 |             border-color: rgba(220, 38, 38, 0.9);
 994 |             box-shadow: 0 0 30px rgba(220, 38, 38, 0.5);
 995 |         }
 996 |     }
 997 | 
 998 |     .rtsa-card::before {
 999 |         content: '';
1000 |         position: absolute;
1001 |         top: 0;
1002 |         left: 0;
1003 |         right: 0;
1004 |         height: 3px;
1005 |         background: linear-gradient(90deg, var(--accent-red), #ff6b6b, var(--accent-red));
1006 |         animation: borderPulse 2s ease-in-out infinite;
1007 |     }
1008 | 
1009 |     @keyframes borderPulse {
1010 |         0%, 100% { opacity: 0.5; }
1011 |         50% { opacity: 1; }
1012 |     }
1013 | 
1014 |     .rtsa-card:hover {
1015 |         transform: translateY(-5px);
1016 |         border-color: var(--accent-red);
1017 |         box-shadow: 
1018 |             0 20px 40px rgba(0, 0, 0, 0.4),
1019 |             0 0 40px rgba(220, 38, 38, 0.3);
1020 |     }
1021 | 
1022 |     .rtsa-badge {
1023 |         position: absolute;
1024 |         top: 1rem;
1025 |         right: 1rem;
1026 |         background: var(--accent-red);
1027 |         color: white;
1028 |         padding: 4px 10px;
1029 |         border-radius: 4px;
1030 |         font-family: 'JetBrains Mono', monospace;
1031 |         font-size: 0.6rem;
1032 |         text-transform: uppercase;
1033 |         letter-spacing: 1px;
1034 |         animation: badgeGlow 1s ease-in-out infinite alternate;
1035 |     }
1036 | 
1037 |     @keyframes badgeGlow {
1038 |         0% { box-shadow: 0 0 5px var(--accent-red); }
1039 |         100% { box-shadow: 0 0 15px var(--accent-red); }
1040 |     }
1041 | 
1042 |     .rtsa-statement {
1043 |         font-family: 'JetBrains Mono', monospace;
1044 |         font-size: 1.1rem;
1045 |         font-weight: 700;
1046 |         color: var(--pure-white);
1047 |         margin-bottom: 1rem;
1048 |         letter-spacing: 1px;
1049 |     }
1050 | 
1051 |     .rtsa-meta {
1052 |         font-size: 0.75rem;
1053 |         color: rgba(255, 255, 255, 0.5);
1054 |         margin-bottom: 1rem;
1055 |     }
1056 | 
1057 |     .rtsa-meta span {
1058 |         margin-right: 1rem;
1059 |     }
1060 | 
1061 |     .rtsa-sarah {
1062 |         font-style: italic;
1063 |         color: rgba(255, 255, 255, 0.6);
1064 |         font-size: 0.8rem;
1065 |         padding: 0.75rem;
1066 |         background: rgba(220, 38, 38, 0.05);
1067 |         border-left: 2px solid var(--accent-red);
1068 |         margin-bottom: 1rem;
1069 |     }
1070 | 
1071 |     .rtsa-btn {
1072 |         width: 100%;
1073 |         padding: 0.75rem 1.5rem;
1074 |         background: linear-gradient(135deg, var(--accent-red), #991b1b);
1075 |         border: none;
1076 |         border-radius: 6px;
1077 |         color: white;
1078 |         font-family: 'JetBrains Mono', monospace;
1079 |         font-size: 0.8rem;
1080 |         text-transform: uppercase;
1081 |         letter-spacing: 2px;
1082 |         cursor: pointer;
1083 |         transition: all 0.3s ease;
1084 |         display: flex;
1085 |         align-items: center;
1086 |         justify-content: center;
1087 |         gap: 0.5rem;
1088 |     }
1089 | 
1090 |     .rtsa-btn:hover {
1091 |         transform: translateY(-2px);
1092 |         box-shadow: 0 10px 30px rgba(220, 38, 38, 0.4);
1093 |     }
1094 | 
1095 |     .rtsa-empty {
1096 |         text-align: center;
1097 |         padding: 3rem;
1098 |         color: rgba(255, 255, 255, 0.4);
1099 |     }
1100 | 
1101 |     .rtsa-empty i {
1102 |         font-size: 2.5rem;
1103 |         margin-bottom: 1rem;
1104 |         color: rgba(220, 38, 38, 0.3);
1105 |     }
1106 | 
1107 |     @media (max-width: 768px) {
1108 |         .rtsa-grid {
1109 |             grid-template-columns: 1fr;
1110 |         }
1111 |     }
1112 | </style>
1113 | {% endblock %}
1114 | 
1115 | {% block content %}
1116 | <div class="merch-page">
1117 |     <!-- Cinematic Hero - Cyberpunk Edition -->
1118 |     <section class="hero-merch">
1119 |         <!-- Background Effects -->
1120 |         <div class="cyber-grid"></div>
1121 |         <div class="glow-orb glow-orb-1"></div>
1122 |         <div class="glow-orb glow-orb-2"></div>
1123 |         <canvas id="cyber-canvas"></canvas>
1124 |         <div class="scanlines"></div>
1125 |         
1126 |         <!-- Data Streams -->
1127 |         <div class="data-stream" style="left: 5%; animation-delay: 0s;">01001000 01000101 01001100</div>
1128 |         <div class="data-stream" style="left: 15%; animation-delay: 2s;">10110100 11001010 00101101</div>
1129 |         <div class="data-stream" style="right: 10%; animation-delay: 4s;">11010010 01010111 10010100</div>
1130 |         <div class="data-stream" style="right: 20%; animation-delay: 1s;">00101011 10101010 01101001</div>
1131 |         
1132 |         <div class="container">
1133 |             <div class="hero-row">
1134 |                 <div class="hero-text">
1135 |                     <span class="accent-text"><span class="typing-text">// INITIALIZING STORE_PROTOCOL</span></span>
1136 |                     <h1>The Protocol<br>Pulse Store.</h1>
1137 |                     <p class="hero-subtitle">Premium merchandise for the Bitcoin revolution. Wear the signal. Own the network.</p>
1138 |                     <div class="hero-stats">
1139 |                         <div class="stat-item">
1140 |                             <span class="stat-value" id="stat-items">--</span>
1141 |                             <span class="stat-label">Items</span>
1142 |                         </div>
1143 |                         <div class="stat-item">
1144 |                             <span class="stat-value">100%</span>
1145 |                             <span class="stat-label">Authentic</span>
1146 |                         </div>
1147 |                         <div class="stat-item">
1148 |                             <span class="stat-value">BTC</span>
1149 |                             <span class="stat-label">Accepted</span>
1150 |                         </div>
1151 |                     </div>
1152 |                 </div>
1153 |                 <div class="hero-visual">
1154 |                     <div class="holo-showcase">
1155 |                         <!-- HUD Frame -->
1156 |                         <div class="hud-frame">
1157 |                             <div class="hud-corner tl"></div>
1158 |                             <div class="hud-corner tr"></div>
1159 |                             <div class="hud-corner bl"></div>
1160 |                             <div class="hud-corner br"></div>
1161 |                             <div class="hud-label top">Product Visualization</div>
1162 |                             <div class="hud-label bottom">Protocol Pulse // Official Merch</div>
1163 |                         </div>
1164 |                         
1165 |                         <!-- 3D Prism -->
1166 |                         <div class="prism-container">
1167 |                             <div class="prism-face"></div>
1168 |                             <div class="prism-face"></div>
1169 |                             <div class="prism-face"></div>
1170 |                             <div class="prism-face"></div>
1171 |                             <div class="prism-face"></div>
1172 |                             <div class="prism-face"></div>
1173 |                         </div>
1174 |                         
1175 |                         <!-- Energy Beam -->
1176 |                         <div class="energy-beam"></div>
1177 |                         
1178 |                         <!-- Central Product -->
1179 |                         <div class="product-core">
1180 |                             <div class="product-image-container glitch-wrapper">
1181 |                                 <img src="/static/images/book-placeholder.svg" alt="Featured Product" id="featured-product-img">
1182 |                             </div>
1183 |                             <div class="product-badge">Verified Authentic</div>
1184 |                         </div>
1185 |                     </div>
1186 |                 </div>
1187 |             </div>
1188 |         </div>
1189 |     </section>
1190 | 
1191 |     <!-- RTSA - Real-Time Signal Drops (Server-Rendered) -->
1192 |     <section class="rtsa-section" id="rtsaSection">
1193 |         <div class="container">
1194 |             <div class="rtsa-header">
1195 |                 <div class="rtsa-label">
1196 |                     <div class="rtsa-pulse"></div>
1197 |                     <span>Real-Time Signal</span>
1198 |                 </div>
1199 |             </div>
1200 |             
1201 |             <div class="rtsa-grid" id="rtsaGrid">
1202 |                 {% if rtsa_hot %}
1203 |                     {% for product in rtsa_hot %}
1204 |                     <div class="rtsa-card hot">
1205 |                         <span class="rtsa-badge"><i class="fas fa-fire"></i> LIVE DROP</span>
1206 |                         <div class="rtsa-statement">"{{ product.statement_text }}"</div>
1207 |                         <div class="rtsa-meta">
1208 |                             <span><i class="fas fa-tag"></i> {{ product.trigger_state or 'NETWORK' }}</span>
1209 |                             {% if product.sentiment_score %}
1210 |                             <span><i class="fas fa-chart-line"></i> {{ product.sentiment_score|round|int }}%</span>
1211 |                             {% endif %}
1212 |                         </div>
1213 |                         {% if product.sarah_description %}
1214 |                         <div class="rtsa-sarah">
1215 |                             <strong>Sarah:</strong> {{ product.sarah_description }}
1216 |                         </div>
1217 |                         {% endif %}
1218 |                         <a href="https://proto-p.printful.me" class="rtsa-btn" target="_blank">
1219 |                             <i class="fas fa-tshirt"></i> View Apparel
1220 |                         </a>
1221 |                     </div>
1222 |                     {% endfor %}
1223 |                 {% endif %}
1224 |                 
1225 |                 {% if rtsa_approved %}
1226 |                     {% for product in rtsa_approved %}
1227 |                     <div class="rtsa-card">
1228 |                         <div class="rtsa-statement">"{{ product.statement_text }}"</div>
1229 |                         <div class="rtsa-meta">
1230 |                             <span><i class="fas fa-tag"></i> {{ product.trigger_state or 'NETWORK' }}</span>
1231 |                             {% if product.sentiment_score %}
1232 |                             <span><i class="fas fa-chart-line"></i> {{ product.sentiment_score|round|int }}%</span>
1233 |                             {% endif %}
1234 |                         </div>
1235 |                         {% if product.sarah_description %}
1236 |                         <div class="rtsa-sarah">
1237 |                             <strong>Sarah:</strong> {{ product.sarah_description }}
1238 |                         </div>
1239 |                         {% endif %}
1240 |                         <a href="https://proto-p.printful.me" class="rtsa-btn" target="_blank">
1241 |                             <i class="fas fa-tshirt"></i> View Apparel
1242 |                         </a>
1243 |                     </div>
1244 |                     {% endfor %}
1245 |                 {% endif %}
1246 |                 
1247 |                 {% if not rtsa_hot and not rtsa_approved %}
1248 |                     {% if rtsa_foundational %}
1249 |                         {% for statement in rtsa_foundational[:3] %}
1250 |                         <div class="rtsa-card">
1251 |                             <div class="rtsa-statement">"{{ statement.statement }}"</div>
1252 |                             <div class="rtsa-meta">
1253 |                                 <span><i class="fas fa-landmark"></i> FOUNDATIONAL</span>
1254 |                                 <span style="color: {{ 'var(--accent-red)' if statement.text_color == '#DC2626' else 'white' }};">
1255 |                                     <i class="fas fa-tshirt"></i> {{ 'Badge' if statement.placement == 'left_chest_badge' else 'Center' }}
1256 |                                 </span>
1257 |                             </div>
1258 |                             <div class="rtsa-sarah">
1259 |                                 <strong>Sarah:</strong> {{ statement.sarah_note }}
1260 |                             </div>
1261 |                             <a href="https://proto-p.printful.me" class="rtsa-btn" target="_blank">
1262 |                                 <i class="fas fa-tshirt"></i> View Apparel
1263 |                             </a>
1264 |                         </div>
1265 |                         {% endfor %}
1266 |                     {% else %}
1267 |                     <div class="rtsa-empty" id="rtsaEmpty">
1268 |                         <i class="fas fa-satellite-dish"></i>
1269 |                         <p>No real-time signals detected. Network state stable.</p>
1270 |                     </div>
1271 |                     {% endif %}
1272 |                 {% endif %}
1273 |             </div>
1274 |         </div>
1275 |     </section>
1276 | 
1277 |     <!-- Products Grid -->
1278 |     <section class="store-section">
1279 |         <div class="container">
1280 |             <span class="section-label">Official Merchandise</span>
1281 |             
1282 |             {% if products and products|length > 0 %}
1283 |             <div class="products-grid">
1284 |                 {% for product in products %}
1285 |                 <div class="product-card" data-product-id="{{ product.id }}">
1286 |                     <div class="product-image-wrapper">
1287 |                         {% if product.main_image or product.thumbnail %}
1288 |                         <img src="{{ product.main_image or product.thumbnail }}" 
1289 |                              alt="{{ product.name }}" 
1290 |                              loading="lazy"
1291 |                              onerror="this.onerror=null; this.src='/static/images/book-placeholder.svg';">
1292 |                         {% else %}
1293 |                         <img src="/static/images/book-placeholder.svg" alt="{{ product.name }}" loading="lazy">
1294 |                         {% endif %}
1295 |                     </div>
1296 |                     <div class="product-body">
1297 |                         <h3 class="product-name">{{ product.name }}</h3>
1298 |                         {% if product.variants and product.variants|length > 0 %}
1299 |                         <div class="product-price">${{ product.variants[0].price }} {{ product.variants[0].currency }}</div>
1300 |                         <div class="product-variants">{{ product.variants|length }} variant{{ 's' if product.variants|length > 1 else '' }} available</div>
1301 |                         {% else %}
1302 |                         <div class="product-price">Price TBD</div>
1303 |                         {% endif %}
1304 |                         <button class="btn-buy" data-product='{{ product|tojson|e }}' onclick="openProductFromBtn(this)">
1305 |                             <i class="fas fa-shopping-cart"></i>Buy Now
1306 |                         </button>
1307 |                     </div>
1308 |                 </div>
1309 |                 {% endfor %}
1310 |             </div>
1311 |             {% else %}
1312 |             <div class="empty-state">
1313 |                 <i class="fas fa-box-open"></i>
1314 |                 <h2>Store Loading...</h2>
1315 |                 <p>Our merchandise collection is being prepared. Check back soon for exclusive Protocol Pulse gear.</p>
1316 |                 <a href="{{ url_for('index') }}" class="btn-buy" style="display: inline-flex; width: auto;">
1317 |                     <i class="fas fa-home"></i>Back to Home
1318 |                 </a>
1319 |             </div>
1320 |             {% endif %}
1321 |         </div>
1322 |     </section>
1323 | </div>
1324 | 
1325 | <!-- Product Detail Modal -->
1326 | <div id="productModal" class="product-modal">
1327 |     <button class="modal-close" onclick="closeProductModal()">&times;</button>
1328 |     <div class="modal-content">
1329 |         <div class="modal-image">
1330 |             <img id="modalImage" src="/static/images/book-placeholder.svg" alt="Product">
1331 |         </div>
1332 |         <div class="modal-details">
1333 |             <h2 id="modalName" class="modal-name">Product Name</h2>
1334 |             <div id="modalPrice" class="modal-price">$0.00</div>
1335 |             <p id="modalDescription" class="modal-description">Product description will appear here.</p>
1336 |             
1337 |             <div class="variant-selector" id="variantSelector" style="display: none;">
1338 |                 <label>Select Size</label>
1339 |                 <div class="variant-options" id="variantOptions"></div>
1340 |             </div>
1341 |             
1342 |             <button class="btn-purchase" id="purchaseBtn" onclick="purchaseProduct()">
1343 |                 <i class="fas fa-shopping-cart"></i>Buy Now
1344 |             </button>
1345 |         </div>
1346 |     </div>
1347 | </div>
1348 | 
1349 | <script>
1350 | // Advanced Cyber Canvas - Particle Rain & Energy Effects
1351 | const cyberCanvas = document.getElementById('cyber-canvas');
1352 | if (cyberCanvas) {
1353 |     const ctx = cyberCanvas.getContext('2d');
1354 |     let particles = [];
1355 |     let energyBursts = [];
1356 |     const particleCount = 80;
1357 |     let animationId;
1358 |     
1359 |     function resize() {
1360 |         cyberCanvas.width = window.innerWidth;
1361 |         cyberCanvas.height = window.innerHeight;
1362 |     }
1363 |     
1364 |     function createParticles() {
1365 |         particles = [];
1366 |         for (let i = 0; i < particleCount; i++) {
1367 |             particles.push({
1368 |                 x: Math.random() * cyberCanvas.width,
1369 |                 y: Math.random() * cyberCanvas.height,
1370 |                 vy: Math.random() * 2 + 0.5,
1371 |                 size: Math.random() * 2 + 0.5,
1372 |                 alpha: Math.random() * 0.4 + 0.1,
1373 |                 trail: []
1374 |             });
1375 |         }
1376 |     }
1377 |     
1378 |     function addEnergyBurst(x, y) {
1379 |         energyBursts.push({
1380 |             x, y,
1381 |             radius: 0,
1382 |             maxRadius: 100 + Math.random() * 50,
1383 |             alpha: 0.6
1384 |         });
1385 |     }
1386 |     
1387 |     function drawParticles(time) {
1388 |         particles.forEach(p => {
1389 |             // Update position
1390 |             p.y += p.vy;
1391 |             p.x += Math.sin(time * 0.001 + p.y * 0.01) * 0.3;
1392 |             
1393 |             // Reset if off screen
1394 |             if (p.y > cyberCanvas.height) {
1395 |                 p.y = -10;
1396 |                 p.x = Math.random() * cyberCanvas.width;
1397 |             }
1398 |             
1399 |             // Draw particle with glow
1400 |             const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 3);
1401 |             gradient.addColorStop(0, `rgba(220, 38, 38, ${p.alpha})`);
1402 |             gradient.addColorStop(1, 'rgba(220, 38, 38, 0)');
1403 |             
1404 |             ctx.beginPath();
1405 |             ctx.arc(p.x, p.y, p.size * 3, 0, Math.PI * 2);
1406 |             ctx.fillStyle = gradient;
1407 |             ctx.fill();
1408 |             
1409 |             // Core
1410 |             ctx.beginPath();
1411 |             ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
1412 |             ctx.fillStyle = `rgba(255, 100, 100, ${p.alpha * 1.5})`;
1413 |             ctx.fill();
1414 |         });
1415 |     }
1416 |     
1417 |     function drawEnergyBursts() {
1418 |         energyBursts = energyBursts.filter(burst => {
1419 |             burst.radius += 3;
1420 |             burst.alpha -= 0.015;
1421 |             
1422 |             if (burst.alpha <= 0) return false;
1423 |             
1424 |             ctx.beginPath();
1425 |             ctx.arc(burst.x, burst.y, burst.radius, 0, Math.PI * 2);
1426 |             ctx.strokeStyle = `rgba(220, 38, 38, ${burst.alpha})`;
1427 |             ctx.lineWidth = 2;
1428 |             ctx.stroke();
1429 |             
1430 |             return true;
1431 |         });
1432 |     }
1433 |     
1434 |     function drawConnections() {
1435 |         const connectionDistance = 150;
1436 |         for (let i = 0; i < particles.length; i++) {
1437 |             for (let j = i + 1; j < particles.length; j++) {
1438 |                 const dx = particles[i].x - particles[j].x;
1439 |                 const dy = particles[i].y - particles[j].y;
1440 |                 const dist = Math.sqrt(dx * dx + dy * dy);
1441 |                 
1442 |                 if (dist < connectionDistance) {
1443 |                     const alpha = (1 - dist / connectionDistance) * 0.1;
1444 |                     ctx.beginPath();
1445 |                     ctx.moveTo(particles[i].x, particles[i].y);
1446 |                     ctx.lineTo(particles[j].x, particles[j].y);
1447 |                     ctx.strokeStyle = `rgba(220, 38, 38, ${alpha})`;
1448 |                     ctx.lineWidth = 0.5;
1449 |                     ctx.stroke();
1450 |                 }
1451 |             }
1452 |         }
1453 |     }
1454 |     
1455 |     function animate(time) {
1456 |         ctx.clearRect(0, 0, cyberCanvas.width, cyberCanvas.height);
1457 |         
1458 |         drawConnections();
1459 |         drawParticles(time);
1460 |         drawEnergyBursts();
1461 |         
1462 |         // Random energy bursts
1463 |         if (Math.random() > 0.995) {
1464 |             addEnergyBurst(
1465 |                 Math.random() * cyberCanvas.width,
1466 |                 Math.random() * cyberCanvas.height
1467 |             );
1468 |         }
1469 |         
1470 |         animationId = requestAnimationFrame(animate);
1471 |     }
1472 |     
1473 |     resize();
1474 |     createParticles();
1475 |     animate(0);
1476 |     
1477 |     window.addEventListener('resize', () => {
1478 |         resize();
1479 |         createParticles();
1480 |     });
1481 |     
1482 |     // Pause when not visible
1483 |     document.addEventListener('visibilitychange', () => {
1484 |         if (document.hidden) {
1485 |             cancelAnimationFrame(animationId);
1486 |         } else {
1487 |             animate(0);
1488 |         }
1489 |     });
1490 | }
1491 | 
1492 | // Product showcase rotation
1493 | {% if products and products|length > 0 %}
1494 | const featuredImg = document.getElementById('featured-product-img');
1495 | const productImages = [
1496 |     {% for product in products %}
1497 |     "{{ product.main_image or product.thumbnail or '/static/images/book-placeholder.svg' }}"{% if not loop.last %},{% endif %}
1498 |     {% endfor %}
1499 | ];
1500 | let imgIndex = 0;
1501 | 
1502 | // Update item count
1503 | document.getElementById('stat-items').textContent = '{{ products|length }}';
1504 | 
1505 | if (featuredImg && productImages.length > 0) {
1506 |     featuredImg.src = productImages[0];
1507 |     featuredImg.onerror = function() { this.src = '/static/images/book-placeholder.svg'; };
1508 |     
1509 |     if (productImages.length > 1) {
1510 |         setInterval(() => {
1511 |             imgIndex = (imgIndex + 1) % productImages.length;
1512 |             featuredImg.style.transform = 'scale(0.8) rotateY(90deg)';
1513 |             featuredImg.style.opacity = '0';
1514 |             
1515 |             setTimeout(() => {
1516 |                 featuredImg.src = productImages[imgIndex];
1517 |                 featuredImg.style.transform = 'scale(1) rotateY(0deg)';
1518 |                 featuredImg.style.opacity = '1';
1519 |             }, 400);
1520 |         }, 5000);
1521 |     }
1522 | }
1523 | {% else %}
1524 | document.getElementById('stat-items').textContent = '0';
1525 | {% endif %}
1526 | 
1527 | let currentProduct = null;
1528 | let selectedVariant = null;
1529 | 
1530 | function openProductFromBtn(btn) {
1531 |     try {
1532 |         var productData = btn.getAttribute('data-product');
1533 |         console.log('Raw product data:', productData);
1534 |         var product = JSON.parse(productData);
1535 |         openProductModal(product);
1536 |     } catch(e) {
1537 |         console.error('Error parsing product:', e);
1538 |         alert('Unable to load product details. Please refresh the page.');
1539 |     }
1540 | }
1541 | 
1542 | function openProductModal(product) {
1543 |     currentProduct = product;
1544 |     
1545 |     const modal = document.getElementById('productModal');
1546 |     const modalImage = document.getElementById('modalImage');
1547 |     const modalName = document.getElementById('modalName');
1548 |     const modalPrice = document.getElementById('modalPrice');
1549 |     const modalDescription = document.getElementById('modalDescription');
1550 |     const variantSelector = document.getElementById('variantSelector');
1551 |     const variantOptions = document.getElementById('variantOptions');
1552 |     
1553 |     modalImage.src = product.main_image || product.thumbnail || '/static/images/book-placeholder.svg';
1554 |     modalImage.onerror = function() { this.src = '/static/images/book-placeholder.svg'; };
1555 |     modalName.textContent = product.name;
1556 |     modalDescription.textContent = product.description || 'Premium Protocol Pulse merchandise. Built for Bitcoin believers.';
1557 |     
1558 |     if (product.variants && product.variants.length > 0) {
1559 |         selectedVariant = product.variants[0];
1560 |         modalPrice.textContent = `$${selectedVariant.price} ${selectedVariant.currency}`;
1561 |         
1562 |         if (product.variants.length > 1) {
1563 |             variantSelector.style.display = 'block';
1564 |             variantOptions.innerHTML = '';
1565 |             
1566 |             product.variants.forEach((variant, index) => {
1567 |                 const btn = document.createElement('button');
1568 |                 btn.className = 'variant-btn' + (index === 0 ? ' active' : '');
1569 |                 btn.textContent = variant.size || variant.name || `Option ${index + 1}`;
1570 |                 btn.onclick = function() {
1571 |                     document.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('active'));
1572 |                     this.classList.add('active');
1573 |                     selectedVariant = variant;
1574 |                     modalPrice.textContent = `$${variant.price} ${variant.currency}`;
1575 |                 };
1576 |                 variantOptions.appendChild(btn);
1577 |             });
1578 |         } else {
1579 |             variantSelector.style.display = 'none';
1580 |         }
1581 |     } else {
1582 |         modalPrice.textContent = 'Price TBD';
1583 |         variantSelector.style.display = 'none';
1584 |     }
1585 |     
1586 |     modal.classList.add('active');
1587 |     document.body.style.overflow = 'hidden';
1588 | }
1589 | 
1590 | function closeProductModal() {
1591 |     document.getElementById('productModal').classList.remove('active');
1592 |     document.body.style.overflow = '';
1593 |     currentProduct = null;
1594 |     selectedVariant = null;
1595 | }
1596 | 
1597 | function purchaseProduct() {
1598 |     console.log('Purchase clicked', currentProduct, selectedVariant);
1599 |     
1600 |     if (!currentProduct) {
1601 |         alert('No product selected');
1602 |         return;
1603 |     }
1604 |     
1605 |     if (!selectedVariant && currentProduct.variants && currentProduct.variants.length > 0) {
1606 |         selectedVariant = currentProduct.variants[0];
1607 |     }
1608 |     
1609 |     if (!selectedVariant) {
1610 |         alert('Please select a size/variant');
1611 |         return;
1612 |     }
1613 |     
1614 |     const purchaseBtn = document.getElementById('purchaseBtn');
1615 |     purchaseBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
1616 |     purchaseBtn.disabled = true;
1617 |     
1618 |     const checkoutData = {
1619 |         items: [{
1620 |             variant_id: selectedVariant.id || selectedVariant.variant_id,
1621 |             quantity: 1,
1622 |             name: currentProduct.name,
1623 |             price: parseFloat(selectedVariant.price || selectedVariant.retail_price || 29.99),
1624 |             size: selectedVariant.size || selectedVariant.name || 'One Size'
1625 |         }]
1626 |     };
1627 |     
1628 |     console.log('Checkout data:', checkoutData);
1629 |     
1630 |     fetch('/api/merch/checkout', {
1631 |         method: 'POST',
1632 |         headers: {
1633 |             'Content-Type': 'application/json'
1634 |         },
1635 |         body: JSON.stringify(checkoutData)
1636 |     })
1637 |     .then(response => {
1638 |         console.log('Response status:', response.status);
1639 |         return response.json();
1640 |     })
1641 |     .then(data => {
1642 |         console.log('Checkout response:', data);
1643 |         if (data.success && data.checkout_url) {
1644 |             // Open Stripe in a new window to avoid iframe restrictions
1645 |             var stripeWindow = window.open(data.checkout_url, '_blank', 'noopener,noreferrer');
1646 |             if (!stripeWindow) {
1647 |                 // Fallback if popup blocked
1648 |                 window.location.href = data.checkout_url;
1649 |             }
1650 |             closeProductModal();
1651 |             purchaseBtn.innerHTML = '<i class="fas fa-shopping-cart"></i> Buy Now';
1652 |             purchaseBtn.disabled = false;
1653 |         } else {
1654 |             throw new Error(data.error || 'Checkout failed');
1655 |         }
1656 |     })
1657 |     .catch(error => {
1658 |         console.error('Checkout error:', error);
1659 |         alert('Unable to process checkout: ' + error.message);
1660 |         purchaseBtn.innerHTML = '<i class="fas fa-shopping-cart"></i> Buy Now';
1661 |         purchaseBtn.disabled = false;
1662 |     });
1663 | }
1664 | 
1665 | document.getElementById('productModal').addEventListener('click', function(e) {
1666 |     if (e.target === this) {
1667 |         closeProductModal();
1668 |     }
1669 | });
1670 | 
1671 | document.addEventListener('keydown', function(e) {
1672 |     if (e.key === 'Escape') {
1673 |         closeProductModal();
1674 |     }
1675 | });
1676 | 
1677 | // RTSA content is now server-rendered (no client-side fetch needed)
1678 | </script>
1679 | {% endblock %}
1680 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
