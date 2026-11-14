# Batch 56 cycle 1: consensus and what was done

- C1 [medium], stale valley_in when the hook's cut moves: implemented. A moved cut is a cut_accept-clean candidate from cut_candidates, so valley_in is False; unchanged cuts keep the pick's flag. For a non-file-head hook, the plan's lead_in_pad_s is always 0.0 (only file heads get a pad in edge_plan), so the hook's pad_s cannot diverge from it.
- qwen F1 (0 votes, but correct), the cut's fade-in is not applied in the measurements: implemented. _cut_head applies the clip's own linear fade-in (prepare's order: fade, then the D1 pad prepended), and hook_lead_at and padded_lead_ms measure that. Re-measured: pin #1 is still refused (best 60 ms); the medley hook still keeps its cut, and check_medley_reference REPRODUCES.
- qwen F2 / glm, cross-examination: step 2 measures with each candidate's own fade now, so what passes step 2 is what the prepared clip will hold.
- glm, cross-examination: added test_a_pad_whose_room_tone_cannot_be_built_is_skipped. The < 80 negative case was already in test_the_pad_only_where_the_padded_head_measures_80_ms (0.98 at 40 ms skipped).
- qwen F3 (0 votes): room_tone returns exactly n samples (out[:n]).
