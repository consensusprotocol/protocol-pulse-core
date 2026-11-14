# Heimdall audit

**Question:** Hostile audit, CYCLE 1, of pp-selectid REQUESTS R7 item 1 applied to pipeline/pinned.py (Protocol Pulse video pipeline). Context: law L-q (moments first, then package) makes a moments-first package the editorial decision; tonight it is rendered through the existing PINNED entry point: the package (written by pp-selectid's package_pin.write_pin) is a PIN.json whose segments carry approved_text (the moments' exact words, located by text in the acquired transcript under the sentence law) plus a top-level 'moments_package' {title, caption, package_sha256, checks {vo_fidelity_ok, context_integrity_ok, ...}, edl_vo {intro, bridges [{text, after_clip}]}}. build_edl takes the VO from the package (intro + one bridge after each clip but the last, the renderer's placement), carries the ONE title and caption (law L-t), the package sha256 and the gate verdicts into the EDL, and refuses (PinError) a bridge the renderer cannot place or a package whose VO-fidelity and context-integrity gates did not BOTH pass; a pin without a package is unchanged (no body VO, Editorial Law 2's default). Downstream every stage is shared and unchanged (validate: edl_rules / editorial gate Law 2 / stand-alone / layout; cut; sentence law; voice; prepare; layout; render 16:9 + 9:16; gates; verify; release authorisation). FIND, with file and line, only what you can verify from the diff ('uncertain' otherwise): (1) any package shape that passes moments_vo but the renderer cannot place or would place differently than intended (indices, after_clip types: bool/float/str, duplicates, order, a bridge after the hook); (2) any way a package whose gates did not both pass, or a package with missing/forged checks, reaches the EDL; (3) missing keys raising something other than PinError (title, caption, package_sha256, edl_vo shape, checks not a dict); (4) whether the EDL's new fields can change what any existing gate accepts for a pin WITHOUT a package (must not); (5) whether the title/caption are actually bound anywhere a downstream stage reads them (law L-t requires them in the release authorisation; say whether this diff does that or leaves it to later); (6) test weaknesses. No praise. 

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0157
## Consensus findings (majority of panel agrees)
- **[high] pipeline/pinned.py:344** after_clip type is not validated; bool and float values pass because True == 1 and 1.0 == 1, so a bridge with after_clip true or 1.0 is accepted and serialized to JSON as true/1.0, which the renderer may not place as intended.
  - evidence: `if not isinstance(b, dict) or not str(b.get("text") or "").strip() or b.get("after_clip") not in idx or                 b["after_clip"] == max(idx):`
  - fix: Require isinstance(b.get("after_clip"), int) and not isinstance(b.get("after_clip"), bool) before the membership check.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:329** Missing title, caption, or package_sha256 raises KeyError instead of PinError, so a malformed package can escape the intended fail-closed path.
  - evidence: `edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],`
  - fix: Read each key with .get and raise PinError when any required key is missing.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:348** If checks is present but not a dict (e.g. None, list, string), .get raises AttributeError instead of PinError.
  - evidence: `if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):`
  - fix: Validate isinstance(mp.get("checks"), dict) and raise PinError otherwise before reading gate verdicts.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:339** If edl_vo is present but not a dict (e.g. list, string), v.get raises AttributeError instead of PinError.
  - evidence: `v = mp.get("edl_vo") or {}`
  - fix: Validate isinstance(v, dict) and raise PinError otherwise.
  - raised by deepseek:F4; agree: deepseek, qwen27b
- **[medium] pipeline/pinned.py:341** If bridges is present but not a list (e.g. int), iterating raises TypeError instead of PinError.
  - evidence: `bridges = v.get("bridges") or []`
  - fix: Validate isinstance(bridges, list) and raise PinError otherwise.
  - raised by deepseek:F5; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:343** The loop only validates each bridge individually; it does not enforce exactly one bridge after each clip but the last. Duplicates, missing bridges, and out-of-order bridges pass, so the renderer may place them differently than intended.
  - evidence: `for b in bridges:
        if not isinstance(b, dict) or not str(b.get("text") or "").strip() or b.get("after_clip") not in idx or                 b["after_clip"] == max(idx):`
  - fix: After the loop, verify the set of after_clip values equals set(range(1, max(idx))), no duplicates exist, and the list order matches clip order.
  - raised by deepseek:F6; agree: deepseek, qwen27b
- **[medium] pipeline/pinned.py:329** The diff adds title and caption to the EDL but does not bind them anywhere a downstream stage reads them; law L-t requires them in the release authorisation, so this diff leaves that binding to later.
  - evidence: `edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],`
  - fix: Add the downstream release-authorisation binding for title and caption, or explicitly document the later stage that will do it.
  - raised by deepseek:F8; agree: deepseek, qwen27b
