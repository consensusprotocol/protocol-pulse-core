"""pipeline/out_edge.py -- RULING 162 (1) (orchestrator 07:45 ET Nov 24, from PBX's review of pin afd8977d at 07:37:
"the first segment cuts off abruptly as the speaker is still saying something"), STANDING, BOTH SIDES, HARD at the OUT
edge: A CLIP NEVER ENDS WHILE THE SPEAKER IS STILL MID-SENTENCE (or mid-thought). "When the checker hears the sentence
carry on past the clip's last word: EXTEND the out point to the sentence's end (ruling 104's tail variant; re-check the
lock and the cut on the extended span; mind the runtime), and if it cannot be extended inside the rules, the clip is
REFUSED." The IN edge stays a flag as ruled (package.soft_edges).

THE QUESTION is the integrator's, ONE file both sides load (owner_rules.out_edge: "does the clip's last sentence finish
the speaker's thought, given what the speaker says next?"); the render asks it again at validate and holds. This module
asks it of every moment of a build's pool on the source's OWN sentences (the BEFORE_N before the clip, the AFTER_N after
it), on the render's model and settings (role "out_edge": heimdall qwen at effort low, the user message only), and:
  - complete: the moment stays, its verdict on it (m["out_edge"], sealed on the pin's "out_edge" row);
  - runs on, a following sentence finishes it: the moment is REPLACED by its extension ending at that sentence's end
    (tail_variant.extend: a new span, recorded as derived from its parent; every gate judges it again from the start:
    the pool's own rules (package.usable, the 20 s clip), step A, the second pass and CUTTABLE at the new OUT, vision,
    the lock pre-check), asked this question again on its own new edge;
  - runs on and nothing listed finishes it, or its extension runs on too, or it cannot be extended: REFUSED;
  - no answer (or no word record, or the file missing): UNVERIFIED (ruling 160 (2a)): never a pass, never a refusal;
    out of this build, asked again next build (an unanswered verdict is never cached)."""
import hashlib
import json
import os
import threading
import types
from concurrent.futures import ThreadPoolExecutor

import eligibility as E

OWNER_RULES = "/home/ultron/protocol_pulse/pipeline/owner_rules.py"   # the integrator's file, read only
ROLE = "out_edge"                 # model_providers.json: the render's model, the render's way (no other model)
BEFORE_N, AFTER_N = 2, 3          # what the render asks with: the 2 sentences before the clip, the 3 after it
DEADLINE_S = 300.0                # the render's HeimdallText timeout
SEED = 7
RULING = "162 (1)"
_LOCK = threading.Lock()
_RULES = {}


