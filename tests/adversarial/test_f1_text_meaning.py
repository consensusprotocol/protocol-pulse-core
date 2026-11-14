"""FAMILY 1 - text / meaning fuzz (law L-k: one canonical form; two strings a listener hears as the same words
compare equal, a different number, unit, sign, name, negation or dropped word never does).

Seeded generator (hypothesis is not installed): adv_helpers.gen_cases builds finance sentences, their SURFACE
variants (entities &#39; &amp; &quot;, unicode quotes / dashes, split tokens '$81 ,000', '$40 trillion' vs '40
trillion dollars', number words vs digits, case, punctuation, no-break spaces) and their MEANING mutants ($81,000
vs $18,000, 16% vs 60%, has vs hasn't, million vs billion vs trillion, Fed vs Treasury, -5% vs +5%, percent vs
dollars). Every comparator that uses the canonical form is exercised through its public entry point:
  canon.same / canon_tokens            the form itself (+ idempotence)
  word_diff.diff / gate_g18            G18 word-for-word (fake transcriber, no Whisper)
  story_semantics.quote_in / adjudicate quote verification (fake model at the HTTP seam)
  editorial_select.align_quote          selection anchor of a verified quote
  sentence_law.anchor                   the selection lock's anchor
  telegram.headline_numbers_said        the drop's headline numbers vs G18's readings
  gates.spoken_channels / gate_g20      sign-off names (L-a)
  qa_gates.gate_g3b                     G3b's last word / leak (readings injected, no Whisper)
A strict xfail names the red-team finding it pins and the request in docs/audits/parallel/pp-tests_REQUESTS.md.
"""
import json
import os

import pytest

import adv_helpers as H

SEED = 20261112
CASES = H.gen_cases(SEED, 600)
ANCHOR_CASES = CASES[:120]          # SequenceMatcher-heavy sites: 20 of each kind (every mutant kind)


def _pairs(cases, kind):
    if kind == "equal":
        return [(c, v) for c in cases for v in c.variants]
    return [(c, (lab, m)) for c in cases for lab, m in c.mutants]


# ─────────────────────────────── the canonical form itself ───────────────────────────────

class TestCanonicalForm:
    def test_surface_variants_compare_equal(self):
        import canon
        bad = [(c.base, v) for c, v in _pairs(CASES, "equal") if not canon.same(v, c.base)]
        assert not bad, bad[:5]

    def test_meaning_mutants_compare_unequal(self):
        import canon
        bad = [(c.kind, lab, m) for c, (lab, m) in _pairs(CASES, "mutant") if canon.same(m, c.base)]
        assert not bad, bad[:5]

    @pytest.mark.parametrize("a,b", [
        ("$81,000", "$18,000"), ("16%", "60%"), ("sixteen percent", "sixty percent"), ("it has broken out",
         "it hasn't broken out"), ("$1.66 million", "$1.66 billion"), ("$1.66 billion", "$1.66 trillion"),
        ("40 million dollars", "40 trillion dollars"), ("the Fed said", "the Treasury said"), ("-5%", "+5%"),
        ("5%", "$5"), ("eighty one thousand", "eighteen thousand"), ("5.5%", "5%"), ("$81,000", "$181,000")])
    def test_named_collisions_stay_different(self, a, b):
        import canon
        assert not canon.same(a, b), (canon.canon_tokens(a), canon.canon_tokens(b))

    @pytest.mark.parametrize("a,b", [
        ("$40 trillion", "40 trillion dollars"), ("it&#39;s S&amp;P &quot;fine&quot;", "it's S&P \"fine\""),
        ("$81 ,000", "$81,000"), ("“Bitcoin” — it’s up", "\"Bitcoin\" - it's up"),
        ("eighty one thousand dollars", "$81,000"), ("eighty-one thousand dollars", "$81k"),
        ("sixteen percent", "16%"), ("$1.66B", "1.66 billion dollars"), ("minus five percent", "-5%"),
        ("74 000", "74,000"), ("U .S.", "U.S."), ("above $74,000 dollars", "above 74,000 dollars")])
    def test_named_equivalences_compare_equal(self, a, b):
        import canon
        assert canon.same(a, b), (canon.canon_tokens(a), canon.canon_tokens(b))

    def test_idempotent_on_generated_and_real_sentences(self):
        """canon(canon(x)) == canon(x) for every generated sentence, variant, mutant and the 200 real
        sentences of tests/fixtures/canon_20261111."""
        import canon
        real = [x["text"] for x in json.load(open(os.path.join(H.REPO, "tests", "fixtures", "canon_20261111",
                                                                "sentences.json")))["sentences"]]
        texts = real + [c.base for c in CASES] + [v for c, v in _pairs(CASES, "equal")] + \
            [m for c, (_, m) in _pairs(CASES, "mutant")]
        bad = [t for t in texts if canon.canon_tokens(canon.canon(t)) != canon.canon_tokens(t)]
        assert not bad, bad[:5]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="PP-01 (new, idempotence): two adjacent spoken numbers re-merge on a "
                                           "second pass (_SPACED_THOUSANDS); REQUESTS.md R-01")
    def test_idempotent_on_adjacent_spoken_numbers(self):
        """Speech often puts two numbers side by side ('two, three hundred dollars'): canon reads them as 2 and
        300, but canon of that canonical text reads 2300. The canonical form must be a fixpoint."""
        import canon
        bad = []
        for t in H.load_fixture("text_cases.json")["adjacent_numbers"]:
            once = canon.canon_tokens(t)
            twice = canon.canon_tokens(canon.canon(t))
            if once != twice:
                bad.append((t, once, twice))
        assert not bad, bad


