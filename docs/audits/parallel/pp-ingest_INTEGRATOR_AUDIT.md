# pp-ingest — INTEGRATOR MERGE AUDIT (pipeline_pp_dod), cycle 1, 2026-11-12 05:02 ET

Branch pp-ingest at 753dec1d audited before merge (pipeline/ingest/*, tools/*, REQUESTS, BIBLE_ADDITIONS; record:
/home/ultron/protocol_pulse/docs/audits/pulse-sentence-law/merge_pp-ingest/cycle1/FRONTIER_anthropic.md; the gpt-6.1-sol
leg failed: OpenAI HTTP 429 credit_balance_exhausted). NOT MERGED until these BLOCKING findings are answered:

- B1 (law L-x: the 90 % tripwire NOTIFIES, never halts) providers.py Router.available: 'if st != "ok": return False,
  f"heimdall spend {st}"' takes the Heimdall leg out at 90 % for good (spend.py: the 90 % state never clears) and also
  when the meter is merely 'unmeasured' (stale or /credits failed). Notify (STATE line 'HEIMDALL SPEND AT 90%'), keep the
  leg, fall back only on a real failure.
- B2 service.py MINE_MAX_TRIES 8 x MINE_RETRY_S 600: an outage of ~80 min (or B1 plus the daily budget caps on the other
  back-ends, which only SKIP) moves a video to MINED_PARTIAL with next_at = +10**9 and coverage.py counts it as mined:
  permanent, silent loss ('nothing is dropped' is false). A skip is not a failure; an exhausted chain must stay
  retryable and be reported, never counted as mined.
- B3 (law L-r) the GPU0 'lease' is an environment string (ab.py PP_INGEST_GPU0_LEASE_HELD) and pipeline/gpu0.py is never
  imported. On merge into main this is closed by main's L-r (4867a74a): story_semantics.LocalLLM._post now calls
  gpu0.require() and swap_to on every request, so the local back-end loads nothing without the real lease. Drop the
  env-string check (it would only give a false sense of custody) and stop the cached LocalLLM when a cycle ends.
- B4 watch.py RATE_LIMIT_MARKS contains 'Sign in to confirm you', a prefix of fetch.py's age-gate mark 'Sign in to
  confirm your age': one age-gated video trips the global YouTube breaker, is requeued forever, and YouTubeGate.calm()
  is never called, so every later trip pauses 60 min. Match the age gate first (terminal 'unavailable'), and calm the
  breaker on success.
Not blocking items are in the record above.
