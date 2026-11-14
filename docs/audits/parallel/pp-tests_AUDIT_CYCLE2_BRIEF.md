# AUDIT BRIEF — pp-tests (tests only): the integrator's merge cycle 2 (three wall failures against law L-r)

## THE LAWS (the session's rules, the integrator's message verbatim, law L-r's code, and what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md); it never edits
pipeline/, scripts/ or segment_v1/. Rules: never change what a check accepts in order to make something pass; nothing
measured is never a pass (L-m); fail closed (L-j); every pinned defect is `xfail(strict=True, raises=AssertionError)`
and every precondition is `pytest.fail` (adv_helpers.control: H.control), so a broken setup shows FAILED, never as the
defect; CPU only (no GPU at all: GPU0 belongs to the live run), no network. Only report what you can verify from the
diff and the excerpts below. If uncertain, say so. Production code is READ-ONLY context: findings about it count only
where they bear on whether a TEST is right.

### The integrator's message (2026-11-14 ~07:00 ET, verbatim essentials)
pp-tests merge, cycle 2. Your B1-B4 answers are VERIFIED in the code; the merge is HELD on 3 test-wall failures
against today's release line. THE RUN: merge worktree (your branch merged into release HEAD 6d7d4287, which now
includes law L-l and law L-r's GPU leases, pipeline/gpu0.py): `CUDA_VISIBLE_DEVICES= python3 -m pytest
tests/adversarial -q` -> 375 passed, 39 xfailed, 3 skipped, 3 FAILED. All three are your CPU-guard design meeting L-r:
1. test_f0_cpu_guard::test_no_module_this_suite_imports_sets_cuda_visible_devices_unreviewed: {'conftest',
   'qa_gates'} != {'qa_gates'}. pipeline/conftest.py is L-r's E-FAIL-053 fix (pytest_runtest_teardown) and sets the
   variable on purpose.
2. test_f0_cpu_guard::test_every_whisper_load_is_refused_and_recorded: "DID NOT RAISE RuntimeError". Today a Whisper
   load first meets gpu0.require/swap_to, which raises gpu0.LeaseMissing ("whisper:large-v3: GPU0 loads need
   CUDA_VISIBLE_DEVICES=0 (it is '')"), before your guard is reached.
3. test_f2_provenance::TestDirtyCache::test_a_failed_transcription_stops_select_cleanly: select's "Transcribing 3
   sources..." hits that same LeaseMissing at pipeline/gpu0.py:287 before your mocked transcription failure. Please
   decide whether the test should fake the failure below the lease, or whether you see a real defect: select not
   stopping cleanly on a lease refusal. If the latter, file it as a request; do not loosen the lease.

### What pp-tests did (the diff under audit is the second step only)
1. Merged the release line (combo-letterbox-quoteonly-v2 4286d879 = 6d7d4287 + one docs-only DoD commit) into the
   pp-tests branch, so the wall is fixed against the code it will run on. A clean merge (no conflict): its tree equals
   the integrator's own merge cc8cccd0 plus the two docs files of 4286d879 (`git diff --stat cc8cccd0 HEAD` shows only
   those). No content of pp-tests is in that merge commit.
2. THE DIFF (CURRENT.diff): tests and docs only.
   - Failure 1: the setter scan resolved each imported NAME to `pipeline/<name>.py` by file name; the suite's own
     `import conftest` (tests/adversarial/conftest.py) matched pipeline/conftest.py, which this suite never imports.
     Now `_resolve(name)`: the module already imported under that name (`sys.modules[name].__file__`), else
     `importlib.util.find_spec(name)` on the suite's sys.path; a control asserts `conftest` resolves to the suite's
     own file. Measured on the merged tree: the old resolution found 18 modules and setters {conftest, qa_gates}; the
     new one 17 modules, setters {qa_gates}; the only name that changed is `conftest`; every other name resolves to the
     same file; the setter regex still matches pipeline/conftest.py's text. KNOWN_CUDA_SETTERS stays {"qa_gates"}.
   - Failure 2: word_diff.Transcriber is lazy under L-r (constructing it loads nothing). The test now asserts both
     layers: a direct faster_whisper load hits the stub (RuntimeError 'forbidden', recorded); G18's default
     transcriber, at its first USE (span on a 1 s ffmpeg tone), raises gpu0.LeaseMissing with the exact message, the
     stub records nothing more, and the gpu0 Whisper model is not loaded.
   - Failure 3 (R-27): the ordinary transcription failure is injected at select's own seam: `_whisper_transcribe`
     returns None for the hook (its documented failure value); the other sources go to the real function (their
     transcripts are cached). The pin still fails on the real defect: re-measured `KeyError: 'VIDAAAAAAAA'` at
     select_passages.py:314 (`_source_for` reads `transcripts[vid]` for a downloaded source whose transcription
     failed). A KeyError raised before the hook's transcription was attempted is a control failure.
   - The integrator's question: a lease refusal during select's transcription is L-r's DESIGN (a Gpu0Stop is a
     BaseException that passes every `except Exception` up to run_fresh's stage runner, which HOLDs), not a crash. A
     new PASSING test pins it: select raises gpu0.LeaseMissing (exact message), writes no edl.json and no transcript,
     and nothing reaches faster_whisper. No request filed for it.
   - R-10's pin (not failing today, but would have errored on its fix under L-r): its proof that the new bytes went to
     Whisper is now the LeaseMissing naming a `whisper:` key (before: the stub's record, which L-r never reaches).
   - Docs: REQUESTS R-10 / R-27 notes, a new R-29 (the builder's exam adapter predates vo_fidelity v1.1: it never
     passes `title` or `universe` to the gate), BIBLE_ADDITIONS PP-E26..E28, COVERAGE note, XFAIL_EVIDENCE
     regenerated.
   Measured after the diff, merged tree: whole wall 378 passed, 40 strict xfails, 3 skipped, 0 failed; with
   --runxfail exactly the 40 fail, each an AssertionError in its own test file; regression_test.sh 26 PASS / 0 FAIL.

### What to check (answer each; cite the diff line)
A. Does `_resolve` give the file the suite really imports for every name the scan sees? Name a case where it would
   differ (sys.path order: segment_v1/, pipeline/, tests/adversarial/ are put first by the conftest; pytest registers
   the suite's conftest as `conftest`). Is the scan at least as strict as before for pipeline / segment_v1 modules?
B. Can test_every_whisper_load_is_refused_and_recorded pass while a Whisper model loads, or while the lease is
   bypassed? Is anything it asserts vacuous?
C. R-27: is `_whisper_transcribe -> None` a faithful stand-in for an ordinary transcription failure in production
   (read the function: which failures return None, which raise)? Can the pin flip (XPASS) without R-27's fix, or stay
   failing after a correct fix?
D. The new passing test: is "a Gpu0Stop leaves select at once" the right expectation under L-r? Is a request needed
   anyway (partial state, a missing HOLD reason)? Is any assertion vacuous?
E. R-10: can the pin XPASS without R-10's fix (e.g. a LeaseMissing that is not the re-transcription)? Can a correct
   fix still leave it failing?
F. R-29: verify its claims against the adapter excerpt below.
G. Anything in the diff that loosens what a check accepts.

### Law L-r: pipeline/gpu0.py (release line), module docstring
```
   2  """pipeline/gpu0.py — law L-r GPU0 NEVER SURPRISES A RUN (orchestrator 2026-11-12 '01:55' B; PBX on the pinned run's
   3  out-of-memory: "let's make sure that never happens again").
   4  
   5  ONE OWNER. GPU0 belongs to whoever holds the lease: an exclusive flock on the lease file (/tmp/pulse_gpu0.lease; the
   6  environment variable PP_GPU0_LEASE overrides it), the holder recorded in the file. Entry points take it:
   7  scripts/pulse_check_run.sh on fd 8 for the whole run (preflight and run_fresh inherit that descriptor), and run_fresh,
   8  replay, preflight, backtest and GPU test sessions with lease() when started on their own. held() is a check, never an
   9  acquisition: true in a process that took the lease with lease(), or that holds a descriptor whose open file description
  10  holds the flock while it is held (a private probe first proves the lock is held at all; a second flock then succeeds
  11  only on the holding description). require() runs before every load AND every use of a loaded model: no lease, no load.
  12  
  13  ONE MODEL AT A TIME. swap_to(key) is the one way anything gets onto GPU0. It refuses a foreign GPU0 user, unloads
  14  everything else this run has resident (its Model objects; its models on the GPU0 Ollama via keep_alive=0, confirmed on
  15  /api/ps), collects garbage and empties torch's cache, then waits until nvidia-smi shows GPU0 free >= REQUIREMENT_MIB[key]
  16  + MARGIN_MIB (MARGIN_MIB alone for a model already resident), re-checking for a foreign user while it waits. A Model
  17  (whisper(), model()) loads through swap_to on first use, is deleted by any later swap, and loads again through swap_to
  18  when used again; its calls re-resolve the live object and run inside guard(). The GPU0 work of a run is done from one
  19  thread (the PeakSampler only reads nvidia-smi).
  20  
  21  FOREIGN. Not this run's: a GPU0 compute process other than this process, its descendants and the processes holding the
  22  lease file open (the wrapper that holds it); a model resident on the shared GPU0 Ollama that this process did not
  23  request; GPU0 memory no listed process accounts for, beyond UNLISTED_MAX_MIB. A foreign user is named and the run HOLDs;
  24  nothing of it is unloaded or killed.
  25  
  26  EVERY GPU HAS ONE OWNER AT A TIME (PBX 2026-11-12, the GPU1 quarantine lifted; orchestrator '22:50'). GPU0 = renders
  27  and the gates that need render-side models (NVENC, the face detector / vision gates, gemma for the editorial gate); GPU1
  28  = everything else (the word-pass worker, the website's Ollama fallback, the watchdog / morning brief / stage broadcast
  29  models, local A/B runs). Each GPU has its own lease (/tmp/pulse_gpu<N>.lease, PP_GPU<N>_LEASE) and its own Ollama
  30  (:11434 on GPU0, :11435 on GPU1); everything above holds per GPU. A process that loads models itself works on ONE GPU,
  31  the one its CUDA_VISIBLE_DEVICES names ('0' or '1'); every function here reads that GPU (current_gpu()). A caller that
  32  only asks a GPU's Ollama (it loads nothing itself: the watchdog, the website) uses ollama_call(gpu, ...). Some Ollama
  33  keys are pinned to one GPU (ON_GPU). A named CO-TENANT within its cap (CO_TENANTS: the website's own CUDA context on
  34  GPU1) is reported, not foreign; the free-memory proof still counts its memory.
  35  
  36  STOPS. Every refusal is a Gpu0Stop, a BaseException, so no `except Exception` between a load and the stage runner can
  37  turn it into another error ('transcription failed' hid an out-of-memory on Nov 12, E-FAIL-052): GpuOOM (a CUDA / NVENC
  38  out-of-memory inside guard() or a finished subprocess), Gpu0Foreign, LeaseMissing, LeaseBusy, Gpu0NotFree (the memory
  39  did not come free in time), Gpu0Unreadable (nvidia-smi, ss or the Ollama listener cannot be read: never 'nothing
  40  there'). run_fresh's stage runner owns the one retry of an out-of-memory and turns every other stop into a HOLD."""
