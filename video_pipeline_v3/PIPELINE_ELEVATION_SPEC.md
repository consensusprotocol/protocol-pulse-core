# PROTOCOL PULSE — PIPELINE ELEVATION SPEC
## "Nothing Like This Exists"

---

## THE VISION

Every Bitcoin media company has a human editing timeline. Every one of them has a guy in Premiere Pro dragging clips around. You're going to have an autonomous pipeline that generates broadcast-quality motion graphics, unique soundtracks, animated captions, data-driven visualizations, and cinematic transitions — all from code. No human touches the timeline. Ever.

Here's every tool, what it replaces, and why it matters.

---

## 1. REMOTION — Motion Graphics Engine
**Replaces:** FFmpeg filtergraphs for all visual effects
**Cost:** Free for teams ≤3 people (you qualify)
**Runs on:** Ultron (Node.js + Chromium headless rendering)

### What It Does
React components that render to video frames. You write a `<BrandedIntro>` component once, and every episode gets a pixel-perfect animated intro. No filtergraph. No silent failures. Deterministic output.

### Remotion Skills + Claude Code
As of January 2026, Remotion has official "Agent Skills" integration with Claude Code. You tell Claude Code in natural language: "Create a 5-second title card with 'WHAT THE BITCOIN INTERNET IS SAYING' that glitches in letter by letter on a dark navy background" — and it writes the Remotion component, previews it in browser, and renders to MP4.

### Scene Templates to Build (7)

```
remotion/src/compositions/
├── BrandedIntro.tsx        # Protocol Pulse logo animation + music sync
├── TitleCard.tsx           # Episode title with BTC price ticker
├── WaveformVisualizer.tsx  # Reactive audio bars on deep space navy bg
├── ThumbnailOverlay.tsx    # YouTube thumbnail PIP with slide-in animation
├── GlitchTransition.tsx    # Branded glitch effect between segments
├── SocialCard.tsx          # "WHAT THE BITCOIN INTERNET IS SAYING" card
├── OutroBranded.tsx        # Animated outro with CTA + affiliate links
├── BTCDataTicker.tsx       # Live BTC price, hash rate, difficulty
└── SponsorCard.tsx         # 15-second animated sponsor placement
```

### How It Integrates

```
CURRENT:  script → tts → ffmpeg (everything) → mp4
UPGRADED: script → tts → remotion (graphics) + ffmpeg (encode/concat) → mp4
```

The assembler calls Remotion CLI to render individual segments:
```bash
npx remotion render src/index.ts BrandedIntro out/intro.mp4 --props='{"title":"Pulse Check #47"}'
npx remotion render src/index.ts GlitchTransition out/glitch.mp4
npx remotion render src/index.ts SocialCard out/social_card.mp4 --props='{"tweets":[...]}'
```

Then FFmpeg concats these with the clips and narration audio — which is what FFmpeg is actually good at.

### Implementation
```bash
# On Ultron
cd ~/protocol_pulse/video_pipeline_v3
npx create-video@latest remotion   # scaffolds project
cd remotion
npm install @remotion/cli @remotion/renderer
```

**Timeline:** 1 Claude Code session to scaffold + build 3 core scenes (BrandedIntro, GlitchTransition, TitleCard). Test render. Then iterate remaining 6 scenes over 2 more sessions.

---

## 2. SUNO PRE-GENERATED MUSIC LIBRARY — Mood-Matched Soundtracks
**Replaces:** Static royalty-free music beds looped across every episode
**Cost:** $0 (PBX has Suno Pro subscription, tracks pre-generated in web UI)
**Runs on:** Ultron (local files, no API needed)

### ⚠️ IMPORTANT: NO SUNO API EXISTS
Suno does NOT offer a public API, even on Pro plans. Do NOT attempt to use third-party Suno API wrappers (Kie AI, AIML API, sunoapi.org, etc.) — they are unofficial, unreliable, and use cookie scraping that breaks constantly. Do NOT install any `suno-api` packages. Do NOT ask PBX for a Suno API key — it doesn't exist.

