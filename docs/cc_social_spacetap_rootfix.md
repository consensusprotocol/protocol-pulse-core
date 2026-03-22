Load ~/protocol_pulse/PIPELINE_LAWS.md first. Two root cause fixes. Read every file fully before touching it.

ROOT CAUSE AUDIT (do not skip — confirmed by live testing):

BUG 1: Social segment shows old Saylor HODL + old Pomp tweets every episode
ROOT CAUSE: nitter_scraper.py sets engagement_rate=0.0 and likes=0 for ALL scraped tweets.
social_fetcher.py sorts by engagement_rate DESC — so the old March 4 cached tweets
(Saylor HODL 65k likes, Pomp 45k likes) ALWAYS beat fresh Nitter tweets that score 0.
Also: Nitter tweets have no created_at so the 7-day recency filter skips them too.

BUG 2: Space Tap NEVER appears in any episode
ROOT CAUSE: The Space Tap fix was added to daily_run.py but the overnight loop calls
daily_producer.py --skip-scan. These are TWO SEPARATE pipeline entry points.
daily_producer.py has ZERO space tap code. It has never been wired in.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 1 — nitter_scraper.py: populate engagement metrics + timestamps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ~/protocol_pulse/services/nitter_scraper.py

Read the full file first. Find where tweets are constructed (likes=0, engagement_rate=0.0).

Fix:
1. When scraping each tweet, extract the actual like/retweet counts from the HTML.
   Nitter shows likes as: <span class="icon-heart"></span><span class="tweet-stat-count">65,156</span>
   or similar. Parse them. If parsing fails, default 0 is fine — but TRY.

2. Set created_at to NOW (UTC ISO format) for any tweet scraped today:
   from datetime import datetime, timezone
   tweet["created_at"] = datetime.now(timezone.utc).isoformat()
   This ensures the 7-day recency filter in social_fetcher.py keeps them.

3. Calculate engagement_rate from parsed likes+retweets if follower count unavailable:
   Use a simple proxy: engagement_rate = (likes + retweets * 2) / 1000
   This is not accurate but gives fresh tweets a fighting chance vs old cached ones.
   Any tweet with likes>100 will score > cached tweets with 0.

4. After fixing nitter_scraper.py, run it immediately:
   python3 ~/protocol_pulse/services/nitter_scraper.py
   Then verify raw_tweets.json has updated likes/engagement_rate:
   python3 -c "import json; d=json.load(open('data/tweet_study/raw_tweets.json')); \
   tweets=d if isinstance(d,list) else d.get('tweets',[]); \
   top=sorted(tweets,key=lambda t:t.get('engagement_rate',0),reverse=True)[:5]; \
   [print(t.get('handle'),t.get('likes'),t.get('engagement_rate')) for t in top]"
   (run from ~/protocol_pulse/video_pipeline_v3/)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 2 — daily_producer.py: Add Space Tap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ~/protocol_pulse/video_pipeline_v3/daily_producer.py

Read the full file. Find where the script is generated (generate_from_clips call).
Find where selections dict is populated. Add Space Tap RIGHT AFTER script generation,
BEFORE the TTS step (Step 6).

Add this block (adapt indentation to match surrounding code):

    # ── Space Tap: live X Spaces clips ──────────────────────────────
    print("\n[STEP 5b] SPACE TAP — LIVE X SPACES INTERCEPT...")
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'x_spaces_scraper'))
        from scraper import get_best_space_clips
        _st = get_best_space_clips(max_clips=3)
        if _st and _st.get('clips'):
            script['space_tap_clips'] = _st['clips']
            # Re-save script with space tap injected
            with open(os.path.join(run_dir, 'script.json'), 'w') as _f:
                import json as _json
                _json.dump(script, _f, indent=2)
            print(f"  Space Tap: {len(_st['clips'])} clips injected from {_st.get('spaces_count',0)} spaces")
        else:
            print("  Space Tap: no live spaces found — segment skipped")
    except Exception as _e:
        print(f"  Space Tap: skipped ({_e})")

Where is BASE defined in daily_producer.py? Check and use the correct path to x_spaces_scraper.
The x_spaces_scraper is at ~/protocol_pulse/x_spaces_scraper/scraper.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. python3 -m py_compile ~/protocol_pulse/services/nitter_scraper.py && echo OK
2. python3 -m py_compile ~/protocol_pulse/video_pipeline_v3/daily_producer.py && echo OK
3. bash ~/protocol_pulse/regression_test.sh — ZERO FAILs

COMMIT:
git add services/nitter_scraper.py video_pipeline_v3/daily_producer.py
git commit -m "fix(social): nitter scraper now sets likes/engagement_rate/created_at — fresh tweets beat stale cache; fix(spacetap): wire Space Tap into daily_producer.py — was in wrong file (daily_run.py) this entire time"
git push

ONLY touch: nitter_scraper.py and daily_producer.py. Nothing else.
