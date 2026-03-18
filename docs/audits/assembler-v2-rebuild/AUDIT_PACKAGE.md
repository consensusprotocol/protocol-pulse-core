# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: assembler-v2-rebuild
# Branch: main
# Generated: 2026-03-18 02:28 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
1. render() NEVER raises. filler_result() on any failure.
2. CRF-only encoding. No -b:v/-maxrate/-bufsize alongside -crf.
3. EpisodeContext episode-scoped. No module globals.
4. ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.
5. Atomic writes via atomic_rename.
6. safe_text() from helpers.py is the single drawtext sanitizer.
7. PiP: eof_action=repeat. stream_loop=-1 on pre-normalized pip_preview.
8. Metrics cache scoped to ctx.workdir NOT /tmp.
9. Outro: -an strips audio before stream_loop.
10. All 29 tests pass before commit.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: video_pipeline_v3/assembler_v2/constants.py (62 lines)
```
   1 | """
   2 | Protocol Pulse V2 — constants.py
   3 | IMMUTABLE CODEC LAW. Every segment must conform. No exceptions.
   4 | """
   5 | from pathlib import Path
   6 | 
   7 | # ── Video ──────────────────────────────────────────────────────────
   8 | VIDEO_W        = 1920
   9 | VIDEO_H        = 1080
  10 | VIDEO_FPS      = 30
  11 | VIDEO_PIX_FMT  = "yuv420p"
  12 | VIDEO_CODEC    = "libx264"
  13 | VIDEO_CRF      = 17
  14 | VIDEO_PRESET   = "medium"
  15 | VIDEO_BITRATE  = "8M"
  16 | VIDEO_MAXRATE  = "10M"
  17 | VIDEO_BUFSIZE  = "15M"
  18 | 
  19 | # ── Audio ──────────────────────────────────────────────────────────
  20 | AUDIO_CODEC        = "aac"
  21 | AUDIO_BITRATE      = "192k"
  22 | AUDIO_SAMPLE_RATE  = 48000
  23 | AUDIO_CHANNELS     = 2
  24 | AUDIO_FORMAT       = "fltp"
  25 | AUDIO_TARGET_LUFS  = -14.0
  26 | AUDIO_MAX_TRUE_PEAK = -2.0
  27 | AUDIO_LRA          = 7.0
  28 | AUDIO_LIMITER      = 0.85
  29 | 
  30 | # ── Asset paths ────────────────────────────────────────────────────
  31 | PIPELINE_DIR   = Path(__file__).parent.parent
  32 | ASSETS_DIR     = PIPELINE_DIR / "assets"
  33 | INTRO_TAG      = ASSETS_DIR / "intro_tag.mp4"
  34 | INTRO_MUSIC    = ASSETS_DIR / "intro_music.mp3"
  35 | BG_LOOP        = ASSETS_DIR / "bg_loop.mp4"
  36 | OUTRO_BRANDED  = ASSETS_DIR / "outro_branded_new.mp4"
  37 | SCANLINE       = ASSETS_DIR / "scanline_overlay.png"
  38 | SFX_WHOOSH     = ASSETS_DIR / "sfx" / "custom_whoosh.wav"
  39 | SFX_SWOOSH     = ASSETS_DIR / "sfx" / "card_swoosh.wav"
  40 | FONT_BOLD      = ASSETS_DIR / "fonts" / "JetBrainsMono-Bold.ttf"
  41 | FONT_MONO      = ASSETS_DIR / "fonts" / "JetBrainsMono-Regular.ttf"
  42 | CHARTS_DIR     = PIPELINE_DIR / "cache" / "charts"
  43 | OUTPUT_DIR     = PIPELINE_DIR / "output"
  44 | 
  45 | # ── Brand colors (ffmpeg hex format) ──────────────────────────────
  46 | COLOR_BG    = "0x0A0A0F"
  47 | COLOR_RED   = "0xFF3B5F"
  48 | COLOR_WHITE = "0xFFFFFF"
  49 | COLOR_CYAN  = "0x5DE4FF"
  50 | COLOR_GOLD  = "0xFFD700"
  51 | 
  52 | # ── QC acceptance policy ───────────────────────────────────────────
  53 | QC_MIN_DURATION          = 480    # 8 minutes
  54 | QC_MAX_DURATION          = 900    # 15 minutes
  55 | QC_MAX_FILLER_SECONDS    = 60
  56 | QC_MAX_DEGRADED_SEGMENTS = 2
  57 | QC_MAX_BLACK_FRAME_S     = 2.0
  58 | QC_MAX_SILENCE_S         = 2.0
  59 | QC_MIN_LUFS              = -17.0
  60 | QC_MAX_LUFS              = -13.0
  61 | QC_MAX_TRUE_PEAK         = -1.0
  62 | 
```

