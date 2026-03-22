## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### 1) `EpisodeRunner.run()` / `_run()`
- `run()` correctly wraps `_run()` in a broad `try/except`, so the **episode-level entrypoint never raises** and returns an `EpisodeReport` on fatal error. Good for top-level robustness. (`episode.py:69-80`)
- `_run()` validates the manifest, runs preflight, creates an episode-scoped context, renders each segment, concatenates outputs, then performs final contract/QC checks. The overall orchestration is coherent. (`episode.py:82-260`)

#### 2) Preflight ordering bug
- Preflight is run **before** `EpisodeContext.create()`, and it receives `output_dir` rather than the episode workdir. (`episode.py:94-108`)
- This is not a crash bug by itself, but it means disk checks are against the parent output directory, not the actual workdir mount/path if those differ. More importantly, any preflight checks that should be episode-scoped cannot use `ctx.workdir` yet.

#### 3) Unknown segment type handling double-counts degradation
- For unknown segment types, `_run()` explicitly calls `ctx.mark_degraded(...)` and then creates a filler via `_make_unknown_filler()`. (`episode.py:115-128`)
- If `_make_unknown_filler()` fails, `RenderedSegment.contract_passed` becomes false, but no fallback beyond that exists. The episode still proceeds.
- Also, this path is inconsistent with the rest of the segment system, which uses `filler_result()` and central degraded accounting.

#### 4) Segment rendering generally follows “never raise”
- Most segment `render()` methods wrap `_render()` in `try/except` and return `self.filler_result(...)` on exception. Good. Examples: `transition.py:15-20`, `wrap.py:19-24`, `cold_open.py:31-37`, `narration.py:21-27`, `partner_clip.py:42-47`, `data_segment.py:121-126`, `social.py:27-33`, `signal_active.py:31-37`, `x_spaces_segment.py:28-34`.

#### 5) Major correctness issue: `filler_result()` can leave no output file
- `Segment.filler_result()` calls `make_filler(output_path, ...)` directly, not via temp + atomic rename. (`segments/base.py:32-60`)
- If `make_filler()` fails, it tries an emergency ffmpeg write directly to `output_path`. (`segments/base.py:37-55`)
- If that also fails, it returns `RenderedSegment(... path=None, contract_passed=False, degraded=True ...)`. (`segments/base.py:57-60`)
- This violates the stated invariant in `RenderedSegment` docstring: “Always populated — degraded=True if filler used.” (`manifest.py:42`)
- It also undermines concat completeness because missing segment files are silently skipped later. (`episode.py:143`)

#### 6) Silent truncation of failed segments in final episode
- Final concat only includes segment reports whose `path` exists. (`episode.py:143`)
- If a segment fails so badly that even filler creation fails, that segment is simply omitted from the final episode rather than forcing a HOLD immediately.
- This can produce a final episode missing required content while still reaching concat/QC stages. That is a production correctness problem.

#### 7) `encode_segment()` return contract is misleading
- `encode_segment()` claims “Write filler to output_path. Never raises.” (`ffmpeg_core/encode.py:31-32`)
- But on failure it returns `(False, False, summary, ms)` even if filler was successfully written. (`ffmpeg_core/encode.py:57-70`)
- Callers then infer degradation from `primary_ok` or `summary["filler_used"]`. This works, but the boolean naming is confusing and easy to misuse.

#### 8) `TransitionSegment` duration reporting can be wrong
- It always returns `duration=dur` (0.25s), even if encode fallback wrote a filler of a different duration or ffprobe summary says otherwise. (`segments/transition.py:65-68`)
- This is minor but inaccurate.

#### 9) `NarrationSegment` double degradation accounting
- On post-publish contract failure, it calls `ctx.mark_degraded(...)` and then calls `self.filler_result(...)`, which itself also calls `ctx.mark_degraded(...)`. (`segments/narration.py:53-57`, `segments/base.py:56`)
- This **double-counts degraded segments and filler seconds** for one failure.
- That directly affects verdict logic in `EpisodeContext.verdict()`. (`state.py:72-83`)

#### 10) `ffprobe_contract()` audio codec check nested incorrectly
- Video codec check is inside the `else:` block for audio presence. (`helpers.py:116-129`)
- If a file has video but no audio, the code never checks whether the video codec is h264.
- Since the contract requires both streams, this won’t create a false pass, but it makes diagnostics incomplete and contract enforcement less precise.

#### 11) `ffprobe_contract()` does not verify stereo layout name, only channels
- Law requires stereo; code checks `channels == 2` but not channel layout. (`helpers.py:119-124`)
- Usually acceptable, but not a strict contract match.

