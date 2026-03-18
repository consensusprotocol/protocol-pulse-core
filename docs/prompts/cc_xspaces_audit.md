Read https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/docs/handoff/CURRENT_STATE.md for full context.

MISSION: Write the 3 remaining x_spaces_pipeline files, then run a REAL full 3-LLM code audit (Gemini + GPT-4o + Grok) against ALL 6 actual files. This is a design-phase code review -- the files don't exist in the repo yet, they are proposed code that must be audited BEFORE being committed.

STEP 1 -- Write these 3 files to /tmp/x_spaces_review/ (monitor.py and recorder.py and transcriber.py already exist there from the previous session):

curator.py:
- Claude claude-sonnet-4-20250514 reads transcripts, extracts top 3 moments
- MAX_DAILY_CALLS=20 hard cap (stored in /tmp/pp_curator_daily.json) -- cost control
- Input: RAW_DIR/*.json files that have 'text' key (transcribed, not just sidecars)
- Output: data/spaces/moments/{stem}_moments.json
- JSON schema: {"moments":[{"rank":1,"start_sec":0.0,"end_sec":0.0,"quote":"exact words","speaker":"unknown","signal_type":"price_thesis","quality_score":0}]}
- Skips files already having moment file, skips if >6hrs old, skips if <200 chars
- Gets handle from data['handle'] not from filename parsing

clipper.py:
- Cuts raw .m4a at curator timestamps using -c:a aac (NOT -c copy -- copy is keyframe-accurate only, aac gives sample-accurate cuts)
- PAD=2.0s each side, max 90s per clip
- Output: data/spaces/clips/{date}_{handle}_{rank}.m4a + .json sidecar
- date extracted as '_'.join(stem.split('_')[:2]) -- safe for pierre_rochard underscores

x_spaces_segment.py:
- assembler_v2 segment (lives in video_pipeline_v3/assembler_v2/segments/)
- All 10 assembler_v2 Laws: render() NEVER raises, CRF-only (-crf 17 no -b:v), filler on failure
- Reads CLIP_DIR/*.json files fresher than 6hrs, top 3 by quality_score
- Visual: ffmpeg showwaves on branded black bg + drawtext @handle + quote
- showwaves filter: [0:a]showwaves=s={VIDEO_W}x{int(VIDEO_H*0.4)}:mode=cline:colors={COLOR_ACCENT}[wave]
- Stitches clips with ffmpeg concat
- Graceful filler if no clips available (never blocks episode render)

STEP 2 -- Syntax check all 6 files with ast.parse(). Fix any errors.

STEP 3 -- Build a comprehensive audit package at /tmp/x_spaces_review/AUDIT_PACKAGE.md containing:
- All 6 files in full (cat each file into the package)
- The existing code context: cat /home/ultron/protocol_pulse/x_spaces_scraper/scraper.py (first 3000 chars), spaces_state.py (first 2000), whisper_worker.py (first 2000)
- The 12 critical audit focus areas from the previous session (zombie prevention, TOCTOU race, SQLite gap, yt-dlp detection viability, auth expiry, showwaves filtergraph, Claude API cost, cron race, GPU contention, filename parsing, copy mode accuracy, API reality)
- Unconstrained audit instructions: find ALL issues, no top-3 limit, CRITICAL/MAJOR/MINOR/NITPICK

STEP 4 -- Fire all 3 LLMs in PARALLEL against the actual code package. Use the API keys from /home/ultron/protocol_pulse/.env:

For Gemini (use google.genai or direct REST):
  - POST to https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}
  - Save response to /tmp/x_spaces_review/CODE_AUDIT_GEMINI.md

For GPT-4o (openai library):
  - client = OpenAI(api_key=OPENAI_API_KEY)
  - model="gpt-4o", max_tokens=8000
  - Save response to /tmp/x_spaces_review/CODE_AUDIT_GPT4O.md

For Grok (openai library with xai base_url):
  - client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
  - model="grok-3-latest", max_completion_tokens=8000
  - Save response to /tmp/x_spaces_review/CODE_AUDIT_GROK.md

Run all 3 in parallel threads. Wait for all to complete. Log any failures with full error.

STEP 5 -- Write a synthesis doc /tmp/x_spaces_review/SYNTHESIS.md that:
- Lists ALL findings from all 3 models by severity (CRITICAL first)
- Flags consensus findings (2+ models agreed)
- Flags unique findings (only 1 model caught it)
- Gives overall design verdict: PROCEED / PROCEED WITH CHANGES / REDESIGN
- Lists minimum required changes before code can be committed

STEP 6 -- Copy the synthesis doc to the repo:
cp /tmp/x_spaces_review/SYNTHESIS.md /home/ultron/protocol_pulse/docs/audits/x-spaces-pipeline/MULTI_LLM_CODE_AUDIT.md
cd /home/ultron/protocol_pulse && git add docs/audits/x-spaces-pipeline/ && git commit -m "audit: x-spaces-pipeline 3-LLM code review -- Gemini+GPT4o+Grok on actual code" && git push

Report back the full SYNTHESIS.md content when done.
