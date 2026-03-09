# PHASE 0 ADDENDUM — p3-sponsor-agent
# Generated: 2026-03-09
# Top Phase 0 suggestions → implementation plan

---

## ADDITIONS TO IMPLEMENT (from C0_SYNTHESIS.md)

### 1. Real-Time Signal Streaming via SSE
**What:** Replace pure cron-batch model with SSE endpoint so scan progress streams live to UI.
**How:** `GET /api/sponsors/scan-stream` returns `text/event-stream` with progress events as Grok
         processes each prospect. UI shows live scan log in the Kanban header.

### 2. Autonomous Agent Mode with Confidence Thresholds
**What:** Toggle-able automation rules: auto-draft if score ≥ 85, always require human approval
         to send (LAW 4). Daily limit cap = 25 outreach emails. Follow-up sequence auto-scheduling.
**How:** `sponsors` table gains `auto_draft_enabled` (global config in sponsor_config table).
         `sponsor_followup.py` schedules follow-ups at T+3d, T+7d, T+14d if no reply.
         Kanban shows "AUTONOMOUS" badge when agent mode is on.

### 3. Multi-Source Signal Fusion — Signal Score Breakdown
**What:** Instead of single Grok search, track signal confidence by source type.
         Sources: podcast_ad_detection, news_funding, linkedin_hiring, competitor_ads.
**How:** `intelligence_notes` stores JSON with per-source signals. UI shows signal breakdown chips.
         Radar scans 4 separate signal axes per prospect, fuses into final score.

### 4. Closed-Loop Learning — Outcome Tracking
**What:** Every send/reply/deal/rejection updates a `outcome_data` JSON column on sponsor record.
         Relevance score formula weights updated per category based on historical conversion rates.
**How:** `sponsor_activity_log` records outcomes. `/api/sponsors/metrics` includes conversion funnel.
         Score recalculation on status change: deal=+20, rejected=-15 applied to category baseline.

### 5. Contact Discovery — Email Validation
**What:** Before saving contact_email, validate format + MX record check (socket-based).
         Flag unverified emails with `email_verified` boolean column.
**How:** `validate_email_deliverability()` helper in sponsor_radar_v2.py.
         UI shows green check / red warning icon on each card's email field.

### 6. Deliverability Management — Rate Limiting + Bounce Tracking
**What:** Cap outbound emails at 25/day. Track `bounce_count` + `spam_complaint_count` columns.
         If bounce_rate > 5%, pause auto-send and alert admin in UI.
**How:** `get_daily_send_count()` check before every send. Resend webhook route for bounces.
         Warning banner in Kanban header if daily limit approached.

### 7. Predictive Deal Scoring
**What:** Beyond AI relevance score, compute a `deal_probability_pct` using: score, category
         base rate, signal strength, days-since-last-contact, company size signal.
**How:** `compute_deal_probability(sponsor_record)` function in sponsor_radar_v2.py.
         Stored in `deal_probability_pct` column. Shown as progress bar on each Kanban card.

### 8. Multi-Channel Outreach Orchestration
**What:** UI lets admin select channel: email / LinkedIn / Twitter DM for each outreach draft.
         Channel stored on `sponsor_outreach.channel`. LinkedIn/Twitter just generates copy
         (no auto-send — admin copies and sends manually). Email sends via Resend.
**How:** `generate_draft()` accepts `channel` param. Shorter copy for LinkedIn/Twitter.
         Kanban card shows channel icons. Channel-specific character limits enforced.

---

## VERIFIED SPEC STRENGTHS (keeping exactly as-is)
- Grok deep research as intelligence backbone (LAW 1)
- Claude Sonnet drafts + Grok review loop (LAW 2)
- Soft-delete only, activity log for every state change (LAW 3)
- Email via Resend only, no auto-send without admin confirmation (LAW 4)
- 6-column Kanban: PROSPECT → RESEARCHED → DRAFTED → CONTACTED → REPLIED → DEAL
- Public /sponsorship page with live metrics + inbound form
