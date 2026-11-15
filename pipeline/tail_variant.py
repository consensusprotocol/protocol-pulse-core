"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN: "a spotlight (and a medley hook or clip) may be sealed
as a variant that ENDS at an earlier sentence boundary of the mined moment, when that is what keeps it lawful (a held word
after the boundary, a tail the cut cannot make, the seconds ceiling). It is a new span: it faces every gate again from
the start (step A both families, CUTTABLE at the new OUT, ALONE >= 4, the opener rating, the 12 s floor, the visual check,
the lock pre-check), and the variant is recorded as derived from its parent row. Omission is judged by step A as always:
a variant that drops the speaker's own condition or conclusion fails there."

- variant(): the parent moment cut to end at the end of one of its own earlier sentences, made by the miner's own
  machinery (moments.record over eligibility.Span: eligibility judged afresh, its id the span's own), with the parent's
  scores, topics and risk, and "derived_from" (here and in its mined record): the parent row.
- for_pool(): the variants a build adds to its pool (every gate then judges them as any moment):
  - a held word: the lock pre-check's HOLD on the parent's exact span under the CURRENT decoder and rules (holds();
    under ruling 103's rules such a hold is final, its targeted re-listen included). The held word is placed on this
    side (held_word); the variant ends at the parent's last sentence boundary before it.
  - a tail the cut cannot make: a current hold that is ruling 73's ("the render cannot cut this span"): the last
    sentence goes.
  - the seconds ceiling: a parent longer than ceil_s: the longest variant within it.
  When two apply, the shorter variant (it satisfies both). None when no earlier boundary does.
  A parent with a current hold is REPLACED by its variant ("the hold is final and the clip may only be saved by a
  variant that leaves the token out", ruling 103): the two never compete for a line-up or a finalist's place. A parent
  over the ceiling stays beside its variant (the medley may still use it).
A variant is never snapped outward (spotlight.snap): that would put back the words it leaves out.
- directive_variant(): ONLY on the orchestrator's written directive (proof_ledger.DIRECTIVES, written by the builder
  quoting the ruling), the variant of a NAMED parent ending as the directive says, as the ALTERNATIVE to a named sealed
  spotlight (ruling 90's one place per channel per day then admits it beside that story, and nothing else)."""
import attest as AT
import canon as C
import eligibility as E
import moments as M

CUT_HOLD = "ruling 73"          # a hold whose reason starts so: the render cannot cut this span (the tail goes)


def variant(m, src, k, ctx, why):
    """The parent moment `m` (a pp.moment/1 record) ending at the end of its source's sentence k, its first sentence
    unchanged (m's first sentence <= k < its last). -> the new moment record. ValueError for any other k."""
    k0, k1 = m["sentences"]
    if not (isinstance(k, int) and k0 <= k < k1):
        raise ValueError(f"a tail variant ends at an earlier sentence of the moment: {k!r} is not in [{k0}, {k1})")
    sp = E.Span(src, k0, k)
    derived = {"ruling": 104, "from": m["moment_id"],
               "ledger_moment_id": (m.get("mined") or {}).get("ledger_moment_id"),
               "sentences": [k0, k], "was": [k0, k1], "end_was": m.get("end"), "why": why,
               "left_out": E.spoken(src.tokens[sp.w1 + 1:src.sentences[k1][1] + 1])}
    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
                        "risk": list(m.get("risk") or []), "topics": list(m.get("topics") or []),
                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
                   dict(m.get("mined") or {}, derived_from=derived))
    rec["rank_score"] = M.rank_score(rec)
    if m.get("source_key"):
        rec["source_key"] = m["source_key"]
    rec["derived_from"] = derived
    return rec


def holds(m, results_dir):
    """The newest lock pre-check HOLD on the parent's exact span (its video, start and end to the millisecond, its own
    text as the approved text, its trim fields, as a hook or a clip) under the CURRENT decoder and rules
    (lock_precheck.answer: entries under any other decoder or rules are never read). -> the entry, or None."""
    import lock_precheck as LP
    base = LP.segments_of([m])[0]
    best = None
    for role in ("hook", "clip"):
        e = LP.answer(dict(base, role=role), results_dir)
        if e is not None and e.get("outcome") == "hold" and (best is None or str(e.get("at") or "") >= best[0]):
            best = (str(e.get("at") or ""), e)
    return best[1] if best else None


def held_word(m, src, entry):
    """The index (into src.tokens) of the parent's first word that the HOLD is about, placed on THIS side: the entry's
    second reading (as_spoken.text) against the parent's own text, through this side's canon and ruling 84's class
    (attest.class_84, as decide() judges an adoption): the first difference outside the class whose approved side is
    not empty, at its tokens' first occurrence among the parent's words (canon.canon_spans). Recomputed from the texts,
    it does not depend on the canon the entry was written under. -> int, or None when it cannot be placed (no second
    reading, no such difference, an insert on the spoken side alone, or tokens not found): then no variant."""
    spoken = ((entry or {}).get("as_spoken") or {}).get("text") if isinstance(entry, dict) else None
    if not isinstance(spoken, str) or not spoken.strip():
        return None
    w0, w1 = m["words"]
    spans = C.canon_spans([t.get("word") or "" for t in src.tokens[w0:w1 + 1]])
    toks = [t for t, _, _ in spans]
    for d in AT.class_84(spoken, m["text"]):
        if d["class"] is not None:
            continue
        want = d["approved"].split()
        if not want:
            return None                                  # the second reading inserted it: nowhere to end before
        for i in range(len(toks) - len(want) + 1):
            if toks[i:i + len(want)] == want:
                return w0 + spans[i][1]
        return None
    return None


def directive_variant(m, src, ctx, d):
    """The orchestrator's directive `d` ({"parent", "ends", "alternative_to", "by", "why"}) on the parent `m`: its variant
    ending at the longest earlier sentence boundary whose words END as d["ends"] (canon tokens), recorded with the
    directive and the spotlight it is the alternative to. -> (variant, None) or (None, why there is none)."""
    k0, k1 = m["sentences"]
    want = C.canon_tokens(str(d.get("ends") or ""))      # canon drops a leading "..." itself (L-k: one form)
    if not want:
        return None, "the directive names no ending"
    for k in range(k1 - 1, k0 - 1, -1):
        got = C.canon_tokens(E.spoken(src.tokens[src.sentences[k0][0]:src.sentences[k][1] + 1]))
        if got[-len(want):] == want:
            v = variant(m, src, k, ctx, f"the orchestrator's directive ({d.get('by')}): {d.get('why') or ''}".strip())
            v["derived_from"].update(directive=d.get("by"), alternative_to=d.get("alternative_to"))
            return v, None
    return None, f"no earlier sentence boundary of the parent ends {d.get('ends')!r}"


def for_pool(moments, sources, ctx, results_dir, ceil_s, directives=None):
    """The ruling-104 variants for this build's pool. directives: {parent id: the orchestrator's directive} (a parent
    named there gets the directive's variant, in its place, whatever its pre-check says). -> (variants, {parent id: why
    it has none / which it got}, {the ids of the parents replaced by their variants})."""
    import context_integrity as CI
    have = {m["moment_id"] for m in moments}
    out, notes, replaced = [], {}, set()
    for m in moments:
        mid = m["moment_id"]
        k0, k1 = m.get("sentences") or (None, None)
        if not (isinstance(k0, int) and isinstance(k1, int) and k1 > k0):
            if mid in (directives or {}):                # glm, audit 1835 C1: never a silent ignore
                notes[mid] = "the directive: no variant, the parent is one sentence (no earlier boundary)"
            continue                                     # one sentence: no earlier boundary
        wanted = []
        if mid in (directives or {}):                    # the orchestrator's directive: this variant, in its place
            try:
                src = CI.source_for(m, sources)
            except KeyError:
                notes[mid] = "the directive: no variant, its word record is not in this build"
                continue
            v, why = directive_variant(m, src, ctx, directives[mid])
            if v is None:                                # the rules stand: the triggers below still apply to it
                notes[mid] = f"the directive: no variant, {why}"
            elif v["moment_id"] in have:
                notes[mid] = f"the directive: its variant {v['moment_id']} is already in the pool"
            else:
                have.add(v["moment_id"])
                out.append(v)
                replaced.add(mid)
                notes[mid] = (f"the directive's variant {v['moment_id']} ({v['duration_s']} s, ends "
                              f"{v['text'][-60:]!r}), in its place, the alternative to "
                              f"{v['derived_from'].get('alternative_to')}")
                continue
        e = holds(m, results_dir)
        try:
            src = CI.source_for(m, sources)
        except KeyError:
            if e is not None or float(m.get("duration_s") or 0) > ceil_s:
                notes[mid] = "no variant: its word record is not in this build"
            continue
        if e is not None:
            if str(e.get("reason") or "").startswith(CUT_HOLD):
                wanted.append((k1 - 1, f"a tail the cut cannot make ({str(e.get('reason'))[:160]})"))
            else:
                i = held_word(m, src, e)
                ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]
                if ks:
                    wanted.append((ks[-1], f"a held word after the boundary: {src.tokens[i].get('word')!r} at "
                                           f"{src.tokens[i].get('start')} s (the lock pre-check's hold, "
                                           f"{e.get('request_id')})"))
                else:                                    # no variant can leave the held word out: none at all,
                    notes[mid] = (notes[mid] + "; " if mid in notes else "") + (            # not even the
                        "no variant: the held word cannot be placed" if i is None else          # ceiling's (qwen,
                        "no variant: the held word is in its first sentence")
                    continue                                                                         # audit 1441 C2)
        if float(m.get("duration_s") or 0) > ceil_s:
            t0 = float(m["start"])
            ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]
            if ks:
                wanted.append((ks[-1], f"the seconds ceiling ({float(m['duration_s']):.2f} s > {ceil_s:g} s)"))
            else:
                notes[mid] = f"no variant: no earlier boundary within {ceil_s:g} s"
        if not wanted:
            continue
        k = min(x[0] for x in wanted)
        if e is not None:
            replaced.add(mid)                            # ruling 103: its hold is final; only the variant may save it
        v = variant(m, src, k, ctx, "; ".join(w for _, w in wanted))
        if v["moment_id"] in have:
            notes[mid] = f"its variant {v['moment_id']} is already in the pool"
            continue
        have.add(v["moment_id"])
        out.append(v)
        notes[mid] = (notes[mid] + "; " if mid in notes else "") + (
                      f"variant {v['moment_id']} ({v['duration_s']} s, ends {v['text'][-60:]!r})"
                      + (", in its place" if mid in replaced else ", beside it"))
    return out, notes, replaced
