#!/usr/bin/env python3
"""pipeline/canon.py — one canonical form for every text comparison (orchestrator order 2026-11-11 '21:10'; the class
behind E-FAIL-035 / 036 / 037: '$40 trillion', split tokens, HTML entities).
property  200 real sentences (tests/fixtures/canon_20261111, sampled from the saved transcripts) under each mutation
          compare EQUAL after canonicalisation: HTML entities, unicode quotes / dashes / ellipsis / nbsp, split
          tokens, currency and percent symbol vs words, digits vs number words up to trillions, decimals, ordinals,
          k / M / B suffixes, casing, trailing punctuation, hyphenation, apostrophes
          ... and real differences compare UNEQUAL: a different number, a dropped word, a different name
aligned   canon_aligned(words) yields the same tokens as canon(text), each owned by the word it starts in
sites     every comparison site goes through canon (TestSites: a grep over pipeline/*.py and qa_gates.py fails any
          ad-hoc normaliser outside canon.py)
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_canon.py"""
import glob
import html
import json
import os
import random
import re
import sys
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import canon as C  # noqa: E402

SENTS = [x["text"] for x in json.load(open(os.path.join(REPO, "tests", "fixtures", "canon_20261111",
                                                          "sentences.json")))["sentences"]]
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")]
ORDS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
        "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth",
        "twentieth"]


def words_int(n, hyphen=False):
    """An integer the way a speaker says it ('seventy four thousand', or 'seventy-four thousand')."""
    if n < 20:
        return ONES[n]
    if n < 100:
        t, u = divmod(n, 10)
        return TENS[t - 2] + (("-" if hyphen else " ") + ONES[u] if u else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + words_int(r, hyphen) if r else "")
    for v, name in SCALES:
        if n >= v:
            q, r = divmod(n, v)
            return words_int(q, hyphen) + " " + name + (" " + words_int(r, hyphen) if r else "")


def words_dec(x):
    i, d = str(x).split(".")
    return words_int(int(i)) + " point " + " ".join(ONES[int(c)] for c in d)


