#!/usr/bin/env python3
"""
PROTOCOL PULSE — CROSS-LLM CODE AUDIT ENGINE
Full two-cycle audit: build code → Cycle 1 (3 LLMs) → consensus → Cycle 2 (3 LLMs review each other)
→ final winner determination → second Claude Code pass prompt generated

Usage:
    python3 cross_llm_audit.py --feature f1-avatar-oracle
    python3 cross_llm_audit.py --feature all
    python3 cross_llm_audit.py --feature f1-avatar-oracle --cycle 2 --cycle1-results /path/to/c1.json

Requirements in .env:
    GEMINI_API_KEY=...
    OPENAI_API_KEY=...
    XAI_API_KEY=...
    ANTHROPIC_API_KEY=...

Created: 2026-03-09
"""

import os, sys, json, time, threading, argparse, subprocess
from pathlib import Path
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE = Path.home() / "protocol_pulse"
GOSPELS = BASE / "docs/gospels"
AUDITS  = BASE / "docs/audits"
AUDITS.mkdir(parents=True, exist_ok=True)

FEATURE_MAP = {
    "fix-freeze-frames": ("PIPELINE_LAWS.md", "main"),
    "fix-silence-gaps":  ("PIPELINE_LAWS.md", "main"),
    "fix-social-spacetap":  ("PIPELINE_LAWS.md", "main"),
    "fix-pip-left-panel":    ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "fix-grading-loop":      ("PIPELINE_LAWS.md", "main"),
    "fix-elevenlabs-voice":  ("PIPELINE_LAWS.md", "main"),
    "f1-avatar-oracle":  ("F1_AVATAR_ORACLE_GOSPEL.md",  "feature/f1-avatar-oracle"),
    "f2-briefing-room":  ("F2_BRIEFING_ROOM_GOSPEL.md",  "feature/f2-briefing-room"),
    "f3-schiff-bot":     ("F3_SCHIFF_BOT_GOSPEL.md",     "feature/f3-schiff-bot"),
    "f4-nostr":          ("F4_NOSTR_GOSPEL.md",          "feature/f4-nostr"),
    "f5-node-watch":     ("F5_NODE_WATCH_GOSPEL.md",     "feature/f5-node-watch"),
    "f6-marketing-os":   ("F6_MARKETING_OS_GOSPEL.md",   "feature/f6-marketing-os"),
    "v30-terminal-api":  ("V30_TERMINAL_API_GOSPEL.md",  "feature/v30-terminal-api"),
    "b1-newsletter":     ("B1_NEWSLETTER_GOSPEL.md",     "feature/b1-newsletter"),
    "v22-multi-format":  ("V22_MULTI_FORMAT_GOSPEL.md",  "feature/v22-multi-format"),
    "video-audio-fix":   ("VIDEO_AUDIO_FIX_GOSPEL.md",   "feature/video-audio-fix"),
    "assembler-v2-rebuild": ("ASSEMBLER_V2_GOSPEL.md", "main"),
    "x-spaces-pipeline": ("X_SPACES_PIPELINE_GOSPEL.md", "main"),
    "f6-price-alerts":  ("F6_PRICE_ALERTS_GOSPEL.md",   "feature/f6-price-alerts"),
    "f8-sponsor-agent": ("P3_SPONSOR_AGENT_GOSPEL.md",  "feature/f8-sponsor-agent"),
    "f4-cron-heygen":   ("F4_CRON_HEYGEN_GOSPEL.md",   "feature/f4-cron-heygen"),
    "stripe_commander": ("F1_STRIPE_COMMANDER_GOSPEL.md", "feature/f1-stripe-commander"),
    "article_page_laws": ("ARTICLE_PAGE_LAWS.md", "feature/f2-article-laws"),
    "tts-pipeline": ("TTS_PIPELINE_AUDIT_GOSPEL.md", "feature/tts-pipeline"),
    "oracle-stage": ("ORACLE_STAGE_GOSPEL.md", "main"),
    "stage-broadcast": ("STAGE_BROADCAST_GOSPEL.md", "main"),
    "pipeline-day3-audit": ("WATCHDOG_LLM_GOSPEL.md", "main"),
    "watchdog-cc-healing": ("WATCHDOG_LLM_GOSPEL.md", "main"),
    "commander-product-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "pipeline-comprehensive-audit": ("PIPELINE_LAWS.md", "main"),
    "intelligence-terminal": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "convergence-detection": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "convergence-build-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "ml-session-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "render-improvement-loop": ("RENDER_IMPROVEMENT_LOOP_GOSPEL.md", "main"),
    "oracle-avatar-fix": ("PIPELINE_LAWS.md", "main"),
    "content-lock": ("PIPELINE_LAWS.md", "main"),
    "oracle-speak-revert": ("PIPELINE_LAWS.md", "main"),
    "stage-avatar-fix": ("PIPELINE_LAWS.md", "main"),
    "oracle-speed": ("PIPELINE_LAWS.md", "main"),
    "oracle-phase2": ("PIPELINE_LAWS.md", "main"),
    "part-cache": ("PIPELINE_LAWS.md", "main"),
    "stage-fix": ("PIPELINE_LAWS.md", "main"),
    "live-terminal-design": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "social-audit": ("PIPELINE_LAWS.md", "main"),
    "friday-demo": ("PIPELINE_LAWS.md", "main"),
    "oracle-fix": ("PIPELINE_LAWS.md", "main"),
    "oracle-forensic": ("PIPELINE_LAWS.md", "main"),
    "oracle-external": ("PIPELINE_LAWS.md", "main"),
    "media-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "media-command-center": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "panopticon": ("VISUAL_DESIGN_SYSTEM.md", "main"),
    "join-page": ("VISUAL_DESIGN_SYSTEM.md", "main"),
}

