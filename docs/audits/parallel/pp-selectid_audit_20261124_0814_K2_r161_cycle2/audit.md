# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 161, CYCLE 2 of the audit of this diff (cycle 1, folder _0742_K_r161: qwen27b PASS and gemma PASS with traced reasoning, gpt-oss no answer; one later fix in this diff: running text is freed only by question 5's listing). The rule (orchestrator 07:36 ET Nov 24, from the owner): sponsor or advertiser material only VISIBLE in a clip is never a refusal and never a counted flag; the pin carries it as information. Still HARD, not in this diff: the clip's own spoken words in an ad, step A's AD_READ. Unchanged: OUR 9:16 crop may not slice burned text (that clip goes 16:9 only).
THIS CYCLE: TRY TO BREAK IT, quoting the code. (a) A NON-sponsor item that sponsor_item(x, rec) marks as sponsor material: a news ticker or crawl, the show's own bug or lower third (e.g. a bug "THE DAILY WOLF" while question 5 lists "Wolf Financial"; _norm's containment with 8+ characters; AD_WORDS on a lower third that is a person's name strap). (b) An input that raises in _norm, sponsor_item, sponsor_graphics, current, flags or formats (None texts, "advertising": null, non-dict items, a record without "burned_in"). (c) A record cached before this change that still decides with its old "formats" or "flags": visual_for's two cache-hit returns call current(); is there any other reader of VISUAL_CACHE or of a moment's "visual" that skips current() (package.soft_graphics, opens_16x9, package_pin.formats_of)? (d) package_pin.SEALED_LATER now lists "visible_sponsor_graphics": can a pin sealed BEFORE this change fail its seal check now? Report only what the code shows; if unsure, say so.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0457
## Consensus findings (majority of panel agrees)
- **[high] pipeline/visual_pin.py:0** sponsor_item treats a running ticker/crawl as sponsor material when its normalized text is a substring of any question-5 ad text. burned_block then returns None for that item, so a non-sponsor running item can stop being an eligibility block. This is broader than the stated rule that running text is freed only by question 5's own listing.
  - evidence: `    n = _norm(t)
    for a in (rec or {}).get("advertising") or []:
        m = _norm((a or {}).get("text"))
        if n and m and (n == m or (min(len(n), len(m)) >= 8 and (n in m or m in n))):
     `
  - fix: For RUNNING kinds, require an exact normalized match to a question-5 listed ad text, or otherwise require the listed ad text to be the same item, not merely a superstring.
  - raised by qwen27b:F1; agree: qwen27b, gemma
- **[high] pipeline/visual_pin.py:0** Any non-running burned-in item whose text matches AD_WORDS is classified as sponsor material. A non-sponsor bug or lower third containing an offer-like word is therefore not flagged, and if it is cut in 9:16 it can force 16:9-only treatment.
  - evidence: `    if x.get("kind") not in RUNNING and (AD_WORDS.search(t) or (x.get("kind") == "bug" and AD_CAPS.search(t))):
        return True`
  - fix: Require positive sponsor/advertiser identification for non-running items, not merely AD_WORDS in the text, or restrict AD_WORDS to contexts that are actually sponsor/advertiser material.
  - raised by qwen27b:F2; agree: qwen27b, gemma
- **[medium] pipeline/visual_pin.py:0** sponsor_graphics adds any on-screen text or lower third containing AD_WORDS to the visible sponsor graphics information line. A person's name strap or other non-sponsor text can therefore be reported as visible sponsor graphics.
  - evidence: `    texts = [x.get("text") for x in rec.get("on_screen_text") or [] if isinstance(x, dict)] + \
        [(rec.get("lower_third") or {}).get("text")]
    out += [t.strip() for t in texts if isinstance(`
  - fix: Only include on-screen text or lower thirds that are identified as sponsor/advertiser material, not all text matching AD_WORDS.
  - raised by qwen27b:F3; agree: qwen27b, gemma
- **[high] pipeline/package.py:0** The package visual row seals the stored flags from each visual record without calling VP.current(v). If a moment's visual list contains a pre-change cached record that was not refreshed through visual_for, its old flags are sealed, which can include sponsor items as flags contrary to RULING 161.
  - evidence: `                            flags=[{"segment": i, **f} for i, v in enumerate(visual) for f in (v or {}).get("flags") or []],`
  - fix: Normalize each visual record with VP.current(v) before reading flags, or ensure every reader of a moment's visual uses the current-rule record.
  - raised by qwen27b:F4; agree: qwen27b, gemma
- **[medium] pipeline/visual_pin.py:0** sponsor_graphics assumes every burned_in entry is a dict. A non-dict entry raises AttributeError before sponsor_item can guard against it. flags and formats make the same assumption.
  - evidence: `    for x in rec.get("burned_in") or []:
        n = _norm(x.get("text"))`
  - fix: Filter or validate burned_in entries as dicts before calling .get, or make all burned_in consumers tolerate non-dict entries.
  - raised by qwen27b:F5; agree: qwen27b, gemma

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- qwen27b: [high] sponsor_item's question-5 containment match is not restricted to RUNNING items. A non-running bug or lower third that does not match AD_WORDS can still be marked sponsor if its normalized text is contained in a listed ad text, causing burned_block to return None and formats to force 16x9-only if cut.
- qwen27b: [medium] sponsor_item does not guard non-dict advertising entries. A non-None non-dict entry in rec['advertising'] makes '(a or {}).get("text")' raise AttributeError, and sponsor_graphics/flags/formats can reach this via sponsor_item.
- qwen27b: [high] _package seals m['visual'] directly without calling visual_pin.current, so a pre-change cached visual record's old flags/formats can be sealed in the pin.
- qwen27b: [low] sponsor_graphics assumes lower_third is dict or None. A string lower_third raises AttributeError at '(rec.get("lower_third") or {}).get("text")'.
- qwen27b: [low] sponsor_item uses AD_WORDS.search(t) where t = x.get('text') or ''. A truthy non-str text value, such as a list or number, raises TypeError, while _norm would have coerced it to str.
- qwen27b: [low] sponsor_graphics suppresses an unlisted burned-in sponsor item if its normalized text is any substring of a listed ad text, with no minimum length. A separate short sponsor item can therefore be omitted from the information line.
- qwen27b: [medium] The visual row's flags list does not filter by measured, so an unmeasured visual record that carries stale flags will contribute flags to the sealed row.