### What It Does
30 pre-generated instrumental tracks across 6 moods live on Ultron. The script_writer tags each episode with a mood, the assembler picks a matching track. Every episode sounds different. Zero API calls, zero cost, zero failure risk.

### Music Library Location
```
~/protocol_pulse/video_pipeline_v3/assets/music/
├── tense_01.mp3 through tense_05.mp3       # Breaking news, urgent
├── confident_01.mp3 through confident_05.mp3 # Bullish, victory lap
├── contemplative_01.mp3 through contemplative_05.mp3 # Deep dive, philosophical
├── upbeat_01.mp3 through upbeat_05.mp3       # Social segment, community
├── intro_01.mp3 through intro_03.mp3         # Episode openers (30sec)
├── outro_01.mp3 through outro_02.mp3         # Episode closers (30sec)
└── edge_01.mp3 through edge_05.mp3           # Controversy, hot takes
```

### How It Works
After the script is written, the script_writer classifies the mood:
```python
MOOD_CLASSIFY_PROMPT = """Based on this Pulse Check script, classify the overall mood.
Choose exactly ONE: tense | confident | contemplative | upbeat | edge
Script: {script_text}"""
```

Then the assembler selects a track:
```python
import random
import glob

def select_music_bed(mood: str) -> str:
    """Select a random track matching the episode mood."""
    music_dir = "~/protocol_pulse/video_pipeline_v3/assets/music"
    tracks = glob.glob(f"{music_dir}/{mood}_*.mp3")
    if not tracks:
        tracks = glob.glob(f"{music_dir}/confident_*.mp3")  # safe fallback
    return random.choice(tracks)

def select_intro_music() -> str:
    tracks = glob.glob(f"{music_dir}/intro_*.mp3")
    return random.choice(tracks)

def select_outro_music() -> str:
    tracks = glob.glob(f"{music_dir}/outro_*.mp3")
    return random.choice(tracks)
```

### Why This Matters
Every other Bitcoin podcast uses the same royalty-free tracks. Listeners subconsciously associate generic music with generic content. 30 unique Suno-generated tracks across 6 moods means no two consecutive episodes sound the same. And when Suno eventually ships an official API, the assembler swaps from local file selection to API generation — the rest of the pipeline doesn't change.

### Refreshing the Library
PBX generates a fresh batch of 30 tracks in Suno's web UI every 2-3 months. SCP to Ultron. Takes 30 minutes. See `SUNO_PROMPT_LIBRARY.md` for exact prompts and filenames.

---

## 3. ANIMATED CAPTIONS — Word-by-Word Kinetic Text
**Replaces:** Static SRT burn-in via FFmpeg `subtitles` filter
**Cost:** Free (built in Remotion)
**Runs on:** Ultron

### What It Does
Instead of flat white text at the bottom of the screen, you get word-by-word animated captions that highlight the current word being spoken. Think TikTok/Reels style — the word lights up as it's said, with color emphasis on key terms (Bitcoin = orange highlight, numbers = bold).

### Implementation in Remotion
```tsx
// AnimatedCaptions.tsx
import { useCurrentFrame, interpolate, spring } from 'remotion';

const CaptionWord = ({ word, startFrame, isKeyword }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [startFrame - 3, startFrame], [0, 1]);
  const scale = spring({ frame: frame - startFrame, fps: 30, config: { damping: 12 } });
  
  return (
    <span style={{
      opacity,
      transform: `scale(${scale})`,
      color: isKeyword ? '#F7931A' : '#FFFFFF',  // Bitcoin orange for keywords
      fontWeight: isKeyword ? 800 : 500,
      textShadow: '2px 2px 8px rgba(0,0,0,0.8)',
    }}>
      {word}{' '}
    </span>
  );
};
```

