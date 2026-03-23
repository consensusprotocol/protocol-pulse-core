Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: SOCIAL MEDIA SYSTEM FULL AUDIT + FIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Protocol Pulse posted 5 near-identical tweets in 3 hours
all hitting "Extreme Fear" angle. Spam. Audience damage.
Additionally: zero auto-replies, zero engagement with mentions.

ROOT CAUSE SUSPECTED: 18 files can post tweets. Dedup only
applies to tweet_machine.py. Other posting paths bypass it entirely.

FILES TO AUDIT (all of these can post tweets):
services/tweet_machine.py
services/x_automation_service.py
services/x_daily_top_article.py
services/x_engagement_engine.py
services/scheduler.py
services/distribution_manager.py
services/comment_radar.py
services/thread_engine.py
services/bookmark_bait.py
services/rtsa_service.py
services/x_service.py
services/video_engine/pulse_distributor.py
services/video_engine/distribution_engine.py
services/video_engine/intel_feed_consumer.py
services/video_engine/pulse_alert.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY: CROSS-LLM PRODUCT AUDIT FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["social-media-audit"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["social-media-audit"] = [
      "services/tweet_machine.py",
      "services/x_automation_service.py",
      "services/x_engagement_engine.py",
      "services/scheduler.py",
      "services/x_service.py",
  ]

python3 utils/cross_llm_audit.py --feature social-media-audit
[save C1] 
python3 utils/cross_llm_audit.py --feature social-media-audit --cycle 2 --cycle1-results [C1]

Each model answers:
1. Which of the 18 posting files are actually firing and how often?
2. Where is the dedup gate and which files bypass it?
3. Why are 5 near-identical tweets posting in 3 hours?
4. What is the correct architecture for a 2-tweet/day maximum globally?
5. Why are auto-replies and engagement not happening?
6. What is the right engagement strategy for a Bitcoin media brand?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — AUDIT ALL 18 POSTING FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read every file that can post tweets. For each:
  - How is it triggered? (cron, Flask route, event, manual?)
  - Does it check the dedup gate before posting?
  - Does it respect the 2/day global limit?
  - Is it currently active or dormant?

Map every active posting path. Build a complete picture.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — IMPLEMENT GLOBAL RATE GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create a single global posting gate in services/x_service.py:

def can_post_tweet(text: str) -> tuple[bool, str]:
    """
    Global gate. Every posting path MUST call this before posting.
    Returns (allowed, reason).
    
    Rules:
    1. Max 3 posts per 24 hours across ALL posting services
    2. Minimum 4 hours between any two posts
    3. 40% similarity threshold against last 48h posts
    4. No hashtags (strip them if present)
    5. Logs every check (allowed or blocked) with reason
    """

Every one of the 18 files must call can_post_tweet() and respect
the result. No exceptions. No bypasses.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — POSTING SCHEDULE (sacred, do not exceed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX 3 posts per day total across all services:
  9:00 AM ET  — Morning signal tweet (tweet_machine.py, morning brief)
  2:00 PM ET  — Top article tweet (x_daily_top_article.py, link post)
  7:00 PM ET  — Evening signal tweet (tweet_machine.py, noon brief)

All other posting files: disable scheduled posting. They may only
post if triggered by a genuinely high-signal breaking event
(Pulse Score crosses threshold, whale alert, breaking news).
Even then: must pass the global gate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — AUTO-ENGAGEMENT (build this)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check x_engagement_engine.py — what does it do currently?
Check comment_radar.py — is it monitoring mentions?

Build/fix auto-engagement to run 2x daily (noon + 6pm ET):
  1. Check @ProtocolPulseHQ mentions in last 12 hours
  2. For each mention from a real account (not bot):
     - Generate a brief, on-brand reply (1-2 sentences max)
     - Bitcoin/sovereignty lens, never sycophantic
     - Must add value — disagree if appropriate
     - Post reply via x_service.py (goes through global gate)
  3. Like 3-5 high-signal Bitcoin tweets from TIER1 handles per day
  4. Retweet max 1 post per day from TIER1 handles — only if genuinely
     exceptional signal, not just because it's from a known account

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ANGLE DIVERSITY ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The tweet machine must never post the same narrative twice in 48h.
Enforce this in the prompt by tracking used angles in the DB:

Categories to rotate through (never repeat same category same day):
  - Macro/monetary policy signal
  - On-chain metric insight  
  - Institutional flow (ETF, treasury)
  - Geopolitical Bitcoin signal
  - Historical pattern/precedent
  - Network fundamentals (hashrate, difficulty)
  - Sovereignty/freedom framing
  - Contrarian take on mainstream narrative

Store last used category per day. Force different category each post.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh — 0 FAILs required
git add services/tweet_machine.py services/x_service.py
git add services/x_engagement_engine.py services/comment_radar.py
git add services/x_automation_service.py services/scheduler.py
git commit -m "fix(social): global posting gate, 3/day max, 4h minimum gap, auto-engagement, angle diversity — eliminates spam"
git push

DO NOT touch: video pipeline files, assembler.py, tts_engine.py
