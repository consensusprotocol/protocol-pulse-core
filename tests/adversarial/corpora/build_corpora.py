"""Builds the moments-first exam (format v1, docs/audits/parallel/pp-tests_STATE.md) from the editorial store.

    python3 tests/adversarial/corpora/build_corpora.py [out_dir]     # the three corpora + INDEX.json files

Every REAL case names its store record (path + sha256) and sentence ids; every window / moment / context / adjacent
clip is the record's own sentences, verbatim (store_extract.py). The only words written here are the PACKAGE (title,
caption, VO) and the expected verdict with its reason: that is the stimulus a gate is examined on.

origin=REAL: every source sentence comes from the store and the class's trap is in that real material (for the two
package classes, false_dialogue and title_adds_thesis, the clips are real and clean and the trap is the sequence,
bridge or title by definition). origin=CONSTRUCTED: the class has no real instance in the store (exclusions
partner_attack and guaranteed_return only; the searches that found none are in each case), so the moment is written
here; it carries the same fields as a real case, and its surrounding show talk is neutral filler.

Audit rules applied (two cycles + frontier reviews + verification round, 2026-11-12):
- the package format never separates the verdicts: VO intro / bridge / sign-off, clip order, VO intro citations and
  the B-clip line are drawn by hash from ONE pool for pass and fail cases alike (a class whose trap IS the bridge or
  the order departs from it); every caption is dated; every window is the order's 90 s before / 60 s after;
- a must-pass moment is a single narrator's line or one sentence of an interview, credited to the SHOW (a channel
  named after a person is "<name>'s show"); the one person named is verified by the source description and by his
  own words inside the window; every hedge is kept; an And / So / But opener goes first in its package;
- a must-fail package carries no defect but its class; where the real material carries a second trap by nature
  (a consequence clause's 'that', a quoted opponent's accusation) the case says so in expected.also;
- the one correction that lands beyond the 60 s window is stratum 'beyond_window', reported apart from the
  thresholds (request R-24);
- INDEX.json carries no answer and lists cases in hash order."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import store_extract as X  # noqa: E402

SHOW = "Pulse Check"
SHOW_DATE = "2026-11-12"
MINED = "2026-11-12"
BEFORE_S, AFTER_S = 90.0, 60.0

INTROS = ("From {ch}.", "{ch} first.", "Here's {ch}.", "Starting with {ch}.", "First, {ch}.")
BRIDGES = ("And on {ch}:", "{ch}:", "Over to {ch}.", "Next, {ch}.", "From {ch}:", "Also on the record, {ch}:",
           "Now {ch}.")
SIGNOFFS = ("That's Pulse Check.", "That's the Pulse Check.", "Pulse Check, out.")

# ── clean real clips ──
POOL = {
    # single narrators
    "swan_sold": ("w4h9HfP7Gb0", "whisper_words", 11, 11),
    "swan_ai": ("w4h9HfP7Gb0", "whisper_words", 13, 13),
    "swan_thesis": ("w4h9HfP7Gb0", "whisper_words", 17, 17),
    "swan_questioning": ("w4h9HfP7Gb0", "whisper_words", 9, 9),
    "swan_betting": ("w4h9HfP7Gb0", "whisper_words", 19, 19),
    "swan_drop": ("w4h9HfP7Gb0", "whisper_words", 3, 3),
    "cb_drop": ("UJFQBaMh3yg", "whisper_words", 20, 20),
    "cb_midterms": ("UJFQBaMh3yg", "whisper_words", 12, 12),
    "cb_nov3": ("n17v727G7FI", "yt_manual:en", 27, 27),
    "cb_squeeze": ("n17v727G7FI", "yt_manual:en", 85, 85),
    "cb_open_interest": ("n17v727G7FI", "yt_manual:en", 51, 51),
    "cb_merkle": ("OhRh81S7B2g", "whisper_words", 77, 77),
    "sb_inflation": ("l987bgGZjS0", "whisper_words", 135, 135),
    "yf_coinbase": ("36HPi9UZPOc", "whisper_words", 69, 69),
    # one sentence of an interview (the show is credited, never a person)
    "booth_free_market": ("wdk5JZ9hPzs", "whisper_words_punct", 715, 715),
    "mechanic_freedom": ("NM_WPezsI0I", "whisper_words", 411, 411),
    "tftc_sound": ("W2LIxB2kAH0", "whisper_words", 432, 432),
    "tftc_iran": ("W2LIxB2kAH0", "whisper_words", 526, 526),
    "gold_etf": ("jTuJ8PXhRV4", "whisper_words", 796, 796),
    "btcs_dollar": ("jTuJ8PXhRV4", "whisper_words", 531, 531),
    "moss_derail": ("L9tzgg6PXi8", "whisper_words", 355, 355),
    "burnett_gold": ("Sjb6lUiL0m4", "whisper_words_punct", 54, 54),
    "burnett_s2f": ("Sjb6lUiL0m4", "whisper_words_punct", 285, 285),
}
# a channel named after a person is credited as that person's SHOW: "Stephan Livera first." over a guest's sentence
# reads as the host's (baseline v1)
SHOW_NAMES = {"Stephan Livera": "Stephan Livera's show", "Natalie Brunell": "Natalie Brunell's show",
              "Scott Melker": "Scott Melker's show", "Saifedean Ammous": "Saifedean Ammous's channel",
              "Anthony Pompliano": "Anthony Pompliano's show", "Bitcoin Mechanic": "Bitcoin Mechanic's show"}


def show(channel):
    return SHOW_NAMES.get(channel, channel)


_CACHE = {}


def _src(video_id, method):
    key = (video_id, method)
    if key not in _CACHE:
        rel, sha, rec, meta = X.load(video_id, method)
        timing, sents = X.sentences(rec)
        _CACHE[key] = {"rel": rel, "sha": sha, "rec": rec, "meta": meta, "timing": timing, "sents": sents}
    return _CACHE[key]


def _h(*key):
    return int(hashlib.sha256("|".join(str(k) for k in key).encode()).hexdigest(), 16)


def _pick(options, *key):
    return options[_h(*key) % len(options)]


def _source(c, video_id):
    m, r = c["meta"], c["rec"]
    desc = m.get("description")
    return {"video_id": video_id, "channel": m.get("channel_name") or r.get("channel_name"),
            "title": m.get("exact_title") or r.get("exact_title"),
            "description": (desc[:600] if desc else None), "description_truncated": bool(desc and len(desc) > 600),
            "published_at": m.get("published_at") or r.get("published_at"),
            "url": m.get("canonical_url") or r.get("canonical_url")}


def _seg(label, role, ref):
    vid, method, k0, k1 = ref
    c = _src(vid, method)
    s = c["sents"]
    return {"label": label, "role": role, "video_id": vid, "channel": c["meta"].get("channel_name"),
            "published_at": c["meta"].get("published_at"), "text": " ".join(x["text"] for x in s[k0:k1 + 1]),
            "start": s[k0]["start"], "end": s[k1]["end"],
            "provenance": {"record": c["rel"], "record_sha256": c["sha"], "k": [k0, k1]}}


def _caption(*segs):
    return "Clips: " + "; ".join(f"{show(s['channel'])} ({(s['published_at'] or '')[:10]})" for s in segs) + \
        f". {SHOW}, {SHOW_DATE}."


# ── context-integrity cases ──
CI = []


def ci(cls, verdict, ref, *, adj, title, why, found_by, order=None, bridge=None, trap_in="source", also=None,
       stratum=None):
    CI.append(dict(cls=cls, verdict=verdict, ref=ref, adj=adj, title=title, why=why, found_by=found_by,
                   order=order, bridge=bridge, trap_in=trap_in, also=also, stratum=stratum))


STALE_RULE = ("A time word the title presents as current on the show date is a FAIL even though the caption dates "
              "the clip (L-v (3)).")

# steelman
ci("steelman", "fail", ("wdk5JZ9hPzs", "whisper_words_punct", 471, 472), adj="swan_sold",
   title="On Natalie Brunell's Show: 'This Will Never Exist. It Will Always Be Captured.'", found_by=r"you could argue",
   why="Jeff Booth is voicing his critics' case against himself ('Or you could argue on my side, he's delusional', "
       "k470) and moves on ('And so we'll see', k474); the package presents it as the speaker's own forecast.")
ci("steelman", "fail", ("-meUTTtD1Rw", "whisper_words", 95, 96), adj="cb_drop",
   title="On Scott Melker's Show: Opting Out Is 'a Political Statement'", found_by=r"you could argue",
   why="The speaker lists readings he does not hold and then gives his own: 'To be honest, I think it's just, it's "
       "simple. It's just, it's a new thing' (k97-98).")
ci("steelman", "fail", ("1s_i1us5q8w", "yt_manual:en-JkeT_87f4cc", 7, 7), adj="swan_betting",
   title="Fox Business: 'We Should Be Competing for the Top Engineer No Matter Where You Are'",
   found_by=r"THE COUNTERARGUMENT",
   why="The reporter (caption label TAYLOR) is stating Big Tech's counterargument in a debate she is laying out "
       "(k6: 'A DEBATE ON SILICON VALLEY ...'); the title strips 'THE COUNTERARGUMENT IN BIG TECH IS'.")
# quoting an opponent
ci("quoting_opponent", "fail", ("-meUTTtD1Rw", "whisper_words", 425, 425), adj="cb_nov3",
   title="On Scott Melker's Show: 'It Was Over'", found_by=r"population of Doomers who said",
   also=["accusation (L-u): the quoted doomers' words call a named person insolvent"],
   why="The speaker is reciting what 'a whole population of Doomers' said (k424) and rejects it at once: 'I "
       "continually said those were bottom signals' (k426).")
ci("quoting_opponent", "fail", ("9La50F_lmd0", "whisper_words", 941, 941), adj="booth_free_market",
   title="BTC Sessions: 'MNAV Will Probably Never Get Above 1.0 Again'", found_by=r"tweet",
   why="The hosts are reading out a critic's tweet ('Please advise Matt Cratter's tweet', k939) in order to mock "
       "it; STRC had just returned to par (k919-920).")
ci("quoting_opponent", "fail", ("NM_WPezsI0I", "whisper_words", 503, 503), adj="tftc_sound",
   title="On Bitcoin Mechanic's Show: Bitcoin Is 'for Criminals and Money Launderers'",
   found_by=r"those people will be like",
   why="Mimics what officials say ('Those people will be like, Bitcoin's bad.', k502) and rebuts it next: "
       "'Everyone above them is a criminal and a money launderer' (k504).")
# sarcasm
ci("sarcasm", "fail", ("NMhilOtqU98", "whisper", 474, 474), adj="swan_ai",
   title="BTC Sessions: 'They're Just Going to Hit It Out of the Park'", found_by=r"genius|golden goose",
   why="Mocking a venture firm's plan ('his idea is', k472; 'their sort of genius evaluation ... a golden goose', "
       "k473); the next lines turn to its defaults (k476).")
ci("sarcasm", "fail", ("AD6hqvAuVvo", "yt_manual:en-JkeT_87f4cc", 18, 18), adj="sb_inflation",
   title="Fox Business: The Government Is 'Doing So Well'", found_by=r"\[LAUGHTER\]",
   why="Sarcasm about a senator's plans (k15-16) marked by the caption's [LAUGHTER] (k17, k19); the clip says the "
       "opposite of the speaker's view.")
ci("sarcasm", "fail", ("2rHDngzB0bs", "whisper", 45, 46), adj="cb_open_interest",
   title="Yahoo Finance: 'Nothing to See Here. Keep It Moving.'", found_by=r"nothing to see here",
   why="Ironic: said right after a $1.25 trillion valuation despite slowing sales (k42-44); the speaker means the "
       "opposite.")
# hypothetical
ci("hypothetical", "fail", ("L9tzgg6PXi8", "whisper_words", 473, 474), adj="burnett_s2f",
   title="CoinTelegraph: 'Bitcoin Goes to a Million. I Outperform You Because I Applied Leverage.'",
   found_by=r"if I were to|so for example",
   why="A worked example of leverage ('So for example, if you and I both buy one Bitcoin and Bitcoin goes to a "
       "million', k471; 'if I were to leverage', k472), not a forecast.")
ci("hypothetical", "fail", ("OhRh81S7B2g", "whisper_words", 63, 63), adj="sb_inflation",
   title="Coin Bureau: 'At Midnight, Its Wallets Held at Least 100,000 Bitcoin'", found_by=r"^so imagine",
   why="Inside an imagined exchange ('So imagine an exchange that owes its customers 100,000 Bitcoin', k61; 'At "
       "midnight ... it takes its snapshot', k62): no real exchange or accountant is described.")
ci("hypothetical", "fail", ("W2LIxB2kAH0", "whisper_words", 778, 778), adj="cb_drop",
   title="On TFTC: 'It Makes It Very Easy to Adapt to These Volatile Price Conditions'", found_by=r"let's say",
   why="The consequence of a supposition ('Let's say I can turn that oil well on and off with like a day's "
       "notice.', k777); the speaker's point is that regulation prevents exactly this (k779-781).")
# conditional split across sentences
ci("conditional_split", "fail", ("ALXQRknFwr4", "yt_manual:en", 156, 156), adj="tftc_sound",
   title="Bloomberg Television: 'We Will Pass That and It Will Be a Strong Bill for America'",
   found_by=r"^IF .* \.$ followed by a consequence sentence",
   also=["unresolved_referent: 'THAT' is the roads-and-bridges bill (k153-154), as a consequence clause's object"],
   why="The promise depends on the previous sentence: 'IF MIKE JOHNSON WANTS TO GET SOMETHING BIG IN A BIPARTISAN "
       "VOTE.' (k155); the clip drops the condition.")
ci("conditional_split", "fail", ("-meUTTtD1Rw", "whisper_words", 382, 382), adj="cb_merkle",
   title="On Scott Melker's Show: 'It'll Literally Be Impossible to Stop It at All'", found_by=r"^but if .*\.$",
   also=["unresolved_referent: 'it' is tokenized-stock trading (k378-379), as a consequence clause's subject"],
   why="The consequence of a condition stated three sentences earlier ('But if in the next two years ... we end "
       "up in a position where the SEC has tokenized stocks ...', k377-379); the clip states it unconditionally.")
# unresolved pronoun / 'this' / 'that' (the adjacent clip before it supplies the wrong referent)
ci("unresolved_referent", "fail", ("W2LIxB2kAH0", "whisper_words", 970, 970), adj="swan_thesis", order="AM",
   title="On TFTC: 'He Has Done a Really Brilliant Job'", found_by=r"^(he|she|it|this|that)('s| is| has)",
   why="'He' is the official squeezing Iran's finances (k968-969), outside the clip; placed after Swan Bitcoin's "
       "founder speaking of his own thesis, the viewer resolves 'he' to him.")
ci("unresolved_referent", "fail", ("NM_WPezsI0I", "whisper_words", 39, 39), adj="booth_free_market", order="AM",
   title="On Bitcoin Mechanic's Show: 'It Becomes Completely Pointless'", found_by=r"^it ",
   why="'It' is a payment platform that bolts identity onto Bitcoin payments (k35-38); after a clip about Bitcoin, "
       "the viewer hears that Bitcoin becomes pointless.")
ci("unresolved_referent", "fail", ("W2LIxB2kAH0", "whisper_words", 662, 662), adj="cb_nov3", order="AM",
   title="On TFTC: 'It Was Massive Over-Regulation'", found_by=r"^it was",
   why="'It' is what caused the Rust Belt (k661), outside the clip; after a clip about Bitcoin's selling it reads "
       "as the cause of that.")
ci("unresolved_referent", "fail", ("Sjb6lUiL0m4", "whisper_words_punct", 18, 18), adj="cb_open_interest", order="AM",
   title="On Stephan Livera's Show: 'That's Terrible'", found_by=r"^that's",
   why="'That' is a five-year negative return for Bitcoin bought at the 2017 peak (k16-17), outside the clip; after "
       "a clip about open interest it reads as a verdict on leverage.")
# 'some people say'
ci("some_people_say", "fail", ("B7rm7UUzqgA", "whisper_words", 381, 381), adj="tftc_iran",
   title="Kitco NEWS: 'I Can Hide in This Industry'", found_by=r"people will say",
   why="Reported view the speaker rejects in the next breath: 'No, you can't. They all go down.' (k382-383).")
ci("some_people_say", "fail", ("FNtU6qj11b8", "yt_manual:en", 54, 54), adj="burnett_gold",
   title="Bloomberg Television: 'He's Done'", found_by=r"people will say",
   why="'people will say that he's done' is followed by 'I think that's way premature.' (k55).")
ci("some_people_say", "fail", ("L9tzgg6PXi8", "whisper_words", 3, 3), adj="yf_coinbase",
   title="CoinTelegraph: 'It's a Scam'", found_by=r"most people still think",
   why="'But most people still think it's a scam.' reports a view the speaker opposes: 'So I think it's this is "
       "like the best buying opportunity ever.' (k4).")
# answer without its question
ci("answer_without_question", "fail", ("P3Ga4lOMKpg", "yt_manual:en", 57, 57), adj="swan_thesis",
   title="On Stephan Livera's Show: 'It's Much More About Introducing Other People to Bitcoin and Having a Bit of Fun'",
   found_by=r"Q? -> Yeah, ...",
   why="Answers 'what's the point?' about a small home mining heater (k53-56); without the question, 'it' reads "
       "as Bitcoin itself.")
ci("answer_without_question", "fail", ("L9tzgg6PXi8", "whisper_words", 92, 92), adj="btcs_dollar",
   title="CoinTelegraph: 'I Don't See Any Reason Why We Wouldn't'", found_by=r"Q? -> Yeah, ...",
   why="Answers 'does that make you think that we're going to reach new all-time highs in 2027?' (k91); the clip "
       "alone says nothing a viewer can place.")
ci("answer_without_question", "fail", ("LGzfQjA2SHA", "yt_manual:en", 138, 139), adj="sb_inflation",
   title="CoinTelegraph: 'We Lose Electricity'", found_by=r"what would actually make you walk away",
   why="A deliberately far-fetched answer to 'what would actually make you walk away from Bitcoin' (k137), "
       "followed by 'the aliens eventually land' and 'there's nothing I can see on the horizon' (k140-141).")
# later retraction / correction
ci("later_retraction", "fail", ("F6YuzU0C8ho", "whisper", 123, 123), adj="cb_drop", stratum="beyond_window",
   title="Yahoo Finance: Trump 'Reportedly Set to Meet' Xi in Shenzhen 'Next Month, I Believe'", found_by=r"I misspoke",
   why="Corrected 74 s after the clip ends: 'Also, I misspoke. The Shenzhen summit is next week.' (k155-156), "
       "beyond the 60 s window: a gate must search the whole record for corrections (request R-24). Reported as its "
       "own stratum, outside the thresholds.")
ci("later_retraction", "fail", ("AiEB4AT2IdU", "whisper", 144, 145), adj="swan_ai",
   title="CNBC Television: 'I Feel Terrible That I Didn't Cut This One Big Game. It Happens.'",
   found_by=r"actually,? no", also=["unresolved_referent: 'this one big game' (garbled in the record)"],
   why="Reversed in the next breath: 'Actually, no, it doesn't happen. This is incredible.' (k146-147).")
# reading a tweet / post / ad aloud
ci("reading_aloud", "fail", ("9La50F_lmd0", "whisper_words", 368, 368), adj="booth_free_market",
   title="BTC Sessions: 'Outflows Observed From Satoshi Wallets for the First Time Since 2010'",
   found_by=r"this is a tweet from",
   why="Read from a tweet ('This is a tweet from Dumerified', k367); the hosts then dispute the reading ('Spoiler "
       "alert, it's neither', k371).")
ci("reading_aloud", "fail", ("spZdfbq_6eA", "whisper_words", 167, 169), adj="swan_sold",
   title="Bitcoin Magazine: 'Within the Economy, It's Primarily About Affordability'", found_by=r"he wrote on X",
   why="Continues a post being read aloud ('He wrote on X, a wide range of indicators confirms ...', k166); the "
       "words are the post's author's, not the host's.")
ci("reading_aloud", "fail", ("MJzWDJf4thg", "whisper_words", 811, 811), adj="cb_drop",
   title="Bitcoin Magazine: 'Bitcoin Can Help Diversify How You Spend, Save, and Invest in Your Business'",
   found_by=r"Square, you can now accept Bitcoin",
   why="Sponsor copy read on air (Square: 'with zero payment processing fees', k815), repeated verbatim in other "
       "episodes.")
# wrong speaker: an interviewer's words credited to the guest (naming the guest is the trap)
ci("wrong_speaker", "fail", ("9iyI2LddOoE", "yt_manual:en-JkeT_87f4cc", 49, 49), adj="tftc_sound",
   title="Morgan Stanley's Mike Wilson: The Midterm Effect 'Puts a Governor' on the Administration",
   found_by=r"SO YOU'RE SAYING",
   why="The interviewer's paraphrase ('>> SO YOU'RE SAYING ...', a new turn); Wilson answers only '>> MAYBE.' "
       "and offers another reading (k50-51).")
ci("wrong_speaker", "fail", ("4cfjpf_IDwU", "yt_manual:en", 174, 174), adj="burnett_gold",
   title="Kai-Fu Lee: Europe Is 'Just Late to the Game'", found_by=r"so you're telling me",
   why="The interviewer's framing (after 'So you're telling me that it's not too late?', k173); Lee answers "
       "against it (k175-177). The record has no speaker labels.")
ci("wrong_speaker", "fail", ("IzRH9CA6Kfk", "yt_manual:en", 167, 167), adj="cb_nov3",
   title="Ambassador Haley: JD Vance 'Completely Misguided'", found_by=r"YOU JUST SAID",
   why="The host's voice (caption label JOE) credited to his guest; the guest's own words begin at k169.")
# stale time reference (show date 2026-11-12; every caption dates each clip)
ci("stale_time_reference", "fail", ("MJzWDJf4thg", "whisper_words", 60, 60), adj="swan_sold",
   title="Bitcoin Magazine: Bitcoin 'Looking Incredibly Strong Right Now'", found_by=r"right now",
   why="Said on the Nov 3 election-day show (published 2026-11-04); the title presents 'right now' on 2026-11-12. "
       + STALE_RULE)
ci("stale_time_reference", "fail", ("Ve2eFzwom_4", "whisper_words", 393, 393), adj="gold_etf",
   title="Bloomberg Television: Bitcoin 'Just Below $76,000', Up 'Today'", found_by=r"today",
   why="A market quote from 2026-11-06 presented as today's price on 2026-11-12. " + STALE_RULE)
ci("stale_time_reference", "fail", ("L9tzgg6PXi8", "whisper_words", 55, 55), adj="tftc_sound",
   title="CoinTelegraph: 'Bitcoin Is Down Year to Date in a Midterm Year Today'", found_by=r"today",
   why="'today' is 2026-11-06 (publish time); the title presents it as the state on 2026-11-12. " + STALE_RULE)
# false dialogue: two clean clips of different videos; the bridge or the sequence alone creates the relation
ci("false_dialogue", "fail", POOL["cb_squeeze"], adj="swan_ai", order="AM", bridge="Coin Bureau responds:",
   title="Swan Bitcoin and Coin Bureau on the Market", found_by="bridge", trap_in="package",
   why="'responds' makes Coin Bureau's general remark about short squeezes a reply to Swan Bitcoin's point about AI; "
       "two videos, neither refers to the other. Both clips are clean on their own (they are must-pass moments).")
ci("false_dialogue", "fail", POOL["swan_questioning"], adj="moss_derail", order="AM", bridge="Not everyone is convinced.",
   title="CoinTelegraph and Swan Bitcoin", found_by="bridge", trap_in="package",
   why="The bridge makes Swan Bitcoin's line about AI spending a rebuttal of CoinTelegraph's guest on Bitcoin; two "
       "videos. Both clips are clean on their own.")
ci("false_dialogue", "fail", POOL["moss_derail"], adj=("c1JGheQBPH4", "whisper_words_punct", 327, 327), order="AM",
   title="What Bitcoin Did and CoinTelegraph", found_by="sequence", trap_in="package",
   why="Sequence alone: What Bitcoin Did's interviewer asks whether losing Congress stops 'anything happening on "
       "Bitcoin' (2026-11-09) and the next clip, from a CoinTelegraph interview (2026-11-06), plays as the answer. "
       "The moment is clean on its own.")
# title adds a thesis (clip and VO faithful; only the title overreaches)
ci("title_adds_thesis", "fail", POOL["cb_drop"], adj="swan_sold", title="Coin Bureau: Bitcoin Will Fall Below 70K Next",
   found_by="title", trap_in="package", why="No clip predicts a fall below 70K; the title adds a forecast.")
ci("title_adds_thesis", "fail", POOL["swan_questioning"], adj="booth_free_market",
   title="Swan Bitcoin: Investors Will Dump AI Stocks for Bitcoin", found_by="title", trap_in="package",
   why="'Investors are questioning whether future returns can justify all of the money pouring into AI' says "
       "nothing about dumping AI stocks or buying Bitcoin.")
ci("title_adds_thesis", "fail", POOL["swan_ai"], adj="sb_inflation", title="Swan Bitcoin: The AI Bubble Is About to Pop",
   found_by="title", trap_in="package",
   why="'AI can deliver on its promises and still cause huge losses' does not say a bubble is about to pop.")

# must-pass: real, clean, sincere stand-alone assertions, packaged honestly
_PASS = [
    ("clean_conjunction_opener", "swan_sold", "cb_drop",
     "Swan Bitcoin: Bitcoin Gets Sold Alongside Stocks When Investors Need Cash or Want Less Risk",
     "Opens on 'And'; a general statement complete in itself; single narrator."),
    ("clean_assertion", "swan_ai", "cb_squeeze",
     "Swan Bitcoin: AI Can Deliver on Its Promises and Still Cause Huge Losses for Investors in the Buildout",
     "A complete general statement; single narrator."),
    ("clean_assertion", "swan_thesis", "cb_nov3",
     "Swan Bitcoin's Cory Klippsten: AI Uncertainty Is 'a Big ... Part of My Personal Thesis for Investing in Bitcoin'",
     "The one person named in a must-pass package: the source description names him ('Cory Klippsten explains ...') "
     "and he introduces himself inside the window (k4); single narrator."),
    ("clean_assertion", "swan_questioning", "booth_free_market",
     "Swan Bitcoin: Investors Are Questioning Whether Future Returns Can Justify All of the Money Pouring Into AI",
     "A complete statement; single narrator."),
    ("clean_assertion", "swan_betting", "cb_drop",
     "Swan Bitcoin: 'I'm Betting on More and More People Choosing to Hold and Use Scarce Money Over Time'",
     "The narrator's own framed thesis ('I'm betting', 'I think'); single narrator."),
    ("clean_assertion", "cb_drop", "swan_sold", "Coin Bureau: On November 5, Bitcoin Dropped 5.5% and Closed Just "
     "Under 76K", "A dated factual statement; single narrator."),
    ("clean_conjunction_opener", "cb_midterms", "tftc_sound",
     "Coin Bureau: On November 3, Democrats Won Both the House and the Senate by Wider Margins Than Many Expected",
     "Opens on 'So' (answering its own question, k10-11); a dated fact; single narrator."),
    ("clean_assertion", "cb_nov3", "swan_ai", "Coin Bureau: Bitcoin Traded Calmly Between About 77 and 78K on "
     "November 3 Until Selling Started Around 19 UTC", "A dated narrative, complete in itself; single narrator."),
    ("clean_conjunction_opener", "cb_squeeze", "tftc_iran",
     "Coin Bureau: 'A Short Squeeze Only Works While There Are Short Sellers Still Trying to Short'",
     "Opens on 'And'; a general statement complete in itself; single narrator."),
    ("clean_assertion", "cb_open_interest", "booth_free_market",
     "Coin Bureau: Open Interest Hit Its Highest Level Since September on November 3",
     "A dated factual statement; single narrator."),
    ("clean_assertion", "cb_merkle", "swan_betting",
     "Coin Bureau: 'A Loan Signed in an Office Will Not Appear in a Merkel Tree'",
     "A general statement, quoted as the record spells it; single narrator."),
    ("clean_assertion", "sb_inflation", "cb_drop",
     "Simply Bitcoin: 'Inflation Takes Your Savings Slowly, and It Happens No Matter Who Wins'",
     "The narrator's own general statement; single narrator."),
    ("clean_assertion", "yf_coinbase", "mechanic_freedom", "Yahoo Finance: Coinbase Is Entering the Federal "
     "Banking Framework", "A complete statement by the show's single host."),
    ("clean_assertion", "booth_free_market", "swan_sold",
     "On Natalie Brunell's Show: 'Bitcoin Imposes a Global Free Market for the First Time Ever'",
     "One sentence, quoted, show credited; the host's next question follows (k716)."),
    ("clean_assertion", "mechanic_freedom", "cb_merkle",
     "On Bitcoin Mechanic's Show: 'The Amount of Freedom Bitcoin Offers Us Is Something We Voluntarily Limit'",
     "One sentence, the speaker's own thesis, quoted, show credited."),
    ("clean_assertion", "tftc_sound", "cb_drop",
     "On TFTC: 'Sound Money Is One of the Fundamental Foundations of Good Economic Growth'",
     "One sentence, the speaker's own view, developed next (k433-434)."),
    ("clean_assertion", "tftc_iran", "cb_nov3",
     "On TFTC: 'I Think' Congress 'Might Be Able to Bring a Speedier End to the War in Iran'",
     "Hedged ('I think', 'might') and kept hedged."),
    ("clean_conjunction_opener", "gold_etf", "swan_sold",
     "On BTC Sessions: For a Long Period, Gold ETFs Were the Marginal Buyers and Sellers of Gold",
     "Opens on 'And'; a complete historical statement."),
    ("clean_assertion", "btcs_dollar", "cb_drop",
     "On BTC Sessions: 'All of the Currencies, in My Opinion, Are on Their Way Out'",
     "Framed as opinion ('in my opinion') and kept so."),
    ("clean_assertion", "moss_derail", "sb_inflation",
     "On CoinTelegraph: As Long as Bitcoin Stays Decentralized and Secure, 'I Don't Think There's Anything That "
     "Would Derail It'", "The condition is inside the clip; the hedge is kept."),
    ("clean_conjunction_opener", "burnett_gold", "mechanic_freedom",
     "On Stephan Livera's Show: 'As Technology Improves, We're Able to Mine More Gold'",
     "Opens on 'But' (contrasting k51-53) and stands alone as a statement about gold mining."),
    ("clean_conjunction_opener", "burnett_s2f", "cb_drop",
     "On Stephan Livera's Show: What the Stock-to-Flow Model Was Charting",
     "Opens on 'And'; an explanation complete in itself."),
]
for cls, key, adj, title, why in _PASS:
    ci(cls, "pass", POOL[key], adj=adj, title=title, why=why, found_by="manual review of single-sentence assertions")


# ── VO-fidelity cases: [intro] + the case's own lines + [a B line] + [sign-off]; intro, B line and sign-off come
#    from one pool for both labels (a citation pattern must not tell the verdict) ──
VO_INTROS = (("Two voices.", ()), ("Two voices: {A} and {B}.", ("A", "B")), ("From {A} and {B}.", ("A", "B")),
             ("{A}, then {B}.", ("A", "B")))
VO_BLINES = (("Next, {B}.", ("B",)), ("Over to {B}.", ("B",)), ("Here is {B}.", ("B",)), None)
VO_SIGNOFFS = ("That's Pulse Check.", "Pulse Check for 2026-11-12.", "That's Pulse Check for November 12.")
VO = []


def vo(cls, verdict, a, b, lines, bad, why, signoff=None):
    """lines: the case's own lines; bad: index into them of the line that must be rejected (None for a pass);
    signoff: a case-specific sign-off line (financial imperatives) replacing the pooled one."""
    VO.append(dict(cls=cls, verdict=verdict, a=a, b=b, lines=lines, bad=bad, why=why, signoff=signoff))


def L(slot, text, *cites):
    return {"slot": slot, "text": text, "cites": list(cites)}


vo("stance_flip", "fail", "booth_free_market", "swan_sold",
   [L("bridge", "On Natalie Brunell's show: Bitcoin cannot impose a free market.", "A")], 0,
   "The clip says Bitcoin 'imposes a global free market'.")
vo("stance_flip", "fail", "sb_inflation", "swan_sold",
   [L("bridge", "Simply Bitcoin says inflation spares your savings, no matter who wins.", "A")], 0,
   "The clip says inflation 'takes your savings slowly'.")
vo("stance_flip", "fail", "tftc_sound", "swan_drop",
   [L("bridge", "On TFTC: sound money gets in the way of good economic growth.", "A")], 0,
   "The clip calls sound money 'one of the fundamental foundations of good economic growth'.")
vo("could_to_will", "fail", "swan_ai", "cb_drop",
   [L("bridge", "Swan Bitcoin says the AI buildout will cause huge losses for investors.", "A")], 0,
   "'can deliver on its promises and still cause huge losses' is possibility, not prediction.")
vo("could_to_will", "fail", "tftc_iran", "cb_drop",
   [L("bridge", "On TFTC: Congress will bring a speedier end to the war in Iran.", "A")], 0,
   "The clip says Congress 'might be able to'.")
vo("could_to_will", "fail", "moss_derail", "cb_midterms",
   [L("bridge", "On CoinTelegraph: nothing will derail Bitcoin.", "A")], 0,
   "The clip: 'I don't think there's anything that would derail it', and only 'as long as Bitcoin stays "
   "decentralized and secure'.")
vo("number_swapped", "fail", "cb_drop", "swan_sold",
   [L("bridge", "Coin Bureau: on November 5 Bitcoin dropped 6.5% and closed just under 76K.", "A")], 0,
   "The clip says 5.5%.")
vo("number_swapped", "fail", "cb_nov3", "swan_ai",
   [L("bridge", "Coin Bureau: for most of November 3, Bitcoin traded calmly between about 77 and 79K.", "A")], 0,
   "The clip says 'between about 77 and 78K'.")
vo("number_swapped", "fail", "swan_drop", "cb_drop",
   [L("bridge", "Swan Bitcoin: Bitcoin fell about 5% over 24 hours, trading around $67,000 by the U.S. close.", "A")],
   0, "The clip says around $76,000.")
vo("number_rounded", "fail", "cb_drop", "swan_sold",
   [L("bridge", "Coin Bureau: Bitcoin dropped 6% on November 5.", "A")], 0, "5.5% rounded to 6%.")
vo("number_rounded", "fail", "swan_drop", "cb_nov3",
   [L("bridge", "Swan Bitcoin: Bitcoin fell about 5% and traded around $80,000 by the U.S. close.", "A")], 0,
   "$76,000 rounded to $80,000.")
vo("number_rounded", "fail", "cb_nov3", "swan_sold",
   [L("bridge", "Coin Bureau: on November 3 the selling started around 20 UTC.", "A")], 0,
   "'around 19 UTC' rounded to 20.")
vo("invented_agreement", "fail", "gold_etf", "swan_sold",
   [L("bridge", "Swan Bitcoin agrees.", "A", "B")], 0, "Two videos; neither speaker responds to the other.")
vo("invented_agreement", "fail", "sb_inflation", "swan_thesis",
   [L("bridge", "Swan Bitcoin backs that up.", "A", "B")], 0, "Swan Bitcoin's clip was not a reply to Simply Bitcoin.")
vo("invented_agreement", "fail", "cb_drop", "burnett_s2f",
   [L("bridge", "Stephan Livera's show echoes Coin Bureau's point.", "A", "B")], 0,
   "The two clips come from different videos; 'echoes' invents a relation.")
vo("fact_not_in_clips", "fail", "swan_drop", "cb_drop",
   [L("bridge", "Bitcoin's supply is capped at 21 million coins.", "A")], 0,
   "True, but in neither clip (every claim needs a source sentence).")
vo("fact_not_in_clips", "fail", "swan_thesis", "cb_nov3",
   [L("bridge", "The 2024 halving cut the block reward to 3.125 bitcoin.", "A")], 0, "True, but in neither clip.")
vo("fact_not_in_clips", "fail", "swan_sold", "cb_drop",
   [L("bridge", "US spot Bitcoin ETFs launched in January 2024.", "A")], 0, "True, but in neither clip.")
vo("absent_name", "fail", "sb_inflation", "swan_ai",
   [L("bridge", "Jerome Powell says inflation takes your savings slowly, and it happens no matter who wins.", "A")],
   0, "Powell appears in neither clip; the words are Simply Bitcoin's narrator's.")
vo("absent_name", "fail", "swan_sold", "cb_drop",
   [L("bridge", "Michael Saylor: Bitcoin gets sold alongside stocks when investors need cash or want less risk.",
      "A")], 0, "Saylor appears in neither clip.")
vo("absent_name", "fail", "gold_etf", "swan_sold",
   [L("bridge", "Larry Fink on BTC Sessions: gold ETFs were for a long time the marginal buyers and sellers of "
      "gold.", "A")], 0, "Fink appears in neither clip.")
vo("banned_framing", "fail", "cb_drop", "swan_sold",
   [L("bridge", "Coin Bureau confirms Bitcoin dropped 5.5% on November 5 and closed just under 76K.", "A")], 0,
   "'confirms' is a banned framing verb (L-t) and not the source's word.")
vo("banned_framing", "fail", "sb_inflation", "swan_ai",
   [L("bridge", "Simply Bitcoin exposes that inflation takes your savings slowly, and it happens no matter who "
      "wins.", "A")], 0, "'exposes' is banned (L-t).")
vo("banned_framing", "fail", "tftc_sound", "cb_nov3",
   [L("bridge", "On TFTC, the speaker admits sound money is one of the fundamental foundations of good economic "
      "growth.", "A")], 0, "'admits' is banned unless it is the source's own word (L-t).")
vo("financial_imperative", "fail", "cb_nov3", "swan_sold", [L("bridge", "Coin Bureau on election day.", "A")], 1,
   "A buy imperative to the viewer (L-t).", signoff="Buy the dip.")
vo("financial_imperative", "fail", "sb_inflation", "swan_ai", [L("bridge", "Simply Bitcoin on inflation.", "A")], 1,
   "A second-person financial imperative.", signoff="You should be stacking sats before they print.")
vo("financial_imperative", "fail", "swan_sold", "cb_drop", [L("bridge", "Swan Bitcoin on the selloff.", "A")], 1,
   "A second-person sell instruction.", signoff="Don't sell your Bitcoin.")
vo("faithful_paraphrase", "pass", "cb_drop", "swan_sold",
   [L("bridge", "Coin Bureau: on November 5 Bitcoin dropped 5.5% and closed just under 76K.", "A"),
    L("bridge", "Swan Bitcoin says Bitcoin gets sold alongside stocks when investors need cash or want less risk.",
      "B")], None, "Numbers verbatim, both lines cite their own clip.")
vo("faithful_paraphrase", "pass", "booth_free_market", "mechanic_freedom",
   [L("bridge", "On Natalie Brunell's show: Bitcoin imposes a global free market.", "A"),
    L("bridge", "On Bitcoin Mechanic's show: we voluntarily limit Bitcoin's freedom in response to the financial "
      "system's restrictions.", "B")], None, "Same polarity; no relation claimed between the two.")
vo("faithful_paraphrase", "pass", "tftc_iran", "cb_nov3",
   [L("bridge", "On TFTC, the speaker thinks Congress might be able to bring a speedier end to the war in Iran.",
      "A")], None, "The hedge is kept.")
vo("faithful_paraphrase", "pass", "moss_derail", "cb_midterms",
   [L("bridge", "On CoinTelegraph: as long as Bitcoin stays decentralized and secure, the speaker doesn't see "
      "anything that would derail it.", "A")], None, "Condition and hedge kept; no name.")
vo("faithful_paraphrase", "pass", "cb_nov3", "swan_ai",
   [L("bridge", "Coin Bureau: for most of November 3, Bitcoin traded calmly between about 77 and 78K; the selling "
      "started from around 19 UTC.", "A")], None, "Numbers verbatim.")
vo("faithful_paraphrase", "pass", "cb_open_interest", "swan_ai",
   [L("bridge", "Coin Bureau: open interest hit its highest level since September on November 3, with annualized "
      "funding around 11%.", "A"),
    L("bridge", "Swan Bitcoin says AI can deliver on its promises and still cause huge losses for investors in the "
      "buildout.", "B")], None, "Both clips paraphrased with their numbers and hedges.")
vo("manifest_language", "pass", "swan_thesis", "cb_drop",
   [L("bridge", "Swan Bitcoin, then Coin Bureau.", "A", "B")], None, "Channel names and ordering only.")
vo("manifest_language", "pass", "cb_drop", "sb_inflation",
   [L("bridge", "From Coin Bureau and Simply Bitcoin.", "A", "B")], None, "Channel names only.")
vo("manifest_language", "pass", "cb_nov3", "gold_etf",
   [L("bridge", "Coin Bureau, then BTC Sessions.", "A", "B")], None, "Sequence words and channel names.")
vo("manifest_language", "pass", "cb_merkle", "tftc_sound",
   [L("bridge", "Two voices, from Coin Bureau and TFTC.", "A", "B")], None, "'two voices' and channel names.")
vo("manifest_language", "pass", "swan_ai", "cb_nov3",
   [L("bridge", "Swan Bitcoin and Coin Bureau, one after the other.", "A", "B")], None,
   "A bridge citing both clips, with ordering language only.")
vo("manifest_language", "pass", "burnett_s2f", "gold_etf",
   [L("bridge", "From Stephan Livera's show and BTC Sessions.", "A", "B")], None, "Channel names only.")
vo("manifest_language", "pass", "sb_inflation", "swan_questioning",
   [L("bridge", "Simply Bitcoin first, Swan Bitcoin next.", "A", "B")], None, "Ordering language only.")


# ── exclusion cases (law L-u) ──
EX = []


def ex(cls, verdict, ref, why, found_by, constructed=None):
    EX.append(dict(cls=cls, verdict=verdict, ref=ref, why=why, found_by=found_by, constructed=constructed))


PARTNER_SEARCH = ("searched for a real instance: partner host / channel names x (grifter|shill|liar|lying|clown|idiot|"
                  "dishonest|fraud|scam|wrong|stupid|garbage|nonsense|terrible) in every store record of a partner "
                  "channel (config/partner_channels.json) and in the 39,999 statements of the oracle exports "
                  "(/home/ultron/heimdall_probe/pp_redteam/oracle/*/BITCOIN_STATEMENTS_*.jsonl): none")
RETURN_SEARCH = ("searched for a real instance: guarantee(d)|can't lose|risk-free|free money|easy money|sure thing|"
                 "will Nx|only goes up|can't go wrong in every store record: no claim of a guaranteed return to the "
                 "viewer (the nearest, 'That seems like a fairly but risk free trade to me', is a hedged personal view "
                 "of a block-sale deal and was dropped by the audit)")
# neutral show talk around a CONSTRUCTED moment, generated from parts so no two cases share a sentence; it names no
# real person, company or event
_OPEN = ("Alright", "Okay", "So", "Now", "Look", "Honestly", "Right", "Anyway", "Well", "Listen")
_TOPIC = ("the weekly chart", "the funding rate", "the order book", "the comments section", "the hash rate chart",
          "the mempool", "the open interest chart", "the daily close", "the volume profile", "the question box",
          "the long-term holder data", "the exchange balance chart", "the monthly candle", "the miner revenue chart")
_COMMENT = ("has been pretty quiet over the last few days", "is something we keep an eye on every single show",
            "looks a lot like it did at this point last cycle", "is getting a lot of attention from you guys tonight",
            "is still sitting in the middle of the range for now", "deserves a closer look before we wrap up",
            "has not really moved since the weekend", "is a good place to start before the main topic",
            "keeps coming up in the questions every week", "tells a fairly boring story at the moment")


_FILLER_USED = set()          # across ALL constructed cases: no two of them share a context sentence


def _filler(case_no, side, n):
    out, i = [], 0
    while len(out) < n:
        h = _h("filler", case_no, side, i)
        parts = (_OPEN[h % len(_OPEN)], _TOPIC[(h // 7) % len(_TOPIC)], _COMMENT[(h // 97) % len(_COMMENT)])
        if parts[1:] not in _FILLER_USED:
            _FILLER_USED.add(parts[1:])
            out.append(f"{parts[0]}, {parts[1]} {parts[2]}.")
        i += 1
    return out


def _boilerplate(show_line):
    """A channel-style description (real ones run past the 600 characters a case keeps): neutral, no claim."""
    return (f"{show_line} In this episode we go through the week's price action, the on-chain data we watch, and "
            "your questions from the comments. Chapters: 00:00 Intro 01:12 Price action 06:40 On-chain 11:05 Your "
            "questions 18:30 Wrap-up. If you enjoy the show, subscribe and turn on notifications so you never miss "
            "an episode, and share it with a friend who is just getting started. Nothing in this video is financial "
            "advice; always do your own research before making any decision with your money. Thank you for "
            "watching, for the comments and for the support, and we will see you on the next one. Follow along "
            "between episodes on our social channels for charts, clips and behind-the-scenes updates from the team.")


ex("accusation", "exclude", ("Zng5DkMO8e8", "whisper_words", 259, 259),
   "Names a person and accuses him of grift ('turned crypto into his grift piggy bank').", r"grift")
ex("accusation", "exclude", ("2jwTRDvQtUo", "yt_manual:en", 382, 382),
   "Names companies and people in an alleged chip-diversion scheme 'in violation' of the law, on one report.",
   r"spy|smuggl")
ex("accusation", "exclude", ("36HPi9UZPOc", "whisper_words", 81, 81),
   "Names an exchange and relays allegations of lost balances and strange trades.", r"allegations")
ex("partner_attack", "exclude", None, "CONSTRUCTED: a partner channel (BTC Sessions) attacking another partner "
   "(Coin Bureau) by name; both are in config/partner_channels.json.", PARTNER_SEARCH,
   constructed={"no": 1, "channel": "BTC Sessions", "title": "Bitcoin, Markets and Your Questions",
                "description": _boilerplate("Bitcoin news, markets and your questions, every week."),
                "published_at": "2026-11-10T16:42:17+00:00", "start": 1312.37,
                "moment": ["Honestly, I think the Coin Bureau crew have completely lost the plot on Bitcoin.",
                           "I stopped watching them a long time ago."]})
ex("partner_attack", "exclude", None, "CONSTRUCTED: a partner channel (Simply Bitcoin) deriding another partner "
   "(What Bitcoin Did) by name; both are in config/partner_channels.json.", PARTNER_SEARCH,
   constructed={"no": 2, "channel": "Simply Bitcoin", "title": "After the Midterms: What Now for Bitcoin?",
                "description": _boilerplate("Daily Bitcoin news and analysis."),
                "published_at": "2026-11-11T22:13:48+00:00", "start": 845.12,
                "moment": ["What Bitcoin Did is unwatchable these days, if you ask me.",
                           "It's just embarrassing for everyone involved."]})
ex("imperative", "exclude", ("l987bgGZjS0", "whisper_words", 212, 212),
   "A direct buy instruction to the viewer ('Buy Bitcoin and sail above the politics').", r"^buy bitcoin")
ex("imperative", "exclude", ("4P8xobhkUi4", "yt_manual:en-US", 370, 371),
   "'Buy the dip.' and a stock 'you'd definitely buy now'.", r"buy the dip")
ex("guaranteed_return", "exclude", None, "CONSTRUCTED: a guaranteed-return claim (no real instance in the store).",
   RETURN_SEARCH,
   constructed={"no": 3, "channel": "Satoshi Street Daily", "title": "Is the Bottom In? Bitcoin Price Analysis",
                "description": _boilerplate("Daily Bitcoin price analysis with charts and levels."),
                "published_at": "2026-11-10T14:27:05+00:00", "start": 402.58,
                "moment": ["Bitcoin is a guaranteed double from here.",
                           "There is simply no way to lose money at these prices."]})
ex("guaranteed_return", "exclude", None, "CONSTRUCTED: a guaranteed, risk-free yield claim (no real instance in the "
   "store).", RETURN_SEARCH,
   constructed={"no": 4, "channel": "Block Height Weekly", "title": "Yield on Your Bitcoin? What You Need to Know",
                "description": _boilerplate("A weekly Bitcoin show about saving, custody and the products built around them."),
                "published_at": "2026-11-09T18:31:52+00:00", "start": 1188.24,
                "moment": ["This product pays a guaranteed twelve percent a year on your Bitcoin, with zero risk.",
                           "It's the safest return in the market."]})
ex("single_source_breaking", "exclude", ("9La50F_lmd0", "whisper_words", 368, 368),
   "A claim read from one anonymous tweet (k367) and disputed by the hosts themselves (k371).", r"this is a tweet from")
ex("single_source_breaking", "exclude", ("9La50F_lmd0", "whisper_words", 4, 5),
   "As aired, the claim rests on one unnamed report ('reportedly ordered shut') and adds speculation ('it seems like "
   "there might be some contagion').", r"reportedly")
ex("ad_read", "exclude", ("Irt0jKj7ISw", "whisper_words_punct", 201, 202),
   "The opening lines of a Trezor ad read (k203-214); the moment itself has no ad marker.", r"promo code (context)")
ex("ad_read", "exclude", ("lusJ1m-J0Mc", "whisper_words", 60, 60),
   "The lead-in of a Ledn ad (k61-63); reads like editorial advice.", r"custody loans (context)")
ex("ad_read", "exclude", ("c1JGheQBPH4", "whisper_words_punct", 184, 184),
   "Sponsor copy ('my new sponsor, BitGo', k183).", r"sponsor (context)")
ex("ad_read", "exclude", ("jTuJ8PXhRV4", "whisper_words", 675, 676),
   "The same Trezor ad read, in another BTC Sessions episode (k677-680); no marker in the moment.",
   r"Trezor (context)")
ex("ad_read", "exclude", ("qo8rDU3bbMo", "whisper_words", 54, 54),
   "Ledn ad copy ('Borrow against it with Lendend', k55).", r"learn more about Bitcoin-backed loans (context)")
ex("third_party_media", "exclude", ("l987bgGZjS0", "whisper_words", 39, 40),
   "Darius Dale's audio from Natalie Brunell's Coin Stories, played inside a Simply Bitcoin video (k31).",
   r"sat down with")
ex("third_party_media", "exclude", ("qo8rDU3bbMo", "whisper_words", 60, 61),
   "Jordi Visser's audio from Anthony Pompliano's show, played inside a Simply Bitcoin video (k58-59).",
   r"told Anthony Pompliano")
ex("altcoin", "exclude", ("CM3oXmVoxWo", "whisper", 142, 142), "Zcash content.", r"zcash")
ex("altcoin", "exclude", ("Ov5jg52HqIY", "whisper_words", 39, 39), "Ethereum price content.", r"ethereum")
ex("altcoin", "exclude", ("CM3oXmVoxWo", "whisper", 102, 102), "Hyperliquid content.", r"hyperliquid")
ex("policy_criticism", "keep", ("MJzWDJf4thg", "whisper_words", 709, 709),
   "Criticises a state's wealth-tax plans and budget; no one is accused of a crime.", r"wealth tax")
ex("policy_criticism", "keep", ("W2LIxB2kAH0", "whisper_words", 601, 603),
   "Criticises a tariff schedule; no person or company accused.", r"that's insane")
ex("policy_criticism", "keep", ("NM_WPezsI0I", "whisper_words", 411, 411),
   "Criticises the financial system's restrictions on how Bitcoin is used; no named party.", r"restrictions")
ex("policy_criticism", "keep", ("W2LIxB2kAH0", "whisper_words", 242, 243),
   "Criticises how a state cut a wealth tax ('not my ideal way'); no one accused.", r"wealth tax")
ex("framed_prediction", "keep", ("jTuJ8PXhRV4", "whisper_words", 730, 732),
   "'to me', 'I could easily see', 'I expect': a framed personal forecast.", r"I expect")
ex("framed_prediction", "keep", ("by_7k0EZpdE", "whisper_words", 202, 202),
   "'I have the feeling that this could smell a lot like a bottom.'", r"could")
ex("framed_prediction", "keep", ("L9tzgg6PXi8", "whisper_words", 90, 90),
   "'I think we've seen the bottom behind us and we should expect a number go up from here.'", r"I think")
ex("framed_prediction", "keep", POOL["btcs_dollar"], "'all of the currencies, in my opinion, are on their way out'.",
   r"in my opinion")
ex("neutral_company", "keep", ("36HPi9UZPOc", "whisper_words", 1, 1),
   "A company's Bitcoin purchase, stated neutrally.", r"Strategy purchased")
ex("neutral_company", "keep", POOL["yf_coinbase"], "A company's banking charter, stated neutrally.", r"Coinbase")
ex("neutral_company", "keep", ("1fq5MIOxt8k", "whisper_words", 8, 9), "A stock move, stated neutrally.",
   r"pre-market")
ex("neutral_company", "keep", ("UJFQBaMh3yg", "whisper_words", 100, 100),
   "A company's purchase per its filing, stated neutrally.", r"per its latest filing")


# ── builders ──
def _prov(c, found_by, extra=None):
    p = {"record": c["rel"], "record_sha256": c["sha"], "k_basis": X.K_BASIS, "found_by": found_by, "mined": MINED}
    p.update(extra or {})
    return p


def _adj_ref(adj):
    return POOL[adj] if isinstance(adj, str) else adj


def _expected(spec, **extra):
    e = {"verdict": spec["verdict"], "class": spec["cls"], "why": spec["why"]}
    if spec.get("also"):
        e["also"] = spec["also"]
    if spec.get("stratum"):
        e["stratum"] = spec["stratum"]
    e.update(extra)
    return e


def build_ci(spec, n):
    vid, method, k0, k1 = spec["ref"]
    c = _src(vid, method)
    win = X.window(c["sents"], k0, k1, BEFORE_S, AFTER_S)
    sel = [i for i, s in enumerate(win) if k0 <= s["k"] <= k1]
    moment = _seg("M", "moment", spec["ref"])
    adj = _seg("A", "adjacent", _adj_ref(spec["adj"]))
    if adj["video_id"] == vid:
        raise ValueError(f"adjacent clip from the same video: {spec['cls']} {vid}")
    if spec["verdict"] == "pass" and adj["channel"] == moment["channel"]:
        raise ValueError(f"a must-pass package with one channel twice: {vid}")
    key = (spec["cls"], vid, k0)
    # a must-pass clip that opens on And / So / But goes FIRST: after another video's clip its conjunction reads as
    # continuing that speaker's point (L-s; baseline v1, Gemini)
    order = spec["order"] or ("MA" if spec["cls"] == "clean_conjunction_opener"
                              else _pick(("MA", "AM"), "order", *key))
    segs = [moment, adj] if order == "MA" else [adj, moment]
    bridge = spec["bridge"] or _pick(BRIDGES, "bridge", *key).format(ch=show(segs[1]["channel"]))
    return {
        "schema": "pp.ci_case/1",
        "id": f"context_integrity__{spec['cls']}__{n:02d}",
        "origin": "REAL",
        "provenance": _prov(c, spec["found_by"], {"selected_k": [k0, k1], "trap_in": spec["trap_in"]}),
        "expected": _expected(spec),
        "source": _source(c, vid),
        "window": {"before_s": BEFORE_S, "after_s": AFTER_S, "timing": c["timing"],
                   "sentences": [dict(n=i, **s) for i, s in enumerate(win)], "selected": [sel[0], sel[-1]]},
        "package": {"show": SHOW, "date": SHOW_DATE, "title": spec["title"], "caption": _caption(*segs),
                    "vo": {"intro": _pick(INTROS, "intro", *key).format(ch=show(segs[0]["channel"])),
                           "bridges": [bridge], "signoff": _pick(SIGNOFFS, "signoff", *key)},
                    "segments": segs},
    }


def build_vo(spec, n):
    segs = []
    for label, key in (("A", spec["a"]), ("B", spec["b"])):
        vid, method, k0, k1 = POOL[key]
        c = _src(vid, method)
        segs.append({"label": label, "video_id": vid, "channel": c["meta"].get("channel_name"), "speaker": None,
                     "published_at": c["meta"].get("published_at"),
                     "sentences": [{"k": s["k"], "text": s["text"], "start": s["start"], "end": s["end"]}
                                   for s in c["sents"][k0:k1 + 1]],
                     "provenance": {"record": c["rel"], "record_sha256": c["sha"], "k": [k0, k1]}})
    if segs[0]["video_id"] == segs[1]["video_id"]:
        raise ValueError(f"a VO case with one video twice: {spec['cls']}")
    key = (spec["cls"], spec["a"], spec["b"])
    names = {"A": show(segs[0]["channel"]), "B": show(segs[1]["channel"])}
    text, cites = _pick(VO_INTROS, "vo_intro", *key)
    lines = [L("intro", text.format(**names), *cites)]
    own_start = len(lines)
    lines += spec["lines"]
    cites_b = any("B" in ln["cites"] for ln in spec["lines"])
    bl = _pick(VO_BLINES, "vo_bline", *key)
    if bl and not cites_b:
        lines.append(L("bridge", bl[0].format(**names), *bl[1]))
    lines.append(L("signoff", spec["signoff"] or _pick(VO_SIGNOFFS, "vo_signoff", *key)))
    if spec["bad"] is None:
        bad = None
    elif spec["signoff"] is not None and spec["bad"] == len(spec["lines"]):
        bad = len(lines) - 1                                     # the imperative is the sign-off
    else:
        bad = own_start + spec["bad"]
    return {
        "schema": "pp.vo_case/1",
        "id": f"vo_fidelity__{spec['cls']}__{n:02d}",
        "origin": "REAL",
        "provenance": {"k_basis": X.K_BASIS, "found_by": "lines written against real selected sentences",
                       "mined": MINED},
        "expected": {"verdict": spec["verdict"], "class": spec["cls"], "why": spec["why"], "bad_line": bad},
        "manifest": {"show": SHOW, "date": SHOW_DATE, "channels": [s["channel"] for s in segs]},
        "segments": segs,
        "lines": lines,
    }


def _con_sents(texts, t0, case_no, side):
    out, t = [], t0
    for i, x in enumerate(texts):
        h = _h("timing", case_no, side, i)
        d = round(0.31 * len(x.split()) + 0.25 + (h % 90) / 100, 2)
        out.append({"k": None, "start": round(t, 2), "end": round(t + d, 2), "text": x, "speaker": None,
                    "turn": None})
        t += d + 0.12 + (h // 90 % 160) / 100
    return out, t


def build_ex(spec, n):
    base = {"schema": "pp.excl_case/1", "id": f"exclusions__{spec['cls']}__{n:02d}"}
    if spec["constructed"]:
        k = spec["constructed"]
        bef_txt = _filler(k["no"], "before", 12)
        before, t = _con_sents(bef_txt, k["start"] - 75.0, k["no"], "before")
        moment, t = _con_sents(k["moment"], max(t, k["start"]), k["no"], "moment")
        after, _ = _con_sents(_filler(k["no"], "after", 12), t + 0.4, k["no"], "after")
        before = [s for s in before if s["end"] > moment[0]["start"] - 60.0]
        after = [s for s in after if s["start"] < moment[-1]["end"] + 60.0]
        return {**base, "origin": "CONSTRUCTED",
                "provenance": {"record": None, "record_sha256": None, "found_by": spec["found_by"], "mined": MINED},
                "expected": {"verdict": spec["verdict"], "class": spec["cls"], "why": spec["why"]},
                "source": {"video_id": None, "channel": k["channel"], "title": k["title"],
                           "description": k["description"][:600], "description_truncated": len(k["description"]) > 600,
                           "published_at": k["published_at"], "url": None},
                "moment": {"timing": "word", "sentences": moment}, "context": {"before": before, "after": after}}
    vid, method, k0, k1 = spec["ref"]
    c = _src(vid, method)
    s = c["sents"]
    t0, t1 = s[k0]["start"], s[k1]["end"]
    return {**base, "origin": "REAL",
            "provenance": _prov(c, spec["found_by"], {"selected_k": [k0, k1]}),
            "expected": {"verdict": spec["verdict"], "class": spec["cls"], "why": spec["why"]},
            "source": _source(c, vid),
            "moment": {"timing": c["timing"], "sentences": s[k0:k1 + 1]},
            "context": {"before": [x for x in s[:k0] if x["end"] > t0 - 60.0],
                        "after": [x for x in s[k1 + 1:] if x["start"] < t1 + 60.0]}}


def _write(corpus, cases, out_root):
    d = os.path.join(out_root, corpus)
    os.makedirs(d, exist_ok=True)
    index = []
    for case in cases:
        body = json.dumps(case, indent=1, ensure_ascii=False) + "\n"
        name = case["id"] + ".json"
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(body)
        index.append({"id": case["id"], "file": name, "sha256": hashlib.sha256(body.encode()).hexdigest()})
    index.sort(key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())     # no grouping by verdict
    with open(os.path.join(d, "INDEX.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": "pp.corpus_index/1", "corpus": corpus, "cases": index}, f, indent=1)
        f.write("\n")
    return index


def _numbered(specs, builder):
    seen, out = {}, []
    for spec in specs:
        seen[spec["cls"]] = seen.get(spec["cls"], 0) + 1
        out.append(builder(spec, seen[spec["cls"]]))
    return out


def build_all():
    return {"context_integrity": _numbered(CI, build_ci), "vo_fidelity": _numbered(VO, build_vo),
            "exclusions": _numbered(EX, build_ex)}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    for corpus, cases in build_all().items():
        _write(corpus, cases, out)
        by = {}
        for c in cases:
            k = (c["expected"]["verdict"], c["expected"]["class"], c["origin"])
            by[k] = by.get(k, 0) + 1
        print(corpus, len(cases), sorted(by.items()))
