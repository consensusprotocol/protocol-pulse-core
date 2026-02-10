# Protocol Pulse — YouTube Medley Engine (4090)

Runs on the 4090 server (e.g. Ultron @ 10.0.0.126). Monitors YouTube channels for new uploads, extracts 60-second "Alpha" clips (Bitcoin-keyword segments via GPU transcription), merges them with a cross-dissolve, and appends your branding tag.

## Quick setup on the 4090 server

```bash
# 1. SSH in
ssh user@10.0.0.126

# 2. Run the three-phase setup script (from this repo)
cd /path/to/ProtocolPulse
chmod +x scripts/setup_4090_medley.sh
./scripts/setup_4090_medley.sh

# 3. Copy Medley Engine into ~/protocol_pulse
rsync -av medley_engine/ ~/protocol_pulse/
cd ~/protocol_pulse

# 4. Install Python deps and run
source venv/bin/activate
pip install -r requirements.txt
# Edit config.yaml: add your YouTube channel URLs and branding path
python run_medley.py --channels-only   # test: list recent uploads
python run_medley.py --daily           # full run
# or
python run_medley.py --merge-only      # merge existing clips + tag
```

## Phase 1–2 (setup script)

- Verifies **nvidia-smi** and GPU count  
- Installs **nvtop** for thermal monitoring  
- Installs **ffmpeg** (with NVENC if available)  
- Installs **yt-dlp**  
- Creates venv in `~/protocol_pulse` and installs **faster-whisper** (GPU)

## Phase 3 (this project)

- **config.yaml** — channels to monitor, Bitcoin keywords, paths, clip length  
- **run_medley.py** — monitor → download → transcribe (GPU 0) → extract Alpha clips → merge (xfade) → append branding

## Branding tag

The end-card lives at **`branding/tag.mp4`** in this folder. Keep it in the repo and deploy with the rest of `medley_engine/` so the 4090 (or any machine) always gets the same file when you sync. If the file is missing, the script still outputs the medley as `output/medley_tagged.mp4` (no tag appended).

## Commands

| Command | Description |
|--------|-------------|
| `python run_medley.py --daily` | Fetch today’s uploads, extract Alpha clips, merge, append tag |
| `python run_medley.py --channels-only` | Only list recent upload URLs |
| `python run_medley.py --merge-only` | Merge existing `clips/alpha_*.mp4` and append tag |

Output: `output/medley_tagged.mp4`.