# ─────────────────────────────── G18 word-for-word ───────────────────────────────

class TestG18:
    def test_diff_equal_variants_and_unequal_mutants(self):
        import word_diff as WD
        bad = [("equal", c.base, v) for c, v in _pairs(CASES, "equal") if WD.diff(c.base, v)]
        bad += [("mutant", lab, m) for c, (lab, m) in _pairs(CASES, "mutant") if not WD.diff(c.base, m)]
        assert not bad, bad[:5]

    def test_edges_see_a_changed_edge_word(self):
        import word_diff as WD
        assert WD.edges("Bitcoin closed above $81,000.", "bitcoin closed above eighty one thousand dollars") == []
        assert WD.edges("Bitcoin closed above $81,000.", "bitcoin closed above $18,000") != []
        assert WD.edges("It has not broken out.", "it has not broken") != []        # a lost last word
        assert WD.edges("It has not broken out.", "it has broken out") == []        # edges see edges only: the
        assert WD.diff("It has not broken out.", "it has broken out") != []         # middle is diff's job

    @pytest.mark.parametrize("heard,ok", [
        ("Bitcoin closed above eighty one thousand dollars after a quiet weekend in Asia.", True),
        ("Bitcoin closed above $81 ,000 after a quiet weekend in Asia.", True),
        ("Bitcoin closed above $18,000 after a quiet weekend in Asia.", False),
        ("Bitcoin closed above $81,000 after a quiet weekend in Asia. All right", False),
        ("closed above $81,000 after a quiet weekend in Asia.", False)])
    def test_gate_g18_through_its_public_entry(self, heard, ok, tmp_path):
        """gate_g18 with an injected transcriber: the final's segment reads `heard`, the source span reads the
        lock (a faithful source)."""
        import word_diff as WD
        lock = "Bitcoin closed above $81,000 after a quiet weekend in Asia."

        class T:
            def span(self, media, t0, t1):
                return heard if media == "final.mp4" else lock
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 5.0}]
        clips = {"hook": {"lock_text": lock, "source": "src.mp4", "cut_in": 1.0, "cut_out": 6.0}}
        got, rows = WD.gate_g18("final.mp4", segs, clips, transcriber=T())
        assert got is ok, rows


    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-cut F08 (OPEN, D): a meaningful middle-word mismatch against the "
                                           "selection lock is report-only; REQUESTS.md R-16")
    def test_gate_g18_fails_a_number_that_differs_from_the_lock(self):
        """The source span and the final agree with each other ('$18,000') but not with the editor's locked
        sentence ('$81,000'): the edges match, so only the reported lock diff sees it."""
        import word_diff as WD
        lock = "Bitcoin closed above $81,000 after a quiet weekend in Asia."
        said = "Bitcoin closed above $18,000 after a quiet weekend in Asia."

        class T:
            def span(self, media, t0, t1):
                return said
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 5.0}]
        ok, rows = WD.gate_g18("final.mp4", segs, {"hook": {"lock_text": lock, "source": "src.mp4", "cut_in": 1.0,
                                                            "cut_out": 6.0}}, transcriber=T())
        H.control(bool(rows[0]["lock_diff_reported"]), f"G18 reports the lock difference: {rows}")
        assert ok is False, rows

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-cut F22 (OPEN): with duplicate manifest labels G18 checks only the "
                                           "last occurrence; REQUESTS.md R-17")
    def test_gate_g18_checks_every_occurrence_of_a_label(self):
        import word_diff as WD
        lock = "Bitcoin closed above $81,000 after a quiet weekend in Asia."
        calls = []

        class T:
            def span(self, media, t0, t1):
                calls.append((media, t0))
                return "completely different words were heard here" if (media, t0) == ("final.mp4", 0.0) else lock
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 5.0},
                {"label": "hook", "type": "talking_head", "start": 5.0, "end": 10.0}]
        clips = {"hook": {"lock_text": lock, "source": "src.mp4", "cut_in": 1.0, "cut_out": 6.0}}
        WD.gate_g18("final.mp4", segs[:1], clips, transcriber=T())          # control (integrator, R-17 pin): the
        H.control(("final.mp4", 0.0) in calls, f"the gate reads a segment at 0.0 s as {calls}")   # stub's key is
        calls.clear()                                                        # what the gate asks for
        ok, rows = WD.gate_g18("final.mp4", segs, clips, transcriber=T())
        assert ok is False, rows


