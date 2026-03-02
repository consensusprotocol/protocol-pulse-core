# ORACLE BRIEFING CONTENT ENGINE — EXECUTE NOW

CRITICAL: Do NOT use planning mode or todolists. Do NOT show a plan and ask to proceed. Start writing code IMMEDIATELY.

## CONTEXT

You already analyzed this and planned it. The Oracle Briefing is a 60-90 second daily intelligence brief from the Proto_P avatar. Short, punchy, authoritative.

Format: HOOK → THE NUMBER (key metric) → THE SIGNAL (top development) → THE TAKE (editorial opinion) → SIGN-OFF

## CREATE THESE FILES in ~/protocol_pulse/oracle_briefing/

### 1. briefing_writer.py — Script Generator
- Uses Claude API (claude-sonnet-4-6) to write Oracle Briefing script
- Fetches live data: BTC price (CoinGecko), mempool (mempool.space API), FNG
- Fetches latest PP articles from local DB or /api/articles/latest
- Prompt: "You are the Protocol Pulse Oracle" — authoritative, punchy, no filler
- Output: JSON with segments (THE NUMBER, THE SIGNAL, THE TAKE), overlay types, thumbnail data
- Each segment: 45-50 words max
- Test: python3 briefing_writer.py --test prints script JSON to stdout

### 2. overlay_engine.py — Data Visualization
- Generate matplotlib overlays (dark theme, 1920x1080 PNG):
  - price_chart: 7-day BTC from CoinGecko, green/red line
  - mempool_viz: fee histogram from mempool.space
  - hashrate_chart: difficulty epochs bar chart
  - article_screenshot: playwright screenshot of PP article URL
- matplotlib.use('Agg') — no GUI
- Each function returns path to generated PNG

### 3. briefing_producer.py — Orchestrator
Pipeline:
1. Fetch live data (BTC price, mempool, hashrate, FNG, articles)
2. Generate script via briefing_writer
3. TTS via ElevenLabs Jessica (reuse video_pipeline_v3/tts_engine.py)
4. Avatar generation via localhost:8200 /generate endpoint
5. Overlay compositing: avatar left (40%), data right (60%) — FFmpeg
6. Prepend intro / append outro (generate simple ones with FFmpeg if no assets)
7. Thumbnail: Pillow 1280x720, avatar face + headline + BTC price
8. Vertical short: center-crop for 1080x1920
9. Output to output/oracle_YYYYMMDD/

--test flag: use sample data, shorter briefing, skip avatar (use static image)
--no-avatar flag: skip avatar, just produce audio + overlays

### 4. relay.py — Helper
Copy pattern from video_pipeline_v3/relay.py for API key access

## DEPENDENCIES
```bash
pip install matplotlib Pillow requests --break-system-packages 2>/dev/null
# playwright should already be installed from xspaces task
which playwright || (pip install playwright --break-system-packages && playwright install chromium)
```

## TEST
```bash
cd ~/protocol_pulse/oracle_briefing && python3 briefing_producer.py --test
```

Expected output:
- oracle_briefing_YYYYMMDD.mp4 (or .mp3 if --no-avatar)
- oracle_short.mp4
- thumbnail.jpg
- script.json
- overlays/*.png

## CRON SETUP
```bash
# Daily at 7 AM EST
(crontab -l 2>/dev/null; echo "0 7 * * * cd /home/ultron/protocol_pulse/oracle_briefing && python3 briefing_producer.py >> ~/protocol_pulse/logs/oracle_briefing.log 2>&1") | crontab -
```

## GIT
```bash
git add -A && git commit -m "feat(oracle): daily briefing pipeline — script gen, overlays, avatar compositing" && git push origin main
```

START CODING NOW.
