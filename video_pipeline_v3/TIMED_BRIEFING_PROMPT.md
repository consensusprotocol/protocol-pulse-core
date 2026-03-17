# TIMED BRIEFING SYSTEM — Oracle Stage

## What to build
After every successful Grade A video render, the Oracle Stage page should automatically update with a condensed cliff-notes briefing — the Oracle avatar reporting the same intel as the full Pulse Check episode, but in 90 seconds instead of 10 minutes.

## Architecture

### 1. `generate_stage_brief.py` (new file in `video_pipeline_v3/`)
Reads the latest render's `script.json` + `selections.json`, generates a condensed stage brief, renders it as a Wav2Lip video.

```
Input:  output/{date}/script.json + selections.json
Output: data/stage_briefs/brief_{YYYYMMDD_HHMM}.mp4 + brief_{YYYYMMDD_HHMM}.json
```

Steps:
1. Read `script.json` — get `episode_title`, `btc_price`, and all dialogue lines
2. Read `selections.json` — get list of clips with channel names and titles
3. Call Claude Haiku API to condense into a 90-second monologue:
   - System: "You are Oracle, a Bitcoin intelligence reporter. Write a punchy 90-second spoken brief (max 200 words). Cover: the top story, 2-3 key signals, one strong closing line. PBX voice: direct, confident, no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
   - User: Full dialogue text + clip list pasted in
4. Call ElevenLabs (`/oracle/voice` endpoint on avatar server — POST text, get audio/mpeg back)
5. Render through Wav2Lip via avatar server `/generate` endpoint (POST with audio)
6. Save MP4 to `data/stage_briefs/`
7. Write metadata JSON: `{title, generated_at, duration, mp4_path, episode_date, script_summary}`
8. Update `data/stage_briefs/latest.json` symlink/file pointing to newest brief

### 2. Hook into `daily_producer.py`
After STEP 13 (QUALITY GATE) passes with score >= 85, add STEP 14:
```python
# STEP 14: Generate stage brief
try:
    from generate_stage_brief import generate_brief
    brief_path = generate_brief(output_dir)
    if brief_path:
        logger.info(f"Stage brief generated: {brief_path}")
except Exception as e:
    logger.warning(f"Stage brief generation failed (non-fatal): {e}")
```
**Non-fatal** — never block a good render over a brief failure.

### 3. Flask API endpoints (add to `routes.py`)

**`GET /api/stage/next_briefing`**
Returns:
```json
{
  "last_brief": {
    "title": "Squeezed, Shocked, and Saying It Loud",
    "generated_at": "2026-03-17T15:30:00Z",
    "mp4_url": "/data/stage_briefs/brief_20260317_1530.mp4",
    "duration": 87.3
  },
  "next_estimated_at": "2026-03-18T15:30:00Z",
  "countdown_seconds": 82800,
  "has_brief": true
}
```
Logic: reads `data/stage_briefs/latest.json`. Next brief = last_brief.generated_at + 24h.

**`GET /data/stage_briefs/<filename>`** — static file serving for the MP4s (or add Flask route).

### 4. Stage page UI additions (in `templates/stage.html`)

Add a countdown panel below the controls:
```html
<div id="briefingCountdown" class="stage-brief-countdown">
  <div class="stage-brief-countdown__label">NEXT BRIEFING</div>
  <div class="stage-brief-countdown__timer" id="countdownTimer">—</div>
  <div class="stage-brief-countdown__sub" id="countdownSub">Checking schedule…</div>
</div>
```

CSS (add to existing stage styles):
- Monospace font, obsidian surface, gold timer text
- Pulsing dot when brief is "ready now"

JS countdown logic:
```javascript
function loadBriefingSchedule() {
  fetch('/api/stage/next_briefing')
    .then(r => r.json())
    .then(d => {
      if (!d.has_brief) { /* show "First brief coming soon" */ return; }
      startCountdown(d.countdown_seconds, d.last_brief);
      // If countdown <= 0, show "New brief available" + auto-play button
    });
}

function startCountdown(seconds, lastBrief) {
  // Update every second
  // When hits 0: show "NEW BRIEF AVAILABLE" + flash red dot + enable play button
}
```

When countdown hits 0 or brief is new:
- Flash the "NEW BRIEF AVAILABLE" badge in red
- Show a "▶ Play Brief" button that fetches and plays the new MP4 via playVid()
- Auto-play if user has interacted with page (has audio gesture)

### 5. Static file serving
Add to `routes.py`:
```python
@app.route('/data/stage_briefs/<path:filename>')
def serve_stage_brief(filename):
    from flask import send_from_directory
    brief_dir = os.path.join(os.path.dirname(__file__), 'data', 'stage_briefs')
    return send_from_directory(brief_dir, filename)
```

## Data directory
Create: `video_pipeline_v3/data/stage_briefs/` with `.gitkeep`
The MP4s and JSONs live there. `latest.json` always points to newest brief.

## Testing
1. Run `python3 generate_stage_brief.py --test` — uses the most recent render output
2. Verify MP4 is generated (should be 60-100 seconds, clean audio, proper Wav2Lip)
3. Hit `/api/stage/next_briefing` — verify JSON response is correct
4. Load `/stage` — verify countdown appears and counts down
5. Verify the brief auto-plays when countdown hits 0

## Critical rules
- `generate_stage_brief.py` must be completely non-fatal — wrap everything in try/except
- Never call the ElevenLabs API directly — use avatar server `/oracle/voice` endpoint
- Never render through GPU directly — use avatar server `/generate` endpoint  
- Brief mp4 must be < 150MB (90 seconds at normal bitrate = ~25MB, plenty of room)
- PIPELINE_LAWS.md applies — read it first
- After all code: `git add -A && git commit -m "feat: timed briefing system — stage brief auto-generated post Grade A render, countdown UI" && git push origin main`