### File: video_pipeline_v3/assembler_v2/helpers.py (283 lines)
```
   1 | """
   2 | Protocol Pulse V2 — helpers.py
   3 | Core utilities. Every ffmpeg call goes through run_ffmpeg(). No exceptions.
   4 | """
   5 | from __future__ import annotations
   6 | import subprocess, json, os, time, shutil, logging
   7 | from pathlib import Path
   8 | from typing import Optional
   9 | from .constants import (
  10 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     COLOR_BG, CHARTS_DIR
  13 | )
  14 | 
  15 | logger = logging.getLogger(__name__)
  16 | 
  17 | 
  18 | # ── Core FFmpeg runner ────────────────────────────────────────────────────────
  19 | 
  20 | def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
  21 |     """
  22 |     Single authoritative ffmpeg runner. All segments use this. Never bypass.
  23 |     Logs full command, duration, and stderr on failure.
  24 |     """
  25 |     cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
  26 |     logger.info(f"[ffmpeg] {label} | cmd: {' '.join(cmd[:10])}...")
  27 |     t0 = time.time()
  28 |     try:
  29 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
  30 |         elapsed = round(time.time() - t0, 2)
  31 |         if result.returncode != 0:
  32 |             logger.error(f"[ffmpeg] FAIL {label} ({elapsed}s) | {result.stderr[-800:]}")
  33 |             return False
  34 |         logger.info(f"[ffmpeg] OK {label} ({elapsed}s)")
  35 |         return True
  36 |     except subprocess.TimeoutExpired:
  37 |         logger.error(f"[ffmpeg] TIMEOUT {label} after {timeout}s")
  38 |         return False
  39 |     except Exception as e:
  40 |         logger.error(f"[ffmpeg] EXCEPTION {label}: {e}")
  41 |         return False
  42 | 
  43 | 
  44 | # ── FFprobe utilities ─────────────────────────────────────────────────────────
  45 | 
  46 | def ffprobe_duration(path: Path) -> float:
  47 |     """Return audio/video duration in seconds. Returns 0.0 on any error."""
  48 |     try:
  49 |         r = subprocess.run(
  50 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  51 |              "-of", "csv=p=0", str(path)],
  52 |             capture_output=True, text=True, timeout=15
  53 |         )
  54 |         val = r.stdout.strip()
  55 |         return float(val) if val else 0.0
  56 |     except Exception:
  57 |         return 0.0
  58 | 
  59 | 
  60 | def ffprobe_streams(path: Path) -> dict:
  61 |     """Return full ffprobe JSON. Returns {} on error."""
  62 |     try:
  63 |         r = subprocess.run(
  64 |             ["ffprobe", "-v", "error", "-print_format", "json",
  65 |              "-show_streams", "-show_format", str(path)],
  66 |             capture_output=True, text=True, timeout=15
  67 |         )
  68 |         return json.loads(r.stdout)
  69 |     except Exception:
  70 |         return {}
  71 | 
  72 | 
  73 | def ffprobe_contract(path: Path) -> tuple:
  74 |     """
  75 |     Verify segment meets the V2 output contract.
  76 |     Returns (passed: bool, summary: dict).
  77 |     Every segment is checked after render. Filler used if failed.
  78 |     """
  79 |     if not path.exists() or path.stat().st_size < 1000:
  80 |         return False, {"error": "file missing or too small", "passed": False}
  81 | 
  82 |     info = ffprobe_streams(path)
  83 |     if not info:
  84 |         return False, {"error": "ffprobe returned no data", "passed": False}
  85 | 
  86 |     streams = info.get("streams", [])
  87 |     fmt = info.get("format", {})
  88 |     video = next((s for s in streams if s.get("codec_type") == "video"), None)
  89 |     audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
  90 | 
  91 |     issues = []
  92 | 
  93 |     if not video:
  94 |         issues.append("no video stream")
  95 |     else:
  96 |         if video.get("width") != VIDEO_W:
  97 |             issues.append(f"width={video.get('width')} (need {VIDEO_W})")
  98 |         if video.get("height") != VIDEO_H:
  99 |             issues.append(f"height={video.get('height')} (need {VIDEO_H})")
 100 |         if video.get("pix_fmt") != VIDEO_PIX_FMT:
 101 |             issues.append(f"pix_fmt={video.get('pix_fmt')} (need {VIDEO_PIX_FMT})")
 102 |         fps_str = video.get("r_frame_rate", "0/1")
 103 |         try:
 104 |             n, d = fps_str.split("/")
 105 |             fps = float(n) / float(d)
 106 |             if abs(fps - VIDEO_FPS) > 0.5:
 107 |                 issues.append(f"fps={fps:.2f} (need {VIDEO_FPS})")
 108 |         except Exception:
 109 |             issues.append(f"unparseable fps: {fps_str}")
 110 | 
 111 |     if not audio:
 112 |         issues.append("no audio stream")
 113 |     else:
 114 |         sr = int(audio.get("sample_rate", 0))
 115 |         if sr != AUDIO_SAMPLE_RATE:
 116 |             issues.append(f"sample_rate={sr} (need {AUDIO_SAMPLE_RATE})")
 117 |         ch = audio.get("channels", 0)
 118 |         if ch != AUDIO_CHANNELS:
 119 |             issues.append(f"channels={ch} (need {AUDIO_CHANNELS})")
 120 |         # Codec checks — critical for concat compatibility
 121 |         if video and video.get("codec_name") != "h264":
 122 |             issues.append(f"video_codec={video.get('codec_name')} (need h264)")
 123 |         if audio.get("codec_name") != AUDIO_CODEC:
 124 |             issues.append(f"audio_codec={audio.get('codec_name')} (need {AUDIO_CODEC})")
 125 | 
 126 |     duration = float(fmt.get("duration", 0))
 127 |     passed = len(issues) == 0
 128 | 
 129 |     summary = {
 130 |         "passed": passed,
 131 |         "issues": issues,
 132 |         "duration": round(duration, 3),
 133 |         "video_codec": video.get("codec_name") if video else None,
 134 |         "audio_codec": audio.get("codec_name") if audio else None,
 135 |         "width": video.get("width") if video else None,
 136 |         "height": video.get("height") if video else None,
 137 |         "fps": fps_str if video else None,
 138 |         "pix_fmt": video.get("pix_fmt") if video else None,
 139 |         "sample_rate": audio.get("sample_rate") if audio else None,
 140 |         "channels": audio.get("channels") if audio else None,
 141 |     }
 142 | 
 143 |     if issues:
 144 |         logger.warning(f"[contract] FAIL {path.name}: {', '.join(issues)}")
 145 |     else:
 146 |         logger.info(f"[contract] PASS {path.name} ({duration:.1f}s)")
 147 | 
 148 |     return passed, summary
 149 | 
 150 | 
 151 | # ── Filler segment ────────────────────────────────────────────────────────────
 152 | 
 153 | def make_filler(output_path: Path, duration: float,
 154 |                 tts_path: Optional[Path] = None) -> bool:
 155 |     """
 156 |     Generate a contract-compliant filler segment.
 157 |     Uses TTS audio if available so PBX voice continues even if video failed.
 158 |     Dark background — clearly not final content but episode continues.
 159 |     """
 160 |     dur = max(float(duration), 5.0)
 161 | 
 162 |     if tts_path and tts_path.exists() and tts_path.stat().st_size > 1000:
 163 |         ok = run_ffmpeg([
 164 |             "-f", "lavfi", "-i",
 165 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 166 |             "-i", str(tts_path),
 167 |             "-map", "0:v", "-map", "1:a",
 168 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
 169 |             "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
 170 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
 171 |             "-ac", str(AUDIO_CHANNELS),
 172 |             "-t", str(dur), "-shortest",
 173 |             str(output_path)
 174 |         ], f"filler+audio {output_path.name}", 60)
 175 |     else:
 176 |         ok = run_ffmpeg([
 177 |             "-f", "lavfi", "-i",
 178 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 179 |             "-f", "lavfi", "-i",
 180 |             f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
 181 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
 182 |             "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
 183 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
 184 |             "-ac", str(AUDIO_CHANNELS),
 185 |             "-t", str(dur),
 186 |             str(output_path)
 187 |         ], f"filler+silence {output_path.name}", 60)
 188 | 
 189 |     return ok and output_path.exists() and output_path.stat().st_size > 1000
 190 | 
 191 | 
 192 | # ── Atomic file operations ────────────────────────────────────────────────────
 193 | 
 194 | def atomic_rename(src: Path, dst: Path) -> bool:
 195 |     """
 196 |     Atomically move src to dst. Never leaves partial files at dst.
 197 |     dst.parent is created if it does not exist.
 198 |     """
 199 |     try:
 200 |         dst.parent.mkdir(parents=True, exist_ok=True)
 201 |         shutil.move(str(src), str(dst))
 202 |         logger.info(f"[atomic] {src.name} -> {dst}")
 203 |         return True
 204 |     except Exception as e:
 205 |         logger.error(f"[atomic] FAIL {src} -> {dst}: {e}")
 206 |         return False
 207 | 
 208 | 
 209 | # ── PiP pre-normalization ─────────────────────────────────────────────────────
 210 | 
 211 | def normalize_pip_preview(clip_path: Path, output_path: Path,
 212 |                            duration: float = 8.0) -> bool:
 213 |     """
 214 |     Pre-normalize a partner clip to pip_preview_norm format.
 215 |     Run ONCE per clip in Stage 2, NOT inside narration renders.
 216 |     Output: 640x360, yuv420p, 30fps CFR, no audio, h264 crf=18, hue=s=0.25.
 217 |     This pre-processing means narration.py only does a simple overlay.
 218 |     No zoompan, no heavy real-time transforms.
 219 |     """
 220 |     if not clip_path.exists() or clip_path.stat().st_size < 50000:
 221 |         logger.warning(f"[pip_norm] clip missing or tiny: {clip_path}")
 222 |         return False
 223 | 
 224 |     clip_dur = ffprobe_duration(clip_path)
 225 |     if clip_dur < 2.0:
 226 |         logger.warning(f"[pip_norm] clip too short ({clip_dur:.1f}s): {clip_path.name}")
 227 |         return False
 228 | 
 229 |     # Extract from midpoint — better face/content shots
 230 |     start = max(0.0, (clip_dur / 2.0) - (duration / 2.0))
 231 |     actual_dur = min(duration, clip_dur - start)
 232 | 
 233 |     ok = run_ffmpeg([
 234 |         "-ss", str(round(start, 3)),
 235 |         "-i", str(clip_path),
 236 |         "-t", str(round(actual_dur, 3)),
 237 |         "-an",
 238 |         "-vf", (
 239 |             "scale=640:360:force_original_aspect_ratio=decrease,"
 240 |             "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
 241 |             f"fps={VIDEO_FPS},"
 242 |             f"format={VIDEO_PIX_FMT},"
 243 |             "hue=s=0.25"
 244 |         ),
 245 |         "-c:v", VIDEO_CODEC, "-crf", "18", "-preset", "veryfast",
 246 |         str(output_path)
 247 |     ], f"pip_norm {clip_path.name}", 120)
 248 | 
 249 |     if ok and output_path.exists():
 250 |         logger.info(f"[pip_norm] OK {output_path.name} ({actual_dur:.1f}s)")
 251 |         return True
 252 |     return False
 253 | 
 254 | 
 255 | # ── Chart PNG helper ──────────────────────────────────────────────────────────
 256 | 
 257 | def get_chart_path(keyword: str) -> Optional[Path]:
 258 |     """
 259 |     Map narration keyword to chart PNG path.
 260 |     Returns None if chart missing — caller must handle gracefully.
 261 |     """
 262 |     mapping = {
 263 |         "price": CHARTS_DIR / "price_chart.png",
 264 |         "hashrate": CHARTS_DIR / "hashrate_chart.png",
 265 |         "mempool": CHARTS_DIR / "dominance_chart.png",
 266 |         "dominance": CHARTS_DIR / "dominance_chart.png",
 267 |     }
 268 |     path = mapping.get(keyword.lower())
 269 |     if path and path.exists() and path.stat().st_size > 1000:
 270 |         return path
 271 |     # Return None for unmapped keywords — segment handles missing chart gracefully
 272 |     # Never return a wrong chart (content integrity rule)
 273 |     if keyword and keyword.lower() not in mapping:
 274 |         return None
 275 |     # For empty keyword (show all charts), return None — segment handles grid layout
 276 |     return None
 277 | 
 278 | def safe_text(text,max_chars=80):
 279 |     t=str(text).strip()[:max_chars]
 280 |     for o,n in [(chr(92),chr(92)*2),(chr(39),""),(chr(58),chr(92)+chr(58)),(chr(37),chr(92)+chr(37)),(chr(91),chr(92)+chr(91)),(chr(93),chr(92)+chr(93)),(chr(44),chr(92)+chr(44)),(chr(59),chr(92)+chr(59))]:
 281 |         t=t.replace(o,n)
 282 |     return t.replace(chr(10)," ")
 283 | 
```

### File: video_pipeline_v3/assembler_v2/manifest.py (89 lines)
```
   1 | """
   2 | Protocol Pulse V2 — manifest.py
   3 | Episode manifest and segment spec dataclasses.
   4 | The manifest is the single source of truth for every episode.
   5 | """
   6 | from __future__ import annotations
   7 | from dataclasses import dataclass, field, asdict
   8 | from pathlib import Path
   9 | from typing import Optional
  10 | import json, uuid, time
  11 | 
  12 | 
  13 | @dataclass
  14 | class SegmentSpec:
  15 |     """Complete specification for one segment. Passed to segment.render()."""
  16 |     segment_type: str           # cold_open|narration|partner_clip|transition|data|social|signal_active|wrap
  17 |     clip_rank: int = 0          # partner clip rank (0 = no clip)
  18 |     tts_path: Optional[str] = None      # absolute path to ElevenLabs m4a
  19 |     clip_path: Optional[str] = None     # absolute path to partner clip mp4
  20 |     pip_path: Optional[str] = None      # absolute path to pip_preview_norm_{rank}.mp4
  21 |     headline: str = ""
  22 |     body: str = ""
  23 |     chart_keyword: str = ""     # "price"|"hashrate"|"mempool"|""
  24 |     social_posts: list = field(default_factory=list)
  25 |     signal_content: dict = field(default_factory=dict)
  26 |     is_required: bool = False   # filler still marks episode DEGRADED if True
  27 |     duration_hint: float = 0.0  # from ffprobe(tts_path)
  28 |     btc_price: str = "N/A"
  29 | 
  30 |     def tts(self) -> Optional[Path]:
  31 |         return Path(self.tts_path) if self.tts_path else None
  32 | 
  33 |     def clip(self) -> Optional[Path]:
  34 |         return Path(self.clip_path) if self.clip_path else None
  35 | 
  36 |     def pip(self) -> Optional[Path]:
  37 |         return Path(self.pip_path) if self.pip_path else None
  38 | 
  39 | 
  40 | @dataclass
  41 | class RenderedSegment:
  42 |     """Result of segment.render(). Always populated — degraded=True if filler used."""
  43 |     spec: SegmentSpec
  44 |     path: Optional[str] = None          # absolute path to rendered mp4
  45 |     duration: float = 0.0
  46 |     contract_passed: bool = False
  47 |     degraded: bool = False
  48 |     render_ms: int = 0
  49 |     ffprobe_summary: dict = field(default_factory=dict)
  50 |     error: str = ""
  51 | 
  52 |     def output(self) -> Optional[Path]:
  53 |         return Path(self.path) if self.path else None
  54 | 
  55 | 
  56 | @dataclass
  57 | class EpisodeManifest:
  58 |     """Complete episode plan. Written before any ffmpeg is called."""
  59 |     episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
  60 |     date_str: str = ""
  61 |     title: str = ""
  62 |     cold_open: str = ""
  63 |     segments: list = field(default_factory=list)  # list of SegmentSpec
  64 |     btc_price: str = "N/A"
  65 |     created_at: float = field(default_factory=time.time)
  66 | 
  67 |     def to_dict(self) -> dict:
  68 |         d = asdict(self)
  69 |         return d
  70 | 
  71 |     def to_json(self) -> str:
  72 |         return json.dumps(self.to_dict(), indent=2, default=str)
  73 | 
  74 |     def save(self, path: Path):
  75 |         path.write_text(self.to_json())
  76 |         return path
  77 | 
  78 |     @classmethod
  79 |     def from_json(cls, path: Path) -> "EpisodeManifest":
  80 |         d = json.loads(path.read_text())
  81 |         d["segments"] = [SegmentSpec(**s) for s in d.get("segments", [])]
  82 |         return cls(**d)
  83 | 
  84 |     def segment_count(self) -> int:
  85 |         return len(self.segments)
  86 | 
  87 |     def narration_segments(self) -> list:
  88 |         return [s for s in self.segments if s.segment_type in ("narration", "cold_open")]
  89 | 
```

