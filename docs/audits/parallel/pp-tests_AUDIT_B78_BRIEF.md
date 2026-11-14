# AUDIT BRIEF — pp-tests (tests only): the integrator's audit batch 78, two consensus findings

## THE LAWS (the session's rules, the integrator's message verbatim, the house key loader, and what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md); it never edits
pipeline/, scripts/ or segment_v1/. Rules: never change what a check accepts in order to make something pass; nothing
measured is never a pass (L-m); fail closed (L-j); every pinned defect is `xfail(strict=True, raises=AssertionError)`
and every precondition is `pytest.fail` (adv_helpers.control: H.control); CPU only, no network, no GPU. Secrets: keys
are read only by NAME inside code and never printed, logged or written. Only report what you can verify from the diff
and the excerpts below. If uncertain, say so. Production code is READ-ONLY context.

### The integrator's message (2026-11-14 ~08:15 ET, verbatim essentials)
Integrator: pp-tests merge, my audit batch 78 cycle 1. Your 621604bb is verified, and the merge stays HELD on TWO
CONSENSUS findings, both verified in the code. Please fix them on your branch and send the commit.
CONSENSUS (qwen27b + glm; must be fixed):
1. baselines/frontier_blind.py:22 hard-codes ENV_FILE to the main tree's key file, and _key(name) (l.67) parses it.
   It reads one key by name and prints nothing, so it is not the "high" the panel said. It still breaks the house
   rule: read keys by NAME through the pipeline's loader, as scripts/integrator/grok_audit.py does:
   sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3"); from relay import get_key
   Never parse a key-file path hard-coded in a test directory.
2. moments_exam.py:92 refuse_network patches getaddrinfo / gethostbyname / gethostbyname_ex but NOT
   socket.gethostbyaddr, so a reverse lookup still leaves the box. Your child guard covers it; the runner's own guard
   does not. Patch it, and add one must-fail line to the runner's network test.
NOTES (one reviewer, not agreed: yours to judge, not required for the merge):
- glm: frontier_blind's preflight estimates per case (PER_CASE_USD) while _call reserves per token, so a run admitted
  by preflight can still hit BudgetExhausted mid-run.
- glm: the child guard's import-time binding caveat (a child that bound socket functions before sitecustomize ran) is
  not documented.
- glm: the import resolver in test_f0 drops a module without __file__ silently. Consider making an unscanned name
  visible.

### What pp-tests did (THE DIFF: CURRENT.diff, tests and docs only)
1. frontier_blind.py: ENV_FILE and the parser are gone. `_key(name)` returns relay.get_key(name) from the pipeline's
   loader. It loads the MAIN tree's video_pipeline_v3/relay.py, because relay finds the project's key file next to
   itself, so the worktree's copy finds none. It loads that file by path (importlib spec_from_file_location under a
   private module name), not with the sys.path.insert of grok_audit.py: the exam process imports gate modules by name,
   and the main tree's video_pipeline_v3 first on sys.path could shadow them. sys.dont_write_bytecode is set for the
   load and restored, so no __pycache__ lands in the main tree, which this session must never write. Measured: three
   keys resolve by name (only booleans printed); sys.path unchanged; a missing key raises KeyError; the main tree's
   relay .pyc has the same mtime and count after the load.
2. moments_exam.refuse_network: every name lookup, forward and reverse, now raises NetworkRefused, naming the
   function: getaddrinfo, gethostbyname, gethostbyname_ex, gethostbyaddr (the finding) and getnameinfo. getnameinfo is
   NOT in the finding: it is the other reverse lookup, missing from all three guards.
