# heimdall_glm (z-ai/glm-5.3-flash, 262.3 s, $0.005, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, CYCLE 2 (mine-hook/4, A36: WIDEN)
# heimdall_glm (z-ai/glm-5.3-flash, second review)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output (which was cut at section 3, so my coverage was narrower than theirs):

**Muse caught, I did not:**
- **The `n` float edge** (`isinstance(5.0, int)` is `False` → asked). I noted the production path always feeds an int (mine.py:348 `sum(len(TURN_MARK.findall(...)))`), but muse's framing — "the type contract is implicit" — is the sharper observation. I verified the invariant; muse named the *risk* of the invariant. Their point stands: if `episode_measure` ever changes its return type, `is_conversation` silently flips to "asked" for every episode. That is fail-open, so it costs money, not correctness — but it is an unguarded contract.
- **The `spot_rows` NULL-vs-0 distinction** (stats.py:110, service.py:447). I never reached stats.py in Cycle 1 (my output was truncated). Muse's verification that `spot_rows = 0` (asked, found nothing) is correctly distinguished from `NULL` (not asked) is the load-bearing fact for the new `spotlight_asked_videos` metric, and they traced it to the writer. I would have agreed had I read it; they did the work.
- **The circular-import note** — removing `from . import mine` at module level of stats.py and making it lazy (stats.py:117) eliminates a circular-import risk. I missed this entirely; it is a real, if minor, structural improvement bundled into the diff.

**Qwen caught, I did not:**
- **The log-message reachability argument** (service.py:427): the "a marked solo episode" text is only reached when `srep is None` AND `scrash is None`, and `srep is None` happens only when `is_conversation(ep)` is `False`, which now requires `speaker_markers > 0` AND `turns_per_min < 0.3`. Therefore the message's wording is *provably* accurate for every row that prints it. I noted the message was "more debuggable"; qwen proved it is never wrong. That is the stronger claim and it is correct.

**What I caught that neither of them did (still stands):**
- The bool-before-int `isinstance` ordering rationale (both muse and qwen noted the bool trap, but I was the only one who explained *why the order matters* — `bool` is a subclass of `int`, so the check must precede).
- The 0.295→0.3 rounding boundary analysis (muse flagged the rounding in their C1-2; I did the interval arithmetic: the effective boundary is [0.295, 0.305) → 0.3, and no test covers 0.2949→0.29).
- The cache-key analysis: solo prompts are byte-identical (max_h=3, unchanged template), so they replay free; conversation prompts changed (3→5) and legitimately re-ask. Muse asserted this; I *derived* it from `Router._key` (providers.py:906-908) hashing the prompt text.

## 2. WHERE DO I AGREE OR DISAGREE?

