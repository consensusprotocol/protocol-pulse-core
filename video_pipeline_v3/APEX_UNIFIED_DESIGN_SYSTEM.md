# APEX UNIFIED DESIGN SYSTEM — GOSPEL
# Supersedes BLACK_DIAMOND_DESIGN_SYSTEM.md and BROADCAST_ENGINE_DESIGN_SYSTEM.md
# Status: ACTIVE | Created: 2026-03-08
# This is the synthesis of all 3 design generations. Best elements merged.

## Philosophy
"Sovereign Broadcast Intelligence" — the best of all three systems:
- **VDS**: Finance terminal density, gold kickers, color temperature pacing
- **Black Diamond**: Tactical L-brackets, 108px impact type, surveillance scanlines
- **Broadcast Engine V2**: 6-scene architecture, cinematic glows, glassmorphic pills

## Color System
| Token          | Hex       | Source | Usage                                      |
|----------------|-----------|--------|---------------------------------------------|
| COLOR_BG       | #020304   | BEV2   | Cinematic obsidian base (not flat black)    |
| COLOR_PANEL    | #050607   | BEV2   | Elevated surface                            |
| COLOR_PANEL2   | #080A0C   | APEX   | Secondary surface                           |
| COLOR_RED      | #FF0000   | BD     | Signal red — all accents, brackets, borders |
| COLOR_RED_WARM | #FF334D   | BEV2   | Warm red — transition elements only         |
| COLOR_WHITE    | #F4F5F8   | BEV2   | Warm white — not pure white                 |
| COLOR_GOLD     | #F8C15C   | VDS    | EYEBROW KICKERS ONLY (not full brand)       |
| COLOR_MUTED    | #888888   | BD     | Secondary labels                            |
| COLOR_MUTED2   | #555555   | APEX   | Metadata, timestamps                        |
| COLOR_GREEN    | #6EE7B7   | BEV2   | Emerald — positive/DONE                     |
| COLOR_CORAL    | #FF8BA0   | VDS    | Coral — negative/warning                    |
| COLOR_RED_DIM  | #1A0000   | BD     | CTA box backgrounds                         |
| COLOR_TICKER_BG| #0C0C0C   | BD     | Ticker bar background                       |

## BANNED Colors
Blue (#00D4FF), Cyan (#5de4ff), Purple (#7B2FFF) — all permanently banned.

## Background (7 layers)
1. BEV2 cinematic obsidian base (#020304)
2. BEV2 3-glow radial (top-left red, top-right white, bottom-center red)
3. VDS perspective grid (bottom 30%, white @4% opacity)
4. BD scanlines (horizontal every 4px, red @2.5%)
5. Vignette (center clear, edges dark)
6. Film grain (SKIPPED — geq too slow; can be re-enabled)
7. BD red border frame (2px all edges, #FF0000 @75%)

## Header Bar (BD structure + BEV2 glassmorphic pill)
- Floating pill: x=20,y=12,w=1880,h=52, black @55%
- Red left accent line (3px, BD signature)
- Left: "● PROTOCOL PULSE" white bold 20px + "LIVE" red 16px
- Center: "Broadcast Signature System" muted mono 11px
- Right: "Motion Active" | "Narration Layer" | "RECON-ID: {id}" muted mono 11px
- Bottom separator: red @25%

## Info Rail (BEV2 gradient bar)
- Height: 48px at y=1032
- 3-zone gradient: red @85% | white @90% | warm red @85%
- BLACK text: BTC price left, PROTOCOLPULSE.IO center, date right
- Font: bold 14-15px

## Narration Wave (BEV2 EKG dual-layer)
- Zone: 1920x120 at y=912 (above info rail)
- Primary: showwaves mode=line, white @80% + red @40%, sqrt scale
- Accent: showwaves mode=cline, warm red @30%, log scale
- Blended via screen mode

## Corner Brackets (BD tactical)
- All 4 corners: 40x4px L-bracket in signal red (#FF0000)

## Scene Types (BEV2 6-scene routing — unchanged)

### Scene 1: COLD OPEN
- BD left impact panel (72px font SIGNAL/DETECTED)
- VDS 2x2 metric cards right (gold eyebrow labels)
- Chart panel with rising bar chart + pulse dot
- Gold eyebrow: "BREAKING INTELLIGENCE"

### Scene 2: NARRATOR + PiP
- BEV2 text zone left + PiP preview right
- BD mini corner brackets on PiP frame (16px)
- Gold eyebrow: "COMING UP NEXT" above PiP
- Status pills: "ORACLE NARRATION ACTIVE" + "Story Arc Locked"

### Scene 3: PARTNER CLIP
- BEV2 restraint — full-frame B-roll
- Glass lower-third with red top accent line
- Speaker name bold 26px + source info
- PROTOCOL PULSE watermark top-right (red, 18px, 60%)

### Scene 4: DATA SEGMENT
- Gold eyebrow labels on all metric cards (VDS)
- Emerald positive / coral negative deltas (VDS)
- Right chart panel with gold "Model Active" pill
- Gold eyebrow: "MARKET STRUCTURE"

### Scene 5: SOCIAL STACK
- BEV2 3-column conviction cards
- VDS gold score badges (not plain white)
- VDS gold tag labels at bottom
- BD primary card red accent border, others white @8%

### Scene 6: WRAP / VERDICT
- BEV2 waveform visualization right
- BD episode segments tracker below (DONE/ACTIVE/PENDING)
- Gold eyebrow: "EPISODE SEGMENTS"
- DONE=emerald, ACTIVE=red, PENDING=dim

## Intro Cold Open Card
- APEX background (all 7 layers)
- Corner brackets
- "PROTOCOL PULSE" centered white bold 72px
- "PULSE CHECK" centered red bold 52px
- Gold date eyebrow
- "// SIGNAL DETECTED //" red mono 16px
- Fade in 0.4s, fade out 0.4s

## Transitions
- VDS glitch sweep (3-layer diagonal red + white flash + radial pulse)
- Total: 0.35s (athletic, per BEV2 philosophy)

## Color Temperature Pacing (VDS)
- Cold Open: HIGH ENERGY — red + gold dominant
- Data: ANALYTICAL — cooler, gold labels for clarity
- Social: WARM — gold score badges
- Wrap: WARM GOLD — resolved energy
