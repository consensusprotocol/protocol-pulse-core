#!/bin/bash
# ─────────────────────────────────────────────────────
# PULSE CHECK — Daily Pipeline Runner
# Cron: 0 23 * * * /home/ultron/protocol_pulse/services/video_engine/run_daily.sh
# ─────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="/home/ultron/protocol_pulse"
VENV_DIR="/home/ultron/protocol_pulse/venv"
DATE=$(date +%Y-%m-%d)
LOG_DIR="$PROJECT_DIR/data/episodes/$DATE"

mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

# Activate venv
source "$VENV_DIR/bin/activate"

# Load environment
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[$DATE] Starting Pulse Check pipeline..."

# Run the pipeline, log to both console and file
python3 -m services.video_engine.first_run 2>&1 | tee "$LOG_DIR/pipeline.log"

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$DATE] Pipeline completed successfully."
else
    echo "[$DATE] Pipeline failed with exit code $EXIT_CODE"
fi

# Deactivate
deactivate 2>/dev/null || true

exit $EXIT_CODE
