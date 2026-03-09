You are a code repair agent. Apply these exact fixes to the Protocol Pulse codebase at ~/protocol_pulse/. Do not deviate from these instructions.

## FIX 1: Nostr REQ filter missing authors (P0)
**File:** ~/protocol_pulse/js/media_unified.js (or the file containing RelayManager class)

**Task:** Locate the RelayManager.connect method where ws.send() dispatches the REQ subscription. Add authors filter with npub-to-hex conversion.

**Find this pattern:**
javascript
ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));


**Replace with:**
javascript
const hexPubkeys = NOSTR_PUBKEYS.map(npub => bech32ToHex(npub));
filter.authors = hexPubkeys;
ws.send(JSON.stringify(['REQ', 'pp-' + Math.random().toString(36).slice(2, 8), filter]));


**Also ensure bech32ToHex function exists. If not present, add this helper at the top of the file:**
javascript
function bech32ToHex(bech32Str) {
  const ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
  const data = bech32Str.slice(bech32Str.indexOf('1') + 1);
  const values = [];
  for (const c of data) {
    const idx = ALPHABET.indexOf(c);
    if (idx === -1) continue;
    values.push(idx);
  }
  // Remove checksum (last 6 values) and convert 5-bit to 8-bit
  const payload = values.slice(0, -6);
  let bits = '';
  for (const v of payload) bits += v.toString(2).padStart(5, '0');
  let hex = '';
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    hex += parseInt(bits.slice(i, i + 8), 2).toString(16).padStart(2, '0');
  }
  return hex;
}


---

## FIX 2: Signal gauge updating wrong elements (P0)
**File:** ~/protocol_pulse/js/media_unified.js (or the file containing updateSignalStrength function)

**Task:** Locate the updateSignalStrength function and change it to update the correct visible gauge elements.

**Find this pattern:**
javascript
splitFlap($('#telem-signal'), state.signalScore);


**Replace with:**
javascript
splitFlap($('#sig-composite'), state.signalScore);
splitFlap($('#sig-sentiment'), state.sentimentScore || 0);
splitFlap($('#sig-spaces'), state.spacesScore || 0);


---

## FIX 3: Highlights not rendering after fetch (P1)
**File:** ~/protocol_pulse/js/media_unified.js (or the file containing fetchHighlights function)

**Task:** Locate where state.highlights is assigned after fetching data and add a call to renderHighlights().

**Find this pattern:**
javascript
state.highlights = fetchedData;


**Replace with:**
javascript
state.highlights = fetchedData;
renderHighlights();


**If renderHighlights function does not exist, verify it exists elsewhere or add a stub:**
javascript
function renderHighlights() {
  const container = $('#highlights-container');
  if (!container || !state.highlights) return;
  container.innerHTML = state.highlights.map(h => `<div class="highlight-item">${h.content || h.text || ''}</div>`).join('');
}


---

## VERIFICATION
After making all changes, run:
bash
cd ~/protocol_pulse/
git diff


Confirm the changes match the fixes above.

---

## COMMIT
bash
cd ~/protocol_pulse/
git add -A
git commit -m "fix(media_unified): P0 nostr authors filter with npub-to-hex, P0 signal gauge element IDs, P1 highlights render call

- Add bech32ToHex converter and include authors in Nostr REQ filter
- Update signal gauge to write to sig-composite/sig-sentiment/sig-spaces
- Call renderHighlights() after state.highlights assignment

Audited by: multi-LLM pipeline (grok winner, gpt4o cross-check)"


Execute all steps in order. Do not skip any fix. Report completion status.