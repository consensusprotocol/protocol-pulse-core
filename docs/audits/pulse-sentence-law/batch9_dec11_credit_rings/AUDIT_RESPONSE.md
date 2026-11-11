# Batch 9 (DEC-11: G12 / G15 measure the credits ring the renderer draws): dispositions

DEC-11 (orchestrator 2026-11-11 13:15 ET, decided). Implemented in pipeline/credit_rings.py (card layout
mirroring segment_v1/scene_shoutout.render_shoutout; ring = an external contour of G12's unchanged brand-red
mask with a ring-sized bounding box; ellipse fitted to that contour), G12 (segment_v1/qa_gates.py: count ==
EDL channels, each at its layout position) and G15 (pipeline/gates.py: aspect >= 0.95 unchanged). Measured:
yesterday's card's RINGS are round (0.999-1.000, at the layout positions); its D4 defect was the 1280x720
video thumbnail squashed into each disc. To keep DEC-11's must-fail, G15 also requires each disc to correlate
>= 0.90 with the credited channel's registered avatar (0.999-1.000 on every v2f and Nov 11 node, both formats;
yesterday 0.297 / -0.030 / -0.142).

Audited: cross-LLM GPT-4o + Gemini (Grok blocked by the xAI ceiling); Heimdall deepseek + qwen27b per file, and
a second pass on the fixed G15 / credit_rings diff (heimdall_r2/). The audit feature name is the session's
standing "pulse-sentence-law" for every Pulse Check batch; this batch is the credits gates.

## Implemented
- Heimdall consensus [high] gates.py (qwen27b F1; both agree) + [medium] run_fresh.py + [medium]
  credit_rings.py (channels None): G15 skipped the avatar check when channels was None / empty (fail-open).
  Now G15 FAILS when the credited channels are unknown (None or []) or fewer discs are measured than channels
  credited; disc_matches returns [] for no channels instead of raising. Test:
  test_g15_fails_closed_without_the_credited_channels (yesterday's card, channels None and []).
- Heimdall not-agreed qwen27b F2 (gates): an empty disc list for credited channels: covered by the same
  length check.
- Heimdall consensus [low] (test skip): the four-avatar test now skips unless both finals and the timeline exist.
- Heimdall not-agreed qwen27b F4: the inner correlation radius now scales with the card (12 px at 1080).
- Cross-LLM P2 [Gemini]: channels.json is loaded once (lru_cache); P2 synthesis: registered_avatar documents
  that its paths come only from the internal registry.

## Rejected, with evidence
- Heimdall consensus [high] credit_rings.py "AVATAR_R_MIN is never referenced; yesterday's card would pass":
  the module is measured by the gate, which enforces it: pipeline/gates.py G15 compares every disc's r with
  CR.AVATAR_R_MIN; test_yesterdays_card_fails_g15_on_the_squashed_avatars_inside_round_rings asserts
  avatar_ok False on yesterday's card (the per-file chunk did not see gates.py).
- Cross-LLM P1 [both] "remove the sys.path.insert in qa_gates.gate_g12": the same function-level pattern is
  how this frozen module already imports pipeline modules (gate_g3c: `sys.path.insert(0, ... "pipeline")`);
  the repo's pipeline directory is not a package.
- Cross-LLM P2 [Gemini] "move in-function imports to module top": the codebase imports lazily inside gates
  on purpose (cv2 / models only when a gate runs); style, not changed.
- Heimdall not-agreed deepseek F1 (qa_gates) "bool(at_layout) is truthy, passes with one ring at layout":
  at_layout is all(...) over EVERY layout position (credit_rings.check_card); test
  test_three_rings_for_four_credited_channels_fail_g12.
- Heimdall not-agreed qwen27b F2 (credit_channels with edl None): run_fresh loads edl.json, which always
  exists after stage validate; a missing file raises and HOLDs through main()'s handler.

## Verification
pipeline/test_pulse_20261110_mustfail.py TestD4Credits: 11 passed (yesterday's card fails G15 on the avatars
with round rings; v2f and today's four-avatar card pass G12 + G15 in both formats; an 80 %-squeezed card fails
G15 on ring aspect; 3 rings for 4 channels fails G12; G15 fails closed without channels).
