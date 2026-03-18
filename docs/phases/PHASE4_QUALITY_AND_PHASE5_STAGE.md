# ORACLE AVATAR — PHASE 4: CONVERSATION QUALITY
# CC Session Prompt — Only run after Phase 3 gate passes

## PREREQUISITE
```bash
python3 /home/ultron/protocol_pulse/tests/phase1_gate.py  # ALL PASS
python3 /home/ultron/protocol_pulse/tests/phase3_gate.py  # ALL PASS
```

## MISSION
Oracle handles edge cases like a human specialist — confusion, tangents, emotional
escalation, mid-setup interruptions, and vision context memory.

---

## DELIVERABLE 1: CONFUSION DETECTION + REPAIR

In `oracle_dialogue_engine.py`, add to `generate_response()`:

```python
# Confusion detection — if last 2 user turns show low intent signal
recent_user = [h["content"] for h in session["history"][-4:] if h["role"] == "user"]
if len(recent_user) >= 2:
    # Check for repeated content (user asked same thing twice)
    if len(recent_user) >= 2 and recent_user[-1].lower().strip() == recent_user[-2].lower().strip():
        context_lines.append(
            "DETECT: User repeated their message. They may be confused or not getting what they need. "
            "Acknowledge you may have missed their point and ask them to clarify differently. "
            "Example: 'I may have misread what you need — can you tell me differently?'"
        )
    
    # Check for short/garbled inputs (< 3 words, no clear intent)
    if len(user_text.split()) < 3 and not any(t in user_text.lower() for t in 
        ["yes","no","ok","done","got","next","step","help","what","how","why","where"]):
        context_lines.append(
            "DETECT: Very short or unclear input. Don't guess — ask what they meant. "
            "Example: 'I want to make sure I understand — what are you trying to do?'"
        )
```

## DELIVERABLE 2: EMOTIONAL ESCALATION DETECTION

Add frustration detection to `_infer_personality()` and inject into context:

```python
FRUSTRATION_SIGNALS = [
    "frustrated", "annoyed", "this is ridiculous", "doesn't work", "nothing works",
    "hours", "tried everything", "give up", "hopeless", "help me", "please", 
    "i give up", "what is wrong", "why isn't", "still not", "i've been trying",
    "!!!", "???", "ugh", "argh", "damn", "broken", "useless"
]

def _detect_frustration(text: str) -> bool:
    text_lower = text.lower()
    return any(sig in text_lower for sig in FRUSTRATION_SIGNALS) or text.count("!") >= 2

# In generate_response():
if _detect_frustration(user_text):
    context_lines.append(
        "EMOTIONAL STATE: User shows frustration. Shift to empathetic mode immediately. "
        "Acknowledge their struggle first before any information. Slow down. "
        "One thing at a time. Example opener: 'I hear you — let's slow down and fix this properly.'"
    )
    # Also temporarily soften personality to AMIABLE
    session["personality"] = "AMIABLE"
```

## DELIVERABLE 3: SETUP FLOW TANGENT HANDLING

Currently, mid-setup off-topic questions break the flow. Fix:

```python
# In generate_response(), when flow is active and user asks something unrelated:
if flow.get("active"):
    # Detect if user question is unrelated to current setup step
    current_instruction = flow["steps"][flow["step"]][0].lower()
    setup_keywords = set(current_instruction.split())
    user_keywords = set(user_text.lower().split())
    overlap = setup_keywords & user_keywords
    
    is_tangent = len(overlap) < 2 and not any(w in user_text.lower() for w in 
        ["done", "ok", "yes", "next", "continue", "step", "ready", "got", "works", "set"])
    
    if is_tangent:
        context_lines.append(
            f"SETUP TANGENT DETECTED: User asked something off-topic while in "
            f"{flow['device']} setup (step {flow['step']+1} of {flow['total_steps']}). "
            f"Answer their question briefly (1-2 sentences max), then offer to resume: "
            f"'...want to pick back up on step {flow['step']+1} of your {flow['device']} setup?'"
        )
        # Don't advance the step — stay at current step
```