### File: video_pipeline_v3/assembler_v2/state.py (99 lines)
```
   1 | """
   2 | Protocol Pulse V2 — state.py
   3 | Episode-scoped state object. NO module-level globals anywhere.
   4 | EpisodeContext is passed as a parameter to every function that needs state.
   5 | """
   6 | from __future__ import annotations
   7 | from dataclasses import dataclass, field
   8 | from pathlib import Path
   9 | import uuid, time, logging
  10 | 
  11 | logger = logging.getLogger(__name__)
  12 | 
  13 | 
  14 | @dataclass
  15 | class EpisodeContext:
  16 |     """
  17 |     All mutable state for one episode render.
  18 |     Created once in episode.py, passed everywhere as ctx.
  19 |     Never stored as a module-level global.
  20 |     """
  21 |     episode_id: str
  22 |     date_str: str
  23 |     workdir: Path
  24 | 
  25 |     # SFX dedup — episode-scoped, not global
  26 |     whoosh_applied: set = field(default_factory=set)
  27 | 
  28 |     # Segment tracking
  29 |     segments_rendered: list = field(default_factory=list)
  30 |     degraded_count: int = 0
  31 |     total_filler_seconds: float = 0.0
  32 | 
  33 |     # Sponsor tracking
  34 |     sponsor_reads_done: list = field(default_factory=list)
  35 | 
  36 |     # Runtime
  37 |     started_at: float = field(default_factory=time.time)
  38 | 
  39 |     @classmethod
  40 |     def create(cls, date_str: str, base_output_dir: Path) -> "EpisodeContext":
  41 |         """Factory method. Creates workdir structure."""
  42 |         episode_id = str(uuid.uuid4())[:8]
  43 |         workdir = base_output_dir / date_str
  44 |         workdir.mkdir(parents=True, exist_ok=True)
  45 |         (workdir / "segments").mkdir(exist_ok=True)
  46 |         (workdir / "logs").mkdir(exist_ok=True)
  47 |         (workdir / "reports").mkdir(exist_ok=True)
  48 |         logger.info(f"[ctx] Episode {episode_id} | workdir: {workdir}")
  49 |         return cls(episode_id=episode_id, date_str=date_str, workdir=workdir)
  50 | 
  51 |     # ── Whoosh dedup ────────────────────────────────────────────────
  52 |     def mark_whoosh(self, path: Path):
  53 |         self.whoosh_applied.add(str(path.resolve()))
  54 | 
  55 |     def has_whoosh(self, path: Path) -> bool:
  56 |         return str(path.resolve()) in self.whoosh_applied
  57 | 
  58 |     # ── Degraded tracking ────────────────────────────────────────────
  59 |     def mark_degraded(self, segment_type: str, reason: str, filler_sec: float = 0.0):
  60 |         self.degraded_count += 1
  61 |         self.total_filler_seconds += filler_sec
  62 |         logger.warning(
  63 |             f"[ctx] DEGRADED #{self.degraded_count} | {segment_type} | {reason} | "
  64 |             f"+{filler_sec:.1f}s filler | total_filler={self.total_filler_seconds:.1f}s"
  65 |         )
  66 | 
  67 |     # ── Verdict ─────────────────────────────────────────────────────
  68 |     def verdict(self) -> str:
  69 |         """PASS | DEGRADED | HOLD"""
  70 |         from .constants import QC_MAX_FILLER_SECONDS, QC_MAX_DEGRADED_SEGMENTS
  71 |         if self.total_filler_seconds >= QC_MAX_FILLER_SECONDS:
  72 |             return "HOLD"
  73 |         if self.degraded_count > QC_MAX_DEGRADED_SEGMENTS:
  74 |             return "DEGRADED"
  75 |         return "PASS"
  76 | 
  77 |     def elapsed(self) -> float:
  78 |         return time.time() - self.started_at
  79 | 
  80 |     def segment_dir(self) -> Path:
  81 |         return self.workdir / "segments"
  82 | 
  83 |     def log_dir(self) -> Path:
  84 |         return self.workdir / "logs"
  85 | 
  86 |     def report_dir(self) -> Path:
  87 |         return self.workdir / "reports"
  88 | 
  89 |     def summary(self) -> dict:
  90 |         return {
  91 |             "episode_id": self.episode_id,
  92 |             "date_str": self.date_str,
  93 |             "segments_rendered": len(self.segments_rendered),
  94 |             "degraded_count": self.degraded_count,
  95 |             "total_filler_seconds": self.total_filler_seconds,
  96 |             "verdict": self.verdict(),
  97 |             "elapsed_seconds": round(self.elapsed(), 1),
  98 |         }
  99 | 
```