#### 12) `normalize_pip_preview()` does not validate output contract
- It logs success if ffmpeg succeeded and file exists. (`helpers.py:276-279`)
- No `ffprobe_contract()`-style validation for the PiP normalization output, despite Law 7 depending on this pre-normalized asset being correct.

#### 13) `overlay_pip()` docstring contradicts implementation
- Docstring says `eof_action=pass`, implementation uses `eof_action=repeat`. (`ffmpeg_core/filters.py:52-62`)
- Implementation matches the law; docstring is stale and misleading.

#### 14) `SocialSegment` Playwright path can leak temp PNGs
- `_render_cards_playwright()` writes PNGs into `ctx.segment_dir()` and never cleans them up. (`segments/social.py:235-240`)
- Not catastrophic, but under high throughput this accumulates junk in workdirs.

#### 15) `SignalActiveSegment` uses global cache file
- `_read_signal()` falls back to `PIPELINE_DIR / "cache" / "active_signal.json"`. (`segments/signal_active.py:19-20`, `39-50`)
- This is read-only, so not a race by itself, but it is shared mutable external state from the perspective of concurrent episodes. If another process writes it non-atomically, reads can see partial JSON.

#### 16) `XSpacesSegment` computes `btc_str` and never uses it
- Dead code / incomplete UI element. (`segments/x_spaces_segment.py:140`)
- Suggests intended attribution/footer content is unfinished.

#### 17) `spaces_pipeline.py` bridge is logically fine
- It filters by source and usability, scores candidates, and returns a segment dict. (`utils/spaces_pipeline.py:73-154`)
- No obvious crash bug there.

### Race conditions / concurrency
- `EpisodeContext` is episode-scoped and uses a per-context lock for metrics refresh. Good. (`state.py:36-38`)
- Metrics cache path is under `ctx.workdir`, avoiding `/tmp` collisions. Good. (`segments/data_segment.py:140`)
- However, `_get_metric()` does synchronous network refresh under lock with a 5s acquire timeout. (`segments/data_segment.py:83-90`)
  - This can serialize multiple data segment renders within one episode and stall rendering.
  - Not a correctness bug, but a throughput concern.
- Shared cache file `SIGNAL_CACHE` is process-global. (`segments/signal_active.py:20`)
- `CHARTS_DIR` is process-global read-only; fine.

### DB / N+1
- No DB code is present in this patch, so no SQLAlchemy/N+1 findings from the provided files.

### Production edge cases
- If ffmpeg is present but Playwright/chromium is not, social falls back gracefully. Good. (`segments/social.py:56-67`, `123-145`)
- If ElevenLabs is unavailable, several segments fall back to silence/filler. Good.
- If final concat succeeds but final contract fails, verdict becomes HOLD, but the invalid final file remains published in `output_dir`. (`episode.py:191-205`, `241-260`)
  - That is a correctness/operational issue: bad artifact is left in the final destination.
- `preflight.py` raises on missing TTS files for all segments, including optional segments that could otherwise degrade gracefully. (`preflight.py:28-34`)
  - This makes the whole episode HOLD before rendering, which may be stricter than intended.

---

## SECTION 2: LAW COMPLIANCE

### Law 1. `render()` NEVER raises. `filler_result()` on any failure.
**PARTIAL**

Compliant:
- All segment `render()` methods shown wrap exceptions and return `filler_result()`.  
  Examples: `segments/cold_open.py:31-37`, `segments/narration.py:21-27`, `segments/partner_clip.py:42-47`, `segments/data_segment.py:121-126`, `segments/social.py:27-33`, `segments/signal_active.py:31-37`, `segments/wrap.py:19-24`, `segments/transition.py:15-20`, `segments/x_spaces_segment.py:28-34`.

Partial / concern:
- `filler_result()` itself can fail to produce a file and return `path=None`. (`segments/base.py:37-60`)
- The law says filler_result on any failure; practically, this should mean a valid fallback artifact is always produced. Current implementation can still fail silently into a missing segment.

### Law 2. CRF-only encoding. No `-b:v/-maxrate/-bufsize` alongside `-crf`.
**COMPLIANT**
- I found no use of `-b:v`, `-maxrate`, or `-bufsize` with `-crf`.
- Audio bitrate `-b:a` is used throughout, which is allowed.