```

### pipeline/gpu0.py: the stop classes, current_gpu, require
```
  87  class Gpu0Stop(BaseException):
  88      """A GPU0 refusal. A BaseException on purpose: it passes every `except Exception` up to the stage runner."""
  89  
  90  
  91  class GpuOOM(Gpu0Stop):
  92      """A CUDA / NVENC out-of-memory (the original exception, when there is one, is its __cause__)."""
  93  
  94  
  95  class Gpu0Foreign(Gpu0Stop):
  96      """GPU0 is used by something that is not this run's."""
  97  
  98  
  99  class LeaseMissing(Gpu0Stop):
 100      """A GPU0 load or use in a process that does not hold the lease (or not on GPU0 only)."""
 101  
 102  
 103  class LeaseBusy(Gpu0Stop):
 104      """Another owner holds the lease."""
 105  
 106  
 107  class Gpu0NotFree(Gpu0Stop):
 108      """The memory a load needs did not come free in time."""
 109  
 110  
 111  class Gpu0Unreadable(Gpu0Stop):
 112      """nvidia-smi, ss or the GPU0 Ollama listener cannot be read."""
...
 131  def current_gpu():
 132      """The GPU these calls act on: inside ollama_call, the GPU it was given; otherwise this process's own, named by its
 133      CUDA_VISIBLE_DEVICES ('1' is GPU1; anything else, a CPU session included, reads GPU0's lease and listener)."""
 134      g = getattr(_tls, "gpu", None)
 135      if g is not None:
 136          return g
 137      return 1 if os.environ.get("CUDA_VISIBLE_DEVICES") == "1" else 0