# Explicit file lists for features already merged to main (no branch diff available)
EXPLICIT_FILES = {
    "fix-freeze-frames": ["video_pipeline_v3/assembler.py"],
    "fix-silence-gaps":  ["video_pipeline_v3/tts_engine.py"],
    "x-spaces-pipeline": ["x_spaces_scraper/scraper.py","x_spaces_scraper/transcript_fetcher.py","x_spaces_scraper/whisper_worker.py","x_spaces_scraper/diarizer.py","x_spaces_scraper/spaces_state.py","x_spaces_scraper/run_scraper.py","x_spaces_scraper/article_generator.py","x_spaces_pipeline/monitor.py","x_spaces_pipeline/recorder.py","x_spaces_pipeline/transcriber.py","x_spaces_pipeline/curator.py","video_pipeline_v3/utils/spaces_pipeline.py","video_pipeline_v3/utils/spaces_monitor.py","video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py"],
    "assembler-v2-rebuild": [
        "video_pipeline_v3/assembler_v2/constants.py",
        "video_pipeline_v3/assembler_v2/helpers.py",
        "video_pipeline_v3/assembler_v2/manifest.py",
        "video_pipeline_v3/assembler_v2/state.py",
        "video_pipeline_v3/assembler_v2/preflight.py",
        "video_pipeline_v3/assembler_v2/ffmpeg_core/encode.py",
        "video_pipeline_v3/assembler_v2/ffmpeg_core/filters.py",
        "video_pipeline_v3/assembler_v2/ffmpeg_core/probe.py",
        "video_pipeline_v3/assembler_v2/segments/base.py",
        "video_pipeline_v3/assembler_v2/segments/transition.py",
        "video_pipeline_v3/assembler_v2/segments/wrap.py",
        "video_pipeline_v3/assembler_v2/segments/cold_open.py",
        "video_pipeline_v3/assembler_v2/segments/narration.py",
        "video_pipeline_v3/assembler_v2/segments/partner_clip.py",
        "video_pipeline_v3/assembler_v2/segments/data_segment.py",
        "video_pipeline_v3/assembler_v2/segments/social.py",
        "video_pipeline_v3/assembler_v2/segments/signal_active.py",
        "video_pipeline_v3/assembler_v2/episode.py",
        "video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py",
        "video_pipeline_v3/utils/spaces_pipeline.py",
        "video_pipeline_v3/utils/spaces_monitor.py",
    ],
    "fix-pip-left-panel": ["video_pipeline_v3/assembler.py"],
    "fix-social-spacetap": [
        "video_pipeline_v3/daily_producer.py",
        "video_pipeline_v3/script_writer.py",
        "video_pipeline_v3/utils/social_fetcher.py",
    ],
    "fix-grading-loop": ["overnight_render_loop.py", "video_pipeline_v3/gemini_grade.py"],
    "stage-broadcast": ["services/stage_broadcast_service.py","core/routes.py","templates/stage.html"],
    "oracle-stage": [
        "templates/stage.html",
        "routes.py",
    ],
    "pipeline-day3-audit": [
        "video_pipeline_v3/script_writer.py",
        "video_pipeline_v3/tts_engine.py",
        "overnight_render_loop.py",
        "services/local_watchdog.py",
        "video_pipeline_v3/clip_selector.py",
        "video_pipeline_v3/clip_extractor.py",
        "services/montage_producer.py",
    ],
    "watchdog-cc-healing": ["services/local_watchdog.py"],
    "pipeline-comprehensive-audit": [
        "overnight_render_loop.py",
        "video_pipeline_v3/daily_producer.py",
        "video_pipeline_v3/script_writer.py",
        "video_pipeline_v3/tts_engine.py",
        "video_pipeline_v3/assembler.py",
        "services/local_watchdog.py",
    ],
    "commander-product-audit": [
        "docs/cc_commander_premium.md",
        "templates/commander_dashboard.html",
    ],
    "intelligence-terminal": [
        "templates/intelligence_page.html",
        "services/sovereign_context_engine.py",
        "services/polymarket_service.py",
    ],
    "convergence-detection": [
        "docs/phase2/convergence_detection_foundation.md",
        "docs/intelligence_terminal_v1_spec.md",
        "services/sentinel.py",
        "core/blueprints/intelligence.py",
        "core/templates/intelligence_terminal.html",
    ],
    "convergence-build-audit": [
        "docs/phase2/convergence_detection_v1_spec.md",
        "services/sentinel.py",
        "core/blueprints/intelligence.py",
        "core/app.py",
        "core/templates/intelligence_terminal.html",
    ],
    "ml-session-audit": [
        "docs/cc_ml_session.md",
        "docs/phase_ml/pcaf_v1_foundation.md",
        "docs/phase_ml/tpa_foundation.md",
        "services/sentinel.py",
        "core/blueprints/intelligence.py",
    ],
    "render-improvement-loop": [
        "overnight_render_loop.py",
        "utils/cross_llm_audit.py",
        "video_pipeline_v3/assembler.py",
        "video_pipeline_v3/clip_extractor.py",
    ],
    "oracle-avatar-fix": [
        "oracle/avatar_server.py",
        "core/blueprints/oracle.py",
    ],
    "content-lock": [
        "video_pipeline_v3/daily_producer.py",
        "overnight_render_loop.py",
    ],
    "oracle-speak-revert": ["oracle/avatar_server.py"],
    "stage-avatar-fix": [
        "templates/stage.html",
        "routes.py",
        "services/stage_broadcast_service.py",
    ],
    "oracle-speed": [
        "oracle/avatar_server.py",
        "oracle/oracle_cache_manager.py",
        "oracle/cache_render_helper.py",
        "oracle/model_registry.py",
        "oracle/oracle_dialogue_engine.py",
        "oracle/oracle_intelligence_feed.py",
        "oracle/blink_engine.py",
        "oracle/face_enhancer.py",
    ],
    "oracle-phase2": [
        "oracle/avatar_server.py",
        "oracle/oracle_cache_manager.py",
        "templates/oracle_live.html",
    ],
    "part-cache": [
        "video_pipeline_v3/daily_producer.py",
        "video_pipeline_v3/assembler.py",
        "video_pipeline_v3/config/feature_flags.json",
    ],
    "stage-fix": [
        "services/stage_brief_pipeline.py",
        "services/stage_broadcast_service.py",
        "templates/stage.html",
        "oracle/avatar_server.py",
    ],
    "live-terminal-design": [
        "docs/audits/live-terminal-design/live_terminal_excerpt.html",
    ],
    "social-audit": [
        "services/tweet_machine.py",
        "services/x_daily_top_article.py",
    ],
    "friday-demo": [
        "templates/oracle_live.html",
        "oracle/avatar_server.py",
        "templates/merch.html",
    ],
    "oracle-fix": [
        "templates/oracle_live.html",
    ],
    "oracle-forensic": [
        "templates/oracle_live.html",
    ],
    "oracle-external": [
        "templates/oracle_live.html",
    ],
    "media-audit": [
        "templates/media_hub.html",
        "services/rss_service.py",
        "models.py",
        "docs/cc_specs/cc_media_audit.md",
    ],
    "media-command-center": [
        "templates/media_hub.html",
        "services/media_feed_service.py",
        "services/rss_service.py",
    ],
    "panopticon": [
        "services/panopticon_service.py",
        "core/blueprints/panopticon.py",
        "templates/panopticon.html",
        "services/scheduler.py",
    ],
    "join-page": [
        "templates/join.html",
        "core/routes.py",
    ],
}

# For large files, extract only relevant route functions instead of the whole file.
# Key: (feature_name, filename) → list of route prefixes to extract
ROUTE_EXTRACTS = {
    ("oracle-stage", "routes.py"): ["/stage", "/api/stage/", "/api/oracle/"],
    ("stage-avatar-fix", "routes.py"): ["/stage", "/api/stage/"],
    ("oracle-speed", "routes.py"): ["/oracle", "/api/oracle/"],
    ("stage-fix", "routes.py"): ["/stage", "/api/stage/"],
    ("join-page", "routes.py"): ["/join", "/api/apply-promo"],
}

