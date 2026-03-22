Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Fix social segment and space tap segment — both have been missing from every render.
Root cause identified: social_posts fetched AFTER generate_from_clips() runs, so Claude
never sees tweet data and skips the social segment. Space tap same issue.

DO NOT touch: assembler.py, tts_engine.py, overnight_render_loop.py, gemini_grade.py

STEP 1 — AUDIT
Read daily_producer.py lines 520-590 fully.
Read script_writer.py generate_from_clips() signature — what parameters does it accept?
Read utils/social_fetcher.py get_todays_social_posts() — what does it return?
Check data/tweet_study/raw_tweets.json exists and has recent tweets.
Check selections.json for today — does space_tap_clips exist in it?

STEP 2 — FIX SOCIAL SEGMENT
In daily_producer.py, find where get_todays_social_posts() is called (line ~567).
Move it to BEFORE the generate_from_clips() call (line ~532).
Pass social_posts as parameter to generate_from_clips():
  social_posts = get_todays_social_posts(max_posts=5)
  social_posts.sort(key=lambda p: p.get("likes", 0), reverse=True)
  script = generate_from_clips(selections, btc_price=btc_price,
                               live_context=live_context,
                               social_posts=social_posts)  # ADD THIS

Check generate_from_clips() signature — add social_posts parameter if not present.
Inside generate_from_clips(), verify social_posts gets passed to the prompt as {social_posts}.

STEP 3 — FIX SPACE TAP SEGMENT
Check if selections.json contains space_tap_clips.
In daily_producer.py, find where space_tap_clips are passed to generate_from_clips.
Verify the space tap prompt section in script_writer.py receives the data.
If space_tap_clips is empty in selections.json, check x_spaces_scraper:
  python3 ~/protocol_pulse/x_spaces_scraper/scraper.py --test 2>&1 | tail -5
  Check ~/protocol_pulse/logs/xspaces_cron.log for errors

STEP 4 — TEST
Run: cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --skip-scan --test 2>&1 | grep -E "social|SOCIAL|space_tap|STEP" | tail -20
Verify script.json contains social_segment entries.
Verify script.json contains space_tap entries (if spaces available).

STEP 5 — REGRESSION + COMMIT
bash ~/protocol_pulse/regression_test.sh
git add video_pipeline_v3/daily_producer.py video_pipeline_v3/script_writer.py
git commit -m "fix(pipeline): social_posts passed to generate_from_clips BEFORE script generation — social segment now appears every render; space tap fix"
git push