...
 280  def require(what, in_process=True):
 281      """No lease, no load (law L-r: every GPU has one owner at a time). An in-process load (torch, Whisper, NVENC) also
 282      needs CUDA_VISIBLE_DEVICES to name exactly the lease's GPU ('0' or '1': CUDA device 0 is then that nvidia-smi GPU;
 283      one GPU per process); a load inside a GPU's own Ollama server (keys 'ollama:') needs only that GPU's lease."""
 284      g = current_gpu()
 285      if in_process:
 286          if os.environ.get("CUDA_VISIBLE_DEVICES") != str(g):
 287              raise LeaseMissing(f"{what}: GPU{g} loads need CUDA_VISIBLE_DEVICES={g} (it is "
 288                                 f"{os.environ.get('CUDA_VISIBLE_DEVICES')!r}; one GPU per process)")
 289          if os.environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID":
 290              raise LeaseMissing(f"{what}: CUDA_DEVICE_ORDER must be PCI_BUS_ID (CUDA device 0 = nvidia-smi GPU {g})")
 291      if not held():
 292          raise LeaseMissing(f"{what}: a GPU{g} load without the GPU{g} lease (law L-r: no lease, no load); "
 293                             f"holder: {holder()}")
 294  
```

### pipeline/gpu0.py: Model, Whisper, whisper()
```
 786  class Model:
 787      """A GPU0 object loaded only through swap_to (see the module docstring). Every use checks the lease; a call
 788      re-resolves the live object (a later swap deleted it: it loads again through swap_to) and runs inside guard();
 789      only plain values (str, int, float, bool, None) of the object are readable directly."""
 790  
 791      def __init__(self, key, build):
 792          self.key, self._build, self._obj = key, build, None
 793  
 794      def get(self):
 795          require(self.key)
 796          with _lock:
 797              if self._obj is None:
 798                  swap_to(self.key)
 799                  with guard(f"{self.key}: load"):
 800                      self._obj = self._build()
 801                  _resident.append(self)
 802              return self._obj
 803  
 804      def unload(self):
 805          with _lock:
 806              self._obj = None
 807              if self in _resident:
 808                  _resident.remove(self)
 809  
 810      @property
 811      def loaded(self):
 812          return self._obj is not None
 813  
 814      def __getattr__(self, name):
 815          if name.startswith("_"):
 816              raise AttributeError(name)
 817          attr = getattr(self.get(), name)
 818          if callable(attr):
 819              del attr                                     # no stale reference: each call re-resolves the live object
 820              key = self.key
 821  
 822              def call(*a, **k):
 823                  obj = self.get()
 824                  with guard(f"{key}: {name}"):
 825                      return getattr(obj, name)(*a, **k)
 826              return call
 827          if isinstance(attr, (str, int, float, bool, type(None))):
 828              return attr
 829          raise AttributeError(f"gpu0.Model {self.key}: {name!r} is an object inside the model; reach the model only "
 830                               f"through its calls (law L-r: nothing may keep it alive past a swap)")
 831  
 832      def __call__(self, *a, **k):
 833          obj = self.get()
 834          with guard(f"{self.key}: call"):
 835              return obj(*a, **k)
 836  
 837  
 838  class Whisper(Model):
 839      def transcribe(self, *a, **k):
 840          obj = self.get()
 841          with guard(f"{self.key}: transcribe"):
 842              segments, info = obj.transcribe(*a, **k)
 843          del obj
 844          return guard_iter(iter(segments), f"{self.key}: decode"), info
 845  
 846  
 847  _models = {}
 848  
 849  
 850  def whisper(name, batched=False):
 851      """The process's one faster-whisper model `name` (float16 on GPU0; batched = a BatchedInferencePipeline)."""
 852      key = f"whisper:{name}" + (":batched" if batched else "")
 853      with _lock:
 854          if key not in _models:
 855              def build():
 856                  from faster_whisper import WhisperModel
 857                  m = WhisperModel(name, device="cuda", compute_type="float16")
 858                  if batched:
 859                      from faster_whisper import BatchedInferencePipeline
 860                      m = BatchedInferencePipeline(model=m)
 861                  return m
 862              _models[key] = Whisper(key, build)
 863          return _models[key]
