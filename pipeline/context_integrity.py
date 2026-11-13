#!/usr/bin/env python3
"""pipeline/context_integrity.py — CONTEXT INTEGRITY (law L-s, orchestrator 2026-11-12 '02:30'; a HARD gate, separate
from VO fidelity): a verbatim whole sentence can still misrepresent its speaker once lifted. Per selected moment:

INPUTS  the source's transcript from >= CONTEXT_BEFORE_S before the moment (pulled back to the question it answers, when
        one ends within CONTEXT_MAX_BEFORE_S) to >= CONTEXT_AFTER_S after it, the video title, the selected sentences,
        and the finished package (order, adjacent clips, VO, title, caption).
STEP A  (context only, the package hidden; role "context_verdict", never the writer's vendor): who is speaking, whose
        view it is (own sincere / attributed / hypothetical / conditional / sarcastic / question / reading aloud / ad
        read), every pronoun and this / that / today with its referent and whether it lies inside the selection, any
        governing condition or time frame, any retraction or qualification in the window, the proposition asserted.
STEP B  (the package only; role "viewer_takeaway", never the writer's vendor): what an ordinary viewer concludes each
        speaker asserts, how certain, and any implied relation (agreeing / answering / rebutting / one conversation)
        between speakers.
STEP C  (role "context_verdict"): does A's in-context proposition entail B's takeaway, same polarity, no stronger
        certainty?
DECIDE  (code) PASS only if: own sincere assertion; no speaker change inside; every referent and condition inside the
        selection; no retraction; C entails, same polarity, not stronger; no implied relation between speakers of
        different source videos. Any "uncertain" fails (law L-m).
REPAIR  dropping the MOMENT and repacking (the law also permits extending the clip by whole locked sentences; that is
        not built); never writing the missing context into the VO (L-s).
"""
import itertools
import json
import re

import eligibility as E

CONTEXT_BEFORE_S = 90.0
CONTEXT_MAX_BEFORE_S = 180.0
CONTEXT_AFTER_S = 60.0
EXCERPT_MAX = 12000                # characters of one escaped window; a longer one is CONTEXT_TOO_LONG (never cut)
EDGE_TOL_S = 30.0                  # a caption record's first / last word this close to the media's start / end
                                   # (its duration) counts as reaching that edge: intros and outros are often wordless
A_KEYS = ("label", "speaker_changes_inside", "view", "referents", "conditions", "retraction", "time_ok", "proposition",
          "certainty", "speaker_is", "speaker_evidence")
VIEWS = ("own_sincere", "attributed", "hypothetical", "conditional", "sarcastic", "question", "reading_aloud",
         "ad_read", "joke", "uncertain")
CERTAINTY = ("certain", "likely", "possible", "speculative", "uncertain")
RELATIONS = ("none", "agreeing", "answering", "rebutting", "same_conversation", "uncertain")
YNU = ("yes", "no", "uncertain")


def window(src, k0, k1, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S, max_before=CONTEXT_MAX_BEFORE_S):
    """Sentence indices (a, b) of the context window around the moment k0..k1: AT LEAST `before` s earlier (back to
    the question the moment answers, when one ends within `max_before` s) and AT LEAST `after` s later, in whole
    sentences, or to the transcript's edge (audit p2 C11: the window was at most those spans)."""
    S, T = src.sentences, src.tokens
    t0 = E._time(T[S[k0][0]], "start")
    t1 = E._time(T[S[k1][1]], "end")
    if t0 is None or t1 is None:
        return None                                 # an unclocked moment has no measurable window (audit C2 K9)
    a = k0
    while a > 0 and t0 is not None:
        cur = E._time(T[S[a][0]], "start")
        if cur is not None and cur <= t0 - before:
            break                                       # the window already starts >= `before` s earlier
        prev = E._time(T[S[a - 1][0]], "start")
        if prev is not None and prev < t0 - max_before:
            break
        a -= 1
    q = a
    while q > 0 and t0 is not None and (E._time(T[S[q - 1][0]], "start") or -1e18) >= t0 - max_before:
        q -= 1
        if (T[S[q][1]].get("word") or "").rstrip().endswith("?"):
            a = min(a, q)
            break
    b = k1
    while b + 1 < len(S) and t1 is not None:
        cur = E._time(T[S[b][1]], "end")
        if cur is not None and cur >= t1 + after:
            break                                       # the window already ends >= `after` s later
        b += 1
    return a, b


