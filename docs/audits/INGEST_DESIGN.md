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

HARD-FLAG PRECISION (orchestrator ruling 40, 2026-11-13: "L-u stays hard; a wrong label is not L-u"):
`tools/ingest_watch.py flagcheck` (pipeline/ingest/flagcheck.py) MEASURES how often the miner's imperative /
accusation / single_source_breaking labels meet the ruling's definitions, and changes nothing (no flag is cleared, the
adapter's exclusions do not read it). Sample: the flagged rows published in the last 72 h, newest first, at most 200.
A second model (role `flagcheck`: two gateway back-ends, never a model or back-end that mined any line of the row's
video) answers ONE narrow question per flag with the definition in the prompt, for every flag of every sampled row:
strict JSON `{"answer": "yes" | "no" | "unsure", "evidence": <words copied from the quote when yes, else empty>,
"why": <= 200 chars}`; a question no back-end answered is unmeasured, never agreement. The checker is calibrated
first on 24 quotes with a clear answer (4 yes + 4 no per flag, fictional names) and its score is reported with the
tables. Option B of the ruling (a flag stands only when both models agree; unsure / unmeasured keep it) is simulated
with the adapter's own read on a copy of the ledger. Option A (the ruling's definitions in the miner's prompt) is
dry-run by `tests/ingest/dryrun_definitions.py` against a control re-run of mine/2. Report:
docs/audits/parallel/pp-ingest_FLAG_PRECISION.md.

Moment line = the pp.moment/1 fields + additions (fields may be added): `flags_ext {about_bitcoin, altcoin}`,
`source {discovered_via, live_status, media_type, published_at_source, duplicate_of}`, `mined.backend`,
`mined.provider`, `mined.window`, `mined.attempt`, `mined.contract_fp`. `topics` stays `[]` until pp-selectid publishes
its TAXONOMY.

## 6. Provider interface (law L-x: NO SINGLE MODEL, ULTRON FIRST)

Every model role (here: `mine`, `judge`, `flagcheck`) goes through `pipeline.ingest.providers.Router`; vendors and model names live
ONLY in `pipeline/ingest/providers.json` (a test reads every identifier and string of the package for them). Back-end
kinds (wire protocols): `openai_compat` (Heimdall, xAI, OpenAI), `anthropic` (SDK), `gemini` (google-genai),
`ollama_local` (gemma3:27b on Ultron through `story_semantics.LocalLLM`: available only while this process holds the
GPU0 lease, `gpu0.held()`, a check; LocalLLM itself takes `gpu0.require` + `swap_to` on every request, main 4867a74a;
`Router.release()` unloads it when a cycle ends). Every back-end names its vendor. Each role names at least two
back-ends.

SPEND FREEZE (orchestrator 05:30 ET Nov 12, until told otherwise): `providers.json` `spend_freeze.vendors` = OpenAI,
Anthropic, xAI, Google. A frozen vendor's back-end is never called by any role, whatever its chain, `only` or `enabled`
say (`Router.available` and `Router._try` both refuse); its stored validated replies cost nothing and may be re-read.
The `mine` chain is Heimdall qwen3.8-27b then the local model, so in this session (no GPU0 lease) Heimdall is the only
callable miner: when it is down, videos WAIT (below) and are mined when it returns; nothing falls through to a paid
frontier model. Lift: remove the vendor from `spend_freeze` (and restore the chain), restart.

Per back-end: bounded in-flight (Heimdall 12, never above the global 20), queue-aware backoff on HTTP 429 and on
503 `provider_overloaded` (Retry-After honoured, else 2 s doubling to 60 s with jitter, shared by every thread of that
back-end), a circuit breaker (open after 5 consecutive failures, or >= 50 % failures over the last 10 calls inside
10 min, or median latency > 150 s over the last 10; half-open probe after 5 min), and a spend book. A 503
`routing_error` (a request the endpoint cannot serve) is not retried on that back-end.

