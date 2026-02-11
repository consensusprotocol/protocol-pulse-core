# Protocol Pulse Runbook

## 1) Environment
- Copy env skeleton from `ENVIRONMENT.example` into `.env` and set real values.
- Minimum required:
  - `SESSION_SECRET`
  - `DATABASE_URL`

## 2) Dev Runtime (manual)
- Activate venv and run app:
  - `cd /home/ultron/protocol_pulse`
  - `./venv/bin/gunicorn -w 3 -k gthread --threads 4 -b 0.0.0.0:5000 app:app`
- Run intel loop manually:
  - `CUDA_VISIBLE_DEVICES=0 ./venv/bin/python scripts/intelligence_loop.py`

## 3) Prod Runtime (systemd --user)
- Web service unit: `~/.config/systemd/user/protocol-pulse.service`
- Intel service unit: `~/.config/systemd/user/pulse_intel.service`

Commands:
- `systemctl --user daemon-reload`
- `systemctl --user enable --now protocol-pulse.service`
- `systemctl --user enable --now pulse_intel.service`
- `systemctl --user status protocol-pulse.service`
- `systemctl --user status pulse_intel.service`

If using systemd user services after reboot/login-less sessions:
- `sudo loginctl enable-linger ultron`

## 4) Migrations (no runtime create_all)
- `cd /home/ultron/protocol_pulse`
- `FLASK_APP=app:app ./venv/bin/flask db upgrade`
- Optional model diff:
  - `FLASK_APP=app:app ./venv/bin/flask db migrate -m "<message>"`

## 5) Self-Check Gates
- Run full gate suite:
  - `cd /home/ultron/protocol_pulse`
  - `./venv/bin/python scripts/self_check.py`
- Exit code `0` = all gates pass.

## 6) Logs
- App:
  - `tail -f /home/ultron/protocol_pulse/logs/app.log`
- Automation:
  - `tail -f /home/ultron/protocol_pulse/logs/automation.log`
- Structured pulse events:
  - `tail -f /home/ultron/protocol_pulse/data/pulse_events.jsonl`

## 7) Common Fixes
- 500 or stale route issues:
  - `systemctl --user restart protocol-pulse.service`
- Loop stalled:
  - `systemctl --user restart pulse_intel.service`
- DB/migration mismatch:
  - run `flask db upgrade`, then restart services
- Premium route test gate (`/hub`, `/api/risk-data`) on localhost:
  - use header `X-Self-Check: 1`
  - ensure `ENABLE_SELF_CHECK_BYPASS=true` in service env

