# Protocol Pulse — Linear Ticket Backlog
# Generated: 2026-03-12 | Import into Linear: linear.app
# Three teams: VIDEO PIPELINE | ORACLE | ARTICLES

---

## TEAM: VIDEO PIPELINE

### PP-001 | P0 | First Grade A render
**Status:** In Progress
**Acceptance Criteria:**
- [ ] `smart_render_loop.py` running in tmux:smart_loop
- [ ] Gemini grader returns Grade A (score >= 88)
- [ ] Zero critical failures: no silence gaps, no black frames, true peak <= -1.0 dBTP
- [ ] Duration 400-550s
- [ ] Bitrate >= 3.0 Mbps
- [ ] WINNER_RECIPE.json written to logs/
- [ ] Episode watchable end-to-end without interruption

**Blocked by:** Nothing — in progress

---

### PP-002 | P0 | Assembler audio pipeline clean
**Status:** In Progress (assembler_fix committed)
**Acceptance Criteria:**
- [ ] True peak consistently <= -1.5 dBTP across 3 consecutive renders
- [ ] loudnorm TP=-2.0 confirmed in ffmpeg command in assembler.py
- [ ] dynaudnorm second-pass limiter active
- [ ] No audio clipping reported by Gemini grader

---

### PP-003 | P0 | Silent gaps eliminated
**Status:** In Progress
**Acceptance Criteria:**
- [ ] Zero silence gaps > 2s in any render
- [ ] TTS pre-validation: files < 5KB rejected before assembly
- [ ] Eryn voice ID kdnRe2koJdOK4Ovxn2DI confirmed generating audio each render
- [ ] Silence detection in post-render forensics confirms 0 gaps

---

### PP-004 | P1 | Episode duration control
**Status:** In Progress
**Acceptance Criteria:**
- [ ] All renders land 400-550s (6.5-9min)
- [ ] Clip duration cap 90s max enforced in manifest_builder.py
- [ ] 5 clips x ~80s avg = ~400s base before narration
- [ ] Duration check in pre-flight catches out-of-range before full render

---

### PP-005 | P1 | Inworld TTS switchover
**Status:** Committed, not activated
**Acceptance Criteria:**
- [ ] TTS_PROVIDER=inworld set in .env
- [ ] Lauren (HOST_1) and Nate (HOST_2) generating audio confirmed in render log
- [ ] Grade comparison: Inworld render vs ElevenLabs render documented
- [ ] atempo=1.2 post-processing verified in output audio

---

### PP-006 | P1 | QC pre-flight gate
**Status:** Committed
**Acceptance Criteria:**
- [ ] Pre-flight catches: silence, true peak, black frames BEFORE upload
- [ ] False positive rate: 0% (no more 94/100 on broken renders)
- [ ] Pre-flight runtime < 60s
- [ ] On failure: specific failure reason logged, render NOT uploaded

---

### PP-007 | P2 | Automated daily cron at 14:00
**Status:** Not started
**Acceptance Criteria:**
- [ ] crontab entry: 0 14 * * * cd ~/protocol_pulse && python3 smart_render_loop.py
- [ ] Previous day's episode confirmed before triggering new one
- [ ] Resend email alert on Grade A (fix domain verification first)
- [ ] Discord webhook on failure

---

### PP-008 | P2 | Vertical video (9:16) output
**Status:** Backlog — do NOT start until PP-001 locked
**Acceptance Criteria:**
- [ ] 1080x1920 output variant alongside 1920x1080
- [ ] Clip reframing: center-crop with subject detection
- [ ] Host narration segments: portrait layout with lower-third
- [ ] Separate output folder: output/{date}/vertical/

---

## TEAM: ORACLE (Avatar)

### OR-001 | P0 | Avatar generate < 15s, no 503
**Status:** In Progress (avatar_final CC running)
**Acceptance Criteria:**
- [ ] curl -X POST /generate with 15-word text returns 200 in < 15s
- [ ] File size > 50KB, valid mp4
- [ ] Two consecutive /generate calls both return 200 (no lock contention)
- [ ] GFPGAN: zero lines in avatar_server.log after restart
- [ ] avg_latency_sec < 15 confirmed in /health after 5+ requests

