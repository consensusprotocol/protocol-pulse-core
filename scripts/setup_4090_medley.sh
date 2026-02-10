#!/usr/bin/env bash
# =============================================================================
# Protocol Pulse — 4090 Server Setup (YouTube Medley)
# Run on Ultron @ 10.0.0.126 (or any Ubuntu/Debian 4090 box) via SSH.
# Usage: bash setup_4090_medley.sh
# =============================================================================
set -e

echo "=============================================="
echo " Phase 1: Hardware & Drivers"
echo "=============================================="

if ! command -v nvidia-smi &>/dev/null; then
  echo "ERROR: nvidia-smi not found. Install NVIDIA drivers first."
  exit 1
fi
echo "nvidia-smi:"
nvidia-smi
echo ""
GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
echo "Detected $GPU_COUNT GPU(s)."
if [ "$GPU_COUNT" -lt 1 ]; then
  echo "ERROR: No GPUs detected."
  exit 1
fi

echo ""
echo "Installing nvtop (thermal monitoring)..."
if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y nvtop 2>/dev/null || {
    echo "nvtop not in apt; trying snap or build..."
    if command -v snap &>/dev/null; then
      sudo snap install nvtop 2>/dev/null || true
    fi
  }
elif command -v dnf &>/dev/null; then
  sudo dnf install -y nvtop 2>/dev/null || true
fi
if command -v nvtop &>/dev/null; then
  echo "nvtop installed: $(which nvtop)"
else
  echo "WARN: nvtop could not be installed; you can build from source later."
fi

echo ""
echo "=============================================="
echo " Phase 2: Video Infrastructure"
echo "=============================================="

# --- ffmpeg with libnvenc ---
echo "Checking ffmpeg and NVENC..."
if command -v ffmpeg &>/dev/null; then
  if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q nvenc; then
    echo "ffmpeg already has libnvenc support."
  else
    echo "ffmpeg found but no NVENC. Install ffmpeg with --enable-nvenc (e.g. from ppa or build)."
    if command -v apt-get &>/dev/null; then
      sudo add-apt-repository -y ppa:savoury1/ffmpeg4 2>/dev/null || true
      sudo apt-get update -qq
      sudo apt-get install -y ffmpeg 2>/dev/null || true
    fi
  fi
else
  echo "Installing ffmpeg..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y ffmpeg
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y ffmpeg
  fi
fi
command -v ffmpeg && ffmpeg -version | head -1

# --- yt-dlp ---
echo ""
echo "Installing yt-dlp..."
if command -v pip3 &>/dev/null; then
  pip3 install -U yt-dlp
elif command -v pip &>/dev/null; then
  pip install -U yt-dlp
fi
if command -v yt-dlp &>/dev/null; then
  echo "yt-dlp: $(yt-dlp --version)"
else
  sudo curl -sL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
  sudo chmod +x /usr/local/bin/yt-dlp
  echo "yt-dlp installed to /usr/local/bin/yt-dlp"
fi

# --- faster-whisper (GPU 0) ---
echo ""
echo "Setting up faster-whisper (GPU-accelerated) in ~/protocol_pulse..."
MEDLEY_HOME="${MEDLEY_HOME:-$HOME/protocol_pulse}"
mkdir -p "$MEDLEY_HOME"
cd "$MEDLEY_HOME"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
set +e
source venv/bin/activate
pip install -U pip
pip install "faster-whisper>=1.0"  # GPU support via CUDA
set -e
echo "faster-whisper install done (use GPU 0 by default with device='cuda')."

echo ""
echo "=============================================="
echo " Phase 3: Medley Engine (project layout)"
echo "=============================================="
mkdir -p "$MEDLEY_HOME"/{channels,clips,output,logs,branding}
echo "Created: $MEDLEY_HOME/{channels,clips,output,logs,branding}"
echo ""
echo "Next: copy or clone the Medley Engine Python code into $MEDLEY_HOME"
echo "  e.g. from this repo: rsync -av medley_engine/ $MEDLEY_HOME/"
echo "  then: cd $MEDLEY_HOME && source venv/bin/activate && pip install -r requirements.txt && python run_medley.py"
echo ""
echo "Setup complete."
