# Heimdall audit

**Question:** DEC-11 (orchestrator 2026-11-11 13:15, decided): G12/G15 measure the credits ring by what the renderer draws (segment_v1/scene_shoutout.render_shoutout: brand-red #FF1A1A ring of radius avatar_diam//2 + ring_gap around each node at a fixed card-layout position), not by a generic circle/contour search over avatar artwork (OD-1: the capital N of 'Natalie Brunell' and an orange avatar background misfired). New pipeline/credit_rings.py: card_layout mirrors the renderer; a ring = an external contour of G12's unchanged brand-red mask (R>100, R>G+40, R>B+40) with a ring-sized bounding box; ellipse fitted to that contour; G15 aspect tolerance unchanged (>= 0.95); G12 count == channels in the EDL, unchanged, plus each ring at its layout position. DEC-11's must-fail is yesterday's card, but measured its RINGS are round (0.999-1.000): its D4 defect was the 1280x720 thumbnail squashed into each disc; so G15 also checks each disc correlates (r >= 0.90) with the credited channel's registered avatar (measured 0.999-1.000 on v2f and today's cards; yesterday's 0.297 / -0.030 / -0.142). run_fresh passes the credited channels (hook first, then clips, each once, as shoutout.build_shoutout). Tests: yesterday's card fails G15 on the avatars with round rings; v2f and today's cards pass G12 + G15; a card squeezed to 80 % width fails G15 on ring aspect; 3 rings for 4 channels fails G12. Find real defects only: misfires on correct cards, a warped or wrong card that passes, fail-open paths (missing frame, missing avatar, channels None), layout formula drift from the renderer. (this chunk: pipeline/gates.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0092
## Consensus findings (majority of panel agrees)
- **[high] pipeline/gates.py:449** Fail-open: when `channels` is None (the default) or an empty list, the entire D4 avatar-correlation check is silently skipped. `avatar_ok` remains True, so a card with wrong or squashed avatars (e.g. yesterday's 1280×720 thumbnails) passes G15 as long as the rings are round. The audit explicitly lists 'channels None' as a fail-open path to catch.
  - evidence: `def gate_g15(final_mp4, segments, qa_dir, channels=None):`
  - fix: Make `channels` a required positional argument (remove the `=None` default), or add an explicit guard: if channels is None, set avatar_ok = False and print a FAIL message, so the gate fails closed when the caller omits the credited channels.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [medium] Fail-open on missing/zero discs: if `CR.disc_matches(img, channels)` returns an empty list (e.g. avatar image files missing, disc region empty, or mask mismatch), the for-loop body never executes, `avatar_ok` stays True, and no failure is recorded. The audit asks about 'missing avatar' as a fail-open path; the code only handles the per-disc case (`d["r"] is None`) but not the case where zero discs are returned for a non-empty `channels` list. (agree: 1)

## Added in cross-examination (not voted on)
- none