### Word Timing Source
Whisper on Ultron already generates word-level timestamps. Feed those directly into the Remotion caption component as props:
```json
{
  "words": [
    {"word": "Bitcoin", "start": 0.5, "end": 0.9, "keyword": true},
    {"word": "just", "start": 0.95, "end": 1.1, "keyword": false},
    {"word": "broke", "start": 1.15, "end": 1.4, "keyword": false},
    {"word": "$200K", "start": 1.45, "end": 1.9, "keyword": true}
  ]
}
```

### Why This Matters
85% of social media video is watched without sound. Animated captions aren't a nice-to-have — they're the difference between someone scrolling past and stopping to watch. Word-by-word animation increases retention by 15-30% in the first 10 seconds according to every creator study in 2025-2026.

---

## 4. D3.js IN REMOTION — Data-Driven Bitcoin Visualizations
**Replaces:** Static screenshot of a chart
**Cost:** Free (D3 is open source, runs inside Remotion)
**Runs on:** Ultron

### What It Does
Animated, cinematic data visualizations that render as video segments. Not a screenshot of TradingView — an animated chart that draws itself, with the BTC price line racing across the screen, hash rate bars growing, difficulty adjustments pulsing.

### Scene Ideas

**BTC Price Action (30 seconds)**
- Line chart draws itself left to right over 3 seconds
- Key moments annotated with animated callouts ("Halving", "ETF Approval")
- Final price pulses with glow effect
- All data pulled live from CoinGecko API at render time

**Hash Rate Dashboard (15 seconds)**
- Bar chart of top mining pools, bars grow from zero
- Total hash rate counter ticks up in real-time
- Difficulty adjustment countdown timer
- Network health indicator (green/yellow/red pulse)

**Fear & Greed Index (10 seconds)**
- Gauge needle swings from center to current value
- Color shifts from red (fear) to green (greed)
- Historical ribbon shows last 30 days

### Implementation
D3.js runs natively inside Remotion since it's just JavaScript. You write a D3 visualization, animate it frame-by-frame using `useCurrentFrame()`, and Remotion renders it to MP4.

```tsx
// BTCPriceChart.tsx
import * as d3 from 'd3';
import { useCurrentFrame, interpolate } from 'remotion';

export const BTCPriceChart = ({ priceData }) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 90], [0, 1], { extrapolateRight: 'clamp' });
  
  // Only show data points up to current progress
  const visibleData = priceData.slice(0, Math.floor(priceData.length * progress));
  
  // D3 scales and line generator
  const xScale = d3.scaleTime().domain(d3.extent(priceData, d => d.date)).range([0, 1800]);
  const yScale = d3.scaleLinear().domain(d3.extent(priceData, d => d.price)).range([900, 100]);
  const line = d3.line().x(d => xScale(d.date)).y(d => yScale(d.price)).curve(d3.curveMonotoneX);
  
  return (
    <svg width={1920} height={1080} style={{ background: '#0a0a14' }}>
      <path d={line(visibleData)} fill="none" stroke="#F7931A" strokeWidth={3} />
      {/* Glowing dot at the tip */}
      {visibleData.length > 0 && (
        <circle 
          cx={xScale(visibleData[visibleData.length-1].date)} 
          cy={yScale(visibleData[visibleData.length-1].price)}
          r={6} fill="#F7931A" filter="url(#glow)" 
        />
      )}
    </svg>
  );
};
```

### Why This Matters
No Bitcoin show has animated data visualizations in their daily content. They all screen-share TradingView or paste a static chart image. This is an immediate visual differentiator that screams "this is not a guy in his basement."

---

## 5. ELEVENLABS VOICE DESIGN — Custom Voice Cloning
**Replaces:** Stock voice presets (Charlotte, Deborah, etc.)
**Cost:** Already on Creator plan ($22/mo, 200K chars)
**Runs on:** API call from Ultron

### What You're Missing
ElevenLabs has a Voice Design feature that lets you create a completely custom voice from a text description. And they have Professional Voice Cloning where you upload 30+ minutes of audio and get a near-perfect clone.

