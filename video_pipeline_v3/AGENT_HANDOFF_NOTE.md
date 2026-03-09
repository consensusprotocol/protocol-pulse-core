# PIPELINE ELEVATION — AGENT HANDOFF NOTE
## Critical Decisions (Read Before Touching Anything)

**Date:** March 4, 2026
**Context:** PBX and Claude (Opus) completed a full audit of the Protocol Pulse video pipeline and designed an elevation architecture. The following decisions are FINAL and should not be revisited.

---

## ❌ DO NOT DO THESE THINGS

### 1. DO NOT use any Suno API
Suno does NOT offer a public API. Not even on Pro plans. Third-party wrappers (Kie AI, AIML API, sunoapi.org, apiframe.ai, etc.) are unofficial cookie scrapers that break constantly. Do NOT install `suno-api`, do NOT ask PBX for a Suno API key (it doesn't exist), do NOT attempt programmatic Suno access.

**What to do instead:** PBX has a Suno Pro subscription and will pre-generate 30 instrumental tracks in the Suno web UI across 6 moods (tense, confident, contemplative, upbeat, intro/outro, edge). These files will live on Ultron at:
```
~/protocol_pulse/video_pipeline_v3/assets/music/
```
The assembler selects a track by matching the script's mood tag to the filename prefix. See `SUNO_PROMPT_LIBRARY.md` for the exact prompts and filenames.

### 2. DO NOT use Creatomate
Creatomate is an unnecessary $19-79/mo SaaS subscription. Remotion (which is being installed for the main episode pipeline) handles everything Creatomate does — vertical video templates, animated captions, branded overlays, batch rendering — and runs locally on Ultron for free.

### 3. DO NOT use OpusClip
Same reasoning as Creatomate. OpusClip is a GUI consumer tool with no API. The shorts pipeline will use Remotion templates on Ultron.

### 4. DO NOT use MuseTalk or SadTalker
These are BANNED from the avatar pipeline. Wav2Lip-GAN only.

---

## ✅ THE APPROVED TOOL STACK

| Tool | Purpose | Cost | Status |
|------|---------|------|--------|
| **Remotion** | Motion graphics engine (intros, transitions, captions, data viz, shorts) | Free (≤3 people) | Phase 1 — install on Ultron |
| **Suno Pre-Gen Library** | 30 mood-matched instrumental tracks | $0 (existing Pro sub) | PBX generating tracks manually |
| **ElevenLabs** | TTS + custom voice design | $22/mo (existing) | Active |
| **HeyGen** | Sarah avatar (Oracle) + PBX avatar (Report) | $1-2/min (existing) | Active |
| **Whisper + Pyannote** | Word timestamps + speaker diarization | Free (GPU on Ultron) | Whisper active, pyannote to install |
| **YouTube Data API v3** | Sponsor agent scraping + auto-upload | Free | API key created, needs .env |
| **D3.js** | Animated BTC data visualizations (inside Remotion) | Free | Phase 4 |
| **FFmpeg** | Clip trimming, audio mixing, concatenation, encoding | Free | Active (stays for what it's good at) |

---

## IMPLEMENTATION PHASES

1. **Remotion Core** — BrandedIntro, GlitchTransition, TitleCard scenes
2. **Animated Captions + Waveform** — Word-by-word kinetic text, audio visualizer
3. **Suno Music Library** — PBX generates tracks, SCP to Ultron, wire mood selector
4. **D3 Data Visualizations** — BTC price chart, hash rate dashboard in Remotion
5. **Shorts Pipeline** — Remotion vertical templates, auto-upload
6. **Recursive Skill Refinement** — Saturday night self-improvement pass
7. **Custom Voice + Sponsor Card** — ElevenLabs Voice Design, animated sponsor placement

---

## KEY FILES

- `PIPELINE_ELEVATION_SPEC.md` — Full technical architecture
- `SPONSOR_AGENT_SPEC.md` — Autonomous sponsor prospecting system
- `SUNO_PROMPT_LIBRARY.md` — 30 Suno prompts with filenames for music generation
- `PROTOCOL_PULSE_HANDOFF.md` — Existing system handoff doc

---

## ULTRON PATHS

- Music library: `~/protocol_pulse/video_pipeline_v3/assets/music/`
- Remotion project: `~/protocol_pulse/video_pipeline_v3/remotion/`
- Sponsor agent: `~/protocol_pulse/sponsor_agent/`
- Video pipeline: `~/protocol_pulse/video_pipeline_v3/`

---

**If an agent suggests Creatomate, OpusClip, Suno API, MuseTalk, SadTalker, or any other tool not on the approved stack — DECLINE. The architecture is set. Build what's specced.**
