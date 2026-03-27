# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: fix-silence-gaps
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REPORT: PROTOCOL PULSE - FIX-SILENCE-GAPS FEATURE

Below is a detailed forensic review of the provided code for the `fix-silence-gaps` feature in the `video_pipeline_v3/tts_engine.py` file. I have analyzed the code with a focus on correctness, compliance, security, quality, and production readiness. My feedback is direct and prioritized for maximum impact on quality and reliability.

---

### SECTION 1: CORRECTNESS
**Main User Flow Analysis (generate_dialogue_audio):**
1. **Purpose**: The code in `generate_dialogue_audio` (lines 1183-1345) generates audio for a dual-host dialogue script, supporting local TTS (Kokoro, F5-TTS, Chatterbox) and ElevenLabs fallback, with silence gaps between speakers.
2. **Step-by-Step Walkthrough**:
   - Input: A list of dialogue entries with host (1 or 2) and text.
   - For each line, it selects a TTS provider (local or ElevenLabs) based on env var (line 1199).
   - Generates audio per line using `tts_local` or `tts_elevenlabs` (lines 1246-1249).
   - Adds silence gaps between speakers (lines 1283-1286).
   - Concatenates all audio into a full dialogue file (lines 1289-1301).
   - Returns metadata with line paths, durations, and start times (lines 1341-1345).
3. **Logic Errors**:
   - **Silent Failures in Concatenation**: If `ffmpeg` concatenation fails silently (line 1295), `full_path` might not exist, but the code still returns a result with `full_path` as `None` (line 1343). This could cause downstream errors in rendering without explicit failure.
   - **Incorrect Duration Handling for CLIP**: For "CLIP" entries (lines 1219-1231), the timeline advances by `clip_duration`, but no audio is generated. If downstream code expects audio for every entry, this will break.
   - **Fallback Silence Overwrite**: If TTS fails for a line, a 3-second silence is written (lines 1262-1267), but this overwrites any potential cached or partially successful output without logging the original failure cause.
4. **Race Conditions**:
   - **Cache File Access**: The TTS cache system (`_tts_cache_get` and `_tts_cache_put`, lines 729-754) uses file operations without locks. Concurrent requests could overwrite or read incomplete cache files, leading to corrupted audio in production.
   - **Temp File Naming**: Temporary files (e.g., `output_path + ".kokoro.wav"`, line 779) are predictable and not unique per request. Concurrent runs could overwrite each other’s temp files.
5. **Edge Cases**:
   - **Empty Dialogue List**: If `dialogue` is empty, `generate_dialogue_audio` will return an empty result without error (lines 1183-1345). Downstream code might fail if it assumes at least one line.
   - **API Timeout**: ElevenLabs API calls (line 1110) have a 90-second timeout, but network issues could still hang. No circuit breaker exists for prolonged outages.
   - **Bad Input**: If `text` contains invalid characters for TTS (e.g., unprintable Unicode), no sanitization is done before passing to TTS engines (line 920), risking crashes or garbled output.

---

### SECTION 2: LAW COMPLIANCE
Since no specific laws are provided in the "GOVERNING LAWS" section of the spec, I will assume general compliance requirements for data privacy, accessibility, and performance as implied by the technology stack and purpose. If specific laws were intended, they are missing from the input.

- **Data Privacy (Assumed)**: PARTIAL | Lines 217-223 (API key caching) store sensitive keys in memory without encryption or secure storage. No mention of user data handling or GDPR compliance for audio/text data.
- **Accessibility (Assumed)**: VIOLATION | No evidence of accessibility features (e.g., captions for generated audio) in the code, which could violate WCAG or similar standards if applicable.
- **Performance (Spec: ~1000 concurrent users)**: PARTIAL | Lines 729-754 (cache system) lack concurrency controls, risking race conditions under load. No rate limiting for API calls (line 1110) to prevent quota exhaustion.

---

### SECTION 3: SECURITY
1. **SQL Injection**: Not applicable. No direct DB queries or ORM usage in this file.
2. **Authentication Bypasses**: Not applicable. No authentication logic in this file.
3. **Rate Limiting Gaps**: VIOLATION | ElevenLabs API calls (lines 1108-1134) implement basic retry logic for 429 errors, but there’s no global rate limiting or quota tracking. A single user or spike could exhaust paid API limits, causing service-wide failures.
4. **Secrets in Code**: VIOLATION | While API keys are fetched dynamically (line 219), hardcoded voice IDs (e.g., line 160) and model paths (line 177) could be considered sensitive if tied to paid services. No secure vault integration is evident.
5. **Unvalidated User Input**: VIOLATION | Dialogue text (line 1216) is passed to TTS engines and `ffmpeg` commands (line 795) without sanitization. Malicious input (e.g., shell injection in filenames or text) could exploit subprocess calls.

---

