# PROTOCOL PULSE — VISUAL DESIGN SYSTEM
# Based on ChatGPT Broadcast Engine (A/B Test Winner)
# Total Visual Overhaul for Video Pipeline
# Status: GOSPEL. Every Remotion component and FFmpeg visual must follow this.
# Created: 2026-03-06

---

## DESIGN PHILOSOPHY

"Bloomberg Terminal meets cinematic newscast."

This is NOT a YouTube channel aesthetic. This is a BROADCAST INTELLIGENCE PRODUCT.
Every frame must communicate: authority, precision, urgency, and premium quality.
The viewer should feel like they're watching a $2M/year production, not an AI tool.

Key principles:
1. INFORMATION DENSITY over empty space — every pixel earns its place
2. EDITORIAL HIERARCHY — eyebrow → headline → body → metadata (always)
3. MULTI-COLOR LIGHT SYSTEM — not monochrome, three coordinated glow sources
4. GOLD AS SIGNATURE — the gold info bar and gold accents are the brand differentiator
5. GLASSMORPHISM WITH RESTRAINT — blur + transparency, but never muddy or illegible
6. MOTION WITH PURPOSE — every animation communicates something, never decorative

---

## SECTION 1: COLOR SYSTEM

### Primary Palette:
```
--bg:        #06070b     (deep space black — base layer)
--panel:     #0d1118     (elevated surface — cards, overlays)
--panel-2:   #121824     (secondary surface — nested elements)
--text:      #eef2ff     (primary text — slightly blue-white, not pure white)
--muted:     #95a0ba     (secondary text — metadata, handles, timestamps)
```

### Accent Colors:
```
--red:       #ff3b5f     (Protocol Pulse red — alerts, active states, brand)
--gold:      #f8c15c     (SIGNATURE — info bar, kickers, section labels, scores)
--cyan:      #5de4ff     (data accents — secondary glow, cool contrast)
--lime:      #89ffb8     (positive metrics — up arrows, gains)
--coral:     #ff8ba0     (negative metrics — danger, compression, losses)
```

### Glow Colors (for shadows and radial gradients):
```
--glow-red:  rgba(255,59,95,0.45)
--glow-gold: rgba(248,193,92,0.30)
--glow-cyan: rgba(93,228,255,0.20)
```