CUSTOM_REVIEW_TASKS = {
    "oracle-speed": """## YOUR REVIEW TASK — ORACLE MAXIMUM SPEED AUDIT (8 CRITICAL QUESTIONS)

You are auditing the Oracle avatar system for LATENCY. Every millisecond matters.
Current: ~15-25s from user input to avatar speaking. Target: <5s perceived, <3s audio start.
Read every file above line-by-line. Your analysis must cite specific line numbers.

### Q1 — CURRENT LATENCY BREAKDOWN
Map every step from POST /oracle/chat to avatar speaking in browser.
Give realistic millisecond estimates for each step:
  - Intent classification
  - Response text generation (Claude Haiku)
  - ElevenLabs/Kokoro TTS call
  - Wav2Lip inference (batch_size=48, FP16, RTX 4090)
  - Video encoding (CRF 18, medium preset)
  - Network transfer to browser
  - Browser decode + play
Where is >80% of latency concentrated?

### Q2 — AUDIO-FIRST STREAMING
The job_id system exists. Audio is fetched first via /oracle/job/<id>/audio.
What is broken/suboptimal in this flow?
How can we get audio to browser in <2s from request?
Can TTS run before Wav2Lip starts? Can audio stream to browser while video renders?

### Q3 — WAV2LIP OPTIMIZATION
Current: batch_size=48, FP16, CRF 18, medium preset, cuda:1.
What are the fastest possible Wav2Lip settings on RTX 4090?
Should batch_size increase beyond 48? GPU memory limit?
Is torch.compile applicable here? Is there a faster lip sync model
(LatentSync, Hallo2, AniPortrait, SadTalker, etc.) that maintains quality?

### Q4 — STREAMING VIDEO DELIVERY
Currently: full video renders, then downloads, then plays.
Can we stream the video as it renders using chunked transfer or HLS?
Minimum chunk size for acceptable lip sync quality?
How would frontend JS need to change for streaming playback?

### Q5 — PARALLEL PIPELINE
Currently: TTS -> Wav2Lip sequential.
Can TTS and Wav2Lip preparation (face detection, mel spectrogram pre-computation)
run in parallel? What is the theoretical minimum latency if audio generation
and video prep are fully parallelized?

### Q6 — PRE-PREDICTION
The INTENT_PATTERNS dict and classify_intent() exist. When a user asks about
"cold wallet", we know before response generation what category the answer is.
Can we pre-render response videos while user is still typing?
What would the architecture look like? Hit rate vs waste ratio?

### Q7 — CACHE ARCHITECTURE
Current cache warms 11 SOVEREIGNTY keys sequentially on startup.
Cache renders block interactive requests via shared GPU semaphore.
What is the optimal caching strategy?
Should cache renders run at low priority on a separate CUDA stream?
Should we cache short 2-3s "thinking" clips to play while rendering?

### Q8 — FRONTEND LATENCY
The oracle_live.html polls /oracle/job/<id> every 2 seconds.
What is the fastest delivery mechanism?
SSE? WebSocket? WebRTC? How to push rendered video/audio
to browser the instant it's ready without polling?

### RESPONSE FORMAT
For each question (Q1-Q8):
- DETAILED ANALYSIS with line number citations
- SPECIFIC RECOMMENDATION with expected latency savings (ms)
- IMPLEMENTATION RISK: LOW / MEDIUM / HIGH
- DEPENDENCIES: what new libs/infra needed

### FINAL SUMMARY
- Total theoretical latency reduction possible (ms)
- Top 3 highest-impact changes
- Which changes conflict with each other
- Recommended implementation order
""",
    "render-improvement-loop": """## YOUR REVIEW TASK — ARCHITECTURE AUDIT (8 CRITICAL QUESTIONS)

You are auditing a GOSPEL SPEC (design document) for an autonomous render improvement loop.
NO code has been written yet. Your job is to find every flaw, gap, failure mode, and token
cost risk BEFORE implementation. Be brutal. Be specific. Cite gospel section numbers.

### Q1 — INTEGRATION RISK
The loop integrates with overnight_render_loop.py via flag files (/tmp/render_fix_complete_iterN).
What are the failure modes? Race conditions? Flag file left over from previous iteration?
Loop crash that never writes the flag, blocking overnight loop forever?

### Q2 — QWEN RELIABILITY
The loop assumes Qwen3:30b is running on Ollama at localhost:11434. What happens if Ollama
is down, model not loaded, or Qwen returns malformed JSON? Does the loop degrade gracefully
or cascade-fail and kill the render cycle?

### Q3 — CC SESSION DETECTION
The loop waits for CC slot by polling tmux. But tmux session names from previous crashed
sessions may still exist as zombies. How does the loop distinguish a live CC session from
a dead one? What is the exact tmux command that proves a session is actively running CC
vs just existing as a shell?

### Q4 — TOKEN COST REALITY
The gospel claims $2 soft limit per cycle. Given 4-6 failing dimensions typically seen
(freeze, avatar, true_peak, visual_polish, etc.), each requiring Qwen + 2 external LLM
calls with ~2000 token payloads, what is the realistic per-cycle cost? Is the $2 limit
achievable or optimistic?

### Q5 — DIMENSION_MAP COMPLETENESS
Review the DIMENSION_MAP in the gospel. Which Gemini grade dimensions are MISSING from
the map? What happens when a new dimension appears in a grade that has no mapping?
Does the loop handle unknown dimensions gracefully?

### Q6 — OVERNIGHT LOOP COUPLING
The minimal change to overnight_render_loop.py is described as "check for flag file,
wait up to 60 min". But overnight_render_loop.py has a 14400s render timeout. If the
improvement loop takes 90 min (CC session can run long), does this blow the timeout?
How should timing be coordinated to avoid killing the render cycle mid-improvement?

### Q7 — CONSENSUS FAILURE HANDLING
When LLMs disagree, the loop sends a Telegram alert and skips the dimension. But if the
3 most critical dimensions (avatar, freeze, visual_polish) all produce disagreement,
the loop commits nothing and the next iteration is identical to the last. What mechanism
prevents infinite identical render loops with no improvement?

### Q8 — IMPLEMENTATION CORRECTNESS
The loop will write fix specs and fire CC. But CC is Opus 4.6 — it reads the spec and
uses its own judgment. What guardrails ensure CC implements ONLY the exact patch and
does not refactor surrounding code, change function signatures, or introduce new
dependencies that break other pipeline stages?

### RESPONSE FORMAT
For each question (Q1-Q8):
- STATE the failure mode(s) clearly
- RATE the severity: CRITICAL / HIGH / MEDIUM / LOW
- PRESCRIBE the exact mitigation (what to add to the gospel)
- CITE the gospel section that needs updating

### FINAL VERDICT
After answering all 8 questions:
- How many CRITICAL issues did you find?
- Is this gospel ready to build from, or does it need fundamental rework?
- What is the single most dangerous gap?
""",
    "live-terminal-design": """## YOUR REVIEW TASK — LIVE TERMINAL VISUAL DESIGN AUDIT (8 DESIGN QUESTIONS)

This is a PRODUCT DESIGN audit, not a code correctness audit.
Goal: Each LLM independently designs the most breathtaking possible real-time
visualization of live Bitcoin network data for a browser page.

CONTEXT — what exists today:
  - live_terminal.html (9,534 lines)
  - Three.js r128 with UnrealBloom post-processing
  - Node globe (Three.js WebGL)
  - 2D canvas mempool bar chart
  - Multiple Chart.js panels
  - WebSocket to wss://mempool.space/api/v1/ws (partially implemented)
  - Data: BTC price, mempool size/fees, hashrate, FNG, block height

The page has GREAT bones but the visualization feels like a collection of
widgets rather than one coherent living thing.

### Q1. HERO VISUALIZATION
Design the centerpiece. What does the "heartbeat of Bitcoin" look like in WebGL?
Be specific about:
- What each particle/node represents
- How transactions appear and travel
- How block confirmations manifest visually
- Color language (what does fee pressure look like? fear vs greed?)
- How Fibonacci ratios or golden spiral physics apply

### Q2. DATA MAPPING
Map each live data point to a visual property.
BTC price → ? Mempool size → ? Hashrate → ? FNG → ?
Block time → ? Fee rate → ? Transaction count → ?

### Q3. LAYOUT
How should the page be organized? The hero vis plus what supporting elements?
What gets cut from the current page?

### Q4. PERFORMANCE
Given Three.js r128 on mobile, what are the specific optimizations needed?
Particle count limits? Instanced mesh vs individual meshes?

### Q5. FIBONACCI/SACRED GEOMETRY
How specifically would you apply golden ratio or Fibonacci spiral to the
particle physics? Give concrete math, not vague references.

### Q6. EMOTIONAL IMPACT
What should a first-time visitor feel in the first 5 seconds? Design that
moment specifically.

### Q7. DATA FRESHNESS
How do you handle the WebSocket connection dropping or mempool.space being slow?
Graceful degradation?

### Q8. KILLER FEATURE
What is the ONE feature that makes this page something people screenshot and
share on Twitter?

### RESPONSE FORMAT
For each question (Q1-Q8):
- DETAILED DESIGN with specific implementable details
- VISUAL DESCRIPTION (describe what the user sees)
- TECHNICAL APPROACH (Three.js specifics, shader details, etc.)
- WHY THIS WINS over alternatives

### FINAL SUMMARY
- Your single strongest design idea
- The one thing that will make people screenshot this
- How this compares to anything else on the web
""",
    "social-audit": """## YOUR REVIEW TASK — SOCIAL PIPELINE PRODUCT AUDIT (8 QUESTIONS)

This is a PRODUCT audit of Protocol Pulse's social media pipeline.
Goal: make every tweet feel like it was written by a brilliant,
opinionated Bitcoiner who lives on a Bitcoin standard and has deep
network intelligence — not an AI bot.

CONTEXT:
- Protocol Pulse = cypherpunk Bitcoin intelligence platform
- Audience = Bitcoiners, node runners, sovereign individuals
- Voice = PBX: contrarian, dry wit, Austrian economics lens
- Current: 1-2 tweets/day from article summaries
- Target: viral-worthy, community-resonant content

### Q1 — SENTIMENT MIRRORING
The user wants to monitor top thought leaders' most-liked posts/comments
for community sentiment, then create our own version of that content.
How do you implement this technically? What sources? What's the pipeline?
Name specific accounts (Preston Pysh, Lyn Alden, Robert Breedlove, TFTC,
Marty Bent, American HODL, etc.) and how to scrape their trending themes.

### Q2 — CONTENT TYPES
Beyond article summaries, what 5 tweet formats would drive the most
engagement for a Bitcoin intelligence brand? Be specific with examples.

### Q3 — TIMING & FREQUENCY
What is the optimal posting schedule for a Bitcoin intelligence account
in 2026? Day/time patterns? How many tweets per day?

### Q4 — REPLY STRATEGY
Should we build automated replies to trending Bitcoin threads?
How do you do it without looking like a bot?

### Q5 — THREAD FORMAT
When and how should we use Twitter threads vs single tweets for maximum reach?

### Q6 — DATA INTEGRATION
We have live BTC price, mempool, FNG, hashrate, block height.
How do you turn this into compelling social content automatically?

### Q7 — COMMUNITY VOICE
How do you make AI-generated content feel genuinely human and community-native?
Specific techniques for the PBX voice (contrarian, dry wit, Austrian economics).

### Q8 — KILLER FORMAT
What is ONE tweet format that would make Protocol Pulse go viral
in the Bitcoin community?

### RESPONSE FORMAT
For each question (Q1-Q8):
- DETAILED ANSWER with specific implementable details
- CONCRETE EXAMPLES (actual tweet text examples)
- TECHNICAL APPROACH (APIs, pipelines, prompts)
- WHY THIS WINS over alternatives

### FINAL SUMMARY
- Your top 3 highest-impact recommendations
- The single most important thing to implement first
- What will make Protocol Pulse's social presence unmistakable
""",
    "friday-demo": """## YOUR REVIEW TASK — FRIDAY DEMO READINESS AUDIT (8 BRUTAL QUESTIONS)

You are auditing Protocol Pulse for a LIVE DEMO in front of 10+ people in 2 days.
Every failure mode, every amateur moment, every broken UX will be seen by a real audience.
Be ruthless. Cite specific line numbers. No mercy.

Files under audit: oracle_live.html (Satomi voice oracle), avatar_server.py (GPU lip-sync server), merch.html (Printful merch store).

### Q1 — MOST LIKELY FAILURE MODE DURING LIVE DEMO
What is the single most likely thing to break during a live demo with 10 people watching?
Consider: network latency, GPU contention, mobile Safari quirks, mic permissions, video autoplay.

### Q2 — PERCEIVED BROKENNESS
What would cause a visitor to think the experience is broken when it actually isn't?
False negatives: loading states that look like errors, delays without feedback, black screens between states.

### Q3 — MOBILE-SPECIFIC FAILURE MODES
What mobile-specific failure modes exist that desktop testing wouldn't catch?
Consider: iOS Safari autoplay restrictions, Android Chrome mic behavior, viewport issues, touch target sizes.

### Q4 — GPU CONTENTION
What happens if the GPU is processing a pipeline render while someone uses the oracle?
How does the semaphore/lock system handle concurrent requests? What does the user see?

### Q5 — WORST UX MOMENT
What is the worst UX moment in the current oracle flow? Where does the experience feel amateur or broken?
Walk through: gate → mic permission → greeting → listening → user speaks → processing → response → listening.

### Q6 — AMATEUR VISUAL ELEMENTS
What visual element would immediately signal "amateur" to a sophisticated audience?
Consider: animation quality, typography, spacing, color consistency, loading states, error messages.

### Q7 — HIGHEST IMPACT SINGLE CHANGE
What is ONE change that would have the highest impact on demo quality?
Be specific — cite the exact file, line, and what to change.

### Q8 — SILENT NETWORK FAILURES
What network conditions would cause a silent failure? Consider:
- Avatar server down but frontend doesn't know
- Slow 3G connection (2s+ latency on every fetch)
- WebSocket/SSE disconnection mid-stream
- Blob URL memory leaks from repeated video plays

### RESPONSE FORMAT
For each question (Q1-Q8):
- FAILURE MODE: What exactly breaks
- SEVERITY: CRITICAL / HIGH / MEDIUM
- FILE:LINE: Exact location in the code
- FIX: Specific code change needed
- DEMO IMPACT: What the audience sees

### FINAL VERDICT
- How many CRITICAL issues did you find?
- Is this demo-ready today?
- Top 3 must-fix items before Friday
""",
    "oracle-fix": """## YOUR REVIEW TASK — ORACLE iOS VIDEO ONENDED RACE CONDITION AUDIT (8 QUESTIONS)

You are auditing the Satomi Oracle live interface (oracle_live.html).
Root cause: After greeting plays, user speaks, but process() never fires.
Server log confirms: /oracle/chat is NEVER received after greeting ends.

The JS chain: playIntent('GREETING') → fetchTO /oracle/speak → playVid(url) → .then() → startRec()
playVid() returns a Promise that resolves on vid.onended.
ON MOBILE (iOS Safari): vid.onended does NOT always fire reliably.
If onended never fires → .then() never fires → startRec() never called → mic dead → busy=true forever.

Read every line of the file. Cite specific line numbers. Be brutal.

### Q1 — PLAYVID PROMISE HANG
In the playIntent() flow, what happens if playVid() Promise never resolves on iOS Safari?
Trace the exact Promise chain from playIntent line 1050 to .finally() line 1100.
What state does the UI get stuck in? Which variables are left in wrong state?

### Q2 — iOS AUTOPLAY + BLOB URLS
How does iOS Safari handle autoplay for blob: URLs — does onended fire reliably?
The code mutes the video first (line 1455), then unmutes on canplay (line 1458-1462).
Is there a scenario where iOS refuses to play, onended never fires, but no error is thrown either?

### Q3 — RACE BETWEEN .then() AND .finally()
Is there a race between .then() (startRec 400ms timer at line 1087) and .finally() (setBusy false at line 1101)?
Could .finally() run BEFORE .then()? If so, the setBusy(false) in .then() would be a no-op
because busy is already false, and the !busy check at line 1088 would pass, but what about isRec?

### Q4 — process() NEVER FIRES AFTER GREETING
After greeting ends and mic starts via startRec(), what exact conditions cause process() to not fire even if user speaks?
Look at recognition.onend (line 1494), the pending variable, and the busy flag.
Could recognition fire onend with empty pending immediately after start()?

### Q5 — RECOGNITION ONEND WITH EMPTY PENDING
The recognition.onend handler (line 1494): if recognition fires onend with no final results (empty pending),
what happens? Does it silently do nothing? Does it restart? Is there any auto-restart logic?

### Q6 — BUSY FLAG DURING USER SPEECH
Could the busy flag ever be true when the user speaks their response, causing process() to return early (line 1111)?
Trace all setBusy(true) and setBusy(false) calls. Is there any timing window where busy stays true
between greeting end and user speech?

### Q7 — iOS MIC ACTIVATION AFTER VIDEO
What is the most reliable way to activate microphone AFTER a video plays on iOS Safari mobile browser?
Does iOS require a user gesture for SpeechRecognition.start()? Can it be called from a Promise chain?
Is the 400ms setTimeout at line 1087 sufficient, or does iOS require a tap event?

### Q8 — SAFETY TIMEOUT ADEQUACY
The safety timeout in playVid (line 1419-1426) is 30 seconds. Is this adequate?
What happens if a greeting video is only 5 seconds — the user waits 30s before mic activates?
Should the safety timeout be based on actual video duration instead of a fixed 30s?

### RESPONSE FORMAT
For each question (Q1-Q8):
- ANALYSIS: Detailed trace with line numbers
- BUG CONFIRMED: Yes/No
- SEVERITY: CRITICAL / HIGH / MEDIUM
- FIX: Specific code change with line numbers

### FINAL VERDICT
- How many CRITICAL issues confirmed?
- Root cause of the "greeting plays but mic never activates" bug
- Ordered fix list (most impactful first)
""",
    "oracle-phase2": """## YOUR REVIEW TASK — ORACLE PHASE 2: THINKING VIDEO + SSE PUSH (4 QUESTIONS)

You are auditing the Oracle avatar system for Phase 2 optimizations.
Phase 1 (commit 6898d3d7) fixed encoding preset and ffmpeg post-processing.
Phase 2 adds: (1) pre-rendered "thinking" video loop, (2) SSE push replacing 2s polling.
Target: 8-15s perceived latency → 4-8s perceived latency.

### Q1 — THINKING VIDEO ARCHITECTURE
Where in oracle_live.html does the video element exist?
When /oracle/chat returns a job_id, what does the frontend currently do while waiting?
What is the minimal change to make it play a looping "thinking" video immediately on chat submit,
then cross-fade to the real video when job completes?
The thinking video should be a 3-4s loop of the avatar with neutral animation
(head movement, blinks) — no mouth movement, no audio. Where should it be generated and stored?

### Q2 — SSE ARCHITECTURE FOR FLASK
Flask threaded mode with long-lived SSE connections: what is the correct implementation pattern?
generator + Response with mimetype text/event-stream? What are the thread-safety concerns
with per-job event queues? How does render_async (which runs in a thread pool) push events
to the SSE generator? Specifically: threading.Event per job, or a queue.Queue?

### Q3 — SSE PAYLOAD DESIGN
What events should the SSE stream send?
  - audio_ready: triggers client to fetch /oracle/job/<id>/audio
  - video_ready: triggers client to fetch /oracle/job/<id>
  - error: render failed
What should happen if client disconnects mid-stream?
How long should the SSE connection stay open?

### Q4 — FRONTEND CROSS-FADE
In oracle_live.html, how should the cross-fade from thinking video to real video work
without glitching? CSS opacity transition? Two overlapping video elements?
What is the minimum thinking video duration before real video arrives that makes the UX
feel responsive vs jarring?

### RESPONSE FORMAT
For each question (Q1-Q4):
- DETAILED ANALYSIS with line number citations from the provided files
- SPECIFIC RECOMMENDATION with expected latency savings (ms)
- IMPLEMENTATION RISK: LOW / MEDIUM / HIGH
- POTENTIAL GOTCHAS that could cause production issues
""",
    "oracle-forensic": """## YOUR REVIEW TASK — ORACLE FORENSIC: GREETING LIP SYNC + RECOVERING LOOP (8 QUESTIONS)

CONFIRMED FACTS FROM SERVER LOGS:
- Server receives POST /oracle/speak -> returns video/mp4 (646KB greeting cache) -> 200 OK
- Server receives GET /oracle/thinking -> 206 (thinking loop served)
- Server receives POST /oracle/chat -> 200 with job_id
- Server renders Wav2Lip correctly (frames, audio, encoding all confirmed working)
- ALL server-side is working perfectly

THE BUGS (user-confirmed, reproducible every time):
BUG 1: Greeting video plays with NO lip sync — Satomi avatar is static/frozen while audio plays
BUG 2: After greeting, any user speech goes to "Recovering" mode and never produces output

### Q1 — iOS SRC SWAP ON ACTIVELY PLAYING VIDEO
The thinking loop video plays first (vid.muted=true, vid.loop=true, vid.src=/oracle/thinking).
When the greeting blob arrives, playVid() sets vid.muted=false, vid.loop=false, vid.src=blobURL.
On iOS Safari: does changing video.src while a video is actively playing require a user gesture?
Could iOS suppress the src change or show a frozen frame from the previous video?

### Q2 — BLOB URL VIDEO PLAYBACK
The greeting is served as a direct video/mp4 response from /oracle/speak (not via job polling).
The frontend checks content-type 'video' and calls r.blob().then(blobURL).
Is there any scenario where the blob URL is created but the video element shows a static frame
instead of playing the lip-sync animation?

### Q3 — RECOVERING STATE MAPPING
After the greeting plays (or appears to play), _greeted=true is set and startRec() is called.
recognition.start() fires. User speaks. recognition.onresult fires and sets pending.
Then recognition.onend fires. process(pending) is called.
process() calls /oracle/chat -> gets job_id -> polls /oracle/job/{id}/audio -> plays audio.
WHERE exactly does "Recovering" state appear and what triggers it?
Map every state transition that could lead to RECOVERING without ever resolving.

### Q4 — RECOVERING NEVER CLEARED
The oracle server logs show the interactive request received and processed successfully
(job rendered, audio ready, video ready). But the frontend shows "Recovering".
This means the frontend either: (a) never receives the job response, (b) receives it but
fails silently, or (c) the setStat('RECOVERING') is called somewhere and never cleared.
Find every place setStat('Recovering') is called and what conditions lead there.

### Q5 — AUDIO/VIDEO RACE CONDITION
Look at the audio polling flow: fetch /oracle/job/{id}/audio with polling retry.
If this returns 202 (audio not ready), it retries. If it returns 200, it plays audio.
Is there a race condition where audio 200 is received but the EventSource for video_ready
fires before audio.onended, causing the state machine to deadlock?

### Q6 — SETTLED GUARD FROM THINKING LOOP
The video element has a settled guard (_settled flag). If _settled=true from the thinking
loop's safety timeout, could it prevent the greeting video from ever triggering _finish()?

### Q7 — iOS BLOB URL + VIDEO ELEMENT ISSUES
On iOS Safari specifically: does fetch() with a blob response work correctly for video/mp4
of 646KB? Are there any known iOS issues with MediaSource, blob URLs, or video element
src swapping that would cause the video to render as a static image?

### Q8 — MUTED FLAG RACE
Is there a timing issue where vid.muted=true is set AFTER playVid() already set it to false?
Trace every place vid.muted is set in the entire template and identify if any async callback
could re-mute the video after playVid() unmutes it.

### RESPONSE FORMAT
For each question (Q1-Q8):
- ANALYSIS: Detailed trace with line number citations
- BUG CONFIRMED: Yes/No
- SEVERITY: CRITICAL / HIGH / MEDIUM
- ROOT CAUSE: Specific code path
- FIX: Specific code change with line numbers

### FINAL VERDICT
- How many CRITICAL issues confirmed?
- Root cause of the lip sync failure
- Root cause of the Recovering loop
- Ordered fix list (most impactful first)
""",
    "oracle-external": """## YOUR REVIEW TASK — ORACLE EXTERNAL AUDIT: DUPLICATE FUNCTIONS + iOS RELIABILITY (4 QUESTIONS)

You are auditing templates/oracle_live.html — the Satomi AI voice oracle for Protocol Pulse.
This file has had 20+ surgical patches applied in 8 hours by multiple developers.
The server side (avatar_server.py, Wav2Lip, Kokoro TTS) is confirmed working — all issues are frontend JS.

The architecture:
- Gate screen: user taps "Activate Microphone" → requestMic() → getUserMedia → go()
- go(): hides gate, shows stage, calls initSR() + playIntent('GREETING')
- playIntent('GREETING'): fetches greeting blob from /oracle/speak, calls playVid()
- playVid(): pause+removeAttribute+load, muted=false, sets src, plays video with baked audio
- After greeting: startRec() creates fresh recognition instance, starts listening
- User speaks → onresult sets pending/transcript → onend auto-submits → process(text)
- process(): calls /oracle/chat with audio_first:false, polls /oracle/job/{id} every 2s
- When video blob arrives: playVid() → video plays with baked audio + lip sync
- After playVid() resolves: setBusy(false) + startRec() → loop continues

Known fix just applied: setBusy(false) was missing `else{mic.disabled=false;}` — mic stayed permanently disabled.

### Q1 — DUPLICATE FUNCTION DEFINITIONS
Scan the ENTIRE file for any function that is defined more than once. In a 2400-line template
with 20+ patches, function definitions can be accidentally duplicated when patches are applied
to the wrong line. List EVERY function name and its line number(s). Flag any function that
appears more than once. Also check for variable name collisions between global scope and
function-local scope that could cause shadowing bugs.

### Q2 — iOS SAFARI POLLING RELIABILITY
The current approach for chat responses is: POST /oracle/chat → get job_id → poll /oracle/job/{id}
every 2 seconds for up to 45 attempts (90 seconds). The video render takes 8-15 seconds on 4x RTX 4090.
On iOS Safari specifically:
- Will the page stay alive during 90 seconds of fetch() polling in the foreground?
- What happens if the user locks their phone briefly during polling?
- Is there a risk of iOS killing the page or suspending JS execution during the poll loop?
- Would a single long-poll fetch be more reliable than repeated short polls?

### Q3 — MINIMAL VIABLE ARCHITECTURE
After all these patches, is there a clean architectural approach that avoids all these failure modes
without a full rewrite? Specifically:
- Can the state machine (IDLE → WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING) be
  simplified to prevent state flag desynchronization?
- Are there redundant state variables that should be consolidated?
- What is the minimum set of state variables needed for correct operation?

### Q4 — WHAT WILL ACTUALLY WORK ON FRIDAY DEMO
Given the current code with all patches applied, what is the most likely failure mode
on an iPhone running iOS Safari during a live demo? Be specific about:
- The exact sequence of events that could fail
- Which state variable is most likely to get stuck
- The single most dangerous race condition remaining
- What manual recovery action the user should take if it breaks during demo

### RESPONSE FORMAT
For each question (Q1-Q4):
- ANALYSIS: Detailed findings with line number citations
- RISK LEVEL: CRITICAL / HIGH / MEDIUM / LOW
- RECOMMENDATION: Specific actionable fix or mitigation

### FINAL VERDICT
- Number of duplicate functions found
- Top 3 risks for Friday demo, ranked by likelihood
- Single most important fix still needed (if any)
""",
    "media-audit": """## YOUR REVIEW TASK — BITCOIN MEDIA COMMAND CENTER ARCHITECTURE (8 DESIGN QUESTIONS)

You are being consulted BEFORE build. The goal: build the definitive Bitcoin media hub page.
One screen. Every voice. Every signal. No competitor comes close.

The existing code shows: templates/media_hub.html (current page with Nostr/X feeds + books + podcasts),
services/rss_service.py (only 2 feeds), models.py (Podcast model, no external feed tracking).

We are adding 15 RSS podcast feeds + 7 YouTube channels + live KOL feeds + signal scoring.

### Q1 — ARCHITECTURE
What is the optimal backend architecture for aggregating 15 RSS feeds + 7 YouTube channels
+ live X/Nostr KOL feeds simultaneously WITHOUT blocking Flask workers or degrading site perf?
Consider: background jobs, Redis caching, SQLite caching, async fetching.
What refresh interval per source type is optimal?

### Q2 — D3 NETWORK GRAPH
Design the Bitcoin voice network topology visualization.
Nodes = Bitcoin voices/channels. Edges = cross-references/mentions.
How do we detect when voices reference each other (quote tweets, mentions)?
What data structure backs this? How do we animate node pulses on new posts?
What's the D3.js force simulation config for ~50 nodes to look stunning?

### Q3 — LIVE TICKER
Design the hyperlinked scrolling ticker at the top.
Each item must deep-link to the exact source (podcast episode, tweet, video).
What's the smoothest CSS animation that doesn't stutter on mobile?
How do we prioritize items (breaking news > new episode > tweet)?

### Q4 — SIGNAL SCORE
Design a 0-100 Signal Score for all content. Inputs: KOL sentiment pipeline,
engagement metrics, topic relevance, source tier (Tier 1 = Odell/Livera/McCormack).
Formula that's backtestable against price action?
How do we calculate this on ingest without API costs?

### Q5 — CLIPS ENGINE
When sentiment pipeline flags high-signal moment (>85% confidence):
YouTube: extract timestamp, generate 60-90s clip via yt-dlp + ffmpeg.
Podcast: extract timestamp from transcript, clip audio.
Overlay Protocol Pulse branded waveform + quote text.
Queue architecture? GPU usage? Storage? Can this run on 4x RTX 4090
without interfering with render pipeline?

### Q6 — EMBEDDED PLAYER
How to embed podcast episodes without redirect? Native HTML5 audio with RSS mp3 URL,
Spotify embed, Apple Podcasts embed, custom player? Which works reliably for all 15 feeds?
How to handle DRM/protected content?

### Q7 — ENGAGEMENT LAYER
Instead of literal drawing wall, what engagement features make Bitcoin users return daily?
Streak tracking, signal accuracy scoring, community price prediction market,
soundboard of famous Bitcoin quotes triggered by price events,
achievement badges for sovereign behaviors.
Which 3 features have highest viral coefficient?

### Q8 — CLAUDE ON INGEST
AI-generated 30-word summaries for each episode using Anthropic API (Claude claude-sonnet-4-6).
How to batch-process RSS items to minimize API cost?
Optimal prompt for 30-word Bitcoin-native signal summary?
How to cache summaries (generate once per episode)?
Estimated monthly cost for 15 feeds x ~20 episodes/week?

### RESPONSE FORMAT
For each question (Q1-Q8):
- DETAILED RECOMMENDATION with specific technologies, configs, code patterns
- ESTIMATED COST / PERFORMANCE impact
- IMPLEMENTATION COMPLEXITY: LOW / MEDIUM / HIGH
- KEY RISKS and mitigations

### FINAL VERDICT
- Top 3 most impactful features for Phase 1 Friday deadline
- Architecture that scales to 50 feeds without rewrite
- The single design decision that separates "good media page" from "best Bitcoin media page on the internet"
""",
    "panopticon": """## YOUR REVIEW TASK — PANOPTICON INTELLIGENCE DASHBOARD AUDIT (5 CRITICAL QUESTIONS)

You are auditing the PANOPTICON dashboard: a congressional insider trading tracker, whale wallet monitor,
and geopolitical intelligence feed cross-referenced with Polymarket prediction markets and Bitcoin on-chain data.

Read every file above line-by-line. Your analysis must cite specific line numbers.

### Q1 — CONGRESSIONAL DATA FETCHING ARCHITECTURE
Is the efts.house.gov API integration correct and production-safe?
- Does the search-index endpoint actually accept these parameters?
- Are there rate limits we're violating?
- Is the XML/JSON parsing robust against schema changes?
- Is the fallback placeholder system appropriate or misleading?

### Q2 — API RATE LIMITING
Are all API endpoints properly rate-limited?
- Blueprint routes: any IP-based throttling?
- External API calls: mempool.space, exchangerate.host, CoinGecko — are we respecting their limits?
- Can a malicious user trigger expensive upstream calls by hammering our endpoints?
- Is the in-memory cache sufficient or do we need Redis/SQLite caching?

### Q3 — CLASSIFIED OVERLAY SECURITY
Is the Commander-gated CLASSIFIED overlay secure against client-side bypass?
- Can a free-tier user inspect DOM, remove CSS classes, or modify JS to see data?
- Is the data actually withheld server-side, or just hidden with CSS?
- Are the API routes properly guarded (not just the page route)?

### Q4 — CORRELATION TIMELINE LOGIC
Is the correlation timeline cross-referencing correct?
- Are temporal correlations actually computed (date math) or just associated?
- Is the correlation_score meaningful or arbitrary?
- Could this produce false correlations that look authoritative?
- Legal risk: does the framing stay within "research correlation" or cross into accusation?

### Q5 — SCALABILITY
Will this scale under 1000 concurrent users?
- In-memory cache: thread-safe? Race conditions?
- External API calls: what happens when 1000 users hit /panopticon simultaneously?
- Does get_dashboard_data() make too many sequential API calls?
- Database writes: any N+1 queries or missing indexes?

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Is the legal framing adequate for a public-facing product?
""",
    "media-command-center": """## YOUR REVIEW TASK — BITCOIN MEDIA COMMAND CENTER AUDIT (5 CRITICAL QUESTIONS)

You are auditing the Bitcoin Media Command Center — the definitive media hub for Bitcoin.
This page aggregates 13 RSS podcast feeds + 7 YouTube channels with live D3 network graph.

### Q1 — ASYNC RSS FETCHING
Are all RSS feeds fetched async without blocking Flask workers?
Check: background threading, sync_feeds_background(), poll interval, error isolation per feed.

### Q2 — D3 NETWORK GRAPH
Is the D3 force simulation correct for 50 nodes?
Check: force configuration, node rendering, hover cards, drag interaction, responsive resize.
Does the data structure (nodes array + links array with source/target) properly feed D3.forceLink?

### Q3 — SIGNAL SCORE ALGORITHM
Will the Signal Score algorithm (source_tier*40 + sentiment*40 + recency*20) produce meaningful differentiation?
Check: keyword weighting, tier scoring, recency decay, normalization, edge cases (score > 100).

### Q4 — TICKER ANIMATION
Is the ticker animation smooth on mobile?
Check: CSS translateX animation, will-change hints, GPU compositing, pause on hover, item truncation.

### Q5 — FEED URL VALIDITY
Are all RSS feed URLs valid and likely to return data?
Check: Simplecast/Megaphone/Anchor URLs, user-agent header, timeout handling, feedparser fallback.

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Overall: PASS / PASS WITH FIXES / FAIL
""",
    "join-page": """## YOUR REVIEW TASK — JOIN PAGE PREMIUM AUDIT (5 CRITICAL QUESTIONS)

You are auditing the /join page for a premium Bitcoin intelligence product ($49/mo Commander tier).
This page is the primary revenue conversion surface. Every pixel matters.

### Q1 — PREMIUM PERCEPTION
Does the page feel premium enough to justify a $49/mo subscription?
Rate the visual hierarchy, glassmorphism quality, typography, color system.

### Q2 — PROMO CODE SECURITY
Is the /api/apply-promo endpoint secure against brute force attacks?
Check: rate limiting, input validation, timing attacks, response enumeration.

### Q3 — STRIPE INTEGRATION
Is the Stripe integration correct for Commander checkout?
Check: STRIPE_PUBLIC_KEY handling, checkout flow, signup modal, error states.

### Q4 — MOBILE LAYOUT
Is the mobile layout production quality?
Check responsive breakpoints (960px, 600px).

### Q5 — VISUAL DESIGN SYSTEM COMPLIANCE
Does the design match the VISUAL_DESIGN_SYSTEM brand standards?
Check: color palette, typography, three-source glow system, glassmorphism.

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Overall: PASS / PASS WITH FIXES / FAIL
""",
    "intelligence-terminal": """## YOUR REVIEW TASK — PREMIUM INTELLIGENCE DASHBOARD COMPETITIVE AUDIT

You are auditing a Bitcoin intelligence dashboard that competes with Bloomberg Terminal ($2000/mo), Glassnode ($500/mo), CryptoQuant ($500/mo), and Santiment ($500/mo). The codebase already collects: BTC price, Fear & Greed, mempool fees, hashrate, lightning stats, KOL sentiment, 1300+ articles with sentiment, exchange flows, whale alerts, Polymarket odds, PCAF anomaly score, and stage brief narratives.

### Q1 — COMPETITIVE GAP ANALYSIS
What specific Bloomberg/Glassnode/CryptoQuant features costing $500-2000/month can we replicate or beat with our existing data? Name exact metrics, charts, and signals.

### Q2 — CROSS-SIGNAL ALPHA
What are the 5 most powerful cross-signal COMBINATIONS from our data that produce predictive alpha? Give specific, backtestable combinations with historical Bitcoin context. Example: hashrate up + exchange outflows + Fear&Greed < 20 = supply shock precursor.

### Q3 — VISUAL INNOVATION
What single visual display would make a hedge fund analyst say "I have never seen this before"? Think beyond standard price charts.

### Q4 — ML MODELS FOR RTX 4090
What open-source ML models (TimeMixer, PatchTST, Chronos, Mamba) can run on RTX 4090 for time-series forecasting without disrupting the render pipeline? Give specific model names, GitHub repos, GPU requirements.

### Q5 — THE $5000/MONTH FEATURE
What is the single feature worth $5000/month that uses ONLY our existing data? Must be technically feasible in one build session and genuinely unique.

### Q6 — DESIGN COMPETITION
What would win a Bloomberg vs Protocol Pulse design competition? Compete on both utility AND visual design. What makes our dashboard look like a $5000/month product vs a free tool?

### RESPONSE FORMAT
For each question: DETAILED ANALYSIS → SPECIFIC RECOMMENDATION → IMPLEMENTATION PRIORITY (P0/P1/P2)

### FINAL SUMMARY
- Top 3 consensus recommendations across all questions
- The single highest-ROI feature to build first
- What to REMOVE as noise
""",
}

