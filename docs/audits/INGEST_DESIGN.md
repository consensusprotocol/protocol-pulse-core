# INGEST + FIRST-PASS MINING: design (branch pp-ingest, session pipeline_pp_ingest)

Order: PBX 02:30 ET Nov 12 ("let's just have heimdall constantly scraping all the new vids that go online to make sure
we dont miss any of the most relevant content of the day"), orchestrator note 02:45 ET (law text L-x NO SINGLE MODEL,
ULTRON FIRST). Laws applied: L-e, L-h / L-i (text read as spoken), L-j / L-m (fail closed; nothing measured is never a
pass), L-l (a model reply counts only whole), L-q (moments first), L-r (GPU0: this service uses no GPU), L-u
(exclusions), L-v (speaker / transcript truth; re-uploads), L-w, L-x.

## 1. What it does

A long-running process (tmux `pipeline_pp_ingest_watch`, no cron) that:

1. WATCHES every registry partner / guest channel (`pipeline/channels.json`: enabled, with a channel id: the selector's
   own universe, `transcript_ingest.editorial_channels`), minus `pipeline/optout.json` when that file exists, every
   ~10 minutes.
2. FETCHES captions for each new video into a staging copy of the editorial transcript store, through the store's own
   writer (`pipeline/transcript_store.py`).
3. MINES each new transcript: numbered sentences go to a model behind one provider interface; the model returns ids,
   scores and flags only; replies are validated strictly, never repaired, and every reply is saved.
4. APPENDS mined moments to an append-only moment ledger in the pp.moment/1 contract that pp-selectid published
   (docs/audits/parallel/pp-selectid_STATE.md, "MOMENTS / PACKAGE INPUT CONTRACT v0").
5. REPORTS live numbers and a daily coverage check: of the partner videos published in the last 24 h, which are in the
   ledger, and why each other one is not.

It never uses a GPU (no Whisper, no Ollama, no NVENC): word-level timing stays the pipeline's job at cut time.

## 2. Data layout (all under the store root; default `<worktree>/data/editorial`, gitignored)

```
data/editorial/                          = PP_EDITORIAL_STORE for transcript_store (staging copy, same layout as main)
  transcripts/<video_id>/meta.json       written once, by pipeline.ingest.fetch.meta_record (ensure_meta's keys + 3)
  transcripts/<video_id>/transcript.yt_manual.json | transcript.yt_auto.json   transcript_store._make_record/_store
  transcripts/<video_id>/attempts.jsonl  transcript_store._log_attempt
  state/caption_circuit.json             transcript_store's caption 429 breaker (staging's own)
  moments/moment_ledger.jsonl            the append-only moment ledger (pp.moment/1, one moment per line)
  ingest/queue.sqlite                    durable queue: channels (last-seen ledger), videos (state machine), calls, events
  ingest/replies/<backend>/<aa>/<sha>.json   every validated reply, keyed by sha256(backend, model, prompt, schema)
  ingest/replies_log/<YYYY-MM-DD>.jsonl  EVERY attempt, accepted or not: raw content, verdict, usage, latency, cost
  ingest/live.json                       the live numbers (rewritten every 10 min)
  ingest/coverage/<YYYY-MM-DD>.json/.md  the daily coverage check
```

Guard: the service refuses to start when the store resolves inside `/home/ultron/protocol_pulse` unless
`PP_INGEST_ALLOW_MAIN_STORE=1` (the integrator sets it when wiring this into the main tree). `transcript_store` is
imported only after `PP_EDITORIAL_STORE` is set, and the service checks `transcript_store.STORE_DIR` equals the store
root before any write (fail closed).

## 3. Watching and fetching

Listing, per channel, every ~10 min (600 s, jitter +-60 s), at most 3 yt-dlp processes at once:
- RSS first: `feeds/videos.xml?channel_id=` (conditional headers are sent when a feed returns validators; YouTube's
  return none). RSS answered HTTP 404 for every channel on 2026-11-07 and at 02:45 ET Nov 12, and 200 for all 64 from
  03:26 ET; a one-channel canary is retried every 30 min and RSS is used for all channels only while it answers 200.
  The feeds are a 15-minute cache (`Cache-Control: public, max-age=900`), so discovery takes up to ~25 min after
  publish (INGEST-FAIL-07).