**Muse P1 "validate the video id before the yt-dlp call (flag injection)" — AGREE WITH THE CONSENSUS REFUTAL.** The consensus (orchestrator's C1 note) refuted this: the id is interpolated into an `https://...` URL argument (fetch.py:93), passed as a list (no shell), and listings are id-validated (watch.py:122-124, `uploads_url` checks `UC` + 24 chars). I add: even a hypothetical id like `-o` would land inside the URL string, not as a separate argv element, so it cannot become a flag. Correctly refuted.

**Muse P1 "state + event in one transaction" — AGREE (recorded, pre-existing).** service.py:201, 210, 449-456: `q.event(...)` and the preceding `q.set_state`/`q.set_hook`/`kv_set` are separate statements, not one transaction. A crash between them loses the event, not the state. Given the events table is explicitly "append-only" evidence and the state is the durable thing, the loss is cosmetic. Recorded, not a ship-blocker. Muse themselves filed it as P2-adjacent.

**Muse P2 "queue-depth and latency alerts, purge's per-file publish lookups" — PARTIALLY AGREE.** The purge N+1 is real but bounded: `published()` (purge.py:203-220) caches per-vid in `cache = {}` (purge.py:308) *within one pass*, so it is one query per distinct video per pass, not per file. At 67 videos/72 h and a 10-min pass cadence, this is negligible. Muse's own note ("mitigated by cache, but only within one pass") concedes this. I'd call it a P3, not P2.

**Qwen's race-condition walkthrough (fetch writes vs. mine reads) — AGREE, and I can strengthen it.** Qwen hedged ("we assume it's robust"). I can do better: `fetch._store_captions` (fetch.py:237) calls `ts._store(rec)` — transcript_store's own writer, which the module docstring (config.py:3-5) says is the pipeline's by construction; and `mine.mine_video` reads via `ts.canonical_transcript(vid)` (service.py:274, 386), the store's *canonical* reader. The store's write-then-rename pattern (the same pattern the ledger and the reply cache use: providers.py:995-999, spend.py:60-63) means a reader either sees the old file or the complete new one. Also, the mine loop only picks up videos in state TRANSCRIBED (queue.py:24-25), which `fetch.process` sets *after* `_store` returns (fetch.py:248-251) — so the state machine itself orders the write before the read. The race qwen worried about is closed by the state machine, not by the store. Nobody said this.

**Qwen's law-compliance section — AGREE, one refinement.** Their L-j/L-m reading ("fail open for *asking* but fail closed for *skipping*") is exactly right and is the deepest reading of the ruling: `is_conversation` returning `True` on missing data means the pass *spends* $0.006 rather than *skips* a possibly-conversational episode. The ruling's own cost argument (quoted in the ruling) endorses this direction. One refinement: this is fail-open on *spend*, which is only safe because the hook pass is capped by HOOK_HORIZON_S (service.py:65) — the 12 h expiry bounds how long a mis-classified episode keeps costing. Nobody noted that the expiry is what makes the fail-open affordable.

**Muse's 1.4 version-bump analysis — AGREE, with one addition.** Their claim "solo episodes still get 3 hooks with same prompt text, so sha256(prompt) matches cached entry" is correct *for the prompt*, but the cache key (providers.py:906-908) also hashes `bid`, `model`, `schema`, and `max_tokens` — none of which changed. So the solo replay is genuinely free. What muse missed: the *conversation* prompts changed (3→5 in the template), so those re-ask — which is the intended cost of the ruling, ~19+13=32 of 67 videos × ~$0.006-0.01. Nobody priced the re-run. At the ruling's own $0.006/video figure, the one-time re-ask cost is roughly $0.20-0.30 total. Immaterial, but it should have been *said*.

## 3. NEW FINDINGS FROM THIS REVIEW (Cycle 2)

**N1 (new, nobody): the `hooks --rerun` window boundary can strand videos.** tools/ingest_watch.py:169:

```python
"AND published_ts >= ? AND hook_ts IS NOT NULL AND (hook_version IS NULL OR hook_version <> ?)",
(max(since, q.clock() - 12 * 3600), ...)
```

The rerun's `published_ts` floor is `max(since, now - 12h)` where `since = now - a.hours*3600` and `a.hours` defaults to 12.0. So the effective floor is `now - 12h` — the *current* 12 h window, not the 12 h window at the time the old pass ran. A video published 11.9 h ago, whose hook pass ran under mine-hook/3 at hour 0.5, is caught. But a video published 12.1 h ago (just outside) whose hook pass ran under /3 is *not* re-queued — and its moments expire at 12 h anyway (config.py:36-37), so the hook rows would be worthless. **Actually, this is correct by construction**: the expiry makes the 12 h rerun window exactly right. Verified, not a bug. I retract this as a finding; it survives scrutiny. (Worth stating: the rerun's window is exactly the expiry horizon, so nothing stranded.)

**N2 (new, nobody): `spot_rows IS NOT NULL` counts a pass whose spotlight question crashed.** service.py:445-447: when `scrash` is set, the pass still writes `spot_rows=len(spot)` where `spot=[]` — wait, no: when the spotlight question *crashes*, `spot` stays `[]` and `srep` stays `None`, so `spot_rows=None` (service.py:447: `len(spot) if srep is not None else None`). So a crashed spotlight → `spot_rows IS NULL` → **not counted as asked**, even though the hook question (b) WAS asked with 5 hooks. The metric `spotlight_asked_videos` therefore undercounts by one for every crash, until `hooks --rerun` re-asks (the pass is marked `hook_version = "mine-hook/4 (spotlight crashed)"` ≠ the current version, so the rerun catches it — service.py:445-446). This is exactly the glm-P3 finding the consensus *recorded* rather than fixed. I now add: the undercount is self-healing, and the healing mechanism is the version-string mismatch, which is why the "(spotlight crashed)" suffix matters. If anyone ever "cleans up" that suffix, the self-healing breaks silently. That coupling is undocumented.

