#!/bin/bash
# Protocol Pulse Oracle Live Avatar Server v2.0
# FastAPI + uvicorn — production-ready

cd ~/protocol_pulse/oracle/oracle-live/backend

# Activate venv if present, else use system python
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load secrets from parent config
export $(grep -E "^ELEVENLABS_API_KEY|^ANTHROPIC_API_KEY" ~/protocol_pulse/.env 2>/dev/null | xargs)

echo "Starting Oracle Live Avatar API on port 8200..."
uvicorn app:app \
    --host 0.0.0.0 \
    --port 8200 \
    --workers 2 \
    --log-level info \
    2>&1 | tee ~/protocol_pulse/logs/oracle_live.log
