# PROTOCOL PULSE — MASTER PLAN OF ACTION
# Synthesized from Forensic Audit + Agent 2 Input
# Last updated: 2026-03-05
# Read this before every session. This is the source of truth.

---

## THE NORTH STAR

A fully autonomous daily Bitcoin intelligence machine that:
1. Scans partner channels every morning
2. Selects the best clips with zero human input
3. Produces a broadcast-quality episode
4. Gates quality before upload (score >= 85)
5. Auto-uploads to YouTube + Nostr cross-post
6. Learns from analytics to improve next episode
7. Rotates sponsor reads automatically
8. Never requires PBX to touch it to run

---

## V11-V21 EXECUTION PLAN

### V11 — VOICE + CHANNEL DEDUP + CLIP PADDING [DONE]
- Nicole voice (piTKgcLEGmPE4e6mEKli) replaces Gigi
- Channel dedup enforced in code
- 8s clip padding + silence detection
- 3 commits pushed, regression passed

### V12 — TRANSITION COLORS + FEATURE FLAGS [DONE]
- Red transitions (brand.ts constants)
- config/feature_flags.json with 11 toggles
- 2 commits pushed, regression passed

### FOUNDATION FIX — ASSEMBLER SYNC + HD QUALITY [IN PROGRESS]
- Root cause: concat adding 0.021s drift (clips are clean, assembly breaks them)
- Fix: normalize all parts before concat, PTS reset on final output, -async 1
- Video quality: CRF 17, 8Mbps target (was 1.2Mbps with CRF 20)
- yt-dlp: bestvideo+bestaudio format selector (was grabbing low-quality pre-mux)

### V13 — YOUTUBE AUTO-UPLOAD + QUALITY GATE
- Quality score engine (0-100)
- YouTube Data API v3 upload
- Score < 85 = hold + alert, do not upload
- youtube_auto_upload flag starts FALSE

### V14 — REAL SOCIAL DATA FROM TWEET STUDY
- raw_tweets.json exists (1,943 tweets from 12 accounts)
- social_fetcher.py reads real data
- script_writer.py uses real tweets, not placeholder
- Per Law A1: if no data, skip segment. Never fabricate.

### V15 — TWEET CARD VISUALS
- make_social_card_visual() in assembler.py
- Red-bordered card, dark bg, handle in red, text in white
- Feature-flagged behind tweet_cards toggle

### V16 — EPISODE MEMORY + MAINSTREAM KEYWORD FILTER
- data/used_clips.json tracks video_ids per episode
- Never reuse same video_id
- filter_keywords applied to mainstream channels

### V17 — ANALYTICS FEEDBACK LOOP
- YouTube Analytics API pull (48hr delay)
- data/performance/{episode_id}.json
- Weekly channel scoring

### V18 — TELEGRAM ALERTS + FAST TEST MODE
- Bot alerts on: start, success, failure, quality hold
- --fast-test: skip scan, 2 cached clips, render in 3 min

### V19 — ORCHESTRATOR INTEGRATION
- Wire pipeline into orchestrator.py night runner
- Pass regression -> auto-trigger next version
- Self-healing: retry once on failure, then hold + alert

### V20 — SELF-ANALYSIS + PROMPT EVOLUTION
- After 20 episodes: analyze what correlates with watch time
- Output: data/prompt_recommendations.json
- Human review before prompt updates go live

### V21 — SPONSOR AGENT (MONETIZATION)
- PREREQUISITE: 10+ consecutive clean auto-uploads
- Meanwhile affiliate rotation
- Curated Mining sidebar reads
- RNS.ID referrals ($300/referral)
- Revenue tracking

---

## PIPELINE LAWS
Categories A-G. Full details in PIPELINE_LAWS.md + ADDENDUM.

- A: Data Integrity (no invented data, source diversity, ad read gate, clip buffer)
- B: Visual Consistency (brand colors, Remotion constants, waveform limits, resolution lock)
- C: Audio/Voice (packet-level sync, no loudnorm, Nicole voice, music bed levels)
- D: Intelligence/Self-Learning (performance DB, channel scoring, prompt evolution, quality score)
- E: Process (one session at a time, regression before commit, feature flags, proof required)
- F: Orchestration (night runner, auto-queue, quality gate enforcement)
- G: Systems Integration (shared data layer Replit/Ultron, tweet study feeds V14, sponsor agent V21)

---

## METRICS FOR SHIP READY (V20 target)

| Metric | Current | Target |
|--------|---------|--------|
| AV sync offset | +0.067s | < 0.03s |
| Video bitrate | 1.2 Mbps | > 5 Mbps |
| Clip cutoff rate | ~5% | 0% |
| Channel diversity | 100% | 100% |
| Social segment real data | 0% | 100% |
| Auto-upload | Manual | Automated |
| Quality gate | Not impl | >= 85/100 |
| Analytics feedback | None | Weekly |
| Daily autonomy | ~80% | 99% |

---

## SESSION STARTUP CHECKLIST
Every Claude Code session touching the pipeline must:
1. Read PIPELINE_LAWS.md
2. Read PIPELINE_LAWS_ADDENDUM.md
3. Read PIPELINE_FORENSIC_AUDIT.md
4. Check config/feature_flags.json
5. Confirm which V-version this session implements
6. Confirm files to be touched have no other active session
7. Run bash regression_test.sh BEFORE making changes
8. Make changes, one commit per fix
9. Run bash regression_test.sh AFTER each commit
10. Report SCP path of new render

---

## THE SPONSOR AGENT RULE
Do not touch SPONSOR_AGENT_SPEC.md until:
- V13 (auto-upload) is live and working
- 10 consecutive episodes auto-uploaded without manual intervention
- Quality score averaging >= 85
Monetization on top of broken infrastructure = embarrassing.
Monetization on top of stable infrastructure = compounding.
