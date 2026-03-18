# ORACLE AVATAR — PHASE 2: INTELLIGENCE DEPTH
# CC Session Prompt — Only run after Phase 1 gate passes

## PREREQUISITE
Phase 1 gate must be complete. Run before starting:
```bash
python3 /home/ultron/protocol_pulse/tests/phase1_gate.py
# Must show ALL PASS before continuing
```

## MISSION
Upgrade Oracle from "knows concepts" to "knows specifics."
A human Bitcoin specialist can answer nuanced multi-part questions with accuracy.
Oracle currently cannot. This phase fixes that without touching session flow or mic behavior.

## STACK CONTEXT
- Dialogue engine: /home/ultron/protocol_pulse/oracle/oracle_dialogue_engine.py
- Avatar server: /home/ultron/protocol_pulse/oracle/avatar_server.py
- Routes: /home/ultron/protocol_pulse/routes.py
- Intelligence data: /home/ultron/protocol_pulse/video_pipeline_v3/cache/
- Anthropic key: loaded from .env (claude-haiku-4-5-20251001 for speed, claude-sonnet-4-20250514 for RAG retrieval)

## READ FIRST
```bash
cat /home/ultron/protocol_pulse/oracle/oracle_dialogue_engine.py | grep -A 20 "def generate_response"
cat /home/ultron/protocol_pulse/video_pipeline_v3/cache/active_signal.json | python3 -m json.tool | head -30
ls /home/ultron/protocol_pulse/video_pipeline_v3/data/channel_archive/ | head -10
```

---

## DELIVERABLE 1: RAG KNOWLEDGE BASE

### Step 1: Build the knowledge base

Create `/home/ultron/protocol_pulse/oracle/knowledge_base/` with these sources:

**Source A: Bitcoin technical FAQ** — write this as a structured document covering:
- What is a UTXO, how does it work
- Coldcard vs Trezor vs Ledger — specific differences (firmware, security model, price, use case)
- Coldcard Q vs Mk4 — what changed, which to buy
- Sparrow wallet — how to connect to own node, how to use with Coldcard, PSBT signing
- Umbrel vs Start9 — differences, which to use
- Lightning Network — channels, capacity, inbound liquidity, routing
- Mempool — what stuck transaction means, RBF, CPFP
- Self-custody 101 — keys, seeds, passphrases, multisig
- Bitcoin mining — pools, solo mining, Bitaxe, hashrate
- DCA strategy — how to dollar cost average, KYC-free options
- Common mistakes — screenshots of seed, digital backup, sharing xpub

**Source B: Protocol Pulse articles** — index the top 20 articles:
```python
# Fetch from the articles DB
from models import Article
articles = Article.query.order_by(Article.views.desc()).limit(20).all()
for a in articles:
    # chunk into 200-word segments with title prepended
```

**Source C: Hardware docs** — pull key sections from:
- coldcard.com/docs (critical setup steps, security features)
- sparrowwallet.com/docs (server connection, PSBT, coin control)
- getumbrel.com/docs (installation, connecting wallets)

### Step 2: Create the retrieval system

Create `/home/ultron/protocol_pulse/oracle/oracle_rag.py`:

```python
"""
RAG retrieval for Oracle dialogue engine.
Uses simple TF-IDF similarity (no external vector DB needed).
Indexes knowledge base on startup, retrieves top-3 chunks per query.
"""

import os, json, math, re
from pathlib import Path

KB_DIR = Path(__file__).parent / 'knowledge_base'
_index = {}  # word -> {chunk_id -> tf-idf score}
_chunks = {}  # chunk_id -> {"text": str, "source": str, "title": str}

def _tokenize(text):
    return re.findall(r'\b[a-z0-9]+\b', text.lower())

def build_index():
    """Load all knowledge base files and build TF-IDF index."""
    global _index, _chunks
    _index = {}
    _chunks = {}
    
    if not KB_DIR.exists():
        return
    
    chunk_id = 0
    for f in KB_DIR.glob('*.json'):
        data = json.loads(f.read_text())
        for item in data.get('chunks', []):
            text = item.get('text', '')
            tokens = _tokenize(text)
            if len(tokens) < 10:
                continue
            _chunks[chunk_id] = {
                'text': text[:400],  # max 400 chars per chunk
                'source': item.get('source', f.stem),
                'title': item.get('title', ''),
            }
            # TF
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for t, count in tf.items():
                if t not in _index:
                    _index[t] = {}
                _index[t][chunk_id] = count / len(tokens)
            chunk_id += 1
    
    # Apply IDF
    N = chunk_id
    for word, docs in _index.items():
        idf = math.log(N / (len(docs) + 1))
        for cid in docs:
            _index[word][cid] *= idf


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Return top_k most relevant chunks for the query."""
    if not _chunks:
        build_index()
    
    tokens = _tokenize(query)
    scores = {}
    for t in tokens:
        if t in _index:
            for cid, score in _index[t].items():
                scores[cid] = scores.get(cid, 0) + score
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for cid, score in ranked[:top_k]:
        if score > 0.01:  # minimum relevance threshold
            results.append(_chunks[cid])
    return results


# Build on import
build_index()
```

