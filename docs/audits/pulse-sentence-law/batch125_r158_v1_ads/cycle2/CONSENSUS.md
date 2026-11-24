# Batch 125, cycle 2
Seats: gemma PASS (1.0); glm PASS (0.6, 1 low); qwen27b (medium) PASS (0.72, 1 low).
- glm (low), "the line's polarity is inverted against the other lines": DISPROVED. It follows the convention of three
  existing lines (no_letterbox_on_talking_heads, no_bad_boundary_frames, no_next_shot_before_transition): the key says
  what must hold and "yes" means it holds. Live, both models answered "no" exactly where ads were seen (4 of 4) and "yes"
  on the clean control (2 of 2).
- qwen (low), "'presented as an ad' scopes only the first item, so a show's own explainer of sign-up bonuses could be
  called an ad": a false positive HOLDS (fails closed), which the ruling accepts ("cannot tell = an ad"). Recorded.
No change.
