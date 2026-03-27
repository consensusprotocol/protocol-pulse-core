# SESSION: tts_recovery
# Recovery prompt — tts_engine.py patching is COMPLETE, training is running separately.
# Goal: integration test → cross-LLM audit → regression test → git commit.
# Then monitor pbx_finetune training and export checkpoint when done.

## MANDATORY FIRST STEP
Read ~/protocol_pulse/PIPELINE_LAWS.md before touching anything.

---

## CURRENT STATE (verified before this session)

tts_engine.py — ALL patches applied and syntax-confirmed OK:
- _init_kokoro() ✓ (line 27)
- _init_f5() ✓ (line 63)
- PBX_CHECKPOINT, PBX_REFERENCE_CLIP, KOKORO_HOST1_VOICE defined ✓ (lines 99-102)
- _get_tts_provider() unlocked for "local" ✓ (line 130)
- tts_kokoro() ✓ (line 693)
- tts_f5_finetuned() ✓ (line 734)
- tts_local() ✓ (line 786)
- tts_preflight_local() ✓ (line 837)
- TTS_PROVIDER=local set in .env ✓

Training session pbx_finetune is running separately in tmux.
Checkpoint will appear at: /home/ultron/.local/lib/python3.10/ckpts/pbx_voice/model_last.pt
Export destination: ~/protocol_pulse/video_pipeline_v3/voices/pbx_voice.pt

DO NOT touch tts_engine.py unless integration test reveals a bug.
DO NOT restart training — it is already running in pbx_finetune tmux session.

---

## PHASE 1: VERIFY KOKORO IS FUNCTIONAL

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/ultron/protocol_pulse/video_pipeline_v3')
os.environ = __import__('os').environ
import os
os.environ['TTS_PROVIDER'] = 'local'
from tts_engine import tts_kokoro, KOKORO_HOST1_VOICE
import subprocess

ok = tts_kokoro('Bitcoin signal confirmed.', '/tmp/kokoro_preflight.m4a', voice=KOKORO_HOST1_VOICE, speed=1.0)
if ok:
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', '/tmp/kokoro_preflight.m4a'],
                       capture_output=True, text=True)
    print(f'Kokoro OK: {float(r.stdout.strip()):.2f}s audio')
else:
    print('Kokoro FAILED')
    sys.exit(1)
"
```

If Kokoro fails, diagnose and fix before proceeding. Check:
- `python3 -c "from kokoro import KPipeline; print('pytorch OK')"` 
- `python3 -c "from kokoro_onnx import Kokoro; print('onnx OK')"`
- If neither works: `pip install kokoro --break-system-packages`

---

## PHASE 2: INTEGRATION TEST

```bash
cd ~/protocol_pulse/video_pipeline_v3

python3 << 'EOF'
import os, sys
os.environ["TTS_PROVIDER"] = "local"

from tts_engine import generate_dialogue_audio, tts_preflight_local

print("=== LOCAL TTS INTEGRATION TEST ===")
tts_preflight_local()

test_dialogue = [
    {"host": 1, "text": "Bitcoin cleared sixty-nine thousand today as ETF inflows hit two hundred million.", "type": "setup"},
    {"host": 2, "text": "That is a significant level. The halving in April cuts miner rewards to three point one two five Bitcoin.", "type": "react"},
    {"host": 1, "text": "On-chain data confirms accumulation. Whales are loading up.", "type": "bridge"},
    {"host": 2, "text": "Stay sovereign. We will break down the full data after this.", "type": "wrap"},
]

out_dir = "/tmp/tts_recovery_test"
result = generate_dialogue_audio(test_dialogue, out_dir)

print(f"\nResults:")
print(f"  Duration: {result['total_duration']:.1f}s")
ok_lines = [l for l in result['lines'] if l.get('path') and os.path.exists(l.get('path', ''))]
print(f"  Lines OK: {len(ok_lines)}/{len(test_dialogue)}")

for l in result["lines"]:
    if l.get("path") and os.path.exists(l["path"]):
        print(f"  host{l['host']}: {l['duration']:.1f}s — {l['text'][:55]}")
    else:
        print(f"  host{l['host']}: FAILED — {l['text'][:55]}")

