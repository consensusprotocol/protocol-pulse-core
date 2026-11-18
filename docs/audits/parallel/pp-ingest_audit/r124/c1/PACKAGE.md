# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at 4c952568
# The change under review: git diff HEAD (working tree) of pipeline/ingest, tools/ingest_watch.py, tests/ingest

## GOVERNING LAWS (this code MUST comply with every law below: flag any violation)
Standing order (PBX 02:30 / orchestrator 02:45 ET 2026-11-12) and laws this code must obey:
- BUILD: continuous ingest of every registered partner channel (RSS first, yt-dlp metadata fallback, ~10 min, ETag /
  backoff, last-seen ledger, re-upload / duplicate detection, Shorts and live-in-progress handled explicitly, durable
  queue); captions into the SAME transcript store format via the store's writer, in a staging copy, never the main
  tree; first-pass mining by sentence ids on Heimdall (bounded concurrency, queue-aware backoff on 429/503, <= ~20 in
  flight, spend tracked vs the $460 cap with a 90 % tripwire that NOTIFIES and falls back, never halts); an
  append-only moment ledger matching pp-selectid's pp.moment/1 contract and an adapter "best unused moments since T";
  a daily coverage check; a blind A/B of back-ends (generator and judge different models).
- L-x NO SINGLE MODEL, ULTRON FIRST: every model role behind ONE provider interface with >= 2 interchangeable
  back-ends; the run continues when any one vendor is down or out of credit; no vendor / model name outside the
  provider config; the local model on Ultron is the default where it meets the bar (it runs only under the GPU0
  lease, which this builder never holds: no GPU use at all here).
- L-l a model reply counts only whole: strict schema, ids validated, NOTHING REPAIRED; a failed call is never a
  default, a pass or an agreement. L-j / L-m: fail closed; nothing measured is never a pass.
- L-h / L-k: transcript text is read as spoken (entities decoded, split tokens joined) through the repo's canonical
  form; stored records are never rewritten. L-e: word timing for anything heard (the packager's job at cut time).
- L-u hard exclusions (accusation, partner attack, buy/sell imperative, guaranteed return, single-source breaking, ad
  read, third-party media) are flagged and excluded before ranking; L-v: a moment never spans a speaker change;
  re-uploads excluded; time-sensitive language needs the original publish time.
- Secrets: keys read by name from the env file inside code; never printed, logged or written.
- SPEND FREEZE (orchestrator 05:30 ET Nov 12, until told otherwise): paid frontier vendors (OpenAI, Anthropic, xAI;
  Google by the builder's assumption) are never called by any role; the watcher's mine chain is Heimdall then the
  local interface ONLY; if both are down the videos queue and are mined later, never on a paid frontier model; Heimdall
  mining continues; the 90 % tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of STATE), never a halt.
Only report issues you can verify from the code provided. Do not speculate. Cite file:line.

## THE CHANGE UNDER REVIEW: its orders and design
# r124: the local model stays the last resort whatever the spend meter says (Nov 17, 21:3x ET)

## Why
- r123 (live since 21:31 ET Nov 17) made the chains' last back-end, the local model on GPU1 under its lease, callable.
  Its startup line then listed the callable back-ends with the LOCAL MODEL FIRST: "callable now: ['local_gemma',
  'heimdall_qwen27b', ...]", because the spend meter had not measured yet in that instant.
- Router.order (integrator B1, Nov 12; orchestrator 02:45 "fall back to the other back-ends rather than halting", 05:30
  "Heimdall mining continues"): while the spend meter is not 'ok' (90 % of the $460 cap, or no reading younger than
  60 min), the METERED back-ends move to the end of every chain, so the others go first; the metered ones are never
  taken out. Every Heimdall back-end is metered (spend_meter: true), so with the local back-end callable, an unmeasured
  or tripped meter would have sent EVERY mining, hook and spotlight request to GPU1 first (a 20 GB model load per
  request, one at a time), against ruling 118 (orchestrator 10:50 ET Nov 16): "Plan B for mining ... is the next
  Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo ...), then the local model on a free card under
  the lease. Heimdall is free and effectively unlimited for us; a video may wait minutes, never hours."
