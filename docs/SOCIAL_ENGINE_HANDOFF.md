# PROTOCOL PULSE — SOCIAL ENGINE REBUILD HANDOFF (v2)
## For the next Claude agent (+ ChatGPT as editorial co-pilot)
## Date: 2026-08-27 (rev 2, evening) | Status: discovery + CLAIM AUDITING + writer proven; EXTERNAL VERIFICATION INCOMPLETE; posting paused
## Supersedes the morning handoff. Sections 3, 4, 6 materially changed.

---

## 0. ONE-PARAGRAPH SUMMARY

We rebuilt the dead tweet machine into `story_engine.py`: broad discovery -> domain-fit -> claim audit -> tiered permission -> multi-register writing -> NO_POST when nothing works. It is live end to end. Then an adversarial side quest (the Trump/USD1 "toll booth" thread) showed that what the morning handoff called the "adversarial verifier" is a **claim auditor**: it decomposes claims and flags inference/motive/causation well, but it only live-checks BTC price and block height. Every other claim is judged by an LLM against the packet's own text. It passed a false "USD1 crossed $4B on Aug 26" claim as a VERIFIED FACT. **External claim verification is now build priority #1, ahead of widening sources.** `POSTING_PAUSED` stays ON.

---

## 1. HOW TO OPERATE (relay + environment)

Unchanged from v1. Relay via Python urllib, token in JSON body (in account-level instructions). ~90s timeout; long ops `nohup python3 -u ... &` then poll (unbuffered `-u` matters, or the log stays empty until exit). Patches: write locally, `base64 -w0` to a file, decode on Ultron, `py_compile`, commit with `HOTFIX_EXEMPT=1`.

Gotchas added today:
- `pgrep -f "<pattern>"` inside a relay cmd matches the relay's own bash and reports RUNNING forever. Poll a saved PID or use `pgrep -x`.
- `data/sovereign_context/history.jsonl` is 173MB and is now gitignored + untracked. It had silently blocked every push since a919dac2; the morning handoff's "all pushed" was false. Never `git add -A` in this repo.
- OpenAI billing live; gpt-4o uses `max_tokens`, gpt-5.x uses `max_completion_tokens`.

---

## 2. KEY FILES

| File | Role | State |
|------|------|-------|
| `services/story_engine.py` | discovery -> audit pipeline | working |
| `services/writer_test.py` | writer harness, RENDER ONLY | working |
| `services/tweet_machine.py` | old writer; reuse persona/dedup/Buffer | PAUSED since 2026-07-17 |
| `data/intelligence/candidate_stories.json` | ranked output (dict: generated_at, total_harvested, stories[]) | per run |
| `data/intelligence/writer_test_output.json` | tweet variants | per run |
| `data/intelligence/rejected_claims.jsonl` | rejected-claim dataset | append-only |
| `data/intelligence/regression_fixtures/trump_usd1_toll_booth_thread.{json,txt}` | **regression test for external verification** | NEW |
| `data/tweet_study/TWEET_VOICE_STUDY.md` | voice study, 1943 tweets | reference |
| `data/POSTING_PAUSED` | kill switch | **ON. Leave on.** |

Commits on `consensusprotocol/protocol-pulse-core` main (hashes REWRITTEN today to drop the 173MB file; v1 hashes are invalid):
```
<next>   [STORY ENGINE] no-evidence invariant + claim-auditor docstring + regression fixture
08d932c2 gitignore data/sovereign_context/history.jsonl
ec58c771 [STORY ENGINE] widen sources + timestamp provenance   (was d4be6b6b)
c49301db [STORY ENGINE] GPT tier ladder                          (was 9a38a341)
4f4234aa [STORY ENGINE] domain-fit gate + writer v3              (was a919dac2)
c57f8827 [STORY ENGINE] adversarial verifier (unchanged)
```
Backup tag `pre-lfs-fix-backup` holds the pre-rewrite commits.

---

## 3. ARCHITECTURE AS ACTUALLY BUILT

