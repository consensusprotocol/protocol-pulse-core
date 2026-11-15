# C2 consensus (FINAL), audit 20261115_0054 (written by the builder; qwen3.8-27b and glm-5.3-flash, Heimdall)

Both P1_OR_WORSE 0 on the fixed diff; Grok not asked (they agree). No third cycle (no real defect). Both accept C1's
answers: only a cut reply (IncompleteRead) and a dropped connection (BadStatusLine) are retried; any other
HTTPException is Unavailable at once; the failover test pins the reservation's single release.
P2s, no change:
- glm, "the retry assertion is weaker than it looks": the test also asserts the RETURNED value is the second try's
  answer; C1 and C5 die on it.
- glm, replay110's clause hard-codes "error": a socket TimeoutError is transport inside _with_backoff (Unavailable ->
  ProviderError); only the Router's own cut ("abandoned at the deadline") is a ruling-100 timeout.
- qwen, "a silent expansion for every other HTTPException": intended, and in the docstring (Unavailable at once,
  "(final)").
- qwen, Cut implements read() only: _http_json calls urlopen(...).read() and nothing else.
Audit cost $0.0235 vendor-reported (cap $1.00; Grok asked once, in C1).