3. The runner's network test is parametrised over two toy gates: `network` (connect) and the new `network_reverse`
   (gethostbyaddr and getnameinfo alternately, one per case). Every row must be the RUNNER's refusal (`NetworkRefused:
   moments_exam: network is disabled`). The old substring "network is disabled" also matched the suite's child guard,
   which runs under the runner, and it hid the missing patch. For network_reverse, both lookups must appear among the
   rows. Measured against the runner from before the fix, with the new child guard loaded so nothing could leave the
   box: both reverse lookups passed the runner's guard and came back as ChildNetworkBlocked, so the new line fails
   there. With the fix, both came back as NetworkRefused.
4. conftest.py and child_guard/sitecustomize.py also refuse getnameinfo; test_f0's lookup test and child probe check
   it (and gethostbyaddr in the child probe).
5. The notes: (a) frontier_blind.preflight's docstring now says it is an estimate and that a run it admits can still
   stop part-way at BudgetExhausted (ERROR rows, reported); (b) the child guard documents the .pth caveat, measured
   on this interpreter; (c) test_f0's setter scan now fails, listing them, on names that have a pipeline / segment_v1
   file but resolve elsewhere or to nothing; the suite's own `conftest` is the one exception.
6. Docs: BIBLE PP-E29 (reverse lookups), PP-E30 (with layered guards, name which guard refused), PP-E31 (keys through
   the loader); XFAIL_EVIDENCE regenerated.
Measured after the diff (release line merged, CUDA_VISIBLE_DEVICES=): whole wall 422 tests = 379 passed, 40 strict
xfails, 3 skipped, 0 failed, 0 errors; --runxfail: exactly the 40 fail, each an AssertionError in its own file.

### What to check (answer each; cite the diff line)
A. frontier_blind._key: does a key now come ONLY by name through relay.get_key? Can it print, log or write a key? Is
   loading the main tree's relay.py by path (no sys.path change, bytecode off) sound, and thread-safe enough (called
   under _TLOCK from _client)? Is anything lost against grok_audit.py's import form?
B. refuse_network: are all lookups, forward and reverse, covered now? Is any other socket path still open from a gate
   in the runner's process?
C. The runner's network test: does it prove the RUNNER refused (not the child guard)? Can network_reverse pass without
   both lookups being refused by the runner?
D. conftest / child guard: is getnameinfo restored by remove() like the others? Any guard asymmetry left?
E. test_f0's unscanned-names assertion: correct? Can it fail on a benign change, or miss a dropped module?
F. Are the docs' claims (the .pth check, the preflight docstring, PP-E29..31) accurate?
G. Does anything in the diff loosen what a check accepts?

### The house key loader: video_pipeline_v3/relay.py (read-only context)
```
   1  import os
   2  """Key resolution helper for Protocol Pulse pipeline.
   3  
   4  Resolution order for every key:
   5    1. Process environment variable (os.environ)
   6    2. ~/protocol_pulse/.env file
   7    3. video_pipeline_v3/.env file (local override)
   8    4. Raise KeyError with a clear message — no network calls.
   9  
  10  Replit relay is deprecated (migrated to Ultron self-hosted Flask).
  11  The run() and query_db() stubs are kept for import compatibility but
  12  do nothing — callers should be updated to use direct DB/service calls.
  13  """
  14  import os
  15  from pathlib import Path
  16  
  17  # ── .env loader ──────────────────────────────────────────────────────────────
  18  
  19  _env_cache: dict = {}
  20  _env_loaded = False
  21  
  22  def _load_dotenv_file(path: str) -> dict:
  23      """Parse a .env file and return key→value dict (no shell expansion)."""
  24      result = {}
  25      try:
  26          with open(path) as f:
  27              for line in f:
  28                  line = line.strip()
  29                  if not line or line.startswith("#") or "=" not in line:
  30                      continue
  31                  k, _, v = line.partition("=")
  32                  k = k.strip()
  33                  v = v.strip().strip("'\"'").strip()  # strip surrounding quotes
  34                  if k:
  35                      result[k] = v
  36      except FileNotFoundError:
  37          pass
  38      return result
  39  
  40  def _load_env():
  41      global _env_cache, _env_loaded
  42      if _env_loaded:
  43          return
  44      base = Path(__file__).resolve().parent
  45      # Load root .env first, then pipeline-local .env (local wins)
  46      root_env   = base.parent / ".env"           # ~/protocol_pulse/.env
  47      local_env  = base / ".env"                  # video_pipeline_v3/.env
  48      merged = {}
  49      merged.update(_load_dotenv_file(str(root_env)))
  50      merged.update(_load_dotenv_file(str(local_env)))
  51      _env_cache = merged
  52      _env_loaded = True
  53  
  54  # ── Public API ───────────────────────────────────────────────────────────────
  55  
  56  def get_key(name: str, required: bool = True) -> str:
  57      """Return the value of an API key.
  58  
  59      Checks (in order):
  60        1. os.environ   — set by systemd unit, Docker, or manual export
  61        2. .env files   — ~/protocol_pulse/.env then video_pipeline_v3/.env
  62  
  63      Args:
  64          name:     Environment variable name, e.g. "ELEVENLABS_API_KEY"
  65          required: If True (default), raises KeyError when key is missing.
  66                    If False, returns empty string instead.
  67      """
  68      # 1. Live environment
  69      val = os.environ.get(name, "")
  70      if val:
  71          return val
  72  
  73      # 2. .env files
  74      _load_env()
  75      val = _env_cache.get(name, "")
  76      if val:
  77          return val
  78  
  79      if required:
  80          raise KeyError(
  81              f"[relay] API key \'{name}\' not found.\n"
  82              f"  Add it to ~/protocol_pulse/.env or export it before running the pipeline.\n"
  83              f"  Example:  echo \'ELEVENLABS_API_KEY=sk-...\' >> ~/protocol_pulse/.env"
  84          )
  85      return ""
  86  
  87  def reload_env():
  88      """Force re-read of .env files (useful after adding keys at runtime)."""
  89      global _env_loaded
  90      _env_loaded = False
  91      _load_env()
```

### The house pattern: scripts/integrator/grok_audit.py (head)
```
   1  """Cycle-2 audit reviewer on xAI Grok (orchestrator 21:10: the audit law's reviewers include Grok; the xAI key is fenced
   2  to the pipeline and LLM audits). Sends EXACTLY the messages Heimdall sent its panel (read from a raw_c1_*.json request),
   3  writes the raw answer next to Heimdall's, prints the verdict and the vendor-reported cost. The key is read by name from
   4  the repo's environment file and never printed.
   5  Usage: python3 grok_audit.py <raw_c1_qwen27b.json> <out.json> [model]"""
   6  import json
   7  import sys
   8  import time
   9  import urllib.request
  10  
  11  src, out = sys.argv[1], sys.argv[2]
  12  model = sys.argv[3] if len(sys.argv) > 3 else "grok-4-0709"
  13  with open(src) as f:
  14      req = json.load(f)["request"]
  15  sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
  16  from relay import get_key  # noqa: E402  (the pipeline's key loader, as pipeline/signoff.py: read by name, never printed)
  17  key = get_key("XAI_API_KEY_MEDLEY")
  18  body = {"model": model, "messages": req["messages"], "temperature": 0, "max_tokens": 8192}
  19  t = time.time()
  20  r = urllib.request.Request("https://api.x.ai/v1/chat/completions", data=json.dumps(body).encode(),
```