- The meter has been 'ok' at every reading of this watcher's log (never unmeasured, never tripped); its last reading,
  21:31 ET, was 12.4 % of the cap, so no request has gone to the local model. The conflict is latent; r124 closes it
  before the meter could ever go stale (60 min after its last good reading).

## The change
- pipeline/ingest/providers.py Router.order: while the meter is not 'ok', the order is [the others] + [the metered
  ones] + [the last-resort ones] (each in chain order); a back-end is last-resort when providers.json says
  "last_resort": true. Router._last_resort(bid) reads it like _metered. validate_config: "last_resort" must be a bool.
  With the meter 'ok' (or no meter), the chain is used as configured (unchanged).
- pipeline/ingest/providers.json: local_gemma "last_resort": true (and its note).
- tests/ingest/test_r124.py (new): a tripped meter keeps a last-resort back-end last and the gateway answers first; B1
  still puts another (non-metered, non-last-resort) back-end first and never takes the metered ones out; the real
  mine / hook / spotlight chains keep ruling 118's order at every meter state; a non-bool flag is refused.

## Unchanged code the change relies on (not in the diff)
- providers.py Router.effective(role) = [b for b in self.order(role) if b in backends, not frozen (unless lifted),
  enabled()]; Router.run tries `self.order(role)` (or `only`).
- spend.py CreditMeter.state(): 'unmeasured' when no reading is younger than stale_after_s (3600 s), 'tripped' at or
  above 90 % of cap_usd, else 'ok'.
