# TTS Voice Assets

## PBX Voice (F5-TTS fine-tuned)
- pbx_raw.wav           — master 29min training recording (DO NOT DELETE)
- pbx_reference.wav     — 30s reference clip (auto-extracted from pbx_raw.wav)
- pbx_voice.pt          — fine-tuned checkpoint (~300MB, DO NOT COMMIT)
- segments/             — auto-segmented training clips (safe to delete post-train)
- finetune/             — training artifacts (safe to delete post-train)
- train.csv             — F5-TTS training manifest (audio_file|text)
- train_manifest.json   — human-readable copy

## Host 1 — Kokoro af_heart
Embedded in Kokoro model — no file needed.

## To retrain
python3 prep_dataset.py && bash finetune/run_finetune.sh