DEFAULT_REVIEW_TASK = """## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
"""

def extract_routes_from_file(filepath: Path, route_prefixes: list[str]) -> str:
    """Extract only route functions matching given prefixes from a large Flask routes file."""
    lines = filepath.read_text().split("\n")
    extracted = []
    in_route = False
    route_start = 0
    brace_indent = 0

    for i, line in enumerate(lines):
        # Detect @app.route decorators matching our prefixes
        if "@app.route(" in line:
            for prefix in route_prefixes:
                if prefix in line:
                    in_route = True
                    route_start = i
                    brace_indent = 0
                    break
            else:
                # Different route — if we were capturing, this ends the previous function
                if in_route:
                    extracted.append((route_start, i - 1))
                    in_route = False
        # End of function: next decorator or top-level def/class not indented
        elif in_route and i > route_start + 1:
            stripped = line.strip()
            if stripped and not line.startswith(" ") and not line.startswith("\t") and not stripped.startswith("#") and not stripped.startswith("@"):
                extracted.append((route_start, i - 1))
                in_route = False

    if in_route:
        extracted.append((route_start, len(lines) - 1))

    # Build output with line numbers
    sections = []
    for start, end in extracted:
        chunk_lines = lines[start:end + 1]
        numbered = "\n".join(f"{start + j + 1:4d} | {l}" for j, l in enumerate(chunk_lines))
        sections.append(numbered)

    return "\n\n# ... (other routes omitted) ...\n\n".join(sections)