### Law 3. EpisodeContext episode-scoped. No module globals.
**PARTIAL**
Compliant:
- Mutable episode state is in `EpisodeContext`. (`state.py:14-107`)
- Metrics lock and refresh timestamp are episode-scoped. (`state.py:36-38`)

Partial:
- `segments/signal_active.py` uses module-level `SIGNAL_CACHE` pointing to a shared cache file. (`segments/signal_active.py:19-20`)
- This is read-only config-ish state, not mutable in-process state, so not a hard violation, but it does rely on shared external global state.
- `SEGMENT_MAP` and constants are fine.

### Law 4. `ffprobe_contract`: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.
**PARTIAL**
Compliant:
- Width/height/pix_fmt/fps/sample_rate/channels/video codec/audio codec are checked. (`helpers.py:98-129`)
- Audio bitrate is checked with tolerance. (`helpers.py:130-142`)

Partial / violation details:
- It does **not strictly enforce 192k**; it allows a range and skips lower-bound enforcement for short segments. (`helpers.py:130-142`)
- It checks stereo by channel count only, not explicit stereo layout. (`helpers.py:119-124`)
- Video codec check is nested under audio existence, so diagnostics are incomplete when audio is missing. (`helpers.py:116-129`)

### Law 5. Atomic writes via `atomic_rename`.
**PARTIAL**
Compliant:
- Many segment outputs use temp file + `atomic_rename()`.  
  Examples: `cold_open.py:53-72`, `partner_clip.py:68-114`, `data_segment.py:145-201`, `social.py:54-78`, `signal_active.py:67-91`, `wrap.py:65-80`, `episode.py:169-193`.

Violations:
- `Segment.filler_result()` writes directly to `output_path` via `make_filler(output_path, ...)`, not temp + atomic rename. (`segments/base.py:34-37`)
- Emergency filler in `filler_result()` also writes directly to `output_path`. (`segments/base.py:41-52`)
- `encode_segment.use_filler()` emergency fallback writes directly to `output_path`. (`ffmpeg_core/encode.py:41-53`)
- `EpisodeManifest.save()` uses `os.replace` directly instead of the mandated `atomic_rename`. (`manifest.py:74-85`)
- `write_concat_list()` uses `os.replace` directly instead of `atomic_rename`. (`helpers.py:317-323`)
- `_refresh_metrics_cache()` uses `os.replace` directly instead of `atomic_rename`. (`segments/data_segment.py:55-60`)

### Law 6. `safe_text()` from `helpers.py` is the single drawtext sanitizer.
**COMPLIANT**
- All user/content-derived drawtext text I checked goes through `safe_text()`.
- `ffmpeg_core.filters.drawtext()` docstring also mandates pre-sanitization. (`ffmpeg_core/filters.py:85-94`)
- I did not find raw user text interpolated into drawtext without `safe_text()`.

### Law 7. PiP: `eof_action=repeat`. `stream_loop=-1` on pre-normalized `pip_preview`.
**COMPLIANT**
- Narration uses `-stream_loop -1` for PiP input. (`segments/narration.py:126-130`)
- Overlay uses `eof_action=repeat`. (`segments/narration.py:67-70`)
- `_check_pip()` explicitly refuses on-demand generation and expects pre-normalized PiP. (`segments/narration.py:29-35`)

### Law 8. Metrics cache scoped to `ctx.workdir` NOT `/tmp`.
**COMPLIANT**
- `cache_path = ctx.workdir / "metrics_cache.json"`. (`segments/data_segment.py:140`)

### Law 9. Outro: `-an` strips audio before `stream_loop`.
**COMPLIANT**
- Wrap segment uses `['-stream_loop','-1','-an','-i',str(OUTRO_BRANDED)]`. (`segments/wrap.py:37-39`, `52-54`)

### Law 10. All 29 tests pass before commit.
**CANNOT VERIFY / PARTIAL**
- No test output included.
- I cannot certify compliance from code alone.

---

## SECTION 3: SECURITY

### Shell / command injection
- FFmpeg/ffprobe invocations use `subprocess.run([...])` with argument lists, not shell strings. Good. (`helpers.py:21-45`, many others)
- `run_ffmpeg()` logs a joined command string, but does not execute via shell. Good.

### Filesystem input handling
- Manifest paths (`tts_path`, `clip_path`, `pip_path`) are accepted as absolute strings and passed directly to ffmpeg. (`manifest.py:30-37`, segment files throughout)
- This is not shell injection, but it is **unvalidated filesystem access**. If untrusted users can influence manifests, they can cause reads from arbitrary local files.
- `write_concat_list()` escapes single quotes but otherwise trusts paths. (`helpers.py:306-326`)

