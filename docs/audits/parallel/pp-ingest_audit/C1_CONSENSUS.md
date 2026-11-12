# pp-ingest audit, cycle 1: consensus and dispositions (written by the session, 2026-11-12 ~04:15 ET)

Driver: tests/ingest/xllm_audit.py (the repo tool's DEFAULT_REVIEW_TASK and cycle-2 prompt, imported read-only; the
tool's own run_audit writes into the main tree and reads key names the env file does not define). Package: every new
file of the diff, line-numbered, plus the design doc and the test inventory.

Reviewers and what they saw:
- gpt-4o (OpenAI), grok-4.20-0309-reasoning (xAI), gemini-3.1-pro-preview (Google): the 08:34 UTC package.
- qwen/qwen3.8-27b (Heimdall): the 08:47 UTC package (c1/PACKAGE.md), identical except the runtime base-URL override
  (providers.Overrides, service wiring, config path) and the Gemini schema change, both made while cycle 1 ran.
- deepseek/deepseek-v4.1-flash (Heimdall): EMPTY content twice (effort low, then none; finish_reason length on a
  64k-token package): no review (the INGEST-FAIL-04 class; recorded, not counted).
- Gemini's reply was cut off after section 6 (its thinking used the 16,000-token budget, and the Gemini adapter forced
  JSON for a free-text review): both causes fixed for cycle 2 (adapter: JSON only with a schema; driver floor 48,000).

Rule (CROSS_LLM_AUDIT_LAW / PIPELINE_LAWS): implement consensus only (the same file, function and root cause from two
reviewers); a single reviewer's finding is implemented only when verified against the code or by measurement, and the
evidence is recorded; everything else is refuted with evidence.

## Consensus (>= 2 reviewers, same root cause)
None. No law violation was reported by any reviewer (law-compliance verdicts: gpt-4o COMPLIANT on all, grok
"COMPLIANT ... no violations", gemini "COMPLIANT", qwen COMPLIANT on all).

## Single-reviewer findings verified and IMPLEMENTED
| # | reviewer | finding | verification | fix |
|---|---|---|---|---|
| V1 | gemini | GeminiBackend ignores the role's schema | code: `complete()` never passed `schema` | providers.GeminiBackend: `response_mime_type` + `response_json_schema` when a schema is given, plain text otherwise; live: a mining window valid (3 moments, 30.5 s) |
| V2 | grok (P0) | the adapter reads and parses the whole ledger on every call | measured: 16-25 s on a 100k-line ledger (263 MB; live lines average 2.6 KB) | ledger.offset_before (bisection on mined.at) + read(from_time): every returnable line was mined at or after min(since, now - 72 h); one day of margin for interleaved videos. Test: tests/ingest/test_ledger_coverage.py `test_the_bounded_read_returns_exactly_what_a_full_read_returns` (equal to the contract's rule over every line; reads < 1/3 of the file) |

## REFUTED with evidence
| reviewer | finding | evidence |
|---|---|---|
| gemini | "AnthropicBackend passes output_config, which does not exist in the Anthropic API (400 on every call)" | the installed SDK's `Messages.create` signature has `output_config` (anthropic 0.84.0); the Claude API reference documents `output_config.format`; live: 284 valid Anthropic mining calls in the 08:36-08:43 UTC outage drill and the 03:10 ET single-window proof |
| grok | "Router._try can leak the global semaphore on an unexpected exception (lines 611 vs 616)" | `with self.sems[bid], self.gsem:` releases each semaphore its `__enter__` acquired whatever the block raises; `BoundedSemaphore.__enter__` cannot fail after acquiring; every client exception inside is converted to BackendError in the block |
| grok (P1) | "mine_video reads meta.json / the transcript while holding a video slot; a slow disk blocks a worker" | local NVMe; both reads are small; an unreadable or corrupt meta raises inside the try and the video goes to mine_waiting (service.mine_video) |
| grok | "text fingerprint uses the first 400 tokens: an edited re-upload is missed" | true as a limit, not a defect against the order ("same title+duration or audio fingerprint later"); recorded in the design (section 3); a re-upload with an edited opening that also changes its title or duration needs the later audio fingerprint |
| grok (P3) | "Bearer scheme hard-coded" | every configured OpenAI-compatible back-end uses Bearer; no back-end needs another (YAGNI; the config can add a field when one does) |
| grok | "no explicit transaction / rollback in Queue" | autocommit per statement; `claim` is one atomic UPDATE; `set_state` is one UPDATE plus an events INSERT (a missing event row after a crash loses an audit line, never a state) |
| qwen (P1) | "a crash between ledger.append and set_state re-appends the same moments" | harmless by the contract: readers de-duplicate by moment_id, the latest line wins (pp-selectid contract v0; ledger.best_unused_moments; test `test_the_latest_line_wins_and_order_is_by_rank`); re-mining costs nothing (validated replies cached) |
| gpt-4o (P0) | "improve retry logic for API calls" (no file:line, no defect named) | the router already retries transport errors with backoff (3), honours Retry-After, opens a breaker, falls back by chain; nothing specific to verify |
| gpt-4o / qwen / grok | Prometheus metrics, a health endpoint, a SQLite mirror of the ledger, embedding-based duplicates | improvements beyond the order's scope; not defects |

## Found by the session after cycle 1 started (not reviewer findings; in cycle 2's package)
- The outage drill showed a back-end's runtime override is read only when that back-end is next called; while its
  breaker is open the restored URL is seen at the half-open probe (08:42:17 for an 08:38:31 restore). Behaviour is
  correct (recovery at the probe); recorded in the design.
