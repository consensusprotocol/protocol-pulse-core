# gpt-6.1-sol (446 s) usage={'prompt_tokens': 82239, 'completion_tokens': 20410, 'total_tokens': 102649, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 82236, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 17423, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

## Findings

Static review of the supplied diff only. I did not run the tests or inspect the media fixtures. Claims that fixture tests are “green” are unverified.

### 1. HIGH — Delivery deduplication and locking are still per option, not per run

**Evidence:** `pipeline/telegram.py:165–168` derives both the checkpoint and lock from `option`:

> `rpath = ... f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json"`  
> `lock = open(rpath + ".lock", "w")`

The completed-delivery and unknown-outcome checks inspect only that checkpoint (`pipeline/telegram.py:174–182`).

Consequently, `deliver_run(rd)` followed by `deliver_run(rd, option="B")` uses different records and locks. The same attested finals can be delivered again. Concurrent calls with different options also bypass “one delivery per run.” An unknown outcome in one option does not stop another option sending the same bytes.

**Fix:** Use one run-wide lock and delivery ledger, independent of the label. Record the option in that ledger. Actual transition variants already have separate run directories. Add cross-option complete, concurrent and in-flight tests.

### 2. HIGH — A malformed JSON response is classified as a definite refusal, permitting duplicate delivery

**Evidence:** `pipeline/telegram.py:313–314`:

> `if not data.get("ok"):`  
> `raise SendRejected(...)`

`deliver_run` then clears the durable in-flight marker for `SendRejected` (`pipeline/telegram.py:210–213`):

> `record["in_flight"] = None`

A valid JSON response such as `{}` is not proof that Telegram refused the message. For example, a proxy can return a JSON error after the upstream request reached Telegram. This implementation classifies that unknown outcome as retryable. The next invocation can duplicate the accepted message.

The crash-window fix does not close this path.

**Fix:** Validate the response structure explicitly. Require an exact successful response with a valid message ID, or a well-formed, explicit refusal before clearing in-flight state. Missing/mistyped `ok`, malformed results and ambiguous upstream failures must remain unknown. Test those cases through `_send_bot_api`, not merely by injecting `SendRejected`.

### 3. HIGH — The upload TOCTOU fix does not protect the metadata used to authorise the headline and construct the drop

**Evidence:** Authorisation occurs at `pipeline/telegram.py:162`. Afterwards, planning rereads live files:

- `pipeline/telegram.py:94–98`: EDL and G18 readings for headline validation.
- `pipeline/telegram.py:47–48`: EDL for the caption.
- `pipeline/telegram.py:139`: publishing-kit generation.

Only planned upload files receive the subsequent byte/digest check (`pipeline/telegram.py:201–209`):

> `if item["rel"]:`  
> `data = f.read()`  
> `if hashlib.sha256(data).hexdigest() != ...`

Changing the EDL and G18 report after `authorise()` but before planning can therefore supply an invented headline and matching invented “heard” text. The original, correctly hashed finals can still be uploaded with that unsupported headline and passing caption. Neither metadata file is checked against the attestation when its contents are consumed.

**Fix:** Build the entire plan from an immutable, digest-verified snapshot. Parse EDL and gate-report bytes only after verifying those exact bytes against the attestation; pass the parsed snapshot into caption, headline and kit construction. Do not reopen those paths during planning.

### 4. HIGH — The new repeat-only acoustic adjudication ignores words inserted into source pauses

**Evidence:** `pipeline/sentence_law.py:555–561` compares only frames selected from the source:

> `speech = ds > np.percentile(ds, 50)`  
> `bad = (...) & speech`

Gain estimation uses another source-only mask (`pipeline/sentence_law.py:587–595`).

G18 removes the textual identity failure when this check returns true (`pipeline/word_diff.py:118–121`):

> `if same:`  
> `row["identity_repeats_only"], row["identity"] = row["identity"], []`

