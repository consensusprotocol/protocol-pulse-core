# Protocol Pulse Observability

## Log Streams
- App runtime: `logs/app.log`
- Automation/runtime loop: `logs/automation.log`
- Structured UI events: `data/pulse_events.jsonl`

## Health Endpoints
- `GET /health`
  - fields: `app`, `db`, `last_heartbeat`, `jobs.{sentry_last_run, whale_last_run, risk_last_update, medley_last_run}`, `gpu[]`
- `GET /ready`
  - readiness probe with DB check
- `GET /health/status`
  - service-level checks (db/node/price/rss/youtube) with degraded reporting

## Runtime Status File
- `logs/runtime_status.json`
- sections updated by running jobs:
  - `heartbeat.last_heartbeat`
  - `sentry.last_run`
  - `whale.last_run`
  - `risk.last_update`
  - `medley.last_run`

## Debug Playbook
- Tail app logs:
  - `tail -f /home/ultron/protocol_pulse/logs/app.log`
- Tail automation logs:
  - `tail -f /home/ultron/protocol_pulse/logs/automation.log`
- Watch structured pulse events:
  - `tail -f /home/ultron/protocol_pulse/data/pulse_events.jsonl`
- Check service health quickly:
  - `curl -s http://127.0.0.1:5000/health | jq .`

## What Good Looks Like
- `/health` returns `status: ok` and non-null heartbeat/job timestamps.
- `protocol-pulse.service` and `pulse_intel.service` are active/running.
- `pulse_events.jsonl` receives appended JSON lines during loop cycles.
- UI-facing streams show heartbeat/data without stack traces.