### File: video_pipeline_v3/assembler_v2/preflight.py (52 lines)
```
   1 | """Protocol Pulse V2 - preflight.py"""
   2 | from __future__ import annotations
   3 | import os,shutil,logging
   4 | from pathlib import Path
   5 | from .constants import INTRO_TAG,INTRO_MUSIC,BG_LOOP,OUTRO_BRANDED,SFX_WHOOSH,SFX_SWOOSH,FONT_BOLD,FONT_MONO,CHARTS_DIR
   6 | from .helpers import ffprobe_duration,ffprobe_streams
   7 | logger=logging.getLogger(__name__)
   8 | CRITICAL=[(INTRO_TAG,"intro_tag.mp4",1000000),(INTRO_MUSIC,"intro_music.mp3",100000),(BG_LOOP,"bg_loop.mp4",1000000),(OUTRO_BRANDED,"outro_branded_new.mp4",1000000),(SFX_WHOOSH,"custom_whoosh.wav",10000),(SFX_SWOOSH,"card_swoosh.wav",10000),(FONT_BOLD,"JetBrainsMono-Bold.ttf",50000),(FONT_MONO,"JetBrainsMono-Regular.ttf",50000)]
   9 | def run_preflight(tts_files:list,clip_files:list,work_dir:Path)->dict:
  10 |     rpt={"passed":True,"critical_failures":[],"warnings":[],"checks":{}}
  11 |     def fail(m):
  12 |         rpt["critical_failures"].append(m);rpt["passed"]=False;logger.error(f"[preflight] CRITICAL: {m}")
  13 |     def warn(m):
  14 |         rpt["warnings"].append(m);logger.warning(f"[preflight] WARNING: {m}")
  15 |     for t in("ffmpeg","ffprobe"):
  16 |         if shutil.which(t):rpt["checks"][t]="OK"
  17 |         else:fail(f"{t} not in PATH")
  18 |     for path,name,mn in CRITICAL:
  19 |         if not path.exists():fail(f"Missing: {name}")
  20 |         elif path.stat().st_size<mn:fail(f"Too small: {name}")
  21 |         else:rpt["checks"][name]=f"OK {path.stat().st_size//1024}KB"
  22 |     try:
  23 |         s=os.statvfs(str(work_dir));fg=(s.f_bavail*s.f_frsize)/(1024**3)
  24 |         if fg<5.0:fail(f"Disk critical {fg:.1f}GB")
  25 |         elif fg<10.0:warn(f"Disk low {fg:.1f}GB")
  26 |         else:rpt["checks"]["disk"]=f"OK {fg:.1f}GB"
  27 |     except Exception as e:warn(f"Disk check: {e}")
  28 |     for p in[Path(x) for x in tts_files]:
  29 |         if not p.exists():fail(f"TTS missing: {p.name}")
  30 |         elif p.stat().st_size<1000:fail(f"TTS empty: {p.name}")
  31 |         else:
  32 |             d=ffprobe_duration(p)
  33 |             if d<0.5:fail(f"TTS silent: {p.name}")
  34 |             else:rpt["checks"][f"tts:{p.name}"]=f"OK {d:.1f}s"
  35 |     for p in[Path(x) for x in clip_files]:
  36 |         if not p.exists():warn(f"Clip missing (filler): {p.name}");continue
  37 |         info=ffprobe_streams(p);streams=info.get("streams",[])
  38 |         hv=any(s.get("codec_type")=="video" for s in streams)
  39 |         ha=any(s.get("codec_type")=="audio" for s in streams)
  40 |         d=ffprobe_duration(p)
  41 |         if not hv:warn(f"Clip no video: {p.name}")
  42 |         if not ha:warn(f"Clip no audio: {p.name}")
  43 |         rpt["checks"][f"clip:{p.name}"]=f"OK {d:.1f}s v={hv} a={ha}"
  44 |     for c in("price_chart.png","hashrate_chart.png","dominance_chart.png"):
  45 |         cp=CHARTS_DIR/c
  46 |         if cp.exists() and cp.stat().st_size>1000:rpt["checks"][c]="OK"
  47 |         else:warn(f"Chart missing: {c}")
  48 |     if rpt["critical_failures"]:
  49 |         raise RuntimeError("Preflight FAILED: "+("; ".join(rpt["critical_failures"])))
  50 |     logger.info(f"[preflight] PASSED {len(rpt['checks'])} checks, {len(rpt['warnings'])} warnings")
  51 |     return rpt
  52 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/encode.py (49 lines)
```
   1 | from __future__ import annotations
   2 | import time,logging
   3 | from pathlib import Path
   4 | from typing import Optional
   5 | from ..constants import VIDEO_CODEC,VIDEO_CRF,VIDEO_PRESET,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_BITRATE,VIDEO_MAXRATE,VIDEO_BUFSIZE,AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS
   6 | from ..helpers import run_ffmpeg,ffprobe_contract,make_filler,atomic_rename
   7 | logger=logging.getLogger(__name__)
   8 | 
   9 | def encode_segment(inputs,filter_complex,video_map,audio_map,output_path,duration,label="segment",timeout=300,tts_path=None):
  10 |     """Single authoritative encode function. Every segment calls this. Never bypass."""
  11 |     tmp=output_path.with_suffix(".tmp.mp4")
  12 |     t0=time.time()
  13 |     flat=[]
  14 |     for i in inputs:
  15 |         flat.extend([str(x) for x in i] if isinstance(i,(list,tuple)) else [str(i)])
  16 |     args=(
  17 |         ["-hide_banner"]  # suppress version banner in logs
  18 |         +flat
  19 |         +["-filter_complex",filter_complex]
  20 |         +["-map",video_map,"-map",audio_map]
  21 |         +["-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset",VIDEO_PRESET]
  22 |         +["-r",str(VIDEO_FPS),"-pix_fmt",VIDEO_PIX_FMT]
  23 |         +["-c:a",AUDIO_CODEC,"-ar",str(AUDIO_SAMPLE_RATE),"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS)]
  24 |         +["-t",str(round(duration,3))]
  25 |         +["-movflags","+faststart"]
  26 |         +[str(tmp)]
  27 |     )
  28 |     # NOTE: run_ffmpeg already prepends ["ffmpeg","-y"] — overwrites tmp safely
  29 |     ok=run_ffmpeg(args,label,timeout)
  30 |     ms=int((time.time()-t0)*1000)
  31 |     def use_filler(reason):
  32 |         logger.error(f"[encode] {reason} for {label} — writing filler")
  33 |         fp=output_path.with_suffix(".filler.mp4")
  34 |         make_filler(fp,duration,tts_path)
  35 |         if fp.exists():
  36 |             atomic_rename(fp,output_path)
  37 |     if not ok or not tmp.exists() or tmp.stat().st_size<1000:
  38 |         use_filler("ENCODE FAILED")
  39 |         return False,False,{"error":"encode failed"},ms
  40 |     passed,summary=ffprobe_contract(tmp)
  41 |     if not passed:
  42 |         tmp.unlink(missing_ok=True)
  43 |         use_filler("CONTRACT FAILED")
  44 |         return True,False,summary,ms
  45 |     atomic_rename(tmp,output_path)
  46 |     dur=summary.get("duration",0)
  47 |     logger.info(f"[encode] OK {label} ({dur:.1f}s, {ms}ms)")
  48 |     return True,True,summary,ms
  49 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/filters.py (96 lines)
```
   1 | """
   2 | Protocol Pulse V2 - ffmpeg_core/filters.py
   3 | Reusable FFmpeg filter snippets. Pure functions — return filter strings.
   4 | No FFmpeg calls here. All transforms composable.
   5 | """
   6 | from __future__ import annotations
   7 | from ..constants import (
   8 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
   9 |     AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_FORMAT,
  10 |     AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA, AUDIO_LIMITER,
  11 |     COLOR_BG
  12 | )
  13 | 
  14 | 
  15 | def normalize_video(label_in: str, label_out: str,
  16 |                     w: int = VIDEO_W, h: int = VIDEO_H) -> str:
  17 |     """Scale, set SAR, set pixel format, reset PTS. Apply to every video input."""
  18 |     return (
  19 |         f"[{label_in}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
  20 |         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
  21 |         f"setsar=1,format={VIDEO_PIX_FMT},"
  22 |         f"fps={VIDEO_FPS},"
  23 |         f"setpts=PTS-STARTPTS[{label_out}]"
  24 |     )
  25 | 
  26 | 
  27 | def normalize_audio(label_in: str, label_out: str,
  28 |                     apply_loudnorm: bool = False) -> str:
  29 |     """
  30 |     Normalize audio to pipeline standard.
  31 |     apply_loudnorm=True for final voice segments.
  32 |     apply_loudnorm=False for clips where we preserve original dynamics.
  33 |     Always: resample, stereo, reset PTS, limiter.
  34 |     """
  35 |     chain = (
  36 |         f"[{label_in}]aformat=channel_layouts=stereo:"
  37 |         f"sample_rates={AUDIO_SAMPLE_RATE}:sample_fmts={AUDIO_FORMAT},"
  38 |         f"asetpts=PTS-STARTPTS"
  39 |     )
  40 |     if apply_loudnorm:
  41 |         chain += (
  42 |             f",loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}"
  43 |             f":LRA={AUDIO_LRA}:linear=true"
  44 |         )
  45 |     chain += f",alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[{label_out}]"
  46 |     return chain
  47 | 
  48 | 
  49 | def overlay_pip(bg_label: str, pip_label: str, out_label: str,
  50 |                 x: int = 1240, y: int = 160,
  51 |                 w: int = 640, h: int = 360) -> str:
  52 |     """
  53 |     Overlay PiP video on background.
  54 |     eof_action=pass: PiP loops without freezing at end.
  55 |     """
  56 |     return (
  57 |         f"[{pip_label}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
  58 |         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
  59 |         f"format={VIDEO_PIX_FMT}[pip_scaled];"
  60 |         f"[{bg_label}][pip_scaled]overlay=x={x}:y={y}:"
  61 |         f"eof_action=repeat:shortest=0[{out_label}]"
  62 |     )
  63 | 
  64 | 
  65 | def build_waveform(audio_label: str, out_label: str,
  66 |                    w: int = 1920, h: int = 80,
  67 |                    color: str = "0xFF3B5F") -> str:
  68 |     """Waveform visualizer strip from audio signal."""
  69 |     return (
  70 |         f"[{audio_label}]showwaves=s={w}x{h}:mode=cline:"
  71 |         f"colors={color}@0.8:scale=sqrt,format={VIDEO_PIX_FMT}[{out_label}]"
  72 |     )
  73 | 
  74 | 
  75 | def fade_video(label_in: str, label_out: str,
  76 |                duration: float, fade_out_dur: float = 0.3) -> str:
  77 |     """Add fade-out to end of video segment."""
  78 |     fade_start = max(0.0, duration - fade_out_dur)
  79 |     return (
  80 |         f"[{label_in}]fade=t=out:st={fade_start:.3f}:"
  81 |         f"d={fade_out_dur}[{label_out}]"
  82 |     )
  83 | 
  84 | 
  85 | def drawtext(label_in: str, label_out: str,
  86 |              text: str, font: str, size: int,
  87 |              color: str, x: str, y: str,
  88 |              box: bool = False, box_color: str = "black@0.5") -> str:
  89 |     """Single drawtext filter. Sanitize text before calling."""
  90 |     safe = text.replace("'", "\'").replace(":", "\:").replace("\n", "")
  91 |     box_str = f":box=1:boxcolor={box_color}:boxborderw=8" if box else ""
  92 |     return (
  93 |         f"[{label_in}]drawtext=fontfile={font}:text='{safe}':"
  94 |         f"fontcolor={color}:fontsize={size}:x={x}:y={y}{box_str}[{label_out}]"
  95 |     )
  96 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/probe.py (71 lines)
```
   1 | from __future__ import annotations
   2 | import subprocess,re,json,logging
   3 | from pathlib import Path
   4 | logger=logging.getLogger(__name__)
   5 | 
   6 | def measure_lufs(path:Path)->tuple:
   7 |     """Measure integrated loudness via loudnorm JSON output. Returns (lufs,true_peak) or (-99,-99)."""
   8 |     try:
   9 |         res=subprocess.run(
  10 |             ['ffmpeg','-hide_banner','-i',str(path),
  11 |              '-af','loudnorm=I=-14:TP=-2:LRA=7:print_format=json',
  12 |              '-f','null','-'],
  13 |             capture_output=True,text=True,timeout=120)
  14 |         # loudnorm JSON is in stderr — find the JSON block
  15 |         stderr=res.stderr
  16 |         json_start=stderr.rfind('{')
  17 |         json_end=stderr.rfind('}')+1
  18 |         if json_start>=0 and json_end>json_start:
  19 |             data=json.loads(stderr[json_start:json_end])
  20 |             lufs=float(data.get('input_i',-99))
  21 |             tp=float(data.get('input_tp',-99))
  22 |             return lufs,tp
  23 |         # Fallback to regex if JSON not found
  24 |         i_m=re.search(r'"input_i"\s*:\s*"([^"]+)"',stderr)
  25 |         tp_m=re.search(r'"input_tp"\s*:\s*"([^"]+)"',stderr)
  26 |         return (float(i_m.group(1)) if i_m else -99.0),(float(tp_m.group(1)) if tp_m else -99.0)
  27 |     except Exception as e:
  28 |         logger.warning(f'[probe] lufs failed {path.name}: {e}')
  29 |         return -99.0,-99.0
  30 | 
  31 | def detect_black_frames(path:Path,min_dur:float=0.5)->list:
  32 |     """Returns list of (start,end,duration) tuples for black segments."""
  33 |     try:
  34 |         res=subprocess.run(
  35 |             ['ffmpeg','-hide_banner','-i',str(path),
  36 |              '-vf',f'blackdetect=d={min_dur}:pix_th=0.02','-an','-f','null','-'],
  37 |             capture_output=True,text=True,timeout=120)
  38 |         return [(float(m.group(1)),float(m.group(2)),float(m.group(3)))
  39 |                 for m in re.finditer(
  40 |                     r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)',
  41 |                     res.stderr)]
  42 |     except Exception as e:
  43 |         logger.warning(f'[probe] blackdetect failed: {e}')
  44 |         return []
  45 | 
  46 | def detect_silence(path:Path,min_dur:float=1.0,noise_db:float=-50.0)->list:
  47 |     """Returns list of (start,end) tuples for silence gaps."""
  48 |     try:
  49 |         res=subprocess.run(
  50 |             ['ffmpeg','-hide_banner','-i',str(path),
  51 |              '-af',f'silencedetect=n={noise_db}dB:d={min_dur}','-f','null','-'],
  52 |             capture_output=True,text=True,timeout=120)
  53 |         starts=re.findall(r'silence_start: ([\d.]+)',res.stderr)
  54 |         ends=re.findall(r'silence_end: ([\d.]+)',res.stderr)
  55 |         return [(float(s),float(e)) for s,e in zip(starts,ends)]
  56 |     except Exception as e:
  57 |         logger.warning(f'[probe] silencedetect failed: {e}')
  58 |         return []
  59 | 
  60 | def has_motion(path:Path)->bool:
  61 |     """Quick check video has actual frames (not frozen/static)."""
  62 |     try:
  63 |         res=subprocess.run(
  64 |             ['ffprobe','-v','error','-select_streams','v',
  65 |              '-show_entries','stream=nb_frames','-of','csv=p=0',str(path)],
  66 |             capture_output=True,text=True,timeout=15)
  67 |         val=res.stdout.strip()
  68 |         return int(val)>1 if val and val.isdigit() else True
  69 |     except Exception:
  70 |         return True
  71 | 