### Color Usage Rules:
- Gold (#f8c15c) = ALL section kickers, eyebrows, labels, score badges, info bar bg
- Red (#ff3b5f) = active card borders, alert states, brand mark, pulse dots
- Cyan (#5de4ff) = secondary data, cool-tone glow source, chart accent
- Lime (#89ffb8) = positive deltas ONLY ("+3.8%", "▲", up arrows)
- Coral (#ff8ba0) = negative deltas, danger states, "compression", "under pressure"
- NEVER use pure white (#ffffff) for text — always #eef2ff (warmer, less harsh)
- NEVER use pure black (#000000) for backgrounds — always #06070b minimum

### Temperature Pacing Across Episode (per PRODUCTION_DESIGN_LAWS):
- Cold open: RED dominant (urgency)
- Title sequence: RED + GOLD (brand identity)
- Narration setup: NEUTRAL (balanced palette)
- Partner clips: WARM (natural, let clip colors dominate)
- Data segment: CYAN + GOLD (analytical, authoritative)
- Social segment: RED + GOLD (engagement energy)
- Wrap: WARM GOLD (resolution, satisfaction)
- Outro: RED + GOLD (brand signoff)

---

## SECTION 2: TYPOGRAPHY

### Font Stack:
```
--sans:  Inter, ui-sans-serif, system-ui, sans-serif     (headlines, body)
--mono:  'JetBrains Mono', 'SF Mono', ui-monospace, monospace  (data, labels, tickers)
```

### Type Scale:
```
HEADLINES (scene titles):
  Cold open headline:    52-64px, weight 900, tracking -0.04em, line-height 0.95
  Section title:         36-42px, weight 900, tracking -0.04em, line-height 0.96
  Title sequence:        72-94px, weight 950, tracking -0.06em, line-height 0.90

EYEBROW KICKERS (above headlines):
  Size: 10-11px, weight 800, tracking 0.18-0.20em, UPPERCASE
  Color: ALWAYS gold (#f8c15c)
  Format: "CATEGORY • DESCRIPTOR" (e.g., "COLD OPEN • HIGHEST STAKES")

BODY TEXT:
  Subtitle/description:  17-22px, weight 400-500, line-height 1.4
  Color: #d7def4 (light blue-white)

DATA VALUES:
  Large metric:          26-34px, weight 900, tracking -0.03em, font: monospace
  Delta/change:          11-14px, weight 700
  Label:                 9-11px, weight 800, tracking 0.18em, UPPERCASE, color: muted

METADATA:
  Handles:              12px, color: muted
  Timestamps:           12px, color: muted
  Tags/chips:           9-11px, weight 800, tracking 0.12em, UPPERCASE
```

### Typography Rules:
- Headlines: ALWAYS use text-shadow: "0 4px 28px rgba(0,0,0,0.4)" for depth
- Headlines: Break long lines strategically with <br /> — never let text run edge-to-edge
- Eyebrows: ALWAYS gold, ALWAYS uppercase, ALWAYS above the headline
- NEVER use more than 2 font weights in one card (e.g., 800 for label + 900 for value)
- Monospace for ALL data: prices, percentages, hashrates, timestamps, scores
- Sans-serif for ALL editorial content: headlines, descriptions, quotes, names

---

## SECTION 3: BACKGROUND SYSTEM

### Three-Source Light Model:
The background is NOT flat. It has three coordinated radial glow sources:

```
Source 1 (RED):   top-left area, rgba(255,59,95,0.14), radius ~300px
Source 2 (CYAN):  top-right area, rgba(93,228,255,0.10), radius ~250px
Source 3 (GOLD):  bottom-center area, rgba(248,193,92,0.06), radius ~200px
```

These create the "cinematic" depth that flat backgrounds lack.
The sources should subtly shift position over time (±30px oscillation, 5-7 second cycle).

### Perspective Floor Grid:
```
- Vanishing point: center frame, 55% from top
- Grid lines: rgba(255,255,255,0.02-0.05), 0.4-0.5px width
- 20 horizontal lines, receding into depth (quadratic spacing)
- 14 vertical lines, converging to vanishing point
- Transform: perspective(1200px) rotateX(72deg) translateY(240px) scale(2.2)
- Subtle red glow filter: drop-shadow(0 0 16px rgba(255,59,95,0.12))
```

### Overlay Layers (bottom to top):
```
Layer 0: Solid #06070b
Layer 1: Three-source radial gradient (red + cyan + gold)
Layer 2: Perspective floor grid (CSS transform or FFmpeg drawgrid)
Layer 3: Noise texture (radial-gradient dots, 8px spacing, 7% opacity, soft-light blend)
Layer 4: Scanlines (horizontal lines, 4px spacing, 4% opacity)
Layer 5: Pulse rings (2 centered, subtle animation, red + cyan)
Layer 6: Signal sweep (diagonal light band, crosses frame every 7 seconds)
Layer 7: Vignette (radial-gradient from transparent center to 45% black edges)
```

### For Remotion:
Each layer is an `<AbsoluteFill>` component stacked in order.
For FFmpeg: composite as overlay filters in the filtergraph.

### For Video Pipeline (FFmpeg equivalent):
```bash
# Background composite (simplified)
ffmpeg -i solid_bg.png \
  -filter_complex "
    [0]drawbox=x=0:y=0:w=1920:h=1080:c=black@1:t=fill[bg];
    [bg]curves=all='0/0 0.15/0.03 1/0.05'[tinted];
    [tinted]vignette=angle=PI/4:mode=forward[vig]
  " output_bg.mp4
```

---

## SECTION 4: NARRATOR SEGMENT LAYOUT

### Split-Screen Composition:
```
┌──────────────────────────────────────────────────────────────────┐
│ [EYEBROW KICKER: gold, 10px, tracking 0.20em]                   │
│                                                                   │
│ [HEADLINE: 52px, white, 2-3 lines max]      ┌──────────────────┐│
│                                              │                  ││
│ [BODY: 17px, #d7def4, max 480px width]       │   PiP PREVIEW    ││
│                                              │   (340x210)      ││
│                                              │   rounded 16px   ││
│                                              │   border + shadow││
│                                              │                  ││
│                                              │  [COMING UP]     ││
│                                              │  [speaker/source]││
│                                              └──────────────────┘│
│                                                                   │
│ ════════════════════════════════════════════════════════════════  │
│ [WAVEFORM: gold gradient, bottom-third, full width]              │
│ ════════════════════════════════════════════════════════════════  │
│ ██████████████████████ GOLD INFO BAR ██████████████████████████  │
└──────────────────────────────────────────────────────────────────┘
```

### PiP Preview Styling:
```
Position:     absolute, right: 36px, bottom: 100px
Size:         340 x 210 pixels (16:9 aspect)
Border:       1px solid rgba(255,255,255,0.10)
Border-radius: 16px
Shadow:       0 16px 48px rgba(0,0,0,0.35), 0 0 30px rgba(255,59,95,0.06)
Background:   actual muted video (not static image)
Label:        "COMING UP" — 10px, gold (#f8c15c), tracking 0.18em, above the frame
Speaker info: glassmorphism bar at bottom of PiP (rgba(0,0,0,0.4) + blur(10px))
```

### Waveform (Gold Gradient):
```
Style:        EKG heartbeat line, NOT frequency bars
Colors:       gradient stroke from rgba(255,59,95,0.15) → rgba(248,193,92,0.85) → rgba(93,228,255,0.12)
Glow:         8px blur in gold, then 3px main line, then 1.2px bright core
Line width:   3px main, with 8px glow behind
Position:     bottom of frame, above info bar
Height:       120px total area
Baseline:     subtle horizontal line at center (rgba(255,255,255,0.04))
```

---

## SECTION 5: GOLD INFO BAR (SIGNATURE ELEMENT)

This is the MOST DISTINCTIVE visual element. It's what makes Protocol Pulse recognizable.

```
Position:     absolute bottom, full width
Height:       42px
Background:   linear-gradient(90deg, rgba(248,193,92,0.88), rgba(255,219,132,0.92))
Text color:   #141515 (dark, near-black — contrast against gold)
Font:         JetBrains Mono, 12px, weight 800, tracking 0.08em
Layout:       3-column grid:
  Left:       "BTC 96,482 ▲ 2.14%" (live price)
  Center:     "PROTOCOLPULSE.IO"
  Right:      "MARCH 2026 • DAILY BRIEF"
```

Rules:
- Info bar appears on EVERY scene except title sequence and outro
- Price updates at render time (not live, but current when rendered)
- Arrow (▲/▼) changes color to match price direction
- This bar is NEVER transparent or dark — always gold

---

## SECTION 6: SOCIAL CARD DESIGN

### Card Container:
```
Background:   linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))
Border:       1px solid rgba(255,255,255,0.08)
              Active card: 1px solid rgba(255,59,95,0.30)
Border-radius: 16px
Padding:      18px 20px
Shadow:       Active: 0 16px 48px rgba(0,0,0,0.35), 0 0 36px rgba(255,59,95,0.12)
              Inactive: 0 8px 24px rgba(0,0,0,0.2)
Backdrop:     blur(16px)
```

### Card Layout:
```
Top row:      [Avatar 42px circle] [Name 16px bold + Handle 12px muted] [Score badge: gold border, gold text]
Body:         Quote text — 22px, weight 700, line-height 1.25, max-width 580px
Footer:       Signal tag — 10px, #ffb6c2 (light coral), tracking 0.16em, weight 800
              Format: "SIGNAL STRENGTH • HIGH CONVICTION" or "MACRO SIGNAL • STRUCTURAL"
```

### Animation:
```
Entry:    slide-in from right, 300ms, easeOutExpo
Hold:     match narration duration exactly
Exit:     fade out, 300ms
Scale:    active card = scale(1), inactive = scale(0.97) + opacity 0.75
```

### Score Badge:
```
Font:         11px, monospace, weight 800
Color:        gold (#f8c15c)
Border:       1px solid rgba(248,193,92,0.20)
Border-radius: 999px (pill shape)
Padding:      5px 10px
```

---

## SECTION 7: DATA SEGMENT DESIGN

### Layout:
```
Split grid: 55% left (text + stat cards) / 45% right (chart)
Gap: 20px
```

### Stat Cards (2x2 grid):
```
Background:   linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))
Border:       1px solid rgba(255,255,255,0.10)
Border-radius: 14px
Padding:      14px 16px
Shadow:       0 12px 36px rgba(0,0,0,0.25)

Content:
  Label:      9px, monospace, tracking 0.18em, color: muted, weight 800, UPPERCASE
  Value:      26px, monospace, weight 900, tracking -0.03em (tight)
  Delta:      11px, weight 700, color varies:
              Positive: lime (#89ffb8)
              Negative: coral (#ff8ba0)
              Neutral:  #cfd7eb
```

### Chart Panel:
```
Background:   same glassmorphism as cards
Grid overlay: 48px spacing, rgba(255,255,255,0.03)
Header:       "BTC / NETWORK STRESS INDEX" + "LIVE MODEL" chip
              Chip: pill shape, rgba(255,59,95,0.10) bg, #ffbdc8 text

Chart line:   SVG path with gradient stroke:
              Red (#ff4d6d) → Gold (#ffd166) → Green (#7bf1a8)
              Stroke-width: 5px, round linecap
Fill:         Below line, gradient from rgba(255,77,109,0.30) → transparent
Pulse dot:    End of line, 7px radius, #ff4d6d, animated pulsing (7→10→7, 2s cycle)
```

---

## SECTION 8: LOWER THIRD DESIGN

### Structure:
```
┌─────────────────────────────────────────────────────────┐
│ ═══════════════ red reveal bar (3px, animated width) ══│
│                                                         │
│  [KICKER: gold, 10px]           [TAG: gold, 10px]      │
│  [NAME: white, 18px bold]       [TIME: muted, 12px]    │
│                                                         │
│ ─────────────── glassmorphism bg + blur ──────────────  │
└─────────────────────────────────────────────────────────┘
```

### Styling:
```
Background:    linear-gradient(90deg, rgba(10,14,22,0.88), rgba(10,14,22,0.72))
Border-top:    1px solid rgba(255,255,255,0.08)
Backdrop:      blur(14px)
Height:        ~87px

Top reveal bar:
  Height: 3px
  Background: linear-gradient(90deg, #ff3b5f, rgba(255,59,95,0.1))
  Width: animated from 0% → 100% over 400ms (easeOutExpo)

Entry animation: slide-in from left, 700ms, easeOutExpo
```

---

## SECTION 9: TITLE SEQUENCE

### Layout: centered, all text stacked
```
[KICKER: "CONSENSUS INTELLIGENCE" — gold, 11px, tracking 0.24em]
[TITLE: "PROTOCOL PULSE" — white, 72px, weight 950, tracking -0.06em]
[SUBTITLE: "Daily Bitcoin Brief • March 2026" — #d9e1f7, 18px]
[PULSE LINE: horizontal gradient line, animated width, centered]
```

### Background: standard three-source glow + radial glow behind title
```
Radial glow: circle, rgba(255,59,95,0.10), centered on title, radius ~300px, blur(10px)
```

### Animation:
```
Logo scale: 0.85 → 1.0 over 20 frames (easeOutExpo)
Title opacity: fade in over 15 frames
Subtitle: delayed fade in (starts at frame 10)
Pulse line: width animates from 0 → 300px starting at frame 15
Duration: 4 seconds total (120 frames at 30fps)
```

---

## SECTION 10: OUTRO

### Content:
```
[KICKER: "TOMORROW'S BRIEF STARTS NOW" — gold, 10px]
[TITLE: "PROTOCOL PULSE" — white, 64px, weight 950]
[CTA: "Subscribe for tomorrow's brief." — #d7def4, 18px]
[EQUALIZER BARS: 5 bars, red/coral gradient, animated bounce]
```

### Equalizer Bars:
```
Count: 5 bars, centered
Width: 10px each, gap: 8px
Height: animated sinusoidal, 14-46px range
Color: linear-gradient(180deg, #ff3b5f, #ff7a4f)
Shadow: 0 0 12px rgba(255,59,95,0.2)
Animation: staggered bounce, 1.4s cycle
```

### Rules:
- NO narration over outro (just visual + outro jingle)
- Ends ABRUPTLY — no fade to black
- Duration: 3-4 seconds
- Info bar HIDDEN during outro

---

## SECTION 11: TRANSITION DESIGN

### Glitch Sweep Transition:
```
Duration: 1.0 second (30 frames at 30fps)
Elements:
  1. Three skewed sweep bars (positions: 18%, 44%, 70% from top)
     - Transform: skewX(-25deg), translate from -120% to +180%
     - Background: linear-gradient(90deg, transparent, rgba(255,59,95,0.20), rgba(255,255,255,0.10), transparent)
     - Blur: 2px
     - Staggered timing: 0ms, 80ms, 140ms delay

  2. Radial flash at peak (frames 6-14)
     - Center-origin radial gradient
     - rgba(255,255,255,0.08) at center → rgba(255,59,95,0.04) → transparent
     - Fades in/out over 8 frames

Audio: custom_whoosh.mp3 synced to visual peak
```

---

## SECTION 12: COLD OPEN SPECIFICS

### Per PRODUCTION_DESIGN_LAWS:
- First frame: NO logo, NO music, immediate voice + face on screen
- Eyebrow kicker above headline (gold)
- Large headline (52-64px, 2-3 lines)
- Body description (17px, max 480px width)
- PiP preview card: right side, showing upcoming speaker

### Visual Hierarchy:
```
1. Eyebrow kicker (gold) — tells viewer what category
2. Headline (white, massive) — the hook
3. Body (light blue) — context
4. PiP preview (right) — face on screen + "COMING UP"
5. Waveform (bottom) — audio visualization
6. Info bar (gold, bottom) — always present
```

### NO logo in cold open. NO branding except the info bar.
The CONTENT is the brand. The info bar handles brand presence.

---

## SECTION 13: PARTNER CLIP SPECIFICS

### Full-frame clip with:
- Subtle warm glow behind speaker (rgba(248,193,92,0.2), radial, behind face area)
- Small "PROTOCOL PULSE" watermark: top-right, 10px, monospace, 50% opacity
- Lower third: slides in from left at clip start, holds 5 seconds, slides out
- Info bar: visible (gold)

### NO waveform during partner clips
### NO background animation during partner clips
### Let the clip BREATHE — the guest's face is the visual

---

## SECTION 14: REMOTION IMPLEMENTATION GUIDE

### Component Architecture:
```
<Episode>
  <BackgroundSystem />           // 7 layers (gradient, grid, noise, scanlines, rings, sweep, vignette)
  <Scene type={manifest.type}>   // Switches based on manifest segment type
    <ColdOpen />                 // or <TitleSequence /> or <PartnerClip /> etc.
  </Scene>
  <WaveformBand />               // Gold gradient EKG (hidden during clips)
  <GoldInfoBar />                // ALWAYS visible except title + outro
  <GlitchTransition />           // Between segments
</Episode>
```

### Each scene reads from the manifest:
```tsx
const segment = manifest.segments[currentIndex];
// segment.type determines which scene component renders
// segment.screen_mode determines visual treatment
// segment.music_state determines audio
// segment.logo_allowed determines brand presence
// segment.primary_visual_type determines what fills the scene
```

### FFmpeg Equivalent (for non-Remotion assembly):
```bash
# Gold info bar overlay
-filter_complex "
  [base]drawbox=x=0:y=1038:w=1920:h=42:c=#f8c15c@0.9:t=fill[bar];
  [bar]drawtext=text='BTC 96,482':x=20:y=1048:fontsize=24:fontcolor=#141515:fontfile=JetBrainsMono[ticker]
"

# Glassmorphism card effect
-filter_complex "
  [bg]crop=w=680:h=300:x=620:y=200[crop];
  [crop]boxblur=16[blurred];
  [base][blurred]overlay=x=620:y=200[glass]
"
```

---

## SECTION 15: QUALITY CHECKLIST

Before any render ships, verify these visual standards:

□ Background has visible depth (three glow sources, not flat black)
□ Gold info bar present on all scenes except title + outro
□ Eyebrow kickers are gold, uppercase, with proper tracking
□ Headlines use the correct weight (900+) and tracking (-0.04em)
□ PiP preview shows actual video, not static image
□ Lower thirds slide in with animated reveal bar
□ Social cards enter/exit with proper animation (no dark gaps)
□ Data segment has chart SVG with gradient fill + pulsing dot
□ Waveform uses gold gradient (not red-only)
□ No logo in narration segments (per Logo Restraint Rule)
□ Stat card deltas use correct colors (lime=up, coral=down)
□ Transitions are exactly 1.0 second with synced whoosh
□ No pure white (#ffffff) text — always #eef2ff
□ No pure black (#000000) backgrounds — always #06070b minimum
□ Monospace font used for ALL numerical data
□ Scanlines present but subtle (4% opacity max)

---

*This document defines the complete visual language for Protocol Pulse video output.
Every Remotion component, FFmpeg filter, and visual decision must reference this.
Pair with: PRODUCTION_DESIGN_LAWS.md, PIPELINE_MANIFEST_SPEC.md, DEFINITIVE_BUILD_PROMPT.md*

