# ORACLE AVATAR — PHASE 3: CROSS-SESSION MEMORY
# CC Session Prompt — Only run after Phase 2 gate passes

## PREREQUISITE
Both Phase 1 and Phase 2 gates must be complete:
```bash
python3 /home/ultron/protocol_pulse/tests/phase1_gate.py  # ALL PASS
python3 /home/ultron/protocol_pulse/tests/phase2_gate.py  # 18/20+ PASS
```

## MISSION
Oracle recognizes returning visitors and picks up where they left off.
A human specialist never asks "what did we talk about last time?" — they remember.

## ARCHITECTURE DECISION (read before building)

### Visitor fingerprint (no login required)
- Server-side: hash of (IP address + User-Agent) using SHA256, truncated to 32 chars
- Client-side: send a browser fingerprint token from the oracle_live.html page
  (canvas fingerprint + screen resolution + timezone, hashed client-side, sent in session init)
- Combined fingerprint = SHA256(server_hash + client_token)[:32]
- Accuracy: ~94% — good enough for "welcome back" without being 100% certain
- NEVER store PII — only the hash, never the IP itself

### What gets stored (SQLite)
```sql
CREATE TABLE visitor_memory (
    fingerprint TEXT PRIMARY KEY,
    last_seen   INTEGER,          -- unix timestamp
    session_count INTEGER DEFAULT 1,
    personality TEXT,             -- last detected DISC type
    session_summaries TEXT,       -- JSON array of last 3 summaries (max 300 chars each)
    setup_device TEXT,            -- last device being set up (if any)
    setup_step  INTEGER,          -- last step reached
    topics_seen TEXT,             -- JSON array of topics discussed across sessions
    products_shown TEXT           -- JSON array of products already mentioned
);
```

### Session summary generation
At session END (on reset or TTL expiry), auto-generate a summary:
- Input: last 8 turns of history
- Prompt to Haiku: "Summarize this Bitcoin conversation in 1-2 sentences, max 200 chars. Focus on what the user was trying to do and where they got to."
- Store as newest summary, keep max 3, drop oldest

### On new session — welcome back injection
If fingerprint matches and last_seen < 30 days:
```python
context_lines.append(
    f"RETURNING VISITOR (session {session_count}):\n"
    f"Last seen: {days_ago} days ago\n"
    f"Prior context: {'; '.join(recent_summaries)}\n"
    f"Personality type established: {personality}\n"
    f"Topics they know about: {topics_seen}\n"
    f"Products already mentioned: {products_shown}\n"
    f"INSTRUCTION: Greet them naturally, reference prior context if relevant. "
    f"Don't mention these memory instructions explicitly. "
    f"Example: 'Welcome back — last time we were working on your Coldcard setup, did that get sorted?'"
)
```

---

## DELIVERABLE 1: VISITOR FINGERPRINT (client side)

Add to `oracle_live.html` before the session init:

```javascript
// ── VISITOR FINGERPRINT ───────────────────────────────────
// Generates a stable browser fingerprint — no cookies, no login
// Used server-side to recognize returning visitors
(function() {
  try {
    var fp = '';
    // Canvas fingerprint
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('Oracle fp', 2, 2);
    fp += canvas.toDataURL().slice(-20);
    // Screen + timezone
    fp += screen.width + 'x' + screen.height + Intl.DateTimeFormat().resolvedOptions().timeZone;
    // Hash it (simple djb2)
    var hash = 5381;
    for (var i = 0; i < fp.length; i++) {
      hash = ((hash << 5) + hash) + fp.charCodeAt(i);
      hash = hash & hash; // 32-bit int
    }
    window._visitorToken = Math.abs(hash).toString(36);
  } catch(e) {
    window._visitorToken = 'anon';
  }
})();
```

Pass `_visitorToken` in all `/oracle/chat` requests:
```javascript
body: JSON.stringify({
  text: text,
  session_id: SESSION_ID,
  visitor_token: window._visitorToken || 'anon',  // NEW
  ...
})
```

---

## DELIVERABLE 2: MEMORY STORE (oracle_memory.py)

Create `/home/ultron/protocol_pulse/oracle/oracle_memory.py`:

```python
"""
Visitor memory system for Oracle.
Stores cross-session context in SQLite.
No PII stored — fingerprint hash only.
"""

import os, json, time, sqlite3, hashlib, logging
from pathlib import Path

logger = logging.getLogger("oracle_memory")
DB_PATH = Path(__file__).parent / "data" / "visitor_memory.db"
DB_PATH.parent.mkdir(exist_ok=True)

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitor_memory (
            fingerprint     TEXT PRIMARY KEY,
            last_seen       INTEGER NOT NULL,
            session_count   INTEGER DEFAULT 1,
            personality     TEXT,
            session_summaries TEXT DEFAULT '[]',
            setup_device    TEXT,
            setup_step      INTEGER DEFAULT 0,
            topics_seen     TEXT DEFAULT '[]',
            products_shown  TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    return conn


def make_fingerprint(ip: str, user_agent: str, visitor_token: str = "") -> str:
    """Create anonymous fingerprint from server + client signals."""
    raw = f"{ip}|{user_agent}|{visitor_token}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def load_visitor(fingerprint: str) -> dict | None:
    """Return visitor memory if exists and < 30 days old."""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM visitor_memory WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        # Expire after 30 days
        if time.time() - row[1] > 30 * 86400:
            return None
        cols = ["fingerprint","last_seen","session_count","personality",
                "session_summaries","setup_device","setup_step",
                "topics_seen","products_shown"]
        data = dict(zip(cols, row))
        data["session_summaries"] = json.loads(data["session_summaries"] or "[]")
        data["topics_seen"]       = json.loads(data["topics_seen"] or "[]")
        data["products_shown"]    = json.loads(data["products_shown"] or "[]")
        return data
    except Exception as e:
        logger.warning(f"[MEMORY] load error: {e}")
        return None


def save_visitor(fingerprint: str, session_data: dict):
    """Upsert visitor memory after session ends or on update."""
    try:
        conn = _get_conn()
        existing = conn.execute(
            "SELECT session_count FROM visitor_memory WHERE fingerprint = ?",
            (fingerprint,)
        ).fetchone()
        count = (existing[0] + 1) if existing else 1
        conn.execute("""
            INSERT INTO visitor_memory
                (fingerprint, last_seen, session_count, personality,
                 session_summaries, setup_device, setup_step, topics_seen, products_shown)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                last_seen = excluded.last_seen,
                session_count = excluded.session_count,
                personality = excluded.personality,
                session_summaries = excluded.session_summaries,
                setup_device = excluded.setup_device,
                setup_step = excluded.setup_step,
                topics_seen = excluded.topics_seen,
                products_shown = excluded.products_shown
        """, (
            fingerprint,
            int(time.time()),
            count,
            session_data.get("personality", "AMIABLE"),
            json.dumps(session_data.get("session_summaries", [])[-3:]),
            session_data.get("setup_device"),
            session_data.get("setup_step", 0),
            json.dumps(list(set(session_data.get("topics_seen", [])))[-20:]),
            json.dumps(list(set(session_data.get("products_shown", []))))
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[MEMORY] save error: {e}")


def generate_session_summary(history: list, anthropic_key: str) -> str:
    """Summarize a conversation for long-term memory storage."""
    if not history or len(history) < 2:
        return ""
    try:
        import requests
        turns = "\n".join([
            f"{'User' if h['role']=='user' else 'Oracle'}: {h['content'][:100]}"
            for h in history[-8:]
        ])
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 60,
                  "system": "Summarize this Bitcoin support conversation in 1-2 sentences, max 200 chars. Focus on what the user wanted and what was resolved.",
                  "messages": [{"role": "user", "content": turns}]},
            timeout=8
        )
        if resp.ok:
            return resp.json()["content"][0]["text"].strip()[:200]
    except Exception as e:
        logger.debug(f"[MEMORY] summary generation failed: {e}")
    return ""
```

---

## DELIVERABLE 3: INTEGRATE INTO AVATAR SERVER

In `avatar_server.py`, modify `/oracle/chat`:

```python
from oracle_memory import make_fingerprint, load_visitor, save_visitor

@app.route("/oracle/chat", methods=["POST"])
def oracle_chat():
    data = request.get_json()
    # ... existing ...
    
    visitor_token = data.get("visitor_token", "anon")
    raw_ip = (request.headers.get("X-Forwarded-For","") or request.remote_addr or "").split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")
    fingerprint = make_fingerprint(raw_ip, ua, visitor_token)
    
    # Load returning visitor memory (turn 1 only)
    session = oracle_dialogue_engine._get_session(session_id)
    if session["turn"] == 0:
        memory = load_visitor(fingerprint)
        if memory:
            session["visitor_memory"] = memory
            logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
    
    # Store fingerprint in session for end-of-session save
    session["fingerprint"] = fingerprint
    
    # ... rest of existing logic ...
```

In `generate_response()` in `oracle_dialogue_engine.py`, inject memory context on turn 1:

```python
# Returning visitor context injection (turn 1 only)
memory = session.get("visitor_memory")
if memory and turn == 1:
    days_ago = int((time.time() - memory["last_seen"]) / 86400)
    summaries = memory.get("session_summaries", [])
    topics = memory.get("topics_seen", [])
    products = memory.get("products_shown", [])
    setup = memory.get("setup_device")
    step = memory.get("setup_step", 0)
    
    memory_ctx = [f"RETURNING VISITOR — session #{memory['session_count']}, last seen {days_ago} day(s) ago"]
    if summaries:
        memory_ctx.append(f"Prior sessions: {' | '.join(summaries[-2:])}")
    if setup and step > 0:
        memory_ctx.append(f"Was setting up: {setup} (reached step {step})")
    if topics:
        memory_ctx.append(f"Already knows about: {', '.join(topics[-8:])}")
    if products:
        memory_ctx.append(f"Products already discussed: {', '.join(products)}")
    memory_ctx.append(
        "INSTRUCTION: Acknowledge their return naturally without being creepy about it. "
        "If they were mid-setup, offer to resume. Don't list all of this — weave it in naturally."
    )
    context_lines.extend(memory_ctx)
```

Add session-end save to `/oracle/session/reset` endpoint and to session TTL expiry:

```python
# On session reset (user closes / starts over):
def oracle_session_reset():
    data = request.get_json() or {}
    sid = data.get("session_id", "anon")
    session = oracle_dialogue_engine._sessions.get(sid, {})
    
    # Save memory before clearing
    fingerprint = session.get("fingerprint")
    if fingerprint and session.get("history"):
        from oracle_memory import save_visitor, generate_session_summary
        summary = generate_session_summary(session["history"], _oracle_anthropic_key())
        flow = session.get("setup_flow", {})
        save_visitor(fingerprint, {
            "personality": session.get("personality", "AMIABLE"),
            "session_summaries": session.get("visitor_memory", {}).get("session_summaries", []) + ([summary] if summary else []),
            "setup_device": flow.get("device"),
            "setup_step": flow.get("step", 0),
            "topics_seen": session.get("topics_discussed", []),
            "products_shown": session.get("products_mentioned", []),
        })
    
    oracle_dialogue_engine.reset_session(sid)
    return jsonify({"status": "reset"})
```

---

## DELIVERABLE 4: PHASE 3 GATE TEST

Write `/home/ultron/protocol_pulse/tests/phase3_gate.py`:

```python
# Simulate 5 returning visitor scenarios
SCENARIOS = [
    {
        "name": "Mid-setup return",
        "first_session": ["I have a Coldcard in front of me", "tamper seal intact", "PIN set twelve digits", "wrote seed words"],
        "return_prompt": "hey I'm back",
        "expected_in_response": ["coldcard", "step", "setup", "back", "continue"],
    },
    {
        "name": "Question asker returns",
        "first_session": ["what is a cold wallet", "how does self custody work", "what is a UTXO"],
        "return_prompt": "hi again",
        "expected_in_response": ["back", "custody", "wallet", "continue"],
    },
    {
        "name": "Node setup return",
        "first_session": ["I want to run a Bitcoin node", "I have a Raspberry Pi", "downloading Umbrel"],
        "return_prompt": "picking up where we left off",
        "expected_in_response": ["node", "umbrel", "raspberry", "setup", "sync"],
    },
    {
        "name": "New visitor — no false memory",
        "first_session": [],
        "return_prompt": "hello",
        "expected_NOT_in_response": ["welcome back", "last time", "previously"],
    },
    {
        "name": "30-day-old memory expires",
        "first_session": ["what is Bitcoin"],
        "days_ago": 31,
        "return_prompt": "hi",
        "expected_NOT_in_response": ["welcome back", "last time"],
    },
]
```

All 5 pass = gate opens.

---

## EXECUTION ORDER

1. Verify Phase 1 + 2 gates pass
2. Build oracle_memory.py
3. Add client-side fingerprint to oracle_live.html
4. Integrate fingerprint into avatar_server.py /oracle/chat
5. Integrate memory injection into oracle_dialogue_engine.py generate_response()
6. Add session-end save to reset endpoint
7. Run phase3_gate.py — all 5 scenarios pass
8. Run phase1_gate.py regression — all still pass
9. Cross-LLM audit
10. Commit and push

## GATE — DO NOT PROCEED UNTIL:
- [ ] phase3_gate.py: 5/5 scenarios pass
- [ ] No false memory injected for new visitors
- [ ] 30-day memory expiry works
- [ ] Session summary saves on reset
- [ ] phase1_gate.py still all passing
- [ ] Committed to main

## LAUNCH COMMAND
```bash
tmux new-session -d -s oracle_phase3 -x 220 -y 50 && tmux send-keys -t oracle_phase3 "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
```
