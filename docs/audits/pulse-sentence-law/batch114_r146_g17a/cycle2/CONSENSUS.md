# Batch 114 (ruling 146 (2)), cycle 2 consensus (downstream of the changed functions)

Reviewers: qwen27b (effort medium, 201.9 s, 37,228 chars of reasoning; confidence 0.92) and gpt-oss-20b (effort
medium, 12.8 s, 6,782 chars). Both returned PASS with no findings.

Traced (a)-(e):
- (a) snap_verdict raises the identical Hold for every refused snap, hook or not, and nothing is reordered.
- (b) `on` cannot be None where the new line runs (see below).
- (d) All three call sites use HOOK_ABRUPT, so the note says one line.
- (e) No reader hard-subscripts cut["hook_lead_short"] on stored entries.

What both reviewers said they could not see in the diff, checked by hand:
- (b) shot_snap.plan returns head = 0 whenever speech_on_s is None (its comprehension filters every change). Both the
  refusal line and the new hook_lead_short line short-circuit on `head`.
- (c) G16 (`_edge_row`) applies 80 ms only at a source FILE HEAD; a non-file-head IN edge needs only cut_lo..cut_hi,
  which accepted_cut's pick satisfies. The D1 pad reads the cut table's lead_in_pad_s, which the soft path sets to
  plan["in"]["lead_in_pad_s"], the value any clip gets. TRANSITIONS.json measures each prepared clip's lead and tail;
  a shorter hook lead only narrows the overlap room. No code outside the four changed files reads hook_lead (grep:
  pipeline/*.py, scripts/integrator/*.py).
- (e) For the builder: older pre-check entries have no "hook_lead_short" key; it was told to read it with .get.

Decision: no change. Batch 114 is ready. It lands in lockstep (DECODER 50fa01b400bd4231e38a9a8b77f6a0df6f16a57d6f0e22de0eb376788f039256)
AFTER the Nov 18 exception video is delivered, at the builder's request (its pin is sealed on fc204e4a4385).