```

### File: video_pipeline_v3/assembler_v2/segments/base.py (42 lines)
```
   1 | from __future__ import annotations
   2 | from abc import ABC, abstractmethod
   3 | from pathlib import Path
   4 | import logging
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import ffprobe_duration, make_filler
   8 | logger = logging.getLogger(__name__)
   9 | 
  10 | class Segment(ABC):
  11 |     criticality: str = 'optional'
  12 | 
  13 |     @abstractmethod
  14 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext, output_path: Path, idx: int) -> RenderedSegment:
  15 |         ...
  16 | 
  17 |     def validate(self, spec: SegmentSpec) -> tuple:
  18 |         if spec.tts_path and not Path(spec.tts_path).exists():
  19 |             return False, f'TTS missing: {spec.tts_path}'
  20 |         return True, ''
  21 | 
  22 |     def get_duration(self, spec: SegmentSpec) -> float:
  23 |         if spec.duration_hint and spec.duration_hint > 0:
  24 |             return spec.duration_hint
  25 |         if spec.tts_path:
  26 |             p = Path(spec.tts_path)
  27 |             if p.exists():
  28 |                 d = ffprobe_duration(p)
  29 |                 if d > 0: return d
  30 |         return 15.0
  31 | 
  32 |     def filler_result(self, spec: SegmentSpec, ctx: EpisodeContext,
  33 |                       output_path: Path, reason: str) -> RenderedSegment:
  34 |         dur = self.get_duration(spec)
  35 |         tts = Path(spec.tts_path) if spec.tts_path else None
  36 |         ok = make_filler(output_path, dur, tts)
  37 |         ctx.mark_degraded(spec.segment_type, reason, dur)
  38 |         actual = ffprobe_duration(output_path) if ok and output_path.exists() else dur
  39 |         return RenderedSegment(spec=spec, path=str(output_path) if ok else None,
  40 |                                duration=actual, contract_passed=ok,
  41 |                                degraded=True, error=reason)
  42 | 
```

### File: video_pipeline_v3/assembler_v2/segments/transition.py (65 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..constants import VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,COLOR_BG,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,SFX_WHOOSH
   8 | from ..ffmpeg_core.encode import encode_segment
   9 | logger=logging.getLogger(__name__)
  10 | TRANSITION_DURATION=0.25
  11 | 
  12 | class TransitionSegment(Segment):
  13 |     criticality='optional'
  14 | 
  15 |     def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
  16 |         try:
  17 |             return self._render(spec,ctx,output_path)
  18 |         except Exception as e:
  19 |             logger.error(f'[transition] exception: {e}')
  20 |             return self.filler_result(spec,ctx,output_path,str(e))
  21 | 
  22 |     def _render(self,spec,ctx,output_path):
  23 |         dur=TRANSITION_DURATION
  24 |         apply_whoosh=SFX_WHOOSH.exists() and not ctx.has_whoosh(output_path)
  25 | 
  26 |         if apply_whoosh:
  27 |             inputs=[
  28 |                 ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
  29 |                 ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
  30 |                 ['-i',str(SFX_WHOOSH)],
  31 |             ]
  32 |             fg=(
  33 |                 f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
  34 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[sil];'
  35 |                 f'[2:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  36 |                 f'afade=t=in:st=0:d=0.05,volume=0.6[whoosh];'
  37 |                 f'[sil][whoosh]amix=inputs=2:duration=first:weights=1 1[a_out]'
  38 |             )
  39 |         else:
  40 |             inputs=[
  41 |                 ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
  42 |                 ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
  43 |             ]
  44 |             fg=(
  45 |                 f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
  46 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[a_out]'
  47 |             )
  48 | 
  49 |         ok,passed,summary,ms=encode_segment(
  50 |             inputs,fg,'[v_out]','[a_out]',output_path,dur,'transition',30)
  51 | 
  52 |         if not ok or not output_path.exists():
  53 |             return self.filler_result(spec,ctx,output_path,'transition encode failed')
  54 | 
  55 |         if apply_whoosh:
  56 |             ctx.mark_whoosh(output_path)
  57 |             logger.info('[transition] OK with whoosh')
  58 |         else:
  59 |             logger.info('[transition] OK (no whoosh)')
  60 | 
  61 |         return RenderedSegment(spec=spec,path=str(output_path),
  62 |                                duration=dur,contract_passed=passed,
  63 |                                degraded=not passed,ffprobe_summary=summary,
  64 |                                render_ms=ms)
  65 | 
```