def mark(parts):
    """[(sentence text, selected?)] -> the excerpt: every sentence escaped (story_semantics.quote_data, no limit),
    the selection wrapped in <selected> AFTER escaping, so the markers survive (audit p2 C11)."""
    from story_semantics import quote_data
    out = []
    for t, sel in parts:
        q = quote_data(t, 10 ** 9)
        out.append(f"<selected>{q}</selected>" if sel else q)
    return " ".join(out)


def caption_parts(src, k0, k1, w0=None, w1=None, before=CONTEXT_BEFORE_S, after=CONTEXT_AFTER_S,
                  max_before=CONTEXT_MAX_BEFORE_S):
    """A moment on a WINDOW word record (the integrator's word-pass worker: about +-45 s of words around one moment,
    on the YouTube clock). Under the contract agreed with the integrator, its L-s context comes from the full-video
    CAPTION record the ledger mined it from (src.context_source). The selection is the window record's own words, and
    the context is the caption's words by TIME: every caption word overlapping the >= `before` s before the selection,
    and every caption word starting in the `after` s after it, or to the media's edge (a caption record is the whole
    video). YouTube's automatic captions carry no punctuation, so the window is cut by time, never by sentences, and
    the pull-back to a question (which needs a '?') does not apply.
    The coverage is MEASURED, never assumed (audit 0123 C1: qwen, glm). The caption must reach `before` s ahead of the
    selection, or begin within EDGE_TOL_S of the media's start. It must reach `after` s past the selection, or end
    within EDGE_TOL_S of the video's duration (cs.duration_s). A caption record that stops short, or an unknown
    duration where the end would need it, leaves the context unavailable. The media's start is 0 s: the YouTube clock.
    The words reach the marks the way window() does for a full-video record (audit 0123 C2: grok, glm). The context
    goes back to the last caption word starting at or before the `before` mark (never past `max_before`), so a
    wordless stretch inside the window is bridged. It goes forward to the first caption word ending at or past the
    `after` mark.
    -> ([(text, selected?)], (from_s, to_s) actually covered), or (None, None) when there is no caption record, a
    time is missing, or the coverage falls short: the context is unavailable and L-s fails closed."""
    cs = getattr(src, "context_source", None)
    S, T = src.sentences, src.tokens
    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
    t0, t1 = E._time(T[lo], "start"), E._time(T[hi], "end")
    if cs is None or t0 is None or t1 is None or not cs.tokens:
        return None, None
    timed = [(tok, E._time(tok, "start"), E._time(tok, "end")) for tok in cs.tokens]
    if any(a is None or b is None for _, a, b in timed):
        return None, None                            # an unclocked caption record: no measurable window
    first, last = min(a for _, a, _ in timed), max(b for _, _, b in timed)
    dur = getattr(cs, "duration_s", None)
    if not (first <= t0 - before or first <= EDGE_TOL_S):
        return None, None                            # the caption starts too late to show what came before
    if not (last >= t1 + after or (isinstance(dur, (int, float)) and last >= float(dur) - EDGE_TOL_S)):
        return None, None                            # it stops short of what comes after, and short of the end
    j = max((i for i, (_, a, _) in enumerate(timed) if t0 - max_before <= a <= t0 - before), default=None)
    pre = ([tok for i, (tok, a, b) in enumerate(timed) if i >= j and a < t0] if j is not None else
           [tok for tok, a, b in timed if b > t0 - before and a < t0])    # nothing within max_before: window()'s stop
    m = min((i for i, (_, a, b) in enumerate(timed) if a >= t1 and b >= t1 + after), default=None)
    post = [tok for i, (tok, a, b) in enumerate(timed) if a >= t1 and (m is None or i <= m)]
    sel = E.spoken(T[lo:hi + 1])
    if not sel.strip():
        return None, None
    parts = [(E.spoken(pre), False), (sel, True), (E.spoken(post), False)]
    covered = (round(min([E._time(x, "start") for x in pre] or [t0]), 3),
               round(max([E._time(x, "end") for x in post] or [t1]), 3))
    return [(t, s_) for t, s_ in parts if t.strip()], covered


def context_around(src, k0, k1, w0=None, w1=None):
    """(the context before the selection, the context after it) as text, for any Source: a window record's from its
    caption record (caption_parts), every other record's from its own window(). (None, None) when unavailable."""
    if getattr(src, "window", None) is not None:
        parts, win = caption_parts(src, k0, k1, w0, w1)
        if parts is None:
            return None, None
        i = next((n for n, (_, sel) in enumerate(parts) if sel), None)
        if i is None:                                # no selection (never from caption_parts; checked anyway)
            return None, None
        return " ".join(t for t, _ in parts[:i]), " ".join(t for t, _ in parts[i + 1:])
    win = window(src, k0, k1)
    if win is None:
        return None, None
    a, b = win
    S, T = src.sentences, src.tokens
    lo, hi = (w0, w1) if w0 is not None and w1 is not None else (S[k0][0], S[k1][1])
    return E.spoken(T[S[a][0]:lo]), E.spoken(T[hi + 1:S[b][1] + 1])


