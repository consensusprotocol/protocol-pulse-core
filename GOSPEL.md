# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 SPONSOR AGENT V2
# Branch: feature/p3-sponsor-agent | Created: 2026-03-09

---

## WHAT THIS IS
Fully automated sponsor intelligence and outreach pipeline. Protocol Pulse needs
revenue. This system finds sponsors, scores them via AI deep research, drafts
hyper-personalized outreach using Protocol Pulse's actual metrics, manages the
pipeline in a Kanban admin UI, and auto-follows up. Passive revenue engine.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-sponsor-agent --phase0
Ask all 3 LLMs: "What are the most advanced 2026 B2B SaaS sponsor/sales intelligence
features that would give a Bitcoin media company an unfair advantage in closing sponsors?"
Incorporate top P0 ideas before building.

## THE LAWS
### LAW 1: Grok Deep Research for prospect intelligence — never hallucinate
- Use Grok-3 with web search to research each prospect company
- Prompt: "Search for recent news, ad spend signals, and podcast sponsorships for [company].
  Is this company currently spending on Bitcoin/crypto podcast ads?"
- Store raw Grok response as intelligence_notes in sponsors table
- Never make up metrics or contact info

### LAW 2: Outreach is hyper-personalized — never generic
- Every outreach draft references: the specific podcasts they sponsor,
  their product category fit with Bitcoin audience, Protocol Pulse actual stats
- Pull live stats from sponsorship_metrics_service.py
- Claude Sonnet drafts; Grok-3 reviews for "would a real sponsor reply to this?"

### LAW 3: Pipeline is sacred — no data loss
- Every state change logged to sponsor_activity_log table with timestamp + actor
- Soft-delete only (is_deleted flag) — never hard delete a sponsor record
- Nightly backup: sponsors table → CSV in ~/protocol_pulse/data/backups/

### LAW 4: Email via Resend only — RESEND_API_KEY in .env
- All outreach sent via Resend (configured, available)
- Track delivery + open rates if Resend webhooks available
- Never send without confirmation from admin UI

## ARCHITECTURE

### Database Schema (add to existing pp.db)
```sql
CREATE TABLE IF NOT EXISTS sponsors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name TEXT NOT NULL,
  category TEXT,                     -- hardware_wallet|exchange|fintech|vpn|health|other
  website TEXT,
  contact_email TEXT,
  contact_name TEXT,
  contact_linkedin TEXT,
  estimated_monthly_spend TEXT,      -- "$5k-$15k/mo" — from Grok research
  podcasts_they_sponsor TEXT,        -- JSON array
  relevance_score INTEGER DEFAULT 0, -- 0-100 AI-calculated
  opportunity_signal TEXT DEFAULT "stable", -- growing|stable|declining
  outreach_angle TEXT,               -- the hook angle Claude identified
  intelligence_notes TEXT,           -- raw Grok deep research result
  status TEXT DEFAULT "prospect",    -- prospect|outreach_drafted|contacted|replied|negotiating|deal|rejected
  pipeline_stage INTEGER DEFAULT 1,  -- 1-6 Kanban stage
  deal_value_monthly INTEGER,        -- estimated if converted
  notes TEXT,
  is_deleted INTEGER DEFAULT 0,
  last_contacted_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sponsor_outreach (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sponsor_id INTEGER REFERENCES sponsors(id),
  version INTEGER DEFAULT 1,         -- draft iteration
  channel TEXT DEFAULT "email",      -- email|linkedin|twitter
  subject TEXT,
  body TEXT,
  grok_review_score INTEGER,         -- Grok scored 0-100 "would a sponsor reply?"
  grok_review_notes TEXT,
  sent_at DATETIME,
  resend_message_id TEXT,
  opened_at DATETIME,
  replied_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sponsor_activity_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sponsor_id INTEGER REFERENCES sponsors(id),
  action TEXT NOT NULL,              -- scan_found|outreach_drafted|email_sent|status_changed|note_added
  detail TEXT,
  actor TEXT DEFAULT "system",       -- system|pbx|admin
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Services
```
services/sponsor_radar_v2.py       — Grok-powered prospect scanner
services/sponsor_outreach_gen.py   — Claude-drafted hyper-personalized emails
services/sponsor_followup.py       — auto follow-up sequence scheduler
```

### sponsor_radar_v2.py
Phase 1: Grok scans 20 Bitcoin podcasts for active sponsors (last 90 days)
Phase 2: For each sponsor found: Grok deep research (company profile, ad spend signals)
Phase 3: Claude scores each sponsor 0-100 for Protocol Pulse fit
Phase 4: Saves to sponsors table, logs to activity_log
Run: python3 -m services.sponsor_radar_v2 --scan
Cron: Sundays at 2 AM

### sponsor_outreach_gen.py
generate_draft(sponsor_id) → dict:
1. Pull sponsor record + Protocol Pulse live metrics (views, visitors, article count)
2. Claude Sonnet drafts email: 3 paras, data-first, Bitcoin audience angle
3. Grok-3 reviews draft: scores it 0-100 "would a busy marketing manager reply?"
4. If score < 70: Claude revises once based on Grok feedback
5. Save best draft to sponsor_outreach table
6. Return {subject, body, grok_score, grok_notes}

### Admin Routes
GET  /admin/sponsors                → Kanban pipeline board
GET  /admin/sponsors/list           → table view with filters
POST /api/sponsors/scan             → trigger radar scan
POST /api/sponsors/draft/{id}       → generate outreach draft
POST /api/sponsors/send/{id}        → send via Resend (confirmation required)
POST /api/sponsors/status/{id}      → update status + log activity
GET  /api/sponsors/export           → CSV export
GET  /api/sponsors/metrics          → pipeline funnel stats

### Admin UI — /admin/sponsors
DESIGN: Dark cyberpunk Kanban board — 6 columns:
PROSPECT → RESEARCHED → DRAFTED → CONTACTED → REPLIED → DEAL
Each card: company name, score badge, category tag, last activity time
Drag cards between columns (native drag-and-drop, no jQuery UI)
Click card: slide-in panel showing: company profile, Grok intel, draft emails, activity log
"Generate Outreach" button → calls /api/sponsors/draft/{id} → shows draft inline
"Send Email" button → shows preview → confirm → sends via Resend
Top stats bar: total prospects | contacted | reply rate % | projected MRR

### Public Sponsorship Deck — /sponsorship
Live media kit page:
- Protocol Pulse reach stats (from sponsorship_metrics_service.py): views, visitors, articles
- Audience profile: Bitcoin-first, high-income, self-sovereign, technically sophisticated
- Ad packages with prices:
  Pulse Check Pre-roll: $500/episode (30s before video)
  Article Sponsorship: $300/article (logo + mention in body)
  Newsletter Feature: $200/send (dedicated section)
  Commander Bundle: $1,500/month (all placements)
  Custom Package: Contact
- "Partner With Us" form → saves to sponsors table as inbound lead, status=inbound
- Elegant dark design, gold accent on prices, red CTA button

## VERIFICATION
- [ ] python3 -m services.sponsor_radar_v2 --scan completes, writes ≥5 prospects to DB
- [ ] POST /api/sponsors/draft/{id} returns subject + body + grok_score
- [ ] GET /admin/sponsors → Kanban board renders with real data
- [ ] GET /sponsorship → HTTP 200 with live metrics
- [ ] Inbound form saves sponsor with status=inbound
- [ ] CSV export works
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-sponsor-agent