# ─────────────────────────────── quote verification ───────────────────────────────

class TestQuoteVerification:
    def test_variants_verified_mutants_refused(self):
        import story_semantics as SM
        bad = [("equal", v) for c, v in _pairs(CASES, "equal") if not SM.quote_in(v, [H.in_context(c.base)])]
        bad += [("mutant", lab, m) for c, (lab, m) in _pairs(CASES, "mutant")
                if SM.quote_in(m, [H.in_context(c.base)])]
        assert not bad, bad[:5]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="Grok47-select F4 (OPEN): quote_in is a character substring test on "
                                           "canonical text; REQUESTS.md R-02")
    def test_a_quote_never_matches_inside_a_longer_word_or_number(self):
        """'$81,000 by the weekend' is not said in '$181,000 by the weekend'; 'coin fell below ...' is not
        said in 'Bitcoin fell below ...'; '... fell 16' is not said in '... fell 160 percent'."""
        import story_semantics as SM
        hits = [(q, t) for q, t in H.load_fixture("text_cases.json")["substring_traps"] if SM.quote_in(q, [t])]
        assert not hits, hits

    # (R-19's pin, 'a compound name written apart is the same quote', was removed from the wall: integrator B3,
    # 2026-11-12. It could only clear by LOOSENING what the quote check accepts; R-19 is withdrawn pending an
    # orchestrator decision, pp-tests_REQUESTS.md.)

    def test_an_empty_or_short_quote_is_never_verified(self):
        """quote_in's minimum (5 canonical tokens) stays (integrator B4): R-02 / R-03's token-run rewrite must keep
        it, because a token run of an EMPTY quote occurs in every text. Each short quote below is said verbatim in
        the text, so only the minimum refuses it; the 5-token control proves the text is otherwise found."""
        import canon
        import story_semantics as SM
        text = "Bitcoin ETFs saw heavy outflows last week as investors pulled money."
        H.control(SM.quote_in("Bitcoin ETFs saw heavy outflows", [text]), "a 5-token quote said in the text is found")
        short = ["", "   ", ".", "?!", "Bitcoin", "Bitcoin ETFs", "saw heavy outflows", "ETFs saw heavy outflows"]
        H.control(all(len(canon.canon_tokens(q)) < 5 for q in short), "every quote below has < 5 canonical tokens")
        verified = [q for q in short if SM.quote_in(q, [text]) or SM.quote_in(q, [text, ""]) or SM.quote_in(q, [""])]
        assert not verified, verified

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="Grok47-select F19 (OPEN): a quote may straddle two excerpts; "
                                           "REQUESTS.md R-03")
    def test_a_quote_never_straddles_two_excerpts(self):
        import story_semantics as SM
        a = "The ETF saw heavy selling on Friday and the flows turned negative."
        b = "Bitcoin is up four percent this morning on strong demand."
        quote = "flows turned negative. Bitcoin is up four percent"
        H.control(SM.quote_in("and the flows turned negative", [a]), "inside one excerpt the quote is found")
        assert not SM.quote_in(quote, [a, b])

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F05 (OPEN): supporting chunk ids are not bound to the "
                                           "verified quote; REQUESTS.md R-04")
    def test_adjudicate_counts_a_quote_only_with_the_chunk_that_says_it(self):
        """adjudicate (public) with a fake model at the HTTP seam: the model names excerpt A as support but the
        quote is only in excerpt B. Counted coverage must rest on the chunk that says the quote."""
        import story_semantics as SM
        ex = [{"chunk_id": "vidA:0010-0040", "text": "Gold was flat and the euro barely moved this week."},
              {"chunk_id": "vidA:0300-0330",
               "text": "Bitcoin ETFs saw one point six six billion dollars of outflows last week."}]
        adj = {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["vidA:0010-0040"],
               "evidence_quote": "Bitcoin ETFs saw one point six six billion dollars of outflows",
               "confidence": 0.9, "reason": "x"}
        sup = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "x"}
        llm = H.fake_llm([json.dumps(adj), json.dumps(sup)])
        q = {"underlying_event": "Bitcoin ETFs saw $1.66B of net outflows last week", "action": "outflows",
             "affected_object": "Bitcoin ETFs", "entities": [{"name": "Bitcoin ETFs"}], "must_not_confuse_with": []}
        quote = adj["evidence_quote"]                  # the precondition, independent of adjudicate (integrator,
        H.control(SM.quote_in(quote, [ex[1]["text"]]) and not SM.quote_in(quote, [ex[0]["text"]]),   # R-04 control:
                  "the quote is said in excerpt B and not in excerpt A")       # quote_verified changes WITH the fix)
        v = SM.adjudicate(llm, q, {"title": "t", "channel": "c", "published_at": "2026-11-11"}, ex, today="2026-11-12")
        H.control(v["verdict"] == "CURRENT_EVENT" and v["supporting_chunk_ids"] == ["vidA:0010-0040"],
                  f"the fake reply reached the decision: {v}")
        assert not v["counted_as_same_event"], v