Consider an interior source pause after “rose.” Insert another “rose” into that pause without shifting the remaining audio. Original speech remains unchanged; the added word occupies source-quiet frames excluded by both masks. The first/last words remain unchanged, and repeat collapsing removes the textual difference. This acoustic check can then clear the actual extra word.

The supplied failing fixture inserts a repeat that shifts later audio; it does not cover insertion into an existing pause.

**Fix:** Detect final-only speech as well as missing source speech after gain removal. Compare the span bidirectionally, including source-quiet intervals. Until that proof exists, retain the identity failure. Add a fixture that repeats an interior word into a source pause without moving subsequent speech.

### 5. MEDIUM — Chained thousands were fixed in text canonicalisation but not in timestamp-span canonicalisation

**Evidence:** Text folding iterates spaced-thousands joining to a fixpoint (`pipeline/canon.py:61–65`). The parallel span parser still requires the accumulated prefix to contain at most three digits (`pipeline/canon.py:213–216`):

> `re.fullmatch(r"\$?\d{1,3}", w.strip())`

For `["1", "000", "000"]`, the first join produces `"1000"`; that prefix no longer satisfies the condition. The resulting canonical tokens are `"1000", "0"`, whereas `canon_tokens("1 000 000")` produces `"1000000"`.

Thus the named chained-thousands case remains inconsistent at the anchoring sites. The same split text and timestamped words need not compare equal.

**Fix:** Use one preparation/tokenisation pass with source-span tracking, rather than a second fragment-joining implementation. At minimum, make chained joining identical and add span/token equivalence tests for three or more thousands groups.

### 6. HIGH — A spaced minus inside a sentence still disappears

**Evidence:** `pipeline/canon.py:71` recognises a spaced minus only at the beginning or after a restricted punctuation set:

> `_SIGN_SPACED = re.compile(r"(^|[(:,;])\s*-\s+(?=\$?\d)")`

The other minus expression requires the digit immediately after the sign (`pipeline/canon.py:70`). Remaining hyphens are then erased (`pipeline/canon.py:82`):

> `t.replace("-", " ")`

Therefore:

- `"change is - 5%"` canonicalises identically to `"change is 5%"`;
- it does **not** canonicalise identically to `"change is minus five percent"`.

The new minus-versus-plus tests can miss this: retaining `plus` alone makes the pair unequal even when the minus was lost.

**Fix:** Recognise spaced unary signs in numeric expressions throughout a sentence, while separately preserving range handling. Test negative versus unsigned, and negative versus spoken “minus,” through both `canon` and G18.

### 7. HIGH — First-party modules from another checkout are still exempted by path substrings

**Evidence:** `pipeline/run_fresh.py:1090–1092` applies dependency-directory exemptions even when the module name is first-party:

> `name.split(".")[-1] in first_party ...`  
> `not any(x in f for x in ("site-packages", "dist-packages", "/venv/"))`

A first-party `canon`, `gates` or `backtest` loaded from another checkout under a path containing `/venv/` or `site-packages` is neither hashed as local code nor reported as foreign code. The added test covers an ordinary temporary directory, not these exemptions.

**Fix:** Reject a first-party module name outside the checkout before applying third-party dependency exemptions. Add foreign-checkout tests under each currently exempted path component.

### 8. HIGH — The original headline-context finding remains open

**Evidence:** `pipeline/telegram.py:74–83` reduces numerical claims to:

> `(sign, value, unit)`

`pipeline/telegram.py:98–106` then unions the readings into a set and matches only those tuples:

> `said |= set(_numeric_claims(...))`

Readings saying **“Bitcoin fell five percent; gold rose ten percent”** satisfy a headline saying **“Bitcoin rose ten percent.”** The value and unit occur, but not that claim. Subject and direction are discarded. The union also does not establish support separately in both formats.

This implements the units portion of the previous finding, not its context portion.

**Fix:** Require each headline quantity to be supported by an audio-derived claim with the corresponding subject and predicate, separately for both formats. A conservative alternative is to restrict numerical headlines to supported canonical clauses from the readings. Add wrong-asset and wrong-direction tests.