if result.get("full") and os.path.exists(result["full"]):
    size = os.path.getsize(result["full"])
    print(f"\n  Full audio: {size/1024:.0f}KB")
    if size > 10240:
        print("  ✅ INTEGRATION TEST PASSED")
    else:
        print("  ❌ FAILED: full_dialogue.m4a too small")
        sys.exit(1)
else:
    print("  ❌ FAILED: no full audio produced")
    sys.exit(1)
EOF
```

If integration test fails, diagnose the specific host/line that failed before proceeding.
ElevenLabs fallback triggering for host2 is EXPECTED and OK — F5 checkpoint not yet exported.
Kokoro failing for host1 is NOT OK — fix before continuing.

---

## PHASE 3: CROSS-LLM AUDIT

```bash
cd ~/protocol_pulse
python3 cross_llm_audit.py \
    --files video_pipeline_v3/tts_engine.py \
    --focus "local TTS integration: _init_kokoro, _init_f5, tts_kokoro, tts_f5_finetuned, tts_local, tts_preflight_local, provider routing in generate_dialogue_audio, dual-host restore, ElevenLabs fallback chain, cache key prefix local_h1/local_h2, normalize_pronunciation import" \
    --cycle 1
```

Address all P0 and P1 findings. Run Cycle 2 after fixes.

---

## PHASE 4: REGRESSION TEST

```bash
cd ~/protocol_pulse
bash regression_test.sh
```

Must show ZERO FAILs. If any fail, fix before committing.

---

## PHASE 5: GIT COMMIT

```bash
cd ~/protocol_pulse

git add \
    video_pipeline_v3/tts_engine.py \
    video_pipeline_v3/voices/README.md \
    video_pipeline_v3/voices/prep_dataset.py \
    video_pipeline_v3/voices/finetune/run_finetune.sh \
    .gitignore

# Confirm no large binaries staged
git diff --cached --stat | grep -E "\.wav|\.pt|\.safetensors" && echo "WARNING: large binary staged — remove it" || echo "No large binaries staged ✓"

git commit -m "feat(tts): local TTS — Kokoro af_heart (host1) + F5-TTS fine-tuned PBX (host2), ElevenLabs fallback; voice assets excluded from git"
git push origin main
```

---

## PHASE 6: MONITOR TRAINING + EXPORT CHECKPOINT

Training is running in pbx_finetune tmux session.
Poll until model_last.pt appears, then export.

```bash
CKPT_DIR="/home/ultron/.local/lib/python3.10/ckpts/pbx_voice"
DEST="$HOME/protocol_pulse/video_pipeline_v3/voices/pbx_voice.pt"
MAX_WAIT=300  # 5 hours max
ELAPSED=0

echo "Monitoring training in pbx_finetune session..."
while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check if training session still alive
    if ! tmux has-session -t pbx_finetune 2>/dev/null; then
        echo "pbx_finetune session exited at ${ELAPSED}min"
        break
    fi

    if [ -f "$CKPT_DIR/model_last.pt" ]; then
        echo "model_last.pt found at ${ELAPSED}min ✓"
        ls -lh "$CKPT_DIR/model_last.pt"
        break
    fi

    ELAPSED=$((ELAPSED + 1))
    [ $((ELAPSED % 10)) -eq 0 ] && echo "[${ELAPSED}min] Still training... $(ls $CKPT_DIR/*.pt 2>/dev/null | wc -l) checkpoints so far"
    sleep 60
done

# Export
if [ -f "$CKPT_DIR/model_last.pt" ]; then
    cp "$CKPT_DIR/model_last.pt" "$DEST"
    ls -lh "$DEST"
    echo "✓ Checkpoint exported to $DEST"