## DELIVERABLE 4: VISION CONTEXT CARRY-FORWARD

Currently each `/vision/analyze` call is stateless. Fix by storing vision summaries in session:

In `avatar_server.py`, after vision analysis:
```python
@app.route("/vision/analyze", methods=["POST"])
def vision_analyze():
    # ... existing Gemini call ...
    
    # Store vision context in session
    session_id = data.get("session_id", "anon")
    session = oracle_dialogue_engine._get_session(session_id)
    vision_history = session.get("vision_history", [])
    vision_history.append({
        "turn": session["turn"],
        "summary": analysis_result[:200]  # first 200 chars of Gemini analysis
    })
    session["vision_history"] = vision_history[-3:]  # keep last 3 vision events
    
    return jsonify({"analysis": analysis_result})
```

In `generate_response()`, inject vision history:
```python
vision_history = session.get("vision_history", [])
if vision_history:
    vis_ctx = " | ".join([f"Turn {v['turn']}: {v['summary'][:80]}" for v in vision_history])
    context_lines.append(f"VISION HISTORY (what user showed you): {vis_ctx}")
```

## DELIVERABLE 5: CONVERSATION REPAIR (reference prior turns)

Add to system prompt:
```
CONVERSATION REPAIR:
When a user asks something vague like "what about that?" or "the other thing" or "can you explain more?" —
look at the conversation history and reference what they likely mean.
Example: "You mentioned earlier you're holding on Coinbase — are you asking about moving that specifically?"
Never ask "what do you mean?" without first making a guess based on prior context.
```

## DELIVERABLE 6: PHASE 4 GATE TEST

Write `/home/ultron/protocol_pulse/tests/phase4_gate.py`:

```python
EDGE_CASES = [
    # Confusion / repair
    ("user repeats question", ["what is a cold wallet", "what is a cold wallet"],
     ["misread", "differently", "clarify", "rephrase"]),
    
    # Frustration
    ("frustrated user", ["I've been trying to do this for 3 hours and nothing works"],
     ["hear", "slow", "together", "fix", "step"]),
    
    # Mid-setup tangent
    ("tangent mid-coldcard", 
     ["Coldcard in front of me", "tamper seal ok", "actually wait how does Bitcoin work?"],
     ["bitcoin", "back", "step", "resume", "setup"]),
    
    # Vision carry-forward
    ("vision memory", 
     ["[VISION_SHOWN: Coldcard seed confirmation screen]", "I showed you that screen — what did I do wrong?"],
     ["seed", "confirm", "word", "screen", "match"]),
    
    # Vague follow-up repair
    ("vague followup",
     ["how does self custody work", "ok but what about the other part?"],
     ["custody", "keys", "seed", "wallet", "referring"]),
    
    # Emotional + then resumes normally
    ("frustration then calm",
     ["this is ridiculous nothing works!!!", "ok i feel better now, let's try again"],
     ["understand", "try", "start", "step", "back"]),
    
    # Off-topic mid-setup doesn't break flow
    ("setup intact after tangent",
     ["Coldcard arrived setting up", "seal ok", "what is inflation?", "ok back to setup"],
     ["step", "pin", "setup", "continue", "coldcard"]),
    
    # Repeated garbled input
    ("garbled input", ["asdfg", "what"],
     ["understand", "mean", "trying", "help", "clarify"]),
    
    # Long frustrated message
    ("long rant",
     ["I cannot believe this - I've been trying to set up this stupid wallet for 6 hours, "
      "nothing is working, the instructions are garbage, I'm about to give up entirely"],
     ["hear", "hours", "slow", "one thing", "step"]),
    
    # Complete session + new one
    ("clean new session",
     [],  # fresh session
     # First response should be a greeting, not reference old context
     ["welcome", "help", "bitcoin", "start"]),
]
```

