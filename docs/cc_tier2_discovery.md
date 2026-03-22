Load ~/protocol_pulse/PIPELINE_LAWS.md first. Build the following in one pass. One new file only — do not touch any existing files.

CONTEXT: channel_scanner.py scans a static channels.yaml list (Bitcoin-native channels). We need a Tier 2 Discovery Engine that uses the YouTube Data API v3 to find high-credibility NON-Bitcoin channels that recently covered Bitcoin. A Bret Weinstein or Lex Fridman covering Bitcoin is more signal-rich than another Bitcoin-native channel. YOUTUBE_API_KEY is already in .env (confirmed present).

BUILD: ~/protocol_pulse/video_pipeline_v3/tier2_discovery.py

The module must export one function: discover_crossover_videos() -> list[dict]

ARCHITECTURE:

1. Load YOUTUBE_API_KEY from .env. If missing return [] with log warning.

2. Run these YouTube Data API v3 searches (youtube/v3/search endpoint):
   queries = ["bitcoin", "bitcoin federal reserve", "bitcoin sound money", "bitcoin inflation hedge", "bitcoin financial sovereignty"]
   For each query: type=video, order=relevance, publishedAfter=48h ago, maxResults=15
   Total API cost: 5 x 100 = 500 units/day (well within 10k free quota)

3. For each video returned, fetch channel stats (youtube/v3/channels):
   fields: subscriberCount, videoCount, publishedAt (channel age)
   Cache channel stats by channel_id to avoid repeat calls (same channel appears across queries)

4. Score each video:
   base_score = log10(subscriber_count) * 10   (100k=50pts, 1M=60pts, 10M=70pts)
   recency_bonus = max(0, 48 - hours_since_published) * 0.5
   crossover_bonus = +25 if channel NOT already in channels.yaml
   frequency_penalty = -20 if channel uploads >2 videos/day average (filters spam)
   DISQUALIFY if: subscriber_count < 50000 OR channel age < 1 year

5. For videos scoring > 40pts: fetch transcript via yt-dlp (same method as channel_scanner.py). Then run a fast Claude API call to confirm Bitcoin is the PRIMARY topic:
   model = claude-haiku-3-5 (fast, cheap)
   prompt = "Is Bitcoin or sound money the PRIMARY subject of this video transcript? Answer only YES or NO."
   Only keep YES responses. Skip if transcript < 500 words.

6. Return list of video dicts in the EXACT same schema as scan_all_channels() returns:
   {
     "video_id": str,
     "title": str,
     "channel": str,
     "channel_id": str,
     "duration": float,
     "upload_date": str,
     "url": str,
     "transcript_text": str,
     "timestamped_text": str,
     "source": "tier2_discovery",
     "credibility_score": float,
     "subscriber_count": int,
   }

7. INTEGRATE into channel_scanner.py — add these lines at the BOTTOM of scan_all_channels() before the return statement:
   try:
       from tier2_discovery import discover_crossover_videos
       crossover = discover_crossover_videos()
       if crossover:
           videos.extend(crossover)
           logger.info(f"Tier 2 Discovery: {len(crossover)} crossover videos added")
   except Exception as e:
       logger.warning(f"Tier 2 Discovery failed (non-fatal): {e}")

8. INTEGRATE into clip_selector.py — in SELECTION_PROMPT add after existing tier description:
   "TIER 4 - CROSSOVER DISCOVERY (1.6x multiplier): Videos from non-Bitcoin channels that specifically covered Bitcoin. A philosopher, scientist, or political commentator covering Bitcoin outscores another Bitcoin-native channel on the same story. Field: source == tier2_discovery. Prioritize these."

9. Cache results to video_pipeline_v3/data/tier2_cache.json with 6h TTL keyed by video_id.

10. Handle missing YOUTUBE_API_KEY gracefully — return [] with log, never crash.

VALIDATION after building:
  cd ~/protocol_pulse/video_pipeline_v3
  python3 -c "
  from tier2_discovery import discover_crossover_videos
  results = discover_crossover_videos()
  print(f'Found {len(results)} crossover videos')
  for v in results[:3]:
      print(v['channel'], '|', v['title'][:60], '| score:', v['credibility_score'])
  "

COMMIT:
  git add video_pipeline_v3/tier2_discovery.py video_pipeline_v3/channel_scanner.py video_pipeline_v3/clip_selector.py
  git commit -m "feat(scanner): Tier 2 Discovery Engine - YouTube API crossover detection, 1.6x multiplier"
  git push

RULES: Do not touch assembler.py, tts_engine.py, gemini_grade.py, daily_run.py, or overnight_render_loop.py. tier2_discovery.py + channel_scanner.py + clip_selector.py only.
