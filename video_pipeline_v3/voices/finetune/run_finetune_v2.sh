#!/bin/bash
# PBX Voice Fine-tune v2
# 25 epochs, warmup=200 (audit fix — was 50), save every 200 updates
# GPU 0 only

set -e
export NCCL_P2P_DISABLE=1
export NCCL_IB_DISABLE=1
LOG="$HOME/protocol_pulse/video_pipeline_v3/voices/finetune/training_v2.log"
mkdir -p "$(dirname $LOG)"
echo "[Fine-tune v2] Starting at $(date)"

CUDA_VISIBLE_DEVICES=0 f5-tts_finetune-cli \
    --exp_name F5TTS_v1_Base \
    --dataset_name pbx_voice_v2 \
    --tokenizer char \
    --finetune \
    --learning_rate 1e-5 \
    --batch_size_per_gpu 3200 \
    --batch_size_type frame \
    --max_samples 64 \
    --grad_accumulation_steps 1 \
    --epochs 25 \
    --num_warmup_updates 200 \
    --save_per_updates 200 \
    --last_per_updates 50 \
    --keep_last_n_checkpoints 8 \
    2>&1 | tee "$LOG"

echo "[Fine-tune v2] Complete at $(date)"
ls -lh /home/ultron/.local/lib/python3.10/ckpts/pbx_voice_v2/model_*.pt 2>/dev/null || echo "No checkpoints yet"