### File: video_pipeline_v3/assembler_v2/segments/wrap.py (71 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,
   8 |                          AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,AUDIO_LIMITER,
   9 |                          AUDIO_SAMPLE_RATE,OUTRO_BRANDED,COLOR_BG)
  10 | from ..helpers import ffprobe_duration
  11 | from ..ffmpeg_core.encode import encode_segment
  12 | logger=logging.getLogger(__name__)
  13 | 
  14 | class WrapSegment(Segment):
  15 |     criticality='optional'
  16 | 
  17 |     def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
  18 |         try:
  19 |             return self._render(spec,ctx,output_path)
  20 |         except Exception as e:
  21 |             logger.error(f'[wrap] exception: {e}')
  22 |             return self.filler_result(spec,ctx,output_path,str(e))
  23 | 
  24 |     def _render(self,spec,ctx,output_path):
  25 |         tts=Path(spec.tts_path) if spec.tts_path else None
  26 |         tts_dur=ffprobe_duration(tts) if tts and tts.exists() else 0.0
  27 |         outro_dur=ffprobe_duration(OUTRO_BRANDED) if OUTRO_BRANDED.exists() else 0.0
  28 |         total_dur=max(tts_dur,outro_dur,10.0)
  29 | 
  30 |         if not OUTRO_BRANDED.exists() or outro_dur<1.0:
  31 |             logger.warning('[wrap] outro asset missing — filler')
  32 |             return self.filler_result(spec,ctx,output_path,'outro asset missing')
  33 | 
  34 |         if tts and tts.exists() and tts_dur>0.5:
  35 |             inputs=[
  36 |                 ['-stream_loop','-1','-an','-i',str(OUTRO_BRANDED)],
  37 |                 ['-i',str(tts)],
  38 |             ]
  39 |             fade_st=max(0,total_dur-0.5)
  40 |             fg=(
  41 |                 f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
  42 |                 f'setpts=PTS-STARTPTS,'
  43 |                 f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
  44 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  45 |                 f'asetpts=PTS-STARTPTS,'
  46 |                 f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  47 |                 f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  48 |             )
  49 |         else:
  50 |             inputs=[['-stream_loop','-1','-i',str(OUTRO_BRANDED)]]
  51 |             fade_st=max(0,total_dur-0.5)
  52 |             fg=(
  53 |                 f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
  54 |                 f'setpts=PTS-STARTPTS,'
  55 |                 f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
  56 |                 f'[0:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  57 |                 f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  58 |             )
  59 | 
  60 |         ok,passed,summary,ms=encode_segment(
  61 |             inputs,fg,'[v_out]','[a_out]',output_path,total_dur,'wrap outro',120,tts)
  62 | 
  63 |         if not ok or not output_path.exists():
  64 |             return self.filler_result(spec,ctx,output_path,'wrap encode failed')
  65 | 
  66 |         logger.info(f'[wrap] OK ({total_dur:.1f}s)')
  67 |         return RenderedSegment(spec=spec,path=str(output_path),
  68 |                                duration=summary.get('duration',total_dur),
  69 |                                contract_passed=passed,degraded=not passed,
  70 |                                ffprobe_summary=summary,render_ms=ms)
  71 | 
```

### File: video_pipeline_v3/assembler_v2/segments/cold_open.py (164 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename
   8 | from ..constants import (
   9 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
  10 |     VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  13 |     INTRO_TAG, INTRO_MUSIC, COLOR_BG, FONT_BOLD, FONT_MONO,
  14 |     COLOR_RED, COLOR_WHITE, COLOR_CYAN
  15 | )
  16 | logger = logging.getLogger(__name__)
  17 | FREEZE_FRAME_BUFFER_S = 1.0  # Extra frames after tag ends so fade-out has video to work on
  18 | 
  19 | 
  20 | class ColdOpenSegment(Segment):
  21 |     """
  22 |     Cold open: intro_tag.mp4 plays with intro_music.mp3 fading under PBX narration.
  23 |     Audio law (confirmed working from old pipeline):
  24 |       - intro_music: volume=0.05, fades out at 6s
  25 |       - PBX TTS: delayed 300ms, amix weight=3.0 vs music weight=0.5
  26 |       - amix duration=first — TTS anchors the output length
  27 |     """
  28 |     criticality = "required"
  29 | 
  30 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  31 |                output_path: Path, idx: int) -> RenderedSegment:
  32 |         try:
  33 |             return self._render(spec, ctx, output_path)
  34 |         except Exception as e:
  35 |             logger.error(f"[cold_open] exception: {e}")
  36 |             return self.filler_result(spec, ctx, output_path, str(e))
  37 | 
  38 |     def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
  39 |                 output_path: Path) -> RenderedSegment:
  40 |         tts = spec.tts()
  41 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  42 |             return self.filler_result(spec, ctx, output_path, "TTS missing")
  43 | 
  44 |         tts_dur = ffprobe_duration(tts)
  45 |         if tts_dur < 0.5:
  46 |             return self.filler_result(spec, ctx, output_path, "TTS silent")
  47 | 
  48 |         # intro_tag provides the visual; its duration caps the segment
  49 |         tag_dur = ffprobe_duration(INTRO_TAG) if INTRO_TAG.exists() else 0.0
  50 |         total_dur = max(tts_dur, tag_dur if tag_dur > 0 else tts_dur)
  51 | 
  52 |         tmp = output_path.with_suffix(".tmp.mp4")
  53 | 
  54 |         if INTRO_TAG.exists() and INTRO_MUSIC.exists():
  55 |             ok = self._render_full(tts, tmp, tts_dur, tag_dur, total_dur)
  56 |         elif INTRO_TAG.exists():
  57 |             ok = self._render_tag_only(tts, tmp, tts_dur, tag_dur, total_dur)
  58 |         else:
  59 |             ok = self._render_tts_only(tts, tmp, tts_dur, spec)
  60 | 
  61 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  62 |             return self.filler_result(spec, ctx, output_path, "cold_open encode failed")
  63 | 
  64 |         passed, summary = ffprobe_contract(tmp)
  65 |         atomic_rename(tmp, output_path)
  66 |         dur = summary.get("duration", total_dur)
  67 |         logger.info(f"[cold_open] OK ({dur:.1f}s)")
  68 |         return RenderedSegment(
  69 |             spec=spec, path=str(output_path),
  70 |             duration=dur, contract_passed=passed,
  71 |             degraded=not passed, ffprobe_summary=summary
  72 |         )
  73 | 
  74 |     def _render_full(self, tts, tmp, tts_dur, tag_dur, total_dur):
  75 |         """Full cold open: intro tag video + music + PBX TTS."""
  76 |         # video: scale intro_tag, freeze last frame to fill TTS duration
  77 |         freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
  78 |         vf = (
  79 |             f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
  80 |             f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
  81 |         )
  82 |         fg = (
  83 |             f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
  84 |             # Music: trim to 8s, fade out at 6s, very quiet under voice
  85 |             f"[2:a]atrim=0:8.0,asetpts=PTS-STARTPTS,"
  86 |             f"afade=t=out:st=6.0:d=2.0,volume=0.05[mus];"
  87 |             # TTS: 300ms delay so music hits first, then PBX voice dominates
  88 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
  89 |             f"adelay=300|300[tts];"
  90 |             # Mix: duration=first = TTS anchors length (confirmed working)
  91 |             f"[mus][tts]amix=inputs=2:duration=first:weights=0.5 3.0,"
  92 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
  93 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
  94 |             f"aresample=async=1[a_out]"
  95 |         )
  96 |         return run_ffmpeg([
  97 |             "-i", str(INTRO_TAG),
  98 |             "-i", str(tts),
  99 |             "-i", str(INTRO_MUSIC),
 100 |             "-filter_complex", fg,
 101 |             "-map", "[v_out]", "-map", "[a_out]",
 102 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 103 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 104 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 105 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 106 |             "-t", str(round(total_dur, 3)),
 107 |             "-movflags", "+faststart", str(tmp)
 108 |         ], "cold_open full", 120)
 109 | 
 110 |     def _render_tag_only(self, tts, tmp, tts_dur, tag_dur, total_dur):
 111 |         """Intro tag video + TTS only (no music file)."""
 112 |         freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
 113 |         vf = (
 114 |             f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
 115 |             f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
 116 |         )
 117 |         fg = (
 118 |             f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
 119 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
 120 |             f"adelay=300|300,"
 121 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
 122 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
 123 |             f"aresample=async=1[a_out]"
 124 |         )
 125 |         return run_ffmpeg([
 126 |             "-i", str(INTRO_TAG), "-i", str(tts),
 127 |             "-filter_complex", fg,
 128 |             "-map", "[v_out]", "-map", "[a_out]",
 129 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 130 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 131 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 132 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 133 |             "-t", str(round(total_dur, 3)),
 134 |             "-movflags", "+faststart", str(tmp)
 135 |         ], "cold_open tag-only", 120)
 136 | 
 137 |     def _render_tts_only(self, tts, tmp, tts_dur, spec):
 138 |         """Fallback: dark background + TTS narration only."""
 139 |         headline = spec.headline or "PULSE CHECK"
 140 |         safe_hl = headline.replace(":", "\\:").replace("'", "\\'")[:60]
 141 |         fg = (
 142 |             f"[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg];"
 143 |             f"[bg]drawtext=fontfile={FONT_BOLD}:text='{safe_hl}':"
 144 |             f"fontcolor={COLOR_RED}:fontsize=72:"
 145 |             f"x=(w-text_w)/2:y=(h-text_h)/2[v_out];"
 146 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
 147 |             f"adelay=300|300,"
 148 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
 149 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]"
 150 |         )
 151 |         return run_ffmpeg([
 152 |             "-f", "lavfi", "-i",
 153 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 154 |             "-i", str(tts),
 155 |             "-filter_complex", fg,
 156 |             "-map", "[v_out]", "-map", "[a_out]",
 157 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 158 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 159 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 160 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 161 |             "-t", str(round(tts_dur + 0.5, 3)),
 162 |             "-movflags", "+faststart", str(tmp)
 163 |         ], "cold_open tts-only fallback", 120)
 164 | 
```

### File: video_pipeline_v3/assembler_v2/segments/narration.py (157 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,normalize_pip_preview
   8 | from ..constants import (
   9 |     VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
  10 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  11 |     AUDIO_LIMITER,AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,
  12 |     BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO
  13 | )
  14 | logger=logging.getLogger(__name__)
  15 | PIP_X,PIP_Y,PIP_W,PIP_H=1240,140,640,360
  16 | 
  17 | 
  18 | class NarrationSegment(Segment):
  19 |     criticality='required'
  20 | 
  21 |     def render(self,spec,ctx,output_path,idx):
  22 |         try:
  23 |             pip=self._ensure_pip(spec,ctx)
  24 |             return self._render(spec,ctx,output_path,pip)
  25 |         except Exception as e:
  26 |             logger.error(f'[narration] exception: {e}')
  27 |             return self.filler_result(spec,ctx,output_path,str(e))
  28 | 
  29 |     def _ensure_pip(self,spec,ctx):
  30 |         pip=spec.pip()
  31 |         if pip and pip.exists() and pip.stat().st_size>10000:
  32 |             return pip
  33 |         clip=spec.clip()
  34 |         if clip and clip.exists() and clip.stat().st_size>50000:
  35 |             pip_out=ctx.segment_dir()/f'pip_preview_r{spec.clip_rank}.mp4'
  36 |             cdur=ffprobe_duration(clip)
  37 |             pdur=min(cdur*0.4,12.0)
  38 |             if normalize_pip_preview(clip,pip_out,pdur) and pip_out.exists():
  39 |                 logger.info(f'[narration] pip generated on-demand rank={spec.clip_rank}')
  40 |                 return pip_out
  41 |         logger.warning(f'[narration] no pip rank={spec.clip_rank} — dark panel')
  42 |         return None
  43 | 
  44 |     def _render(self,spec,ctx,output_path,pip):
  45 |         tts=spec.tts()
  46 |         if not tts or not tts.exists() or tts.stat().st_size<1000:
  47 |             return self.filler_result(spec,ctx,output_path,'TTS missing')
  48 |         dur=ffprobe_duration(tts)
  49 |         if dur<0.5:
  50 |             return self.filler_result(spec,ctx,output_path,'TTS silent')
  51 |         has_pip=pip and pip.exists() and pip.stat().st_size>1000
  52 |         has_bg=BG_LOOP.exists()
  53 |         if has_pip:
  54 |             ok=self._render_with_pip(tts,pip,output_path,dur,spec,has_bg)
  55 |         else:
  56 |             ok=self._render_no_pip(tts,output_path,dur,spec,has_bg)
  57 |         if not ok or not output_path.exists() or output_path.stat().st_size<1000:
  58 |             return self.filler_result(spec,ctx,output_path,'narration encode failed')
  59 |         passed,summary=ffprobe_contract(output_path)
  60 |         actual=summary.get('duration',dur)
  61 |         logger.info(f'[narration] OK ({actual:.1f}s pip={has_pip})')
  62 |         return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
  63 |                                contract_passed=passed,degraded=not passed,
  64 |                                ffprobe_summary=summary)
  65 | 
  66 |     def _build_fg_with_pip(self,pip,dur,headline,body):
  67 |         return (
  68 |             f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
  69 |             f'[2:v]scale={PIP_W}:{PIP_H}:force_original_aspect_ratio=decrease,'
  70 |             f'pad={PIP_W}:{PIP_H}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},'
  71 |             f'format={VIDEO_PIX_FMT}[pip];'
  72 |             f'[bg][pip]overlay=x={PIP_X}:y={PIP_Y}:eof_action=repeat:shortest=0[wp];'
  73 |             f'[wp]drawbox=x={PIP_X-2}:y={PIP_Y-2}:w={PIP_W+4}:h={PIP_H+4}:'
  74 |             f'color={COLOR_RED}@0.8:t=2[pf];'
  75 |             f"[pf]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
  76 |             f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
  77 |             f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
  78 |             f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
  79 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  80 |             f'asetpts=PTS-STARTPTS,'
  81 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  82 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  83 |         )
  84 | 
  85 |     def _build_fg_no_pip(self,dur,headline,body):
  86 |         return (
  87 |             f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
  88 |             f'[bg]drawbox=x={PIP_X}:y={PIP_Y}:w={PIP_W}:h={PIP_H}:'
  89 |             f'color={COLOR_BG}@1.0:t=fill[wp];'
  90 |             f"[wp]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
  91 |             f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
  92 |             f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
  93 |             f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
  94 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  95 |             f'asetpts=PTS-STARTPTS,'
  96 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  97 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  98 |         )
  99 | 
 100 |     def _encode(self,inputs_list,fg,output_path,dur,label):
 101 |         tmp=output_path.with_suffix('.tmp.mp4')
 102 |         flat=[str(x) for i in inputs_list for x in i]
 103 |         ok=run_ffmpeg(flat+['-filter_complex',fg,
 104 |             '-map','[v_out]','-map','[a_out]',
 105 |             '-c:v',VIDEO_CODEC,'-crf',str(VIDEO_CRF),'-preset','medium',
 106 |             '-r',str(VIDEO_FPS),'-pix_fmt',VIDEO_PIX_FMT,
 107 |             '-c:a',AUDIO_CODEC,'-ar',str(AUDIO_SAMPLE_RATE),
 108 |             '-b:a',AUDIO_BITRATE,'-ac',str(AUDIO_CHANNELS),
 109 |             '-t',str(round(dur,3)),'-movflags','+faststart',str(tmp)],label,180)
 110 |         if ok and tmp.exists():
 111 |             atomic_rename(tmp,output_path)
 112 |             return True
 113 |         tmp.unlink(missing_ok=True)
 114 |         return False
 115 | 
 116 |     def _render_with_pip(self,tts,pip,output_path,dur,spec,has_bg):
 117 |         hl=self._safe_text(spec.headline or spec.segment_type.upper(),55)
 118 |         bd=self._safe_text(spec.body or '',80)
 119 |         if has_bg:
 120 |             inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)],
 121 |                     ['-stream_loop','-1','-i',str(pip)]]
 122 |         else:
 123 |             inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
 124 |                     ['-i',str(tts)],['-stream_loop','-1','-i',str(pip)]]
 125 |         return self._encode(inputs,self._build_fg_with_pip(pip,dur,hl,bd),
 126 |                             output_path,dur,f'narration+pip rank={spec.clip_rank}')
 127 | 
 128 |     def _render_no_pip(self,tts,output_path,dur,spec,has_bg):
 129 |         hl=self._safe_text(spec.headline or spec.segment_type.upper(),55)
 130 |         bd=self._safe_text(spec.body or '',80)
 131 |         if has_bg:
 132 |             inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)]]
 133 |         else:
 134 |             inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
 135 |                     ['-i',str(tts)]]
 136 |         return self._encode(inputs,self._build_fg_no_pip(dur,hl,bd),
 137 |                             output_path,dur,f'narration no-pip rank={spec.clip_rank}')
 138 | 
 139 |     @staticmethod
 140 |     def _safe_text(text, max_chars):
 141 |         """Sanitize text for FFmpeg drawtext. Escapes all filter-special chars."""
 142 |         t = text.strip()[:max_chars]
 143 |         # Order matters: backslash must be first
 144 |         replacements = [
 145 |             ('\\', '\\\\'),  # backslash first
 146 |             ("'", ''),         # remove single quotes (can break f-string delimiter)
 147 |             (':', '\\:'),      # colon is filter option separator
 148 |             ('%', '\\%'),      # percent triggers drawtext variable expansion
 149 |             ('[', '\\['),      # square brackets are stream labels
 150 |             (']', '\\]'),
 151 |             (',', '\\,'),      # comma separates filter options
 152 |             (';', '\\;'),      # semicolon separates filters in complex
 153 |         ]
 154 |         for old, new in replacements:
 155 |             t = t.replace(old, new)
 156 |         return t.replace('\n', ' ')  # newlines become spaces
 157 | 
