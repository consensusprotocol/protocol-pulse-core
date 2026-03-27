#!/bin/bash
set -e
STYLETTS2_DIR="$HOME/protocol_pulse/video_pipeline_v3/voices/styletts2"
LOG="$STYLETTS2_DIR/training.log"
echo "[StyleTTS2] Fine-tune starting at $(date)" | tee "$LOG"

# Use GPU 1 only — GPU 0 may be in use by pipeline render
export CUDA_VISIBLE_DEVICES=1

cd /tmp/StyleTTS2
python3 train_finetune.py -p "$STYLETTS2_DIR/config_finetune.yml" 2>&1 | tee -a "$LOG"

echo "[StyleTTS2] Training complete at $(date)" | tee -a "$LOG"
ls -lh "$STYLETTS2_DIR/checkpoints/"*.pth 2>/dev/null | tee -a "$LOG" || echo "No checkpoints found"