def rules(path=None):
    """The integrator's owner_rules, loaded by FILE PATH under a name of its own (this tree has modules of its own
    names) from the very bytes hashed, so the sha sealed is the code that asked. -> (module, sha256 hex). OSError when
    the file is missing: no question, so every clip is UNVERIFIED (pool())."""
    p = path or OWNER_RULES
    with open(p, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    with _LOCK:
        mod = _RULES.get((p, sha))
        if mod is None:
            mod = types.ModuleType(f"owner_rules_{sha[:12]}")
            mod.__file__ = p
            exec(compile(raw, p, "exec"), mod.__dict__)              # noqa: S102  the integrator's file, as hashed
            _RULES[(p, sha)] = mod
    return mod, sha


def around(m, src):
    """What the question is asked with, from the moment's own Source: (the text before the clip: up to BEFORE_N
    sentences, [up to AFTER_N following sentences, each its own text], [the source sentence index each of those ends
    with, or [] when no extension can follow them]). An extension keeps the IN edge, so it exists only for a moment of
    whole sentences on a Source of its own (not a window record: its sentences stop at the window)."""
    k0, k1 = m["sentences"]
    w0, w1 = m["words"]
    S, T = src.sentences, src.tokens
    before = E.spoken(T[S[max(0, k0 - BEFORE_N)][0]:w0]) if w0 > S[max(0, k0 - BEFORE_N)][0] else ""
    whole = w0 == S[k0][0] and w1 == S[k1][1] and getattr(src, "window", None) is None
    if whole:
        ks = list(range(k1 + 1, min(len(S), k1 + 1 + AFTER_N)))
        return before, [E.spoken(T[S[k][0]:S[k][1] + 1]) for k in ks], ks
    nxt = []                                          # cut inside a sentence, or a window record: the words after the
    if w1 < S[k1][1]:                                 # clip as far as its sentence goes, then whole sentences; no
        nxt.append(E.spoken(T[w1 + 1:S[k1][1] + 1]))   # extension is made from them
    k = k1 + 1
    while len(nxt) < AFTER_N and k < len(S):
        nxt.append(E.spoken(T[S[k][0]:S[k][1] + 1]))
        k += 1
    return before, nxt, []


def _key(m, sha, before, nxt):
    d = hashlib.sha256(json.dumps([m.get("text") or "", before, nxt]).encode()).hexdigest()[:16]
    return f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{sha[:16]}:{d}"


def load_cache(path):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(path, cache):
    if not path:
        return
    tmp = f"{path}.{os.getpid()}.tmp"
    with _LOCK:
        with open(tmp, "w") as f:
            json.dump(cache, f, indent=1, sort_keys=True)
        os.replace(tmp, path)


def ask(router, m, src, cache=None, path=None):
    """The out-edge verdict on ONE moment (cached by moment, span, the rules file's sha and the texts asked with): the
    integrator's out_edge() on this router's role "out_edge". -> {"complete", "finishes_at", "why", "backend",
    "measured", "version", "sha256", "next": the sentences asked with, "ks": their source indices, "cached"}. Only
    the router's no-answer errors are unmeasured; any other error propagates (the spend stop)."""
    import providers as P
    OR, sha = rules(path)
    before, nxt, ks = around(m, src)
    key = _key(m, sha, before, nxt)
    hit = (cache or {}).get(key) if cache is not None else None
    if isinstance(hit, dict) and hit.get("measured") is True:
        return dict(hit, cached=True)
    v = OR.out_edge(router, m.get("text") or "", before, nxt, seed=SEED, role=ROLE,
                    no_answer=(P.ProviderError, P.ReplayMiss), deadline_s=DEADLINE_S)
    out = dict(v, sha256=sha, next=nxt, ks=ks, cached=False)
    if cache is not None and out.get("measured") is True:          # an unanswered verdict is never cached
        with _LOCK:
            cache[key] = {k: x for k, x in out.items() if k != "cached"}
    return out


def sealed(v):
    """The part of a verdict the pin's "out_edge" row seals: never the texts asked with."""
    return {k: v.get(k) for k in ("complete", "why", "backend", "measured", "version", "sha256")}


def pool(router, ms, sources, ctx, cache_path=None, log=print, extend=None, workers=4, path=None, admit=None):
    """RULING 162 (1) on a build's pool (see the module). -> (the moments that may play, each carrying "out_edge", the
    extensions in their parents' places; the record {"version", "sha256", "asked", "complete", "extended": {parent:
    extension}, "refused": {id: why}, "unverified": {id: why}}). extend(m, src, k, ctx, why): tail_variant.extend.
    ITEM 3 (orchestrator 09:45 ET Nov 24, final): "the deterministic edge check runs first": the caller passes only
    moments the second recogniser's OUT edge already passed, and admit(extension) -> (ok, why) puts every extension
    through the pool's rules, step A and that deterministic check BEFORE its own question (None: refused, no
    extension is made without them)."""
    import context_integrity as CI
    if extend is None:
        import tail_variant as TV
        extend = TV.extend
    rec = {"ruling": RULING, "version": None, "sha256": None, "asked": 0, "complete": [], "extended": {},
           "refused": {}, "unverified": {}}
    try:
        OR, sha = rules(path)
    except OSError as e:                              # no question: no clip passes, none is refused (ruling 160 (2a))
        why = f"the out-edge question is not available ({type(e).__name__}: {str(e)[:160]}): UNVERIFIED"
        rec["unverified"] = {m["moment_id"]: why for m in ms}
        log(f"  RULING 162 (1): {why}: {len(ms)} moment(s) out of this build")
        return [], rec
    rec["version"], rec["sha256"] = OR.VERSION, sha
    cache = load_cache(cache_path) if cache_path else {}

    def one(m):
        try:
            src = CI.source_for(m, sources)
        except KeyError:
            return m, None, None, "its word record is not in this build: the question cannot be asked"
        return m, src, ask(router, m, src, cache, path), None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = list(ex.map(one, ms))
    rec["asked"] = sum(1 for _, _, v, _ in got if v is not None)
    keep, todo = [], []
    for m, src, v, err in got:
        mid = m["moment_id"]
        if v is None or v.get("measured") is not True:
            rec["unverified"][mid] = err or f"no answer from {v.get('backend') or 'the out-edge model'}: " \
                                            f"{str(v.get('why'))[:200]}"
        elif v.get("complete") is True:
            keep.append(dict(m, out_edge=sealed(v)))
            rec["complete"].append(mid)
        elif v.get("finishes_at") is None:
            rec["refused"][mid] = f"the thought runs on past its last word and no following sentence asked finishes " \
                                  f"it ({str(v.get('why'))[:160]})"
        elif not v.get("ks"):
            rec["refused"][mid] = f"the thought runs on past its last word and the clip cannot be extended (cut " \
                                  f"inside a sentence, or a window record) ({str(v.get('why'))[:160]})"
        else:
            todo.append((m, src, v))
    ext = []
    for m, src, v in todo:                            # the extension: admitted (ITEM 3), then asked on its own edge
        mid, k = m["moment_id"], v["ks"][v["finishes_at"]]
        try:
            x = extend(m, src, k, ctx, f"ruling 162 (1): the thought runs on past the clip's last word; it ends at "
                                       f"the end of the following sentence {v['finishes_at'] + 1} "
                                       f"({str(v.get('why'))[:160]})")
        except ValueError as e:
            rec["refused"][mid] = f"the thought runs on and the clip cannot be extended: {str(e)[:200]}"
            continue
        ok, why = admit(x) if admit is not None else (False, "no extension is admitted without its own checks")
        if not ok:
            rec["refused"][mid] = f"its extension {x['moment_id']} fails before its question: {str(why)[:200]}"
            continue
        ext.append((m, src, x))

    def again(t):
        m, src, x = t
        return m, x, ask(router, x, src, cache, path)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for m, x, v2 in ex.map(again, ext):
            mid = m["moment_id"]
            rec["asked"] += 1
            if v2.get("measured") is not True:
                rec["unverified"][mid] = f"its extension {x['moment_id']} got no answer: {str(v2.get('why'))[:200]}"
            elif v2.get("complete") is not True:
                rec["refused"][mid] = f"its extension {x['moment_id']} runs on too ({str(v2.get('why'))[:160]})"
            else:
                keep.append(dict(x, out_edge=sealed(v2)))
                rec["extended"][mid] = x["moment_id"]
    if cache_path:
        save_cache(cache_path, cache)
    log(f"  RULING 162 (1) (the OUT edge, {OR.VERSION}, sha {sha[:12]}): {rec['asked']} asked; "
        f"{len(rec['complete'])} end a thought, {len(rec['extended'])} extended to its end, "
        f"{len(rec['refused'])} refused, {len(rec['unverified'])} UNVERIFIED (no answer)"
        + "".join(f"; {k[:8]} -> {v[:8]}" for k, v in rec["extended"].items())
        + "".join(f"; {k[:8]}: {w[:120]}" for k, w in list(rec["refused"].items())[:6]))
    return keep, rec
