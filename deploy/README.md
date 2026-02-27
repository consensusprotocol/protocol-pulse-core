# Deploy: Protocol Pulse

## systemd (Gunicorn)

Install the service for 24/7 auto-job and web app:

```bash
sudo cp deploy/protocol-pulse.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now protocol-pulse.service
sudo systemctl status protocol-pulse.service
```

- **ENABLE_LIVE_POSTING**: Set to `true` in `/home/ultron/protocol_pulse/.env` to allow the viral reel auto-job (every 30m) to post to X and Telegram. Default in the unit is `false`; `.env` overrides.
- Logs: `tail -f /home/ultron/protocol_pulse/logs/app.log`
- Restart: `sudo systemctl restart protocol-pulse.service`

## Test reel pipeline (Batch 6)

From repo root with venv activated:

```bash
./venv/bin/python scripts/test_reel_pipeline.py [--video-id VIDEO_ID] [--channel-name NAME] [--no-narration] [--no-publish]
```

Produces:

- Full narrated reel MP4 (when narration and build succeed)
- Publish log: `logs/test_reel_pipeline_<timestamp>.json` and `.log`

Requires: `XAI_API_KEY`, `ELEVENLABS_API_KEY` (for narration), yt-dlp, ffmpeg. Use `--no-narration --no-publish` for a build-only dry run.
