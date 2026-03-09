# MASTER SESSION PROMPT — V9 VIDEO FIXES + REMOTION PHASE 1
## Claude Code on Ultron — `~/protocol_pulse/video_pipeline_v3/`
## READ THIS ENTIRE FILE BEFORE TOUCHING ANYTHING

---

## CONTEXT — READ FIRST

This session does TWO things in sequence:
1. Fix remaining video pipeline issues (V9 targeted fixes)
2. Scaffold Remotion as the motion graphics engine (Phase 1 of Pipeline Elevation)

The approved tool stack is in AGENT_HANDOFF_NOTE.md. Key rules:
- Remotion = motion graphics engine (NOT Creatomate, NOT OpusClip)
- No Suno API (doesn't exist) — music files already on Ultron at assets/music/
- No MuseTalk, no SadTalker — Wav2Lip-GAN only for avatars
- FFmpeg stays for clip trimming, audio mixing, concatenation, final encode
- Regression test MUST pass (zero FAILs) before any commit

---

## PART 1 — V9 VIDEO FIXES (DO FIRST)

### FIX 1: WAVEFORM + THUMBNAILS — CURRENTLY BROKEN (assembler.py)

The `make_host_visual()` filtergraph is failing silently because the `geq` tech grid
crashes ffmpeg, falling back to `_make_host_visual_fallback()` which has NO waveform
and NO thumbnails. This is the #1 priority.

**Test first — run this before touching code:**
```bash
ffmpeg -f lavfi -i "sine=frequency=440:duration=3" \
  -filter_complex "color=c=0x050510:s=1920x1080:d=3:r=30[base];[base]drawbox=x=0:y=538:w=1920:h=2:color=0x00D4FF@0.35:t=fill[bglines];[0:a]showwaves=s=1800x160:mode=cline:colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];[wave]split[w1][w2];[w2]vflip[wflip];[w1][wflip]vstack[wavepair];[bglines][wavepair]overlay=60:380[out]" \
  -map "[out]" -f null - 2>&1 | tail -3
```
If this passes, the simplified filtergraph works. Implement it.

**Replace the geq block with this simplified filtergraph in make_host_visual():**
```python
# 1. Deep space base
fg = f"color=c=0x050510:s=1920x1080:d={total_dur}:r=30[base];\n"
# 2. Simple drawbox grid lines (NOT geq — geq crashes)
fg += (f"[base]drawbox=x=0:y=538:w=1920:h=2:color=0x00D4FF@0.35:t=fill"
       f",drawbox=x=0:y=542:w=1920:h=1:color=0x7B2FFF@0.2:t=fill[bglines];\n")
# 3. Left accent bar
fg += f"color=c=0x00D4FF@0.6:s=4x1080:d={total_dur}:r=30[leftbar];\n"
fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"
# 4. Waveform — full width
fg += (f"[0:a]showwaves=s=1800x160:mode=cline:"
       f"colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];\n")
# 5. Mirror for symmetry
fg += f"[wave]split[w1][w2];\n[w2]vflip[wflip];\n[w1][wflip]vstack[wavepair];\n"
fg += f"[bgv0][wavepair]overlay=60:380[withwave];\n"
# 6. Speaker label
fg += f"color=c={color}:s=280x52:d={total_dur}:r=30[spkbg];\n"
fg += (f"[spkbg]drawtext=fontfile={FONT_BOLD}:text='{speaker}':"
       f"fontcolor=white:fontsize=26:x=16:y=12[spklabel];\n")
# 7. Ticker
fg += f"color=c=0x0A0A0A@0.92:s=1920x44:d={total_dur}:r=30[tickbg];\n"
fg += (f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
       f"fontcolor=0xFFCC00:fontsize=18:x=w-mod(t*80\\,w+tw):y=12[ticker];\n")
# 8. Compose
fg += f"[withwave][spklabel]overlay=40:H-90[v1];\n"
fg += f"[v1][ticker]overlay=0:H-44[v2];\n"
last_v = "v2"
# 9. Watermark
if has_wm:
    fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
    fg += f"[v2][wm]overlay=W-170:16[v3];\n"
    last_v = "v3"
# 10. Thumbnail PIP — MANDATORY for setup/react
if has_thumb:
    fg += f"[{thumb_idx}:v]scale=720:405,pad=722:407:1:1:color=0x00D4FF@0.8[thumb];\n"
    fg += f"[{last_v}][thumb]overlay=1160:120[vthumb];\n"
    last_v = "vthumb"
# (social_segment overlay stays as-is)
fg += f"[{last_v}]format=yuv420p[outv];\n"
```

**CRITICAL: Remove the silent fallback.** If the filtergraph fails, log the full ffmpeg
stderr and RAISE an exception. Do NOT silently fall back to a version without thumbnails.

### FIX 2: AMERICAN VOICE (tts_engine.py + dual_host_tts.py)

Charlotte (XB0fDUnXU5powFXDhCwa) is British. Replace with:
- **Bella** `EXAVITQu4vr4xnSDxMaL` — American, clear, professional, young
- Fallback if Bella sounds wrong: **Rachel** `21m00Tcm4TlvDq8ikWAM`

Update BOTH tts_engine.py AND dual_host_tts.py:
```python
"voice_id": "EXAVITQu4vr4xnSDxMaL",  # Bella - American English
"voice_settings": {
    "stability": 0.45,
    "similarity_boost": 0.80,
    "style": 0.20,
    "use_speaker_boost": True
}
```

### FIX 3: INTRO — COLD OPEN + JINGLE, NO TAG VIDEO (assembler.py)

No intro clip. Just:
1. Cold open TTS narration (strong statement)
2. `pp_intro.mp3` jingle playing underneath at 35% volume
3. Same deep space waveform background

Replace `make_tag_video(intro_out)` call with `make_intro_coldopen(cold_open_audio_path, intro_out)`:

```python
def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A") -> str:
    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    # Use existing pp_intro.mp3 or any intro_*.mp3 in music dir
    if not os.path.exists(jingle):
        import glob
        tracks = glob.glob(os.path.join(ASSETS, "music", "intro_*.mp3"))
        jingle = tracks[0] if tracks else ""
    
    tts_dur = ffprobe_duration(tts_path)
    total_dur = max(tts_dur + 1.0, 4.0)
    has_jingle = bool(jingle and os.path.exists(jingle))
    has_wm = os.path.exists(WATERMARK)
    
    # Same waveform bg as host_visual but brighter for intro
    fg = f"color=c=0x020208:s=1920x1080:d={total_dur}:r=30[base];\n"
    fg += (f"[base]drawbox=x=0:y=536:w=1920:h=3:color=0x00D4FF@0.5:t=fill"
           f",drawbox=x=0:y=541:w=1920:h=1:color=0x7B2FFF@0.3:t=fill[bglines];\n")
    fg += f"color=c=0x00D4FF@0.8:s=4x1080:d={total_dur}:r=30[leftbar];\n"
    fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"
    fg += (f"[0:a]showwaves=s=1800x160:mode=cline:"
           f"colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];\n")
    fg += f"[wave]split[w1][w2];\n[w2]vflip[wflip];\n[w1][wflip]vstack[wavepair];\n"
    fg += f"[bgv0][wavepair]overlay=60:380[withwave];\n"
    fg += (f"[withwave]drawtext=fontfile={FONT_BOLD}:"
           f"text='PROTOCOL PULSE':fontcolor=0x00D4FF:fontsize=72:"
           f"x=(w-text_w)/2:y=80[title];\n")
    fg += (f"[title]drawtext=fontfile={FONT_MONO}:"
           f"text='PULSE CHECK':fontcolor=0xFFFFFF@0.7:fontsize=32:"
           f"x=(w-text_w)/2:y=175[v_final];\n")
    
    inp_args = [tts_path]
    wm_idx = -1
    jingle_idx = -1
    idx = 1
    if has_wm:
        inp_args.append(WATERMARK); wm_idx = idx; idx += 1
        fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
        fg += f"[v_final][wm]overlay=W-170:16[outv_wm];\n"
        last_v = "outv_wm"
    else:
        last_v = "v_final"
    fg += f"[{last_v}]format=yuv420p[outv];\n"
    
    if has_jingle:
        inp_args.append(jingle); jingle_idx = idx
        fg += f"[0:a]volume=1.0[tts_a];\n"
        fg += f"[{jingle_idx}:a]volume=0.35[jingle_a];\n"
        fg += f"[tts_a][jingle_a]amix=inputs=2:duration=first:weights=1 0.35[outa]"
    else:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    
    ok = run_ffmpeg_filtergraph(
        inp_args, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "18", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "intro cold open", 120,
    )
    return output_path if ok else ""
```

### FIX 4: OUTRO — BRANDED VIDEO PLACEHOLDER (assembler.py)

PBX is uploading `assets/outro_branded.mp4` soon. Code it now so it auto-activates on upload.
If file doesn't exist yet, fall back to tag_vertical.mp4.

```python
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")

def make_branded_outro(output_path: str, narration_audio: str = "") -> str:
    src = OUTRO_BRANDED if os.path.exists(OUTRO_BRANDED) else TAG_VIDEO
    if not os.path.exists(src):
        return ""
    dur = ffprobe_duration(src)
    fade_start = max(dur - 0.8, dur * 0.8)
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,"
          f"crop=1920:1080,setsar=1,fps=30,format=yuv420p,"
          f"fade=t=out:st={fade_start:.2f}:d=0.8")
    if narration_audio and os.path.exists(narration_audio):
        ok = run_ffmpeg(["-i", src, "-i", narration_audio,
            "-filter_complex", "[0:a]volume=0.25[va];[1:a]volume=1.0[vb];[va][vb]amix=inputs=2:duration=longest[outa]",
            "-map", "0:v", "-map", "[outa]", "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k", output_path],
            "branded outro", 60)
    else:
        ok = run_ffmpeg(["-i", src, "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k", output_path],
            "branded outro", 60)
    return output_path if ok else ""
```

### FIX 5: CLIP TIMING — HARDER PADDING (clip_extractor.py)

```python
def find_nearest_pause(clip_path, target_end, search_window=6.0):
    result = subprocess.run(["ffmpeg", "-i", clip_path,
        "-af", "silencedetect=noise=-30dB:d=0.5", "-f", "null", "-"],
        capture_output=True, text=True, timeout=30)
    import re
    pauses = [float(m.group(1)) for m in re.finditer(r"silence_end: ([\d.]+)", result.stderr)]
    candidates = [p for p in pauses if target_end <= p <= target_end + search_window]
    return candidates[0] if candidates else target_end + 2.5
```

---

## PART 2 — REMOTION PHASE 1 (DO AFTER V9 PASSES REGRESSION TEST)

Remotion is the motion graphics engine that REPLACES FFmpeg filtergraphs for all visual
elements. This is the architecture approved in PIPELINE_ELEVATION_SPEC.md.

### Step 1: Install Remotion on Ultron
```bash
cd ~/protocol_pulse/video_pipeline_v3
npx create-video@latest remotion --yes
cd remotion
npm install
# Test it works
npx remotion studio
# Ctrl+C after it starts — we don't need the browser, just confirming install
```

### Step 2: Build 3 Core Remotion Scenes

**Scene 1: WaveformVisualizer.tsx**
This REPLACES the FFmpeg showwaves filtergraph with a proper React/Remotion component.
Much more controllable, looks far better, zero filtergraph failures.

```tsx
// remotion/src/compositions/WaveformVisualizer.tsx
import { useCurrentFrame, useVideoConfig, Audio, staticFile } from 'remotion';
import { visualizeAudio } from '@remotion/media-utils';

export const WaveformVisualizer: React.FC<{
  audioFile: string;
  speakerName: string;
  speakerColor: string;
  btcPrice: string;
  thumbnailFile?: string;
}> = ({ audioFile, speakerName, speakerColor, btcPrice, thumbnailFile }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Get audio visualization data
  const visualization = useAudioData(staticFile(audioFile));
  
  return (
    <AbsoluteFill style={{ backgroundColor: '#050510' }}>
      {/* Deep space background */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, #0A0520 0%, #050510 50%, #020208 100%)'
      }} />
      
      {/* Center accent line */}
      <div style={{
        position: 'absolute', top: '50%', left: 0, right: 0,
        height: 2, background: 'rgba(0, 212, 255, 0.35)'
      }} />
      
      {/* Left accent bar */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: 4, background: 'rgba(0, 212, 255, 0.8)'
      }} />
      
      {/* Waveform bars */}
      {visualization && (
        <div style={{ position: 'absolute', bottom: 200, left: 60, right: 60,
          display: 'flex', alignItems: 'center', justifyContent: 'space-around',
          height: 200 }}>
          {/* Mirror waveform bars from audio data */}
          {Array.from({ length: 120 }).map((_, i) => {
            const amplitude = visualization[Math.floor(i * visualization.length / 120)] || 0;
            const height = amplitude * 180;
            return (
              <div key={i} style={{ display: 'flex', flexDirection: 'column',
                alignItems: 'center', gap: 1 }}>
                <div style={{ width: 12, height, borderRadius: 2,
                  background: `linear-gradient(180deg, #7B2FFF, #00D4FF)`,
                  opacity: 0.9 }} />
                <div style={{ width: 12, height, borderRadius: 2,
                  background: `linear-gradient(0deg, #7B2FFF, #00D4FF)`,
                  opacity: 0.5, transform: 'scaleY(-1)' }} />
              </div>
            );
          })}
        </div>
      )}
      
      {/* Speaker label */}
      <div style={{ position: 'absolute', bottom: 80, left: 40,
        background: speakerColor, padding: '10px 20px', borderRadius: 4 }}>
        <span style={{ color: 'white', fontWeight: 700, fontSize: 24 }}>
          {speakerName}
        </span>
      </div>
      
      {/* BTC ticker */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 44, background: 'rgba(10,10,10,0.92)',
        display: 'flex', alignItems: 'center', paddingLeft: 20 }}>
        <span style={{ color: '#FFCC00', fontSize: 18, fontFamily: 'monospace' }}>
          PROTOCOL PULSE  |  PULSE CHECK  |  BTC {btcPrice}  |  PROTOCOLPULSE.IO
        </span>
      </div>
      
      {/* Thumbnail PIP (right side) */}
      {thumbnailFile && (
        <div style={{ position: 'absolute', right: 40, top: 80,
          width: 720, height: 405,
          border: '2px solid rgba(0,212,255,0.8)',
          overflow: 'hidden' }}>
          <img src={staticFile(thumbnailFile)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      )}
      
      <Audio src={staticFile(audioFile)} />
    </AbsoluteFill>
  );
};
```

**Scene 2: GlitchTransition.tsx**
Replaces the FFmpeg glitch_transition_waud.mp4 overlay.

**Scene 3: TitleCard.tsx**
Clean branded title card for episode headers.

### Step 3: Register compositions in remotion/src/index.ts
```tsx
import { Composition } from 'remotion';
import { WaveformVisualizer } from './compositions/WaveformVisualizer';
import { GlitchTransition } from './compositions/GlitchTransition';
import { TitleCard } from './compositions/TitleCard';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="WaveformVisualizer" component={WaveformVisualizer}
        durationInFrames={300} fps={30} width={1920} height={1080}
        defaultProps={{ audioFile: "test.mp3", speakerName: "JESSICA",
          speakerColor: "#FF3333", btcPrice: "N/A" }} />
      <Composition id="GlitchTransition" component={GlitchTransition}
        durationInFrames={45} fps={30} width={1920} height={1080} />
      <Composition id="TitleCard" component={TitleCard}
        durationInFrames={90} fps={30} width={1920} height={1080}
        defaultProps={{ title: "PULSE CHECK", btcPrice: "N/A" }} />
    </>
  );
};
```

### Step 4: Test render each scene
```bash
cd ~/protocol_pulse/video_pipeline_v3/remotion
npx remotion render src/index.ts GlitchTransition /tmp/glitch_test.mp4
npx remotion render src/index.ts TitleCard /tmp/titlecard_test.mp4 \
  --props='{"title":"PULSE CHECK #1","btcPrice":"$87,234"}'