# ─────────────────────────────── selection anchors ───────────────────────────────

class TestSelectionAnchors:
    def test_surface_variants_anchor_on_the_sentence(self):
        import editorial_select as ES
        import sentence_law as L
        bad = []
        for c, v in _pairs(ANCHOR_CASES, "equal"):
            words = H.words_of(H.in_context(c.base))
            if ES.align_quote(v, words, 0.0, 1e9) is None:
                bad.append(("align_quote", v))
            if L.anchor(words, v) is None:
                bad.append(("anchor", v))
        assert not bad, bad[:5]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F04 / GPT-cut F06 (OPEN, D): a fuzzy anchor changes a "
                                           "number, negation, sign, unit or name; REQUESTS.md R-05")
    def test_align_quote_never_moves_a_quote_onto_a_different_claim(self):
        import editorial_select as ES
        accepted = [(c.kind, lab, m) for c, (lab, m) in _pairs(ANCHOR_CASES, "mutant")
                    if ES.align_quote(m, H.words_of(H.in_context(c.base)), 0.0, 1e9) is not None]
        assert not accepted, (len(accepted), accepted[:6])

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-cut F06 / GPT-select F04 (OPEN, D): the selection lock is made "
                                           "on words that say something else; REQUESTS.md R-05")
    def test_sentence_law_anchor_never_locks_a_different_claim(self):
        import sentence_law as L
        accepted = [(c.kind, lab, m) for c, (lab, m) in _pairs(ANCHOR_CASES, "mutant")
                    if L.anchor(H.words_of(H.in_context(c.base)), m) is not None]
        assert not accepted, (len(accepted), accepted[:6])


