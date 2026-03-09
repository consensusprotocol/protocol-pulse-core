# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: F6 MARKETING OS + BTC MILESTONE TRIGGERS
# Branch: feature/f6-marketing-os | Created: 2026-03-09
---

## WHAT THIS IS
When Bitcoin hits price milestones, Protocol Pulse auto-activates pre-designed
marketing campaigns. The Marketing OS is the content calendar, campaign manager,
and automated trigger system — all governed by Bitcoin's price.

## THE LAWS

### LAW 1: Launch gate — 9 items must ALL be ✓ before milestone campaigns fire
```
[ ] Pulse Check producing clean daily renders (video pipeline stable)
[ ] Oracle page working (F1 complete)
[ ] Briefing Room live (F2 complete)
[ ] Nostr monitor running (F4 complete)
[ ] Node Watch live (F5 complete)
[ ] Newsletter sending (B1 complete)
[ ] 100+ articles indexed and live
[ ] BTC price proxy sub-second (<500ms)
[ ] All 12 nav pages returning HTTP 200
```

### LAW 2: Price milestone triggers (fire ONCE per milestone, never repeat)
```python
MILESTONES = [
    {"price": 100_000, "label": "SIX FIGURES", "campaign": "btc_100k"},
    {"price": 120_000, "label": "$120K",        "campaign": "btc_120k"},
    {"price": 150_000, "label": "$150K",        "campaign": "btc_150k"},
    {"price": 175_000, "label": "$175K",        "campaign": "btc_175k"},
    {"price": 200_000, "label": "TWO HUNDRED",  "campaign": "btc_200k"},
    {"price": 250_000, "label": "$250K",        "campaign": "btc_250k"},
    {"price": 500_000, "label": "HALF MILLION", "campaign": "btc_500k"},
    {"price": 1_000_000, "label": "ONE MILLION","campaign": "btc_1m"},
]
```

### LAW 3: What each milestone trigger fires
1. Auto-generates a special Pulse Check episode (urgent tone, milestone framing)
2. Posts Nostr note celebrating the milestone
3. Sends newsletter blast to all subscribers
4. Activates homepage banner for 48 hours
5. Updates Oracle briefing context to reference the milestone

### LAW 4: Performance metrics schema
```sql
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    page_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    articles_published INTEGER DEFAULT 0,
    videos_rendered INTEGER DEFAULT 0,
    oracle_sessions INTEGER DEFAULT 0,
    briefings_generated INTEGER DEFAULT 0,
    newsletter_opens INTEGER DEFAULT 0,
    newsletter_clicks INTEGER DEFAULT 0,
    btc_price_open REAL,
    btc_price_close REAL,
    milestone_triggered TEXT,  -- NULL or milestone label
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## MILESTONE TRIGGER SERVICE

```python
# services/milestone_service.py
class MilestoneService:
    def check_price(self, current_price):
        """Called every 5 min by price monitor cron"""
        for milestone in MILESTONES:
            if not self.already_fired(milestone['price']):
                if current_price >= milestone['price']:
                    self.fire_milestone(milestone)
    
    def already_fired(self, price):
        return db.session.query(MilestoneFired).filter_by(price=price).first() is not None
    
    def fire_milestone(self, milestone):
        # 1. Log it
        # 2. Trigger emergency Pulse Check generation
        # 3. Post to Nostr
        # 4. Send newsletter blast
        # 5. Activate homepage banner
        # 6. Mark as fired (never repeat)
        pass
```

## VERIFICATION
- [ ] performance_metrics table exists
- [ ] Milestone check runs every 5 min without error
- [ ] Test milestone with fake price: $1M → all 5 actions fire
- [ ] already_fired() prevents double-trigger
- [ ] Launch gate checklist endpoint: /api/launch-gate returns gate status
- [ ] regression_test.sh: zero FAILs

## CLAUDE CODE PROMPT
```
Read ~/protocol_pulse/docs/gospels/F6_MARKETING_OS_GOSPEL.md.
Branch: feature/f6-marketing-os.
1. Create DB migrations: performance_metrics + milestone_fired tables
2. Create services/milestone_service.py
3. Add milestone check to price monitor cron (every 5 min)
4. Create /api/launch-gate endpoint (returns all 9 gate statuses)
5. Add homepage banner component (shows 48h after milestone, auto-hides)
6. Create weekly performance analysis cron (Sunday 00:00 UTC)
7. regression_test.sh: zero FAILs → commit + push feature/f6-marketing-os
```

## LLM TRIFECTA
### Claude: RISK — double-trigger if price oscillates around threshold. already_fired() is critical.
### Gemini: "Is APScheduler appropriate for milestone triggers, or should this be Redis-based?"
### Grok: "Current BTC price? Will any milestones fire immediately on deploy?"

