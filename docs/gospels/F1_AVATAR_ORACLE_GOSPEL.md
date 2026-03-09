# PROTOCOL PULSE — GOSPEL: F1 AVATAR SYSTEM + ORACLE UI OVERHAUL
# Status: GOSPEL. Load into EVERY Claude Code session touching avatar or oracle.
# Branch: feature/f1-avatar-oracle
# Created: 2026-03-09
# LLM Trifecta: Claude (author) → Gemini (architecture review) → Grok (API verification)

---

## WHAT THIS FEATURE IS

The Oracle page is Protocol Pulse's most powerful differentiator — a live AI
avatar that delivers Bitcoin intelligence on demand. Right now it's broken,
inconsistent, and visually unfinished. This gospel defines the complete,
production-grade implementation.

Two parallel deliverables:
1. **Oracle Avatar Identity** — a distinct visual persona (anime-realism female,
   cyberpunk Bloomberg aesthetic) with locked assets, voice, and personality
2. **Oracle Sanctuary UI** — a fully rebuilt oracle.html that matches the
   VISUAL_DESIGN_SYSTEM.md standard (gold info bar, red/cyan/gold radial glow,
   animated SVG elements, skewed sweep transitions)

---

## THE LAWS (inviolable — never override without PBX approval)

### LAW 1: Wav2Lip is the ONLY approved lip-sync engine
- batch_size=48, FP16, GPU-cached at startup
- 134fps on 4090 = 3.8s generation for 10s audio
- DO NOT install MuseTalk, SadTalker, or any other lip-sync library
- DO NOT call HeyGen for the Oracle avatar (HeyGen is for Market Briefing Room only)

### LAW 2: apply_blink() is permanently disabled
- The blink engine creates black oval artifacts
- Body of apply_blink() must be: `return frame`
- Do not attempt to fix the blink engine — disable it, ship without blinking

### LAW 3: Voice = Jessica only
- ElevenLabs voice ID: cgSgspJ2msm6clMCkdW9
- Model: eleven_turbo_v2_5
- Settings: stability=0.45, similarity_boost=0.75, style=0.20
- Do not change the voice without PBX explicit approval

### LAW 4: No Three.js, no VR, no DAO, no WebGL shaders
- Oracle Sanctuary uses CSS/SVG animations only
- Background: CSS radial gradients + animated SVG data streams
- Glow effects: CSS box-shadow and filter:blur only

### LAW 5: avatar_server.py is the authoritative file
- Path: ~/protocol_pulse/oracle/avatar_server.py (currently 977 lines)
- Port: 8200, served via avatar.protocolpulse.io
- GPU cache warms at startup — never cold-start Wav2Lip per request
- ModelRegistry pattern must be preserved

### LAW 6: Proto-P avatar asset
- Source image: oracle/assets/Proto_P_Avatar_512.png
- This is the current avatar face used for lip sync
- New anime-realism female avatar replaces this ONLY when new asset is approved
- Until PBX provides new asset, use Proto_P_Avatar_512.png

---

## ARCHITECTURE

### File Map
```
~/protocol_pulse/
├── oracle/
│   ├── avatar_server.py          ← MAIN (977 lines) — GPU server, Wav2Lip, ElevenLabs
│   ├── assets/
│   │   ├── Proto_P_Avatar_512.png  ← current face asset
│   │   └── face_landmarker.task    ← MediaPipe landmark model
├── templates/
│   ├── oracle.html               ← REBUILD TARGET (current: 276 lines, broken)
│   ├── oracle_v2.html            ← v2 attempt (541 lines, incomplete)
│   └── stage.html                ← F2 will rename this — DO NOT TOUCH in F1
└── static/
    ├── css/pulse.css             ← design system
    └── js/oracle.js              ← oracle page JS (create if not exists)
```

### Avatar Server API (current endpoints — do NOT remove any)
```
POST /generate          ← main: {text} → MP4 video response
POST /generate-stream   ← streaming: {text} → chunked MP4
GET  /health            ← {status, gpu_available, model_loaded}
GET  /status            ← detailed server status
POST /warm              ← pre-warm GPU cache
```