```

### pipeline/select_passages.py: _whisper_transcribe, the transcription loop, _source_for
```
  71  def _whisper_transcribe(source_path, video_id, run_dir):
  72      """Run faster-whisper on a source file for word-level timestamps (verbatim decode). Where that
  73      decode has no punctuation, sentence punctuation is added from a prompted reference decode of the
  74      same audio, onto aligned words only (pipeline/punctuation.py; the words never change).
  75  
  76      Returns dict with 'words' list or None on failure.
  77      """
  78      import punctuation
  79      transcript_path = os.path.join(run_dir, "transcripts", f"{video_id}.json")
  80      os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)
  81  
  82      try:
  83          result = None
  84          if os.path.exists(transcript_path):
  85              with open(transcript_path) as f:
  86                  result = json.load(f)
  87              if result.get("punctuation") or not punctuation.needs_restoration(result.get("words", [])):
  88                  return result
  89  
  90          import gpu0
  91          model = gpu0.whisper("large-v3")      # L-r: loaded through swap_to; a GPU0 stop passes the except below
  92          if result is None:
  93              segments, info = model.transcribe(
  94                  source_path, language="en", beam_size=5,
  95                  word_timestamps=True, vad_filter=False,
  96              )
  97              words = []
  98              for seg in segments:
  99                  if seg.words:
 100                      for w in seg.words:
 101                          words.append({
 102                              "word": w.word.strip(),
 103                              "start": round(w.start, 3),
 104                              "end": round(w.end, 3),
 105                              "probability": round(w.probability, 3),
 106                          })
 107              result = {"words": words, "language": info.language,
 108                        "duration": info.duration}
 109          result = punctuation.ensure(result, source_path, model, model_name="large-v3")
 110          with open(transcript_path, "w") as f:
 111              json.dump(result, f, indent=2)
 112          return result
 113  
 114      except Exception as e:
 115          import gpu0
 116          if gpu0.is_oom(e):           # L-r: an out-of-memory is never 'transcription failed' (E-FAIL-052)
 117              raise gpu0.GpuOOM(f"{video_id}: Whisper: CUDA out of memory ({type(e).__name__}: {str(e)[:200]})") from e
 118          print(f"    WARN: whisper failed for {video_id}: {e}")
 119          return None