```
LAYER 1  SENSING
  harvest_rss()  — 39 feeds (was 15). Primary sources added: SEC, ECB, BoE, BoJ, BEA, OCC,
                   Fed speeches, BIS speeches, FSB; plus Bloomberg, Economist, NYT, CNBC,
                   Optech, BitMEX, Protos, Decrypt, Blockstream, Utility Dive, Register,
                   Wired, EFF, Krebs, BBC World, Al Jazeera. All probed live 2026-08-27.
                   Timestamps now calendar.timegm (UTC). The old time.mktime pushed every
                   fresh UTC item ~4h into the future where the 48h gate dropped it.
  harvest_xai()  — 13 themes (was 6). Now requests published_at from Grok; unknown -> 12h-old
                   default (recency 0.5), never "now". Every item carries discovered_ts +
                   timestamp_provenance.

LAYER 1.5  DOMAIN-FIT GATE — unchanged; cap raised 40 -> 60.

LAYER 2  HYBRID SCORING — unchanged.

LAYER 3  CLAIM AUDITOR  (function still named adversarial_verify; docstring corrected)
  WHAT IT DOES:  extract atomic numeric/superlative claims; LLM splits FACT vs INFERENCE;
                 flags motive attribution / unproven causation / stale / single-source;
                 emits do-not-say list; logs rejections.
  WHAT IT DOES NOT DO:  check any claim against the world, except BTC price and block height.
  KNOWN FAILURES (2026-08-27 side quest):
    - passed "USD1 crossed $4B on Aug 26" as VERIFIED FACT (actual: ~$4.05B, down from $4.6B July)
    - flags a person's first-person statement of their own motive as "motive attribution"
    - tier is gated on source DOMAIN string (SOURCE_QUALITY dict), not on claim content:
      identical facts were UNVERIFIED from crowdfundinsider.com and REPORTED_ATTRIBUTED from cnbc.com
    - could return REPORTED_ATTRIBUTED with EMPTY facts and writer_eligible=True  -> FIXED, see below
  TIER LADDER unchanged. New invariant:
    writer_eligible = status in allowed AND usable_claim_count > 0   (no evidence -> no eligibility)

LAYER 3.5  EXTERNAL VERIFIER — NOT BUILT. Spec in Section 6.

LAYER 4  WRITER — unchanged. Registers stay distinct. NO_POST valid.

LAYER 5  tweet_machine.py downstream — built, not wired.
```

---

## 4. TEST RESULTS

Discovery run, same auditor, before vs after today's fixes:

| | v1 baseline | widen only | widen + provenance |
|---|---|---|---|
| raw pool | 97 | 325 | 314 |
| survived 48h gate | 68 | 196 | 182 |
| writer-eligible / top 20 | 9 | 9 | **17** |
| UNVERIFIED | 11 | 11 | **3** |
| x.com in top 20 | ~10 | 10 | 3 |
| VERIFIED_* | 0 | 0 | **0** |

Widening alone changed nothing; the xAI discovery-time bug was flooding the top 20 with recency-1.0 x.com items. VERIFIED_* is still zero because (a) no external checks exist and (b) the same story from 3 outlets counts as 3 stories with srcs=1 (open loop: semantic corroboration).

Side quest (Trump/USD1 thread): editorial conclusion NO_POST. GPT's draft QT failed on a false fresh fact; Claude caught it by out-of-pipeline research; the auditor did not. This is the regression fixture.

---

## 5. BRAND / VOICE — unchanged from v1. No maximalist clichés, no hashtags, no emoji, no motive attribution, BIP-110 peaceful, em dashes OK in tweets (study wins).

Editorial principle added today: **publication freshness is not event freshness.** A restatement, a repost, or a fresh article about an old number does not make a story fresh. When the only new thing is a correction, NO_POST is usually right.

---

## 6. NEXT STEPS (re-prioritised; GPT's call, PBX-relayed)

1. **EXTERNAL CLAIM VERIFICATION (new Layer 3.5)** — build BEFORE anything else.
   Pipeline per atomic claim:
     claim -> claim_type -> preferred verifier -> retrieve -> locate evidence -> compare value/date/context -> status
   Claim types and verifiers to start with:
     - live_market_value (stablecoin supply, BTC/ETH price, gold, DXY, yields): DeFiLlama, mempool, Yahoo GC=F, FRED
     - quoted_statement ("X said Y"): fetch the cited URL; locate the quote; establish ORIGINAL date vs repost date
     - dated_event (charter approved, database deleted, law signed): fetch primary (agency press release / Federal Register / congress.gov); record event date; if >72h old -> STALE for freshness purposes even if true
     - modelled_estimate (Brookings $2.3T): fetch report; capture the range + caveats; tag editorial words ("captive") as not-in-source
   Output per claim: {candidate_value, observed_value, observed_at, source_url, result: VERIFIED|STALE|CONTRADICTED|UNVERIFIED}
   Source domain quality becomes a prior, not the gate.
   ACCEPTANCE: rerun `regression_fixtures/trump_usd1_toll_booth_thread` with NO out-of-pipeline research.
   The machine must reach NO_POST and match `expected_claim_results` in the fixture JSON.
