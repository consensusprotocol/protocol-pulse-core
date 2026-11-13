# Batch 64 cycle 1: one consensus finding, fixed
glm F1 [medium], agreed by qwen27b: "the reuse key is span + window + approved_text only; role and trimmed_leading /
untrimmed_start are not part of it, so a request differing only in them gets the earlier answer although the lock
depends on them". VALID for the trimmed fields: trimmed_lock changes the lock (i0, the text) and can refuse.
role does not change the lock (make_lock and adjudicate_lock never read it), but it names a validate_range hold's tag.
FIX: KEY = (role, approved_text, trimmed_leading, untrimmed_start). Every entry records them, and latest() / the reuse
filter on all four. A reused entry is copied whole (its role is no longer overwritten). New test:
test_the_reuse_key_is_every_field_the_answer_depends_on (a role change and a trimmed request are answered again, from
ONE cached decode; an identical request is reused). The fake transcriber now caches by path, as the real
_whisper_transcribe does. test_lock_precheck: 13 passed.
Raised but not agreed, checked against the code, no change:
- qwen27b F1 [critical] "no lease when every request is cached": a fully cached request runs no decode and touches no
  GPU (answer() copies entries), so there is nothing to lease.
- qwen27b F2 [high] "a render mid-decode makes the request an error": decode() returns None, serve_once breaks before
  adding it to `decoded`, and only requests in `decoded` are answered. It stays pending (test_a_render_comes_first).
- qwen27b F3: window floats are stored from the same request numbers, float(lo), float(hi): an exact comparison.
- qwen27b F4: the flag check after taking the lease is exercised by the side_effect sequence [False, False, True].
- glm F2: a span sent alone after a line-up has a different window, so it may decode differently. Not reusing it is
  by design (the window is part of the key).
- glm cross-examination: decode() looks for sources/<vid>.mp4, which is _download_window's own out_path. Concurrent
  writers: run ONE serving process (now stated in the docstring).