...
 186      if len(sources) < 2:
 187          print("  Not enough sources downloaded — STOP")
 188          return False
 189  
 190      # Transcribe each source with faster-whisper
 191      print(f"  Transcribing {len(sources)} sources...")
 192      transcripts = {}
 193      for vid, path in sources.items():
 194          result = _whisper_transcribe(path, vid, run_dir)
 195          if result:
 196              transcripts[vid] = result
 197              print(f"    {vid}: {len(result.get('words', []))} words")
 198          else:
 199              print(f"    {vid}: FAILED")
 200  
 201      # Filter chosen passages to those with successful downloads + transcripts
 202      valid = [p for p in chosen if p["video_id"] in sources and p["video_id"] in transcripts]
 203      if len(valid) < 2:
 204          print("  Not enough valid passages — STOP")
 205          return False
...
 303      def _source_for(p):
 304          vid = p["video_id"]
 305          if vid not in sources:
 306              res = _download_window(vid, p["start"], p["end"], run_dir)
 307              if not res or not res[0]:
 308                  return "download failed"
 309              sources[vid], offsets[vid] = res
 310              tr = _whisper_transcribe(sources[vid], vid, run_dir)
 311              if not tr:
 312                  return "transcription failed"
 313              transcripts[vid] = tr
 314          span = transcripts[vid].get("duration") or 0
 315          if span and not (offsets[vid] + 1.0 <= p["start"] and p["end"] <= offsets[vid] + span - 1.0):
 316              return "outside the downloaded window"
 317          return None
