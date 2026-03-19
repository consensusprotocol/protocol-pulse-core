#!/bin/bash
set -e

VOICES_DIR="$HOME/protocol_pulse/video_pipeline_v3/voices"
LOG_FILE="$VOICES_DIR/finetune/training.log"
mkdir -p "$VOICES_DIR/finetune"

export NCCL_P2P_DISABLE=1
export NCCL_IB_DISABLE=1

echo "[Fine-tune] Starting at $(date)"

CUDA_VISIBLE_DEVICES=0 f5-tts_finetune-cli \
    --exp_name F5TTS_v1_Base \
    --dataset_name pbx_voice \
    --tokenizer char \
    --finetune \
    --learning_rate 1e-5 \
    --batch_size_per_gpu 3200 \
    --batch_size_type frame \
    --max_samples 64 \
    --grad_accumulation_steps 1 \
    --epochs 100 \
    --num_warmup_updates 100 \
    --save_per_updates 500 \
    --last_per_updates 100 \
    --keep_last_n_checkpoints 3 \
    2>&1 | tee "$LOG_FILE"

echo "[Fine-tune] Complete at $(date)"