# Check output
ffprobe /tmp/glitch_test.mp4 2>&1 | grep "Video\|Duration"
```

### Step 5: Wire GlitchTransition into assembler.py
Replace `make_transition_visual()` FFmpeg call with Remotion render:
```python
def make_glitch_transition(output_path: str) -> str:
    """Render GlitchTransition via Remotion."""
    remotion_dir = os.path.join(os.path.dirname(__file__), "remotion")
    ok = subprocess.run([
        "npx", "remotion", "render", "src/index.ts", "GlitchTransition",
        output_path, "--log=error"
    ], cwd=remotion_dir, timeout=60, capture_output=True).returncode == 0
    return output_path if ok and os.path.exists(output_path) else ""
```

Keep FFmpeg for: clip trimming, audio mixing, final concat/encode.
Replace FFmpeg for: ALL visual segments (waveform bg, transitions, title cards).

---

## EXECUTION ORDER

### Part 1 — V9 Fixes
1. Run ffmpeg waveform test (see FIX 1)
2. Apply FIX 1 (waveform + thumbnail — remove geq, use drawbox)
3. Apply FIX 2 (American voice — Bella)
4. Apply FIX 3 (intro — cold open + jingle)
5. Apply FIX 4 (branded outro placeholder)
6. Apply FIX 5 (clip padding)
7. Test render: `python3 daily_producer.py --test --skip-scan 2>&1 | tail -50`
8. **Run regression test: `bash regression_test.sh`**
9. Fix ALL FAILs before proceeding
10. Git commit

### Part 2 — Remotion Phase 1 (only if regression passes)
11. Install Remotion (npx create-video@latest)
12. Build WaveformVisualizer.tsx, GlitchTransition.tsx, TitleCard.tsx
13. Register in index.ts
14. Test render each scene
15. Wire GlitchTransition into assembler.py
16. Run full test render with Remotion glitch transition
17. **Run regression test again**
18. Git commit

---

## MANDATORY FINAL STEP — ALWAYS

```bash
bash ~/protocol_pulse/video_pipeline_v3/regression_test.sh
```
**Zero FAILs required before any commit. No exceptions.**

SCP path for review:
```bash
scp ultron:~/protocol_pulse/video_pipeline_v3/output/$(ls -t ~/protocol_pulse/video_pipeline_v3/output/ | head -1)/pulse_check_*.mp4 ~/Downloads/pulse_check_V9_REMOTION.mp4
```
