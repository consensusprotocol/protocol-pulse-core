# C1 consensus, audit 20261115_0158 (written by the builder; qwen3.8-27b P1_OR_WORSE 1, glm-5.3-flash 3; both raised a
# P1, so they agree and Grok was not asked)

## qwen P1, "production does not append ' Reply with one JSON object only.'": NOT SO
providers.HeimdallBackend.complete (base pipeline/providers.py:422) appends it, and the body test proves it: production's body and
FormatBackend's are equal once the two added fields are removed. No change.

## glm P1, "the copy could differ from production on another prompt shape": ACCEPTED, test widened
The body test now also asks a VISION prompt of both back-ends and pins that the bodies are equal but for the two
fields. Mutation Y3 (the body drifts from production's) is killed.

## glm P1, "medium's reasoning counts against the output budget": TRUE AND INTENDED, now documented
The reasoning counts against the same output budget (max_out, 16,000 tokens) that production gives every call; the
01:5x probe showed completion_tokens includes the reasoning. An answer that budget cuts is "truncated" by shape() and
counts against medium in choose(), as it would in production. Stated in the docstring.

## glm P1 -> P2 (glm's own downgrade), the overshoot past the stop: BOUNDED BY MEASUREMENT, documented
At most --workers (6) calls are in flight when the ledger reaches $0.38. Ruling 110 measured this model at medium at a
median of $0.000058 and a maximum of $0.001122 a call, so they add at most about $0.007, inside the $0.02 margin to the
order's $0.40.

## glm, choose() (glm's own P3), and a real gap found here: FIXED
When no effort gives a single valid answer on the sample, choose() returns None and no full run is made: nothing would
be measured. Test added (choose returns None for 0 valid; a single valid answer is enough); mutation Y13 is killed.

## glm P2s
- "valid JSON, wrong fields" can also be right fields with refused labels or values: RENAMED "valid JSON, not the
  contract".
- SOURCE_110 / CUT_NOTE defined below table(): moved above it.
- the names fallback: a key missing from names falls to replay110's name(), which raises KeyError for any non-110
  key, so a misconfiguration fails loudly. The cost fragment ("_reported if the gateway reports cost only when...")
  states no defect; production reads usage.cost the same way. No change.
After the fixes: test_replay111 (9) and test_replay110 (9) pass; 13 of 13 mutations killed.