### Secrets
- No hardcoded API keys found.
- Environment variable `ELEVENLABS_API_KEY` is used appropriately. (`segments/social.py:91`, `segments/signal_active.py:180`, `segments/x_spaces_segment.py:94`)

### Rate limiting / paid API exhaustion
- No rate limiting or quota guard exists around inline ElevenLabs TTS generation.
- `SocialSegment`, `SignalActiveSegment`, and `XSpacesSegment` can all trigger paid API calls per render. (`segments/social.py:87-112`, `segments/signal_active.py:176-226`, `segments/x_spaces_segment.py:85-116`)
- Under ~1000 concurrent users, this is a serious cost/exhaustion risk unless upstream routing already gates it.

### Authentication / SQL injection
- No routes or DB code are present in the provided files, so cannot assess auth bypass or SQL injection here.

### Input sanitization
- Drawtext text is sanitized well via `safe_text()`. (`helpers.py:329-348`)
- HTML for Playwright cards uses `html.escape()`. (`segments/social.py:163-167`)
- Good.

### SSRF / external calls
- External URLs are hardcoded to mempool.space and ElevenLabs, not user-controlled. Good.
- Timeouts are present. (`segments/data_segment.py:36-52`, `social.py:105`, `signal_active.py:196`, `x_spaces_segment.py:108`)

**Security summary:** no obvious injection bug in this patch, but there is a real **cost/rate-limit exposure** and **arbitrary local file read risk** if manifests are user-influenced.

---

## SECTION 4: FRONTEND QUALITY

- There is effectively **no frontend/UI code** in the provided patch except HTML/CSS used internally by Playwright to render social cards.
- So I cannot assess:
  - app layout fidelity
  - mobile viewport behavior
  - JS errors
  - async loading/error/empty states
  - world-class product UI quality

What I can assess:
- The Playwright-rendered social card HTML/CSS is decent and visually intentional, not sloppy. (`segments/social.py:169-231`)
- But it is not app frontend code.

**Conclusion:** N/A for actual frontend review from the supplied files.

---

## SECTION 5: BACKEND QUALITY

### Error handling
- Strong overall pattern: broad exception handling and degradation to filler.
- Weak point: fallback artifact creation is not guaranteed, and missing segments can be silently omitted from concat. (`segments/base.py:37-60`, `episode.py:143`)

### External API calls
- Timeouts exist for mempool.space and ElevenLabs calls. Good. (`data_segment.py:36-52`, `social.py:105`, `signal_active.py:196`, `x_spaces_segment.py:108`)
- Retries are inconsistent:
  - `_get_metric()` fallback uses `http_get(... max_attempts=2)`. (`data_segment.py:103-112`)
  - ElevenLabs inline TTS calls appear single-attempt only.
- Graceful degradation is generally present.

### Logging
- Logging is generally good and production-usable.
- `run_ffmpeg()` logs stderr tail on failure. (`helpers.py:31-45`)
- Segment logs include labels and outcomes.
- Some logs could include episode_id/segment index more consistently.

### Memory / cleanup
- No obvious memory leaks.
- Workdir artifacts and Playwright PNGs are not cleaned up. (`segments/social.py:235-240`)
- Under high volume, disk usage in workdirs may grow significantly.

### Throughput / load
- FFmpeg-heavy synchronous rendering per request is expensive.
- Playwright startup per social segment is expensive. (`segments/social.py:158-161`)
- Synchronous network fetches during render path (`_get_metric`, inline TTS) add latency and contention.
- For ~1000 concurrent users, this architecture likely needs queueing/background jobs rather than request-thread execution.

### DB operations
- No DB writes/queries shown, so cannot assess rollback/index compliance from this patch.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

Material gaps only:

1. **No deterministic artifact guarantee on failure**
   - A premium pipeline must guarantee every segment slot resolves to a valid artifact or the episode hard-fails immediately.
   - Current behavior can silently drop segments from final concat. (`segments/base.py:37-60`, `episode.py:143`)

2. **No asynchronous job orchestration / admission control**
   - For a premium product at 1000 concurrent users, rendering should be queued, deduplicated, and capacity-aware.
   - This code is still “render inline and hope.” That is prototype-grade operationally.

3. **No immutable publish gate**
   - Invalid final episodes are atomically published before final QC/contract verdict is known. (`episode.py:191-205`)
   - World-class systems publish only after all gates pass, or publish to quarantine/staging first.

