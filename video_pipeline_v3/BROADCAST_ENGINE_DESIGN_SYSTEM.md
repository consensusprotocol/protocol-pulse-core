# BROADCAST ENGINE V2 DESIGN SYSTEM — GOSPEL
# Supersedes BLACK_DIAMOND_DESIGN_SYSTEM.md for scene rendering
# Status: ACTIVE | Created: 2026-03-07

## Philosophy
"Premium sports-broadcast intelligence" — ESPN / UFC MMA Central energy with Bloomberg Terminal restraint.
NOT cyberpunk. NOT gold. Harder, cleaner, more athletic.
Red / Black / White only. Motion is athletic and event-driven, not decorative.

## Color System
| Token          | Hex         | Usage                                      |
|----------------|-------------|---------------------------------------------|
| OBSIDIAN       | #020304     | Deepest bg — almost black, not pure black   |
| DEEP_PANEL     | #050607     | Elevated surface                            |
| SIGNAL_RED     | #FF334D     | Primary accent — slightly warmer red        |
| STARK_WHITE    | #F4F5F8     | Primary text — slightly warm white          |
| MUTED          | #FFFFFF55   | Secondary text ~33% white                   |
| EMERALD        | #6EE7B7     | Positive/bullish metrics                    |
| GRADIENT_RAIL  | red-white   | #FF334D -> #FFFFFF -> #FF8595               |

## Fonts
- FONT_BOLD: /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
- FONT_MONO: /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf

## BANNED
Blue, cyan, purple, gold, amber — all banned from Broadcast Engine V2.

## 6 Scene Types

### Scene 1: COLD OPEN
- Tag: "BREAKING INTELLIGENCE" / "REDLINE"
- Left 58% (x=0,y=72,w=1110,h=960): impact text zone
- Right 42% (x=1120,y=90,w=760,h=900): ImpactMonitor panel with 4 metrics

### Scene 2: NARRATOR + PiP (SIGNATURE)
- Tag: "NARRATIVE SETUP" / "SIGNATURE"
- Left 58%: narration context
- Right 42% (x=1120,y=140,w=740,h=500): PiP preview panel

### Scene 3: PARTNER CLIP
- Tag: "SOURCE ON SCREEN" / "SOURCE"
- Full-frame B-roll, minimal overlay
- Premium lower-third, watermark top-right only

### Scene 4: DATA SEGMENT
- Tag: "MARKET STRUCTURE" / "ANALYTICS"
- Left 58%: text + 2x2 metric cards
- Right 42% (x=1120,y=90,w=760,h=820): chart panel

### Scene 5: SOCIAL STACK
- Tag: "SIGNAL LAYER" / "SENTIMENT"
- Header zone top, 3 social conviction cards below (3-column grid)

### Scene 6: WRAP / VERDICT
- Tag: "FINAL TAKE" / "RESOLVE"
- Left 58%: final text
- Right 42% (x=1120,y=140,w=740,h=680): Signal Wave panel

## Shared Elements

### Broadcast Background
- Obsidian base (#020304)
- 3 radial glows: top-left red/18, top-right white/6, bottom-center red/10
- Perspective grid (bottom 65%, very subtle)
- Vignette + film grain + scanlines

### Top System Bar
- Floating pill at x=24,y=18,w=1872,h=52
- "Protocol Pulse Live" left, "Narration Layer" right

### Signature Info Rail (ticker)
- Red-white-red gradient bar at y=1034, h=46
- BLACK text on gradient background
- BTC price left, PROTOCOLPULSE.IO center, date right

### Narration Wave
- 1920x120 EKG-style waveform at y=914 (above info rail)
- showwaves mode=line, white primary + red accent