- Fallback: the uploads playlist `playlist?list=UU<id[2:]>` (`--flat-playlist --playlist-end 30`, approximate dates):
  one request lists regular uploads, livestream VODs, live / upcoming streams and Shorts (INGEST-FAIL-02: the /videos
  tab misses streams and Shorts).
- Per-channel backoff on errors (2^n min, max 60 min); a YouTube rate-limit / bot-check answer opens a global yt-dlp
  breaker (10, 20, 40, 60 min).
- Last-seen ledger per channel: last poll, last success, source, ETag / Last-Modified, newest published, errors.

Per new video id (one `yt-dlp -J`, then a state):

| probe says | state | next |
|---|---|---|
| `media_type` short | `short` | recorded, never mined (L-u fairness: never re-cut a partner's own Short) |
| `is_upcoming` | `upcoming_waiting` | re-probe at the scheduled start + 15 min, then every 30 min |
| `is_live` / `post_live` | `live_waiting` | re-probe every 20 min; meta.json is NOT written (INGEST-FAIL-01) |
| VOD, duration > 6 h | `too_long` | recorded with reason (the selector's own ceiling is 3 h: noted in REQUESTS) |
| VOD, no English captions yet | `captions_pending` | re-probe at +10, +20, +40, +80 min, then every 2 h; at publish + 48 h: `no_captions` (needs the pipeline's Whisper; listed by the coverage check) |
| VOD with captions | `transcribed` after `transcript_store.fetch_captions` stores the record | mining |
| private / removed / members-only / age-gated | `unavailable` | recorded with yt-dlp's reason |
| same canonical title + duration within 2 s, or same transcript text fingerprint, as an earlier video | `duplicate` | `duplicate_of` set; not mined (L-v 3: re-uploads are excluded) |
| channel in optout.json | `excluded_optout` | nothing fetched |

Publish time: a regular upload's yt-dlp `timestamp`; a livestream VOD's `release_timestamp` (when it was said;
INGEST-FAIL-03); the source is recorded (`published_at_source`).

Text is stored verbatim (the store never rewrites a record) and READ AS SPOKEN everywhere it is used: sentences,
moment text and prompts go through `eligibility.spoken` = `transcript_store.read_text` (entities decoded, split tokens
joined; laws L-h / L-k).

## 4. Sentence ids and the moment contract

Ids are the contract's, by import, never by copy: `tokens = select_by_id.tokens_from_record(record)`,
`sentences = eligibility.split_sentences(tokens)`, `text = eligibility.spoken(tokens[w0..w1])`,
`moment_id = sha256('video_id|transcript_sha256|w0|w1')[:20]`. Pre-merge the two modules are imported read-only from
the pp-selectid worktree (`PP_SELECTID_PIPELINE`), after merge from `pipeline/`. Every moment carries
`mined.contract_fp`: sha256 of the defining functions' source plus their output on a fixed probe text; the reader
re-derives any moment whose fingerprint differs and drops it when the ids no longer give its text (fail closed).

Caption records give `timing: "segment"`: `start` / `end` are the record's interpolated times (a locator),
`duration_s` is null and `duration_estimate_s` is flagged. The packager re-anchors a chosen moment on a word record
at cut time (law L-e); eligibility is recorded as judged at mining time (role clip) and is re-judged by the packager.

`speaker.turn_change_inside` is `true` when a caption speaker marker (`>>`) lies inside the span (a measurement),
otherwise null (not measured; the packager requires false: diarisation is pp-selectid phase 2, law L-v).

## 5. Mining

Windows: whole sentences of ONE video (never two videos in a call: the v3 replay found cross-video leaks at batch 2),
at most 40 sentences / 900 words per window, 6 sentences overlap; an unfinished last sentence is never offered. A
window with no Bitcoin term (bitcoin, btc, sats, satoshi, halving, hash rate, lightning network, self-custody, ...)
is not sent to any model (recorded as `screened_no_bitcoin`; L-f screens before any model call too).

The model sees `[S<k> mm:ss] <sentence as spoken>` inside an untrusted `<sentences>` block and returns ONE JSON object
(prompt mine/2): `{"moments": [{"first": id, "count": 1-5, "scores": {7 integers 0-5}, "names_person": bool, "risk":
[enum], "about_bitcoin": bool, "altcoin": bool, "reason": "<= 160 chars"}]}`, at most 6 moments; the schema is sent to
every back-end that takes one (guided decoding / structured output), so `count` cannot exceed 5 (under mine/1's
`[first, last]` qwen chose 6-8-sentence ranges 17 times). Rejected, never repaired (L-l): anything but one JSON object
(markdown fences included), a missing / extra / duplicate key, a non-integer id (bools and floats too), an id not
offered in this window, a count outside 1-5, a duplicate range, a score outside 0-5, an unknown risk value, a reason
over 160 chars, more than 6 moments. A rejected reply is asked again with the reason (3 attempts), then the window goes
to the next back-end. Every attempt is saved with its verdict. Heimdall's qwen runs at reasoning effort `none` (at
`low` it spent the whole 4,000-token budget reasoning and returned empty content: INGEST-FAIL-04).

Moment line = the pp.moment/1 fields + additions (fields may be added): `flags_ext {about_bitcoin, altcoin}`,
`source {discovered_via, live_status, media_type, published_at_source, duplicate_of}`, `mined.backend`,
`mined.provider`, `mined.window`, `mined.attempt`, `mined.contract_fp`. `topics` stays `[]` until pp-selectid publishes
its TAXONOMY.

## 6. Provider interface (law L-x: NO SINGLE MODEL, ULTRON FIRST)

Every model role (here: `mine`, `judge`) goes through `pipeline.ingest.providers.Role`; vendors and model names live
ONLY in `pipeline/ingest/providers.json`. Back-ends: `openai_compat` (Heimdall, xAI, OpenAI), `anthropic` (SDK),
`gemini` (google-genai), `ollama_local` (gemma3:27b on Ultron through `story_semantics.LocalLLM`'s GPU0 guard; refuses
unless the GPU0 lease is held: the integrator enables it). Each role has an ordered chain of at least two enabled
back-ends; the run continues while any one back-end works.

Per back-end: bounded in-flight (Heimdall 12, never above the global 20), queue-aware backoff on HTTP 429 and on
503 `provider_overloaded` (Retry-After honoured, else 2 s doubling to 60 s with jitter, shared by every thread of that
back-end), a circuit breaker (open after 5 consecutive failures, or >= 50 % failures over the last 10 calls inside
10 min, or median latency > 150 s over the last 10; half-open probe after 5 min), and a spend book. A 503
`routing_error` (a request the endpoint cannot serve) is not retried on that back-end.

Default order today (`mine`): local gemma3:27b (disabled until the integrator runs the A/B under the GPU0 lease and it
meets the bar) -> Heimdall qwen3.8-27b -> Anthropic -> xAI. The order is data: the A/B (section 8) decides it and is
re-run so the role migrates to local as local improves.

Heimdall spend: measured from `GET /credits` (total_usage minus the sweep baseline 0.2036796658, the probe's own
measure, PHASE3_FLEET_LOAD.md) every 10 min, plus this service's own `usage.cost` since the last measurement. At 90 % of
the $460 cap (orchestrator 02:45: a NOTIFY, not a halt) the service writes "HEIMDALL SPEND AT 90%" at the top of the
STATE file and routes mining to the other back-ends. Spend unmeasured for over 60 min is treated the same way (law L-m).
Frontier back-ends have a daily dollar budget in the config; when it is used up the back-end refuses and the next one
is tried; when every back-end refuses, videos wait in the queue (nothing is dropped).

## 7. Durability and "nothing lost"

The queue is SQLite (WAL). A video's moments are appended in one write (fsync) after all its windows are mined, then
the state moves to `mined` (a crash between the two re-appends identical lines on restart: readers keep the latest
line per moment_id, by the contract). The adapter bisects the ledger on `mined.at` and reads only the tail that can
hold a returnable line (min(since, now - 72 h) - 1 day): 16-25 s per 100k lines before, the recent tail after. A
runtime file `<store>/ingest/overrides.json` (`{"<back-end id>": {"base_url": ...}}`) moves an OpenAI-compatible
back-end without a restart; the service logs every change (outage drills; endpoint moves). A back-end's URL is read
when it is next called, so while its breaker is open a restored URL is seen at the half-open probe. On restart, `probing` -> `discovered` and `mining` -> `transcribed`; validated replies are
reused from the reply cache, so a re-mine costs nothing. A torn final ledger line (crash mid-write) is sealed with a
newline on start; readers skip and count unparseable lines. Every state change is an `events` row.

## 8. Comparison (orchestrator 02:45: blind A/B per role)

`tools/ingest_watch.py ab` runs the same 30 videos from the saved universes (`runs/fresh_*/TOPIC_SELECTION.json`,
records read read-only from the main store and hash-checked) through each chosen back-end on identical windows and
reports per back-end: validity / failures, latency (p50 / p95 per call), dollars (per call, per video, per day at the
live rate), agreement on the top 5 moments per video (sentence-range overlap, both directions), agreement on hard
flags, recall of the PBX-approved Nov 11 preview passages, and a BLIND judge verdict (a model of another vendor than
every generator; sides shuffled, names hidden). Local gemma3:27b runs under the GPU0 lease by the integrator with the
same harness and prompts (`--backends local_gemma`).

## 9. Coverage check

Daily (and on demand): an independent listing of every partner channel at check time (RSS when it answers, else the
uploads playlist); every video published in the last 24 h is matched to the queue and the ledger; the report gives
mined / published (Shorts reported separately: never mined by policy), and every other video with its reason (still
live, captions pending, no captions, too long, duplicate, unavailable, all back-ends failed, never discovered = a watcher
miss). A channel whose listing fails is "unmeasured", never counted as covered (L-m).

## 10. Hand-off to the main tree (the integrator's act)

1. Transcripts: `tools/ingest_watch.py handoff --main /home/ultron/protocol_pulse/data/editorial` (dry run by
   default) lists, per video, the staging files absent from the main store and verifies each record's
   `transcript_sha256`; `--apply` copies only absent files (never overwrites; write-once like the store) and is run by
   the integrator. A main record that already exists for the video is left as is (the store reads its best method).
2. Moments: the packager takes the ledger path as an argument (`data/editorial/moments/moment_ledger.jsonl` in the
   store it reads); `pipeline.ingest.ledger.best_unused_moments(path, since, now, delivered_ids, ...)` is the adapter.
3. Wiring into the main tree: set `PP_INGEST_ALLOW_MAIN_STORE=1`, run `tools/ingest_watch.py run` from the main tree in
   its own tmux, enable `local_gemma` in providers.json only under the GPU0 lease.

## 11. Assumptions (most defensible reading; the integrator may overrule)

- A1 Registry: the selector's universe = `pipeline/channels.json` enabled with a channel id (64 channels at c1451047,
  identical to the main tree's file at 02:40 ET); read-only.
- A2 Shorts are not mined (strategy review: never re-cut a partner's own Short; the packager needs whole sentences of
  long-form speech); they are recorded and reported.
- A3 VOD ceiling 6 h for captions (no Whisper cost on this path); the selector's 3 h ceiling is its own.
- A4 A caption record is the transcript this path stores; no Whisper, so `timing` is `segment`.
- A5 Frontier fallback model: the provider config names it (Anthropic's default model per the Claude API reference);
  live fallback budget $15/day, A/B budget $25 total, both in the config.
- A6 The 90 % Heimdall tripwire notifies and falls back (orchestrator 02:45), it never halts.
