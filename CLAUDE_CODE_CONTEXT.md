# PROTOCOL PULSE — COMPLETE CONTEXT FOR AUTONOMOUS WORK
# Last updated: March 3, 2026
# Push this to /home/runner/workspace/CLAUDE_CODE_CONTEXT.md before starting any session

## WHAT IS PROTOCOL PULSE

Protocol Pulse is an automated Bitcoin intelligence platform. It generates articles every 15 minutes, has an AI avatar (The Oracle) that delivers briefings via lip-synced video, and provides real-time market data, network stats, and community tools. The brand aesthetic is DARK CINEMATIC — deep blacks (#0a0f0a to #111), red accent (#CC2222), green for BTC price, monospace terminal feel. Think Bloomberg Terminal meets cypherpunk.

## INFRASTRUCTURE

### Replit (Frontend + API + DB)
- Flask/Python app at /home/runner/workspace/
- Main entry: main.py → imports app from app.py
- Routes: routes.py (8,478 lines — the big one)
- Templates: /home/runner/workspace/templates/ (50+ HTML files)
- Static: /home/runner/workspace/static/
- DB: PostgreSQL via DATABASE_URL env var
- Gunicorn: 1 worker, 2 threads, port 5000
- Domain: protocolpulse.replit.app

### Ultron (GPU Server — 2x RTX 4090)
- Avatar server: /home/ultron/protocol_pulse/oracle/avatar_server.py (port 8200)
- Wav2Lip-GAN engine with eye blinks + head movement
- Cloudflare tunnel: avatar.protocolpulse.io → localhost:8200
- Relay server: /home/ultron/protocol_pulse/ultron_relay.py (port 8201)
- Cloudflare tunnel: relay.protocolpulse.io → localhost:8201
- Voice: ElevenLabs Jessica (cgSgspJ2msm6clMCkdW9)
- LLM: Claude Sonnet 4.5 for Oracle responses

### GitHub
- Repo: consensusprotocol/protocol-pulse-core
- RULE: Every change must be committed and pushed

## KEY DATABASE TABLES

- `articles` — Main articles table. Key columns: id, title, content, summary, category, status (published/draft), cover_image_url, slug, created_at
- `article` — DUPLICATE table (legacy). Some code references this, some references `articles`. Be careful.
- `podcast` — Podcast episodes with cover_image_url
- `affiliate_partner` — Affiliate programs (slug, url, category)
- `sponsor` — Sponsor relationships
- `onboarding_session` — User onboarding responses
- `oracle_sessions` — Oracle chat history
- `pulse_event` — Events data

## WHAT WORKS RIGHT NOW (DO NOT BREAK)

1. Article generation pipeline — every 15 min, uses Claude API + Grok fact-checking, publishes to `articles` table
2. Homepage — renders with latest articles, BTC price, hero section
3. Oracle page (/oracle) — full pipeline: Claude → ElevenLabs TTS → Wav2Lip video → plays in browser
4. Article pages (/articles, /articles/<id>) — server-rendered, working
5. Live Pulse (/market) — real-time BTC data, market dashboard
6. Dossier (/dossier) — "Sovereign 7" interactive experience (937 lines, canvases, quizzes)
7. Search, About, Contact, Donate pages — all working

## WHAT IS BROKEN OR NEEDS WORK

### CRITICAL
1. **Podcasts page** (/podcasts) — Design is terrible. Intelligence Operators section has broken Twitter profile images (pbs.twimg.com blocks hotlinking). Quotes are hardcoded, not live data. Needs complete visual overhaul. Template: templates/podcasts.html
2. **Signal Clips page** (/clips) — Shows "0 clips" with ugly placeholder. Template: templates/clips.html (probably). Video pipeline exists but isn't producing clips yet. UI needs professional overhaul even for empty state.
3. **Onboarding** (/onboarding) — Repeats same question 4x, submission fails, affiliate recommendations too aggressive. Template: templates/oracle_onboarding.html. Service: services/onboarding_service.py. REDESIGN as conversational flow, not quiz.
4. **Charts page** (/charts) — Missing gold/silver/copper/real estate charts below BTC. Should show "everything measured in Bitcoin."
5. **Maps page** (/map) — Too dark, hard to read. Missing Bitcoin event markers. Template: may use Leaflet/Mapbox.
6. **Live Pulse reorganization** (/market) — Too many widgets crammed together. Some belong on other pages. Template: templates/live_terminal.html (7000+ lines)

### ALREADY FIXED TODAY (DO NOT REDO)
- Article image deduplication (threshold set to >1, 589 overused images cleared)
- Glow effects removed (60 patterns across 32 templates)
- Meanwhile CTA updated (/go/meanwhile → /articles/1838)
- Timechain Clock removed
- Events page created (/events)
- Events nav link added
- Oracle avatar verified working (lip sync PASS, blinks PASS, head movement PASS)
- Git cleanup on Ultron

## DESIGN STANDARDS

- Background: #0a0f0a to #111111 (very dark, almost black)
- Primary accent: #CC2222 (Protocol Pulse red)
- Secondary: green for BTC positive, amber for neutral
- Font: 'Space Mono' for monospace headers, system sans-serif for body
- Cards: background rgba(20,20,20,0.8), border 1px solid rgba(255,255,255,0.08), border-radius 8px
- NO animated glow effects on cards. Use subtle static box-shadow: 0 1px 3px rgba(0,0,0,0.3)
- Hover: box-shadow: 0 4px 12px rgba(0,0,0,0.4) with transition 0.3s
- Section headers: uppercase, letter-spacing 3px, font-size 0.75rem, color #CC2222
- This is NOT a generic Bootstrap site. Every element should feel hand-crafted and cinematic.

## TEMPLATE PATTERN

Most templates extend base.html:
```
{% extends 'base.html' %}
{% block title %}Page Title | Protocol Pulse{% endblock %}
{% block content %}
  ...
{% endblock %}
```

base.html contains: nav bar, search overlay, footer, common CSS/JS. Nav links are in base.html.

## ARTICLE ROUTING

Articles use INTEGER IDs, not slugs: /articles/<int:article_id>
Route is in routes.py around line 1362.

## ORACLE PIPELINE

1. User types question on /oracle page
2. Frontend POSTs to /api/oracle/speak with {message, history}
3. oracle_routes.py: call_claude() → generate_tts() → generate_avatar_video()
4. generate_avatar_video() POSTs audio_base64 to https://avatar.protocolpulse.io/generate
5. Returns {response, audio_base64, video_base64, pipeline_time}
6. Frontend plays video in circular avatar container + audio separately

## AFFILIATE SYSTEM

Meanwhile affiliate: https://application.meanwhile.bm/start?referralCode=KKM73K
Legacy Leak CTA on Live Pulse now links to /articles/1838 (article about Meanwhile)
Affiliate partners in DB: affiliate_partner table
Oracle onboarding recommends affiliates based on user answers

## ENVIRONMENT VARIABLES AVAILABLE

ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, PEXELS_API_KEY, XAI_API_KEY (Grok), 
OPENAI_API_KEY, DATABASE_URL, RESEND_API_KEY (newsletter, not active),
various social media tokens

## RULES

1. NEVER break existing working features
2. ALWAYS git commit and push after changes
3. Test every change by curling the page
4. Dark cinematic aesthetic — no bright whites, no generic Bootstrap blue
5. No animated glow effects on cards
6. Mobile responsive (check at 375px width)
7. Every template change needs gunicorn restart: kill -HUP $(pgrep -f 'gunicorn.*main:app' | head -1)
