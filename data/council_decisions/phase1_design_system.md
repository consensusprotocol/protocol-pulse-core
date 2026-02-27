# Phase 1 Council Decision — Design System + Base Layout
**Date**: 2026-02-25
**Council Mode**: Single-agent (no external API keys configured)

## Brief
Create a world-class dark theme design system and base layout for a Bitcoin intelligence
platform. Bloomberg Terminal dark mode meets Apple's design language.

## Merged Build Specification

### Migration Strategy
- Keep Bootstrap loaded for backward compatibility with 80+ existing templates
- New `pulse.css` becomes the design system authority
- Existing `protocol-pulse-tokens.css` colors shift from red (#e54848) to teal (#00d4aa)
- All new components use `pp-` prefix with new palette
- Existing pages migrate incrementally

### Color Palette
- `--pp-black`: #0a0a0a (primary background)
- `--pp-teal`: #00d4aa (primary accent — replaces red)
- `--pp-amber`: #f5a623 (secondary accent / warning / Bitcoin)
- `--pp-surface`: #111111 (card backgrounds)
- `--pp-surface-2`: #1a1a1a (elevated surfaces)
- `--pp-border`: rgba(255,255,255,0.08)
- `--pp-text`: #f0f0f0 (primary text)
- `--pp-text-secondary`: rgba(255,255,255,0.65)
- `--pp-text-muted`: rgba(255,255,255,0.4)

### Typography
- Inter (body, UI) — weights 400, 500, 600, 700
- JetBrains Mono (data, prices, code) — weights 400, 500, 600, 700

### Component Architecture
1. **pp-nav** — Glassmorphism navigation with live BTC ticker
2. **pp-card** — Base card with hover glow effect
3. **pp-grid** — CSS Grid responsive system (1/2/3/4 columns)
4. **pp-skeleton** — Loading skeleton animations
5. **pp-btn** — Button system (primary teal, secondary amber, ghost)
6. **pp-badge** — Tag/label system
7. **pp-section** — Page section containers
8. **pp-footer** — Redesigned footer

### File Manifest
- CREATE: `static/css/pulse.css` (master design system)
- MODIFY: `templates/base.html` (new nav, footer, load Inter + pulse.css)
- MODIFY: `static/css/protocol-pulse-tokens.css` (update tokens to new palette)

### Responsive Breakpoints
- 375px (mobile)
- 768px (tablet)
- 1024px (desktop)
- 1440px (wide desktop)
