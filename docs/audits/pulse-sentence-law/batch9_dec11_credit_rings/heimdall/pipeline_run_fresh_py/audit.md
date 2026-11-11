# Heimdall audit

**Question:** DEC-11 (orchestrator 2026-11-11 13:15, decided): G12/G15 measure the credits ring by what the renderer draws (segment_v1/scene_shoutout.render_shoutout: brand-red #FF1A1A ring of radius avatar_diam//2 + ring_gap around each node at a fixed card-layout position), not by a generic circle/contour search over avatar artwork (OD-1: the capital N of 'Natalie Brunell' and an orange avatar background misfired). New pipeline/credit_rings.py: card_layout mirrors the renderer; a ring = an external contour of G12's unchanged brand-red mask (R>100, R>G+40, R>B+40) with a ring-sized bounding box; ellipse fitted to that contour; G15 aspect tolerance unchanged (>= 0.95); G12 count == channels in the EDL, unchanged, plus each ring at its layout position. DEC-11's must-fail is yesterday's card, but measured its RINGS are round (0.999-1.000): its D4 defect was the 1280x720 thumbnail squashed into each disc; so G15 also checks each disc correlates (r >= 0.90) with the credited channel's registered avatar (measured 0.999-1.000 on v2f and today's cards; yesterday's 0.297 / -0.030 / -0.142). run_fresh passes the credited channels (hook first, then clips, each once, as shoutout.build_shoutout). Tests: yesterday's card fails G15 on the avatars with round rings; v2f and today's cards pass G12 + G15; a card squeezed to 80 % width fails G15 on ring aspect; 3 rings for 4 channels fails G12. Find real defects only: misfires on correct cards, a warped or wrong card that passes, fail-open paths (missing frame, missing avatar, channels None), layout formula drift from the renderer. (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0070
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/run_fresh.py:859** No guard against `credited` being None before passing to gate_g15. If `credit_rings.credit_channels()` returns None (e.g., EDL lacks a shoutout segment or is malformed), `channels=None` is forwarded to both G15 calls. The audit spec explicitly lists 'channels None' as a fail-open path to check; with no validation here, a None channels argument could cause gate_g15 to skip the avatar-correlation sub-check, letting a card with wrong/missing avatars pass G15.
  - evidence: `credited = credit_rings.credit_channels(json.load(f))
    g15_16_ok, g15_16 = G.gate_g15(final16, segs16, os.path.join(qa, "g15_16x9"), channels=credited)
    g15_9_ok, g15_9 = G.gate_g15(final9, segs`
  - fix: Add a guard after the credit_channels call: `if credited is None: credited = []` (or raise a controlled gate-fail) so that gate_g15 never receives a None channels argument. Alternatively, assert `credited is not None` and let the gate record a hard failure rather than silently skipping the avatar check.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