### The Play
Create the "Protocol Pulse Voice" — a custom-designed voice that doesn't exist on any other podcast. Not Charlotte. Not Deborah. YOUR voice identity. You can either:

**Option A: Voice Design (instant)**
```python
# Create a unique voice from description
voice = client.voices.design(
    name="Proto",
    description="Female, 30s, American, confident Bloomberg anchor energy. "
                "Slight edge, not corporate. Like she trades Bitcoin and reads Camus.",
    text="Bitcoin just printed a new all-time high and the market is on fire."
)
```

**Option B: Clone your own voice**
Upload 30+ minutes of PBX podcast audio → get a cloned version of your voice for the daily briefings. YOUR voice, running autonomously.

### Why This Matters
Voice is brand identity. Every time someone hears Charlotte on another project, your brand is diluted. A custom voice is yours alone.

---

## 6. REMOTION SHORTS PIPELINE — Automated Social Clips
**Replaces:** Manual clip cutting / FFmpeg shorts pipeline
**Cost:** $0 (Remotion is already installed for main episode rendering)
**Runs on:** Ultron

### ⚠️ IMPORTANT: DO NOT USE CREATOMATE OR OPUSCLIP
Creatomate ($19-79/mo) and OpusClip are unnecessary SaaS subscriptions. Remotion already handles everything they do — vertical reframing, animated captions, branded templates, batch rendering — and it runs locally on Ultron for free. Do NOT sign up for or integrate Creatomate, OpusClip, or any other third-party video clip service.

### What It Does
After the main episode renders, the pipeline auto-generates 3-5 branded vertical Shorts (9:16) using Remotion templates. Each Short gets animated captions, Protocol Pulse branding, and a CTA end card. Auto-uploaded to YouTube Shorts, TikTok, Instagram Reels, and X.

### Remotion Short Template
```tsx
// ShortClip.tsx — 9:16 vertical format
export const ShortClip = ({ clipVideo, words, hookText, ctaText, btcPrice }) => {
  return (
    <AbsoluteFill style={{ width: 1080, height: 1920, background: '#0a0a14' }}>
      <Video src={clipVideo} style={{ width: '100%', objectFit: 'cover' }} />
      <HookText text={hookText} />           {/* Animated hook at top */}
      <AnimatedCaptions words={words} />     {/* Word-by-word captions */}
      <BTCTicker price={btcPrice} />          {/* Live price bottom corner */}
      <EndCard cta={ctaText} />               {/* Subscribe CTA last 3 sec */}
    </AbsoluteFill>
  );
};
```

### Pipeline Integration
```python
# After episode renders, auto-generate shorts
clips = identify_viral_moments(transcript)  # Claude scores top 3-5 moments

for clip in clips:
    subprocess.run([
        "npx", "remotion", "render", "src/index.ts", "ShortClip",
        f"out/short_{clip.id}.mp4",
        f"--props={json.dumps({
            'clipVideo': clip.video_path,
            'words': clip.word_timestamps,
            'hookText': clip.hook_text,
            'ctaText': 'Full episode → protocolpulse.io',
            'btcPrice': get_current_btc_price()
        })}"
    ])
```

### Why This Matters
Every episode should spawn 3-5 Shorts. That's 3-5x the content from a single production run. YouTube Shorts get 50B daily views. The algorithm pushes Shorts to non-subscribers. This is how you go from 0 to 1K subs in 60 days. And it costs nothing because Remotion is already on Ultron.

---

## 7. WHISPER DIARIZATION — Smart Clip Boundaries
**Replaces:** Dumb time-based clip cutting that chops mid-sentence
**Cost:** Free (Whisper + pyannote on Ultron GPU)
**Already partially built:** Whisper is on Ultron

### What It Does
Speaker diarization identifies WHO is speaking WHEN. Combined with Whisper's word-level timestamps, you get:
- Never cut a clip mid-sentence (detect sentence boundaries)
- Never have narrator overlap clip audio (detect speaker change points)
- Auto-identify the most quotable 30-second segments (sentence scoring by engagement prediction)