## Verification of the 16 cycle-1 dispositions

“Implemented” below refers to the named case visible in the diff, not a verified test result.

| Original finding | Verification |
|---|---|
| **GPT #1 — absent/malformed evidence** | Implemented for the named cases. `blockers` converts missing/non-mapping evidence and format entries into no evidence, then checks every REQUIRED row (`pipeline/release_auth.py:86–94`). |
| **GPT #2 — checked path reopened for upload** | The upload-byte issue is addressed: delivery hashes the bytes it passes to the sender (`pipeline/telegram.py:201–209`). Metadata consumption remains exposed: **finding 3**. |
| **GPT #3 — kill before checkpoint** | Durable in-flight state precedes the request and success checkpoint (`pipeline/telegram.py:206–229`). The broader no-duplicate guarantee remains incomplete: **findings 1–2**. |
| **GPT #4 — spelled-number end ownership** | Implemented for the named spelled-number case: number spans retain their final source word, and both anchors use that end index (`pipeline/canon.py:168–169`; `pipeline/sentence_law.py:352`; `pipeline/editorial_select.py:189`). Parallel tokenisation remains inconsistent: **finding 5**. |
| **GPT #5 — “one and two”** | The named conjunction case is addressed: consuming `and` requires the preceding scale state (`pipeline/canon.py:108–109`). |
| **GPT #6 — sign layouts** | Not complete. The sign handling still loses a spaced interior minus: **finding 6**. |
| **GPT #7 — headline magnitudes against lock text** | The check now reads G18 readings and retains signs, units and ordinals (`pipeline/telegram.py:80–106`). It is not a closed headline check: **findings 3 and 8**. |
| **GPT #8 — foreign checkout by module name** | Not complete because path exemptions override first-party names: **finding 7**. |
| **Claude #1 — REQUIRED/MONITORING and vertical gates** | The requested deciding rows are in the inventory (`pipeline/release_auth.py:35–44`), and non-PASS monitoring rows are named in the caption (`pipeline/telegram.py:49–58`). Fixture execution and claimed green results cannot be verified from this diff. |
| **Claude #2 — evidence and six-key sample count** | Missing/malformed evidence is addressed as above. `_samples` excludes string labels and boolean flags (`pipeline/run_fresh.py:780–789`). Whether each production gate supplies sufficient actual measurement data is not established by the supplied gate implementations. |
| **Claude #3 — anchor edge equality/span** | The span-end change is visible (`pipeline/sentence_law.py:352–355`). The claimed equality checks inside the window-search loop are outside the supplied hunk, so I cannot verify that part of the disposition. |
| **Claude #4 — killed process/sent bytes** | Same disposition as GPT #2–3: upload bytes are bound; durable in-flight state exists; **findings 1–3** remain. |
| **Claude #5 — conjunctions, chained thousands, ordinals** | Conjunction handling and separation of simple ordinals from cardinals are visible (`pipeline/canon.py:108–109,151–158`). Chained thousands are not fixed consistently: **finding 5**. |
| **Claude #6 — vacuous tests/secret-bearing exception text** | The import/grep assertions were tightened (`pipeline/test_canon.py:235–264`), and preflight reports exception type rather than exception text (`pipeline/preflight.py:147–150`). No execution result is verified. |
| **Claude #7 — headline units/context/ordinals** | Units and ordinals are retained. Context remains unimplemented: **finding 8**. |
| **Claude #8 — named crash paths** | The named guards are present: verdict type checks (`pipeline/release_auth.py:76–85`), rejection of zero-compared alignments (`pipeline/sentence_law.py:515–525`), per-segment exception handling (`pipeline/sentence_law.py:858–870`), and missing-row handling in reporting (`pipeline/run_fresh.py:1227–1229,1294–1296`). This does not establish that arbitrary malformed reports cannot crash. |