### Step 3: Inject RAG context into dialogue engine

In `oracle_dialogue_engine.py`, in `generate_response()`, add after existing context_lines building:

```python
# RAG retrieval — inject relevant knowledge chunks
try:
    from oracle_rag import retrieve
    rag_chunks = retrieve(user_text, top_k=2)
    if rag_chunks:
        rag_text = '\n'.join([
            f"[FROM {c['source'].upper()}] {c['title']}: {c['text']}"
            for c in rag_chunks
        ])
        context_lines.append(
            f"RELEVANT KNOWLEDGE (use this for accuracy, don't quote directly):\n{rag_text}"
        )
except Exception as e:
    logger.debug(f"RAG retrieval failed: {e}")
```

---

## DELIVERABLE 2: REAL-TIME INTEL IN RESPONSES

### Problem
Oracle says "Bitcoin is at seventy-four thousand dollars" — no context about what's happening right now.

### Solution
Enhance `get_live_intel()` to include:

```python
def get_live_intel() -> dict:
    intel = {}
    
    # 1. Live BTC price (already exists — keep)
    
    # 2. 1-hour price change (NEW)
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=4)
        if r.ok:
            current = float(r.json()["data"]["amount"])
            intel["price_float"] = current
            # Store in a simple cache file to compute delta
            cache_path = os.path.join(os.path.dirname(__file__), "..", "data", "price_cache.json")
            try:
                cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
                hour_ago = cache.get("1h_ago", current)
                delta_pct = ((current - hour_ago) / hour_ago) * 100
                intel["price_delta_1h"] = delta_pct
                intel["price_delta_spoken"] = (
                    f"up {delta_pct:.1f}% in the last hour" if delta_pct > 0
                    else f"down {abs(delta_pct):.1f}% in the last hour"
                )
                # Update cache every hour
                import time
                if not cache or time.time() - cache.get("updated", 0) > 3600:
                    json.dump({"1h_ago": current, "updated": time.time()}, open(cache_path, "w"))
            except Exception:
                pass
    except Exception:
        pass
    
    # 3. Fear & Greed context phrase (NEW)
    score = intel.get("sentiment_score", 50)
    if score < 25:
        intel["market_context"] = "the market is in extreme fear right now"
    elif score < 40:
        intel["market_context"] = "the market is fearful"
    elif score > 75:
        intel["market_context"] = "the market is in extreme greed"
    elif score > 60:
        intel["market_context"] = "the market is greedy"
    else:
        intel["market_context"] = "the market is neutral"
    
    # 4. Top Nostr signal (NEW — inject single best post as context)
    try:
        cache_path = os.path.join(os.path.dirname(__file__), "..", "video_pipeline_v3", "cache", "active_signal.json")
        if os.path.exists(cache_path):
            signal = json.load(open(cache_path))
            posts = sorted(signal.get("nostr_posts", []), key=lambda x: x.get("score", 0), reverse=True)
            if posts:
                intel["top_signal"] = posts[0].get("text", "")[:120]
    except Exception:
        pass
    
    return intel
```

Inject the new intel into context_lines:
```python
if live_intel.get("price_delta_spoken"):
    context_lines.append(f"PRICE MOVEMENT: Bitcoin is {live_intel['price_delta_spoken']}")
if live_intel.get("market_context"):
    context_lines.append(f"MARKET CONTEXT: {live_intel['market_context']}")
if live_intel.get("top_signal"):
    context_lines.append(f"NOSTR SIGNAL RIGHT NOW: {live_intel['top_signal']}")
```

---

## DELIVERABLE 3: CONFIDENCE CALIBRATION

