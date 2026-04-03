Fire a Protocol Pulse video render.

Mode: $ARGUMENTS
- If blank or "test": `python3 daily_producer.py --test --no-resume`
- If "fast": `python3 daily_producer.py --fast-test --no-resume`
- If "full": `python3 daily_producer.py --no-resume` (production render)
- If "reuse": `python3 daily_producer.py --test --reuse-content` (re-render with cached content)

```bash
export PATH=$HOME/.deno/bin:$PATH
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py $ARGUMENTS 2>&1 | tee /tmp/latest_render.log
```
Monitor output. If it fails, diagnose root cause, fix it, and re-run.
After success, copy output to static/renders/ and report duration + file size.