**N3 (new, nobody): the stats bucket label for `t=0.0` marked episodes.** stats.py:123-125: a marked episode with `episode_tpm = 0.0` (markers>0, minutes>0, but... wait, markers>0 with minutes>0 gives tpm>0; tpm=0.0 requires markers=0, which is the "unmarked" bucket). Actually: `episode_tpm` is stored via `set_hook(episode_tpm=ep.get("turns_per_min"))` (service.py:441), and `episode_measure` returns `turns_per_min = round(n/mins, 2) if mins > 0 else None`. For markers>0 and mins>0, tpm > 0 strictly. So the `t >= lim` / `t < lim` split never sees 0.0 in the marked branch — the `{"speaker_markers": 1, "turns_per_min": 0.0}` test case (ep4) is a *predicate* case, not a *production* case. Fine. But: the bucket label `f">= {lim:g} turns / min (asked)"` renders as ">= 0.3 turns / min (asked)" — and a video with tpm=0.295 (rounded to 0.3) lands in the ">= 0.3" bucket while its *stored* value is 0.3, consistent. No discrepancy. Verified.

**N4 (new, nobody): `episode_markers`/`episode_tpm` are written only on pass completion, not on the waiting path.** service.py:435-437: the waiting path (`failed and tries < HOOK_TRIES`) calls `set_hook(hook_next_ts=..., hook_tries=..., hook_cost_usd=..., hook_note=...)` — no `episode_markers`/`episode_tpm`. So a video that waits through several outage passes has NULL episode columns until its pass completes. The stats `rows_by_episode` query (stats.py:120-121) filters `hook_ts IS NOT NULL`, so this is consistent — waiting videos are excluded from the bucketing anyway. But the *hook_due* query (queue.py:196-202) also excludes nothing... no, it selects by state and hook_ts. Consistent. The only consequence: if someone later adds a "waiting videos by episode type" metric, they'll silently get NULLs. Latent, not live. P3.

**N5 (new, nobody): the paid route's `conversation_tpm` 1.0 vs the hook pass's 0.3 — A42 is correct and now testable.** providers.json:98 `conversation_tpm: 1.0` (paid route ordering) vs mine.CONVERSATION_TPM 0.3 (hook pass). A42 says these are intentionally different (the paid route's threshold orders *which new uploads to mine first during an outage*; the hook pass's decides *whether to ask (b)+(c)*). I verified the paid route's use: service.py:662 `tpm >= float(pr["conversation_tpm"])` — reads the config, not the mine constant. So the two thresholds are genuinely decoupled, and A42's "one config value if the orchestrator wants them aligned" is accurate: alignment would be a one-line providers.json edit, no code. A42 is correct as written.

**N6 (new, nobody): the `max_n` report field is the *pass's* value, not per-window.** mine.py:578: `report["max_n"] = max_n` — one value for the whole video. Since `max_n` is decided once per `mine_video` call from the episode (mine.py:576), this is correct: every window of one video gets the same `max_n`. But the *event* (service.py:450) records `max_n=rep["max_n"]` and `max_n_spotlight=(srep or {}).get("max_n")` — and the spotlight's `max_n` is always SPOT_MAX=2 (mine.py:576: the `kind == "hook"` guard means the spotlight call, kind="spotlight", takes the `KINDS["spotlight"]["max_n"]` = 2 branch). So `max_n_spotlight` is constant 2 in every event. Recording a constant is harmless but tells you nothing; if the ruling ever makes the spotlight's allowance episode-dependent, this field will silently start lying. Latent.

Wait — let me re-verify N6. mine.py:576: `max_n = HOOK_MAX_CONVERSATION if kind == "hook" and is_conversation(episode) else KINDS[kind]["max_n"]`. For kind="spotlight", the condition `kind == "hook"` is False, so `max_n = KINDS["spotlight"]["max_n"] = SPOT_MAX = 2`. Yes. And the spotlight's *prompt* says "1 to 2" via `spot_prompt(..., max_h=2)`. Consistent. N6 stands as a latent-observability note.