- tests/ingest/test_providers.py test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out and
  test_an_unmeasured_spend_is_never_read_as_below_the_tripwire_and_never_halts (B1's own tests) pass unchanged.

## What to check
- B1 holds: the meter only notifies; a metered back-end is never removed; a non-metered, non-last-resort back-end
  still goes first while the meter is not 'ok'.
- Ruling 118's order holds at every meter state for the real chains.
- A back-end both metered and last-resort ends up last (once).

Suite: tests/ingest 443 passed (4 new in test_r124.py). Mutations M65-M68: 4 of 4 killed (M65 restores r123's order:
the tests fail on the code live now); the unmutated control passed.


```diff
diff --git a/pipeline/ingest/providers.json b/pipeline/ingest/providers.json
index ce90e3d0..2f887827 100644
--- a/pipeline/ingest/providers.json
+++ b/pipeline/ingest/providers.json
@@ -11,8 +11,8 @@
   "backends": {
     "local_gemma": {
       "kind": "ollama_local", "vendor": "ultron-gpu1", "model": "gemma3:27b", "enabled": true, "requires": "gpu1_lease",
-      "lease_wait_s": 60, "yield_s": 3, "num_ctx": 16384,
-      "note": "Ruling 118 (orchestrator 10:50 ET Nov 16 (2)): the local model on a free card under the lease, the last of the mine, hook and spotlight chains. Ultron GPU1 (law L-r's layout, PBX 2026-11-12: GPU0 renders and their gates, GPU1 everything else) through the main tree's lease client (services/gpu_lease_client.py, gpu0.ollama_call; main fb973fd0): per request the GPU1 lease within lease_wait_s, the memory proven free and a foreign user waited out within the same bound, keep_alive 0, the unload confirmed before the lease is released. A card not free within the bound is 'busy' (not retried; the videos wait). After each request that reached the card it is left free for yield_s (gpu0.lease polls every 0.2 s, ollama_call every 1 s). num_ctx: the pipeline's LocalLLM setting, at which gpu0.REQUIREMENT_MIB was measured; the longest mine prompt measured is 2,643 tokens (Nov 16-17), the role's reply budget 4,000. timeout_s: the request (the model's load and the reply).",
+      "lease_wait_s": 60, "yield_s": 3, "num_ctx": 16384, "last_resort": true,
+      "note": "Ruling 118 (orchestrator 10:50 ET Nov 16 (2)): the local model on a free card under the lease, the last of the mine, hook and spotlight chains. Ultron GPU1 (law L-r's layout, PBX 2026-11-12: GPU0 renders and their gates, GPU1 everything else) through the main tree's lease client (services/gpu_lease_client.py, gpu0.ollama_call; main fb973fd0): per request the GPU1 lease within lease_wait_s, the memory proven free and a foreign user waited out within the same bound, keep_alive 0, the unload confirmed before the lease is released. A card not free within the bound is 'busy' (not retried; the videos wait). After each request that reached the card it is left free for yield_s (gpu0.lease polls every 0.2 s, ollama_call every 1 s). num_ctx: the pipeline's LocalLLM setting, at which gpu0.REQUIREMENT_MIB was measured; the longest mine prompt measured is 2,643 tokens (Nov 16-17), the role's reply budget 4,000. timeout_s: the request (the model's load and the reply). last_resort (r124): the spend meter's reorder (integrator B1: while the meter is not ok, the metered gateway models go after the others) never moves it ahead of them; ruling 118's order stands: the next Heimdall model, then the local model.",
       "max_inflight": 1, "timeout_s": 300,
       "price": {"in_per_mtok": 0.0, "out_per_mtok": 0.0, "basis": "local"}
     },
diff --git a/pipeline/ingest/providers.py b/pipeline/ingest/providers.py
index facc37c5..3b3163ea 100644
--- a/pipeline/ingest/providers.py
+++ b/pipeline/ingest/providers.py
@@ -11,8 +11,9 @@ SPEND FREEZE (orchestrator 05:30 ET 2026-11-12): every back-end names its vendor
 spend_freeze is never called by any role, whatever its chain, `only`, or `enabled` say (a stored validated reply costs
 nothing and may still be reused). The spend meter only NOTIFIES (orchestrator 02:45; integrator B1): while it is not
 'ok' the metered back-ends move to the end of every chain, so the others go first where any are available; they are
-never taken out. AllBackendsFailed.outage tells a chain that was down or refusing (the caller waits, no try used) from
-one whose back-ends answered and were rejected.
+never taken out; a last-resort back-end (ruling 118's local model) stays after all of them (r124).
+AllBackendsFailed.outage tells a chain that was down or refusing (the caller waits, no try used) from one whose
+back-ends answered and were rejected.
 
 Keys are read by NAME from the env file named in the config, inside code; never logged, never in an exception (error
 text is redacted of every key value before it is recorded), never sent after a redirect.
@@ -113,6 +114,8 @@ def validate_config(cfg):
     for bid, b in cfg["backends"].items():
         if type(b.get("vendor")) is not str or not b["vendor"]:
             raise ValueError(f"back-end {bid}: no 'vendor' (every back-end names its vendor: the spend freeze)")
+        if "last_resort" in b and type(b["last_resort"]) is not bool:
+            raise ValueError(f"back-end {bid}: 'last_resort' must be true or false")
     fz = cfg.get("spend_freeze")
     if fz is not None and (type(fz) is not dict or type(fz.get("vendors")) is not list
                            or not all(type(v) is str and v for v in fz["vendors"])):
@@ -838,12 +841,19 @@ class Router:
     def _metered(self, bid):
         return bool((self.cfg["backends"].get(bid) or {}).get("spend_meter"))
 
+    def _last_resort(self, bid):
+        return bool((self.cfg["backends"].get(bid) or {}).get("last_resort"))
+
     def order(self, role):
         """The role's chain as tried now. While the spend meter is not 'ok' (90 % of the cap, or unmeasured) the
-        metered back-ends go last: the others first where any are available; the metered ones are never removed."""
+        metered back-ends go last: the others first where any are available; the metered ones are never removed. A
+        last-resort back-end (providers.json "last_resort": ruling 118's local model, "the next Heimdall model ...,
+        then the local model") is never moved ahead: it stays after every other back-end of the chain (r124)."""
         ch = self.chain(role)
         if self.meter is not None and self.meter.state() != "ok":
-            ch = [b for b in ch if not self._metered(b)] + [b for b in ch if self._metered(b)]
+            last = [b for b in ch if self._last_resort(b)]
+            ch = [b for b in ch if not self._metered(b) and b not in last] + \
+                [b for b in ch if self._metered(b) and b not in last] + last
         return ch
 
     def effective(self, role):
diff --git a/tests/ingest/test_r124.py b/tests/ingest/test_r124.py
new file mode 100644
index 00000000..6c22ddec
--- /dev/null
+++ b/tests/ingest/test_r124.py
@@ -0,0 +1,81 @@
+"""tests/ingest/test_r124.py: the local model stays the last resort whatever the spend meter says (ruling 118; r124).
+
+Found at r123's restart (21:31 ET Nov 17): the startup line listed the local back-end FIRST among the callable ones.
+Router.order (integrator B1, orchestrator 02:45) moves the metered back-ends after the others while the spend meter is
+not 'ok' (90 % of the cap, or no reading for an hour), and every gateway model is metered: with the local model callable
+(r123), an unmeasured meter would have sent every mining request to GPU1 first (a model load per request) against
+ruling 118's order, "the next Heimdall model ..., then the local model on a free card under the lease". A back-end
+marked last_resort now stays after every other back-end of its chain; B1 otherwise unchanged (the meter notifies, the
+metered back-ends are never taken out, others first).
+"""
+import json
+
+import pytest
+
+import helpers as H
+from pipeline.ingest import providers, spend
+
+OK = json.dumps({"ok": True})
+
+
+def validate_obj(content):
+    obj = json.loads(content)
+    if obj != {"ok": True}:
+        raise providers.Invalid("not ok")
+    return obj
+
+
+def tripped(router, h):
+    m = spend.CreditMeter(H.router_cfg(["h"])["spend_meter"], h)
+    router.meter = m
+    m.measure()                                    # 95 of a 100 cap: at 90 %, tripped
+    assert m.state() == "tripped"
+
+
+def test_a_last_resort_back_end_stays_last_while_the_meter_is_not_ok():
+    h = H.FakeBackend("h", [OK], cfg={"spend_meter": True}, usage_total=95.0)
+    h2 = H.FakeBackend("h2", [OK], cfg={"spend_meter": True})
+    loc = H.FakeBackend("loc", [OK], cfg={"last_resort": True})
+    r = H.make_router([h, h2, loc])
+    tripped(r, h)
+    assert r.order("mine") == ["h", "h2", "loc"]
+    out = r.run("mine", "p", None, validate_obj)
+    assert out.backend == "h" and loc.calls == []
+    h.fn = h2.fn = (lambda p: providers.BackendError("network", "down"))      # the gateway down: the last resort answers
+    assert r.run("mine", "p2", None, validate_obj).backend == "loc"
+
+
+def test_b1_still_puts_another_back_end_first_and_never_takes_the_metered_ones_out():
+    h = H.FakeBackend("h", [OK, OK], cfg={"spend_meter": True}, usage_total=95.0)
+    b = H.FakeBackend("b", [OK])
+    loc = H.FakeBackend("loc", [OK], cfg={"last_resort": True})
+    r = H.make_router([h, b, loc])
+    tripped(r, h)
+    assert r.order("mine") == ["b", "h", "loc"]
+    assert r.run("mine", "p", None, validate_obj).backend == "b"
+    r.meter = None                                  # no meter (or 'ok'): the configured chain as it is
+    assert r.order("mine") == ["h", "b", "loc"]
+
+
+def test_the_real_chains_keep_ruling_118s_order_whatever_the_meter_says():
+    cfg = providers.load_config()
+    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"))
+
+    class Meter:
+        def __init__(self, s):
+            self.s = s
+
+        def state(self):
+            return self.s
+    for st in ("ok", "unmeasured", "tripped"):
+        r.meter = Meter(st)
+        for role in ("mine", "hook", "spotlight"):
+            assert r.order(role) == cfg["roles"][role]["chain"], (st, role)
+            assert r.effective(role)[-1] == cfg["roles"][role]["chain"][-1], (st, role)
+
+
+def test_last_resort_must_be_true_or_false():
+    cfg = H.router_cfg(["a", "b"])
+    cfg["backends"]["b"]["last_resort"] = "yes"
+    with pytest.raises(ValueError, match="last_resort"):
+        providers.validate_config(cfg)

```

You see the diff, not the whole files: when a finding needs code outside it, say which function you need instead of
guessing.

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