4. **Inconsistent atomic-write discipline**
   - The code aspires to strong artifact integrity, but fallback paths bypass atomic rename. (`segments/base.py:34-52`, `ffmpeg_core/encode.py:41-53`)
   - Bloomberg-grade pipelines are obsessive about this.

5. **No cost controls around paid TTS**
   - Premium systems would cache, dedupe, and quota-protect generated TTS aggressively.
   - Current inline generation can burn API budget under load.

What is already strong:
- The codec/contract discipline is much better than average.
- Episode-scoped state is a solid design choice.
- The fallback philosophy is good and practical.
- `safe_text()` centralization is excellent.

---

## SECTION 7: SCORES (0-100 each)

- Backend logic:    74/100
- Frontend/UI:      20/100
- Error handling:   78/100
- Security:         72/100
- Performance:      58/100
- Law compliance:   76/100
- World-class gap:  52/100
- OVERALL:          68/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Guarantee filler artifacts are always written atomically or hard-fail the episode immediately | `segments/base.py:34-52` | direct writes to `output_path` can leave partial/missing files, and missing segments are later silently omitted from concat

P0 CRITICAL | Stop silently dropping failed segments from final concat; HOLD if any segment lacks a valid artifact | `episode.py:143-153` | production episodes can publish with missing required content and still appear “successful”

P0 CRITICAL | Do not publish final episode before final contract/QC gate passes | `episode.py:191-205` | invalid final artifacts are moved into the output directory before they are known-good

P0 CRITICAL | Remove double degradation accounting in narration post-publish failure path | `segments/narration.py:53-57` and `segments/base.py:56` | one failure can count twice, corrupting verdict logic and filler totals

P1 HIGH     | Enforce atomic writes consistently in all fallback/cache/manifest paths using `atomic_rename` | `manifest.py:74-85`, `helpers.py:317-323`, `segments/data_segment.py:55-60`, `ffmpeg_core/encode.py:41-53` | current integrity guarantees are inconsistent and violate the stated law

P1 HIGH     | Tighten `ffprobe_contract()` to strictly and independently validate all contract fields, including bitrate semantics and video codec regardless of audio presence | `helpers.py:77-165` | current contract enforcement is softer than the law and diagnostics are incomplete

P1 HIGH     | Add quota/caching/rate limiting around inline ElevenLabs generation | `segments/social.py:87-112`, `segments/signal_active.py:176-226`, `segments/x_spaces_segment.py:85-116` | concurrent renders can exhaust paid API limits and create latency spikes

P1 HIGH     | Validate/whitelist manifest file paths if manifests can be user-influenced | `manifest.py:30-37` and all segment path consumers | arbitrary local file reads are possible through untrusted path injection

P1 HIGH     | Make preflight optional-aware instead of hard-failing the whole episode on missing optional TTS/clip inputs | `preflight.py:28-43` | current behavior prevents graceful degradation and can HOLD episodes unnecessarily

P2 MEDIUM   | Validate normalized PiP outputs after generation | `helpers.py:238-279` | Law 7 depends on pre-normalized assets being correct, but success is currently inferred from file existence only

P2 MEDIUM   | Clean up Playwright-generated PNGs and transient audio artifacts after use | `segments/social.py:235-240`, `segments/signal_active.py:187-223` | workdir bloat will accumulate under load

P2 MEDIUM   | Improve segment result semantics so `encode_segment()` reports filler success explicitly | `ffmpeg_core/encode.py:31-73` | current boolean contract is confusing and easy to misuse in future changes

P2 MEDIUM   | Include episode_id and segment index in more logs for production traceability | multiple files | debugging concurrent renders will be harder than necessary

P3 LOW      | Fix stale docstring in `overlay_pip()` | `ffmpeg_core/filters.py:52-62` | implementation is correct but documentation is misleading

P3 LOW      | Remove dead code / unfinished footer data in X Spaces segment | `segments/x_spaces_segment.py:140` | indicates incomplete implementation and confuses maintainers

P3 LOW      | Normalize style/readability in `preflight.py` and other compressed files | `preflight.py:1-52` | maintainability suffers and future defects become more likely

---

## SECTION 9: THE ONE THING

Make segment failure impossible to hide: every segment must produce a valid atomic fallback artifact or the entire episode must hard-stop before concat.

---

## SECTION 10: FINAL VERDICT

Not production-ready yet. The biggest issue is artifact integrity: fallback paths are not consistently atomic, failed segments can disappear from the final concat, and the final episode is published before final QC/contract gates are known to pass. Fix those first; after that, address degradation accounting and paid API throttling.