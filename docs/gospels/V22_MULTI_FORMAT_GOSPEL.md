# PROTOCOL PULSE — GOSPEL: V22 MULTI-FORMAT OUTPUT ENGINE
# Branch: feature/v22-multi-format | Created: 2026-03-09
# BLOCKING: Requires video pipeline stable first (clean daily renders)
---

## WHAT THIS IS
One pipeline run → six distribution formats simultaneously. This is the
multiplier that makes the expensive daily pipeline 6x more valuable.

## THE LAWS
### LAW 1: Only runs AFTER the 12-min episode is fully rendered and QC-passed
### LAW 2: Never adds latency to the main episode render — runs in parallel subprocess
### LAW 3: Article adapter MUST rewrite for reading (strip TTS language)
### LAW 4: Tweet thread max 8 tweets, each under 280 chars, no em dashes
### LAW 5: Nostr publish uses PP keypair (NOSTR_PRIVATE_KEY in .env)

## SIX OUTPUT FORMATS
1. **12-min YouTube** — existing pipeline (no change)
2. **3-5 YouTube Shorts** — shorts_cutter.py (enhanced clip selection)
3. **Podcast MP3** — strip visual segments, push to Fountain RSS
4. **Written article** — script → article rewrite → POST to /api/v2/articles
5. **Tweet thread** — 8 tweets, hook + story + link to episode
6. **Nostr long-form** — NIP-23 post via relay

## ARCHITECTURE
```python
# format_multiplier.py — runs as subprocess after main render
def run_all_formats(manifest, episode_mp4, script_text):
    pool = multiprocessing.Pool(processes=4)
    pool.apply_async(cut_shorts, [manifest, episode_mp4])
    pool.apply_async(create_podcast, [episode_mp4, script_text])
    pool.apply_async(publish_article, [script_text, manifest])
    pool.apply_async(post_tweet_thread, [script_text, manifest])
    pool.apply_async(post_nostr, [script_text, manifest])
    pool.close()
    pool.join()
```

## VERIFICATION
- [ ] All 6 formats produce outputs in single pipeline run
- [ ] Article appears on site within 5 min of render
- [ ] Tweet thread posts (verify X API key in .env)
- [ ] Podcast episode in RSS feed
- [ ] No added latency to main episode
- [ ] regression_test.sh: zero FAILs

## CLAUDE CODE PROMPT
```
Read ~/protocol_pulse/docs/gospels/V22_MULTI_FORMAT_GOSPEL.md.
Read ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md.
Branch: feature/v22-multi-format.
PREREQUISITE: Only build this if daily pipeline is producing clean renders.
1. Create video_pipeline_v3/format_multiplier.py
2. Implement all 5 secondary format functions
3. Wire into daily_producer.py as post-render step
4. Add X API integration (TWITTER_BEARER_TOKEN in .env)
5. Test each format individually, then full run
6. regression_test.sh: zero FAILs → commit + push feature/v22-multi-format
```

