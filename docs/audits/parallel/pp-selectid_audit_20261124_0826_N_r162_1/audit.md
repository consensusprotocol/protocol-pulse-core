# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 162 (1) (orchestrator 07:45 ET Nov 24, from the owner's review of a video whose opening clip "cuts off abruptly as the speaker is still saying something"): A CLIP NEVER ENDS WHILE THE SPEAKER IS STILL MID-SENTENCE, HARD at the OUT edge; "EXTEND the out point to the sentence's end (re-check the lock and the cut on the extended span; mind the runtime), and if it cannot be extended inside the rules, the clip is REFUSED"; the IN edge stays a flag. The question is the integrator's (one file both sides load, owner_rules.out_edge: unchanged guard, not in this diff; it returns {"complete", "finishes_at", "measured"}; it calls router.call(role, prompt, max_tokens=, seed=, **call_kw) and turns only the `no_answer` exception kinds into measured False).
THE CHANGE (diff below): pipeline/out_edge.py asks it of every pool moment (package._build after usable()/reposted_once(); spotlight.build after its pool()) on the source's own sentences (around()); complete: kept with m["out_edge"]; runs on and finishes_at given: REPLACED by tail_variant.extend (a later-ending span of whole sentences, IN unchanged), asked again on its own edge; runs on otherwise, or a moment cut inside a sentence / a window record: refused; no answer: UNVERIFIED (out, never cached, never a refusal). package.out_edges then runs usable() on the extensions (the 20 s clip). package.soft_edges: an OUT edge failure is never soft. inventory() gets an "out_edge" row (PASS only when every clip's verdict is measured and complete), required on this side through OWN_REQUIRED added to the gate_problems calls (package_pin.REQUIRED_GATES unchanged). A dedicated back-end "heimdall:qwen/qwen3.8-27b@low" (model_providers.json: reasoning effort low, "plain": the user message only, min_out 2000) is the role's only member; providers.HeimdallBackend honours "plain" and "reasoning".
CHECK, quoting the code: (1) can a clip reach a sealed package (medley voiced, no-voice, spotlight) without a measured complete verdict on its OWN span (an extension, a ~trim variant made after the pass, a moment added later by a swap or the no-voice path's added clip); (2) can an exception other than ProviderError/ReplayMiss be swallowed, or an unanswered verdict be cached or counted as complete; (3) does around() give the right sentence indices for the extension (k1+1+finishes_at) and refuse every moment whose words are not whole sentences; (4) can the "plain"/"reasoning" change alter any OTHER Heimdall call's request body. Report only what the code shows; if unsure, say so.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0471
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/out_edge.py:0** A moment whose OUT edge is not at a sentence end (or which is a window record) can still be kept and sealed if the verdict is measured and complete is True. around() only suppresses extension for non-whole moments by returning ks=[], but pool() does not structurally refuse them; it keeps any measured complete verdict. The pin's out_edge row then passes because it only checks measured and complete, not that the span's OUT edge is at a sentence end.
  - evidence: `    whole = w0 == S[k0][0] and w1 == S[k1][1] and getattr(src, "window", None) is None
    if whole:
        ks = list(range(k1 + 1, min(len(S), k1 + 1 + AFTER_N)))
        return before, [E.spoken(T[`
  - fix: Enforce the hard OUT-edge rule structurally in pool(): for a measured verdict, require the OUT edge to be at a sentence end (w1 == S[k1][1] and no window) before keeping it, or extend the span to S[k1][1] when that is the ruled extension. If the span cannot be made to end at a sentence end inside the rules, refuse it instead of keeping a complete verdict.
  - raised by qwen27b:F1; agree: qwen27b, gemma

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
