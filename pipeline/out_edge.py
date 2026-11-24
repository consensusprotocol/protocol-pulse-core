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
import re
import subprocess
import threading
import types
from concurrent.futures import ThreadPoolExecutor

import eligibility as E

OWNER_RULES = None                # a FILE to load instead of the release revision: tests only (None in every build)
RELEASE_REPO = "/home/ultron/protocol_pulse"          # the integrator's repository: read through git, never its files
RELEASE_REF = "origin/combo-letterbox-quoteonly-v2"   # its PUSHED release branch (the integrator's push moves it)
RULES_FILE = "pipeline/owner_rules.py"
LIVE_RULES = os.path.join(RELEASE_REPO, RULES_FILE)   # the render's live copy: compared by pin(), never loaded
ROLE = "out_edge"                 # model_providers.json: the render's model, the render's way (no other model)
BEFORE_N, AFTER_N = 2, 3          # what the render asks with: the 2 sentences before the clip, the 3 after it
DEADLINE_S = 300.0                # the render's HeimdallText timeout
SEED = 7
RULING = "162 (1)"
_LOCK = threading.Lock()
_RULES = {}                       # sha256 -> the module made from those bytes
_PIN = {}                         # {"rev": the release revision a build pinned} (pin()); else the ref resolved once
_AT = {}                          # commit -> (module, sha256) of its rules file
_JSON = {}                        # (commit, path) -> a JSON file of the release revision (release_json)
REGISTRY_FILE = "pipeline/channels.json"   # the render's channel registry (display_name, aliases)
NO_VERDICT = re.compile(r"STEP_A_HELD|NOT MEASURED|no verdict|NO JUDGE ANSWERED")   # LEAN (2): an admit() that failed
#   for want of an answer (step A held, the second recogniser not measured): open work (UNVERIFIED), never a refusal


def _git(*args, binary=False):
    """git in the integrator's repository -> its stdout. OSError when git fails (nothing read: the caller fails
    closed)."""
    try:
        r = subprocess.run(["git", "-C", RELEASE_REPO, *args], capture_output=True, timeout=60)
    except (subprocess.SubprocessError, OSError) as e:
        raise OSError(f"git {' '.join(args)}: {type(e).__name__}: {e}") from e
    if r.returncode != 0:
        raise OSError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace').strip()[:200]}")
    return r.stdout if binary else r.stdout.decode().strip()


def release_rev():
    """The PUSHED release revision: the commit RELEASE_REF names now -> its 40-hex sha. OSError when it cannot be
    resolved."""
    return _git("rev-parse", "--verify", RELEASE_REF + "^{commit}")


def _load(raw, label):
    """The module made from these very bytes, under a name of its own (this tree has modules of its own names), so
    the sha sealed is the code that asked -> (module, sha256 hex)."""
    sha = hashlib.sha256(raw).hexdigest()
    with _LOCK:
        mod = _RULES.get(sha)
        if mod is None:
            mod = types.ModuleType(f"owner_rules_{sha[:12]}")
            mod.__file__ = label
            exec(compile(raw, label, "exec"), mod.__dict__)          # noqa: S102  the integrator's file, as hashed
            _RULES[sha] = mod
    return mod, sha


def _at(rev):
    """The rules file at one commit (a commit's content never changes: read once per process)."""
    with _LOCK:
        got = _AT.get(rev)
    if got is None:
        got = _load(_git("show", f"{rev}:{RULES_FILE}", binary=True), f"{RELEASE_REF}@{rev[:12]}:{RULES_FILE}")
        with _LOCK:
            _AT[rev] = got
    return got


def pin(rev=None):
    """ORCHESTRATOR 10:55 ET Nov 24 (the verifier's finding: these checks followed the live main tree's uncommitted
    edits): a build reads the integrator's owner_rules from the PUSHED release revision and pins ONE revision before
    any model call; every later rules() reads that revision. -> the build record's {"ref", "rev", "sha256",
    "version", "live_sha256"}. OSError, so the build aborts, when the revision or its file cannot be read, or when the
    render's live copy (LIVE_RULES) is not that revision's file: a mismatch (the render would judge by other rules)."""
    rev = rev or release_rev()
    mod, sha = _at(rev)
    try:
        with open(LIVE_RULES, "rb") as f:
            live = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        live = None
    if live != sha:
        raise OSError(f"owner_rules mismatch: the live {LIVE_RULES} (sha {str(live)[:12]}) is not the pushed release "
                      f"revision {rev[:12]}'s {RULES_FILE} (sha {sha[:12]}): no build")
    with _LOCK:
        _PIN.clear()
        _PIN["rev"] = rev
    return {"ref": RELEASE_REF, "rev": rev, "sha256": sha, "version": getattr(mod, "VERSION", None),
            "live_sha256": live}


