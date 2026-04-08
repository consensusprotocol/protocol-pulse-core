# Protocol Pulse — Hook Editing DNA

> Forensic analysis of Cypherpunk'd intro hooks to map PBX's editing patterns into automatable rules.

## Methodology

- **Source**: YouTube playlist `PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd` (Cypherpunk'd series)
- **Sample**: 8 videos, first 120 seconds each (1920x1080, 24fps)
- **Tools**: PySceneDetect (ContentDetector, threshold=27), FFprobe audio RMS analysis, FFmpeg frame extraction
- **Videos analyzed**:
  1. Adoption: Knut Svanholm | Everything Divided By 21
  2. Bitcoin Is Under Attack From Within - Luke Dashjr
  3. Bitcoin, Fatherhood, Adoption & Why Modern Families...
  4. Emmy-Winning Journalist Exposes Media Censorship
  5. Inevitable: Knut Svanholm | Everything Divided By 21
  6. The Bitcoin Inheritance Problem | Jason Leibowitz
  7. Transition: Knut Svanholm | Everything Divided By 21
  8. "There Is No Line They Won't Cross" - FDI Insider

---

## Timing Patterns

| Metric | Value |
|--------|-------|
| **Average first cut** | 2.55s after start |
| **Median first cut** | 2.50s after start |
| **First cut range** | 0.67s — 4.62s |
| **Average segment duration** | 3.25s |
| **Median segment duration** | 3.25s |
| **Average cuts per minute** | 21.0 |
| **Cuts/min range** | 11.5 — 35.5 |
| **Shortest segment (mean)** | 0.703s |
| **Shortest segment (absolute)** | 0.625s |
| **Longest hold (mean)** | 18.3s |
| **Longest hold (absolute)** | 44.5s |

### Key Insight
The first cut comes FAST. Within 2.5 seconds on average. The viewer is never staring at a static frame for more than ~4.6 seconds before something changes. This is the #1 retention rule.

---

## Segment Duration Distribution (336 total segments)

```
< 0.5s      0 segments  ( 0.0%)
0.5 - 1s   57 segments  (17.0%)  ████████
1 - 2s    117 segments  (34.8%)  █████████████████
2 - 3s     65 segments  (19.3%)  █████████
3 - 5s     57 segments  (17.0%)  ████████
5 - 10s    31 segments  ( 9.2%)  ████
10 - 20s    7 segments  ( 2.1%)  █
20s+        2 segments  ( 0.6%)
```

**The sweet spot is 1-2 seconds.** Over half of all segments (51.8%) are under 3 seconds. The dominant editing rhythm is rapid cuts with occasional breather holds.

---

## Pacing Acceleration (The Deceleration Curve)

PBX hooks start FAST and gradually decelerate — the opposite of what most creators do.

| Time Window | Avg Segment | Cuts/Min (per video) | Strategy |
|-------------|-------------|---------------------|----------|
| **0-10s** | 2.09s | 33.0 | **HOOK** — Rapid fire, grab attention |
| **10-30s** | 2.33s | 27.0 | **SUSTAIN** — Still fast, building narrative |
| **30-60s** | 2.59s | 23.0 | **SETTLE** — Slightly relaxed, story developing |
| **60-120s** | 3.61s | 16.0 | **BREATHE** — Longer holds, interview rhythm |

### The Formula
```
OPEN  (0-10s):   ~33 cuts/min  |  2.1s avg segment  |  MAXIMUM ENERGY
BUILD (10-30s):  ~27 cuts/min  |  2.3s avg segment  |  HIGH ENERGY
EASE  (30-60s):  ~23 cuts/min  |  2.6s avg segment  |  MODERATE ENERGY
RIDE  (60-120s): ~16 cuts/min  |  3.6s avg segment  |  CONVERSATION RHYTHM
```

**Acceleration factor**: Segments in the first 30s are 0.63x the length of segments after 30s. The opening is 37% faster than the body.

---

## Audio Patterns

| Metric | Value |
|--------|-------|
| **Audio-cut correlation (mean)** | 27.3% |
| **Best correlation** | 56.5% (Luke Dashjr episode) |
| **Lowest correlation** | 0% (2 videos — FFprobe RMS extraction issue) |
| **Effective mean (valid samples)** | 36.4% |

### Interpretation
PBX's editing is **NOT heavily music-driven**. Cuts follow the conversational rhythm (speaker changes, emphasis moments) rather than being locked to beat drops. When there IS audio alignment:

- Bass hits coincide with cuts at ~36% of cut points (in working samples)
- The Luke Dashjr episode (highest CPM at 35.5) also had the highest audio correlation (56.5%) — suggesting rapid-fire montage segments DO sync to music
- Documentary-style episodes (Knut Svanholm series) have lower audio correlation — cuts follow the narrative, not the beat

### Audio Energy Behavior
- Mean RMS across clips: -25 to -30 dB (typical podcast/interview levels)
- Peak moments correlate with speaker emphasis, not music hits
- No consistent "bass drop at first cut" pattern — the hook is visual, not audio

---

## Visual Patterns (Frame Analysis)

### Shot Types Identified

1. **Tight Close-Up (TCU)** — Single speaker, chest-to-head framing, studio background
   - Most common shot type (~60% of frames)
   - Red/black angular geometric backdrop (Cypherpunk'd branding)
   - Speaker with podcast mic, often wearing headphones

2. **Wide Two-Shot** — Both host + guest visible, full studio setup
   - Used for establishing shots and transition moments
   - Shows branded "Bitcoin: 21M" center table display
   - Used at start of interview segments and after B-roll

3. **Split-Screen** — Side-by-side host/guest composition
   - Used in opening hooks before the viewer knows who's speaking
   - Creates a "debate" or "confrontation" energy

4. **Cinematic B-Roll** — Urban/exterior footage overlaid with the guest
   - City street shots with subject walking (wearing headphones from studio)
   - Shallow depth of field, warm color grade
   - Used to break the "talking heads" pattern

5. **Text Card** — Large bold white text overlaid on the speaker
   - Word-by-word karaoke-style subtitles (1-3 words at a time)
   - White bold sans-serif font, centered on lower third
   - Key phrases get LARGER text with emphasis styling
   - Present in most episodes — core to the visual identity

### Studio Environments
- **Primary**: Red/black geometric angular wall (Cypherpunk'd branded)
- **Secondary**: Grey/neutral studio (some Knut Svanholm episodes)
- **Consistent elements**: Black gaming chairs, podcast mics, reflective table surface

---

## Pacing Formula

The archetypal PBX 2-minute hook follows this structure:

```
[0.0s - 0.7s]  COLD OPEN: Guest mid-sentence, provocative quote
                Shot: TCU of guest, word-by-word subtitles
                Duration: 0.7s single shot OR split-screen

[0.7s - 5.0s]  RAPID MONTAGE: 3-5 flash cuts (0.7-1.5s each)
                Shots: TCU guest, TCU host reaction, B-roll, text card
                Audio: Guest continues talking over the cuts

[5.0s - 15.0s] HOOK PAYOFF: Let the provocative statement land
                Shot: Single TCU hold (3-6s) on speaker
                This is the "earworm" moment — the thesis in one sentence

[15.0s - 30.0s] BUILD: Resume rapid cutting (2-3s segments)
                 Mix of host reactions, guest close-ups, B-roll inserts
                 Word-by-word captions continue

[30.0s - 60.0s] CONTEXT: Slower pacing (2.5-4s segments)
                 Settle into interview rhythm
                 Occasional B-roll break every 15-20s

[60.0s - 120.0s] RIDE: Full conversation mode (3-5s segments)
                  Standard podcast editing rhythm
                  Host-guest alternation with reaction shots
```

### The Rhythm in Musical Terms
```
Measure 1 (0-10s):    ♩♩♩♩♩ (rapid eighth notes — 5+ cuts)
Measure 2 (10-30s):   ♩ ♩ ♩ ♩ (quarter notes — 6-8 cuts)
Measure 3 (30-60s):   ♩  ♩  ♩  (half notes — 5-7 cuts)
Measure 4 (60-120s):  ♩    ♩   (whole notes — 8-12 cuts, longer holds)
```

---

## Per-Video Breakdown

| Video | 1st Cut | CPM | Avg Seg | Shortest | Longest | Audio % | Style |
|-------|---------|-----|---------|----------|---------|---------|-------|
| Adoption (Knut) | 4.33s | 11.5 | 5.22s | 0.83s | 44.46s | 13.6% | Docu-slow |
| Luke Dashjr | 0.67s | 35.5 | 1.69s | 0.63s | 5.33s | 56.5% | Rapid-fire |
| Fatherhood | 2.17s | 30.5 | 1.97s | 0.67s | 11.58s | N/A | Fast-narrative |
| Emmy Journalist | 2.83s | 17.5 | 3.43s | 0.67s | 17.88s | 23.5% | Mid-pace |
| Inevitable (Knut) | 2.17s | 13.5 | 4.45s | 0.71s | 19.88s | 50.0% | Docu-mid |
| Inheritance (Jason) | 2.92s | 19.5 | 3.08s | 0.79s | 9.83s | 52.6% | Standard |
| Transition (Knut) | 0.71s | 17.0 | 3.53s | 0.71s | 30.79s | 21.9% | Mixed |
| FDI Insider | 4.62s | 23.0 | 2.61s | 0.63s | 6.88s | N/A | Mid-fast |

### Observations
- **Two editing modes**: "Rapid-fire" (CPM > 25, used for action/controversy topics) vs "Documentary" (CPM 11-17, used for philosophical/book episodes)
- **Knut Svanholm** episodes are consistently slower-paced (documentary style with cinematic B-roll)
- **Controversy/attack** episodes (Luke Dashjr, FDI) have the fastest cutting
- The first cut is ALWAYS under 5 seconds, regardless of pacing mode

---

## Automatable Rules

### Rule 1: First Cut Timing
```python
FIRST_CUT_TARGET = 2.5  # seconds
FIRST_CUT_MAX = 4.5     # never exceed this
```

### Rule 2: Segment Duration by Time Window
```python
def target_segment_duration(timestamp_sec):
    if timestamp_sec < 10:
        return random.uniform(0.7, 2.5)   # HOOK: rapid fire
    elif timestamp_sec < 30:
        return random.uniform(1.5, 3.5)   # BUILD: still fast
    elif timestamp_sec < 60:
        return random.uniform(2.0, 5.0)   # EASE: moderate
    else:
        return random.uniform(3.0, 6.0)   # RIDE: conversation
```

### Rule 3: Cuts Per Minute Targets
```python
CPM_TARGETS = {
    "rapid_fire": 30,    # controversy/attack topics
    "standard": 20,      # interviews, general
    "documentary": 13,   # philosophical, deep-dive
}
```

### Rule 4: Shot Rotation Pattern
```python
SHOT_ROTATION = [
    "TCU_speaker",       # 1-3s — person currently talking
    "TCU_reaction",      # 0.7-1.5s — other person reacting
    "TCU_speaker",       # 2-4s — back to speaker
    "B_roll_insert",     # 1-2s — contextual footage
    "TCU_speaker",       # 2-4s — continue narrative
    "wide_two_shot",     # 2-3s — re-establish spatial context
]
# B-roll every 4-6 shots. Wide shot every 6-8 shots.
```

### Rule 5: Subtitle Behavior
```python
SUBTITLE_CONFIG = {
    "style": "word_by_word",      # karaoke — 1-3 words at a time
    "font": "bold_sans_serif",    # white, centered lower-third
    "emphasis_words": "LARGER",   # key nouns/verbs get scaled up
    "always_on": True,            # subtitles throughout entire hook
    "position": "center_lower",   # overlaid on speaker's chest area
}
```

### Rule 6: Cold Open Formula
```python
def generate_cold_open():
    """
    Always start with the guest mid-sentence on the most
    provocative quote from the interview.
    Never start with the host.
    Never start with a title card or logo.
    The first words the viewer hears should be the hook line.
    """
    return {
        "start_with": "guest_mid_sentence",
        "shot_type": "TCU_guest or split_screen",
        "subtitle": True,
        "duration_before_first_cut": 2.5,  # seconds
    }
```

### Rule 7: Flash Cut Minimum
```python
FLASH_CUT_MIN = 0.625   # seconds — never shorter than 15 frames at 24fps
FLASH_CUT_MAX = 0.833   # seconds — 20 frames at 24fps
# Flash cuts used for: reaction shots, emphasis moments, montage transitions
```

### Rule 8: Hold Duration Limits
```python
MAX_SINGLE_SHOT_HOLD = 10.0   # seconds — beyond this, viewer attention drops
# Exception: dramatic monologue moments can hold up to 20s
# The 44s and 30s outliers in the data are interview body, not hooks
```

### Rule 9: Pacing Mode Selection
```python
def select_pacing_mode(topic_keywords):
    """Select editing pace based on content type."""
    rapid_keywords = ["attack", "war", "expose", "insider", "threat", "crash"]
    docu_keywords = ["philosophy", "adoption", "history", "book", "journey"]

    if any(kw in topic_keywords for kw in rapid_keywords):
        return "rapid_fire"   # 30+ CPM
    elif any(kw in topic_keywords for kw in docu_keywords):
        return "documentary"  # 13 CPM
    else:
        return "standard"     # 20 CPM
```

### Rule 10: The Deceleration Curve (FFmpeg Implementation)
```bash
# For a 120s hook assembled from segments:
# Phase 1 (0-10s):  target 5-6 cuts, segments avg 1.8s
# Phase 2 (10-30s): target 6-8 cuts, segments avg 2.5s
# Phase 3 (30-60s): target 6-8 cuts, segments avg 3.5s
# Phase 4 (60-120s): target 10-15 cuts, segments avg 4.0s
#
# Total: ~30-35 cuts in 120 seconds (~17-20 CPM for standard mode)
```

---

## Summary: PBX Editing DNA

The signature is a **decelerating cascade**: maximum energy in the first 10 seconds, gradually slowing to a conversational rhythm. Combined with word-by-word karaoke subtitles, tight close-ups on a red/black branded set, and cinematic B-roll punctuation every 15-20 seconds.

The hook doesn't rely on music drops or flashy graphics. It relies on **the provocative quote landing fast** (guest mid-sentence at frame 1), **rapid visual variety** (flash cuts between angles), and **continuous text reinforcement** (subtitles ensure the message lands even on mute).

This is podcast editing optimized for YouTube retention. The viewer is never bored because the visual frame changes every 1-3 seconds in the hook, while the audio maintains a single continuous thought.
