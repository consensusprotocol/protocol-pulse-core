#!/usr/bin/env bash
set -e

echo "=== Protocol Pulse 4090 Server Setup ==="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"

echo "[*] Using Python: $PYTHON_BIN"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found. Install Python 3.12 first."
  exit 1
fi

echo "[*] Creating virtual environment (.venv)..."
$PYTHON_BIN -m venv .venv
source .venv/bin/activate

echo "[*] Upgrading pip..."
pip install --upgrade pip

echo "[*] Installing PyTorch with CUDA (4090 / CUDA 12.x)..."
pip install "torch>=2.2.0" --index-url https://download.pytorch.org/whl/cu121

echo "[*] Installing project requirements..."
pip install -r core/requirements.txt

echo "[*] Setup complete."
echo "Activate with: source .venv/bin/activate"
