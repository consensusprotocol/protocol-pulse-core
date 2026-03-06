#!/bin/bash
set -a
source ~/protocol_pulse/.env 2>/dev/null
set +a
cd ~/protocol_pulse/oracle_live/backend
exec ~/.local/bin/uvicorn app:app --host 0.0.0.0 --port 8202 --log-level info 2>&1 | tee ~/protocol_pulse/logs/oracle_live.log
