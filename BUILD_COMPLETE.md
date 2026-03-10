# BUILD COMPLETE — F5: NODE WATCH
Feature ID: f5-node-watch
Branch: feature/f5-node-watch
Completed: 2026-03-09
Commit: ecd3e8e (post-audit second pass — 6 consensus improvements)

---

## WHAT WAS BUILT

### Routes (core/routes.py)
- `GET /api/proxy/bitnodes/snapshot` — proxied Bitnodes snapshot, 5min server cache
- `GET /api/proxy/bitnodes/history` — proxied Bitnodes 24hr history, 1hr server cache
- `GET /nodes` — dedicated Node Watch page

### Templates
- `templates/nodes.html` — Live node count, 24hr sparkline chart, version breakdown, geo top-10, alert log

### Model (core/models.py)
- `NodeSnapshot` table — stores node_count, timestamp, snapshot_data (JSON), alert_fired

### Cron
- `cron/node_watch_cron.py` — runs every 15min, fetches Bitnodes snapshot, stores in DB, runs stateful alert logic

### Homepage
- `templates/index.html` — stats row updated to show live node count from /api/proxy/bitnodes/snapshot

---

## AUDIT SUMMARY

### Audit Grade
- Backend Logic: 72/100 → improved in second pass
- Error Handling: 75/100
- Security: 85/100
- Performance: 83/100
- Law Compliance: 63/100 → alert logic fixed in second pass

### Key Findings Fixed (P0/P1)
1. U1 — Alert "fire once per crossing" logic replaced with stateful threshold tracker
2. U2 — Cache key collision between snapshot/history endpoints fixed
3. U3 — DB write failures now rollback cleanly; alert not marked as fired on DB error
4. C1 (majority) — Bitnodes fallback to cached last-known value on API down
5. C2 (majority) — Rate limit guard: skip poll if last snapshot < 14min ago
6. Performance: index added on node_snapshots.timestamp

---

## REGRESSION TEST
- Result: 29 PASS | 0 FAIL | 1 WARN (uncommitted changes — expected)

---

## PBX ACTIONS REQUIRED
None — Bitnodes API is free/public, no credentials needed.