2. Semantic corroboration (entity + event-type + date fingerprint) so one wire story from 3 outlets = 1 story, 3 corroborations. Likely the thing that unlocks VERIFIED_SECONDARY.
3. Fix the motive-attribution false positive (first-person statements are quotes).
4. Debug dump of the 60 post-fit items: check whether SEC/ECB/BEA press releases die at domain-fit or in soft scoring (none reached the top 20).
5. Tune registers (deadpan under-fires).
6. Widen sources further (was #1; demoted).
7. presentation_strategy / image layer (parked).
8. Wire to tweet_machine.py; blind-test models.
9. THEN lift POSTING_PAUSED after PBX approves a human-reviewed batch. Never before.

---

## 7. RULES OF ENGAGEMENT — v1 rules stand. Added today:

- **Attack the appealing framing.** The side quest worked because the draft was treated as a suspect, not a product.
- **"Verifier" is a reserved word.** Do not call a component a verifier unless it fetches evidence from outside the packet.
- **Claim nothing is pushed until `git status -sb` shows `main...origin/main` with no ahead count.**
- The morning handoff overstated: "discovery + verification + writer PROVEN" -> "discovery + claim auditing + writer proven; external verification incomplete."

---

## POST-CALIBRATION ROADMAP (GPT spec, PBX-relayed 2026-09-01 — DO NOT START before 20 decisions)

Sequence is fixed. Nothing below begins until the calibration batch is graded and analyzed.

1. **Calibration batch (NOW, PBX only):** grade 20-30 candidates at /admin/review. STORY and COPY
   separately, POST/EDIT/KILL, kill reasons. Claude fixes only outright bugs revealed by the batch.
   Known already: story-age rollup uses oldest receipt date, not the current event (MAS case);
   NO_POST on 🔥 stories = writer too timid; quip-bolting = TRY_HARD; wordy edge notes.
   After 20 decisions: export review_decisions.jsonl + machine drafts to GPT for the final writer spec.
2. **Final writer spec:** GPT derives it from the decisions. Lock registers (likely cold_forensic /
   native_deadpan / investigative / maybe FLASH ultra-short). Freeze the voice prompt. No further style iteration.
3. **Presentation selection:** TEXT_ONLY / QUOTE_POST / RECEIPT_SCREENSHOT / ORIGINAL_CHART / TWO_IMAGE / NO_POST.
   Receipt screenshots + quote posts first, charts second. Never scraped/generic images or BTC-logo decoration.
4. **Human-approved POST -> Buffer:** wire the review queue's POST action through tweet_machine's existing
   Buffer GraphQL path. Human-approved posting != autonomous posting; POSTING_PAUSED continues to block
   unattended publication. This is the moment the channel is operational again.
5. **Supervised run 1-2 weeks:** collect approval rates, edit distance, kill reasons, topic/register/
   presentation, and X performance (impressions, replies, reposts, bookmarks, follows where accessible).
6. **Autonomy criteria (all required):** regression suite clean; zero unsupported claims in reviewed batch;
   STORY approval >=~60%; COPY approval-or-light-edit >=~60%; no recurring stale-event failures; NO_POST
   proven; Buffer path proven; kill switch tested. Then autonomous posting conservatively,
   VERIFIED_PRIMARY/SECONDARY only at first.

### ATTENTION ENGINE (separate lane, build after calibration)
`attention_engine.py`, standalone from story_engine.py. Job: find posts already proving they are attention
magnets that Protocol Pulse can add something to — not "important stories."
- Monitor curated handle lists via xAI X Search (allowlists, date windows, video/image understanding):
  Bitcoin-native, political-economy/libertarian, finance/tech/viral culture.
- Every 10-15 min, posts <~3h old, especially clips. Score: engagement velocity (per-minute relative to
  account size), cross-account spread, comment opportunity, brand fit (money/power/freedom/institutions/
  culture/absurdity/tech), saturation (obvious joke already made 50x), context risk (misleading edit,
  ragebait, provenance).
- Output: original post, velocity, why spreading, 3 QT options, QT/SKIP. Human-reviewed quote posts ONLY.
  Never auto-post. SKIP is valid.
- Comment writer prefers: undercut / compress the implication / add ONE verified missing fact.
  Never summarize the clip.
- Keep the lane analytically separate from intelligence output for performance comparison.
- Politics widening = political economy + institutional absurdity (spending, taxation, surveillance,
  banking, property rights, censorship, war financing, capital controls, regulation, central banks,
  prediction markets, receipts-backed corruption, bureaucratic absurdity). Reward economic/freedom/tech
  relevance; penalize team-sport framing and ragebait. "That's a weird incentive," never "our side destroys."
- Doubles as audience research: track what Bitcoin-native audiences over-index on outside Bitcoin; feed
  migration signals back into discovery.

### MEMORY / PURCHASING-POWER lane (inside attention engine, not a new subsystem)
NOSTALGIA / PURCHASING_POWER discovery category. Nostalgia is the hook; the verified economic contrast is
the story. Pipeline: historical clip/image -> identify date/place/product/price -> verify provenance ->
extract nominal prices/wages -> inflation-adjust (CPI AND hours-of-median-labor) -> compare present ->
editorial score -> QT/original/SKIP. Mandatory historical-price verification before any economic claim.
The machine must be allowed to find the OPPOSITE (things that got cheaper); no manufactured debasement
stories. Raw material: grocery/menu/dealership/catalog/home-listing/gas-sign/wage/tuition/ticket footage.

### Target output mix (loose, not quotas)
~50% INTELLIGENCE / ~25-30% ATTENTION / ~20-25% POWER, with MEMORY inside ATTENTION.
Bitcoin appears naturally across lanes (15-35% by week), no silo.