# High-stakes features get full 2-cycle audit. Others can use 1-cycle if score > 85.
HIGH_STAKES = {"f1-avatar-oracle", "assembler-v2-rebuild", "x-spaces-pipeline", "v30-terminal-api", "v22-multi-format", "f2-briefing-room", "render-improvement-loop", "oracle-speed", "oracle-phase2", "live-terminal-design", "friday-demo", "oracle-fix", "oracle-external"}

# ─── AUDIT PACKAGE BUILDER ───────────────────────────────────────────────────

def build_audit_package(feature_name: str) -> str:
    """Pull all new/modified files from feature branch and assemble audit package."""
    gospel_file, branch = FEATURE_MAP[feature_name]
    gospel_text = (GOSPELS / gospel_file).read_text()

    # Extract just the LAWS section from gospel
    laws_section = ""
    in_laws = False
    for line in gospel_text.split("\n"):
        if "## THE LAWS" in line:
            in_laws = True
        elif line.startswith("## ") and in_laws and "LAW" not in line:
            in_laws = False
        if in_laws:
            laws_section += line + "\n"

    # Get diff vs main
    print(f"  [PACKAGE] Pulling code diff for {branch}...")
    # Check for explicit file list first (features already on main)
    if feature_name in EXPLICIT_FILES:
        diff_files = EXPLICIT_FILES[feature_name]
        print(f"  [PACKAGE] Using explicit file list: {diff_files}")
    elif branch == "main":
        diff_files = []
        print(f"  [PACKAGE] Branch is main and no explicit files — no diff available")
    else:
        try:
            diff_files = subprocess.check_output(
                ["git", "diff", "main.." + branch, "--name-only"],
                cwd=BASE, text=True
            ).strip().split("\n")
            diff_files = [f for f in diff_files if f]
        except Exception as e:
            print(f"  [PACKAGE] Git diff failed: {e}. Using worktree scan.")
            worktree = Path.home() / f"worktrees/{feature_name}"
            if worktree.exists():
                diff_files = [
                    str(p.relative_to(worktree))
                    for p in worktree.rglob("*.py")
                    if "pycache" not in str(p)
                ] + [
                    str(p.relative_to(worktree))
                    for p in worktree.rglob("*.html")
                    if "pycache" not in str(p)
                ]
            else:
                diff_files = []

    # Build code section
    code_sections = []
    worktree = Path.home() / f"worktrees/{feature_name}"
    for fpath in diff_files[:20]:  # cap at 20 files to stay within context
        full_path = worktree / fpath if worktree.exists() else BASE / fpath
        if not full_path.exists():
            continue
        try:
            # Check if we should extract specific routes from a large file
            route_key = (feature_name, fpath)
            if route_key in ROUTE_EXTRACTS:
                numbered = extract_routes_from_file(full_path, ROUTE_EXTRACTS[route_key])
                total_lines = len(full_path.read_text().split("\n"))
                code_sections.append(f"\n### File: {fpath} (extracted stage routes from {total_lines} lines)\n```\n{numbered}\n```")
            elif full_path.stat().st_size < 100_000:
                code = full_path.read_text()
                lines = code.split("\n")
                numbered = "\n".join(f"{i+1:4d} | {l}" for i, l in enumerate(lines))
                code_sections.append(f"\n### File: {fpath} ({len(lines)} lines)\n```\n{numbered}\n```")
        except Exception:
            pass

    code_block = "\n".join(code_sections) if code_sections else "(No code files found — run after Claude Code session completes)"

    # Assemble the full audit package
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    package = f"""# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: {feature_name}
# Branch: {branch}
# Generated: {timestamp}
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
{gospel_text.split("## WHAT THIS FEATURE IS")[1].split("##")[0].strip() if "## WHAT THIS FEATURE IS" in gospel_text else "(see gospel)"}

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
{laws_section}

---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)
{code_block}

---

{CUSTOM_REVIEW_TASKS.get(feature_name, DEFAULT_REVIEW_TASK)}
"""
    return package


