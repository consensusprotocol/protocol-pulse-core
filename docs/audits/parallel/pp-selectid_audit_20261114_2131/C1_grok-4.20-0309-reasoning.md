# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 20777 / out 786 usd_reported=0.042059 usd~0.124 (upper-bound price)

**CODE AUDIT: pp-selectid-20261114_2131 (parallel reviewer)**

**Summary:** The diff implements the orchestrator's 21:10/21:31 rulings (visual-3 burned-caption handling, 16:9-only "formats" sealing + hold, ROLE claim gate, spotlight_source "format" recording, reseal directive for same-moment story replacement). It stays within "smallest diff / no new renderer / GPU0 only" constraints. Core logic for formats_of/seal, layout_block, clean_visual, vo_fidelity ROLE_RE, and prompt updates is sound and matches the provided tests. New visual sampling (1 s, 40 tiles) and prompt explicitly fix the root cause that let Blockware captions be missed. Release-auth, pin SHA, and selection-lock invariants are preserved (formats omitted when absent; old pins recompute identically).

**Findings:**

[P1] **Breaks LAW 22 (and L-d protected preview).** `layout_block()` and `clean_visual()` now reject any record where `version != "visual-3"` (or missing `burned_in` list). Frozen `references/v2f_2026-11-06` and the 2026-11-11 preview reference use earlier visual records (visual-1/visual-2). These will now fail `clean_visual` / `layout_block` on re-run, preventing byte-identical re-renders. No backward-compatibility exception, cached-record bypass, or reference-visual upgrade path is present. This is a hard regression on a governing law that must be fixed before merge. (The `RENDER_16X9_ONLY` hold compounds the issue for any re-validated old pins.)

[P2] Hard-coded `RENDER_16X9_ONLY = False` (with 15-line comment) plus the temporary hold message in `layout_block` creates a merge-time landmine once the integrator's format-aware render lands. Should be a config constant or feature flag to keep the diff minimal and auditable.

[P2] `tail_variant.py` mutates the caller's `moments` dict in-place when applying a reseal directive (`m["derived_from"] = {...}`). While tests pass and the directive is strict, this side-effect violates the "immutable input" pattern used elsewhere in the pipeline and risks subtle bugs if the same moment object is referenced by multiple pools.

[P3] Vision prompt for captions now requires the model to evaluate sliding 9:16 crops "while speaker's whole face stays inside with a tenth-of-frame margin." This is semantically complex; LLM variance could produce inconsistent "whole"/"cut" verdicts even on identical sheets. (Matches the ruling but increases flakiness of a REQUIRED gate.)

[P3] `vo_fidelity.ROLE_RE` + normalization (`replace("-","").rstrip("s")`) works for the test cases but is a parallel ad-hoc normalizer outside `pipeline/canon.py` (cf. L-k ONE CANONICAL FORM and test_canon.py's "TestSites fails any ad-hoc normaliser"). Minor duplication.

[P3] New test files (`test_formats.py`, `test_role_claims.py`) are thorough and pin the exact behaviors requested in "PLEASE CHECK," but `test_role_claims` is example-driven rather than exhaustive on all role words / slot combinations. Nit.

All other governing laws (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, M2, M12, fail-closed, canonical-form routing, release_auth exact-byte semantics, etc.) are respected. No criminal, exploit, or guideline violations. No changes to audio cuts, punctuation, edge-word fidelity, sign-off transcription, or model JSON validation.

P1_OR_WORSE: 1