def _window_text(src, k0, k1, w0=None, w1=None):
    """The window's text with the selection marked. With word indices w0..w1 the selection is marked by WORDS (a
    moment cut inside a store sentence, ruling 7 / orchestrator 06:45), else by sentences k0..k1. A moment on a WINDOW
    word record takes its context from its caption record (caption_parts)."""
    if getattr(src, "window", None) is not None:
        parts, win = caption_parts(src, k0, k1, w0, w1)
        return (mark(parts), win) if parts is not None else (None, None)
    win = window(src, k0, k1)
    if win is None:
        return None, None
    a, b = win
    S, T = src.sentences, src.tokens
    if w0 is None or w1 is None:
        return mark([(E.spoken(T[S[k][0]:S[k][1] + 1]), k0 <= k <= k1) for k in range(a, b + 1)]), (a, b)
    lo, hi = S[a][0], S[b][1]
    parts = [(E.spoken(T[lo:w0]), False), (E.spoken(T[w0:w1 + 1]), True), (E.spoken(T[w1 + 1:hi + 1]), False)]
    return mark([(t, sel) for t, sel in parts if t.strip()]), (a, b)


STEP_A = """You read transcripts of Bitcoin videos. For each EXCERPT below, the sentences inside <selected> are a clip
that may be shown on its own. Use the whole excerpt (what comes before and after) to judge the selected words. You do
not know how the clip will be used.

{excerpts}

For each excerpt answer:
- "speaker_changes_inside": does the speaker change inside the selected words? "yes" / "no" / "uncertain"
- "view": whose view the selected words express: "own_sincere" (the speaker's own sincere assertion), "attributed"
  (someone else's view, quoted or reported), "hypothetical", "conditional" (true only under a condition), "sarcastic",
  "question", "reading_aloud" (reading a post or article), "ad_read", "joke", or "uncertain"
- "referents": every pronoun or pointing word in the selected words (it, they, this, that, he, she, today, here...)
  that points at something specific, with what it refers to; "inside": true if the selected words themselves give
  its antecedent or the predicate that completes it (an ellipsis completed by an earlier selected sentence: "It's not
  Bitcoin that's getting hacked. It's other intermediaries." = other intermediaries are getting hacked), or it points
  only at a general topic the clip presupposes; "inside": false if a listener needs the words before or after the
  selection; "changes_assertion": "yes" if resolving it differently would change WHAT THE SPEAKER ASSERTS, "no" if
  not, "uncertain". Leave out words that point at nothing outside: a dummy "it" ("it's raining", "it's not X that
  ...", where X is in the selection), and a generic "we" / "you" / "they" meaning people in general
- "conditions": any condition or time frame that governs the selected words, and whether it is INSIDE them
- "retraction": "none", or what the speaker later in the excerpt WITHDRAWS, REVERSES, CORRECTS or MATERIALLY LIMITS
  about the selected words ("actually I misspoke", "that said, I don't believe that", "but that only holds if ...").
  A later elaboration or warning that is CONSISTENT with a condition already stated inside the selected words is not
  a retraction ("none"); it would be one if the selected words had dropped that condition
- "time_ok": "yes" if every time word in the selected words (today, now, this week, just, recently, a "current"
  price) still holds on the show date given when the video was published (both on the excerpt), or there is none;
  "no" if it is stale; "uncertain"
- "proposition": in one sentence, what the speaker asserts in the selected words, read in context
- "certainty": "certain", "likely", "possible", "speculative" or "uncertain"
- "speaker_is": "host" if the excerpt shows that the speaker of the selected words is the channel's own host,
  "guest" if it shows a guest or another person speaking them, "uncertain" otherwise; "speaker_evidence": the exact
  words of the excerpt that show it (copied exactly, e.g. the host's own "welcome back to my channel"), or ""
Return ONLY this JSON object: {{"excerpts": [{{"label": "...", "speaker_changes_inside": "...", "view": "...",
"referents": [{{"word": "...", "refers_to": "...", "inside": true, "changes_assertion": "no"}}], "conditions":
[{{"text": "...", "inside": true}}],
"retraction": "none", "time_ok": "yes", "proposition": "...", "certainty": "...", "speaker_is": "...",
"speaker_evidence": "..."}}]}}"""