# ─── LLM CALLERS ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str, results: dict, errors: dict):
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        results["gemini"] = resp.text
        score_hint = "?"
        for line in resp.text.split("\n"):
            if "OVERALL" in line.upper() and "/100" in line:
                score_hint = line.strip()
                break
        print(f"  [GEMINI] ✅ Done — {score_hint}")
    except Exception as e:
        errors["gemini"] = str(e)
        print(f"  [GEMINI] ❌ ERROR: {e}")

def call_gpt4o(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=6000,
            temperature=0.3,
        )
        results["gpt4o"] = resp.choices[0].message.content
        print(f"  [GPT-4o] ✅ Done")
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"  [GPT-4o] ❌ ERROR: {e}")

def call_grok(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=6000,
            temperature=0.3,
        )
        results["grok"] = resp.choices[0].message.content
        print(f"  [GROK]   ✅ Done")
    except Exception as e:
        errors["grok"] = str(e)
        print(f"  [GROK]   ❌ ERROR: {e}")

def fire_all_llms(prompt: str) -> tuple[dict, dict]:
    """Fire all 3 LLMs in parallel threads. Returns (results, errors)."""
    results, errors = {}, {}
    threads = [
        threading.Thread(target=call_gemini, args=(prompt, results, errors)),
        threading.Thread(target=call_gpt4o,  args=(prompt, results, errors)),
        threading.Thread(target=call_grok,   args=(prompt, results, errors)),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    return results, errors


# ─── CONSENSUS SYNTHESIS ─────────────────────────────────────────────────────

def synthesize_consensus(feature: str, cycle: int, results: dict, errors: dict,
                          prev_results: dict = None) -> str:
    """Claude synthesizes all LLM outputs into consensus report."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    models_output = []
    for name, text in results.items():
        models_output.append(f"## {name.upper()} OUTPUT\n{text[:8000]}")

    prev_section = ""
    if prev_results:
        prev_section = "\n\n## CYCLE 1 RESULTS (for context)\n"
        for name, text in prev_results.items():
            prev_section += f"### {name.upper()} CYCLE 1\n{text[:3000]}\n\n"

    synthesis_prompt = f"""You are synthesizing a Cycle {cycle} multi-LLM code audit for Protocol Pulse feature: {feature}

Three independent AI models (Gemini 2.5 Pro, GPT-4o, Grok-3) reviewed the same code.
{prev_section}

Their Cycle {cycle} outputs:

{"".join(models_output)}

Errors/failures: {json.dumps(errors) if errors else "None"}

Produce the CONSENSUS REPORT with these exact sections:

# CONSENSUS REPORT — {feature.upper()} — CYCLE {cycle}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Models: {", ".join(results.keys())} {"(+" + str(len(errors)) + " failed)" if errors else ""}

## SCORES
| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
[extract scores from each model's output and populate the table]

## UNANIMOUS FINDINGS (all {len(results)} models agree — implement unconditionally)
[List every issue flagged by ALL models. These are the highest-confidence fixes.]
For each: what it is, which file/line, what to change.

## MAJORITY FINDINGS (2 of {len(results)} models agree)
[Issues flagged by 2+ models. Implement unless there's a compelling reason not to.]

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)
[Novel observations from a single model. Some will be the most valuable findings.]
Your assessment of each: implement / skip / investigate further.

## CONFLICTS (models disagree — your tiebreaker)
[Where models gave contradictory recommendations. State who is right and why.]

## VALIDATED STRENGTHS (all models agree this is already excellent)
[These areas are strong. Do NOT change them in the second pass.]

## LAW COMPLIANCE CONSENSUS
Which laws are violated? Which are fully compliant? Final determination.

## SECURITY CONSENSUS
Any security issues all/most models flagged? Priority order.

## WORLD-CLASS GAP CONSENSUS
What does the combined intelligence of 3 models say is missing from a
truly world-class product? Only include items 2+ models mentioned.

## FINAL ACTION PLAN (sorted by consensus priority)
P0 CRITICAL | [change] | [file:line] | [models: all/2/unique] | [why]
P1 HIGH     | [change] | [file:line] | [models] | [why]
P2 MEDIUM   | [change] | [file:line] | [models] | [why]

## CYCLE {cycle} VERDICT
{'Is the code ready for a second build pass, or does it need fundamental rework?' if cycle == 1 else 'After two full cycles of 3-model review: is this code production-ready? What is the absolute final blocker if any?'}

## SECOND PASS PROMPT (ready to fire into Claude Code)
```
Read ~/protocol_pulse/docs/gospels/{FEATURE_MAP.get(feature, ('GOSPEL.md',''))[0]}.
Read ~/protocol_pulse/docs/audits/{feature}_CONSENSUS_C{cycle}.md.

This is the {'SECOND' if cycle == 1 else 'FINAL'} PASS for {feature}.
The first build was reviewed by {len(results)} independent AI models across {cycle} cycle(s).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:
[copy the action plan from above]

VALIDATED (do NOT touch — all models confirmed excellent):
[copy validated strengths]

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat({feature}): post-audit pass — consensus improvements"
git push origin {FEATURE_MAP.get(feature, ('','feature/'+feature))[1]}
```
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    return msg.content[0].text


# ─── CYCLE 2 PACKAGE BUILDER ─────────────────────────────────────────────────

def build_cycle2_prompt(feature: str, original_package: str,
                         c1_results: dict, c1_consensus: str) -> str:
    """Build the Cycle 2 prompt where each LLM sees what the others said."""
    others_text = "\n\n".join(
        f"## {name.upper()} — CYCLE 1 OUTPUT\n{text[:5000]}"
        for name, text in c1_results.items()
    )
    return f"""# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: {feature}
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
{others_text}

## CLAUDE'S CYCLE 1 CONSENSUS
{c1_consensus[:3000]}

---

## ORIGINAL CODE (same code as Cycle 1)
{original_package[original_package.find("## THE CODE"):original_package.find("## YOUR REVIEW TASK")]}

---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
"""


# ─── MAIN RUNNER ─────────────────────────────────────────────────────────────

def run_audit(feature: str, start_cycle: int = 1, c1_results_path: str = None):
    print(f"\n{'='*60}")
    print(f"PROTOCOL PULSE CROSS-LLM AUDIT — {feature.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Verify API keys
    missing_keys = [k for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"]
                    if not os.environ.get(k)]
    if missing_keys:
        print(f"❌ MISSING API KEYS: {missing_keys}")
        print("Add them to ~/protocol_pulse/.env and re-run.")
        sys.exit(1)
    print(f"✅ All API keys present\n")

    audit_dir = AUDITS / feature
    audit_dir.mkdir(parents=True, exist_ok=True)

    # ── CYCLE 1 ───────────────────────────────────────────────────────────────
    if start_cycle == 1:
        print("── CYCLE 1: BUILDING AUDIT PACKAGE ────────────────────────────")
        package = build_audit_package(feature)
        (audit_dir / "AUDIT_PACKAGE.md").write_text(package)
        print(f"  Package written: {len(package):,} chars\n")

        print("── CYCLE 1: FIRING 3 LLMs IN PARALLEL ─────────────────────────")
        c1_results, c1_errors = fire_all_llms(package)
        (audit_dir / "C1_GEMINI.md").write_text(c1_results.get("gemini", f"FAILED: {c1_errors.get('gemini')}"))
        (audit_dir / "C1_GPT4O.md").write_text(c1_results.get("gpt4o",  f"FAILED: {c1_errors.get('gpt4o')}"))
        (audit_dir / "C1_GROK.md").write_text(c1_results.get("grok",   f"FAILED: {c1_errors.get('grok')}"))
        print(f"\n  Cycle 1 complete: {list(c1_results.keys())} succeeded, {list(c1_errors.keys())} failed\n")

        print("── CYCLE 1: SYNTHESIZING CONSENSUS ─────────────────────────────")
        c1_consensus = synthesize_consensus(feature, 1, c1_results, c1_errors)
        (audit_dir / "C1_CONSENSUS.md").write_text(c1_consensus)
        print("  Consensus written\n")
    else:
        # Load from previous run
        print("── LOADING CYCLE 1 RESULTS ─────────────────────────────────────")
        c1_results = {
            "gemini": (audit_dir / "C1_GEMINI.md").read_text(),
            "gpt4o":  (audit_dir / "C1_GPT4O.md").read_text(),
            "grok":   (audit_dir / "C1_GROK.md").read_text(),
        }
        c1_consensus = (audit_dir / "C1_CONSENSUS.md").read_text()
        package = (audit_dir / "AUDIT_PACKAGE.md").read_text()
        print("  Loaded from previous run\n")

    # Check if we need Cycle 2 (skip for low-stakes if high score)
    run_cycle2 = feature in HIGH_STAKES
    if not run_cycle2:
        # Check if overall score > 85 across all models
        scores = []
        for text in c1_results.values():
            for line in text.split("\n"):
                if "OVERALL" in line.upper() and "/100" in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line.split("/")[0].split()[-1])))
                        scores.append(score)
                    except: pass
        avg_score = sum(scores) / len(scores) if scores else 0
        run_cycle2 = avg_score < 85
        print(f"  Average Cycle 1 score: {avg_score:.0f}/100 — {'Running Cycle 2' if run_cycle2 else 'Score high enough, skipping Cycle 2'}\n")

    if run_cycle2:
        # ── CYCLE 2 ───────────────────────────────────────────────────────────
        print("── CYCLE 2: BUILDING CROSS-REVIEW PROMPT ───────────────────────")
        c2_prompt = build_cycle2_prompt(feature, package, c1_results, c1_consensus)
        (audit_dir / "C2_PROMPT.md").write_text(c2_prompt)

        print("── CYCLE 2: FIRING 3 LLMs WITH CROSS-VISIBILITY ────────────────")
        c2_results, c2_errors = fire_all_llms(c2_prompt)
        (audit_dir / "C2_GEMINI.md").write_text(c2_results.get("gemini", f"FAILED: {c2_errors.get('gemini')}"))
        (audit_dir / "C2_GPT4O.md").write_text(c2_results.get("gpt4o",  f"FAILED: {c2_errors.get('gpt4o')}"))
        (audit_dir / "C2_GROK.md").write_text(c2_results.get("grok",   f"FAILED: {c2_errors.get('grok')}"))
        print(f"\n  Cycle 2 complete: {list(c2_results.keys())} succeeded\n")

        print("── CYCLE 2: FINAL CONSENSUS + WINNER ───────────────────────────")
        final_consensus = synthesize_consensus(feature, 2, c2_results, c2_errors, c1_results)

        # Determine "winner" — the model whose Cycle 1 findings had the most
        # items validated by Cycle 2 consensus
        winner_prompt = f"""Based on this 2-cycle cross-LLM audit, determine which model (Gemini, GPT-4o, or Grok)
provided the highest-quality analysis overall.

Criteria:
1. Accuracy — did their findings prove correct in Cycle 2?
2. Depth — did they find issues others missed?
3. Actionability — were their recommendations specific and implementable?
4. Completeness — did they cover all sections thoroughly?

CYCLE 1 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c1_results.items()})}
CYCLE 2 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c2_results.items()})}
FINAL CONSENSUS: {final_consensus[:2000]}

State: WINNER: [model name] — [2 sentence justification]
Then: FINAL SECOND-PASS PRIORITY LIST — the definitive ordered list of what to implement."""

        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        winner_msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=2000,
            messages=[{"role": "user", "content": winner_prompt}]
        )
        winner_text = winner_msg.content[0].text

        final_report = final_consensus + "\n\n---\n\n# WINNER DETERMINATION\n\n" + winner_text
        (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)
    else:
        final_report = c1_consensus
        (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE — {feature.upper()}")
    print(f"{'='*60}")
    print(f"\nOutputs at: {audit_dir}/")
    print(f"  AUDIT_PACKAGE.md    — code package sent to LLMs")
    if run_cycle2:
        print(f"  C1_*.md             — Cycle 1 individual outputs")
        print(f"  C1_CONSENSUS.md     — Cycle 1 synthesis")
        print(f"  C2_*.md             — Cycle 2 individual outputs")
    print(f"  FINAL_CONSENSUS.md  — final action plan + second-pass prompt")
    print(f"\nNEXT: Fire the second-pass Claude Code session using the prompt")
    print(f"      in FINAL_CONSENSUS.md → '## SECOND PASS PROMPT' section")
    print(f"\n{'='*60}\n")

    # Print the second-pass prompt for immediate use
    for line in final_report.split("\n"):
        if "SECOND PASS PROMPT" in line.upper():
            idx = final_report.find(line)
            print("READY TO FIRE — SECOND PASS PROMPT:")
            print("-"*40)
            print(final_report[idx:idx+2000])
            break

    # Auto-update AUDIT_REGISTRY.json so CI integrity gate stays green
    try:
        import json as _j, subprocess as _sp
        from datetime import datetime as _dt, timezone as _tz
        rp = BASE / "docs" / "audits" / "AUDIT_REGISTRY.json"
        existing = _j.loads(rp.read_text()) if rp.exists() else {}
        audits = [a for a in existing.get("audits", []) if a.get("feature") != feature]
        audits.append({"feature": feature, "date": _dt.now(_tz.utc).strftime("%Y-%m-%d"), "models": ["gemini", "gpt4o", "grok"]})
        sha = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
        rp.write_text(_j.dumps({"last_audit": _dt.now(_tz.utc).isoformat(), "feature": feature, "commit": sha, "audits": audits[-20:]}, indent=2))
        print(f"[registry] AUDIT_REGISTRY.json updated for {feature}")
    except Exception as _e:
        print(f"[registry] Warning: could not update registry: {_e}")
    return final_report


# --- ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load .env
    env_path = Path.home() / "protocol_pulse/.env"
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    parser = argparse.ArgumentParser(description="Cross-LLM code audit engine")
    parser.add_argument("--feature", required=True,
                        help=f"Feature to audit. Options: {list(FEATURE_MAP.keys()) + ['all']}")
    parser.add_argument("--cycle", type=int, default=1,
                        help="Start from cycle 1 (default) or 2 (resume)")
    parser.add_argument("--cycle1-results", help="Path to existing cycle 1 results dir")
    args = parser.parse_args()

    if args.feature == "all":
        for feat in FEATURE_MAP:
            if feat != "video-audio-fix":  # skip until PBX provides notes
                run_audit(feat, start_cycle=1)
                time.sleep(10)  # avoid API rate limits between features
    elif args.feature in FEATURE_MAP:
        run_audit(args.feature, start_cycle=args.cycle)
    else:
        print(f"Unknown feature: {args.feature}")
        print(f"Options: {list(FEATURE_MAP.keys())}")
        sys.exit(1)
