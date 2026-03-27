#!/bin/bash
echo "=== PROTOCOL PULSE MORNING CHECK ==="
echo "Time: $(date)"
echo ""
echo "--- LOOP STATUS ---"
tail -5 ~/protocol_pulse/video_pipeline_v3/logs/overnight_loop.log 2>/dev/null || echo "No loop log"
echo ""
echo "--- WINNER RECIPE ---"
cat ~/protocol_pulse/video_pipeline_v3/logs/WINNER_RECIPE.json 2>/dev/null || echo "Not yet — loop still running"
echo ""
echo "--- LATEST VIDEO ---"
ls -lh ~/protocol_pulse/video_pipeline_v3/output/2026-03-20/*.mp4 2>/dev/null | grep -v ".mp4." | tail -3
echo ""
echo "--- PROCESSES ---"
pgrep -la python3 | grep -E "overnight|daily_producer" || echo "No render running"
echo ""
echo "--- GPU ---"
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv,noheader