STEP_B = """You are an ordinary viewer of a 60-second video. Here is everything the video shows and says, in order.

{package}

For each clip say what you conclude its speaker asserts, how certain they sound, and whether it is positive, negative
or neutral about its subject. What you conclude a speaker asserts INCLUDES whatever the title, the caption or the
voice-over ATTRIBUTES to that speaker ("X: Y" or "X says Y" tells you that X asserts Y). The voice-over's own opinion,
framing, question or takeaway, attributed to nobody, is the host's, not the speaker's. Each clip's label is the text inside label="..." after the word CLIP: use exactly that
label in "label" and in "labels", never the speakers' names. Labels: {labels}. Then, for each pair of clips, say whether the video presents their speakers as RELATED TO EACH
OTHER: one answering the other, one rebutting the other, one agreeing WITH the other ("X agrees", "Y backs that up",
"both say"), or the two being in one conversation. Two speakers who each state their own view on the same subject,
each credited, are NOT related ("none") unless the video says or implies that they respond to each other.
Return ONLY this JSON object: {{"takeaways": [{{"label": "...", "asserts": "...", "certainty": "certain" | "likely" |
"possible" | "speculative" | "uncertain", "polarity": "positive" | "negative" | "neutral"}}], "relations":
[{{"labels": ["...", "..."], "relation": "none" | "agreeing" | "answering" | "rebutting" | "same_conversation" |
"uncertain"}}]}}"""

STEP_C = """For each pair below, A is what a speaker asserted, read in its original context; CLIP is the speaker's exact
words as the viewer hears them; B is what a viewer of a short video concludes the same speaker asserted (from the clip
and from whatever the video's title, caption or voice-over attributes to the speaker). The video's own words are:

{vo}

Answer for each pair:
- "entails": does A support what the CLIP'S OWN WORDS assert? Judge the speaker's in-context assertion against the
  clip's words as heard, not two paraphrases. A difference of scope is "no" ONLY when the context LIMITS the claim in a
  way the clip's words drop ("in this one case", "for small holders only", "back in 2021") and that limit changes what
  a reasonable viewer concludes; a presupposed topic or occasion is not such a limit. "yes", "no" or "uncertain".
- "dropped_limit": when "entails" is "no", that limit in the context's own words; otherwise "".
- "added_by": the EXACT words of the video's title, caption or voice-over that ATTRIBUTE to this speaker something A
  does not support (e.g. a title "Swan Bitcoin: the AI bubble is about to pop" when the speaker said investors could
  lose money), or "" when none do. The host's own commentary, attributed to nobody, attributes nothing.
- "same_polarity": do A and B have the same polarity? "yes", "no" or "uncertain".
- "stronger_certainty": is B more certain than A? "yes", "no" or "uncertain"; and "raising_words": when it is, the
  EXACT words of the video's voice-over, title or caption above that make the speaker sound more certain, or "" when no
  such words exist (the speaker's own words alone).

{pairs}

Return ONLY this JSON object: {{"pairs": [{{"label": "...", "entails": "...", "dropped_limit": "...",
"added_by": "...", "same_polarity": "...", "stronger_certainty": "...", "raising_words": "..."}}]}}"""


def _q(t, n):
    from story_semantics import quote_data
    return quote_data(t, n)


def package_view(package):
    """The package as a viewer meets it, in the RENDERER's order (render16.py / render_vertical.py segment lists): the
    hook, then the VO intro, then each clip with any VO bridge after it (after_clip, including after the last clip),
    then the sign-off; the title and caption."""
    out = [f"TITLE: {_q(package['title'], 200)}", f"CAPTION: {_q(package['caption'], 400)}"]
    vo = package["vo"]
    bridges = list(vo.get("bridges") or [])
    after = list(vo.get("bridges_after_clip") or range(1, len(bridges) + 1))   # bridge j follows clip after[j]
    by_clip = {a_: b_ for a_, b_ in zip(after, bridges)}
    for i, seg in enumerate(package["segments"]):                            # segment 0 is the hook, i = clip index
        out.append(f'CLIP label="{seg["label"]}" (on screen: {_q(seg["channel"], 80)}): "{_q(seg["text"], 900)}"')
        if i == 0 and vo.get("intro"):
            out.append(f"VOICE-OVER: {_q(vo['intro'], 400)}")
        if i and by_clip.get(i):
            out.append(f"VOICE-OVER: {_q(by_clip[i], 400)}")
    if vo.get("signoff"):
        out.append(f"VOICE-OVER: {_q(vo['signoff'], 300)}")
    return "\n".join(out)