def ordinal_digits(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def insert(s, phrase, rng):
    """The phrase between neutral words, so an inserted spoken number never runs into a number word the sentence
    already has ('... one hundred twenty' + 'two real big areas' would be heard as 'twenty-two')."""
    w = s.split()
    k = rng.randrange(len(w) + 1)
    return " ".join(w[:k] + ["about", phrase, "units"] + w[k:])


def amounts(rng):
    """Integers across every magnitude up to trillions."""
    return [rng.choice([7, 13, 45, 99, 105, 999]), rng.randrange(1000, 99999), rng.randrange(10 ** 5, 10 ** 9),
            rng.randrange(1, 999) * 10 ** 9 + rng.randrange(0, 999) * 10 ** 6, rng.randrange(1, 99) * 10 ** 12]


class TestEquivalence(unittest.TestCase):
    def assert_pairs(self, pairs):
        bad = [(a, b, C.canon(a), C.canon(b)) for a, b in pairs if not C.same(a, b)]
        self.assertFalse(bad, bad[:3])

    def test_html_entities(self):
        self.assert_pairs([(html.escape(s, quote=True), s) for s in SENTS] +
                          [(insert(s, "the S&amp;P 500 and it&#39;s &quot;fine&quot;", random.Random(i)),
                            insert(s, "the S&P 500 and it's \"fine\"", random.Random(i))) for i, s in enumerate(SENTS)])

    def test_unicode_quotes_dashes_ellipsis_nbsp(self):
        def uni(s):
            s = s.replace("'", "’").replace(" - ", " – ").replace("...", "…")
            return re.sub(r" ", lambda m, c=[0]: " " if (c.__setitem__(0, c[0] + 1) or c[0] % 3 == 0) else " ", s)
        self.assert_pairs([(uni(s), s) for s in SENTS] + [(f"“{s}” — well…", f'"{s}" - well...')
                                                          for s in SENTS])

    def test_split_tokens(self):
        self.assert_pairs([(insert(s, "above $81 ,000 and 1 .3 percent in the U .S.", random.Random(i)),
                            insert(s, "above $81,000 and 1.3 percent in the U.S.", random.Random(i)))
                           for i, s in enumerate(SENTS)])

    def test_currency_and_percent_symbols_vs_words(self):
        pairs = []
        for i, s in enumerate(SENTS):
            rng = random.Random(i)
            n = rng.choice([5, 74, 81000, 40])
            pairs.append((insert(s, f"${n:,}", random.Random(i)), insert(s, f"{n:,} dollars", random.Random(i))))
            pairs.append((insert(s, f"${n} trillion", random.Random(i)), insert(s, f"{n} trillion dollars", random.Random(i))))
            pairs.append((insert(s, "5.5%", random.Random(i)), insert(s, "5.5 percent", random.Random(i))))
            pairs.append((insert(s, "$50%", random.Random(i)), insert(s, "50 percent", random.Random(i))))
        self.assert_pairs(pairs)

    def test_digits_vs_number_words_up_to_trillions(self):
        pairs = []
        for i, s in enumerate(SENTS):
            rng = random.Random(1000 + i)
            for n in amounts(rng):
                pairs.append((insert(s, f"{n:,}", random.Random(i)), insert(s, words_int(n, hyphen=i % 2 == 0),
                                                                           random.Random(i))))
        self.assert_pairs(pairs)

    def test_decimals(self):
        pairs = []
        for i, s in enumerate(SENTS):
            x = random.Random(i).choice(["1.66", "5.5", "0.3", "12.75", "2.05"])
            pairs.append((insert(s, x, random.Random(i)), insert(s, words_dec(x), random.Random(i))))
            pairs.append((insert(s, f"{x} billion", random.Random(i)), insert(s, f"{words_dec(x)} billion", random.Random(i))))
        self.assert_pairs(pairs)

    def test_ordinals(self):
        self.assert_pairs([(insert(s, f"the {ordinal_digits(n)} of November", random.Random(i)),
                            insert(s, f"the {ORDS[n - 1]} of November", random.Random(i)))
                           for i, s in enumerate(SENTS) for n in [random.Random(i).randrange(1, 21)]])

    def test_k_m_b_suffixes(self):
        pairs = []
        for i, s in enumerate(SENTS):
            r = random.Random(i)
            pairs.append((insert(s, "74k", r), insert(s, "74,000", random.Random(i))))
            pairs.append((insert(s, "1.5M", random.Random(i)), insert(s, "1,500,000", random.Random(i))))
            pairs.append((insert(s, "$1.66B", random.Random(i)), insert(s, "1.66 billion dollars", random.Random(i))))
        self.assert_pairs(pairs)

    def test_casing_trailing_punctuation_hyphens_apostrophes(self):
        pairs = []
        for s in SENTS:
            pairs += [(s.upper(), s), (s.title(), s), (s.rstrip(".!?,") + ".", s.rstrip(".!?,")),
                      (s + "?!", s), (s.replace("'", "’"), s)]       # curly = straight; "it's" != "its"
            w = s.split()
            if len(w) > 3:
                pairs.append((" ".join(w[:2]) + "-" + " ".join(w[2:]), s))
        self.assert_pairs(pairs)


class TestDifferences(unittest.TestCase):
    def test_a_different_number_a_dropped_word_a_different_name_stay_different(self):
        same = []
        for i, s in enumerate(SENTS):
            rng = random.Random(i)
            n = rng.choice(amounts(rng))
            for a, b in ((insert(s, f"{n:,}", random.Random(i)), insert(s, f"{n + 1:,}", random.Random(i))),
                         (insert(s, words_int(n), random.Random(i)), insert(s, f"{n * 10:,}", random.Random(i)))):
                if C.same(a, b):
                    same.append((a, b))
            w = s.split()
            k = next((j for j, x in enumerate(w) if re.search(r"[A-Za-z0-9]{2}", x)), None)
            if k is not None and C.same(s, " ".join(w[:k] + w[k + 1:])):
                same.append((s, "dropped " + w[k]))
            if C.same(insert(s, "Natalie Brunell", random.Random(i)), insert(s, "Yahoo Finance", random.Random(i))):
                same.append((s, "name"))
            if C.same(insert(s, "it's", random.Random(i)), insert(s, "its", random.Random(i))):
                same.append((s, "it's / its"))                       # different words (cross-LLM M1)
            if len(w) > 4:                                           # an INTERIOR word dropped (claude-fable #6)
                j = len(w) // 2
                if re.search(r"[A-Za-z0-9]{2}", w[j]) and C.same(s, " ".join(w[:j] + w[j + 1:])):
                    same.append((s, "dropped interior " + w[j]))
            for a, b in (("one and two", "one two"), ("5 percent", "5 dollars"), ("not", "now")):
                if C.same(insert(s, a, random.Random(i)), insert(s, b, random.Random(i))):
                    same.append((s, f"{a} / {b}"))
        self.assertFalse(same, same[:3])


class TestAuditBatch16(unittest.TestCase):
    """gpt-6.1-sol on batch 16: a dropped 'and' between two numbers, signs in other layouts, and a number's span."""

    def test_a_conjunction_is_only_consumed_inside_a_compound_number(self):
        self.assertFalse(C.same("one and two", "one two"))
        self.assertFalse(C.same("twenty and five", "twenty five"))
        self.assertTrue(C.same("one hundred and two", "102"))
        self.assertTrue(C.same("two thousand and five", "2005"))

    def test_every_sign_layout_keeps_its_sign(self):
        for a, b in (("- 5%", "+ 5%"), ("$-5", "$+5"), ("\u22125%", "+5%"), ("(-$40M)", "($40M)"),
                     ("prices: - 5%", "prices: + 5%"), ("up +5%", "up 5%")):
            self.assertFalse(C.same(a, b), (a, b))
        for a, b in (("\u22125%", "-5%"), ("- 5% today", "minus five percent today"), ("$-5", "minus 5 dollars")):
            self.assertTrue(C.same(a, b), (a, b))
        for t in ("5-10%", "2026-11-11", "70 - 75", "well-known"):     # ranges, dates, hyphens: no sign
            self.assertNotIn("minus", C.canon_tokens(t), t)

    def test_a_number_spans_every_word_it_read(self):
        self.assertEqual(C.canon_spans("at seventy four thousand dollars".split()),
                         [("at", 0, 0), ("74000", 1, 3), ("dollars", 4, 4)])
        self.assertEqual(C.canon_spans(["up", "$81", ",000", "today"]),
                         [("up", 0, 0), ("81000", 1, 2), ("dollars", 2, 2), ("today", 3, 3)])

    def test_a_lock_ending_on_a_spelled_number_ends_on_its_last_word(self):
        import sentence_law as L
        ws = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25}
              for i, w in enumerate("So bitcoin is now at seventy four thousand. Then it fell.".split())]
        self.assertEqual(L.anchor(ws, "bitcoin is now at seventy four thousand")[:2], (1, 7))
        self.assertEqual(L.anchor(ws, "Bitcoin is now at 74,000.")[:2], (1, 7))