else
    # Try highest step number as fallback
    BEST=$(ls "$CKPT_DIR"/model_[0-9]*.pt 2>/dev/null | \
        awk -F'[/_.]' '{print $(NF-1), $0}' | sort -n | tail -1 | awk '{print $2}')
    if [ -n "$BEST" ]; then
        cp "$BEST" "$DEST"
        echo "✓ Exported best available checkpoint: $BEST"
        ls -lh "$DEST"
    else
        echo "❌ No checkpoint found — training may still be running or failed"
        echo "Check: tmux attach -t pbx_finetune"
        tail -20 "$HOME/protocol_pulse/video_pipeline_v3/voices/finetune/training.log"
    fi
fi
```

---

## PHASE 7: POST-EXPORT VOICE TEST

Only run this after pbx_voice.pt is confirmed exported.

```bash
python3 << 'EOF'
import os, subprocess
import soundfile as sf
import numpy as np
from f5_tts.api import F5TTS

VOICES_DIR = os.path.expanduser("~/protocol_pulse/video_pipeline_v3/voices")
CKPT = os.path.join(VOICES_DIR, "pbx_voice.pt")
REF = os.path.join(VOICES_DIR, "pbx_reference.wav")
OUT = "/tmp/pbx_voice_final_test.wav"

if not os.path.exists(CKPT):
    print("pbx_voice.pt not yet exported — skip this phase")
    exit(0)

print(f"Loading fine-tuned checkpoint: {os.path.getsize(CKPT)/1e6:.0f}MB")
f5 = F5TTS(model_type="F5TTS_v1_Base", ckpt_file=CKPT, device="cuda")

lines = [
    "Bitcoin cleared sixty-nine thousand today as ETF inflows surged.",
    "The halving is thirty days out. Miners are feeling the heat.",
    "Stay sovereign. Stack sats. See you tomorrow on Protocol Pulse.",
]

all_audio = []
sr = None
for i, text in enumerate(lines):
    print(f"Line {i+1}: {text[:50]}")
    wav, sample_rate, _ = f5.infer(
        ref_file=REF,
        ref_text="",
        gen_text=text,
        speed=1.1,
        show_info=False,
        progress=None,
    )
    all_audio.append(wav)
    sr = sample_rate

sf.write(OUT, np.concatenate(all_audio), sr)
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", OUT], capture_output=True, text=True)
dur = float(r.stdout.strip())
print(f"\n✅ Fine-tuned PBX voice test PASS: {dur:.1f}s")
print(f"   Listen: {OUT}")
EOF
```

---

## PHASE 8: FINAL COMMIT (after checkpoint export)

```bash
cd ~/protocol_pulse

# Confirm pbx_voice.pt exists and is NOT staged (covered by .gitignore)
ls -lh video_pipeline_v3/voices/pbx_voice.pt
git status video_pipeline_v3/voices/pbx_voice.pt  # should show "ignored"

# Update handoff doc
python3 sync_handoff.sh 2>/dev/null || bash sync_handoff.sh 2>/dev/null || echo "sync_handoff not found — skip"

git add docs/handoff/CURRENT_STATE.md 2>/dev/null
git diff --cached --quiet || git commit -m "docs: update handoff — local TTS complete, PBX voice fine-tuned"
git push origin main
```

---

## PHASE 9: STATUS REPORT

Output all of:
1. Kokoro backend active (pytorch | onnx)
2. F5-TTS checkpoint exported (yes/no, path, size)
3. pbx_reference.wav confirmed present
4. Integration test result per host (duration, provider used)
5. Cross-LLM audit: any P0/P1 found and fixed?
6. Regression test: PASS/FAIL count
7. Git commits pushed (hashes)
8. TTS_PROVIDER in .env
9. Training status (complete | still running | failed)

---

## CRITICAL: DO NOT

- Do NOT restart the pbx_finetune training — it is already running
- Do NOT modify tts_engine.py unless integration test reveals a specific bug
- Do NOT commit pbx_raw.wav, pbx_voice.pt, or any .safetensors — .gitignore covers them
- Do NOT touch oracle/avatar_server.py or oracle_dialogue_engine.py
- Do NOT change TTS_PROVIDER back to elevenlabs
- Do NOT skip regression test before committing
- Do NOT break ElevenLabs fallback path — it must still work when F5 is unavailable