Order before the freeze (`mine`): local gemma3:27b (disabled until the integrator runs the A/B under the GPU0 lease
and it meets the bar) -> Heimdall qwen3.8-27b -> Anthropic -> xAI. Under the freeze: Heimdall -> local. The order is
data: the A/B (section 8) decides it and is re-run so the role migrates to local as local improves.

Gateway spend (`spend_meter` in the config: the Heimdall back-end, label HEIMDALL): measured from `GET /credits`
(total_usage minus the sweep baseline 0.2036796658, the probe's own measure, PHASE3_FLEET_LOAD.md) every 10 min, plus
this service's own `usage.cost` since the last measurement. The account is shared with the fleet: the meter reads the
fleet's spend, not only this service's. At 90 % of the $460 cap, or when the spend is unmeasured for over 60 min (law
L-m), it NOTIFIES and never halts (orchestrator 02:45 + 05:30; integrator B1): "HEIMDALL SPEND AT 90%" (or
"... UNMEASURED") goes on the first line of the STATE file (rewritten only when that line changes) and the metered
back-ends move to the END of every chain, so other callable back-ends go first; when there is none, Heimdall keeps
mining. Frontier back-ends have a daily dollar budget in the config; a used-up budget skips that back-end. Recorded
cost: the vendor's own figure where it reports one (`usage.cost`; `usage.cost_in_usd_ticks` / 1e10), else tokens x
the price table (estimates marked in the config). Error text is redacted of every key value before it is recorded; a
redirect is refused (the bearer key never follows one); a runtime base-URL override is honoured only for this machine
or the configured host.

## 7. Durability and "nothing lost"

One mining pass per video; each failed window carries whether its chain was in an OUTAGE (every back-end skipped,
down or refusing access: nothing answered and was rejected) or REJECTED it (a back-end answered: invalid, refused,
empty, a 4xx). Integrator B2:
- outage only: the video waits (`mine_waiting`, reason `OUTAGE ...`), retried every 10 min, no try used, for as long
  as the outage lasts (the breaker skips the dead back-end at no cost; its half-open probe every 5 min finds it back);
- rejected windows: a try is used; after 3 such passes the good windows' moments go to the ledger and the video is
  `mined_partial`: retried every 6 h until 72 h after publish (every pass that mines windows appends its lines, the
  latest line wins; a pass that mines none leaves the ledger and the count as they are), never counted as mined
  (coverage, stats);
- every window mined: `mined`.
Videos waiting on an outage for over 30 min put one line at the top of the STATE file ("MINING WAITING ON AN OUTAGE: n
video(s) waiting since T ..."), removed when none waits; it shares that top block with the spend notices, each writer
replacing only its own lines. A coverage report with an unmeasured channel is tried again every hour that day.
Caption downloads respect the yt-dlp breaker, and a throttled caption answer trips it.
The queue is SQLite (WAL). A video's moments are appended in one write (fsync) when its pass ends, each line's
`mined.at` stamped under the append lock (so the file is in mined.at order), then its state moves
(a crash between the two re-appends identical lines on restart: readers keep the latest line per moment_id, by the
contract). Every line is checked before the write (one bad line and nothing is written); a torn tail left by a failed
write is closed with a newline under the append lock. A range seen from two overlapping windows is one line whose
flags are the union of both observations (fail closed, L-u). One service per store: `run` / `once` hold an flock on
`<store>/ingest/service.lock`; a second one is refused before it recovers anything. The adapter bisects the ledger on `mined.at` and reads only the tail that can
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
Under the spend freeze (orchestrator 05:30) the `judge` role's back-ends (xAI, Google, Anthropic) are all frozen: the
A/B prints "no judge" and reports no blind verdict until a judge of another, unfrozen model family is configured
(REQUESTS R9; the freeze audit measured two Heimdall-served families, glm-5.3-flash and muse-spark-open, reviewing a
100k-token package coherently at reasoning effort none).

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

## 12. Expiry and the rolling purge (rulings 76 + 77, orchestrator 18:09 ET Nov 13)

PBX 18:01: "do we have a system in place to stop our clipping system from reusing old clips? We need to delete all the
contents after like 6 to 12 hours so that we never reuse any of it." The builder's ruling 76: a moment is usable only
within 12 h of its video's publish time, then never again.
- EXPIRY IN THE LEDGER: every line carries `expires_at` = its video's publish time + 12 h (`config.EXPIRY_H`), written
  when it is mined (lines are never rewritten). The adapter (`ledger.best_unused_moments`, the builder's and the
  word-pass worker's only read) refuses a moment whose expiry has passed BEFORE any other rule: `expired (rulings 76 +
  77 ...)`. The expiry used is the EARLIER of the recorded field and the publish time + 12 h, so a line mined before
  the field existed, or a field that says later, never extends a moment's life (fail closed); a line without a
  measured publish time is refused as before. Expired rows stay in the ledger file: the receipt that a moment was
  said and seen (first-said, the dedupe against re-posts). The adapter's default horizon is 12 h.
- THE PURGE (`pipeline/ingest/purge.py`, scope `pipeline/ingest/purge.json`): the watcher's own loop (no cron), every
  10 min, deletes MEDIA files of videos published more than 12 h ago from three targets only: the acquired mp4
  sections of the runs (`runs/*/sources/<video id>.<ext>`), the lock precheck's acquired sections
  (`data/lock_precheck/work/*/sources/`), and a dead word-pass cycle's temporary audio and window WAVs
  (`/tmp/word_pass_*` untouched for 12 h). Kept, always: ONE COPY PER DELIVERY of a DELIVERED video (a video cut into
  a run with a delivery record, TELEGRAM_DELIVERY or REVIEW_DROP, or into a pin the stand-alone scorer records as
  delivered, or into a reference with delivery evidence). The orchestrator's 08:15 ruling 3 (A19, Nov 14) replaced
  "wherever it lies": each delivery keeps the acquired source section(s) its PROVENANCE.json names, BY SHA256 (its own
  sources/<file> or run/sources/<file> when the hash matches, else the copy of that video in the targets with the
  hash; `purge.kept_copies`, hashes cached by path, size and mtime, the cache emptied at 4,096 entries; a copy only in
  ANOTHER unit's non-target directory is not looked for, so that video is unresolved: none on Nov 14, audit a19 c1); a
  video it cut that its PROVENANCE does not list, or a delivery whose PROVENANCE names no sources, keeps the
  delivery's own section(s) by name; a delivered video whose copy cannot be identified (no hash named, no copy with
  it, no own section, a candidate that cannot be read) by ANY of its deliveries keeps EVERY copy (fail closed, per
  video; the pass names the video and every delivery that could not identify its copy: live.json
  `purge.last_pass.one_copy_per_delivery.unresolved`, and the `purge` command lists them: audit a19 c2). Invariant
  (audit a19 c2, glm): the deletion loop keeps exactly the paths kept_copies names plus every copy of an unresolved
  video; a named path the loop could not reach (outside its unit, protected) is kept by the loop's own guards. It
  holds because both sides fail closed: a fast path added to either side must re-derive it. Every other cached copy of
  a delivered video (re-renders, replays, recuts) is media like any other below, and each deletion names the copy kept
  (deleted.jsonl `other_copy_of_delivered`, `kept_copies`, by the video id it was kept for, not by its file name).
  Measured before it went live (a read-only dry run, 09:2x ET Nov 14): 15 deliveries, every PROVENANCE hash found, 46
  copies kept, 121 other copies (3.36 GB) to go; 3 more copies of the v2f reference's video (3.53 GB) stay because its
  publish time is not measured. The hashing it costs, measured in a fresh process (10:3x ET Nov 14): 39 files, 0.45
  GB, 0.8 s; the pass 1.3 s, the next 0.5 s (the cache). Also kept: a file whose publish time is not measured, a run
  touched in the last 2 h (a render in progress), a file a process holds open, a symlink; and every non-media file
  (transcripts, PROVENANCE.json, transcript hashes, the pins). Renders and their intermediates (out/, qa/, VERIFY/),
  our voice-over, references/ and test fixtures are never targets. Media outside the targets is measured and reported
  (`purge --measure`), never deleted. A delivered set or /proc that cannot be read stops the pass (L-j). Every
  deletion is a line in `<store>/ingest/purge/deleted.jsonl`, every pass one in `passes.jsonl`; the last pass and the
  total freed are in live.json (`purge`).
- MINING ORDER: newest uploads first, always (`Queue.due` orders by publish time, newest first, for both the caption
  fetch and the mining; three videos mine at once).

## 13. The hook pass (ruling 80, orchestrator 18:42 ET Nov 13)

The 12 h pool had no moment rated 4 as a HOOK: the miner finds good statements, not openers. The hook pass is a
second mining question over the SAME windows (`mine.HOOK_PROMPT`, version mine-hook/1; role `hook` in providers.json,
the mine role's chain): "the 1 to 3 lines in this window that would stop a scroll as the FIRST words of a short
video". The prompt carries the builder's judge question VERBATIM (pp-selectid package.py HOOK_QUESTION, rulings 52 /
59: "scroll", "alone", "setup", each 1-5; a test compares it with the builder's source), the ruling's definition of a
hook (4 to 14 s, whole sentences, one speaker, understandable alone, a concrete / surprising / sharply put claim,
contrast, number or question about Bitcoin or money) and its NOT list (a greeting or show intro, a date or "this
week", an ad read, a price prediction, an accusation), and the moment prompt's own score axes and flag list. A hook row
is a moment line (pp.moment/1) with `role_hint: "hook"`, eligibility judged with the builder's role "hook", and
`mined.prompt_version` mine-hook/1; it has the moment id of its span (the builder's dedupe and delivered checks keep
working). A row outside 4-14 s (or unmeasured) is not written. Every ledger append goes through one lock that carries
the video's earlier flags for the same moment (`ledger.carry_forward`): the adapter returns the latest line, which
must never lose a flag. The watcher's `hook` loop (every 5 s, 2 videos at once) runs it on mined videos published in
the last 12 h, newest first: the current window at start, then every new upload after its moment pass. Report:
`tools/ingest_watch.py hooks` and live.json `hooks_12h`.

CONVERSATIONS (mine-hook/3: the orchestrator's 08:15 ruling 2, Nov 14, ruling 92's options (b) + (c); "last night's
pools had exactly one opener rated 4 in each window: this is where the supply is"). WHICH EPISODES (mine-hook/4, the
orchestrator's 09:02 ruling, A36: WIDEN; it was ruling 92's 1.0 line, which measured 26 of 67 mined videos as
conversations and cut off Bitcoin Magazine's and CoinDesk's interviews and Pompliano at 0.97): (b) + (c) run on every
episode EXCEPT one that is MARKED (it carries caption speaker markers) and sits under `mine.CONVERSATION_TPM` (0.3)
turns a minute, a measured solo recap (`mine.is_conversation`). An episode with NO markers at all (auto captions often
carry none, e.g. Stephan Livera's interviews; professional captions never do) is asked, and so is a marked one whose
rate cannot be measured: "at $0.006 a video the cost of asking is nothing and the cost of missing an interview is the
whole point". (The rate compared is `episode_measure`'s, rounded to 2 decimals; audit a36 c1 / c2.) The builder gets the matching ruling for its source test. In such an episode:
- (b) the hook question allows up to `HOOK_MAX_CONVERSATION` (5) openers a window (the prompt says it, the validator
  holds the reply to it); elsewhere it stays 3, and its prompt is byte-identical to mine-hook/2's (so a re-run of a
  solo video is answered from the reply cache at no cost).
- (c) the SPOTLIGHT question (`mine.SPOT_PROMPT`, mine-spot/1, role `spotlight`: the hook role's chain) is asked over
  the same windows: "one speaker's complete claim, number or question that a stranger understands cold and would stop
  scrolling for", ruling 90's spotlight: ONE passage of one speaker, 12 to 35 s (1 to 8 whole sentences), played alone;
  the builder's judge question verbatim (its "scroll" and "alone" parts: nothing follows a spotlight) and the
  stand-alone test of the whole clip; the hook prompt's NOT list plus "a host reading news aloud, or a speaker reacting
  to a clip played inside the video" (ruling 92's source rule). At most 2 a window. Its rows are moments with
  `role_hint: "spotlight"`, eligibility judged with the builder's role "clip" (its 12-20 s is a target that ranks, law
  L-o; the builder's spotlight pool takes up to 35 s), `mined.pass` "spotlight"; a row outside 12-35 s or opening on a
  pronoun, a conjunction or a reply word (the OPENER rule) is not written. The builder reads every row through the
  adapter and re-judges it (role_hint is advisory; `carry_forward` carries any hint, a later line's own winning).
- The pass records its version (`hook_version` mine-hook/4), the spotlight rows (`spot_rows`; NULL for a video the
  question was not asked of) and its cost over both roles (`hook_cost_usd`); live.json
  `hooks_12h.spotlight_asked_videos` and
  `spotlight_rows`. A pass with failed windows in either question is retried as before (the hook question's replies
  come back from the reply cache, free). A spotlight question that CRASHES (an exception, not a model failure) never
  holds back the hook rows: they are written, the crash is an event (`spotlight_crash`) and the pass's note, and the
  pass is recorded as "<version> (spotlight crashed)", so `hooks --rerun` asks it again (audit hk3 c2). `tools/ingest_watch.py hooks
  --rerun` re-asks every video of the 12 h window whose pass is older. A provider config without a role for every
  mining question stops the start (`service.check_roles`).

## 14. The shared Heimdall-down signal (ruling 87, orchestrator 21:18 ET Nov 13; the builder's contract, Nov 14)

ONE "Heimdall down" signal for the builder and this watcher: the builder's module (pp-selectid
`pipeline/heimdall_health.py`, 125e7381), loaded by path at the watcher's start and used through its API only
(`note`, `mode`, `probe_due`, `probe_result`); its state file `tests/package/proof/HEIMDALL_HEALTH.json` in the
builder's worktree under its own flock. Down = no Heimdall family answering for 15 min (`plan_b`); back after 3 probe
answers in a row. This side (`pipeline/ingest/downsignal.py`, the `signal` loop every 5 s):
- NOTES: every real call of the watcher to a back-end of `providers.json down_signal.vendor` (mining, hooks, the
  second-model check) is one outcome: answered (`ok`, or `invalid`: the gateway answered inside the back-end's
  deadline) or not (any other outcome of a real call: down, refusing, empty, late, 429). No note for a stored reply or
  a missing key (no call), a probe call (its outcome is the probe's), another vendor. A back-end under an
  overrides.json `base_url` override (the outage drill) is noted `drill=True` (recorded, never counted). The router's
  threads only leave the outcome in memory (the latest answer and the first failure after it, each with its time):
  one thread calls the module, so a held or stuck shared lock never stalls the miner.
- THE PROBE (role `probe`: the miner's qwen3.8-27b, then glm-5.3-flash, each a probe-only back-end with the builder's
  60 s deadline, one in flight): while `probe_due`, "Reply with the single word OK."; the first answer ends it; never
  from a stored reply (`use_cache=False`), never held back or taught by the circuit breaker (`breaker: false`), no
  transport retry, never while a probe back-end is under an override; a probe whose back-ends could not be called is
  no probe. Since pp-selectid 11ed255f (this branch's REQUESTS R12) `probe_due` CLAIMS its 2-minute slot for the whole
  fleet: this watcher passes who="pp-ingest probe" when the loaded module's `probe_due` takes it (said once in the log
  when it does not); a slot claimed and then not probed stays spent from its claim.
- SWITCHES: every switch in the shared state, whoever made it, goes once to the top of `pp-ingest_STATE.md` (line 1,
  the module's words IN CAPITALS with the time ET, plus who made it and the miner's Plan B; newest first on one
  physical line, kept first whatever other notice comes or goes) and to the evidence file
  `data/editorial/ingest/down_signal.jsonl` (the module also writes its own switch record there when this watcher
  trips it). The module is given NO STATE path: its own head writer would leave a lock file beside STATE.md and bypass
  the notices' lock.
- FAIL CLOSED: an unreadable state, a missing module or a call stuck on the lock is never read as up or down
  (live.json `down_signal.mode` null with the reason at once; a "<LABEL> DOWN SIGNAL NOT READ" line on STATE after
  30 min, removed when it is read again).
- THE MINER'S PLAN B: queue and wait (the 05:30 Nov 12 spend freeze; the orchestrator's question is open). Nothing in
  the signal changes what the miner calls: in Plan B it calls Heimdall (then the local model, disabled), and when
  nothing answers the videos wait in the queue, never dropped (section 7's outage handling).

## 15. The miner's Plan B: the paid route (ruling 98, orchestrator 06:13 ET Nov 14)

PBX's fail-safe (21:08 Nov 13) covers the miner: "if [Heimdall] ever fails to respond for more than perhaps 10 to 20
minutes ... use Groc mainly or whatever other AI tokens we have".
- OPENS (downsignal `_route_tick`, the signal thread) when the shared state says `plan_b` AND its failure clock
  (`failing_since_utc`, a time with its zone) is at least `paid_route.after_down_s` (20 min) old: no Heimdall family
  has answered for 20 min running. CLOSES at the signal's back switch (3 good probes). A signal not read opens,
  closes and spends nothing (`paid_open` False; the queue keeps the recorded state for a restart).
- WHILE OPEN the mine loop takes only NEW uploads (published inside `new_within_s`, 6 h), conversations first (the
  caption turns per minute >= `conversation_tpm`, ruling 92's measure), then newest; older videos wait for Heimdall
  (no backfill); the hook pass and the flag checks stay on Heimdall (they wait). Mining is on role `mine_paid` (Grok,
  then Gemini): the ONLY role allowed past the spend freeze (`freeze_lifted` names the ruling; the router lets a frozen
  vendor through for no other role), under `daily_cap_usd` $2.00 per ET day: each call holds its priced worst case
  (every attempt at its full reply budget) before it starts, the day's spend loaded from the queue's calls; past it,
  the videos queue and wait.
- EVERY ROW carries `miner_route` (the role that mined it: mine | mine_paid | hook | spotlight, the last since the
  08:15 ruling 2). When the signal is back, every
  video the paid route mined that is still inside `recheck_within_s` (12 h, its moments' life) is mined again on the
  mine role, once (a later paid mining makes it due again); every moment both passes found carries both models' flags
  (`ledger.carry_forward`). The builder re-judges every clip with its own gates whatever mined it, so a paid label can
  cost yield, never integrity (the builder's word, Nov 14).
- EVERY SWITCH on STATE line 1 in capitals, with the signal's own: "MINER ON THE PAID ROUTE (...)", "MINER OFF THE
  PAID ROUTE (...)", "MINER PAID ROUTE CAP REACHED (...)" (once per ET day); kept and retried until written. Live:
  live.json / `status` `paid_route` (open, why not open, spend today, cap).

## 16. The second-model flag check in the watcher (ruling 40 P1, orchestrator 19:22 ET Nov 13; F1, Nov 14)

The miner's `imperative` and `single_source_breaking` labels are hard flags (L-u) only when a second model agrees.
- THE CHECK (service `check` loop, every 30 s): every flag of those two on a moment still inside 12 h with no answer
  that counts is asked of the role `flagcheck` (glm, then muse on Heimdall; never a model or back-end that mined any
  line of the video) with the ruling's definition (flagcheck.PROMPT); the answer goes into a new line of the moment
  (`risk_checks`). The adapter releases such a flag only on a "no" from a model other than the miner under the current
  prompt version (`ledger.check_valid`, `effective_risk`; the label moves to `risk_notes` in the returned row); "yes",
  "unsure", no answer: the flag stands. `accusation` is never released (P2 measured it unsafe). A question nobody
  answered is asked again after CHECK_RETRY_S (600 s).
- THE CALIBRATION decides which back-ends may answer: the 16 quotes of the two flags with a clear answer
  (`flagcheck.PROBES`, fictional names); a back-end answers if it answered every quote, right. Asked at every start and
  once a day. F1 (Nov 14): every quote is put to the model LIVE (`flagcheck.calibrate(fresh=True)`, the router's
  `use_cache=False`). Until then the calibration was answered from the reply cache, so every start and every daily
  calibration replayed the first answers (measured 20:10-23:05 ET Nov 13) and re-measured nothing: a model changed
  behind the same gateway name would have kept releasing flags on a stale calibration. A quote a back-end did not
  answer is asked of it again, only that quote, up to CALIBRATION_ROUNDS (3) rounds. When no back-end passed and one
  still could (a quote unanswered, none answered wrong: an outage at calibration time; or no back-end of the role could
  be called at all, which asks nothing: audit f1 c2), the next calibration comes
  after CHECK_RETRY_S, the wait doubling while it keeps failing (600, 1200, 2400 s ... up to a day: about eight
  calibrations a day at worst, each at most 3 rounds of 32 short questions); when one passed, or every back-end
  answered a quote wrong (at temperature 0 it would answer the same again), the next is the daily one. A calibration
  that CRASHES (audit f1 c1) is an event (`check_calibration_crash`) and counts like an unanswered one: nobody
  answers (an earlier allowance is not kept), the stored calibration is emptied, and the next comes after the
  doubling wait, so a crash after its live calls never repeats every 30 s. Nothing measured is never a pass: an
  unanswered quote never counts as right. The measurement CLI (`tools/ingest_watch.py flagcheck`) keeps its stored
  replies (a report is reproduced from them; it releases nothing). Live: live.json
  `second_model_checks_12h.calibration`, per back-end: right, of, unmeasured, `wrong` (flag, expected, answered, the
  quote), `asked_at` (the calibration's start) and `seconds` (its duration), and `calibration_crashes` (the crash
  events of the last 12 h: audit f1 c2); the log line says the same.
- A RESTART keeps the last live calibration when it is under a day old (`service._reuse_calibration`, Nov 14): the
  stored record must name exactly the role's callable back-ends with their current models, have been measured on the
  same prompts (`prompts_sha`: `flagcheck.calibration_sha`, a sha256 of every calibration prompt with its expected
  answer; a record without it is refused: audit reuse c2), carry ONE `asked_at` (the live calibration's start) under
  CHECK_RECALIBRATE_S old, and show at least one back-end that answered all 16 quotes right; then that back-end may answer at once, no quote is asked, the next calibration stays due a day after the
  live one, and the event `check_calibration_reused` and the log say so ("calibration reused (asked live at ...)").
  Anything else (an older record, a changed model or chain, a record without `asked_at` from the cached era, one in
  which nobody passed, an outage calibration) is asked live as before, and the log says why ("the stored calibration
  is not reused (asked 25.0 h ago): asked live now": audit reuse c1), so F1 holds: no allowance ever comes from a
  stored reply, only from a measurement taken live within the day. Why: each restart re-asked 32 quotes (the check
  loop waiting 1-2 minutes), and at 09:16 ET Nov 14 a restart's calibration ended on one 502 that a quiet watcher
  turned into a false 'down' (ruling 87, since amended at 10:05: any answer, a probe's too, resets the clock).

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
