Fire a Protocol Pulse test render with all latest fixes.
```bash
export PATH=$HOME/.deno/bin:$PATH
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py --test --no-resume 2>&1 | tee /tmp/latest_render.log
```
Monitor output. If it fails, diagnose root cause, fix it, and re-run.
After success, copy output to static/renders/ and report duration + file size.