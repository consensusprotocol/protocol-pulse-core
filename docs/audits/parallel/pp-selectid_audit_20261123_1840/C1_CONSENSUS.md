# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 3 of 3 (gpt-oss-20b in the first run; qwen3.8-27b and gemma-4-31b-it were HTTP 429 there and answered
in a retry of the same prompt, seats limited to those two). P0/P1: 0, 0, 0.
- qwen P2 (the sponsor row's "n" is len(exc), every clip's exclusion verdict, not the flagged count): DISPROVED as a
  defect. "n" in these rows is how many items the row's check read: the sibling graphics row has n = len(visual), one
  visual record per clip, flagged or not. The flags list carries one sentence per kept marked clip (qwen's own answer
  to check 3: "exactly one entry per kept marked clip"). No change.
- qwen P3 (ad_before_soft tells a before-marker by str.endswith): the reason strings are moments.ad_read_marker's own
  two fixed forms (moments.py:365: "ad-read marker '<hit>' in the moment" | "... in the sentence before it"); the test
  test_the_mark_is_the_passs_own_and_the_cache_key_its_own feeds both forms. No change.
- qwen P3 (ad_before_soft mutates the list in place): by design, the pass's own copies (with_verdict gives _build its
  own copy of every moment; the mark is popped first, test-pinned, mutation S5 killed). No change.
All seats: check 1 (clip's own ad words) NO; check 2 (clean pass / cross-pass cache) NO; check 3 flag right YES;
check 4 (gate_problems refuses a legitimate live pin) NO. Cycle 2 cross-examines the same diff.