- **[low] pipeline/test_pinned.py:290** Tests do not cover bool/float after_clip, duplicate bridges, missing bridges, checks not a dict, edl_vo not a dict, or missing title/caption/package_sha256, so the fail-closed behavior is under-tested.
  - evidence: `def test_refused_packages(self):`
  - fix: Add cases for non-int after_clip, duplicate/missing/out-of-order bridges, non-dict checks, non-dict edl_vo, and missing required package keys.
  - raised by deepseek:F9; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:330** Duplicate after_clip values in bridges pass validation; the renderer receives two (or more) bridges for the same clip position with no defined placement order
  - evidence: `for b in bridges:
        if not isinstance(b, dict) or not str(b.get("text") or "").strip() or b.get("after_clip") not in idx or                 b["after_clip"] == max(idx):
            raise PinErro`
  - fix: After the per-bridge loop, collect the set of after_clip values and raise PinError if len(set) != len(bridges), e.g. seen=set(); for b in bridges: ...; if b["after_clip"] in seen: raise PinError(...); seen.add(b["after_clip"])
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:335** If mp["checks"] is not a dict (e.g. a string or list), .get() raises AttributeError instead of PinError, bypassing the fail-closed contract
  - evidence: `if not mp.get("checks", {}).get("vo_fidelity_ok") or not mp.get("checks", {}).get("context_integrity_ok"):
        raise PinError("moments_package: the VO-fidelity and context-integrity gates did not `
  - fix: Guard with isinstance: checks = mp.get("checks"); if not isinstance(checks, dict) or not checks.get("vo_fidelity_ok") or not checks.get("context_integrity_ok"): raise PinError(...)
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:326** Missing top-level keys title, caption, or package_sha256 in the package dict raise KeyError (not PinError) when building the EDL
  - evidence: `edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
                   moments_checks=mp.get("checks"))`
  - fix: Use mp.get("title") etc. and raise PinError if any is None/missing, or wrap in try/except KeyError and re-raise as PinError
  - raised by qwen27b:F3; agree: deepseek, qwen27b
- **[high] pipeline/pinned.py:322** If mp["edl_vo"] is a truthy non-dict (e.g. a string or list), v.get("intro") raises AttributeError instead of PinError
  - evidence: `v = mp.get("edl_vo") or {}
    intro = v.get("intro")`
  - fix: After the assignment, add: if not isinstance(v, dict): raise PinError("moments_package edl_vo must be a dict")
  - raised by qwen27b:F4; agree: deepseek, qwen27b
- **[medium] pipeline/pinned.py:329** after_clip of type bool (True/False) or float (1.0) passes the membership check because Python treats True==1 and 1.0==1; the returned EDL carries a non-int after_clip that the renderer may not handle identically
  - evidence: `b.get("after_clip") not in idx or                 b["after_clip"] == max(idx)`
  - fix: Add an explicit type guard: if not isinstance(b.get("after_clip"), int) or isinstance(b.get("after_clip"), bool): raise PinError(...)
  - raised by qwen27b:F5; agree: deepseek, qwen27b
- **[medium] pipeline/pinned.py:323** If mp["edl_vo"]["bridges"] is a truthy non-iterable (e.g. the integer 5), the for-loop raises TypeError instead of PinError
  - evidence: `bridges = v.get("bridges") or []
    idx = {c["index"] for c in clips}
    for b in bridges:`
  - fix: After the assignment, add: if not isinstance(bridges, list): raise PinError("moments_package edl_vo.bridges must be a list")
  - raised by qwen27b:F6; agree: deepseek, qwen27b
- **[medium] pipeline/pinned.py:326** Title and caption are written into the EDL but no code in this diff binds them into the release authorisation stage; law L-t requires them there, so this diff leaves that obligation unmet
  - evidence: `edl.update(title=mp["title"], caption=mp["caption"], moments_package_sha256=mp["package_sha256"],
                   moments_checks=mp.get("checks"))`
  - fix: Either add the binding in the release-authorisation stage in this diff, or explicitly document (and test) that a subsequent diff will wire edl["title"]/edl["caption"] into the release authorisation record
  - raised by qwen27b:F7; agree: deepseek, qwen27b
- **[low] pipeline/test_pinned.py:290** test_refused_packages does not cover: duplicate after_clip, bool/float after_clip, checks as a non-dict, missing title/caption/package_sha256, edl_vo as a non-dict, or bridges as a non-list; these are the exact shapes that raise non-PinError exceptions (F2–F6)
  - evidence: `for name, m in (("gates not both passed", self.mp(checks={"vo_fidelity_ok": True})),
                        ("bridge after the last clip", self.mp(edl_vo={"intro": None,
                             `
  - fix: Add cases: duplicate after_clip, after_clip=True, after_clip=1.0, checks="passed", missing title key, edl_vo="notadict", bridges=5; assert PinError (not AttributeError/KeyError/TypeError) for each
  - raised by qwen27b:F8; agree: deepseek, qwen27b
- **[low] pipeline/test_pinned.py:283** test_a_pin_without_a_package_is_unchanged only asserts title is absent; it does not verify caption, moments_package_sha256, or moments_checks are also absent, so a regression that leaks a default value would go undetected
  - evidence: `self.assertNotIn("title", edl)`
  - fix: Also assert: self.assertNotIn("caption", edl); self.assertNotIn("moments_package_sha256", edl); self.assertNotIn("moments_checks", edl)
  - raised by qwen27b:F9; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F7 [medium] The code carries package_sha256 and checks into the EDL but never verifies that checks correspond to the package content or that package_sha256 is authentic; a forged package with checks True passes. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [high] A moments_package that is present but not a dict is silently ignored, so a malformed package bypasses the moments-first decision instead of raising PinError.
- deepseek: [high] A missing intro (None) is accepted because the check only rejects non-None empty strings, but the package contract requires an intro.
- deepseek: [high] Gate verdicts are checked by truthiness, so non-boolean truthy values such as the string "false" pass as if the gates succeeded.
- deepseek: [medium] intro and bridge text are not required to be strings; non-string values that stringify non-empty pass and are returned unchanged.
- qwen27b: [low] If clips is empty (idx is an empty set) and bridges is non-empty, the f-string in the PinError message calls max(idx) which raises ValueError before PinError is constructed, leaking a non-PinError exception.
- qwen27b: [low] The intro field is not type-checked; a non-string value (e.g. integer 42, a list, a dict) passes the `str(intro).strip()` check and is returned in the VO dict as-is, which the renderer may not handle as a spoken line.
