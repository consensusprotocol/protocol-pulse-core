# Protocol Pulse Architecture Map

## Host Baseline (Phase 0)
- Hostname: `ultron`
- Kernel: `Linux ultron 6.8.0-88-generic`
- Python: `3.10.12`
- GPUs:
  - `GPU0: NVIDIA GeForce RTX 4090 (24564 MiB)`
  - `GPU1: NVIDIA GeForce RTX 4090 (24564 MiB)`
- Memory: `93 GiB total`
- Root disk: `/dev/nvme0n1p2` (`1.8T`, ~6% used)

## Runtime Components
- Web App: Flask app object at `app:app` served by Gunicorn on `0.0.0.0:5000`
- Background Intel Loop: `scripts/intelligence_loop.py`
- Medley Director: `medley_director.py` (`ffmpeg` + `h264_nvenc`)
- Local Model Lane: Ollama (`127.0.0.1:11434`)

## GPU Lane Assignment
- `GPU0` (`CUDA_VISIBLE_DEVICES=0`): intelligence loop/model-side tasks
- `GPU1` (`CUDA_VISIBLE_DEVICES=1`): Medley render path (NVENC)

## Network / Ports
- `5000`: Protocol Pulse web app (Gunicorn)
- `11434`: Ollama local inference
- `22`: SSH

## Data Flows (Core)
1. Browser -> Flask routes (`routes.py`) -> DB/services -> templates/SSE/socket responses.
2. Intel loop -> X-sentry + whale cycle -> DB + `logs/automation.log` + `data/pulse_events.jsonl`.
3. Hub/Value Stream UIs poll APIs and stream from:
   - `/api/signal-terminal/stream` (SSE)
   - `/api/value-stream/pulse`
4. Medley trigger (`/api/hub/medley/start`) -> `medley_director.py` -> MP4 artifact in `logs/`.

## Persistence / Files
- DB URL from env (`DATABASE_URL`), fallback sqlite
- Runtime status: `logs/runtime_status.json`
- App logs: `logs/app.log`
- Automation logs: `logs/automation.log`
- Structured pulse stream: `data/pulse_events.jsonl`

## Service Topology (systemd --user)
- `protocol-pulse.service`: Gunicorn web runtime
- `pulse_intel.service`: intelligence loop