class TestAligned(unittest.TestCase):
    def test_aligned_tokens_equal_text_tokens_and_owners_are_source_words(self):
        bad = []
        for i, s in enumerate(SENTS):
            for t in (s, insert(s, "above $81 ,000 and 74 000 people and $40 trillion", random.Random(i))):
                words = t.split()
                pairs = C.canon_aligned(words)
                if [p for p, _ in pairs] != C.canon_tokens(t) or any(not 0 <= o < len(words) for _, o in pairs):
                    bad.append(t)
        self.assertFalse(bad, bad[:2])

    def test_an_amount_is_owned_by_its_words(self):
        self.assertEqual(C.canon_aligned("above $40 trillion .".split()),
                         [("above", 0), ("40000000000000", 1), ("dollars", 2)])
        self.assertEqual(C.canon_aligned(["up", "$81", ",000", "today"]),      # the amount spans words 1-2; the
                         [("up", 0), ("81000", 1), ("dollars", 2), ("today", 3)])  # spoken 'dollars' follows word 2


class TestSites(unittest.TestCase):
    """Every comparison site goes through canon (orchestrator 21:10 'a grep test failing any site not using it'):
    no ad-hoc normaliser in the pipeline's code (pipeline/*.py except tests, segment_v1/qa_gates.py). Allowed:
    canon.py itself, and transcript_store.read_text's html.unescape (the acquisition reader that stores the
    words as spoken, law L-h; it is not a comparison)."""
    FORBIDDEN = [r"\.lower\(\)\.replace\(", r"re\.sub\(\s*r?[\"']\[\^\\w", r"re\.split\(\s*r?[\"']\[\^a-z0-9",
                 r"re\.(sub|split|findall)\(\s*r?[\"']\[\^?a-z0-9",
                 r"unicodedata\.normalize\(", r"html\.unescape\(", r"str\.maketrans\(", r"\.casefold\(\)",
                 r"translate\(str\.maketrans"]
    ALLOWED = {("transcript_store.py", "html.unescape(")}

    def test_no_ad_hoc_normaliser_outside_canon(self):
        files = [f for f in glob.glob(os.path.join(PIPELINE, "*.py"))
                 if not os.path.basename(f).startswith("test_") and os.path.basename(f) != "canon.py"]
        files.append(os.path.join(REPO, "segment_v1", "qa_gates.py"))
        bad = []
        for f in files:
            for n, line in enumerate(open(f, encoding="utf-8"), 1):
                code = line.split("#", 1)[0]
                for pat in self.FORBIDDEN:
                    m = re.search(pat, code)
                    if m and (os.path.basename(f), m.group(0)) not in self.ALLOWED:
                        bad.append(f"{os.path.relpath(f, REPO)}:{n}: {line.strip()[:120]}")
        self.assertFalse(bad, "ad-hoc text normaliser outside pipeline/canon.py:\n" + "\n".join(bad))

    def test_the_comparison_sites_import_canon(self):
        """The named comparison sites (quote verification, selection anchors, edge words, G3 / G3b, G18,
        sign-off names, ledger statements, approved PIN text, G1 / G13 VO text) call canon."""
        sites = ["story_semantics.py", "editorial_select.py", "sentence_law.py", "word_diff.py", "gates.py",
                 "editorial_gate.py", "cut_accept.py", "stand_alone.py", "punctuation.py", "pinned.py"]
        imp = re.compile(r"^\s*(import canon\b|from canon import)", re.M)   # an import, not the word 'canonical'
        missing = [f for f in sites if not imp.search(open(os.path.join(PIPELINE, f)).read())]
        if not imp.search(open(os.path.join(REPO, "segment_v1", "qa_gates.py")).read()):
            missing.append("segment_v1/qa_gates.py")
        self.assertFalse(missing, missing)


if __name__ == "__main__":
    unittest.main()