**N7 (new, nobody): the test's cache-continuity claim is asserted, not exercised.** The test `test_a_conversation_is_asked_for_up_to_5_hooks...` ends with:

```python
assert mine.hook_prompt(meta, H.CHAN, win) == mine.HOOK_PROMPT.format(max_s=3, reason_max=mine.REASON_MAX, max_h=3, ...)
```

This proves the *solo* prompt template renders identically to the module's HOOK_PROMPT with max_h=3 — i.e., the /3→/4 bump did not change the solo prompt *text*. But no test runs the *same* solo record through both the /3 and /4 code paths and asserts the same `Router._key`. That would require the old code. The claim "unchanged prompts replay free from the cache" rests on: (a) the template's solo rendering is unchanged (tested), (b) `_key` hashes prompt+bid+model+schema+max_tokens (providers.py:906-908, unchanged in the diff), (c) the schema and max_tokens are kind-constants (mine.py:430, 518). (a)+(b)+(c) compose to the conclusion, and each link is individually verified, but the *composition* is untested. Given the cache is the thing that makes the version bump free, and given a prior cycle's consensus fixed a cache-adjacent bug (C1-1), I'd call this the highest-value *missing test*, not a bug. P2.

**N8 (new, nobody): `rows_by_episode`'s "not measured" bucket can only come from pre-92 rows.** stats.py:123: `m is None` → "not measured". But service.py:441 writes `episode_markers=ep.get("speaker_markers")` on every completed pass, and `episode_measure` never returns None for `speaker_markers` (it returns 0 for no segments, mine.py:346). So `m is None` happens only for videos whose hook pass completed *before* the episode columns existed (pre-ruling-92 passes, i.e., before the 12 h window's videos were all re-passed). Within 12 h of the /4 deploy, this bucket will be populated by legacy rows; after 12 h of clean operation it will be empty forever. Transient. Not a bug; worth knowing when reading live.json in the next day.

