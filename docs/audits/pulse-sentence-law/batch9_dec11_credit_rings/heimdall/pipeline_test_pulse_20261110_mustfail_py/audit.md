# Heimdall audit

**Question:** DEC-11 (orchestrator 2026-11-11 13:15, decided): G12/G15 measure the credits ring by what the renderer draws (segment_v1/scene_shoutout.render_shoutout: brand-red #FF1A1A ring of radius avatar_diam//2 + ring_gap around each node at a fixed card-layout position), not by a generic circle/contour search over avatar artwork (OD-1: the capital N of 'Natalie Brunell' and an orange avatar background misfired). New pipeline/credit_rings.py: card_layout mirrors the renderer; a ring = an external contour of G12's unchanged brand-red mask (R>100, R>G+40, R>B+40) with a ring-sized bounding box; ellipse fitted to that contour; G15 aspect tolerance unchanged (>= 0.95); G12 count == channels in the EDL, unchanged, plus each ring at its layout position. DEC-11's must-fail is yesterday's card, but measured its RINGS are round (0.999-1.000): its D4 defect was the 1280x720 thumbnail squashed into each disc; so G15 also checks each disc correlates (r >= 0.90) with the credited channel's registered avatar (measured 0.999-1.000 on v2f and today's cards; yesterday's 0.297 / -0.030 / -0.142). run_fresh passes the credited channels (hook first, then clips, each once, as shoutout.build_shoutout). Tests: yesterday's card fails G15 on the avatars with round rings; v2f and today's cards pass G12 + G15; a card squeezed to 80 % width fails G15 on ring aspect; 3 rings for 4 channels fails G12. Find real defects only: misfires on correct cards, a warped or wrong card that passes, fail-open paths (missing frame, missing avatar, channels None), layout formula drift from the renderer. (this chunk: pipeline/test_pulse_20261110_mustfail.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0084
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_pulse_20261110_mustfail.py:0** The skip condition for test_todays_four_avatar_card_passes_g15_and_g12 only checks for segment.mp4, but the test also requires segment_vertical.mp4 and qa/transitions_timeline.json. If those are missing, the test raises FileNotFoundError instead of skipping.
  - evidence: `@unittest.skipUnless(os.path.isfile(os.path.join(REPO, "runs", "pinned_20261111_172202", "out", "segment.mp4")),
                     "Nov 11 DEC-10 recut not on this machine")
def test_todays_four_av`
  - fix: Check all required files in the skip condition, e.g., use all(os.path.isfile(...) for ...) for both segment.mp4 and segment_vertical.mp4, and also verify qa/transitions_timeline.json exists.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