### Oracle Page Data Flow
```
User types question
  → POST /api/oracle/ask (Flask route)
    → Calls ElevenLabs TTS (Jessica voice) → audio WAV
    → Calls avatar_server POST /generate (Wav2Lip + audio → MP4)
    → Returns {video_url, transcript, timestamp}
  → oracle.html JS receives response
    → Hides typing indicator
    → Shows video player with autoplay
    → Renders transcript in sidebar
    → Logs to oracle_sessions DB table
```

---

## ORACLE SANCTUARY UI SPEC

### Visual Identity
- Background: `#0a0a0a` with animated radial glow
  `radial-gradient(ellipse at 50% 30%, rgba(220,38,38,0.15), transparent 60%)`
  `radial-gradient(ellipse at 80% 70%, rgba(0,212,170,0.08), transparent 50%)`
- Header: "ORACLE" in `--pp-font-mono`, 48px, letter-spacing: 0.3em
  Subtitle: "Bitcoin Intelligence · Powered by Protocol Pulse"
- Animated SVG data stream in background (vertical scrolling binary/hex, opacity 0.06)
- Signal strength indicator (5-bar CSS animation, pulses on generation)

### Layout (single column, centered, max-width 900px)
```
┌─────────────────────────────────────────┐
│  ◈ ORACLE   [signal: ████░]  [status]   │  ← header strip
├─────────────────────────────────────────┤
│                                          │
│      [VIDEO PLAYER — 16:9 ratio]        │  ← 640x360 when idle, 800x450 active
│      glow border: 1px rgba(220,38,38)   │
│      box-shadow: 0 0 40px rgba(220,38,38,0.3) │
│                                          │
├─────────────────────────────────────────┤
│  [INPUT BAR]  [ASK ORACLE ▶]            │  ← sticky bottom
│  Placeholder: "What does the protocol   │
│  signal today?"                         │
├─────────────────────────────────────────┤
│  RECENT BRIEFINGS (last 5, collapsible) │
└─────────────────────────────────────────┘
```

### Interaction States
- **Idle**: Video player shows Proto_P_Avatar_512.png as poster, slight pulse glow
- **Generating**: Typing indicator (3 animated dots), signal bar pulses red
- **Playing**: Video autoplays, no controls visible during playback, show after
- **Error**: Red border flash, "Oracle temporarily offline" message, retry button

### CSS Classes to Create (in oracle.html `{% block head %}`)
```css
.oracle-sanctuary          /* main wrapper */
.oracle-header             /* header strip */
.oracle-signal             /* 5-bar signal indicator */
.oracle-player-wrap        /* video container with glow */
.oracle-player             /* video element */
.oracle-input-bar          /* bottom input */
.oracle-ask-btn            /* CTA button — pp-btn-primary style */
.oracle-generating         /* typing indicator */
.oracle-recent             /* recent briefings list */
.oracle-session-item       /* individual session */
```

---

## DATABASE

### oracle_sessions table (create if not exists)
```sql
CREATE TABLE IF NOT EXISTS oracle_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question TEXT NOT NULL,
    transcript TEXT,
    video_url TEXT,
    duration_seconds REAL,
    voice_id TEXT DEFAULT 'cgSgspJ2msm6clMCkdW9',
    generation_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    ip_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_oracle_sessions_created ON oracle_sessions(created_at DESC);
```

---

## KNOWN BUGS TO FIX (from avatar_server.py audit)

1. **apply_blink() black oval artifacts** — DISABLE: replace body with `return frame`
2. **Head movement not applying visually** — verify `apply_head_movement()` is called
   in the render loop and that the overlay compositing is correct
3. **Audio cutoff on longer responses** — verify `ceil+2 frames` and `-shortest`
   removal are in the current code (were fixed in a previous session)
4. **80ms itsoffset** — verify this is still in the ffmpeg command for AV sync

---

## FLASK ROUTES TO ADD/FIX

```python
# In core/routes.py — verify these exist, add if missing:
@app.route('/oracle')
def oracle():
    return render_template('oracle.html')

@app.route('/api/oracle/ask', methods=['POST'])
def oracle_ask():
    # POST {question: str} → {video_url, transcript, generation_ms}
    # Calls avatar_server at avatar.protocolpulse.io
    # Logs to oracle_sessions table
    pass

@app.route('/api/oracle/recent')
def oracle_recent():
    # GET → [{question, transcript, video_url, created_at}] last 5
    pass
```

---

## VERIFICATION CRITERIA (all must pass before commit)