### SECTION 4: FRONTEND QUALITY
Not applicable. This file (`tts_eng

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### 1) Provider selection / preflight
- `generate_dialogue_audio()` chooses provider via `_get_tts_provider()` and runs either `tts_preflight_local()` or checks for ElevenLabs key first (`1199-1206`).
- This is directionally correct, but there are correctness issues:
  - **Preflight is incomplete for actual host 2 path**. `tts_preflight_local()` only validates Kokoro host1 (`974-980`) and merely logs F5 status (`985-990`). It does **not** validate host2 primary (`am_onyx`) or fallback chain. So local preflight can pass while host2 is broken in production.
  - Comment drift: preflight warning says host2 uses `Kokoro am_adam` (`990`) but config says `am_onyx` (`180`). That’s a sign the code path and operational assumptions are out of sync.

#### 2) Silence gap generation
- The feature claims “fix-silence-gaps” and the file says it “Generates per-line audio with 0.3s silence gaps” (`6`, `260`, `1207-1208`, `1281-1285`).
- The implementation **does add a 0.3s silence file between non-CLIP entries**, but:
  - It adds the gap between **all adjacent spoken lines**, not specifically “between speakers” as the comment says (`1281-1285`). If host1 speaks twice in a row, it still inserts a gap. That may be intended, but the comment is inaccurate.
  - It does **not** add a gap before or after `CLIP` entries, while `CLIP` entries still advance timeline (`1218-1231`). Depending on downstream assembler behavior, this can create timing discontinuities between spoken audio and clip segments.

#### 3) Per-line TTS generation
- For each dialogue line, it computes `host_num`, output path, and calls either `tts_local()` or `tts_elevenlabs()` (`1233-1249`).
- Major correctness issues:
  1. **Fatal contradiction: “silence fallback no longer allowed” is not true.**
     - `_tts_generate_silence_fallback()` explicitly raises to prevent silent renders (`756-767`).
     - But `generate_dialogue_audio()` catches any `_tts_ok == False` and writes **3 seconds of silence anyway** (`1259-1267`).
     - This directly defeats the stated hard-fail policy and can still produce garbage renders.
  2. **Per-host validation is ineffective.**
     - `host_stats["ok"]` increments if the path exists (`1325-1326`), not if TTS truly succeeded.
     - Since failed lines are replaced with generated silence files (`1260-1267`), those files exist, so they count as “ok”.
     - Result: the “silent host” guard can pass even when every line for a host is synthetic silence.
  3. **`dur` can be undefined in edge cases.**
     - In the success branch, `dur` is only assigned in `1255`.
     - If `_tts_ok` is `True`, file exists, size >= 1000, and `len(text) <= 10`, then the `dur < 0.5` check is skipped and `dur` may still be uninitialized before appending to `lines` (`1269-1273`).
     - Example: very short valid text like “Yes.” could trigger this.
  4. **Validation exceptions can crash unexpectedly.**
     - `tts_local()` calls `validate_tts_output(output_path)` without wrapping it (`958-961`).
     - `tts_elevenlabs()` does the same in both single and multi-chunk paths (`1152-1156`, `1176-1179`).
     - These functions return `bool`, but can actually raise `RuntimeError`, which is inconsistent with their interface and can abort the whole loop unexpectedly.

#### 4) Local TTS path
- `tts_local()` normalizes text, checks cache, then:
  - host1: Kokoro -> ElevenLabs fallback (`943-947`)
  - host2: Kokoro -> F5 -> ElevenLabs fallback (`948-956`)
- Problems:
  1. **Comments do not match implementation.**
     - Docstring says host2 is `Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX fallback` (`917-918`).
     - Actual code is `Kokoro am_onyx -> F5 -> ElevenLabs` (`949-956`).
     - `tts_chatterbox()` exists but is never used (`813-855`).
  2. **Global lazy init is not thread-safe.**
     - `_KOKORO_*`, `_F5_MODEL`, `_BIGVGAN_MODEL`, `_CHATTERBOX_MODEL`, `_KEY_CACHE`, `_PROSODY_CACHE` are module globals (`21-27`, `215`).
     - Under concurrent requests, multiple threads/processes can race during initialization and cache writes. At best this wastes resources; at worst it can corrupt state or double-load huge GPU models.
  3. **`sys.path` mutation per request is dangerous.**
     - `tts_local()` mutates `sys.path` dynamically (`927-930`).
     - In a multi-threaded server this is global process state and not safe as request-time behavior.

#### 5) ElevenLabs path
- `tts_elevenlabs()` chunks text, retries requests, writes MP3 chunks, concatenates, converts to M4A, validates, caches (`1047-1180`).
- Good: timeouts exist (`1036`, `1110`), retries exist (`1107-1133`).
- Problems:
  1. **Docstring is false.**
     - Says it “Falls back to pyttsx3 system TTS, then silence” (`1053`), but pyttsx3 is nowhere present; it raises fatal via `_tts_generate_silence_fallback()` (`1055-1062`).
  2. **No rate limiting / quota protection at application level.**
     - With ~1000 concurrent users, one burst can hammer ElevenLabs a

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — FIX-SILENCE-GAPS — CYCLE 1
Generated: 2026-03-22 16:21
Models: grok, gpt4o (+1 failed — Gemini 2.5 Pro, API key leaked/revoked)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | ❌ N/A | 58/100 | 75/100 | **66/100** |
| Frontend/UI | ❌ N/A | N/A | N/A | **N/A** |
| Error Handling | ❌ N/A | 40/100 | 60/100 | **50/100** |
| Security | ❌ N/A | 45/100 | 50/100 | **47/100** |
| Performance | ❌ N/A | 45/100 | 55/100 | **50/100** |
| Law Compliance | ❌ N/A | 65/100 | 40/100 | **52/100** |
| **Overall** | ❌ N/A | **51/100** | **55/100** | **53/100** |

> ⚠️ **Scoring confidence is reduced.** Gemini failed (403 — leaked API key). Scores are derived from 2 of 3 models. The consensus average skews optimistic compared to what a 3-model agreement would likely produce. Treat the 53/100 overall as a ceiling, not a floor.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — Silence Fallback Defeats Its Own Hard-Fail Policy
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 756–767, 1259–1267
**What it is:** `_tts_generate_silence_fallback()` raises an exception explicitly to prevent silent renders. However, `generate_dialogue_audio()` catches `_tts_ok == False` and writes 3 seconds of silence *anyway*, completely nullifying the guard.
**What to change:** Remove the silence-write fallback block at lines 1259–1267 entirely. On TTS failure, either raise immediately (hard-fail) or enqueue a retry — do not generate synthetic silence and continue. The current behavior guarantees corrupted podcast episodes reach downstream render with no warning.

---

### U2 — Non-Atomic Cache Writes Allow Race Conditions and Corrupt Reads
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 729–754 (`_tts_cache_get`, `_tts_cache_put`)
**What it is:** Cache writes copy files directly without locking. Under concurrent requests, two writers can race producing partial files; a reader can copy a half-written file and serve corrupted audio for the lifetime of the cache entry.
**What to change:** Write to a `.tmp` file first, then `os.replace()` (atomic on POSIX). Add a per-key `threading.Lock()` or use `fcntl.flock()` around the critical section. At minimum: write-to-temp + atomic rename.

---

### U3 — ffmpeg Subprocess Return Codes Routinely Ignored
**File:** `video_pipeline_v3/tts_engine.py` | **Lines:** 226–235, 1164–1168, 1294–1298
**What it is:** Both models independently flagged that ffmpeg/ffprobe subprocess calls do not check return codes before downstream operations consume their output. A failed ffmpeg concat at line 1294 still produces a `full_path` reference in the returned metadata; `_mp3_to_m4a()` at line 1169 receives a nonexistent input after a failed concat at 1164–1168.
**What to change:** After every `subprocess.run()` call involving ffmpeg/ffprobe: check `returncode != 0`, log stderr, and raise or return a structured failure. Never pass ffmpeg

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: video_pipeline_v3/tts_engine.py (1368 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V10 — Dual-host local TTS pipeline.
   3 | Host 1: Kokoro af_heart (female) — setup/bridge.
   4 | Host 2: Kokoro am_onyx (male) — react/wrap. F5-TTS PBX when ready.
   5 | Fallback: ElevenLabs per-line. TTS_PROVIDER=local (default) or elevenlabs.
   6 | Generates per-line audio with 0.3s silence gaps."""
   7 | import os, sys, json, subprocess, tempfile, time, struct, shutil, logging, re
   8 | from pathlib import Path
   9 | 
  10 | try:
  11 |     import requests
  12 |     HAS_REQUESTS = True
  13 | except ImportError:
  14 |     HAS_REQUESTS = False
  15 | 
  16 | from relay import get_key
  17 | 
  18 | logger = logging.getLogger(__name__)
  19 | 
  20 | # ── LOCAL TTS BACKENDS ──────────────────────────────────────────────────────
  21 | _KOKORO_PIPELINE = None
  22 | _KOKORO_BACKEND = None
  23 | _KOKORO_INSTANCE = None
  24 | _F5_MODEL = None
  25 | _BIGVGAN_MODEL = None
  26 | _CHATTERBOX_MODEL = None
  27 | _PROSODY_CACHE = {}  # hash(text) -> prosody-planned text
  28 | 
  29 | 
  30 | def _init_kokoro():
  31 |     """Lazy-initialize Kokoro (PyTorch first, ONNX fallback)."""
  32 |     global _KOKORO_PIPELINE, _KOKORO_BACKEND, _KOKORO_INSTANCE
  33 |     if _KOKORO_BACKEND is not None:
  34 |         return _KOKORO_BACKEND
  35 |     try:
  36 |         from kokoro import KPipeline
  37 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
  38 |         _KOKORO_BACKEND = "pytorch"
  39 |         logger.info("[TTS/Kokoro] Backend: PyTorch")
  40 |         return "pytorch"
  41 |     except Exception as e_pt:
  42 |         logger.warning(f"[TTS/Kokoro] PyTorch failed: {e_pt} — trying ONNX")
  43 |     try:
  44 |         from kokoro_onnx import Kokoro as _KokoroONNX
  45 |         _VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
  46 |         _onnx_model = os.path.join(_VOICES_DIR, "kokoro-v0_19.onnx")
  47 |         _onnx_voices = os.path.join(_VOICES_DIR, "voices-v1.0.bin")
  48 |         if not os.path.exists(_onnx_model):
  49 |             logger.info("[TTS/Kokoro] Downloading ONNX model files...")
  50 |             subprocess.run([
  51 |                 "python3", "-c",
  52 |                 "from huggingface_hub import hf_hub_download; "
  53 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'kokoro-v0_19.onnx', local_dir='{_VOICES_DIR}'); "
  54 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'voices-v1.0.bin', local_dir='{_VOICES_DIR}')"
  55 |             ], timeout=300)
  56 |         _KOKORO_INSTANCE = _KokoroONNX(_onnx_model, _onnx_voices)
  57 |         _KOKORO_BACKEND = "onnx"
  58 |         logger.info("[TTS/Kokoro] Backend: ONNX")
  59 |         return "onnx"
  60 |     except Exception as e_onnx:
  61 |         logger.error(f"[TTS/Kokoro] Both backends failed: {e_onnx}")
  62 |         _KOKORO_BACKEND = "unavailable"
  63 |         return "unavailable"
  64 | 
  65 | 
  66 | def _init_f5():
  67 |     """Lazy-initialize fine-tuned F5-TTS model."""
  68 |     global _F5_MODEL
  69 |     if _F5_MODEL is not None:
  70 |         return True
  71 |     ckpt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "pbx_voice.pt")
  72 |     if not os.path.exists(ckpt):
  73 |         logger.warning(f"[TTS/F5] Fine-tuned checkpoint missing: {ckpt}")
  74 |         return False
  75 |     try:
  76 |         from f5_tts.api import F5TTS
  77 |         _F5_MODEL = F5TTS(model="F5TTS_v1_Base", ckpt_file=ckpt, device="cuda:1")
  78 |         logger.info(f"[TTS/F5] Fine-tuned model loaded: {ckpt}")
  79 |         return True
  80 |     except Exception as e:
  81 |         logger.error(f"[TTS/F5] Failed to load checkpoint: {e}")
  82 |         return False
  83 | 
  84 | 
  85 | def _init_chatterbox():
  86 |     """Lazy-initialize Chatterbox TTS on cuda:0."""
  87 |     global _CHATTERBOX_MODEL
  88 |     if _CHATTERBOX_MODEL is not None:
  89 |         return True
  90 |     try:
  91 |         from chatterbox.tts import ChatterboxTTS
  92 |         _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device="cuda:0")
  93 |         logger.info("[TTS/Chatterbox] Model loaded on cuda:0")
  94 |         return True
  95 |     except Exception as e:
  96 |         logger.error(f"[TTS/Chatterbox] Failed to load: {e}")
  97 |         return False
  98 | 
  99 | 
 100 | def _init_bigvgan():
 101 |     """Lazy-initialize BigVGAN2 44kHz vocoder on cuda:1."""
 102 |     global _BIGVGAN_MODEL
 103 |     if _BIGVGAN_MODEL is not None:
 104 |         return True
 105 |     try:
 106 |         import bigvgan as _bv
 107 |         _BIGVGAN_MODEL = _bv.BigVGAN.from_pretrained(
 108 |             "nvidia/bigvgan_v2_44khz_128band_512x",
 109 |             use_cuda_kernel=False,
 110 |         )
 111 |         _BIGVGAN_MODEL = _BIGVGAN_MODEL.eval().to("cuda:1")
 112 |         logger.info("[TTS/BigVGAN2] 44kHz vocoder loaded on cuda:1")
 113 |         return True
 114 |     except Exception as e:
 115 |         logger.error(f"[TTS/BigVGAN2] Init failed: {e}")
 116 |         return False
 117 | 
 118 | 
 119 | def _bigvgan_upsample(wav_path_24k: str) -> str:
 120 |     """Upsample 24kHz WAV to 44kHz via BigVGAN2. Returns path to 44kHz WAV.
 121 |     Graceful fallback: returns original path if BigVGAN2 fails."""
 122 |     if not _init_bigvgan():
 123 |         return wav_path_24k
 124 |     try:
 125 |         import torch
 126 |         import soundfile as sf
 127 |         import librosa
 128 |         wav_data, sr = sf.read(wav_path_24k)
 129 |         if sr != 24000:
 130 |             wav_data = librosa.resample(wav_data, orig_sr=sr, target_sr=24000)
 131 |         # BigVGAN expects mel spectrogram input — compute from audio
 132 |         import torchaudio
 133 |         wav_tensor = torch.FloatTensor(wav_data).unsqueeze(0).to("cuda:1")
 134 |         # Use torchaudio to compute mel spectrogram matching BigVGAN's expected input
 135 |         mel_transform = torchaudio.transforms.MelSpectrogram(
 136 |             sample_rate=24000, n_fft=2048, hop_length=256, n_mels=128,
 137 |             f_min=0, f_max=12000,
 138 |         ).to("cuda:1")
 139 |         mel = mel_transform(wav_tensor)
 140 |         mel = torch.log(torch.clamp(mel, min=1e-5))
 141 |         with torch.inference_mode():
 142 |             wav_out = _BIGVGAN_MODEL(mel)
 143 |         wav_np = wav_out.squeeze().cpu().numpy()
 144 |         out_path = wav_path_24k.replace(".wav", ".44k.wav")
 145 |         sf.write(out_path, wav_np, 44100)
 146 |         logger.info(f"[TTS/BigVGAN2] Upsampled {wav_path_24k} → {out_path}")
 147 |         return out_path
 148 |     except Exception as e:
 149 |         logger.warning(f"[TTS/BigVGAN2] Upsample failed: {e} — using 24kHz")
 150 |         return wav_path_24k
 151 | 
 152 | 
 153 | def prosody_plan(text: str, host: int = 2) -> str:
 154 |     """Strip all [bracket] prosody markers and return clean text.
 155 |     Prosody injection disabled — markers caused TTS artifacts."""
 156 |     import re
 157 |     return re.sub(r'\[.*?\]', '', text).strip()
 158 | 
 159 | 
 160 | PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"
 161 | 
 162 | _PBX_VOICE = {
 163 |     "voice_id": PBX_VOICE_ID,
 164 |     "name": "PBX",
 165 |     "model_id": "eleven_multilingual_v2",
 166 |     "speed": 1.0,  # Multilingual v2: natural broadcast pace, no speedup needed
 167 |     "voice_settings": {
 168 |         "stability": 0.50,
 169 |         "similarity_boost": 0.85,
 170 |         "style": 0.30,
 171 |         "use_speaker_boost": True,
 172 |     },
 173 | }
 174 | 
 175 | # ── LOCAL TTS VOICE CONFIG ──────────────────────────────────────────────────
 176 | VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
 177 | PBX_CHECKPOINT = "/home/ultron/.local/lib/python3.10/ckpts/pbx_voice/model_500.pt"  # PBX voice model_500
 178 | PBX_REFERENCE_CLIP = os.path.join(VOICES_DIR, "pbx_reference.wav")
 179 | KOKORO_HOST1_VOICE = "af_heart"
 180 | KOKORO_HOST2_VOICE = "am_onyx"   # primary; swap for PBX F5 when ready
 181 | F5_SPEED = 1.1
 182 | KOKORO_SPEED_H1 = 1.0
 183 | KOKORO_SPEED_H2 = 1.1
 184 | 
 185 | _ERYN_VOICE = {
 186 |     "voice_id": "kdnRe2koJdOK4Ovxn2DI",
 187 |     "name": "Eryn",
 188 |     "model_id": "eleven_turbo_v2_5",
 189 |     "speed": 1.0,
 190 |     "voice_settings": {
 191 |         "stability": 0.55,
 192 |         "similarity_boost": 0.80,
 193 |         "style": 0.15,
 194 |         "use_speaker_boost": True,
 195 |     },
 196 | }
 197 | # Dual-host: HOST_1 = Eryn/af_heart (female), HOST_2 = PBX (fine-tuned F5 / ElevenLabs fallback)
 198 | VOICES = {
 199 |     1: _ERYN_VOICE,
 200 |     2: _PBX_VOICE,
 201 | }
 202 | 
 203 | def _get_tts_provider() -> str:
 204 |     """TTS provider selector.
 205 |     'local'      → Kokoro af_heart (host1) + Chatterbox PBX (host2) + ElevenLabs fallback
 206 |     'elevenlabs' → ElevenLabs only (emergency override, preserves single-host Option A)
 207 |     """
 208 |     val = os.environ.get("TTS_PROVIDER", "local").lower().strip()
 209 |     if val not in ("local", "elevenlabs"):
 210 |         logger.warning(f"[TTS] Unknown TTS_PROVIDER='{val}', defaulting to 'local'")
 211 |         return "local"
 212 |     return val
 213 | 
 214 | 
 215 | _KEY_CACHE: dict = {}
 216 | 
 217 | def _get_cached_key(name: str) -> str:
 218 |     if name not in _KEY_CACHE:
 219 |         k = get_key(name)
 220 |         if k:
 221 |             _KEY_CACHE[name] = k.strip()
 222 |     return _KEY_CACHE.get(name, "")
 223 | 
 224 | 
 225 | def ffprobe_duration(path: str) -> float:
 226 |     r = subprocess.run(
 227 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 228 |          "-of", "csv=p=0", path],
 229 |         capture_output=True, text=True,
 230 |     )
 231 |     try:
 232 |         return float(r.stdout.strip())
 233 |     except Exception:
 234 |         logger.warning(f"[TTS] ffprobe_duration failed for {path}")
 235 |         return -1.0
 236 | 
 237 | 
 238 | def _generate_silence(output_path: str, duration: float) -> bool:
 239 |     """Generate a silent audio file."""
 240 |     r = subprocess.run(
 241 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
 242 |          f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
 243 |          "-c:a", "aac", "-b:a", "192k", output_path],
 244 |         capture_output=True, text=True, timeout=30,
 245 |     )
 246 |     return r.returncode == 0 and os.path.exists(output_path)
 247 | 
 248 | 
 249 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 250 |     # eleven_multilingual_v2 at speed=1.0 — no atempo needed (natural broadcast pace)
 251 |     r = subprocess.run(
 252 |         ["ffmpeg", "-y", "-i", mp3_path,
 253 |          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
 254 |         capture_output=True, text=True, timeout=120,
 255 |     )
 256 |     return r.returncode == 0 and os.path.exists(m4a_path)
 257 | 
 258 | 
 259 | MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
 260 | SILENCE_GAP = 0.3  # seconds between speakers
 261 | 
 262 | # Voice mode overrides per segment type (applied to whichever host speaks)
 263 | VOICE_MODES = {
 264 |     "cold_open":       {"stability": 0.42, "similarity_boost": 0.85, "style": 0.35},
 265 |     "setup":           {"stability": 0.50, "similarity_boost": 0.85, "style": 0.30},
 266 |     "react":           {"stability": 0.48, "similarity_boost": 0.85, "style": 0.32},
 267 |     "bridge":          {"stability": 0.50, "similarity_boost": 0.85, "style": 0.28},
 268 |     "social_segment":  {"stability": 0.48, "similarity_boost": 0.85, "style": 0.32},
 269 |     "wrap":            {"stability": 0.45, "similarity_boost": 0.85, "style": 0.35},
 270 | }
 271 | 
 272 | 
 273 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 274 |     if len(text) <= max_chars:
 275 |         return [text]
 276 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 277 |     sentences = raw.split("\x00")
 278 |     chunks, current = [], ""
 279 |     for sent in sentences:
 280 |         if len(current) + len(sent) + 1 <= max_chars:
 281 |             current = f"{current} {sent}".strip() if current else sent
 282 |         else:
 283 |             if current:
 284 |                 chunks.append(current)
 285 |             current = sent
 286 |     if current:
 287 |         chunks.append(current)
 288 |     return [c for c in chunks if c.strip()]
 289 | 
 290 | 
 291 | def expand_numbers_for_tts(text: str) -> str:
 292 |     """Round 2 Fix 1: Full num2words preprocessing — converts ALL numbers >999 to spoken form.
 293 | 
 294 |     Previous version used manual thousand/million/billion templates which caused garbled
 295 |     speech on numbers like "1,056 EH/s" or "$74,000". Now uses num2words for natural
 296 |     spoken-word output: "$74,000" → "seventy-four thousand dollars".
 297 |     """
 298 |     import re as _re
 299 |     try:
 300 |         from num2words import num2words as _n2w
 301 |     except ImportError:
 302 |         logger.warning("[TTS] num2words not installed — falling back to basic expansion")
 303 |         return _expand_numbers_basic(text)
 304 | 
 305 |     # Issue 12: Year detection BEFORE general number expansion
 306 |     # 4-digit numbers 1600-2099 not preceded by $ or currency → spoken as years
 307 |     def _year_to_words(y: int) -> str:
 308 |         """Convert year number to spoken form: 1602→sixteen oh two, 2024→twenty twenty-four."""
 309 |         if 2000 <= y <= 2009:
 310 |             return f"two thousand {_n2w(y - 2000) if y > 2000 else ''}".strip()
 311 |         if 2010 <= y <= 2099:
 312 |             return f"twenty {_n2w(y - 2000)}"
 313 |         hi = y // 100
 314 |         lo = y % 100
 315 |         hi_word = _n2w(hi)
 316 |         if lo == 0:
 317 |             return f"{hi_word} hundred"
 318 |         elif lo < 10:
 319 |             return f"{hi_word} oh {_n2w(lo)}"
 320 |         else:
 321 |             return f"{hi_word} {_n2w(lo)}"
 322 | 
 323 |     def _year_sub(m):
 324 |         val = int(m.group(0))
 325 |         return _year_to_words(val)
 326 |     # Match 1600-2099 NOT preceded by $ or digits
 327 |     text = _re.sub(r'(?<!\$)(?<!\d)\b(1[6-9]\d{2}|20[0-9]\d)\b(?!\s*(?:EH|TH|PH|dollars|percent|%|K\b))', _year_sub, text)
 328 | 
 329 |     # Dollar + billion/million shorthand first: $308 billion → "three hundred and eight billion dollars"
 330 |     def _dollar_scale(m):
 331 |         num_str = m.group(1)
 332 |         scale = m.group(2).lower()
 333 |         try:
 334 |             val = float(num_str)
 335 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 336 |             return f"{spoken} {scale} dollars"
 337 |         except Exception:
 338 |             return m.group(0)
 339 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _dollar_scale, text)
 340 | 
 341 |     # Dollar amounts: $74,000 → "seventy-four thousand dollars"
 342 |     def _dollar(m):
 343 |         val_str = m.group(1).replace(",", "")
 344 |         try:
 345 |             val = int(float(val_str))
 346 |             if val > 999:
 347 |                 return f"{_n2w(val)} dollars"
 348 |             return f"{val} dollars"
 349 |         except Exception:
 350 |             return m.group(0)
 351 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 352 | 
 353 |     # Hashrate units BEFORE plain numbers (so "1,056 EH/s" is caught here)
 354 |     def _hashrate(m):
 355 |         val_str = m.group(1).replace(",", "")
 356 |         unit = m.group(2)
 357 |         unit_map = {"EH": "exahashes", "TH": "terahashes", "PH": "petahashes"}
 358 |         try:
 359 |             val = float(val_str)
 360 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 361 |             return f"{spoken} {unit_map.get(unit, unit)} per second"
 362 |         except Exception:
 363 |             return m.group(0)
 364 |     text = _re.sub(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(EH|TH|PH)/?s', _hashrate, text)
 365 | 
 366 |     # Percentages: 42% → "forty-two percent"
 367 |     def _pct(m):
 368 |         val_str = m.group(1)
 369 |         try:
 370 |             val = float(val_str)
 371 |             if val == int(val):
 372 |                 return f"{_n2w(int(val))} percent"
 373 |             # 8.4% → "eight point four percent"
 374 |             whole = int(val)
 375 |             frac = val_str.split('.')[1] if '.' in val_str else ''
 376 |             if frac:
 377 |                 frac_spoken = ' '.join(_n2w(int(d)) for d in frac)
 378 |                 return f"{_n2w(whole)} point {frac_spoken} percent"
 379 |             return f"{_n2w(int(val))} percent"
 380 |         except Exception:
 381 |             return m.group(0)
 382 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 383 | 
 384 |     # Large plain numbers with commas: 70,015 → "seventy thousand and fifteen"
 385 |     def _plain_num(m):
 386 |         val_str = m.group(0).replace(",", "")
 387 |         try:
 388 |             val = int(val_str)
 389 |             if val > 999:
 390 |                 return _n2w(val)
 391 |             return m.group(0)
 392 |         except Exception:
 393 |             return m.group(0)
 394 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 395 | 
 396 |     # Billion/million shorthand in text (no dollar): 1.2 billion → "one point two billion"
 397 |     def _scale(m):
 398 |         val_str = m.group(1)
 399 |         scale = m.group(2).lower()
 400 |         try:
 401 |             val = float(val_str)
 402 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 403 |             return f"{spoken} {scale}"
 404 |         except Exception:
 405 |             return m.group(0)
 406 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _scale, text)
 407 | 
 408 |     # K shorthand: 74K → "seventy-four thousand"
 409 |     def _k(m):
 410 |         try:
 411 |             val = float(m.group(1))
 412 |             return _n2w(int(val * 1000))
 413 |         except Exception:
 414 |             return m.group(0)
 415 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 416 | 
 417 |     # Standalone large numbers without commas (e.g. 74000)
 418 |     def _bare_num(m):
 419 |         try:
 420 |             val = int(m.group(0))
 421 |             if val > 999:
 422 |                 return _n2w(val)
 423 |             return m.group(0)
 424 |         except Exception:
 425 |             return m.group(0)
 426 |     text = _re.sub(r'\b\d{4,}\b', _bare_num, text)
 427 | 
 428 |     # Issue 6: Strip commas and "and" from num2words output to prevent micro-pauses
 429 |     text = _re.sub(r'(\w),\s', r'\1 ', text)  # remove commas in spoken numbers
 430 |     text = _re.sub(r'\band\b\s*', '', text)  # remove "and" (e.g. "one hundred and fifty" → "one hundred fifty")
 431 |     text = _re.sub(r'\s{2,}', ' ', text)  # collapse double spaces
 432 | 
 433 |     return text
 434 | 
 435 | 
 436 | def _expand_numbers_basic(text: str) -> str:
 437 |     """Fallback number expansion without num2words (original logic)."""
 438 |     import re as _re
 439 | 
 440 |     def _dollar(m):
 441 |         val_str = m.group(1).replace(",", "")
 442 |         try:
 443 |             val = int(float(val_str))
 444 |         except ValueError:
 445 |             return m.group(0)
 446 |         if val >= 1_000_000_000:
 447 |             return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
 448 |         if val >= 1_000_000:
 449 |             return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
 450 |         if val >= 1_000:
 451 |             b = val // 1000
 452 |             r = val % 1000
 453 |             if r == 0:
 454 |                 return f"{b} thousand dollars"
 455 |             return f"{b} thousand {r} dollars"
 456 |         return f"{val} dollars"
 457 | 
 458 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
 459 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)
 460 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 461 | 
 462 |     def _plain_num(m):
 463 |         val_str = m.group(0).replace(",", "")
 464 |         try:
 465 |             val = int(val_str)
 466 |         except ValueError:
 467 |             return m.group(0)
 468 |         if val >= 1_000_000_000:
 469 |             return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
 470 |         if val >= 1_000_000:
 471 |             return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
 472 |         if val >= 10_000:
 473 |             b = val // 1000
 474 |             r = val % 1000
 475 |             if r == 0:
 476 |                 return f"{b} thousand"
 477 |             return f"{b} thousand {r}"
 478 |         return m.group(0)
 479 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 480 | 
 481 |     def _pct(m):
 482 |         return m.group(1).replace(".", " point ") + " percent"
 483 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 484 | 
 485 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
 486 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
 487 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)
 488 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
 489 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)
 490 | 
 491 |     def _k(m):
 492 |         val = float(m.group(1))
 493 |         if val == int(val):
 494 |             return f"{int(val)} thousand"
 495 |         return f"{val} thousand"
 496 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 497 | 
 498 |     return text
 499 | 
 500 | 
 501 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 502 | 
 503 | 
 504 | 
 505 | # ── Bitcoin Ecosystem Pronunciation Map ────────────────────────────────────
 506 | # ElevenLabs renders these phonetic substitutions naturally.
 507 | # Longer/more specific entries first to avoid partial replacements.
 508 | PRONUNCIATION_MAP = {
 509 |     # Satoshi
 510 |     "Satoshi Nakamoto": "sah TOE shee nah kah MOE toe",
 511 |     "Satoshi": "sah TOE shee",
 512 |     "Nakamoto": "nah kah MOE toe",
 513 |     # Saylor
 514 |     "Michael Saylor": "Michael Sayler",
 515 |     "Saylor": "Sayler",
 516 |     # Lyn Alden
 517 |     "Lyn Alden": "Lin AWL-den",
 518 |     # Lummis
 519 |     "Cynthia Lummis": "SIN-thee-ah LUM-iss",
 520 |     "Lummis": "LUM-iss",
 521 |     # Brunell
 522 |     "Natalie Brunell": "Natalie Brunelle",
 523 |     "Brunell": "Brunelle",
 524 |     # Preston Pysh
 525 |     "Preston Pysh": "Preston PISH",
 526 |     "Pysh": "PISH",
 527 |     # Max Keiser
 528 |     "Max Keiser": "MAX KY-zer",
 529 |     "Keiser": "KY-zer",
 530 |     # Nayib Bukele
 531 |     "Nayib Bukele": "NYE-eeb boo-KEH-leh",
 532 |     "Bukele": "boo-KEH-leh",
 533 |     # Saifedean Ammous
 534 |     "Saifedean Ammous": "sy-feh-DEAN AH-moos",
 535 |     "Saifedean": "sy-feh-DEAN",
 536 |     "Ammous": "AH-moos",
 537 |     # Robert Breedlove
 538 |     "Robert Breedlove": "Robert BREED love",
 539 |     "Breedlove": "BREED love",
 540 |     # Alex Gladstein
 541 |     "Alex Gladstein": "AL-ex GLAD-steen",
 542 |     "Gladstein": "GLAD-steen",
 543 |     # Knut Svanholm
 544 |     "Knut Svanholm": "kuh-NOOT SVAHN-holm",
 545 |     "Svanholm": "SVAHN-holm",
 546 |     # Luke Dashjr
 547 |     "Luke Dashjr": "LUKE DASH-junior",
 548 |     "Dashjr": "DASH-junior",
 549 |     # Andreas Antonopoulos
 550 |     "Andreas Antonopoulos": "ahn-DRAY-us an-TON-oh-POO-lus",
 551 |     "Antonopoulos": "an-TON-oh-POO-lus",
 552 |     "Andreas": "ahn-DRAY-us",
 553 |     # Charlie Shrem
 554 |     "Charlie Shrem": "CHAR-lee SHREM",
 555 |     "Shrem": "SHREM",
 556 |     # Lawrence Lepard
 557 |     "Lawrence Lepard": "LAW-rents leh-PARD",
 558 |     "Larry Lepard": "LAIR-ee leh-PARD",
 559 |     "Lepard": "leh-PARD",
 560 |     # Erik Voorhees
 561 |     "Erik Voorhees": "AIR-ik VOR-hees",
 562 |     "Voorhees": "VOR-hees",
 563 |     # Gabor Gurbacs
 564 |     "Gabor Gurbacs": "GAH-bor GUR-bacs",
 565 |     "Gurbacs": "GUR-bacs",
 566 |     # Gary Gensler
 567 |     "Gary Gensler": "GAIR-ee GENZ-ler",
 568 |     "Gensler": "GENZ-ler",
 569 |     # Jerome Powell
 570 |     "Jerome Powell": "jeh-ROME POW-ul",
 571 |     "Powell": "POW-ul",
 572 |     # CJ Konstantinos
 573 |     "CJ Konstantinos": "see-JAY kon-stan-TEE-nos",
 574 |     "Konstantinos": "kon-stan-TEE-nos",
 575 |     # Bob Iaccino
 576 |     "Bob Iaccino": "BOB ee-ah-CHEE-no",
 577 |     "Iaccino": "ee-ah-CHEE-no",
 578 |     # Alex Stanczyk
 579 |     "Alex Stanczyk": "AL-ex STAN-chik",
 580 |     "Stanczyk": "STAN-chik",
 581 |     # Matt Odell
 582 |     "Matt Odell": "MAT OH-dell",
 583 |     "Odell": "OH-dell",
 584 |     # Marty Bent
 585 |     "Marty Bent": "MAR-tee BENT",
 586 |     # Willy Woo
 587 |     "Willy Woo": "WIL-ee WOO",
 588 |     # Technical terms
 589 |     "EH/s": "exahashes per second",
 590 |     "TH/s": "terahashes per second",
 591 |     "PH/s": "petahashes per second",
 592 |     "UTXO": "you-tee-ex-oh",
 593 |     "HODL": "HODDLE",
 594 |     "blockchain": "blockchain",
 595 |     "halving": "HAV-ing",
 596 |     "SegWit": "SEG-wit",
 597 |     "Segwit": "SEG-wit",
 598 |     "hodl": "HODDLE",
 599 |     "mempool": "mem-pool",
 600 |     "multisig": "MUL-tee-sig",
 601 |     "satoshis": "sah-TOH-sheez",
 602 |     "MicroStrategy": "MY-crow-STRAT-uh-jee",
 603 |     "Coinbase": "KOYN-base",
 604 |     "Binance": "BY-nance",
 605 |     "Chainalysis": "CHAIN-uh-LY-sis",
 606 |     # Issue 10: BTC → Bitcoin spoken form
 607 |     "BTC": "Bitcoin",
 608 | }
 609 | 
 610 | 
 611 | def _expand_handle(handle: str) -> str:
 612 |     """Issue 11: Convert @handle to spoken form.
 613 |     CamelCase → separate words, underscores → spaces, ALL CAPS → spelled out."""
 614 |     import re as _re
 615 |     name = handle.lstrip("@")
 616 |     # ALL CAPS (like TFTC, WBD) → spelled out with dashes
 617 |     if name.isupper() and len(name) <= 6:
 618 |         return "at " + "-".join(name)
 619 |     # Split camelCase: MaxKeiser → Max Keiser
 620 |     name = _re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
 621 |     # Split underscores
 622 |     name = name.replace("_", " ")
 623 |     return "at " + name
 624 | 
 625 | 
 626 | # Known handles with correct spoken forms
 627 | _HANDLE_PRONUNCIATIONS = {
 628 |     "@maxkeiser": "at Max Kaiser",
 629 |     "@prestopysh": "at Preston Pish",
 630 |     "@tftc": "at T-F-T-C",
 631 |     "@wbd": "at W-B-D",
 632 |     "@saborchain": "at Sabor Chain",
 633 | }
 634 | 
 635 | 
 636 | _ORDINAL_MAP = {
 637 |     "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
 638 |     "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
 639 |     "9th": "ninth", "10th": "tenth", "11th": "eleventh", "12th": "twelfth",
 640 |     "13th": "thirteenth", "14th": "fourteenth", "15th": "fifteenth",
 641 |     "16th": "sixteenth", "17th": "seventeenth", "18th": "eighteenth",
 642 |     "19th": "nineteenth", "20th": "twentieth", "21st": "twenty-first",
 643 |     "22nd": "twenty-second", "23rd": "twenty-third", "24th": "twenty-fourth",
 644 |     "25th": "twenty-fifth", "26th": "twenty-sixth", "27th": "twenty-seventh",
 645 |     "28th": "twenty-eighth", "29th": "twenty-ninth", "30th": "thirtieth",
 646 |     "31st": "thirty-first",
 647 | }
 648 | 
 649 | 
 650 | def _expand_ordinals(text: str) -> str:
 651 |     """Pre-process ordinal numbers (e.g. '27th') to spoken form to prevent TTS splitting."""
 652 |     import re as _re
 653 |     def _ordinal_sub(m):
 654 |         key = m.group(0).lower()
 655 |         return _ORDINAL_MAP.get(key, m.group(0))
 656 |     return _re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', _ordinal_sub, text, flags=_re.IGNORECASE)
 657 | 
 658 | 
 659 | def apply_pronunciation_map(text: str) -> str:
 660 |     """Replace names/terms with phonetic versions ElevenLabs renders correctly.
 661 |     Processes longer entries first to avoid partial replacements."""
 662 |     import re
 663 |     # Pre-process ordinals before pronunciation map
 664 |     text = _expand_ordinals(text)
 665 |     # Issue 11: Pre-process @handles before pronunciation map
 666 |     def _handle_sub(m):
 667 |         raw = m.group(0).lower()
 668 |         if raw in _HANDLE_PRONUNCIATIONS:
 669 |             return _HANDLE_PRONUNCIATIONS[raw]
 670 |         return _expand_handle(m.group(0))
 671 |     text = re.sub(r'@[A-Za-z0-9_]+', _handle_sub, text)
 672 | 
 673 |     # Sort by length descending so longer matches take priority
 674 |     for written, phonetic in sorted(PRONUNCIATION_MAP.items(), key=lambda x: -len(x[0])):
 675 |         # Word-boundary aware replacement (case-insensitive)
 676 |         pattern = re.compile(r'\b' + re.escape(written) + r'\b', re.IGNORECASE)
 677 |         text = pattern.sub(phonetic, text)
 678 |     return text
 679 | 
 680 | 
 681 | def _trim_trailing_silence(audio_path: str) -> None:
 682 |     """Round 2 Fix 2: Trim trailing silence/vowel-stretch from TTS output.
 683 | 
 684 |     Detects if the last 0.5s is significantly quieter than the body (trailing off)
 685 |     and trims it to avoid the stretched-vowel artifact common in ElevenLabs output.
 686 |     """
 687 |     try:
 688 |         import re as _re
 689 |         # Measure RMS of last 0.5s vs body
 690 |         result = subprocess.run(
 691 |             ["ffmpeg", "-i", audio_path, "-af",
 692 |              "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
 693 |             capture_output=True, text=True, timeout=15,
 694 |         )
 695 |         # Find silence at end of file
 696 |         dur = ffprobe_duration(audio_path)
 697 |         if dur <= 1.0:
 698 |             return
 699 |         silences = [float(m.group(1)) for m in
 700 |                     _re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
 701 |         if not silences:
 702 |             return
 703 |         last_silence = silences[-1]
 704 |         # If silence starts within last 0.5s, trim there
 705 |         if dur - last_silence <= 0.5 and last_silence > dur * 0.8:
 706 |             trimmed = audio_path + ".trimmed.m4a"
 707 |             trim_ok = subprocess.run(
 708 |                 ["ffmpeg", "-y", "-i", audio_path,
 709 |                  "-t", f"{last_silence + 0.05:.3f}",
 710 |                  "-c:a", "aac", "-ar", "48000", "-b:a", "192k", trimmed],
 711 |                 capture_output=True, text=True, timeout=15,
 712 |             )
 713 |             if trim_ok.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
 714 |                 os.replace(trimmed, audio_path)
 715 |                 logger.info(f"[TTS] Trimmed trailing silence: {dur:.2f}s → {last_silence + 0.05:.2f}s")
 716 |             elif os.path.exists(trimmed):
 717 |                 os.remove(trimmed)
 718 |     except Exception as e:
 719 |         logger.debug(f"[TTS] Trailing silence trim skipped: {e}")
 720 | 
 721 | 
 722 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 723 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 724 |     import hashlib
 725 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 726 |     return hashlib.sha256(payload).hexdigest()[:16]
 727 | 
 728 | 
 729 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 730 |     """Return True if valid cached file exists and passes validation."""
 731 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 732 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
 733 |         shutil.copy2(cache_file, output_path)
 734 |         try:
 735 |             validate_tts_output(output_path)
 736 |             return True
 737 |         except RuntimeError:
 738 |             logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
 739 |             try:
 740 |                 os.remove(cache_file)
 741 |                 os.remove(output_path)
 742 |             except Exception:
 743 |                 pass
 744 |     return False
 745 | 
 746 | 
 747 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 748 |     """Save audio to TTS cache for future runs."""
 749 |     import shutil
 750 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 751 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 752 |     if not os.path.exists(cache_file):
 753 |         shutil.copy2(audio_path, cache_file)
 754 | 
 755 | 
 756 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 757 |     """HARD FAIL: silence fallback is no longer allowed.
 758 | 
 759 |     Previously generated silent AAC as a last resort, masking total TTS failure.
 760 |     This caused downstream black frames and F-grade renders that QC scored 94/100.
 761 |     Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
 762 |     """
 763 |     snippet = (text[:80] + "...") if len(text) > 80 else text
 764 |     raise RuntimeError(
 765 |         f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
 766 |         f"Text: \"{snippet}\". Fix the TTS provider before re-running."
 767 |     )
 768 | 
 769 | 
 770 | def tts_kokoro(text: str, output_path: str, voice: str = "af_heart",
 771 |                speed: float = 1.0) -> bool:
 772 |     """Generate TTS via Kokoro GPU inference. Output: M4A 48kHz AAC 192k."""
 773 |     backend = _init_kokoro()
 774 |     if backend == "unavailable":
 775 |         return False
 776 |     try:
 777 |         import soundfile as sf
 778 |         import numpy as np
 779 |         wav_tmp = output_path + ".kokoro.wav"
 780 |         if backend == "pytorch":
 781 |             samples_list = []
 782 |             for _, _, audio in _KOKORO_PIPELINE(text, voice=voice, speed=speed):
 783 |                 samples_list.append(audio)
 784 |             if not samples_list:
 785 |                 return False
 786 |             audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
 787 |             sf.write(wav_tmp, audio_np, 24000)
 788 |         else:
 789 |             samples, sr = _KOKORO_INSTANCE.create(text, voice=voice, speed=speed, lang="en-us")
 790 |             sf.write(wav_tmp, samples, sr)
 791 | 
 792 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 793 |             return False
 794 |         # Direct encode: 24kHz WAV → 48kHz AAC (no BigVGAN2 — causes double-vocoding)
 795 |         r = subprocess.run([
 796 |             "ffmpeg", "-y", "-i", wav_tmp,
 797 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 798 |         ], capture_output=True, text=True, timeout=60)
 799 |         try:
 800 |             if os.path.exists(wav_tmp):
 801 |                 os.remove(wav_tmp)
 802 |         except Exception:
 803 |             pass
 804 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 805 |         if ok:
 806 |             logger.info(f"[TTS/Kokoro] OK: {ffprobe_duration(output_path):.2f}s, voice={voice}")
 807 |         return ok
 808 |     except Exception as e:
 809 |         logger.error(f"[TTS/Kokoro] Exception: {e}")
 810 |         return False
 811 | 
 812 | 
 813 | def tts_chatterbox(text: str, output_path: str, exaggeration: float = 0.4,
 814 |                     cfg_weight: float = 0.5) -> bool:
 815 |     """Generate TTS using Chatterbox for PBX (Host 2).
 816 | 
 817 |     Chatterbox produces clean audio — no post-processing EQ needed.
 818 |     Output: M4A 48kHz AAC 192k.
 819 |     """
 820 |     if not _init_chatterbox():
 821 |         logger.warning("[TTS/Chatterbox] Model not loaded")
 822 |         return False
 823 | 
 824 |     try:
 825 |         import torchaudio
 826 |         wav_tmp = output_path + ".cb.wav"
 827 | 
 828 |         wav = _CHATTERBOX_MODEL.generate(text, exaggeration=exaggeration,
 829 |                                           cfg_weight=cfg_weight)
 830 |         torchaudio.save(wav_tmp, wav, 24000)
 831 | 
 832 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 833 |             logger.error("[TTS/Chatterbox] Zero output from inference")
 834 |             return False
 835 | 
 836 |         # Convert WAV to M4A (48kHz AAC 192k)
 837 |         r = subprocess.run([
 838 |             "ffmpeg", "-y", "-i", wav_tmp,
 839 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 840 |         ], capture_output=True, text=True, timeout=60)
 841 | 
 842 |         try:
 843 |             if os.path.exists(wav_tmp):
 844 |                 os.remove(wav_tmp)
 845 |         except Exception:
 846 |             pass
 847 | 
 848 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 849 |         if ok:
 850 |             logger.info(f"[TTS/Chatterbox] OK: {ffprobe_duration(output_path):.2f}s (PBX)")
 851 |         return ok
 852 |     except Exception as e:
 853 |         logger.error(f"[TTS/Chatterbox] Exception: {e}")
 854 |         return False
 855 | 
 856 | 
 857 | def tts_f5_finetuned(text: str, output_path: str, speed: float = None) -> bool:
 858 |     """Generate TTS using fine-tuned F5-TTS for PBX (Host 2).
 859 | 
 860 |     Uses pbx_voice.pt checkpoint with pbx_reference.wav for voice cloning.
 861 |     Output: M4A 48kHz AAC 192k.
 862 |     CRITICAL: show_info MUST be print or a callable — False crashes F5 (bool not callable).
 863 |     """
 864 |     if not _init_f5():
 865 |         logger.warning("[TTS/F5] Model not loaded")
 866 |         return False
 867 | 
 868 |     if not os.path.exists(PBX_REFERENCE_CLIP):
 869 |         logger.warning(f"[TTS/F5] Reference clip missing: {PBX_REFERENCE_CLIP}")
 870 |         return False
 871 | 
 872 |     if speed is None:
 873 |         speed = F5_SPEED
 874 | 
 875 |     try:
 876 |         import soundfile as sf
 877 |         wav_tmp = output_path + ".f5.wav"
 878 | 
 879 |         wav, sr, _ = _F5_MODEL.infer(
 880 |             ref_file=PBX_REFERENCE_CLIP,
 881 |             ref_text="",
 882 |             gen_text=text,
 883 |             speed=speed,
 884 |             show_info=print,
 885 |         )
 886 |         sf.write(wav_tmp, wav, sr)
 887 | 
 888 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 889 |             logger.error("[TTS/F5] Zero output from inference")
 890 |             return False
 891 | 
 892 |         # Convert WAV to M4A (48kHz AAC 192k)
 893 |         r = subprocess.run([
 894 |             "ffmpeg", "-y", "-i", wav_tmp,
 895 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 896 |         ], capture_output=True, text=True, timeout=60)
 897 | 
 898 |         try:
 899 |             if os.path.exists(wav_tmp):
 900 |                 os.remove(wav_tmp)
 901 |         except Exception:
 902 |             pass
 903 | 
 904 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 905 |         if ok:
 906 |             logger.info(f"[TTS/F5] OK: {ffprobe_duration(output_path):.2f}s (PBX fine-tuned)")
 907 |         return ok
 908 |     except Exception as e:
 909 |         logger.error(f"[TTS/F5] Exception: {e}")
 910 |         return False
 911 | 
 912 | 
 913 | def tts_local(text: str, output_path: str, host: int = 1,
 914 |               segment_type: str = "") -> bool:
 915 |     """Primary TTS dispatcher — local GPU inference with per-line ElevenLabs fallback.
 916 | 
 917 |     Host 1 → Kokoro af_heart → ElevenLabs Eryn fallback
 918 |     Host 2 → Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX fallback
 919 |     """
 920 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
 921 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
 922 |     text = expand_numbers_for_tts(text)
 923 |     text = apply_pronunciation_map(text)
 924 |     # Prosody planner: add natural delivery markers before TTS
 925 |     text = prosody_plan(text, host=host)
 926 |     try:
 927 |         _oracle_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oracle")
 928 |         if _oracle_path not in sys.path:
 929 |             sys.path.insert(0, _oracle_path)
 930 |         from oracle_dialogue_engine import normalize_pronunciation
 931 |         text = normalize_pronunciation(text)
 932 |     except Exception as _e:
 933 |         logger.warning(f"[TTS/Local] normalize_pronunciation unavailable: {_e}")
 934 | 
 935 |     cache_key = _tts_cache_key(text, f"local_h{host}", segment_type)
 936 |     if _tts_cache_get(cache_key, output_path):
 937 |         print(f"  [tts/local] Cache HIT (host{host}): {text[:50]}")
 938 |         return True
 939 | 
 940 |     start_t = time.time()
 941 |     ok = False
 942 | 
 943 |     if host == 1:
 944 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST1_VOICE, speed=KOKORO_SPEED_H1)
 945 |         if not ok:
 946 |             logger.warning("[TTS/Local] Kokoro host1 FAILED → ElevenLabs Eryn fallback")
 947 |             ok = tts_elevenlabs(text, output_path, host=1, segment_type=segment_type)
 948 |     else:
 949 |         # Kokoro am_onyx primary; F5-TTS PBX fallback when checkpoint confirmed ready
 950 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST2_VOICE, speed=KOKORO_SPEED_H2)
 951 |         if not ok:
 952 |             logger.warning("[TTS/Local] Kokoro am_onyx FAILED → F5-TTS fallback")
 953 |             ok = tts_f5_finetuned(text, output_path)
 954 |         if not ok:
 955 |             logger.warning("[TTS/Local] Kokoro host2 FAILED → ElevenLabs PBX fallback")
 956 |             ok = tts_elevenlabs(text, output_path, host=2, segment_type=segment_type)
 957 | 
 958 |     if ok and os.path.exists(output_path):
 959 |         _trim_trailing_silence(output_path)
 960 |         validate_tts_output(output_path)
 961 |         _tts_cache_put(cache_key, output_path)
 962 |         elapsed = time.time() - start_t
 963 |         dur = ffprobe_duration(output_path)
 964 |         print(f"  [tts/local] host{host} OK: {dur:.1f}s audio in {elapsed:.1f}s wall ← {text[:50]}")
 965 | 
 966 |     return ok
 967 | 
 968 | 
 969 | def tts_preflight_local() -> bool:
 970 |     """Preflight for TTS_PROVIDER=local: verify Kokoro works, report F5 status."""
 971 |     test_text = "Bitcoin signal confirmed today."
 972 |     test_out = "/tmp/tts_preflight_local.m4a"
 973 |     try:
 974 |         ok = tts_kokoro(test_text, test_out, voice=KOKORO_HOST1_VOICE, speed=1.0)
 975 |         if not ok or not os.path.exists(test_out):
 976 |             raise RuntimeError("[TTS/Local] Kokoro preflight failed to generate audio")
 977 |         dur = ffprobe_duration(test_out)
 978 |         if dur < 0.5:
 979 |             raise RuntimeError(f"[TTS/Local] Kokoro output too short: {dur:.2f}s")
 980 |         logger.info(f"[TTS/Local] Kokoro preflight PASS: {dur:.2f}s")
 981 |         try:
 982 |             os.remove(test_out)
 983 |         except Exception:
 984 |             pass
 985 |         if os.path.exists(PBX_CHECKPOINT) and os.path.exists(PBX_REFERENCE_CLIP):
 986 |             logger.info("[TTS/Local] F5 ready: checkpoint + reference clip")
 987 |         elif os.path.exists(PBX_CHECKPOINT):
 988 |             logger.warning(f"[TTS/Local] F5 checkpoint found but reference clip missing: {PBX_REFERENCE_CLIP}")
 989 |         else:
 990 |             logger.warning("[TTS/Local] F5 checkpoint missing — host2 using Kokoro am_adam")
 991 |         return True
 992 |     except Exception as e:
 993 |         raise RuntimeError(f"[TTS/Local] Preflight FAILED: {e}")
 994 | 
 995 | 
 996 | def validate_tts_output(path: str, min_size: int = 10240) -> None:
 997 |     """Validate TTS output file is real audio, not empty/corrupt.
 998 | 
 999 |     Raises RuntimeError if:
1000 |       - File doesn't exist
1001 |       - File < min_size bytes (10KB default)
1002 |       - ffprobe duration < 0.5s
1003 |     """
1004 |     if not os.path.exists(path):
1005 |         raise RuntimeError(f"TTS output missing: {path}")
1006 |     size = os.path.getsize(path)
1007 |     if size < min_size:
1008 |         raise RuntimeError(
1009 |             f"TTS output too small ({size} bytes < {min_size}): {path} — "
1010 |             f"ElevenLabs likely returned empty audio"
1011 |         )
1012 |     dur = ffprobe_duration(path)
1013 |     if dur < 0.5:
1014 |         raise RuntimeError(
1015 |             f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
1016 |             f"audio is effectively silent/corrupt"
1017 |         )
1018 | 
1019 | 
1020 | def tts_preflight_test() -> bool:
1021 |     """Preflight: call ElevenLabs with a 5-word test phrase, confirm >1000 bytes returned.
1022 |     Raises RuntimeError on failure so the pipeline aborts before wasting render time."""
1023 |     if not HAS_REQUESTS:
1024 |         raise RuntimeError("TTS preflight: 'requests' library not installed")
1025 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1026 |     if not key:
1027 |         raise RuntimeError("TTS preflight: ELEVENLABS_API_KEY not available")
1028 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
1029 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1030 |     body = {
1031 |         "text": "Bitcoin signal confirmed today.",
1032 |         "model_id": _PBX_VOICE["model_id"],
1033 |         "voice_settings": dict(_PBX_VOICE["voice_settings"]),
1034 |     }
1035 |     try:
1036 |         r = requests.post(url, json=body, headers=headers, timeout=20)
1037 |         if r.status_code != 200:
1038 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned HTTP {r.status_code}: {r.text[:200]}")
1039 |         if len(r.content) < 1000:
1040 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned only {len(r.content)} bytes (need >1000)")
1041 |         logger.info(f"[TTS] Preflight PASS: PBX voice returned {len(r.content)} bytes")
1042 |         return True
1043 |     except requests.RequestException as e:
1044 |         raise RuntimeError(f"TTS preflight: ElevenLabs unreachable: {e}")
1045 | 
1046 | 
1047 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
1048 |                    segment_type: str = "") -> bool:
1049 |     """Generate TTS for a single line using the specified host voice.
1050 | 
1051 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
1052 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
1053 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
1054 |     """
1055 |     if not HAS_REQUESTS:
1056 |         # No requests lib — try pyttsx3 or silence
1057 |         return _tts_generate_silence_fallback(text, output_path)
1058 | 
1059 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1060 |     if not key:
1061 |         return _tts_generate_silence_fallback(text, output_path)
1062 | 
1063 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
1064 |     # These tags are for script structure — narrator should never read them aloud
1065 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
1066 |     # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
1067 |     text = expand_numbers_for_tts(text)
1068 |     # R25 FIX 7: Apply pronunciation map (Pysh→PISH, etc.) — was defined but never called
1069 |     text = apply_pronunciation_map(text)
1070 | 
1071 |     voice = VOICES.get(host, VOICES[2])  # All hosts → PBX
1072 |     # Check TTS cache first — avoid API call if same text+voice was generated before
1073 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
1074 |     if _tts_cache_get(cache_key, output_path):
1075 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
1076 |         return True
1077 | 
1078 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
1079 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1080 | 
1081 |     # Apply voice mode overrides based on segment type (both hosts)
1082 |     voice_settings = dict(voice["voice_settings"])
1083 |     if segment_type in VOICE_MODES:
1084 |         mode = VOICE_MODES[segment_type]
1085 |         for k, v in mode.items():
1086 |             if k != "speed":
1087 |                 voice_settings[k] = v
1088 | 
1089 |     chunks = _chunk_text(text)
1090 |     chunk_files = []
1091 | 
1092 |     for ci, chunk in enumerate(chunks):
1093 |         body = {
1094 |             "text": chunk,
1095 |             "model_id": voice["model_id"],
1096 |             "voice_settings": voice_settings,
1097 |         }
1098 |         # Add speed parameter from voice config (host-specific)
1099 |         speed = voice.get("speed", 1.0)
1100 |         if speed != 1.0:
1101 |             body["speed"] = speed
1102 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
1103 |         success = False
1104 | 
1105 |         # FIX iter1: Increase retries from 3 to 5 with longer backoff to survive
1106 |         # transient ElevenLabs outages that were causing grade failures
1107 |         max_retries = 5
1108 |         for attempt in range(max_retries):
1109 |             try:
1110 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
1111 |                 if r.status_code == 200:
1112 |                     with open(mp3_tmp, "wb") as f:
1113 |                         f.write(r.content)
1114 |                     # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
1115 |                     if os.path.getsize(mp3_tmp) < 1000:
1116 |                         print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
1117 |                         if attempt < max_retries - 1:
1118 |                             time.sleep(2 ** attempt)
1119 |                             continue
1120 |                     success = True
1121 |                     break
1122 |                 elif r.status_code == 429:
1123 |                     wait = min(2 ** (attempt + 1), 30)  # cap at 30s
1124 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
1125 |                     time.sleep(wait)
1126 |                 else:
1127 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
1128 |                     if attempt < max_retries - 1:
1129 |                         time.sleep(2 ** attempt)
1130 |             except Exception as e:
1131 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
1132 |                 if attempt < max_retries - 1:
1133 |                     time.sleep(2 ** attempt)
1134 | 
1135 |         if not success:
1136 |             for f in chunk_files:
1137 |                 try:
1138 |                     os.remove(f)
1139 |                 except Exception:
1140 |                     pass
1141 |             logger.error(f"[tts] ElevenLabs failed after {max_retries} retries for chunk {ci} — returning False")
1142 |             return False
1143 |         chunk_files.append(mp3_tmp)
1144 | 
1145 |     # Single chunk
1146 |     if len(chunk_files) == 1:
1147 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
1148 |         try:
1149 |             os.remove(chunk_files[0])
1150 |         except Exception:
1151 |             pass
1152 |         if ok and os.path.exists(output_path):
1153 |             _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
1154 |             validate_tts_output(output_path)
1155 |             _tts_cache_put(cache_key, output_path)
1156 |         return ok
1157 | 
1158 |     # Multi-chunk concat
1159 |     concat_list = output_path + ".concat.txt"
1160 |     mp3_combined = output_path + ".combined.mp3"
1161 |     with open(concat_list, "w") as f:
1162 |         for p in chunk_files:
1163 |             f.write(f"file '{os.path.abspath(p)}'\n")
1164 |     subprocess.run(
1165 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
1166 |          "-c", "copy", mp3_combined],
1167 |         capture_output=True, text=True,
1168 |     )
1169 |     ok = _mp3_to_m4a(mp3_combined, output_path)
1170 |     for f in chunk_files + [concat_list, mp3_combined]:
1171 |         try:
1172 |             if os.path.exists(f):
1173 |                 os.remove(f)
1174 |         except Exception:
1175 |             pass
1176 |     if ok and os.path.exists(output_path):
1177 |         _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
1178 |         validate_tts_output(output_path)
1179 |         _tts_cache_put(cache_key, output_path)
1180 |     return ok
1181 | 
1182 | 
1183 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
1184 |     """Generate audio for the entire dual-host dialogue.
1185 | 
1186 |     Args:
1187 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
1188 |         output_dir: Directory for audio files
1189 | 
1190 |     Returns:
1191 |         {
1192 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
1193 |             "full": str,  # path to concatenated full audio
1194 |             "total_duration": float,
1195 |         }
1196 |     """
1197 |     os.makedirs(output_dir, exist_ok=True)
1198 | 
1199 |     _active_provider = _get_tts_provider()
1200 |     if _active_provider == "local":
1201 |         tts_preflight_local()
1202 |     else:
1203 |         key = _get_cached_key("ELEVENLABS_API_KEY")
1204 |         if not key:
1205 |             raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
1206 | 
1207 |     silence_path = os.path.join(output_dir, "silence.m4a")
1208 |     _generate_silence(silence_path, SILENCE_GAP)
1209 | 
1210 |     lines = []
1211 |     parts_for_concat = []
1212 |     current_time = 0.0
1213 | 
1214 |     for i, entry in enumerate(dialogue):
1215 |         host = entry.get("host")
1216 |         text = entry.get("text", "")
1217 | 
1218 |         # Skip CLIP markers — they don't have audio but DO advance the timeline
1219 |         if host == "CLIP":
1220 |             clip_duration = float(entry.get("duration", 30.0))  # use actual duration or default 30s
1221 |             lines.append({
1222 |                 "path": None,
1223 |                 "host": "CLIP",
1224 |                 "duration": clip_duration,  # record actual duration, not hardcoded 0.0
1225 |                 "start": current_time,
1226 |                 "source": entry.get("source", ""),
1227 |                 "query": entry.get("query", ""),
1228 |                 "text": text,
1229 |             })
1230 |             current_time += clip_duration  # advance timeline so subsequent audio is correctly offset
1231 |             continue
1232 | 
1233 |         _provider = _get_tts_provider()
1234 |         if _provider == "local":
1235 |             host_num = host if host in (1, 2) else 2
1236 |         else:
1237 |             host_num = 2   # ElevenLabs: single-host Option A preserved
1238 |         voice = VOICES[host_num]
1239 |         segment_type = entry.get("type", "")
1240 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
1241 | 
1242 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
1243 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
1244 | 
1245 |         _provider = _get_tts_provider()
1246 |         if _provider == "local":
1247 |             _tts_ok = tts_local(text, line_path, host_num, segment_type=segment_type)
1248 |         else:
1249 |             _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
1250 |         if _tts_ok:
1251 |             if not os.path.exists(line_path) or os.path.getsize(line_path) < 1000:
1252 |                 logger.warning(f"[tts] Line {i} zero/tiny audio — writing silence")
1253 |                 _tts_ok = False
1254 |             else:
1255 |                 dur = ffprobe_duration(line_path)
1256 |                 if dur < 0.5 and len(text) > 10:
1257 |                     logger.warning(f"[tts] Line {i} too short ({dur:.2f}s) — writing silence")
1258 |                     _tts_ok = False
1259 |         if not _tts_ok:
1260 |             # Degrade gracefully: write 3s silence so assembler can continue
1261 |             logger.error(f"[tts] TTS failed line {i} — writing silence")
1262 |             subprocess.run([
1263 |                 "ffmpeg", "-y", "-f", "lavfi",
1264 |                 "-i", "anullsrc=r=48000:cl=stereo",
1265 |                 "-t", "3", "-c:a", "aac", "-b:a", "192k", line_path
1266 |             ], capture_output=True)
1267 |             dur = 3.0
1268 | 
1269 |         lines.append({
1270 |             "path": line_path,
1271 |             "host": host_num,
1272 |             "duration": dur,
1273 |             "start": current_time,
1274 |             "text": text,
1275 |             "type": segment_type,
1276 |             "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
1277 |         })
1278 |         parts_for_concat.append(line_path)
1279 |         current_time += dur
1280 | 
1281 |         # Add silence gap between speakers (not after last line, not before CLIP)
1282 |         next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
1283 |         if next_entry is not None and next_entry.get("host") != "CLIP":
1284 |             parts_for_concat.append(silence_path)
1285 |             current_time += SILENCE_GAP
1286 | 
1287 |     # Concatenate all lines into full audio
1288 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
1289 |     if parts_for_concat:
1290 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
1291 |         with open(concat_file, "w") as f:
1292 |             for p in parts_for_concat:
1293 |                 f.write(f"file '{os.path.abspath(p)}'\n")
1294 |         subprocess.run(
1295 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
1296 |              "-c", "copy", full_path],
1297 |             capture_output=True, text=True,
1298 |         )
1299 |         if os.path.exists(concat_file):
1300 |             os.remove(concat_file)
1301 | 
1302 |     # Guard: full_dialogue.m4a must not be zero-byte or tiny
1303 |     if os.path.exists(full_path):
1304 |         full_size = os.path.getsize(full_path)
1305 |         if full_size < 10240:
1306 |             raise RuntimeError(
1307 |                 f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
1308 |                 f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
1309 |             )
1310 | 
1311 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
1312 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
1313 | 
1314 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
1315 | 
1316 |     # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
1317 |     host_stats = {}  # {host_num: {"total": N, "ok": N}}
1318 |     for l in lines:
1319 |         h = l.get("host")
1320 |         if h == "CLIP":
1321 |             continue
1322 |         if h not in host_stats:
1323 |             host_stats[h] = {"total": 0, "ok": 0}
1324 |         host_stats[h]["total"] += 1
1325 |         if l.get("path") and os.path.exists(l.get("path", "")):
1326 |             host_stats[h]["ok"] += 1
1327 | 
1328 |     for h, stats in host_stats.items():
1329 |         voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
1330 |         if stats["ok"] == 0 and stats["total"] > 0:
1331 |             raise RuntimeError(
1332 |                 f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
1333 |                 f"All audio is missing/silent. Aborting before render."
1334 |             )
1335 |         if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
1336 |             raise RuntimeError(
1337 |                 f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
1338 |                 f"successful lines (<50%). Too many failures to produce a quality render."
1339 |             )
1340 | 
1341 |     return {
1342 |         "lines": lines,
1343 |         "full": full_path if os.path.exists(full_path) else None,
1344 |         "total_duration": total_dur,
1345 |     }
1346 | 
1347 | 
1348 | # Legacy compatibility — V3 pipeline used generate_all_audio
1349 | def generate_all_audio(script: dict, output_dir: str) -> dict:
1350 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
1351 |     if "dialogue" in script:
1352 |         return generate_dialogue_audio(script["dialogue"], output_dir)
1353 |     # V3 fallback
1354 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
1355 | 
1356 | 
1357 | if __name__ == "__main__":
1358 |     from script_writer import generate_script
1359 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
1360 |     script = generate_script(style=style)
1361 |     base = os.path.dirname(os.path.abspath(__file__))
1362 |     audio_dir = os.path.join(base, "output", "audio_test")
1363 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
1364 |     print(json.dumps(
1365 |         {k: v for k, v in result.items() if k != "lines"},
1366 |         indent=2,
1367 |     ))
1368 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
