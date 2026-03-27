Read ~/protocol_pulse/docs/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/audits/stage-broadcast/ for prior context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAGE AVATAR — SEPARATE CROSS-LLM AUDIT + BUILD
Stage serves a different purpose than Oracle. Treat as independent system.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PURPOSE DISTINCTION (critical context):
- Oracle: conversational, reactive, responds to user questions, 1:1 dialogue
- Stage: broadcast, monologue-driven, PBX avatar delivers briefings to audience,
  designed for many viewers simultaneously, eventually live-streamable

CONFIRMED BUGS:
BUG 1 — STAGE NEVER RENDERS ("warming up" forever):
  All /generate calls return 503 (GPU semaphore locked by pipeline).
  After GPU isolation fix in oracle session, this may self-resolve.
  But Stage may have additional issues beyond GPU — audit fully.

BUG 2 — MOBILE TICKER TOO FAST:
  The scrolling info bar in Stage header animates at full desktop speed
  on mobile, text unreadable. CSS animation-duration not responsive.

STEP 1 — AUDIT THE STAGE SYSTEM

Read these files fully:
  core/blueprints/oracle.py (Stage routes if Stage shares this blueprint)
  core/templates/ — find Stage template (check for stage.html, stage_*.html)
  oracle/avatar_server.py lines 1300-1500 (generate_idle_loop, Stage-specific code)

Map every Stage route end-to-end:
  grep -rn "stage\|Stage\|STAGE" core/blueprints/ core/templates/ oracle/ | grep -v ".pyc" | head -40

Identify: does Stage have its own blueprint or share oracle.py?
What template serves the Stage page? What JS handles the "warming up" state?
What endpoint does Stage call to get video? Why does it show "warming up" vs an error?

Register in cross_llm_audit.py FEATURE_MAP:
  "stage-avatar-fix": ("PIPELINE_LAWS.md", "main")

EXPLICIT_FILES for stage-avatar-fix:
  [all Stage-relevant files found above, max 4 files]

Fire cycle 1 — each LLM answers independently:

Q1 — STAGE ARCHITECTURE: What is the complete Stage system?
How does it differ architecturally from Oracle? Where does the "warming up"
state come from — is it a frontend timeout, a 503 handler, or something else?

Q2 — STAGE GPU ISOLATION: After Oracle gets cuda:2, what CUDA device
should Stage use? Should Stage share with Oracle or get cuda:3?
Map all GPU users: pipeline (which device?), oracle (cuda:1→2), stage (?).
Ultron has 4x RTX 4090 — assign each service its own GPU.

Q3 — MOBILE TICKER FIX: Find the CSS animation for the scrolling header bar.
What is the current animation-duration? What should it be on mobile?
Write the exact CSS media query fix. Must be readable at normal speed on mobile.

Q4 — STAGE CONTENT PIPELINE: Where does Stage get its monologue content?
Is it pulling from morning_intelligence_brief.json? From a live API?
Is the content pipeline working even if GPU render is broken?
What would Stage show if GPU was free right now?

python3 utils/cross_llm_audit.py --feature stage-avatar-fix
Save: docs/audits/stage_avatar_fix_c1.json

STEP 2 — CYCLE 2
python3 utils/cross_llm_audit.py --feature stage-avatar-fix --cycle 2 --cycle1-results docs/audits/stage_avatar_fix_c1.json
Save: docs/audits/stage_avatar_fix_c2.json

STEP 3 — IMPLEMENT CONSENSUS FIXES

FIX 1 — GPU DEVICE FOR STAGE:
Assign Stage its own CUDA device based on audit consensus.
Ensure pipeline, Oracle, Stage are on separate devices.
Document GPU map in QWEN_CONTEXT_BIBLE.md:
  cuda:0 — [pipeline or free]
  cuda:1 — [pipeline daily_producer]
  cuda:2 — Oracle avatar_server
  cuda:3 — Stage (or shared with Oracle if Stage is low-traffic)

FIX 2 — STAGE RENDER UNBLOCK:
Fix whatever is causing "warming up" forever beyond GPU issue.
If frontend JS has a timeout that shows "warming up" on any non-200 response,
fix the UX to show a proper error + retry button instead.
The warming up spinner must never spin more than 30s without feedback.

FIX 3 — MOBILE TICKER:
In the Stage template CSS, add:
  @media (max-width: 768px) {
    .ticker-animation { animation-duration: [appropriate value]s; }
  }
Test: animation should complete one full cycle in 15-20s on mobile.

FIX 4 — STAGE CONTENT VERIFY:
Confirm the briefing content pipeline is feeding Stage correctly.
The monologue must have real content before GPU matters.

STEP 4 — VERIFY
curl -s http://localhost:5000/stage (or Stage route) — must return 200
With GPU free: POST to Stage generate endpoint — must return video, not 503
Mobile ticker: verify CSS fix in template

STEP 5 — BIBLE + COMMIT
Document Stage GPU assignment and all fixes in QWEN_CONTEXT_BIBLE.md
bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add -A
git commit -m "fix(stage): GPU isolation on dedicated device, mobile ticker speed, warming-up UX feedback"
git push

NOTE: The pre-rendering continuous monologue loop (live stream feed concept)
is a PHASE 2 feature — do not build in this session. The generate_idle_loop()
function at line 1308 of avatar_server.py is the foundation for that.
Park it. Fix the basics first.
