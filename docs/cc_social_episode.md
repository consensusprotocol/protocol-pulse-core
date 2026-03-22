Load ~/protocol_pulse/PIPELINE_LAWS.md first. Wire fresh social intelligence into the Pulse Check episode pipeline. Three surgical additions only.

CONTEXT:
- Nitter scraper is LIVE: ~/protocol_pulse/services/nitter_scraper.py
- raw_tweets.json NOW HAS: 2,372 tweets, 217 unique handles, fresh as of today Mar 20 2026
- narrative_context.json: ~/protocol_pulse/video_pipeline_v3/data/intelligence/narrative_context.json
- clip_scorer.py: ~/protocol_pulse/video_pipeline_v3/clip_scorer.py  
- script_writer.py: ~/protocol_pulse/video_pipeline_v3/script_writer.py
- daily_run.py: ~/protocol_pulse/video_pipeline_v3/daily_run.py
- TWEET LAW already in script_writer.py (enforces real handles, no fabrication)
- social_fetcher.py already reads raw_tweets.json correctly
- NARRATIVE_INJECTION already in script_writer.py (dominant_narrative, clip_selection_priority)

ADDITION 1 - DISCOURSE MULTIPLIER IN CLIP SCORING:
Read clip_scorer.py fully first. Find where clips are scored.
Add discourse multiplier:
  - Load narrative_context.json at scorer init
  - Get clip_selection_priority list (e.g. ["price", "regulation", "lightning"])
  - For each clip being scored:
    * If clip transcript contains ANY priority keyword: multiply final score by 1.8
    * If clip channel matches trending topic channel type: multiply by 1.4
    * Only one multiplier per clip (take highest)
    * Log: "[ClipScorer] Discourse boost: {keyword} matched in {clip_title} -> score*1.8"
  - If narrative_context.json missing or empty: skip silently, no crash

ADDITION 2 - "WHAT BITCOIN IS SAYING" SEGMENT UPGRADE:
Read script_writer.py social segment generation fully (search for "social_posts", "social_segment").
Currently: passive card display with narration reading handles and text.
Upgrade narration style ONLY - do not change the card visual system or assembler.

In the script_writer prompt where it generates social segment narration, change from:
  "Narrate each tweet simply"
To this narration style instruction:
  "PBX reacts to each post as LIVE intelligence he is reporting from the field.
   Format for each post:
   - State handle + engagement: 'Saylor just posted to 65,000 likes...'
   - Quote or paraphrase the post in 1 sentence
   - Add PBX analysis: 'Here is what that signals in today's market...' (1-2 sentences)
   - Feel: PBX has been on Twitter all morning and is reporting back live
   - Max 3 posts, 20-25 seconds each, total segment ~75 seconds
   - Never say 'posted on Twitter/X' - just say 'posted' or 'said'
   - TWEET LAW still applies: only reference handles actually in social_posts list"

ADDITION 3 - MORNING BRIEF WIRING INTO DAILY_RUN:
In daily_run.py, find Step 0 (narrative intelligence section, around line 69).
After the NarrativeIntelligenceEngine block, add morning brief loading:

  BRIEF_PATH = os.path.expanduser("~/protocol_pulse/data/intelligence/morning_intelligence_brief.json")
  morning_brief = {}
  if os.path.exists(BRIEF_PATH):
      try:
          with open(BRIEF_PATH) as f:
              morning_brief = json.load(f)
          brief_age_h = (time.time() - os.path.getmtime(BRIEF_PATH)) / 3600
          if brief_age_h < 18:  # use if less than 18h old
              print(f"  Morning brief loaded ({brief_age_h:.1f}h old): {morning_brief.get('dominant_narratives', [])[:2]}")
          else:
              morning_brief = {}
              print("  Morning brief too old (>18h), skipping")
      except Exception as e:
          print(f"  Morning brief unavailable: {e}")

Then pass morning_brief into the script generation call as an additional context parameter.
In script_writer.py generate_from_clips(), add morning_brief as optional param (default=None).
If present, append to the narrative injection:
  "MORNING INTELLIGENCE BRIEF: {morning_brief.get('dominant_narratives')}
   Trending language today: {morning_brief.get('trending_language')}
   Top active accounts: {morning_brief.get('top_accounts_active')}
   Avoid: {morning_brief.get('topics_to_avoid')}"

VALIDATION after each addition:
1. python3 -c "from clip_scorer import score_clips; print('ClipScorer OK')" (from video_pipeline_v3/)
2. python3 -c "from script_writer import generate_from_clips; print('ScriptWriter OK')" (from video_pipeline_v3/)
3. bash ~/protocol_pulse/regression_test.sh - ZERO FAILs

COMMIT after all three:
  git add video_pipeline_v3/clip_scorer.py video_pipeline_v3/script_writer.py video_pipeline_v3/daily_run.py
  git commit -m "feat(pipeline): discourse multiplier in clip scoring, upgraded social segment narration, morning brief wiring"
  git push

DO NOT TOUCH: assembler.py, tts_engine.py, gemini_grade.py, overnight_render_loop.py, nitter_scraper.py
