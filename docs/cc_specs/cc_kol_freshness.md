TASK: Fix stale KOL quotes appearing in stage avatar (Pompliano CNBC quote)

The stage avatar narrated a Pompliano "buy Bitcoin" CNBC quote claiming it was from "today"
when it was actually old. This is coming from the script_writer or intel feed using KOL tweets
without checking their publication date.

1. Find where KOL data is injected into stage content:
   grep -rn "pompliano\|kol_pulse\|kol_tweet\|KOL" ~/protocol_pulse/services/video_engine/ --include="*.py" | head -15
   grep -rn "kol_pulse_item\|tweet.*script\|quote.*today" ~/protocol_pulse/video_pipeline_v3/ --include="*.py" | head -10

2. Find the script_writer.py KOL quote section:
   grep -n "kol\|tweet\|quote\|CNBC\|pompliano" ~/protocol_pulse/video_pipeline_v3/script_writer.py 2>/dev/null | head -15

3. Add strict 24-hour freshness filter:
   Any KOL tweet/quote injected into scripts MUST have fetched_at or published_at within 24 hours
   Add: WHERE fetched_at > datetime('now', '-24 hours') to any KOL DB query
   
4. Add source citation requirement: if a quote is used, the script must include the date
   e.g. "Earlier today, Pompliano said..." only if tweet IS from today
   Otherwise skip the quote entirely

5. Test: run script_writer with --dry-run and verify no stale quotes appear

6. git add -A && git commit -m "fix(pipeline): 24h freshness filter on KOL quotes — no stale data in scripts" && git push