---

## EXECUTION ORDER

1. Verify all prior gates pass
2. Add confusion detection to generate_response()
3. Add frustration detection and AMIABLE pivot
4. Fix setup flow tangent handling
5. Add vision context carry-forward
6. Add conversation repair instruction to system prompt
7. Run phase4_gate.py — all 10 pass
8. Run full regression: phase1_gate.py
9. Cross-LLM audit
10. Commit and push

## GATE — DO NOT PROCEED UNTIL:
- [ ] phase4_gate.py: 10/10 pass
- [ ] Frustration triggers empathetic response within 1 turn
- [ ] Mid-setup tangent gets answered AND offers to resume
- [ ] Vision context from turn 3 referenced in turn 5
- [ ] phase1_gate.py still all passing
- [ ] Committed to main

## LAUNCH COMMAND
```bash
tmux new-session -d -s oracle_phase4 -x 220 -y 50 && tmux send-keys -t oracle_phase4 "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
```

---
---
---

# ORACLE AVATAR — PHASE 5: STAGE INTEGRATION
# CC Session Prompt — Only run after Phase 4 gate passes

## PREREQUISITE
```bash
python3 /home/ultron/protocol_pulse/tests/phase1_gate.py  # ALL PASS
python3 /home/ultron/protocol_pulse/tests/phase4_gate.py  # ALL PASS
```

## MISSION
Stage avatar completes the timed briefing system, becomes interactive between segments,
and gets the full RAG + real-time intel from Phase 2.

---

## DELIVERABLE 1: TIMED BRIEFING (complete the CC session already running)

Check if the timed_brief CC session already committed anything:
```bash
git log --oneline -10
# Look for "timed briefing" commits
```

If not complete, build:
- `generate_stage_brief.py` — reads render output/script.json, condenses via Haiku, renders via Wav2Lip
- Hook into `daily_producer.py` after quality gate (non-fatal)
- `/api/stage/next_briefing` endpoint returning countdown + last brief metadata
- Countdown UI on stage page — gold timer, "NEW BRIEF AVAILABLE" flash at zero
- Static serving for brief MP4s

Full spec is in: `/home/ultron/protocol_pulse/video_pipeline_v3/TIMED_BRIEFING_PROMPT.md`

## DELIVERABLE 2: INTERACTION WINDOW BETWEEN SEGMENTS

Stage page should switch between two modes:

**BROADCAST MODE** (during briefing playback):
- Avatar plays the timed brief video
- No microphone, no chat input
- Status: "● ON AIR" in red
- Countdown shows "Next briefing in X:XX:XX"
- Nostr feed updates every 2 minutes

**INTERACTIVE MODE** (between briefings — countdown is running):
- Avatar shows idle pose (greeting video loops)
- Microphone activates (pulseMic on idle)
- Chat works — same Oracle dialogue engine as oracle_live.html
- Status: "Ask Oracle anything"
- Small badge: "BETWEEN SEGMENTS — X:XX until next briefing"
- When countdown hits zero: smooth transition back to BROADCAST MODE, plays new brief

### Implementation in stage.html

```javascript
var STAGE_MODE = 'interactive'; // 'broadcast' | 'interactive'

function enterBroadcast(briefUrl) {
    STAGE_MODE = 'broadcast';
    document.getElementById('stageModeBadge').textContent = '● ON AIR';
    document.getElementById('stageModeBadge').style.color = 'var(--s-red)';
    document.getElementById('interactivePanel').style.display = 'none';
    document.getElementById('broadcastPanel').style.display = 'block';
    playBriefVideo(briefUrl);
}

function enterInteractive() {
    STAGE_MODE = 'interactive';
    document.getElementById('stageModeBadge').textContent = 'Ask Oracle anything';
    document.getElementById('stageModeBadge').style.color = 'var(--s-green)';
    document.getElementById('broadcastPanel').style.display = 'none';
    document.getElementById('interactivePanel').style.display = 'block';
    // Show Oracle avatar in idle state
    // Enable mic with pulseMic hint
    setTimeout(pulseMic, 1000);
}
```