def rules(path=None):
    """The integrator's owner_rules -> (module, sha256 of the bytes loaded): the revision the build pinned (pin()),
    else RELEASE_REF resolved once for this process; NEVER the live tree's working copy (10:55 ET Nov 24). path (or
    OWNER_RULES) loads that file instead (tests). OSError when nothing can be read: no question, so every clip is
    UNVERIFIED (pool()); attest.meaning_swaps holds."""
    p = path or OWNER_RULES
    if p:
        with open(p, "rb") as f:
            return _load(f.read(), p)
    return _at(_rev())


def _rev():
    """The release revision every read uses: the one the build pinned, else RELEASE_REF resolved once."""
    with _LOCK:
        rev = _PIN.get("rev") or _PIN.get("resolved")
    if not rev:
        rev = release_rev()
        with _LOCK:
            _PIN.setdefault("resolved", rev)
    return rev


def release_json(path):
    """A JSON file of the integrator's repository at the same release revision as rules() (never its working tree):
    the render's registry pipeline/channels.json, whose "aliases" item 2's names read as run_fresh.our_line_faults
    does. -> the parsed JSON (once per revision). OSError / ValueError when it cannot be read: the caller fails
    closed."""
    rev = _rev()
    with _LOCK:
        got = _JSON.get((rev, path))
    if got is None:
        got = json.loads(_git("show", f"{rev}:{path}", binary=True))
        with _LOCK:
            _JSON[(rev, path)] = got
    return got


def around(m, src, recover=False):
    """What the question is asked with, from the moment's own Source: (the text before the clip: up to BEFORE_N
    sentences, [up to AFTER_N following sentences, each its own text], [the source sentence index each of those ends
    with, or [] when no extension can follow them]). An extension keeps the IN edge, so it exists only for a moment of
    whole sentences on a Source of its own (not a window record: its sentences stop at the window).
    LEAN (2) (recover=True, the owner's assignment issue 2: "certain transcript representations prohibit extension
    despite available following context"): the indices are aligned with the texts, one per text, None where that text
    cannot end an extension; a clip whose IN edge is a sentence start may end at the end of any listed text: its own
    last sentence when it is cut inside it (the OUT edge RE-ANCHORED to that sentence's end), or a following sentence,
    on a window record too, never the window record's LAST sentence (the decode window may have cut it short, so its
    end is not known to be the sentence's). The texts asked with are the same either way (the cache key keeps)."""
    k0, k1 = m["sentences"]
    w0, w1 = m["words"]
    S, T = src.sentences, src.tokens
    before = E.spoken(T[S[max(0, k0 - BEFORE_N)][0]:w0]) if w0 > S[max(0, k0 - BEFORE_N)][0] else ""
    whole = w0 == S[k0][0] and w1 == S[k1][1] and getattr(src, "window", None) is None
    if whole:
        ks = list(range(k1 + 1, min(len(S), k1 + 1 + AFTER_N)))
        return before, [E.spoken(T[S[k][0]:S[k][1] + 1]) for k in ks], ks
    nxt, kk = [], []                                  # cut inside a sentence, or a window record: the words after the
    if w1 < S[k1][1]:                                 # clip as far as its sentence goes, then whole sentences; no
        nxt.append(E.spoken(T[w1 + 1:S[k1][1] + 1]))   # extension is made from them (LEAN (2): see above)
        kk.append(k1)
    k = k1 + 1
    while len(nxt) < AFTER_N and k < len(S):
        nxt.append(E.spoken(T[S[k][0]:S[k][1] + 1]))
        kk.append(k)
        k += 1
    if not recover:
        return before, nxt, []
    last = len(S) - 1 if getattr(src, "window", None) is not None else None
    return before, nxt, [k if w0 == S[k0][0] and k != last else None for k in kk]


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