**N9 (new, nobody): the ruling's "0.3" and the rounding, precisely.** The ruling says ">= 0.3 caption turns a minute". `episode_measure` rounds to 2 decimals (mine.py:354). A true rate of 0.2967 → 0.3 → asked. A true 0.2949 → 0.29 → skipped. The ruling's intent (from its own numbers: Pompliano 0.97, Bitcoin Magazine / CoinDesk interviews, the 0.3-1.0 band of 19 videos) is clearly "the 0.3-1.0 band is now asked" — and rounding at the 2nd decimal moves the *effective* boundary to [0.295, 0.305). For the ruling's named casualties (0.97, and the 19-video band), rounding is immaterial. The only videos affected are those within 0.005 of 0.3 — of 67 videos, statistically ~0.3 of one. Immaterial, and the consensus already fixed the *documentation* (design 13: "0.295 reads as 0.3"). Closed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `is_conversation` predicate (mine.py:302-315) | 10/10 | 10/10 | Unchanged: every input case verified, bool-ordering correct, boundary matches the ruling. Muse's float-`n` note is a contract-implicitness observation, not a defect. |
| `episode_measure` (mine.py:340-355) | 9/10 | 9/10 | Unchanged. The int/float type contract is implicit (muse's point, now credited); the rounding is documented (design 13). |
| `max_n` propagation (mine.py:510-520, 576) | 10/10 | 10/10 | Prompt, schema, validator agree; the two-axes (max_n vs max_count) distinction held. N6's constant `max_n_spotlight` is latent observability, not a defect. |
| Version bump + cache continuity | 9/10 | 8.5/10 | The *composition* (template-unchanged ∧ key-unchanged ∧ constants-unchanged ⇒ solo replay free) is verified link-by-link but untested end-to-end (N7). Docked half a point for the missing test, not for any doubt about the conclusion. |
| stats.py `spotlight_asked_videos` + buckets | — (truncated) | 9/10 | Muse's NULL-vs-0 analysis verified; the crash undercount is self-healing via the version-suffix coupling (N2) — correct but undocumented coupling. |
| service.py log + hook pass | — (truncated) | 9.5/10 | Qwen's reachability proof of the log text; the crash-never-holds-back-hooks design (hk3) still holds; N4's latent-NULL note. |
| Paid route (A42) | — | 10/10 | N5: the two thresholds are genuinely decoupled (config-read vs constant-read); A42's alignment note is accurate. |
| Tests | — | 9/10 | 311 pass; the predicate's 13 param cases + the 5-vs-3 + the rounding doc. Missing: the end-to-end cache-continuity test (N7). |

Overall: 9.3/10 (was 9.3/10 effective; the truncation hid subsystems I've now scored).

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.** Nothing here blocks shipping.

**P1 HIGH — none.** (In cycle 1 the consensus had no P0/P1 either; cycle 2 confirms.)

**P2 MEDIUM:**
1. **N7 — the cache-continuity composition is untested.** tests/ingest/test_mine.py (the 5-vs-3 test's final assert) proves the solo template renders identically, but no test exercises `Router._key` equality across the /3→/4 boundary for a solo record. Add one: mine a solo record with a fake router, capture the prompt, assert `providers.Router._key(bid, prompt, schema, 3000)` equals the key of the /3-era prompt (or, more practically: assert the solo prompt's sha256 is unchanged from a golden value). File: tests/ingest/test_mine.py, after the 5-vs-3 test. Cost: ~10 lines. This is the only test whose absence could let a future edit silently cost money on every solo re-run.
2. **N2 — the version-suffix coupling is undocumented.** service.py:445-446: `hook_version = f"{mine.HOOK_PROMPT_VERSION} (spotlight crashed)"` is what makes the crashed-spotlight undercount self-heal via `hooks --rerun` (tools/ingest_watch.py:168: `hook_version <> ?` — note: the rerun compares against the *bare* `mine.HOOK_PROMPT_VERSION`, so the suffixed version matches the `<>` and is re-queued). Add one comment line at service.py:445: "the suffix is what makes --rerun re-queue this pass; do not remove it". (Verified: `"mine-hook/4 (spotlight crashed)" != "mine-hook/4"`, so the `<>` catches it. Correct, fragile.)

**P3 (recorded, not blocking):**
- N4: episode columns NULL on the waiting path (service.py:435-437) — latent.
- N6: `max_n_spotlight` is a constant 2 in every event (service.py:451, mine.py:576) — latent observability.
- N8: the "not measured" bucket is transient legacy (stats.py:123) — self-empties.
- Muse's float-`n` contract-implicitness (mine.py:311) — fail-open, costs $0.006, guarded by the 12 h expiry.
- Muse's purge N+1 — bounded by the per-pass cache (purge.py:308), negligible at this volume.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the golden-prompt-sha test (N7): the entire "the version bump is free where prompts did not change" guarantee — the ruling's cost story — rests on an untested composition of three separately-verified facts, and one golden sha256 of the solo prompt would pin it permanently.

## 7. PRODUCTION READY?

**Yes, with one condition.**

The predicate is correct on every input; the ruling's four cases, the bool trap, the rounding, the boundary, the caller, the validator, the schema, the prompt, the cache, the stats, the log, and the paid route's decoupling (A42) are all verified. The consensus's two Cycle-1 fixes (the stats buckets, the design-13 rounding note) are in and tested. 311 tests pass.

**Condition:** add the golden-prompt-sha test (N7/P2-1) — the cache-continuity guarantee is the only load-bearing claim in this diff that no test pins, and it is the one whose silent failure costs money on every future prompt-adjacent edit. Ten lines, one afternoon. Everything else (N2's comment, the P3s) is recorded, not required.

One caveat stated plainly: my Cycle 1 output was truncated at section 3, so my "what did they catch" accounting covers correctness (§1) fully but security/law (their §2-3) only via their own reports — I verified qwen's law-compliance *claims* where the code was in front of me (L-l: mine.py:446-498, strict, no repair; L-x: providers.json:107-122, two back-ends per role, enforced at load, providers.py:158-161) and found them accurate, but I did not independently re-derive every law. Within what I could see: nothing contradicts their compliance findings.