---

### OR-002 | P0 | GFPGAN fully removed
**Status:** In Progress
**Acceptance Criteria:**
- [ ] grep -rni "gfpgan" oracle/ returns zero results
- [ ] face_enhancer.py enhance_frames_batch() returns frames passthrough
- [ ] model_registry.py: no GFPGAN model loaded at startup
- [ ] Startup log contains zero "GFPGAN" mentions
- [ ] Visual quality of output still acceptable (sharpen_mouth_region active)

---

### OR-003 | P0 | Oracle page end-to-end working
**Status:** Not verified
**Acceptance Criteria:**
- [ ] protocolpulse.io/oracle loads HTTP 200
- [ ] Clicking "Ask Oracle" sends text, receives video response
- [ ] Video plays in browser without buffering
- [ ] Jessica voice (cgSgspJ2msm6clMCkdW9) confirmed in TTS log
- [ ] Mobile: page usable on iPhone Safari

---

### OR-004 | P1 | Vision: Bitcoin device identification
**Status:** Endpoints exist, not wired to frontend
**Acceptance Criteria:**
- [ ] oracle.html has "Show your device" camera/upload button
- [ ] Image sent to /vision/analyze returns device identification
- [ ] /vision/guide provides step-by-step setup for: Coldcard, Ledger, Trezor, Casa, Umbrel, Bitcoin Core, ASIC miner
- [ ] Oracle speaks the guidance via /generate after vision analysis
- [ ] Works with photo taken on phone in bad lighting

---

### OR-005 | P1 | Oracle briefings auto-published daily
**Status:** Not started
**Acceptance Criteria:**
- [ ] After video pipeline Grade A: oracle briefing auto-generated
- [ ] HeyGen Sarah avatar renders 3x daily briefing clips
- [ ] Clips auto-uploaded to /briefings page
- [ ] Duration 60-90s each

---

## TEAM: ARTICLES

### AR-001 | P0 | Article page loads clean on mobile + desktop
**Status:** Merged (p4-article-page)
**Acceptance Criteria:**
- [ ] protocolpulse.io/articles HTTP 200, renders in < 2s
- [ ] Individual article protocolpulse.io/articles/1 loads with image
- [ ] No 404 on cover_image_url
- [ ] Mobile: readable without horizontal scroll
- [ ] Zero JS console errors

---

### AR-002 | P0 | Article generation pipeline live
**Status:** Running but quality unknown
**Acceptance Criteria:**
- [ ] At least 3 articles generated per day automatically
- [ ] Each article has: title, body >500 words, cover image, category, publish date
- [ ] Grok fact-check running on each article before publish
- [ ] No duplicate articles (semantic dedup confirmed)
- [ ] Category rotation enforced (no 3x same category in a row)

---

### AR-003 | P1 | Article images working
**Status:** Known issue
**Acceptance Criteria:**
- [ ] 90% of articles use Pexels stock photos (verified by spot check)
- [ ] 10% top articles use Grok hyper-realistic images
- [ ] cover_image_url column populated for all articles
- [ ] No broken image links on articles page
- [ ] Images load in < 1s (CDN or direct Pexels URL)

---

### AR-004 | P2 | Signal Terminal data populated
**Status:** Shell only — Nostr/Zap data not ingesting
**Acceptance Criteria:**
- [ ] value_stream_service returns real posts
- [ ] ZapEvent table has data (or graceful empty state shown)
- [ ] Page loads without 500 error
- [ ] Decision: either fix data ingestion or show "coming soon" state

---

## PROCESS RULES (add as team description in Linear)

1. Nothing moves to DONE without every acceptance criterion checked
2. One CC session per ticket — sequential, not parallel  
3. Live URL verification required before closing any ticket
4. smart_render_loop.py is the source of truth for pipeline state
5. PIPELINE_LESSONS.md accumulates all render learnings — read before every fix session
6. New features: backlog only until PP-001, OR-001, AR-001 are all Done