The interactive panel is the same Oracle chat UI from oracle_live.html (same SESSION_ID flow, same `/oracle/chat` calls) — just embedded in the stage page layout.

## DELIVERABLE 3: STAGE GETS PHASE 2 INTEL

The stage `/api/stage/intel` endpoint should return the same enriched intel as Phase 2:
- Real-time price delta (from price_cache.json built in Phase 2)
- Market context phrase
- Top Nostr signal text
- RAG context not needed for stage display — just the intel panel data

Update `api_stage_intel()` in routes.py to pull from the enhanced `get_live_intel()`.

## DELIVERABLE 4: STAGE BRIEF GENERATION TRIGGERS RAG

When `generate_stage_brief.py` writes a new brief, also:
1. Update the channel transcript cache (`/api/stage/transcripts`)
2. Trigger a Nostr signal refresh (`fetch_signal_cache.py`)
3. Clear the RAG stale-content flag so next Oracle session gets fresh articles

## DELIVERABLE 5: PHASE 5 GATE TEST

Write `/home/ultron/protocol_pulse/tests/phase5_gate.py`:

```python
TESTS = [
    # Timed briefing
    "stage_brief_generates_from_render",        # generate_stage_brief.py --test succeeds
    "next_briefing_api_returns_countdown",       # /api/stage/next_briefing has countdown_seconds
    "next_briefing_has_mp4_url",                 # last_brief.mp4_url is accessible
    "countdown_ui_present_in_stage",             # 'countdownTimer' in stage HTML
    
    # Mode switching
    "broadcast_mode_disables_mic",               # STAGE_MODE=broadcast → mic disabled
    "interactive_mode_enables_oracle",           # STAGE_MODE=interactive → /oracle/chat works
    "mode_badge_updates",                        # stageModeBadge text changes on mode switch
    "transition_at_countdown_zero",              # enterBroadcast() called when countdown hits 0
    
    # Stage intel enriched
    "stage_intel_has_price_delta",               # price_delta_1h in /api/stage/intel response
    "stage_intel_has_market_context",            # market_context phrase in response
    
    # Full end-to-end
    "full_flow_render_to_stage",                 # render → brief generated → stage shows it
    
    # Regression
    "oracle_live_still_works",                   # /oracle-live responds 200
    "oracle_chat_still_responds",               # /oracle/chat returns video
    "all_phase1_tests_pass",                    # run phase1_gate.py inline
]
```

All 14 tests must pass.

---

## EXECUTION ORDER

1. Verify all prior gates pass
2. Check if timed_brief CC session completed — if not, complete it
3. Implement broadcast/interactive mode switching in stage.html
4. Wire Oracle chat into stage interactive panel
5. Update api_stage_intel() with Phase 2 enriched data
6. Add post-brief triggers (transcript refresh, Nostr refresh)
7. Run phase5_gate.py — 14/14 pass
8. Run full regression: phase1_gate.py
9. Cross-LLM audit
10. Final commit: "feat(phase5): stage interactive mode, timed briefing complete, full avatar launch ready"
11. Push, restart all services

## FINAL GATE — LAUNCH READY WHEN:
- [ ] phase5_gate.py: 14/14 pass
- [ ] phase1_gate.py: all pass
- [ ] You personally tested the full flow on iPhone Safari: greeting → question → device setup walkthrough → stage page → interactive between segments
- [ ] Timed briefing auto-generates after a Grade A render
- [ ] stage.protocolpulse.io / oracle-live both respond cleanly
- [ ] Committed: "feat: oracle avatar v2.0 — launch ready"

## LAUNCH COMMAND
```bash
tmux new-session -d -s oracle_phase5 -x 220 -y 50 && tmux send-keys -t oracle_phase5 "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
```