# ─────────────────────────────── the drop's headline numbers ───────────────────────────────

def _snap(headline, heard):
    return {"edl": {"headline": headline, "topic": headline},
            "report": {"G18": {f: [{"segment": "hook", "heard": heard}] for f in ("16x9", "9x16")}}}


class TestHeadlineNumbers:
    NUMERIC = ("dollars", "percent", "scale", "sign")

    def test_a_headline_number_said_in_any_written_form_is_said(self):
        import telegram as T
        bad = []
        for c in CASES[:240]:
            if c.kind not in self.NUMERIC:
                continue
            for v in c.variants:
                miss = T.headline_numbers_said("", _snap(c.base, v))
                if miss:
                    bad.append((c.base, v, miss))
        assert not bad, bad[:5]

    def test_a_different_number_sign_or_unit_is_not_said(self):
        import telegram as T
        bad = []
        for c in CASES[:240]:
            if c.kind not in self.NUMERIC:
                continue
            for lab, m in c.mutants:
                if not T.headline_numbers_said("", _snap(c.base, m)):
                    bad.append((c.base, lab, m))
        assert not bad, bad[:5]

    def test_actor_swap_in_a_numeric_headline_is_not_said(self):
        import telegram as T
        assert T.headline_numbers_said("", _snap("Treasury yields climb 5% on Monday",
                                                 "the fed yields climb five percent on monday")) != []
        assert T.headline_numbers_said("", _snap("Treasury yields climb 5% on Monday",
                                                 "treasury yields climb five percent on monday")) == []


# ─────────────────────────────── sign-off names (G20, law L-a) ───────────────────────────────

def _registry():
    return json.load(open(os.path.join(H.REPO, "pipeline", "channels.json")))


class TestSignoffNames:
    @pytest.mark.parametrize("text", [
        "Big thanks to DataDash, Natalie Brunell, Yahoo Finance &amp; Bitcoin Magazine for the clips today.",
        "BIG THANKS TO DATADASH, NATALIE BRUNELL, YAHOO FINANCE AND BITCOIN MAGAZINE. FOLLOW THEM ALL.",
        "Big thanks to Data‑Dash, Natalie Brunell’s show, Yahoo Finance, and Bitcoin Magazine.",
        "Big thanks to DataDash, Natalie Brunel, Yahoo Finance, and Bitcoin Magazine for the clips today."])
    def test_every_credited_name_heard_in_any_surface_form(self, text):
        import gates as G
        cred = ["DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"]
        assert G.spoken_channels(text, _registry(), cred) == set(cred)

    def test_a_missing_name_is_missing(self):
        import gates as G
        cred = ["DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"]
        heard = G.spoken_channels("Clips today from Natalie Brunell, Yahoo Finance, and Bitcoin Magazine. Go "
                                  "follow them for more.", _registry(), cred)
        assert heard == set(cred) - {"DataDash"}

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-gates F17 (OPEN): G20 hears another registry channel's name as "
                                           "the credited one; REQUESTS.md R-06")
    @pytest.mark.parametrize("credited,spoken", [
        ("Bitcoin Magazine", "Bitcoin Magazine Pro"), ("Bitcoin Magazine Pro", "Bitcoin Magazine"),
        ("Coffeezilla", "Coffeezilla Extras"), ("CNBC", "CNBC Television")])
    def test_a_different_channel_variant_is_not_the_credited_channel(self, credited, spoken):
        import gates as G
        heard = G.spoken_channels(f"Big thanks to {spoken} for the clips today. Follow them for more.",
                                  _registry(), [credited])
        assert credited not in heard, heard

    def test_a_shorter_spoken_name_is_not_a_longer_credited_name(self):
        import gates as G
        assert G.spoken_channels("Big thanks to Real Vision for the clips today. Follow them for more.",
                                 _registry(), ["Real Vision Finance"]) == {"Real Vision"}

    def test_gate_g20_public_entry_names_all_and_fails_a_missing_one(self, tmp_path, monkeypatch):
        import gates as G
        import qa_gates as Q
        final = H.make_media(str(tmp_path / "final.mp4"), dur=4.0)
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 2.0},
                {"label": "shoutout", "type": "shoutout", "start": 2.0, "end": 4.0}]
        cred = ["DataDash", "Natalie Brunell"]
        for text, ok in (("Big thanks to DataDash and Natalie Brunell for the clips.", True),
                         ("Big thanks to Natalie Brunell for the clips.", False),
                         ("", False)):
            monkeypatch.setattr(Q, "whisper_segment", lambda wav, qa, t=text: t)
            got, det = G.gate_g20(final, segs, cred, str(tmp_path))
            assert got is ok, (text, det)


