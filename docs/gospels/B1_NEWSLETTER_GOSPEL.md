# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: B1 NEWSLETTER ENGINE
# Branch: feature/b1-newsletter | Created: 2026-03-09
---

## WHAT THIS IS
Daily newsletter sent to subscribers via Resend API. Auto-generated from the day's
top articles + network stats + a brief from Oracle. Sends at 08:00 ET daily.

## THE LAWS
### LAW 1: Resend API only (RESEND_API_KEY in .env)
### LAW 2: One newsletter per day. Never two in the same day.
### LAW 3: Newsletter format
```
Subject: "Protocol Pulse — [Date] | BTC: $[price] [change]"
From: pulse@protocolpulse.io
Content:
  - Top story (featured article title + 2-sentence summary)
  - 4 other articles (title + 1-sentence)
  - Network stat of the day (hashrate or difficulty)
  - Oracle signal of the day (today's signal text)
  - CTA: "Read full briefing at protocolpulse.io"
  - Footer: unsubscribe link, npub address
```
### LAW 4: Unsubscribe must work (CAN-SPAM compliance)
- Unsubscribe link: /unsubscribe?token={unsubscribe_token}
- Token = UUID per subscriber, stored in newsletter_subscribers table

## DATABASE
```sql
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    unsubscribe_token TEXT UNIQUE NOT NULL,
    subscribed BOOLEAN DEFAULT 1,
    subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    unsubscribed_at DATETIME,
    source TEXT  -- 'homepage', 'api', 'import'
);

CREATE TABLE IF NOT EXISTS newsletter_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    resend_batch_id TEXT,
    recipient_count INTEGER,
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## FLASK ROUTES
```python
@app.route('/api/newsletter/subscribe', methods=['POST'])  # POST {email}
@app.route('/unsubscribe')                                  # GET ?token=xxx
@app.route('/api/newsletter/send', methods=['POST'])        # Admin trigger
```

## VERIFICATION
- [ ] POST /api/newsletter/subscribe adds subscriber
- [ ] Cron sends at 08:00 ET
- [ ] Resend API call succeeds (test with PBX email first)
- [ ] Unsubscribe link works
- [ ] regression_test.sh: zero FAILs

## CLAUDE CODE PROMPT
```
Read ~/protocol_pulse/docs/gospels/B1_NEWSLETTER_GOSPEL.md.
Branch: feature/b1-newsletter.
pip install resend --break-system-packages
1. DB migrations: newsletter_subscribers + newsletter_sends
2. Create services/newsletter_service.py (content assembly + Resend send)
3. Add subscribe/unsubscribe routes
4. Create cron/newsletter_cron.py (08:00 ET daily)
5. Test: send to pbx@protocolpulse.io manually
6. regression_test.sh: zero FAILs → commit + push feature/b1-newsletter
```

