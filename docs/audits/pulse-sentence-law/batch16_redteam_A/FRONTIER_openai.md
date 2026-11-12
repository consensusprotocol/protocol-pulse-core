# gpt-6.1-sol (317 s) usage={'prompt_tokens': 73707, 'completion_tokens': 13973, 'total_tokens': 87680, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 73704, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 12325, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

1. **HIGH — Missing execution evidence bypasses the release check.**  
   **Evidence:** `pipeline/release_auth.py:84` makes validation conditional: `"if evidence is not None:"`. Both attestation and authorisation obtain evidence with `.get("evidence")` (`pipeline/release_auth.py:131–132,181–183`).

   An otherwise valid report with the entire `evidence` field absent or null can therefore receive `ALL_PASS` and be authorised. Missing one row’s evidence blocks; missing *all* evidence bypasses validation. A truthy non-mapping format entry also crashes at `"(ev or {}).get(k)"` (`pipeline/release_auth.py:87`).

   **Fix:** Require an evidence mapping unconditionally, validate each format’s mapping before accessing it, and return blockers for malformed types. Add tests deleting/nulling the entire evidence field and supplying malformed format entries.

2. **HIGH — The digest check and upload do not use the same immutable bytes.**  
   **Evidence:** `pipeline/telegram.py:159–162` calls `check_file(...)`, then separately calls `send(...)`. The sender subsequently reopens the pathname: `"with open(path, 'rb') as fh:"` (`pipeline/telegram.py:256–258`). `pipeline/release_auth.py:213` hashes another independently opened file.

   Replacing or modifying the file after that hash—or during upload—can send unattested bytes with the passing caption. The post-send digest recorded at `pipeline/telegram.py:171–172` does not reject anything and cannot retract the upload.

   **Fix:** Upload an immutable payload snapshot whose exact bytes were hashed against the attestation. Pass that same protected snapshot/buffer to the sender; do not reopen the mutable run pathname. An open descriptor alone does not prevent in-place modification.

3. **HIGH — A crash after Telegram accepts a message causes automatic duplication.**  
   **Evidence:** The network call occurs at `pipeline/telegram.py:162`, but the successful message is appended and checkpointed only at `pipeline/telegram.py:177–178`: `"record['messages'].append(m)"`, then `"save()"`. The unknown-outcome handler surrounds only the send call (`pipeline/telegram.py:161–168`).

   A process kill between acceptance and checkpointing leaves the old checkpoint—or no checkpoint for the first message. A post-send hash failure or checkpoint-write failure has the same problem. The next invocation has no indication that this message may already exist and sends it again.

   **Fix:** Persist and durably sync an `in_flight`/unknown checkpoint **before** each network request. Replace it with the message ID after success; clear it only on a definite rejection. On restart, never automatically resend an unresolved in-flight message. Serialize delivery attempts with a per-run lock.

4. **HIGH — Canonical number alignment truncates the selected source span.**  
   **Evidence:** `pipeline/canon.py:121,152` assigns a collapsed number the owner of its first source word: `"t, own = toks[i], pairs[i][1]"`, then `"out.append((_value(num), own))"`. `pipeline/sentence_law.py:352–355` uses those owners directly as both boundaries: `"i0, i1 = toks[s][1], toks[e][1]"`.

   For `bitcoin is now at seventy four thousand`, the canonical `74000` token belongs to **seventy**. An exact anchor consequently ends at *seventy*, not *thousand*. Canonical equality is being mistaken for complete source-word coverage.

   **Fix:** Preserve both the first and last consumed source-word indices for every canonical token. Use the ending index for `i1` and the ending timestamp. Test actual returned word boundaries for spelled numbers, scaled amounts and split numeric tokens—not merely that owners are in range.

5. **HIGH — Number parsing deletes a spoken conjunction, making different words equal.**  
   **Evidence:** `pipeline/canon.py:97–101` consumes `"and"` whenever a number has been seen and another number word follows:  
   `"elif w == 'and' and seen ...:"` → `"pass"` → `"seen, j = True, j + 1"`.  
   However, another unit immediately stops parsing (`pipeline/canon.py:81–82`).

   These rules canonicalise both **“one and two”** and **“one two”** to `1 2`: the conjunction is consumed before the parser discovers that the next unit cannot extend this number. G18’s canonical comparison consequently cannot detect that dropped word.

   **Fix:** Consume conjunctions only within a valid compound-number production. If the following token cannot extend that production, terminate before the conjunction and preserve it as a word. Add inequality tests for this case alongside valid `one hundred and two` equivalence tests.

6. **HIGH — Supported financial sign layouts collapse positive and negative amounts.**  
   **Evidence:** `pipeline/canon.py:66` recognises signs only with `"(?<![\\w.,$%])([-+])(?=\\$?\\d)"`. Remaining hyphens are replaced with spaces (`pipeline/canon.py:71`), while `_TOKEN` does not retain plus or minus characters (`pipeline/canon.py:46`).

   Consequently, `- 5%` and `+ 5%` both become `5 percent`. Likewise, `$-5` and `$+5` both become `5 dollars`, because the preceding dollar sign prevents sign recognition.

   **Fix:** Tokenise signs explicitly, supporting whitespace and currency ordering without confusing numeric ranges with unary signs. Do not silently discard an unrecognised sign on an amount. Add inequality fixtures for these layouts, including Unicode minus.

7. **HIGH — Headline checking discards the signs and units it must distinguish.**  
   **Evidence:** `pipeline/telegram.py:80–84` builds a set from selection-lock tokens, then checks only headline tokens matching `"\\d+(\\.\\d+)?"`.

   Even when canonicalisation correctly preserves adjacent signs, a headline saying **`+5%`** is accepted against a lock saying **`-5%`**: the tested token is just `5`. A headline dollar amount can similarly match a percentage. Furthermore, the evidence consulted here is the EDL’s intended lock text, not the final-audio transcription.

   **Fix:** Compare structured numeric claims preserving sign and unit against the attested final-audio readings. Do not reduce claims to an unordered set of bare magnitudes. Test opposite signs and incompatible units with the same magnitude.

8. **HIGH — Foreign-checkout detection silently ignores arbitrary checkout paths.**  
   **Evidence:** `pipeline/run_fresh.py:1128–1131` records modules inside `REPO`, but flags an outside module only under:  
   `"elif re.search(r'/(protocol_pulse|worktrees)/', f):"`.

   A loaded first-party module at `/tmp/alternate/pipeline/canon.py`, for example, is neither recorded nor flagged by this branch. Its directory spelling exempts it from the claimed foreign-checkout check.

   **Fix:** Identify first-party modules by expected module identity and validate their resolved origins against the authorised checkout root. Reject outside origins regardless of directory name. Add a test loading a first-party module from a foreign checkout whose path contains neither recognised directory name.