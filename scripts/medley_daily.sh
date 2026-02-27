#!/usr/bin/env bash
set -euo pipefail

cd /home/ultron/protocol_pulse

mkdir -p /home/ultron/protocol_pulse/logs

export CUDA_VISIBLE_DEVICES=1
export PYTHONUNBUFFERED=1

/home/ultron/protocol_pulse/venv/bin/python - << 'PY'
from services.scheduler import run_task
result = run_task("daily_medley_gpu1")
print(result)
if not result.get("success"):
    raise SystemExit(1)
PY