```

### File: video_pipeline_v3/assembler_v2/segments/partner_clip.py (120 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_streams,ffprobe_contract,atomic_rename
   8 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
   9 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  10 |     AUDIO_LIMITER,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO)
  11 | logger=logging.getLogger(__name__)
  12 | LT_HEIGHT,LT_Y_OFFSET=80,60
  13 | LT_BG_ALPHA="0.82"
  14 | 
  15 | 
  16 | def _is_hdr(clip):
  17 |     """Detect if clip uses HDR color space (BT.2020 / PQ / HLG)."""
  18 |     try:
  19 |         import subprocess,json as j
  20 |         res=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
  21 |             "-show_entries","stream=color_space,color_transfer,color_primaries",
  22 |             "-of","json",str(clip)],capture_output=True,text=True,timeout=10)
  23 |         s=j.loads(res.stdout).get("streams",[{}])[0]
  24 |         hdr_markers={"bt2020","smpte2084","arib-std-b67","bt2020nc","bt2020c"}
  25 |         vals={s.get("color_space",""),s.get("color_transfer",""),s.get("color_primaries","")}
  26 |         return bool(vals & hdr_markers)
  27 |     except Exception:
  28 |         return False
  29 | 
  30 | 
  31 | def _tonemap_filter():
  32 |     """HDR-to-SDR tone mapping chain. Applied when HDR source detected."""
  33 |     return ("zscale=t=linear:npl=100,format=gbrpf32le,"
  34 |             "zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
  35 |             "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
  36 | 
  37 | 
  38 | def _safe_label(text,max_chars=40):
  39 |     t=text.strip()[:max_chars]
  40 |     for o,n in [(chr(92),chr(92)*2),(chr(39),""),(chr(58),chr(92)+chr(58)),
  41 |                 (chr(37),chr(92)+chr(37)),(chr(91),chr(92)+chr(91)),
  42 |                 (chr(93),chr(92)+chr(93)),(chr(44),chr(92)+chr(44)),
  43 |                 (chr(59),chr(92)+chr(59))]:
  44 |         t=t.replace(o,n)
  45 |     return t.replace(chr(10)," ")
  46 | 
  47 | 
  48 | class PartnerClipSegment(Segment):
  49 |     criticality="required"
  50 | 
  51 |     def render(self,spec,ctx,output_path,idx):
  52 |         try:
  53 |             return self._render(spec,ctx,output_path)
  54 |         except Exception as e:
  55 |             logger.error("[partner_clip] exception: "+str(e))
  56 |             return self.filler_result(spec,ctx,output_path,str(e))
  57 | 
  58 |     def _render(self,spec,ctx,output_path):
  59 |         clip=spec.clip()
  60 |         if not clip or not clip.exists() or clip.stat().st_size<50000:
  61 |             return self.filler_result(spec,ctx,output_path,"clip missing")
  62 |         dur=ffprobe_duration(clip)
  63 |         if dur<2.0:
  64 |             return self.filler_result(spec,ctx,output_path,"clip too short")
  65 |         info=ffprobe_streams(clip)
  66 |         streams=info.get("streams",[])
  67 |         has_v=any(s.get("codec_type")=="video" for s in streams)
  68 |         has_a=any(s.get("codec_type")=="audio" for s in streams)
  69 |         if not has_v:
  70 |             return self.filler_result(spec,ctx,output_path,"clip no video")
  71 |         hdr=_is_hdr(clip)
  72 |         ch=_safe_label(spec.headline or "PARTNER SIGNAL")
  73 |         sl="PROTOCOL PULSE  PARTNER CLIP"
  74 |         lty=VIDEO_H-LT_HEIGHT-LT_Y_OFFSET
  75 |         tmp=output_path.with_suffix(".tmp.mp4")
  76 |         W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
  77 |         fb,fm=str(FONT_BOLD),str(FONT_MONO)
  78 |         cw,cr=COLOR_WHITE,COLOR_RED
  79 |         sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)
  80 |         vfg=";".join([
  81 |             "[0:v]scale="+W+":"+H+":force_original_aspect_ratio=increase,"
  82 |             "crop="+W+":"+H+","
  83 |             +(_tonemap_filter()+"," if hdr else "")
  84 |             +"setsar=1,format="+pf+",setpts=PTS-STARTPTS[vn]",
  85 |             "[vn]drawbox=x=0:y="+str(lty)+":w="+W+":h="+str(LT_HEIGHT)+
  86 |                 ":color=black@"+LT_BG_ALPHA+":t=fill[lb]",
  87 |             "[lb]drawtext=fontfile="+fb+":text="+ch+
  88 |                 ":fontcolor="+cw+":fontsize=28:x=32:y="+str(lty+12)+"[lc]",
  89 |             "[lc]drawtext=fontfile="+fm+":text="+sl+
  90 |                 ":fontcolor="+cr+":fontsize=18:x=32:y="+str(lty+46)+"[v_out]",
  91 |         ])
  92 |         afg=("[{i}:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
  93 |              "asetpts=PTS-STARTPTS,alimiter=limit="+lim+":attack=5:release=50[a_out]")
  94 |         if has_a:
  95 |             fg=vfg+";"+afg.format(i=0)
  96 |             inputs=[["--i",str(clip)]]
  97 |             inputs[0][0]="-i"
  98 |         else:
  99 |             logger.warning("[partner_clip] no audio: "+clip.name)
 100 |             fg=vfg+";"+afg.format(i=1)
 101 |             inputs=[["--i",str(clip)],["--f","lavfi","--i","anullsrc=r="+sr+":cl=stereo"]]
 102 |             inputs[0][0]="-i";inputs[1][0]="-f";inputs[1][2]="-i"
 103 |         flat=[str(x) for i in inputs for x in i]
 104 |         ok=run_ffmpeg(flat+["-filter_complex",fg,
 105 |             "-map","[v_out]","-map","[a_out]",
 106 |             "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
 107 |             "-r",str(VIDEO_FPS),"-pix_fmt",pf,
 108 |             "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
 109 |             "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
 110 |             "partner_clip rank="+str(spec.clip_rank),300)
 111 |         if not ok or not tmp.exists() or tmp.stat().st_size<1000:
 112 |             tmp.unlink(missing_ok=True)
 113 |             return self.filler_result(spec,ctx,output_path,"encode failed")
 114 |         passed,summary=ffprobe_contract(tmp)
 115 |         atomic_rename(tmp,output_path)
 116 |         actual=summary.get("duration",dur)
 117 |         logger.info("[partner_clip] OK rank="+str(spec.clip_rank))
 118 |         return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
 119 |                                contract_passed=passed,degraded=not passed,ffprobe_summary=summary)
 120 | 
```

