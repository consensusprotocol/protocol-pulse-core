# Batch 63 cycle 1: no consensus findings
glm F1 [low], 1 vote: "latest() defaults kind to 'moments' and silently reuses old story entries as moments verdicts".
It does not. latest() keeps an entry only when e.get("kind", "story") == kind, so an entry without a kind is a STORY
entry and never matches 'moments'. Every result under this code is also under a new scorer_sha (story_semantics.py and
stand_alone.py changed), so it lives in a new file. test_latest_prefers_a_scored_entry_for_the_event holds such a
kind-less entry and reads it only as story. No change.