def _strict(raw, top, item_keys):
    obj = json.loads(raw.strip())
    if not isinstance(obj, dict) or set(obj) != set(top):
        raise ValueError(f"keys must be exactly {sorted(top)}")
    for k, keys in item_keys.items():
        if not isinstance(obj[k], list):
            raise ValueError(f"'{k}' must be a list")
        for it in obj[k]:
            if not isinstance(it, dict) or set(it) != set(keys):
                raise ValueError(f"each item of '{k}' needs exactly {sorted(keys)}")
    return obj


def contexts_from_sources(package, sources, now=None):
    """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
    out = {}
    for seg in package["segments"]:
        src = sources[seg["video_id"]]
        w = seg.get("words") or (None, None)
        text, win = _window_text(src, seg["k0"], seg["k1"], w[0], w[1])
        if text is None:
            continue                                # judged as unavailable (require_all)
        out[seg["label"]] = {"text": text, "title": src.title or "", "channel": seg["channel"], "window": win,
                             "published": str(src.published_at or "")[:16],
                             "show_date": now.strftime("%Y-%m-%d") if now else None}
    return out


def check(router, package, sources, writer_vendor, seed=7):
    """The pipeline's entry: contexts built from the sources' records (every segment is a moment)."""
    return check_contexts(router, package, contexts_from_sources(package, sources), writer_vendor, seed)


def step_a(router, contexts, writer_vendor, seed=7, writer_family=None):
    """Step A alone (context only, the package hidden): {label: item} for exactly the given labels, and the back-end.
    Raises ValueError / ProviderError when it cannot be had or read."""
    labels = list(contexts)
    for lb in labels:
        if len(contexts[lb]["text"]) > EXCERPT_MAX:
            raise ValueError(f"CONTEXT_TOO_LONG: {lb}'s window is {len(contexts[lb]['text'])} characters (> "
                             f"{EXCERPT_MAX}); never truncated")
    ex = [f'<excerpt label="{lb}" channel="{_q(contexts[lb]["channel"], 80)}" video_title='
          f'"{_q(contexts[lb].get("title") or "", 160)}" published="{contexts[lb].get("published") or "unknown"}" '
          f'show_date="{contexts[lb].get("show_date") or "unknown"}">{contexts[lb]["text"]}</excerpt>'
          for lb in labels]
    ra = router.call("context_verdict", STEP_A.format(excerpts="\n".join(ex)), 4000, seed, avoid_vendor=writer_vendor,
                     avoid_family=writer_family)
    try:
        A = _strict(ra.text, {"excerpts"}, {"excerpts": A_KEYS})
        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
            raise ValueError(f"step A must answer exactly the labels {labels}")
    except (ValueError, TypeError):
        if hasattr(router, "reject"):
            router.reject(ra)
        raise
    for lb in labels:
        a_by[lb] = dict(a_by[lb], backend=ra.backend, replayed=bool(getattr(ra, "replayed", False)),
                        speaker_verified=speaker_verified(a_by[lb], contexts[lb]["text"]))
    return a_by, ra.backend


def speaker_verified(a, excerpt_text):
    """Law L-v 1: the speaker of the selected words is the channel's own host only with step A's "host" AND its
    evidence a verbatim run (>= 3 canonical tokens) of the SELECTED words themselves: evidence elsewhere in the window
    does not show who speaks the clip (audit C2 K10). -> bool."""
    import canon
    ev = a.get("speaker_evidence")
    if a.get("speaker_is") != "host" or not isinstance(ev, str):
        return False
    et = canon.canon_tokens(ev)
    inside = " ".join(re.findall(r"<selected>(.*?)</selected>", excerpt_text or "", flags=re.S))
    xt = canon.canon_tokens(inside)                # the evidence must lie INSIDE the selection (audit C2 K10)
    return len(et) >= 3 and any(xt[i:i + len(et)] == et for i in range(len(xt) - len(et) + 1))


def referent_outside(r):
    """Orchestrator 06:00 ruling 3: a referent is OUTSIDE only if the selected words give no antecedent or completing
    predicate ("inside" not true) AND resolving it differently would change what the speaker asserts (anything but an
    explicit "no"; an uncertain or missing answer fails, law L-m)."""
    return not isinstance(r, dict) or (r.get("inside") is not True and r.get("changes_assertion") != "no")


def a_failures(a):
    """The step-A half of the decision rule for one moment: [rule, ...] (empty = its own context passes)."""
    out = []
    if a.get("speaker_changes_inside") != "no":
        out.append("SPEAKER_CHANGE")
    if a.get("view") != "own_sincere":
        out.append("NOT_OWN_SINCERE")
    refs, conds = a.get("referents"), a.get("conditions")
    if not isinstance(refs, list) or any(referent_outside(r) for r in refs):
        out.append("REFERENT_OUTSIDE")
    if not isinstance(conds, list) or any(not isinstance(c, dict) or c.get("inside") is not True for c in conds):
        out.append("CONDITION_OUTSIDE")
    if a.get("retraction") != "none":
        out.append("RETRACTION")
    if a.get("time_ok") != "yes":                   # law L-v 3; a missing field is a failure (L-l, audit p2 C11)
        out.append("STALE_TIME")
    if a.get("certainty") not in CERTAINTY[:4]:
        out.append("UNCERTAIN")
    return out


def clips_alone(package):
    """The package with every VO line, the title and the caption removed: the clips as heard on their own (the
    baseline for STRONGER, orchestrator 05:25 item 3)."""
    return dict(package, title="", caption="", vo={"intro": "", "bridges": [], "bridges_after_clip": [], "signoff": ""})


def vo_words(package):
    """The video's own words for step C: the VO lines in the renderer's order, the title, the caption."""
    vo = package["vo"]
    lines = [f"TITLE: {_q(package.get('title') or '', 200)}", f"CAPTION: {_q(package.get('caption') or '', 400)}"]
    if vo.get("intro"):
        lines.append(f"VOICE-OVER after the hook: {_q(vo['intro'], 400)}")
    for a_, t in zip(list(vo.get("bridges_after_clip") or []), list(vo.get("bridges") or [])):
        lines.append(f"VOICE-OVER after clip {a_}: {_q(t, 400)}")
    return "\n".join(lines)


def raising_words_ok(words, package):
    """Step C's cited raising words are a verbatim run (>= 2 canonical tokens) of the video's own VO, title or caption
    (orchestrator 06:00 ruling 3)."""
    import canon
    if not isinstance(words, str) or not words.strip():
        return False
    wt = canon.canon_tokens(words)
    vo = package["vo"]
    texts = [package.get("title") or "", package.get("caption") or "", vo.get("intro") or ""] + list(vo.get("bridges") or [])
    return len(wt) >= 2 and any(any(tt[i:i + len(wt)] == wt for i in range(len(tt) - len(wt) + 1))
                                for tt in (canon.canon_tokens(t) for t in texts))


def outside_words(words, window_text):
    """Step C's named limit is the context's OWN words: a verbatim run (>= 2 canonical tokens) of the excerpt OUTSIDE
    the selected sentences (orchestrator 06:22 ruling 5: a limit the clip's words drop)."""
    import canon
    if not isinstance(words, str) or not words.strip():
        return False
    outside = re.sub(r"<selected>.*?</selected>", " | ", window_text or "", flags=re.S)
    wt = canon.canon_tokens(words)
    for part in outside.split(" | "):
        pt = canon.canon_tokens(part)
        if len(wt) >= 2 and any(pt[i:i + len(wt)] == wt for i in range(len(pt) - len(wt) + 1)):
            return True
    return False


def attributes_to(words, seg):
    """The cited words name this segment's show (channel) or its stated speaker: an attribution to it."""
    import canon
    wt = canon.canon_tokens(words or "")
    for name in (seg.get("channel"), seg.get("speaker")):
        nt = canon.canon_tokens(name or "")
        nt2 = [re.sub(r"['’]s$", "", t) for t in nt]
        wt2 = [re.sub(r"['’]s$", "", t) for t in wt]
        if nt2 and any(wt2[i:i + len(nt2)] == nt2 for i in range(len(wt2) - len(nt2) + 1)):
            return True
    return False


def _rank(c):
    return CERTAINTY.index(c) if c in CERTAINTY else len(CERTAINTY)


def check_contexts(router, package, contexts, writer_vendor, seed=7, a_by=None, writer_family=None,
                   require_all=False):
    """package: {"segments": [{"label", "video_id", "channel", "text"}], "vo": {"intro", "bridges",
    "bridges_after_clip", "signoff"}, "title", "caption"}; contexts: {label: {"text" (the window, the moment inside
    <selected>), "title", "channel"}} for the segments to judge (a segment without a context is judged only through the
    package: relations). a_by: step A items already screened (package-independent), by label.
    -> {"ok", "segments", "relations", "violations", "backends", "measured"}. A step that cannot be had or read fails
    and leaves the gate NOT measured (L-m); step B must rate EVERY pair of clips (audit p2 C5)."""
    import providers as P
    segs = package["segments"]
    labels = [s["label"] for s in segs if s["label"] in contexts]
    all_labels = [s["label"] for s in segs]
    out = {"segments": {}, "relations": [], "violations": [], "backends": {}, "measured": False, "replayed": False}
    V = lambda label, rule, detail: out["violations"].append({"segment": label, "rule": rule, "detail": detail})
    if not labels or (require_all and set(labels) != set(all_labels)):     # production: every segment (audit C2 K9)
        V("-", "CONTEXT_UNAVAILABLE", f"segments without their source context: "
                                      f"{sorted(set(all_labels) - set(labels)) or all_labels}")
        out["ok"] = False
        return out
    r0 = rb = rc = None
    try:
        if a_by is None:
            a_by, out["backends"]["A"] = step_a(router, {lb: contexts[lb] for lb in labels}, writer_vendor, seed,
                                                writer_family)
        else:
            missing = [lb for lb in labels if not isinstance(a_by.get(lb), dict) or set(A_KEYS) - set(a_by[lb])]
            if missing:
                raise ValueError(f"precomputed step A lacks {missing} or a field")
            a_by = {lb: a_by[lb] for lb in labels}
            out["backends"]["A"] = {lb: a_by[lb].get("backend") or "precomputed (unnamed)" for lb in labels}
        lab_list = ", ".join(all_labels)
        r0 = router.call("viewer_takeaway", STEP_B.format(package=package_view(clips_alone(package)), labels=lab_list),
                         3000, seed)
        out["backends"]["B0"] = r0.backend
        B0 = _strict(r0.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
                                                           "relations": ("labels", "relation")})
        b0_by = {t["label"]: t for t in B0["takeaways"] if isinstance(t.get("label"), str)}
        if not set(labels) <= set(b0_by):
            raise ValueError(f"step B (clips alone) must answer at least {labels}")
        rb = router.call("viewer_takeaway", STEP_B.format(package=package_view(package), labels=lab_list), 3000, seed,
                         avoid_vendor=writer_vendor, avoid_family=writer_family)
        out["backends"]["B"] = rb.backend
        B = _strict(rb.text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
                                                          "relations": ("labels", "relation")})
        b_by = {t["label"]: t for t in B["takeaways"] if isinstance(t.get("label"), str)}
        if not set(labels) <= set(b_by) or any(not isinstance(b_by[lb].get("asserts"), str) for lb in labels):
            raise ValueError(f"step B must answer at least {labels}")
        pairs_want = {frozenset(p) for p in itertools.combinations(all_labels, 2)}
        got = []
        for rel in B["relations"]:
            labs = rel.get("labels")
            if not isinstance(labs, list) or len(labs) != 2 or not all(isinstance(x, str) for x in labs) or \
                    labs[0] == labs[1] or rel.get("relation") not in RELATIONS:
                raise ValueError(f"step B relation out of contract: {json.dumps(rel)[:160]}")
            got.append(frozenset(labs))
        if len(got) != len(set(got)) or set(got) != pairs_want:
            raise ValueError(f"step B must rate every pair of clips exactly once ({len(pairs_want)} pairs, got "
                             f"{len(set(got))} distinct of {len(got)})")
        text_of = {sg["label"]: sg["text"] for sg in segs}
        pairs = "\n".join(f'<pair label="{lb}"><A>{_q(a_by[lb]["proposition"], 400)} (certainty: '
                          f'{a_by[lb]["certainty"]})</A><CLIP>{_q(text_of[lb], 900)}</CLIP><B>{_q(b_by[lb]["asserts"], 400)}'
                          f' (certainty: {b_by[lb]["certainty"]})</B></pair>' for lb in labels)
        rc = router.call("context_verdict", STEP_C.format(pairs=pairs, vo=vo_words(package)), 2000, seed,
                         avoid_vendor=writer_vendor, avoid_family=writer_family)
        out["backends"]["C"] = rc.backend
        C = _strict(rc.text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
                                                   "stronger_certainty", "raising_words")})
        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
            raise ValueError(f"step C must answer exactly the labels {labels}")
    except (P.ProviderError, P.SpendLimit, ValueError, KeyError, TypeError) as e:
        for r_ in (r0, rb, rc):
            if r_ is not None and isinstance(e, (ValueError, KeyError, TypeError)) and hasattr(router, "reject"):
                router.reject(r_)
        V("-", "CONTEXT_UNAVAILABLE", f"{type(e).__name__}: {str(e)[:240]}")
        out["ok"] = False
        return out
    out["measured"] = True
    out["replayed"] = any(bool(getattr(r_, "replayed", False)) for r_ in (r0, rb, rc))
    vid = {s["label"]: s["video_id"] for s in segs}
    segs_by = {s["label"]: s for s in segs}
    for lb in labels:
        a, b, c = a_by[lb], b_by[lb], c_by[lb]
        out["segments"][lb] = {"A": a, "B": b, "B0": b0_by[lb], "C": c, "window": (contexts[lb] or {}).get("window")}
        for rule in a_failures(a):
            if rule == "REFERENT_OUTSIDE":
                for r in a["referents"] if isinstance(a["referents"], list) else [None]:
                    if referent_outside(r):
                        V(lb, rule, f"{(r or {}).get('word')!r} -> {(r or {}).get('refers_to')!r} (changes the "
                                    f"assertion: {(r or {}).get('changes_assertion')!r})")
            elif rule == "CONDITION_OUTSIDE":
                for cnd in a["conditions"] if isinstance(a["conditions"], list) else [None]:
                    if not isinstance(cnd, dict) or cnd.get("inside") is not True:
                        V(lb, rule, f"{(cnd or {}).get('text')!r}")
            else:
                V(lb, rule, {"SPEAKER_CHANGE": f"speaker change inside: {a.get('speaker_changes_inside')}",
                             "NOT_OWN_SINCERE": f"view: {a.get('view')}",
                             "RETRACTION": str(a.get("retraction"))[:200],
                             "STALE_TIME": f"time words stale on the show date: {a.get('time_ok')}",
                             "UNCERTAIN": f"certainty A {a.get('certainty')}"}.get(rule, rule))
        if b["certainty"] not in CERTAINTY[:4]:
            V(lb, "UNCERTAIN", f"certainty B {b['certainty']}")
        limit = c.get("dropped_limit") if isinstance(c.get("dropped_limit"), str) else ""
        if c["entails"] == "uncertain" or (c["entails"] != "yes" and outside_words(limit, contexts[lb]["text"])):
            V(lb, "NOT_ENTAILED", f"entails: {c['entails']}; the context's limit the clip drops: {limit[:200]!r}")
        elif c["entails"] != "yes":                  # orchestrator 06:22 ruling 5: a scope difference without a limit
            out.setdefault("notes", []).append(
                f"{lb}: step C answers entails {c['entails']!r} but names no limit in the context's OWN words outside "
                f"the clip (named: {limit[:120]!r}): a NOTE, not NOT_ENTAILED (orchestrator 06:22 ruling 5)")
        added = c.get("added_by")
        if isinstance(added, str) and added.strip():
            if raising_words_ok(added, package) and attributes_to(added, segs_by[lb]):
                V(lb, "NOT_ENTAILED", f"the video's words {added!r} attribute to this speaker more than they asserted "
                                      f"in context")
            else:
                out.setdefault("notes", []).append(
                    f"{lb}: step C cites {added[:120]!r} as adding to the speaker, but those words are not the video's "
                    f"own or do not attribute anything to this speaker (no show or speaker name): a NOTE")
        if c["same_polarity"] != "yes":
            V(lb, "POLARITY", f"same polarity: {c['same_polarity']}")
        if c["stronger_certainty"] == "uncertain":
            V(lb, "STRONGER", "stronger certainty: uncertain")
        elif c["stronger_certainty"] != "no":
            cited = raising_words_ok(c.get("raising_words"), package)
            alone_certain = b0_by[lb]["certainty"] == "certain"      # the ruling's words: "the clip alone reads as certain"
            if cited and not alone_certain:
                V(lb, "STRONGER", f"stronger certainty: the video's words {c['raising_words']!r} make the clip sound "
                                  f"{b['certainty']} (in context {a['certainty']}; the clip alone "
                                  f"{b0_by[lb]['certainty']})")
            else:                                     # orchestrator 05:25 item 3 and 06:00 ruling 3
                out.setdefault("notes", []).append(
                    f"{lb}: step C reads the viewer's takeaway as firmer than the speaker in context ({a['certainty']} -> "
                    f"{b['certainty']}) but " + ("cites no words of the video that raise it" if not cited else
                                                  "the clip ALONE already sounds certain") +
                    ": a NOTE, not STRONGER (orchestrator 06:00 ruling 3: a STRONGER failure cites the exact VO / "
                    "title words that raise the certainty; an attribution verb firmer than the clip's hedge is "
                    "vo_fidelity's HEDGE rule)")
    for rel in B["relations"]:
        labs, kind = rel["labels"], rel["relation"]
        if kind == "none":
            continue
        if kind == "uncertain" or vid[labs[0]] != vid[labs[1]]:
            V("+".join(labs), "FALSE_RELATION", f"the package makes them look {kind}; they are not one conversation")
    out["relations"] = B["relations"]
    out["judged"] = labels
    out["ok"] = not out["violations"]
    return out