### File: video_pipeline_v3/assembler_v2/segments/data_segment.py (185 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,get_chart_path
   8 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
   9 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  10 |     AUDIO_LIMITER,BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,COLOR_CYAN,FONT_BOLD,FONT_MONO)
  11 | logger=logging.getLogger(__name__)
  12 | 
  13 | KEYWORD_MAP={
  14 |     "price":"price","$":"price","dollar":"price","usd":"price",
  15 |     "hashrate":"hashrate","eh/s":"hashrate","mining":"hashrate",
  16 |     "miner":"hashrate","difficulty":"hashrate","exahash":"hashrate",
  17 |     "mempool":"mempool","fee":"mempool","sat/vb":"mempool",
  18 |     "transaction":"mempool","congestion":"mempool","backlog":"mempool",
  19 | }
  20 | 
  21 | def _detect_keyword(text):
  22 |     t=text.lower()
  23 |     for kw,cat in KEYWORD_MAP.items():
  24 |         if kw in t: return cat
  25 |     return ""
  26 | 
  27 | METRICS_CACHE_TTL=120  # seconds — cache valid for 2 minutes
  28 | 
  29 | 
  30 | def _refresh_metrics_cache(cache_path):
  31 |     """Fetch all metrics and write to cache. Called in background thread."""
  32 |     import json,urllib.request,time
  33 |     data={}
  34 |     try:
  35 |         with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=4) as resp:
  36 |             d=json.loads(resp.read())
  37 |             data["price"]="$"+"{:,}".format(d.get("USD",0))
  38 |     except Exception:
  39 |         pass
  40 |     try:
  41 |         with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=4) as resp:
  42 |             d=json.loads(resp.read())
  43 |             data["hashrate"]=str(round(d.get("currentHashrate",0)/1e18,1))+" EH/s"
  44 |     except Exception:
  45 |         pass
  46 |     try:
  47 |         with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=4) as resp:
  48 |             d=json.loads(resp.read())
  49 |             data["mempool"]=str(round(d.get("mempool_byte_per_vbyte",0),1))+" sat/vB"
  50 |     except Exception:
  51 |         pass
  52 |     if data:
  53 |         data["_ts"]=time.time()
  54 |         try:
  55 |             import json as j
  56 |             open(str(cache_path),"w").write(j.dumps(data))
  57 |         except Exception:
  58 |             pass
  59 | 
  60 | 
  61 | def _get_metric(key,fallback,cache_path):
  62 |     """
  63 |     Cache-first metric fetch. Scoped to episode workdir — no /tmp races.
  64 |     Refreshes cache in background thread, falls back to quick API call.
  65 |     On any failure: returns fallback immediately, never raises.
  66 |     """
  67 |     import json,time,threading
  68 |     from pathlib import Path
  69 |     cp=Path(cache_path)
  70 |     try:
  71 |         cache=json.loads(cp.read_text())
  72 |         age=time.time()-cache.get("_ts",0)
  73 |         if age<METRICS_CACHE_TTL and key in cache:
  74 |             return cache[key]
  75 |         # Stale — refresh in background, use stale value
  76 |         threading.Thread(target=_refresh_metrics_cache,args=(cp,),daemon=True).start()
  77 |         if key in cache:
  78 |             return cache[key]
  79 |     except Exception:
  80 |         # Cache missing — fire background refresh
  81 |         threading.Thread(target=_refresh_metrics_cache,args=(cp,),daemon=True).start()
  82 |     # One-shot fallback with short timeout — won't block long
  83 |     try:
  84 |         import urllib.request
  85 |         if key=="price":
  86 |             with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=2) as resp:
  87 |                 return "$"+"{:,}".format(json.loads(resp.read()).get("USD",0))
  88 |         if key=="hashrate":
  89 |             with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=2) as resp:
  90 |                 return str(round(json.loads(resp.read()).get("currentHashrate",0)/1e18,1))+" EH/s"
  91 |         if key=="mempool":
  92 |             with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=2) as resp:
  93 |                 return str(round(json.loads(resp.read()).get("mempool_byte_per_vbyte",0),1))+" sat/vB"
  94 |     except Exception:
  95 |         pass
  96 |     return fallback
  97 | 
  98 | def _safe(text,n=30):
  99 |     t=text.strip()[:n]
 100 |     for o,s in [(chr(92),chr(92)*2),(chr(39),""),(chr(58),chr(92)+chr(58)),
 101 |                 (chr(37),chr(92)+chr(37)),(chr(91),chr(92)+chr(91)),(chr(93),chr(92)+chr(93)),
 102 |                 (chr(44),chr(92)+chr(44)),(chr(59),chr(92)+chr(59))]:
 103 |         t=t.replace(o,s)
 104 |     return t.replace(chr(10)," ")
 105 | 
 106 | class DataSegment(Segment):
 107 |     """Bitcoin data overlay: live metrics + keyword-matched chart. Optional segment."""
 108 |     criticality="optional"
 109 | 
 110 |     def render(self,spec,ctx,output_path,idx):
 111 |         try:
 112 |             return self._render(spec,ctx,output_path)
 113 |         except Exception as e:
 114 |             logger.error("[data] exception: "+str(e))
 115 |             return self.filler_result(spec,ctx,output_path,str(e))
 116 | 
 117 |     def _render(self,spec,ctx,output_path):
 118 |         tts=spec.tts()
 119 |         if not tts or not tts.exists() or tts.stat().st_size<1000:
 120 |             return self.filler_result(spec,ctx,output_path,"TTS missing")
 121 |         dur=ffprobe_duration(tts)
 122 |         if dur<0.5:
 123 |             return self.filler_result(spec,ctx,output_path,"TTS silent")
 124 |         keyword=spec.chart_keyword or _detect_keyword(spec.body+" "+spec.headline)
 125 |         chart=get_chart_path(keyword)
 126 |         cache_path=ctx.workdir/"metrics_cache.json"
 127 |         btc=_safe(_get_metric("price",spec.btc_price or "$N/A",cache_path),20)
 128 |         hr=_safe(_get_metric("hashrate","N/A EH/s",cache_path),20)
 129 |         mp=_safe(_get_metric("mempool","N/A sat/vB",cache_path),20)
 130 |         hl=_safe(spec.headline or "BITCOIN SIGNAL",45)
 131 |         tmp=output_path.with_suffix(".tmp.mp4")
 132 |         W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
 133 |         fb,fm=str(FONT_BOLD),str(FONT_MONO)
 134 |         cw,cr,cc=COLOR_WHITE,COLOR_RED,COLOR_CYAN
 135 |         sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)
 136 | 
 137 |         if BG_LOOP.exists():
 138 |             inputs=[["-stream_loop","-1","-i",str(BG_LOOP)],["-i",str(tts)]]
 139 |             bg_fg="[0:v]scale="+W+":"+H+",setsar=1,format="+pf+",setpts=PTS-STARTPTS[bg]"
 140 |         else:
 141 |             inputs=[["-f","lavfi","-i","color=c="+COLOR_BG+":s="+W+"x"+H+":r="+str(VIDEO_FPS)],["-i",str(tts)]]
 142 |             bg_fg="[0:v]format="+pf+",setpts=PTS-STARTPTS[bg]"
 143 | 
 144 |         if chart and chart.exists():
 145 |             inputs.append(["-loop","1","-framerate",str(VIDEO_FPS),"-i",str(chart)])
 146 |             ci=str(len(inputs)-1)
 147 |             chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
 148 |                 +"[mp]drawtext=fontfile="+fb+":text="+hl+":fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
 149 |                 +"[h1]drawtext=fontfile="+fm+":text="+btc+":fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
 150 |                 +"[m1]drawtext=fontfile="+fm+":text="+hr+":fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
 151 |                 +"[m2]drawtext=fontfile="+fm+":text="+mp+":fontcolor="+cw+":fontsize=22:x=20:y=152[v_m];"
 152 |                 +"["+ci+":v]scale=1340:754:force_original_aspect_ratio=decrease,"
 153 |                 +"pad=1340:754:(ow-iw)/2:(oh-ih)/2:"+COLOR_BG+",format="+pf+"[chart];"
 154 |                 +"[v_m][chart]overlay=x=490:y=163:eof_action=repeat[v_out]")
 155 |             fg=bg_fg+";"+chart_fg
 156 |         else:
 157 |             no_chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
 158 |                 +"[mp]drawtext=fontfile="+fb+":text="+hl+":fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
 159 |                 +"[h1]drawtext=fontfile="+fm+":text="+btc+":fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
 160 |                 +"[m1]drawtext=fontfile="+fm+":text="+hr+":fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
 161 |                 +"[m2]drawtext=fontfile="+fm+":text="+mp+":fontcolor="+cw+":fontsize=22:x=20:y=152[v_out]")
 162 |             fg=bg_fg+";"+no_chart_fg
 163 | 
 164 |         audio_fg=("[1:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
 165 |                   "asetpts=PTS-STARTPTS,"
 166 |                   "loudnorm=I=-14:TP=-2:LRA=7:linear=true,"
 167 |                   "alimiter=limit="+lim+":attack=5:release=50[a_out]")
 168 |         fg=fg+";"+audio_fg
 169 |         flat=[str(x) for i in inputs for x in i]
 170 |         ok=run_ffmpeg(flat+["-filter_complex",fg,
 171 |             "-map","[v_out]","-map","[a_out]",
 172 |             "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
 173 |             "-r",str(VIDEO_FPS),"-pix_fmt",pf,
 174 |             "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
 175 |             "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
 176 |             "data_segment keyword="+keyword,180)
 177 |         if not ok or not tmp.exists() or tmp.stat().st_size<1000:
 178 |             tmp.unlink(missing_ok=True)
 179 |             return self.filler_result(spec,ctx,output_path,"data encode failed")
 180 |         passed,summary=ffprobe_contract(tmp)
 181 |         atomic_rename(tmp,output_path)
 182 |         logger.info("[data] OK ("+str(round(dur,1))+"s chart="+keyword+")")
 183 |         return RenderedSegment(spec=spec,path=str(output_path),duration=summary.get("duration",dur),
 184 |                                contract_passed=passed,degraded=not passed,ffprobe_summary=summary)
 185 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
