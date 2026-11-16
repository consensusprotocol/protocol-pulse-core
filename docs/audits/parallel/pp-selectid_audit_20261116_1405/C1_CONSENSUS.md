# C1 CONSENSUS — pp-selectid audit 20261116_1405 (RULING 123 (2): a 16:9-only hook)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: mimo 0,
gemma 1 (a P0), qwen 1. Cycle 1 $0.0094 of Heimdall, not capped.

gemma's P0 ("the seal disables the exception: crop_only returns None once the record has formats assigned"): NOT SO.
visual_pin.formats(rec) (visual_pin.py:268, unchanged) never reads the record's "formats" key: it answers ["16x9"] only
for a burned CAPTION the 9:16 crop cuts (rec["burned_in"] items of kind "caption"); and RENDER_16X9_ONLY is True
(visual_pin.py:48: the integrator's format-aware release landed, c396c3c8). Sealing formats ["16x9"] on the hook's
record therefore changes nothing crop_only reads. The tests run the real build through the final per-segment check:
test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only gets a PACKAGE whose segment 0 is the 16:9-only hook
(the line-up check excused it), and mutations W2 / W4 die on exactly that path (gemma's P3 answered).
qwen's P1 ("with RENDER_16X9_ONLY False, crop_only returns None"): that is the intent, and it is now said directly:
CHANGED (in cycle 2's diff) the guard to "not RENDER_16X9_ONLY": the exception makes a 16:9-only pin, so it fires only
when the render can pass one; equal today (the flag is True), stricter if it ever is not.
gemma's P2 (opens_16x9 also checks the record's formats): kept on purpose: the excuse holds only while the sealed record
still says 16:9 only (a record seen again without it is not excused).
