#!/bin/bash
# Master fix script — runs entirely on Ultron, no relay needed
# Execute: bash ~/protocol_pulse/scripts/run_all_fixes.sh

cd ~/protocol_pulse
echo "=== STARTING ALL FIXES $(date) ==="

# Write all CC prompts to files
cat > /tmp/nav_ticker_media_prompt.txt << 'PROMPT'
Read PIPELINE_LAWS.md first.

THREE FIXES:

FIX 1: NAV MORE DROPDOWN
grep -n "More\|dropdown\|panopticon\|value-stream" templates/base.html | head -20
Add to More dropdown: Panopticon->/panopticon, Proof of Value->/value-stream, Sovereign Money->/sovereign-money, Bitcoin Map->/map, Podcasts->/podcasts, Nostr->/nostr, Intelligence->/intelligence-terminal

FIX 2: TICKER DUPLICATE TITLES
grep -n "ticker\|marquee\|top_articles\|headline" templates/index.html core/routes.py | head -15
Deduplicate by title before rendering. Track seen titles in a set, skip dupes.

FIX 3: MEDIA PAGE LAYOUT REGRESSION
git log --oneline templates/media_hub.html | head -5
Check if commit 20c652e7 overwrote the media_build layout. Restore large interactive UI layout while keeping auto-fresh FIFO content rotation logic.

git add -A && git commit -m "fix(nav+ticker+media): nav all pages, dedup ticker, media big UI with fresh content" && git push
PROMPT

# Fire the CC session using autopilot
bash ~/protocol_pulse/scripts/autopilot.sh nav_ticker_fix /tmp/nav_ticker_media_prompt.txt
echo "=== nav_ticker_fix FIRED ==="

# Status check
sleep 5
echo "=== ACTIVE SESSIONS ==="
tmux ls
echo "=== GPU ==="
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
