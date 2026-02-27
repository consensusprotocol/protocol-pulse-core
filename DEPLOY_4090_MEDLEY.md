# Deploy Protocol Pulse Medley to 4090 Server (Ultron)

One-place checklist to get the YouTube Medley Engine running on your 4090 box (e.g. **Ultron @ 10.0.0.126**).

## 1. Copy repo to the server (if not already)

From your dev machine:

```bash
rsync -av --exclude venv --exclude .git /path/to/ProtocolPulse/ user@10.0.0.126:~/ProtocolPulse/
```

Or clone from your git remote on the server.

## 2. On the server: run Phase 1 & 2 setup

SSH in and run the automated setup (drivers check, nvtop, ffmpeg, yt-dlp, faster-whisper venv):

```bash
ssh user@10.0.0.126
cd ~/ProtocolPulse
chmod +x scripts/setup_4090_medley.sh
./scripts/setup_4090_medley.sh
```

This creates `~/protocol_pulse` and a venv there. It does **not** copy the Medley Engine code into it; you do that next.

## 3. Deploy the Medley Engine into ~/protocol_pulse

On the server:

```bash
cd ~/ProtocolPulse
rsync -av medley_engine/ ~/protocol_pulse/
cd ~/protocol_pulse
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Configure and run

- Edit `~/protocol_pulse/config.yaml`: add real YouTube channel URLs under `channels:`.
- **Branding tag:** `medley_engine/branding/tag.mp4` is in the repo. When you rsync `medley_engine/` to the server it becomes `~/protocol_pulse/branding/tag.mp4`, so the 4090 always has the same tag no matter which machine you deploy from.

Then:

```bash
cd ~/protocol_pulse
source venv/bin/activate
python run_medley.py --channels-only   # list recent uploads
python run_medley.py --daily          # full pipeline
# or
python run_medley.py --merge-only     # merge existing clips + append tag
```

Output: `~/protocol_pulse/output/medley_tagged.mp4`.

## 5. Monitor GPUs

```bash
nvtop          # thermal / load
nvidia-smi     # quick status
```

---

**Summary:** Run `scripts/setup_4090_medley.sh` on the 4090 server, then rsync `medley_engine/` into `~/protocol_pulse`, install deps, edit `config.yaml`, and run `run_medley.py`.
