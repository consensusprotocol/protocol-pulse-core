#!/bin/bash
# Protocol Pulse AutoResearch Runner
# Runs Claude Code in an autonomous loop to fix the video pipeline

cd ~/protocol_pulse/video_pipeline_v3

echo "=== PROTOCOL PULSE AUTORESEARCH ==="
echo "Starting autonomous pipeline fix loop at $(date)"
echo "Claude Code will iterate on the pipeline until renders succeed"

# Launch Claude Code with the program
unset ANTHROPIC_API_KEY
claude --dangerously-skip-permissions -p "Read program.md and begin the experiment loop. Your goal is to make the render succeed. Start by reading the latest crash log, diagnose the failing filtergraph, simplify it, and rerun. Iterate until the render completes successfully."
