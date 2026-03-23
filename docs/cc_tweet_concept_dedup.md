Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/services/tweet_machine.py fully.
Read ~/protocol_pulse/services/x_service.py fully — especially can_post_tweet().

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: CONCEPT-LEVEL TWEET DEDUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM:
The current gate blocks similar WORDING (30% keyword overlap) but not
similar CONCEPTS. "Extreme Fear index at peak" and "Extreme Fear readings
historically compress into violent rallies" are different words but the
SAME concept: Fear & Greed Index + Bitcoin bullish historical pattern.

Result: the same narrative posted 2-3 days in a row with slight rewording.
Audience sees spam. Credibility damaged.

THE FIX: Extract the core concept from every tweet before posting.
Block that concept for 72 hours. Force genuine variety.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY: CROSS-LLM AUDIT FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["tweet-concept-dedup"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["tweet-concept-dedup"] = [
      "services/x_service.py",
      "services/tweet_machine.py",
  ]

python3 utils/cross_llm_audit.py --feature tweet-concept-dedup
[save C1]
python3 utils/cross_llm_audit.py --feature tweet-concept-dedup --cycle 2 --cycle1-results [C1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — ADD concept COLUMN TO x_post_ledger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Migrate the existing SQLite ledger to add a concept column:

ALTER TABLE x_post_ledger ADD COLUMN concept TEXT;

In _init_gate_db(), update the CREATE TABLE to include:
  concept TEXT  -- extracted core concept, e.g. "fear_greed_index"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — CONCEPT TAXONOMY (fixed list, not LLM-generated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Define a fixed set of 20 core Bitcoin narrative concepts.
Use keyword matching to classify — fast, no API call needed.

CONCEPT_TAXONOMY = {
    "fear_greed_index":     ["fear index", "extreme fear", "fear & greed", "fng", "fear greed"],
    "etf_flows":            ["etf", "inflow", "outflow", "blackrock", "fidelity", "ibit"],
    "stablecoin_power":     ["stablecoin", "usdt", "usdc", "tether", "180b", "treasury backing"],
    "price_action":         ["price", "rally", "dump", "ath", "all-time high", "correction", "dip"],
    "macro_fed":            ["fed", "federal reserve", "interest rate", "powell", "monetary policy"],
    "geopolitical":         ["iran", "war", "sanctions", "tariff", "geopolit", "china", "russia"],
    "institutional_buying": ["saylor", "microstrategy", "strategy", "corporate", "treasury"],
    "mining_hashrate":      ["mining", "hashrate", "miner", "difficulty", "halving", "exahash"],
    "dollar_debasement":    ["dollar", "inflation", "debasement", "fiat", "printing", "dxy"],
    "on_chain":             ["on-chain", "wallet", "utxo", "hodl", "accumulation", "cold storage"],
    "lightning_network":    ["lightning", "layer 2", "l2", "payment", "channel"],
    "regulatory":           ["sec", "regulation", "congress", "legislation", "gensler", "ban"],
    "petrodollar":          ["petrodollar", "oil", "yuan", "reserve currency", "brics"],
    "historical_cycle":     ["cycle", "halving", "4 year", "previous", "last time", "historically"],
    "sovereignty":          ["sovereignty", "self-custody", "censor", "confiscat", "freedom"],
    "whale_activity":       ["whale", "large wallet", "exchange outflow", "cold storage move"],
    "network_health":       ["node", "decentraliz", "network", "protocol", "upgrade"],
    "privacy":              ["privacy", "coinjoin", "kyc", "surveillance", "mixer"],
    "adoption":             ["adoption", "merchant", "payment", "use case", "el salvador"],
    "other":                []  # fallback
}

def extract_concept(tweet_text: str) -> str:
    text = tweet_text.lower()
    for concept, keywords in CONCEPT_TAXONOMY.items():
        if any(kw in text for kw in keywords):
            return concept
    return "other"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — ADD CONCEPT CHECK TO can_post_tweet()
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add after the existing similarity check (Rule 3), before Rule 5:

# Rule 4: Concept dedup — no same concept within 72 hours
concept = extract_concept(text)
if concept != "other":
    cutoff_72h = (now - timedelta(hours=72)).isoformat()
    same_concept_rows = conn.execute(
        "SELECT posted_at, tweet_text FROM x_post_ledger "
        "WHERE posted_at >= ? AND allowed = 1 AND concept = ?",
        (cutoff_72h, concept)
    ).fetchall()
    if same_concept_rows:
        last_post = same_concept_rows[-1]
        reason = (
            f"BLOCKED: concept '{concept}' already used in last 72h — "
            f"last post: {last_post[1][:60]}..."
        )
        _log_gate(conn, now, text, source, angle_category,
                  allowed=False, reason=reason)
        return (False, reason)

Store concept in _log_gate():
  Update INSERT to include concept column.
  Pass concept as parameter to _log_gate().

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — WIRE CONCEPT INTO tweet_machine.py GENERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before generating a tweet, extract the banned concepts from the ledger
and inject them into the prompt so the LLM avoids them entirely:

# Get banned concepts for next 72h
from services.x_service import extract_concept, get_recent_angles
banned = []
try:
    from services.x_service import _init_gate_db, _GATE_DB, CONCEPT_TAXONOMY
    import sqlite3
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    conn = sqlite3.connect(str(_GATE_DB))
    rows = conn.execute(
        "SELECT DISTINCT concept FROM x_post_ledger "
        "WHERE posted_at >= ? AND allowed = 1 AND concept IS NOT NULL",
        (cutoff,)
    ).fetchall()
    conn.close()
    banned = [r[0] for r in rows if r[0] != "other"]
except Exception:
    pass

if banned:
    banned_context = (
        "\n\nBANNED CONCEPTS (do NOT use these — already posted in last 72h):\n"
        + "\n".join(f"  - {c.replace('_', ' ')}" for c in banned)
        + "\nPick a concept NOT on this list. Genuinely different angle."
    )
else:
    banned_context = ""

# Add banned_context to the brief_text before generating
brief_text_with_bans = brief_text + banned_context

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — BACKFILL EXISTING LEDGER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After adding the concept column, backfill existing rows:

conn = sqlite3.connect(str(_GATE_DB))
rows = conn.execute("SELECT id, tweet_text FROM x_post_ledger WHERE concept IS NULL").fetchall()
for row_id, text in rows:
    concept = extract_concept(text or "")
    conn.execute("UPDATE x_post_ledger SET concept = ? WHERE id = ?", (concept, row_id))
conn.commit()
conn.close()
print(f"Backfilled {len(rows)} rows")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verify concept dedup works end-to-end:
  python3 -c "
  from services.x_service import can_post_tweet, extract_concept
  # Test: post extreme fear tweet, try again — should block
  r1 = can_post_tweet('Extreme Fear index hits historical low', source='test')
  print('First post:', r1)
  r2 = can_post_tweet('Extreme Fear readings at peak levels', source='test')
  print('Second post (should block):', r2)
  "

bash regression_test.sh — 0 FAILs required
git add services/x_service.py services/tweet_machine.py
git commit -m "feat(tweets): concept-level dedup — 20-concept taxonomy, 72h ban per concept, injected into LLM prompt — eliminates narrative repetition"
git push

IMPORTANT: Do not ask for confirmation before committing.
Run git add, commit, and push automatically.