# ─────────────────────────────── G3b last word / leak ───────────────────────────────

def _g3b(tmp_path, monkeypatch, lock_text, readings, next_word=None):
    import gates  # noqa: F401  (LAW 24: a fix pipeline/gates.py installs ON qa_gates at import applies here too)
    import qa_gates as Q
    final = str(tmp_path / "final.mp4")
    if not os.path.exists(final):
        H.make_media(final, dur=6.0)
    edl = {"hook": {"channel": "DataDash", "video_id": "v1", "selection_lock": {"text": lock_text}}, "clips": []}
    if next_word is not None:
        edl["hook"]["next_source_word"] = next_word
    p = tmp_path / "edl.json"
    p.write_text(json.dumps(edl))
    seq = list(readings)
    monkeypatch.setattr(Q, "whisper_segment", lambda wav, qa: seq.pop(0) if len(seq) > 1 else seq[0])
    segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 5.0}]
    return Q.gate_g3b(final, segs, str(tmp_path), edl_path=str(p))


class TestG3b:
    def test_written_and_spoken_amount_is_the_same_last_word(self, tmp_path, monkeypatch):
        ok, t = _g3b(tmp_path, monkeypatch, "Its market cap sits above $40 trillion.",
                     ["sits above 40 trillion dollars.", "sits above $40 trillion.", "above forty trillion dollars"])
        assert ok, t

    def test_a_clipped_last_word_fails(self, tmp_path, monkeypatch):
        ok, t = _g3b(tmp_path, monkeypatch, "how the market shapes up this week.",
                     ["how the market shapes up this", "shapes up this", "the market shapes up"])
        assert not ok, t

    def test_a_leaked_next_word_fails(self, tmp_path, monkeypatch):
        ok, t = _g3b(tmp_path, monkeypatch, "how the market shapes up this week.",
                     ["shapes up this week. All", "shapes up this week all", "this week. All"], next_word="All")
        assert not ok, t

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-gates F15 (OPEN): G3b's match is 'expected in heard' (a "
                                           "substring); REQUESTS.md R-07")
    def test_a_longer_word_containing_the_last_word_is_a_different_word(self, tmp_path, monkeypatch):
        ok, t = _g3b(tmp_path, monkeypatch, "how the market shapes up this week.",
                     ["shapes up this weekend.", "shapes up this weekend", "up this weekend."])
        assert not ok, t

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-gates F16 / Claude-gates T2 (OPEN): the leak check anchors on "
                                           "the LAST match, so a next word equal to the last word hides; "
                                           "REQUESTS.md R-08")
    def test_a_next_word_equal_to_the_last_word_still_leaks(self, tmp_path, monkeypatch):
        """'... rose again this week. Week after week ...': the cut leaked 'Week'."""
        ok, t = _g3b(tmp_path, monkeypatch, "Bitcoin rose again this week.",
                     ["rose again this week. Week", "again this week week", "this week. Week"], next_word="Week")
        assert not ok, t
