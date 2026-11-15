# C1 CONSENSUS — pp-selectid audit 20261115_1418 (ruling 114's x-bf-tunnel-instance replay, tests/package/replay114.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1) and glm-5.3-flash (P1_OR_WORSE: 1). Both raise a P1, so they agree on the
count and Grok was not asked. Cycle 1: $0.0062 vendor-reported. No paid call of the driver has been made.

THE TWO P1s:
1. qwen [P1] "`usage` may be None if backend.complete returns None for it". replay111.FormatBackend.complete always
   returns a dict (tests/package/replay111.py:84-86, UNCHANGED), so it cannot happen today; GUARDED anyway
   (`usage or {}`), as a defence that costs nothing.
2. glm [P1] F1 "pick() compares whole dicts (`r not in first`), so two rows with the same content collapse; distinct
   records are not guaranteed". FIXED: the rows are de-duplicated BY RECORD PATH first (one row a record), and the
   rest is taken by record path, never by dict equality. The test now feeds a record twice and still gets 30 distinct
   records. On the real file the pick is unchanged: 30 distinct records, the five named first (7, 122, 171, 497, 1564).

THE P2s ACTED ON:
3. glm F18 "a call retried by providers._with_backoff (429 / 5xx) keeps only the LAST attempt's headers; an earlier
   attempt's instance header is exactly the evidence probed". FIXED: Capture keeps every attempt's status and headers
   in order ("attempts"); the row's top level is the last. New test: a 429 (x-bf-instance vllm-3) then a 200
   (pinga282): both kept. The report counts retried calls.
4. glm F10 "header names compared case-sensitively". FIXED: names are lowercased at capture (headers_of), a repeated
   header's values joined in order, so the differing-headers count compares like with like.
5. glm F10b "the report names the x-bf headers but not their VALUES (the instance names)". FIXED: the report lists
   every x-bf header with its value and count, per leg, over every attempt.
6. glm F3 "a 200 whose body is not JSON loses everything". FIXED: the first 500 characters of such a body are kept
   (diagnosis only). (The gateway's body is JSON; it is the content inside it that comes back unclosed.)
7. qwen "a corrupted spend ledger reads as $0 and lets calls past the cap". FIXED: a ledger that exists but cannot be
   read stops the run (RuntimeError) before any call; no ledger yet is $0. New test: no call is made.
8. qwen "an unreadable record file crashes the run". FIXED: an error row for each leg, no call.
9. qwen "shape_of on a non-string". GUARDED: str(text or "").

THE OTHERS:
10. glm F2 "the ledger is read-modify-write with no lock; the check is before the call and the cost after, so the last
    call may pass the stop". The driver is single-threaded by design (one call at a time); the stop is $0.14 against
    the order's $0.15 cap, and a call is ~$0.0003 (replay111: 96 step-A calls $0.032), so the overshoot is at most one
    call. No change.
11. glm F5 "on a resume, which leg goes first depends on the pick index". The source (replay111's OUT_OF_CONTRACT.jsonl)
    is a committed proof file; the pick is deterministic over it. No change.
12. glm F11 "`usage.get("out")` is dead on the raw path": the token count reads the raw response's completion_tokens
    first and the backend's own figure only as a fallback (two sources, both kept). No change.
13. glm F6 / F7 / F8 / F9 / F12-F17 (P3): noted. The x-bf header is added on top of providers' headers on purpose (the
    "without" leg's test asserts providers never sends it); a row's keys cannot collide with Capture's (fixed names);
    the docstring's "$0.14 of the order's $0.15" is as intended.

TESTS: 6 offline (was 4): + every attempt of a retried call, + the unreadable ledger stops before any call; the pick
with a record given twice. All pass with the network blocked. tests/package/test_hook115.py (ruling 115 (3)'s driver,
a separate file in the same scratch copy) is not part of this audit.