### Implementation
```bash
pip install pyannote.audio  # speaker diarization
```

```python
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
diarization = pipeline("episode.wav")

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"Speaker {speaker}: {turn.start:.1f}s → {turn.end:.1f}s")
```

This feeds directly into the assembler to solve the narrator-interrupting-clips problem permanently.

---

## 8. RECURSIVE SKILL REFINEMENT — The Self-Improving Pipeline
**Replaces:** You manually telling me what to fix after every render
**Cost:** One Claude API call per week (~$0.50)
**Runs on:** Ultron orchestrator Saturday night pass

### What It Does
Every Saturday night, the orchestrator runs a "skill refinement" pass:

1. **Searches** for the latest YouTube production best practices, thumbnail strategies, podcast growth tactics, Bitcoin content trends
2. **Reads** the top 5 results
3. **Extracts** actionable insights
4. **Updates** its own prompt templates (script_writer tone, thumbnail composition rules, title formulas, caption styles)
5. **Logs** what it changed and why

This is the Jason Calacanis / All-In play — the thumbnail agent that found the Mr. Beast heat map article on its own and incorporated it into its skills.

### Implementation
Add to orchestrator's Saturday cron:
```python
# skill_refiner.py
SEARCH_QUERIES = [
    "YouTube thumbnail best practices {current_year}",
    "podcast growth strategies {current_year}",
    "Bitcoin content trends this week",
    "viral short-form video techniques",
    "programmatic video production tips"
]

for query in SEARCH_QUERIES:
    results = web_search(query)
    insights = claude_extract_insights(results)
    update_skill_files(insights)
    log_changes(insights)
```

### Skill Files That Get Auto-Updated
```
skills/
├── script_tone.md         # Voice, banned phrases, openers, closers
├── thumbnail_rules.md     # Composition, text placement, color theory
├── title_formulas.md      # SEO patterns, hook structures, click triggers
├── caption_styles.md      # Animation preferences, keyword highlighting rules
└── changelog.md           # What changed and why (audit trail)
```

---

## COMPLETE UPGRADED ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    DAILY PRODUCER                         │
│  (orchestrates entire pipeline, runs at 6AM EST)         │
└───────────┬─────────────────────────────────┬───────────┘
            │                                 │
     ┌──────▼──────┐                  ┌───────▼───────┐
     │ CONTENT      │                  │ MUSIC          │
     │ SOURCES      │                  │ Pre-gen Suno   │
     │ Articles     │                  │ library (30    │
     │ X/Tweets     │                  │ tracks, local) │
     │ Spaces       │                  └───────┬───────┘
     │ Nostr        │                          │
     └──────┬──────┘                          │
            │                                 │
     ┌──────▼──────┐                          │
     │ SCRIPT       │                          │
     │ WRITER       │◄─── skills/script_tone.md│
     │ (Claude)     │     (auto-updated weekly)│
     └──────┬──────┘                          │
            │                                 │
     ┌──────▼──────┐                          │
     │ TTS ENGINE   │                          │
     │ ElevenLabs   │                          │
     │ Custom Voice │                          │
     └──────┬──────┘                          │
            │                                 │
     ┌──────▼──────────────────────────────────▼──────┐
     │              ASSEMBLER V10                       │
     │                                                  │
     │  Remotion renders:          FFmpeg handles:      │
     │  ├── BrandedIntro.mp4      ├── Clip trimming     │
     │  ├── TitleCard.mp4         ├── Audio mixing       │
     │  ├── WaveformViz.mp4       ├── Concatenation      │
     │  ├── GlitchTransition.mp4  ├── Final encoding     │
     │  ├── SocialCard.mp4        └── yuv420p/AAC       │
     │  ├── BTCDataChart.mp4                            │
     │  ├── SponsorCard.mp4                             │
     │  └── OutroBranded.mp4                            │
     │                                                  │
     │  Whisper + Diarization:                          │
     │  ├── Word-level timestamps                       │
     │  ├── Speaker boundaries                          │
     │  └── Smart clip cut points                       │
     │                                                  │
     │  Animated Captions:                              │
     │  └── Word-by-word kinetic text (Remotion)        │
     └──────┬──────────────────────────────────────────┘
            │
     ┌──────▼──────┐
     │ OUTPUT       │
     │              │
     │ Episode MP4  │──→ YouTube auto-upload (Data API v3)
     │              │──→ Podcast RSS (Spotify, Apple, Fountain)
     │              │
     │ 3-5 Shorts   │──→ YouTube Shorts
     │ (Remotion)    │──→ TikTok
     │              │──→ Instagram Reels
     │              │──→ X Video
     │              │
     │ Thumbnail    │──→ A/B test via YouTube API
     │ (Remotion)    │
     │              │
     │ SEO Package  │──→ Title, description, tags (Claude)
     └──────────────┘