def ask(router, m, src, cache=None, path=None, recover=False):
    """The out-edge verdict on ONE moment (cached by moment, span, the rules file's sha and the texts asked with): the
    integrator's out_edge() on this router's role "out_edge". -> {"complete", "finishes_at", "why", "backend",
    "measured", "version", "sha256", "next": the sentences asked with, "ks": their source indices, "cached"}. Only
    the router's no-answer errors are unmeasured; any other error propagates (the spend stop). LEAN (2): a cached
    verdict answers the very same question (its key: moment, span, rules sha, texts asked with); where its sentences
    may end an extension is read from the source again (around(), recover), never from the cache."""
    import providers as P
    OR, sha = rules(path)
    before, nxt, ks = around(m, src, recover)
    key = _key(m, sha, before, nxt)
    hit = (cache or {}).get(key) if cache is not None else None
    if isinstance(hit, dict) and hit.get("measured") is True:
        return dict(hit, cached=True, next=nxt, ks=ks)
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


def pool(router, ms, sources, ctx, cache_path=None, log=print, extend=None, workers=4, path=None, admit=None,
         recover=False, floor_s=None):
    """RULING 162 (1) on a build's pool (see the module). -> (the moments that may play, each carrying "out_edge", the
    extensions in their parents' places; the record {"version", "sha256", "asked", "complete", "extended": {parent:
    extension}, "refused": {id: why}, "unverified": {id: why}}). extend(m, src, k, ctx, why): tail_variant.extend.
    ITEM 3 (orchestrator 09:45 ET Nov 24, final): "the deterministic edge check runs first": the caller passes only
    moments the second recogniser's OUT edge already passed, and admit(extension) -> (ok, why) puts every extension
    through the pool's rules, step A and that deterministic check BEFORE its own question (None: refused, no
    extension is made without them).
    LEAN (2) (recover=True): BOUNDED RECOVERY of a clip whose thought runs on, every new span a new moment through
    admit() and asked this question on its own edge again (unanswered: UNVERIFIED, never a pass): (a) EXTENDED or
    RE-ANCHORED to the end of the listed sentence that finishes the thought (around(): its own cut sentence's end or a
    following sentence, on a window record too, never the window's last sentence; at most AFTER_N sentences: only what
    the checker read; the pool's 20 s clip through admit); else (b) SHORTENED, once, to the end of its own previous
    sentence, when its IN edge is a sentence start and the shorter clip keeps floor_s seconds; else REFUSED (dropped).
    The record adds "shortened": {parent: span}."""
    import context_integrity as CI
    import tail_variant as TV
    if extend is None:
        extend = TV.extend
    rec = {"ruling": RULING, "version": None, "sha256": None, "asked": 0, "complete": [], "extended": {},
           "refused": {}, "unverified": {}, **({"shortened": {}} if recover else {})}
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
        return m, src, ask(router, m, src, cache, path, recover), None
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = list(ex.map(one, ms))
    rec["asked"] = sum(1 for _, _, v, _ in got if v is not None)
    keep, todo, short = [], [], []

    def runs_on(m, src, why):                         # LEAN (2): a clip that cannot be extended may be shortened
        if recover:                                   # (below); else it is refused, as before
            short.append((m, src, why))
        else:
            rec["refused"][m["moment_id"]] = why
    for m, src, v, err in got:
        mid = m["moment_id"]
        if v is None or v.get("measured") is not True:
            rec["unverified"][mid] = err or f"no answer from {v.get('backend') or 'the out-edge model'}: " \
                                            f"{str(v.get('why'))[:200]}"
        elif v.get("complete") is True:
            keep.append(dict(m, out_edge=sealed(v)))
            rec["complete"].append(mid)
        elif v.get("finishes_at") is None:
            runs_on(m, src, f"the thought runs on past its last word and no following sentence asked finishes it "
                            f"({str(v.get('why'))[:160]})")
        else:
            fa, ks = v.get("finishes_at"), v.get("ks") or []
            k = ks[fa] if type(fa) is int and 0 <= fa < len(ks) else None
            if k is None:
                runs_on(m, src, f"the thought runs on past its last word and the clip cannot be extended (cut "
                                f"inside a sentence, or a window record" + (": its IN edge inside a sentence, or the "
                                f"window record's last sentence" if recover else "") +
                                f") ({str(v.get('why'))[:160]})")
            else:
                todo.append((m, src, v, k))
    ext = []
    for m, src, v, k in todo:                         # the extension: admitted (ITEM 3), then asked on its own edge
        mid = m["moment_id"]
        try:
            x = extend(m, src, k, ctx, f"ruling 162 (1): the thought runs on past the clip's last word; it ends at "
                                       f"the end of the following sentence {v['finishes_at'] + 1} "
                                       f"({str(v.get('why'))[:160]})")
        except ValueError as e:
            runs_on(m, src, f"the thought runs on and the clip cannot be extended: {str(e)[:200]}")
            continue
        ok, why = admit(x) if admit is not None else (False, "no extension is admitted without its own checks")
        if not ok and recover and NO_VERDICT.search(str(why or "")):   # LEAN (2): no answer is never a refusal:
            rec["unverified"][mid] = (f"its extension {x['moment_id']} got no verdict before its question: "   # open
                                      f"{str(why)[:200]}")   # work, asked again next build (never shortened for it)
            continue
        if not ok:
            runs_on(m, src, f"its extension {x['moment_id']} fails before its question: {str(why)[:200]}")
            continue
        ext.append((m, src, x))

    def again(t):
        m, src, x = t
        return m, src, x, ask(router, x, src, cache, path, recover)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for m, src, x, v2 in ex.map(again, ext):
            mid = m["moment_id"]
            rec["asked"] += 1
            if v2.get("measured") is not True:
                rec["unverified"][mid] = f"its extension {x['moment_id']} got no answer: {str(v2.get('why'))[:200]}"
            elif v2.get("complete") is not True:
                runs_on(m, src, f"its extension {x['moment_id']} runs on too ({str(v2.get('why'))[:160]})")
            else:
                keep.append(dict(x, out_edge=sealed(v2)))
                rec["extended"][mid] = x["moment_id"]
    for m, src, why in short:                         # LEAN (2) (b): ONE shortening, to its own previous sentence
        mid = m["moment_id"]
        (k0, k1), w0 = m["sentences"], m["words"][0]
        if admit is None or k1 <= k0 or w0 != src.sentences[k0][0]:
            rec["refused"][mid] = why + ("; it cannot be shortened (one sentence, or its IN edge inside a sentence)"
                                         if admit is not None else "")
            continue
        x = TV.variant(m, src, k1 - 1, ctx, f"lean (2): its thought runs on past its last word ({why[:160]}); "
                                            f"shortened to the end of its previous sentence")
        x["derived_from"] = dict(x["derived_from"], ruling=RULING, how="shortened (lean 2)")
        if floor_s is not None and float(x.get("duration_s") or 0.0) < float(floor_s):
            rec["refused"][mid] = f"{why}; shortened it keeps {x.get('duration_s')} s, under the {floor_s:g} s floor"
            continue
        ok, why2 = admit(x)
        if not ok and NO_VERDICT.search(str(why2 or "")):
            rec["unverified"][mid] = f"shortened ({x['moment_id']}) it got no verdict before its question: {str(why2)[:200]}"
            continue
        if not ok:
            rec["refused"][mid] = f"{why}; shortened ({x['moment_id']}) it fails before its question: {str(why2)[:160]}"
            continue
        v2 = ask(router, x, src, cache, path, recover)
        rec["asked"] += 1
        if v2.get("measured") is not True:
            rec["unverified"][mid] = f"shortened ({x['moment_id']}) it got no answer: {str(v2.get('why'))[:200]}"
        elif v2.get("complete") is not True:
            rec["refused"][mid] = f"{why}; shortened ({x['moment_id']}) it runs on too ({str(v2.get('why'))[:120]})"
        else:
            keep.append(dict(x, out_edge=sealed(v2)))
            rec["shortened"][mid] = x["moment_id"]
    if cache_path:
        save_cache(cache_path, cache)
    log(f"  RULING 162 (1) (the OUT edge, {OR.VERSION}, sha {sha[:12]}): {rec['asked']} asked; "
        f"{len(rec['complete'])} end a thought, {len(rec['extended'])} extended to its end, "
        + (f"{len(rec['shortened'])} shortened (lean 2), " if recover else "") +
        f"{len(rec['refused'])} refused, {len(rec['unverified'])} UNVERIFIED (no answer)"
        + "".join(f"; {k[:8]} -> {v[:8]}" for k, v in rec["extended"].items())
        + "".join(f"; {k[:8]} => {v[:8]}" for k, v in (rec.get("shortened") or {}).items())
        + "".join(f"; {k[:8]}: {w[:120]}" for k, w in list(rec["refused"].items())[:6]))
    return keep, rec
