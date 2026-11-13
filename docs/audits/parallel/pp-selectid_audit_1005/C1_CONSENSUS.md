# pp-selectid audit 1005 (ruling 52's hook rating in the coherence verdict too): cycle 1 consensus

- grok: no P0 / P1, "SHIP: yes"; qwen: no P0 / P1, "SHIP: yes"; glm: "SHIP: yes", with one P1 to confirm.
- glm's P1, confirmed from the code: no consumer compares the coherence verdict's keys exactly.
  - Every reader in package.py takes specific keys: coh.get("clips"), coh.get("vo_point"), coh.get("through_line"),
    coh.get("measured"), coh.get("backend"), coh["vo_point"], coh["clips"].
  - inventory()'s "coherence" row records status, backend, replayed and measured only (row(...)).
  - package_pin's sealed "checks" is a fixed summary dict, not the verdict.
  - So the new key hook_rule reaches neither the seal nor any strict check, as with the clips-alone verdict (audit
    0815 A3).
- glm's recommended identity check of the derivation: the line in coherence() is the same expression as medley()'s:
  `clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}`.
- No change. Verification: test_medley 92 OK; every other suite OK.