```

### pipeline/word_diff.py: Transcriber
```
 118  class Transcriber:
 119      def __init__(self):
 120          import gpu0
 121          self.model = gpu0.whisper(ASR["model"])      # L-r: loaded through swap_to on first use
 122  
 123      def span(self, media, t0, t1):
 124          if t1 - t0 < 0.05:
 125              return ""
 126          with tempfile.TemporaryDirectory(prefix="g18_") as tmp:
 127              wav = os.path.join(tmp, "span.wav")
 128              subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", media,
 129                              "-vn", "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
 130              segs, _ = self.model.transcribe(wav, language=ASR["language"], beam_size=ASR["beam_size"],
 131                                              word_timestamps=ASR["word_timestamps"], vad_filter=ASR["vad_filter"])
 132              return " ".join(w.word.strip() for s in segs for w in (s.words or []))
```

### pipeline/conftest.py (release line; NOT loaded by `pytest tests/adversarial`)
```
   1  """pytest and GPU0 (law L-r ONE OWNER, pipeline/gpu0.py). Decided once, before collection:
   2    unset, '' or '-1'                a CPU session: takes nothing, hides every GPU (CUDA_VISIBLE_DEVICES=''); a GPU0 load in
   3                                     it is refused (gpu0.require), and a CUDA context of it on GPU0 stops the session
   4    '0'                              a GPU session, GPU0 only: holds the GPU0 lease for the whole session, or stops at
   5                                     once with exit 75 naming the holder (a run or another session has GPU0)
   6    '1'                              a GPU session, GPU1 only: the same with the GPU1 lease (law L-r: every GPU has
   7                                     one owner at a time)
   8    anything else ('0,1', ...)       refused (exit 2): one GPU per session"""
   9  import os
  10  import sys
  11  
  12  import pytest
  13  
  14  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # gpu0 lives next to this file
  15  
  16  _CVD = os.environ.get("CUDA_VISIBLE_DEVICES")
  17  _CPU = _CVD in (None, "", "-1")
  18  _LEASE = []
  19  if _CPU:
  20      import tempfile
  21      os.environ["CUDA_VISIBLE_DEVICES"] = ""            # unset would show every GPU to the libraries: hide them all
  22      # and a private lease file: code under test that enters gpu0.lease() (preflight.main, replay) never takes or blocks
  23      # the production GPU0 lease from a CPU session (Nov 12: test_preflight briefly held /tmp/pulse_gpu0.lease)
  24      _private = tempfile.mkdtemp(prefix="pp_cpu_session_")
  25      os.environ["PP_GPU0_LEASE"] = os.path.join(_private, "gpu0.lease")
  26      os.environ["PP_GPU1_LEASE"] = os.path.join(_private, "gpu1.lease")   # neither real lease, GPU1's included
  27  
  28  
  29  def pytest_configure(config):
  30      if _CPU:
  31          return
```

### The builder's adapter (origin/pp-selectid aef73873, pipeline/moments_gate_adapter.py): vo_fidelity
```
 102  @_measured
 103  def vo_fidelity(case):
 104      man = case.get("manifest") or {}
 105      segments = {}
 106      for s in case["segments"]:                  # a speaker is named only when the case states it (law L-v 1)
 107          segments[s["label"]] = {"show": s["channel"], "speaker": s.get("speaker") or None,
 108                                  "names": [s["speaker"]] if s.get("speaker") else [], "video_id": s["video_id"],
 109                                  "text": _join(s["sentences"])}
 110      lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
 111               for i, ln in enumerate(case["lines"])]
 112      levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
 113      try:
 114          res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
 115      except P.ReplayMiss as e:
 116          raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
 117      if not res["deterministic"]["ok"]:
 118          return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}"
 119                                                       for v in res["deterministic"]["violations"])[:600]}
 120      if not res.get("measured"):
 121          raise GateNotMeasured("; ".join(v["detail"] for v in res["verdict"]["violations"])[:300])
 122      if res["ok"]:
 123          return {"verdict": "pass", "why": "every claim bound to its speaker's words; verdict yes with verbatim support"}
 124      return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}
```
The v1.1 stale-price cases: stale_price_title__01 ('Bitcoin ran from 16K to 126K') and __02 ('Bitcoin holds 76K'): bad_line null, bad_title true; stale_price_line__01: bad_line 1 ('And Bitcoin is still holding seventy-six thousand.'), rule 'B: stale against the universe (present tense)'. v1.1 cases carry `title`, `universe` {built_at, date, news, use} and `lines[i].after`; no case carries `current_levels`.
