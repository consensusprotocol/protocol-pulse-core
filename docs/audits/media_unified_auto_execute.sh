#!/bin/bash
cd ~/protocol_pulse
unset ANTHROPIC_API_KEY
# Feed the prompt file to claude non-interactively
claude --dangerously-skip-permissions -p "$(cat /home/ultron/protocol_pulse/docs/audits/media_unified_second_pass_prompt.md)" 2>&1
echo "[AUTO-EXECUTE] Done"
