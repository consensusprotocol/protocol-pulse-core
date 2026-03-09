# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: F5 NODE COUNT WATCH
# Branch: feature/f5-node-watch | Created: 2026-03-09
---

## WHAT THIS IS
Real-time Bitcoin node count monitor using the Bitnodes API. Shows total reachable
nodes, geographic distribution, version breakdown, and fires alerts when node count
crosses thresholds. Displayed as a live panel on the homepage + dedicated /nodes page.

## THE LAWS
### LAW 1: Proxy endpoints only — never hit Bitnodes from the browser
- /api/proxy/bitnodes/snapshot — 5min server cache
- /api/proxy/bitnodes/history — 1hr server cache
- All JS fetches /api/proxy/bitnodes/* — never api.bitnodes.io directly

### LAW 2: Alert thresholds (fire once per crossing, not every poll)
- ±500 nodes from yesterday's count → "Network change alert"
- New all-time high → "ATH ALERT: Bitcoin nodes hit [N]"
- Round milestones (20000, 25000, etc.) → milestone celebration
- -1000 over 7 days → "Network contraction warning"

### LAW 3: Poll every 15 minutes via cron, not per-request
- cron/node_watch_cron.py runs every 15min
- Stores snapshot in node_snapshots table
- Alert check runs after each snapshot

## ARCHITECTURE

### Bitnodes API (free, no auth)
```
GET https://bitnodes.io/api/v1/snapshots/?limit=1
→ {count, timestamp, nodes: {ip: [version, services, ...]}}

GET https://bitnodes.io/api/v1/snapshots/?limit=48  (48 × 30min = 24hr history)
```

### Database
```sql
CREATE TABLE IF NOT EXISTS node_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_count INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_data TEXT,  -- JSON with version breakdown, geo data
    alert_fired TEXT     -- NULL or alert type
);
```

### Homepage Panel (add to index.html stats row)
The existing pp-stats-row shows: EH/s, T Difficulty, Intel Briefs, 24/7
Replace "0+" Intel Briefs with LIVE node count from /api/proxy/bitnodes/snapshot
Keep the 24/7 Live Coverage stat.

### Flask Routes
```python
@app.route('/api/proxy/bitnodes/snapshot')
@cache.cached(timeout=300)  # 5 min cache
def bitnodes_snapshot():
    ...

@app.route('/api/proxy/bitnodes/history')
@cache.cached(timeout=3600)  # 1 hr cache
def bitnodes_history():
    ...

@app.route('/nodes')
def nodes_page():
    ...
```

## VERIFICATION
- [ ] /api/proxy/bitnodes/snapshot returns node count > 10000
- [ ] Homepage stats row shows live node count
- [ ] /nodes page loads with chart
- [ ] Alert logic fires correctly on threshold crossing
- [ ] regression_test.sh: zero FAILs

## CLAUDE CODE PROMPT
```
Read ~/protocol_pulse/docs/gospels/F5_NODE_WATCH_GOSPEL.md.
Branch: feature/f5-node-watch.
1. Add /api/proxy/bitnodes/snapshot + /history to core/routes.py
2. Test both endpoints return valid data
3. Update index.html stats row to pull node count from proxy
4. Create node_snapshots table migration
5. Create cron/node_watch_cron.py (15min poll + alert logic)
6. Create templates/nodes.html (simple: count, chart, version breakdown)
7. Add /nodes route
8. regression_test.sh: zero FAILs → commit + push feature/f5-node-watch
```

## LLM TRIFECTA
### Claude: RISK — Bitnodes sometimes goes down. Need fallback (cached last known value).
### Gemini: "Is 15-min polling appropriate? What's Bitnodes' rate limit policy?"
### Grok: "Is api.bitnodes.io still the correct endpoint? Any auth required in 2026?"