```

---

## IMPLEMENTATION PRIORITY

### Phase 1 — Remotion Core (Week 1)
Build 3 foundation scenes: BrandedIntro, GlitchTransition, TitleCard.
Wire into assembler. Test render. Regression test.
**One Claude Code session. ~2 hours.**

### Phase 2 — Animated Captions + Waveform (Week 1-2)
Build AnimatedCaptions and WaveformVisualizer components.
Feed Whisper word timestamps into Remotion props.
**One Claude Code session. ~1.5 hours.**

### Phase 3 — Suno Music Library Integration (Week 2)
PBX pre-generates 30 tracks in Suno web UI (see SUNO_PROMPT_LIBRARY.md).
SCP to Ultron. Wire mood classifier into script_writer. Assembler picks by mood.
NO API. NO third-party wrappers. Local files only.
**30 minutes of code once files are on Ultron.**

### Phase 4 — D3 Data Visualizations (Week 2-3)
Build BTCPriceChart and HashRateDashboard Remotion scenes.
Pull live data from CoinGecko API at render time.
**One Claude Code session. ~1.5 hours.**

### Phase 5 — Shorts Pipeline (Week 3)
Remotion-based vertical clip generator (9:16 ShortClip template).
Auto-identify viral moments from transcript via Claude scoring.
Auto-upload to YouTube Shorts, TikTok, X.
NO Creatomate. NO OpusClip. Remotion handles everything locally on Ultron.
**One Claude Code session. ~2 hours.**

### Phase 6 — Recursive Refinement (Week 3-4)
Skill refiner runs Saturday nights.
Auto-updates script tone, thumbnail rules, title formulas.
Logs all changes for audit trail.
**30 minutes of code.**

### Phase 7 — Custom Voice + Sponsor Card (Week 4)
Design Protocol Pulse voice via ElevenLabs Voice Design.
Build SponsorCard Remotion scene for automated ad placements.
**1 hour total.**

---

## WHAT THIS LOOKS LIKE WHEN IT'S DONE

6AM EST every morning:
1. Content sources scraped (articles, tweets, spaces, nostr)
2. Script written with auto-updated tone rules
3. Mood-matched soundtrack selected from 30-track Suno library
4. TTS renders narration in Protocol Pulse's unique voice
5. Remotion renders: animated intro, title card, waveform bg, data charts, social cards, glitch transitions, sponsor card, animated outro
6. FFmpeg assembles clips + narration + Remotion segments + music
7. Animated word-by-word captions burned in
8. Final episode MP4 auto-uploaded to YouTube
9. 3-5 branded Shorts auto-generated and pushed to Shorts/TikTok/Reels/X
10. SEO-optimized title, description, tags auto-generated
11. Thumbnail auto-generated with A/B variant
12. Regression test passes. Git commit. Done.

**Total human involvement: Zero.**
**Total time from trigger to published: ~20 minutes.**
**Output quality: Broadcast. Not "AI content." Broadcast.**

Nobody else has this. Nobody.
