# FEATURE SPEC — newsletter-engine
## IDENTITY
- **FEATURE:**       Newsletter automation via Resend
- **BRANCH:**        agent/newsletter-engine
- **WORKTREE_DIR:**  ~/worktrees/newsletter-engine
- **SESSION:**       agent_newsletter-engine
- **PRIORITY:**      🟢 Queue

## SCOPE
Build automated newsletter generation and delivery via Resend API.
Weekly newsletter: top 5 articles, BTC price summary, Suits & Sats macro insight,
X Spaces highlights. HTML email template matching Protocol Pulse visual system.
Triggered: Sunday 8am UTC. Admin trigger: POST /api/newsletter/send.
Subscriber management via existing DB. Unsubscribe link required.

## SUCCESS CRITERIA
1. Newsletter generated from last 7 days of articles (top 5 by views/score)
2. HTML template matches Protocol Pulse visual system (dark, orange accents)
3. Suits & Sats macro insight included if tradfi_weekly.json exists
4. Resend API sends without error (test with verified sender domain)
5. Unsubscribe link functional
6. Cron: Sunday 8am UTC fires newsletter_engine.py
7. Admin endpoint POST /api/newsletter/send triggers manual send
8. Regression zero FAILs

## FILES_TO_TOUCH
- `core/services/newsletter_engine.py` — create
- `core/routes.py` — /api/newsletter/send endpoint
- `templates/newsletter_template.html` — create

## FILES_NEVER_TOUCH
- `video_pipeline_v3/` — no pipeline touches
- `regression_test.sh`

## GPU USAGE
- Requires GPU render: NO

## PR FORMAT
- **Title:** `feat(newsletter): automated weekly newsletter via Resend — articles, BTC, Suits & Sats`

## STATUS
- [x] Spec written
- [ ] Agent launched