Add to system prompt:
```
CONFIDENCE CALIBRATION:
- For well-established Bitcoin facts (fixed supply, halving schedule, how keys work): answer confidently.
- For hardware wallet specifics (exact firmware versions, specific menu paths): say "on most Coldcard firmware" or "check the latest docs at coldcard.com — menus can shift between versions"
- For price predictions or market timing: always decline with "I don't predict prices — no one reliably can"
- For legal/tax questions: "I'm not a tax advisor — for your jurisdiction, speak to someone qualified"
- NEVER make up a specific technical detail you don't know. Say "I'm not certain on that specific detail" and give what you do know.
```

---

## DELIVERABLE 4: PHASE 2 GATE TEST

Write `/home/ultron/protocol_pulse/tests/phase2_gate.py`:

```python
# 20 technical edge-case questions — 18+ must be answered correctly
EDGE_CASES = [
    ("What's the difference between Coldcard Q and Mk4?",
     ["Q", "Mk4", "NFC", "QR", "air-gapped"]),
    ("My Sparrow shows unconfirmed — is it stuck?",
     ["mempool", "RBF", "CPFP", "fee", "stuck"]),
    ("Can I use my Coldcard with BlueWallet on iPhone?",
     ["PSBT", "watch-only", "sign", "air-gap", "QR"]),
    ("What is a UTXO and why does it matter for privacy?",
     ["unspent", "output", "coin control", "privacy", "trace"]),
    ("What's the difference between SegWit and Taproot?",
     ["SegWit", "Taproot", "Schnorr", "signature", "fee"]),
    ("How do I set up inbound liquidity on Lightning?",
     ["inbound", "channel", "capacity", "open", "peer"]),
    ("What is a passphrase and is it the same as my PIN?",
     ["passphrase", "PIN", "different", "25th word", "seed"]),
    ("How do I verify my Coldcard received my Bitcoin?",
     ["mempool.space", "address", "verify", "node", "explorer"]),
    ("What is coin control and when should I use it?",
     ["UTXO", "coin control", "privacy", "change", "Sparrow"]),
    ("Is it safe to use a hardware wallet with a passphrase and multisig?",
     ["multisig", "passphrase", "backup", "seed", "quorum"]),
    ("What is RBF and CPFP and when do I use each?",
     ["replace", "fee", "stuck", "bump", "parent"]),
    ("How do I connect Sparrow to my Umbrel node?",
     ["Sparrow", "server", "Umbrel", "RPC", "Bitcoin Core"]),
    ("What's the difference between a hot wallet and cold wallet?",
     ["online", "offline", "keys", "connected", "air"]),
    ("How do I set up BTCPay Server for my business?",
     ["BTCPay", "invoice", "node", "merchant", "Lightning"]),
    ("What is the mempool and how do I check if my transaction is stuck?",
     ["mempool", "unconfirmed", "fee rate", "explorer", "sat/vbyte"]),
    ("What is xpub and should I share it with anyone?",
     ["xpub", "watch-only", "privacy", "public", "never"]),
    ("How do I do a coinjoin for privacy?",
     ["CoinJoin", "Wasabi", "Joinmarket", "UTXO", "privacy"]),
    ("What's the best way to DCA without KYC?",
     ["peer-to-peer", "KYC", "Bisq", "Robosats", "privacy"]),
    ("How does Lightning routing work?",
     ["route", "hop", "channel", "fee", "path"]),
    ("What is a watch-only wallet?",
     ["xpub", "receive", "watch", "no keys", "monitor"]),
]

# Test: response must contain at least 2 of the expected keywords
# 18/20 must pass for gate to open
```

---

## EXECUTION ORDER

1. Read Phase 1 gate results (all pass required)
2. Create knowledge_base/ directory and populate all three sources
3. Build oracle_rag.py
4. Enhance get_live_intel() with price delta + market context + top signal
5. Add confidence calibration to system prompt
6. Inject RAG context into generate_response()
7. Run phase2_gate.py — 18/20 edge cases must pass
8. Run full regression: phase1_gate.py — all must still pass
9. Cross-LLM audit
10. Commit and push

## GATE — DO NOT PROCEED UNTIL:
- [ ] phase2_gate.py: 18/20 edge cases answered correctly
- [ ] phase1_gate.py: still all passing (no regression)
- [ ] Real-time price delta appears in live Oracle conversation
- [ ] "I'm not certain" appears when Oracle is asked something obscure
- [ ] Committed to main

## LAUNCH COMMAND
```bash
tmux new-session -d -s oracle_phase2 -x 220 -y 50 && tmux send-keys -t oracle_phase2 "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
```