- [ ] `curl -s https://avatar.protocolpulse.io/health` returns `{"status":"ok","model_loaded":true}`
- [ ] POST /api/oracle/ask with `{"question":"What is Bitcoin?"}` returns video_url within 8s
- [ ] Video plays without black oval artifacts
- [ ] Video has no audio cutoff — full response heard
- [ ] AV sync: lips match audio throughout video
- [ ] oracle.html loads at https://protocolpulse.io/oracle with HTTP 200
- [ ] Oracle Sanctuary design renders (red glow, dark bg, mono font header)
- [ ] Input bar is visible and functional
- [ ] Last 5 sessions appear in Recent Briefings
- [ ] `apply_blink()` body is `return frame` — confirmed in code

---

## CLAUDE CODE PROMPT (fire this into the session)

```
Read ~/protocol_pulse/oracle/avatar_server.py in full.
Read ~/protocol_pulse/templates/oracle.html and oracle_v2.html.
Read ~/protocol_pulse/ARTICLE_PAGE_LAWS.md (for general laws).
Read ~/protocol_pulse/docs/gospels/F1_AVATAR_ORACLE_GOSPEL.md (THIS FILE — your primary spec).

You are building F1: Avatar System Completion + Oracle UI Overhaul.
Branch: feature/f1-avatar-oracle (create from main).

PHASE 1 — AVATAR SERVER FIXES:
1. Confirm apply_blink() body is `return frame` — fix if not
2. Confirm AV sync fix (80ms itsoffset, ceil+2 frames, no -shortest) — fix if not
3. Confirm head_movement is visually applying — fix if not
4. Run: cd oracle && python3 -c "import avatar_server; print('import OK')"
5. Test: curl -X POST https://avatar.protocolpulse.io/generate -d '{"text":"Bitcoin is sound money."}' -o /tmp/oracle_test.mp4
6. Run ffprobe on /tmp/oracle_test.mp4 — report duration, video codec, audio codec
7. Extract frame at 2s — confirm no black oval artifacts

PHASE 2 — ORACLE SANCTUARY UI:
8. Delete oracle_v2.html (it's a dead end)
9. Rebuild oracle.html from scratch per the gospel spec
10. Use {% block head %} for all CSS (NOT {% block styles %})
11. All CSS in-page (no separate oracle.css file)
12. Signal indicator: 5 CSS bars, animated pulse when generating
13. Video player: 800x450 active, poster=Proto_P_Avatar_512.png, glow border
14. Input bar: sticky bottom, placeholder "What does the protocol signal today?"
15. Recent briefings: fetch /api/oracle/recent on load, render last 5

PHASE 3 — FLASK ROUTES:
16. Verify /oracle route exists in core/routes.py — add if missing
17. Add /api/oracle/ask route (POST, calls avatar_server, logs to DB)
18. Add /api/oracle/recent route (GET, last 5 sessions)
19. Create oracle_sessions table migration

PHASE 4 — VERIFY:
20. Hard reload https://protocolpulse.io/oracle — confirm 200 + Oracle Sanctuary renders
21. POST a question — confirm video plays, no artifacts, lips sync
22. Run regression_test.sh — zero FAILs required
23. git add -A && git commit -m "feat(F1): Avatar fixes + Oracle Sanctuary UI"
24. git push origin feature/f1-avatar-oracle
```

---

## LLM TRIFECTA AUDIT NOTES

### Claude Gap Analysis (self-audit):
- RISK: avatar_server.py FP16 model may not be loaded if server was restarted since
  last session — warm endpoint needed before first request
- RISK: `/api/oracle/ask` route may conflict with existing route names — grep routes.py first
- MISSING: Rate limiting on /api/oracle/ask (ElevenLabs costs money per call)
- MISSING: Question sanitization / max length enforcement (prevent abuse)
- VERIFY: oracle_sessions table may already exist with different schema

### For Gemini (paste this gospel + ask):
"Review the architecture. Specifically: Is the avatar_server→Flask→oracle.html
data flow sound? Are there race conditions in the video generation pipeline?
Is the database schema appropriate for the use case?"

### For Grok (paste this gospel + ask):
"Verify: ElevenLabs voice ID cgSgspJ2msm6clMCkdW9 — is this a valid current
voice ID? Is eleven_turbo_v2_5 the best model for low-latency generation?
Current ElevenLabs pricing for this use pattern?"
