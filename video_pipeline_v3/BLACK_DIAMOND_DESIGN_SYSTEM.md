# BLACK DIAMOND DESIGN SYSTEM — GOSPEL
# Supersedes VISUAL_DESIGN_SYSTEM.md (Section 19)
# Status: ACTIVE | Created: 2026-03-07

## Philosophy
"Sovereign Command Center" — MMA Central impact typography meets Bloomberg Terminal 2026 data density.
Every frame = clandestine intelligence briefing. Audio-reactive. Surveillance grid. Tactical brackets.

## Color System
| Token          | Hex       | Usage                                      |
|----------------|-----------|---------------------------------------------|
| OBSIDIAN       | #000000   | Pure black base                             |
| SIGNAL_RED     | #FF0000   | Waveforms, borders, accents, ticker text    |
| STARK_WHITE    | #FFFFFF   | Headlines, primary labels                   |
| PANEL_DARK     | #0A0A0A   | Glass panels                                |
| PANEL_DARK2    | #070707   | Left panel glass                            |
| MUTED          | #888888   | Secondary labels                            |
| DATA_GREEN     | #00FF88   | DONE status, bullish signals                |
| DATA_AMBER     | #FF8800   | PENDING / warning                           |
| RED_DIM        | #1A0000   | CTA box bg, deep glow                       |
| TICKER_BG      | #0C0C0C   | Ticker bar background                       |

## Fonts
- FONT_BOLD: /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
- FONT_MONO: /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf

## BANNED Colors
Blue (#00D4FF), Cyan (#5de4ff), Purple (#7B2FFF), Gold (#f8c15c) — all removed.

## Layout Zones (1920x1080)
| Zone        | Position           | Size       | Description                    |
|-------------|--------------------|-----------:|--------------------------------|
| HEADER      | x=0, y=0           | 1920x72   | Dark panel + red bottom line   |
| LEFT PANEL  | x=0, y=72          | 720x958   | Glass panel, 6px red left edge |
| RIGHT TOP   | x=740, y=72        | 1180x420  | Full audio waveform visualizer |
| RIGHT MID   | x=740, y=500       | 1180x160  | 3 data panels side by side     |
| RIGHT BOT   | x=740, y=660       | 1180x360  | Episode segment tracker        |
| V DIVIDER   | x=720, y=72        | 1x958     | Red vertical separator @30%    |
| TICKER BAR  | x=0, y=1032        | 1920x48   | Red scrolling intel ticker     |
| CORNERS     | All 4 corners      | 40x4px    | L-bracket, signal red          |

## Component Specs

### Header Bar
- Panel: #050505 @0.97, full width, 72px tall
- Bottom line: #FF0000 @0.8, 2px at y=70
- "PROTOCOL PULSE" white bold 28px at x=24,y=22
- "LIVE" red bold 22px at x=242,y=26
- Episode number (day of year) mono 16px muted
- "LAYER 04 ACTIVE" mono 14px red
- RECON-ID timestamp mono 13px at right edge

### Left Panel
- Glass bg: #070707 @0.92
- Red left border: 6px #FF0000 @0.92
- Eyebrow: signal red mono 13px
- Headlines: bold 108px (line 1 white, line 2 red)
- Body text: mono 20px #BBBBBB, wrapped
- CTA box: #1A0000 bg with red left accent
- Mini waveform: 680x90 at bottom of panel

### Right Top — Waveform
- showwaves 1140x200 cline red, sqrt scale
- Mirror reflection: vflip + 25% opacity
- Stacked: 1140x400 total

### Right Mid — 3 Data Panels
- BTC SIGNAL: price + sovereign signal indicator
- RENDER ENGINE: FPS + GPU info
- AUDIO AMPLITUDE: mini live waveform

### Right Bot — Episode Segments
- 4 rows: COLD OPEN, ORACLE BRIEF, CLIP REACTION, DUAL-HOST SEGMENT
- Status: DONE (#00FF88), ACTIVE (#FF0000), PENDING (#444444)

### Ticker Bar
- #0C0C0C bg, red top separator line
- "// LIVE INTEL //" static label
- Scrolling red text at 90px/s

### Corner Brackets
- All 4 corners: 40x4px + 4x40px L-bracket in signal red
