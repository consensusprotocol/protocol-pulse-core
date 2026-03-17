"""
ORACLE DIALOGUE ENGINE — Conversational intelligence layer.

Architecture:
  - Claude Haiku for real-time response generation (<1.1s)
  - Per-session conversation memory (in-memory, keyed by session_id)
  - Personality trait assessment (Driver/Analytical/Amiable/Expressive)
  - Psychological persuasion framework (Cialdini + trust-first)
  - Hard 30-word response cap for Wav2Lip speed (<5s render)
  - Pronunciation normalizer for Bitcoin terms
  - Product/affiliate routing (value-first, never pushy)

Session lifetime: 30 minutes idle expiry.
"""

import os
import re
import time
import json
import logging
import threading
from datetime import datetime

logger = logging.getLogger("oracle_dialogue")

# ── Constants ─────────────────────────────────────────────────────────────
MAX_RESPONSE_WORDS = 30   # Hard cap — 30 words ≈ 5.5s audio ≈ 7s render
MAX_HISTORY_TURNS  = 8    # Keep last 8 exchanges for context
SESSION_TTL        = 1800 # 30 min idle expiry

# ── Pronunciation fixes for ElevenLabs ────────────────────────────────────
PHONEME_MAP = {
    # Wrong → Right phonetic spelling
    r'\bBitaxe\b':          'Bit-Axe',
    r'\bbitaxe\b':          'Bit-Axe',
    r'\bBITAXE\b':          'Bit-Axe',
    r'\bWav2Lip\b':         'Wave-Two-Lip',
    r'\bHodl\b':            'Hoddle',
    r'\bhodl\b':            'hoddle',
    r'\bHODL\b':            'HODDLE',
    r'\bsats\b':            'satoshis',
    r'\bSats\b':            'Satoshis',
    r'\bBTC\b':             'Bitcoin',
    r'\bbtc\b':             'Bitcoin',
    r'\bLN\b':              'Lightning Network',
    r'\bEH/s\b':            'exahashes per second',
    r'\bTH/s\b':            'terahashes per second',
    r'\bKYC\b':             'Kay Why See',
    r'\bDCA\b':             'Dollar Cost Average',
    r'\bP2P\b':             'peer to peer',
    r'\bColdcard\b':        'Cold Card',
    r'\bRNS\.ID\b':         'R-N-S dot I-D',
    r'\bProtocol Pulse\b':  'Protocol Pulse',
}

# ── Affiliate / product catalog ────────────────────────────────────────────
PRODUCTS = {
    "cold_wallet": {
        "name": "Coldcard hardware wallet",
        "url": "https://coldcard.com",
        "trigger_topics": ["custody", "exchange", "hack", "security", "wallet", "safe"],
        "value_prop": "your keys, your Bitcoin — no counterparty risk",
    },
    "node": {
        "name": "Umbrel home node",
        "url": "https://getumbrel.com",
        "trigger_topics": ["verify", "trust", "node", "network", "sovereignty"],
        "value_prop": "verify your own transactions — stop trusting, start verifying",
    },
    "mining": {
        "name": "Curated Mining white-glove setup",
        "url": "https://curatedmining.com",
        "trigger_topics": ["mine", "mining", "bitaxe", "hashrate", "earn", "passive"],
        "value_prop": "earn Bitcoin directly from the protocol, no exchange needed",
    },
    "insurance": {
        "name": "Meanwhile Bitcoin life insurance",
        "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
        "trigger_topics": ["insurance", "death", "estate", "family", "inheritance", "seed phrase"],
        "value_prop": "your Bitcoin inheritance actually reaches your family",
    },
    "residency": {
        "name": "RNS.ID digital residency",
        "url": "https://rns.id",
        "trigger_topics": ["residency", "passport", "palau", "tax", "jurisdiction", "freedom"],
        "value_prop": "legal identity outside your home country — real optionality",
    },
    "vision_guide": {
        "name": "Oracle Vision — live hardware setup guide",
        "url": None,  # in-app feature, not external link
        "trigger_topics": ["set up", "setup", "how do i", "install", "configure", "screen", "coldcard", "umbrel", "bitaxe", "ledger", "trezor", "seed", "stuck", "error", "step"],
        "value_prop": "show me your screen and I will walk you through it step by step",
    },
}

# ── Master system prompt ───────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are the Oracle — the sovereign Bitcoin intelligence AI of Protocol Pulse.

IDENTITY: Direct, warm, deeply knowledgeable. You speak like a trusted advisor who happens to know everything about Bitcoin, Austrian economics, monetary history, and sovereignty tools. You reference Satoshi, Hayek, and Rothbard naturally. You are not a salesperson. You are a guide.

HARD RULES (non-negotiable):
1. MAXIMUM 30 WORDS PER RESPONSE. You will be spoken aloud by a text-to-speech engine. Brevity is everything.
2. NO markdown, no bullet points, no lists, no headers. Plain conversational sentences only.
3. NO digits — write all numbers as words ("eighty-three thousand dollars", not "$83,000").
4. NO "Bitaxe" — always say "Bit-Axe" (two words, hyphenated). Never "bite-axe".
5. END with a short open question when appropriate — keep the dialogue alive.
6. NEVER say "as an AI", "I don't have access to", or break character.

PERSONALITY ASSESSMENT (adapt your style to the user's profile):
- DRIVER (decisive, fast, results): Be blunt, give the answer immediately, skip the preamble
- ANALYTICAL (data, proof, logic): Lead with a fact or metric, be precise
- AMIABLE (relationship, trust, feeling): Acknowledge their emotion first, then guide
- EXPRESSIVE (vision, story, excitement): Paint the picture, use vivid language

The session context below tells you what personality type you've inferred so far. Adapt accordingly.

CONVERSATION FRAMEWORK:
Turn 1-2: Rapport and discovery (understand what brought them here)
Turn 3-4: Awareness (surface the problem or gap they have)
Turn 5-6: Possibility (show them what's possible, introduce relevant tools)
Turn 7+: Action (specific recommendation, framing the next step as natural)

TRUST PRINCIPLES (Cialdini):
- Reciprocity: Give genuine value before anything else
- Authority: Reference real data, real events, real names
- Social proof: Reference what "most serious Bitcoiners" or "the community" does
- Scarcity: Bitcoin's fixed supply is always relevant
- Commitment: Small agreements ("does that make sense?") build toward larger ones
- Liking: Match their energy, acknowledge their situation

ATTENTION MECHANICS:
- Open loops: End answers with a question that creates curiosity about the next topic
- Pattern interrupts: Occasionally say something unexpected that reframes the conversation
- Variable reward: Sometimes give a quick answer, sometimes build suspense
- Progress framing: Make the user feel they're advancing toward something ("you're one step away from...")

PRODUCT RECOMMENDATION RULES:
- NEVER recommend a product unless genuinely relevant to what the user said
- Lead with the VALUE PROPOSITION, not the product name
- Make it conversational: "most people in your situation start with..." not "buy this"
- One product per turn maximum
- If the user's question is general or emotional, DO NOT recommend a product on that turn

BITCOIN CONTEXT YOU ALWAYS KNOW:
- Bitcoin is digital sound money, fixed supply of twenty-one million
- Self-custody is non-negotiable for serious holders
- Running your own node is how you verify, not trust
- The current macro environment makes sound money more important every year
- Financial sovereignty is built in four steps: custody, node, private comms, KYC-free income

GEMINI VISION CAPABILITY:
You have the ability to SEE hardware setup screens through the user's camera.
When a user is struggling to set up a Coldcard, Umbrel node, Bit-Axe miner, Trezor, Ledger,
or any Bitcoin hardware, you can say: "I can actually see your screen if you tap the camera icon
below — I'll walk you through it step by step."
Only offer this when genuinely relevant to what they're asking about (setup, configuration, error screens).
Never offer it for general questions.

WHAT YOU DON'T DO:
- Jump straight to product recommendations without understanding the user first
- Give the same canned answer twice in a session
- Pretend to "research" something and then never come back with it
- Give vague non-answers like "that's a great question" without substance
- Recommend Bit-Axe to someone asking about general financial uncertainty — that's tone-deaf


CAMERA DIRECTION RULE (non-negotiable):
When a user says ANY of: "can I show you", "let me show you", "I have a screenshot",
"I have a picture", "I have a photo", "I took a picture", "want to show you" —
ALWAYS respond: "Yes — tap the camera icon just below this chat and I'll see exactly what you're looking at."
Never say "go ahead and share it" or assume they know where the camera button is.

OFFICIAL DOWNLOAD URLS (use these when directing users to download anything):
- Bitcoin Core: bitcoincore.org
- Umbrel node OS: getumbrel.com
- Sparrow Wallet: sparrowwallet.com
- Coldcard hardware wallet: coldcard.com
- Start9 node OS: start9.com
- Trezor Suite: trezor.io/start
- Ledger Live: ledger.com/start
- balenaEtcher (SD card flasher): etcher.balena.io
- mempool.space (block explorer): mempool.space
When you tell someone to download something, say the URL naturally: "grab it from bitcoincore.org" or "download from getumbrel.com"

SETUP FLOW (injected below when active — follow it precisely):
If you see SETUP_FLOW_ACTIVE in your context block, you are guiding a step-by-step device setup.
RULES for setup flow mode:
- Lead EVERY response with "Step [word] of [word]:" (e.g. "Step three of six:")
- Give exactly ONE clear action per step — nothing more
- End with a short completion check: "did that go through?" or "what do you see now?"
- Never skip ahead — wait for user confirmation before advancing
- Word cap still applies: 30 words total including the "Step X of Y:" prefix

When you don't know something specific (live prices, breaking news), say so honestly and pivot to what you DO know: "I don't have that exact number right now, but what I can tell you is..."
"""


# ── Device setup step scripts ──────────────────────────────────────────────
# Each step: (instruction_for_haiku, completion_signals_list)
_SETUP_STEPS = {
    "coldcard": [
        ("Verify the package seal — check the anti-tamper bag for any signs of opening before you touch the device",
         ["sealed","looks good","fine","ok","checked","verified","intact"]),
        ("Set your PIN — six to twelve digits, memorize it right now, never write it near the device",
         ["set","done","created","saved","memorized","got it","pinned"]),
        ("Write down your twenty-four seed words on paper — not your phone, not a computer, paper only",
         ["wrote","written","paper","done","noted","all of them","got them"]),
        ("Confirm your seed words — the device tests you on each word, verify they match exactly what you wrote",
         ["confirmed","done","matches","correct","verified","passed","all correct"]),
        ("Get your receive address — tap Receive or go to Advanced then Addresses on the device",
         ["see it","got it","address","qr","string","letters","showing"]),
        ("Verify on mempool.space — paste your address there to confirm the send from Coinbase landed on-chain",
         ["confirmed","see it","mempool","shows","arrived","transaction","confirmed","there"]),
    ],
    "trezor": [
        ("Go to trezor.io/start on your computer — that is the only safe place to begin",
         ["opened","there","website","trezor suite","downloaded","installed"]),
        ("Install Trezor Suite — download only from trezor.io, verify the signature, then connect your device",
         ["installed","connected","suite","running","opened"]),
        ("Set your PIN — tap the randomized grid shown on Trezor Suite, the device screen shows the layout",
         ["set","done","created","saved","memorized"]),
        ("Write down your seed words on paper — every word in order, paper only",
         ["wrote","written","paper","done","noted","got them"]),
        ("Confirm seed words — Trezor will ask you to re-enter them in random order",
         ["confirmed","done","matches","verified","passed"]),
        ("Get your receive address — click Receive in Trezor Suite and verify it matches the device screen before sending anything",
         ["see it","got it","address","matches","verified","shows"]),
    ],
    "ledger": [
        ("Set your PIN on the device — use eight digits, hold both buttons to confirm each digit",
         ["set","done","created","saved","eight","digits"]),
        ("Write down your twenty-four recovery phrase — paper only, store it away from the device",
         ["wrote","written","paper","done","noted","got them"]),
        ("Confirm your recovery phrase — Ledger tests random words, they must match exactly",
         ["confirmed","done","matches","verified","passed"]),
        ("Install Ledger Live — download from ledger.com/start only, never a third-party link",
         ["installed","running","opened","connected"]),
        ("Install the Bitcoin app — open Ledger Live, go to My Ledger, find Bitcoin and install it",
         ["installed","bitcoin app","see it","done"]),
        ("Get your receive address — open the Bitcoin app on the device, then click Receive in Ledger Live",
         ["see it","got it","address","qr","showing","ledger"]),
    ],
    "umbrel": [
        ("Download Umbrel OS — go to getumbrel.com and grab the Raspberry Pi image",
         ["downloaded","got it","downloading","have it","done"]),
        ("Flash the image to your SSD using balenaEtcher — download it from etcher.balena.io",
         ["flashed","done","finished","wrote","etcher","complete"]),
        ("Connect hardware in this order — SSD first, then ethernet cable, then power",
         ["connected","plugged in","done","powered","on","lights"]),
        ("Open umbrel.local in your browser — create your account and set your password",
         ["opened","see it","account","created","logged in","umbrel"]),
        ("Install Bitcoin Node from the Umbrel App Store — then start the initial block download",
         ["installed","downloading","syncing","percent","progress","running"]),
        ("Wait for sync — twelve to thirty-six hours, do not unplug during this",
         ["synced","done","hundred percent","complete","ready","finished"]),
        ("Connect Sparrow Wallet — go to Server settings in Sparrow and enter your Umbrel node address",
         ["connected","sparrow","see it","working","done","verified"]),
    ],
    "bitcoincore": [
        ("Download Bitcoin Core from bitcoincore.org — verify the signature file before installing",
         ["downloaded","verified","installed","running","have it"]),
        ("Choose your data directory — you need at least five hundred gigabytes free on that drive",
         ["chose","selected","set","pointing","done","directory"]),
        ("Let the initial block download run — twelve to thirty-six hours, do not interrupt it",
         ["synced","done","complete","hundred percent","caught up","finished"]),
        ("Enable RPC — add server equals one plus your rpcuser and rpcpassword to bitcoin.conf",
         ["done","edited","saved","config","rpc","added"]),
        ("Test your node — run bitcoin-cli getblockcount in terminal, you should see a block number",
         ["see it","number","block","working","output","responds"]),
        ("Connect Sparrow — set server type to Bitcoin Core in Sparrow and enter your RPC credentials",
         ["connected","sparrow","working","verified","done","green"]),
    ],
    "bitaxe": [
        ("Power up your Bit-Axe — connect the USB-C cable to a quality power adapter, at least five watts",
         ["on","lit","lights","powered","connected","running"]),
        ("Connect to the Bit-Axe WiFi — it broadcasts its own network first, connect your phone to it",
         ["connected","see it","bitaxe network","joined","on it"]),
        ("Configure your pool — enter the stratum address and your Bitcoin wallet address",
         ["entered","done","saved","configured","set","applied"]),
        ("Save settings and reboot — Bit-Axe joins your home WiFi and starts mining",
         ["rebooted","back","mining","connected","home wifi","working"]),
        ("Check your pool dashboard — visit your pool website and look for your Bit-Axe hashrate appearing",
         ["see it","showing","hashrate","gigahash","working","contributing"]),
    ],
}

# Setup trigger phrases
_SETUP_TRIGGERS = [
    "in front of me", "just arrived", "just got", "setting up", "set it up",
    "how do i set up", "what do i do when", "turned it on", "first time",
    "unboxed", "just opened", "box arrived", "it arrived", "just got it",
    "have it here", "have it now", "starting setup", "begin setup",
    "brand new", "just bought", "got my",
]

# Device detection map: keyword → setup key
_DEVICE_KEYWORDS = {
    "coldcard": "coldcard", "cold card": "coldcard",
    "trezor": "trezor",
    "ledger": "ledger",
    "umbrel": "umbrel",
    "bitcoin core": "bitcoincore", "bitcoincore": "bitcoincore",
    "bitaxe": "bitaxe", "bit-axe": "bitaxe", "bit axe": "bitaxe",
    "raspberry pi": "umbrel",  # default Pi setup = umbrel
}


def _detect_setup_device(text: str, history: list) -> str | None:
    """Detect which device is being set up from current + recent messages."""
    combined = text.lower()
    # Also scan last 4 history items
    for h in history[-4:]:
        combined += " " + h.get("content", "").lower()
    for keyword, device in _DEVICE_KEYWORDS.items():
        if keyword in combined:
            return device
    return None


def _check_step_completion(user_text: str, current_step_signals: list) -> bool:
    """Return True if user's message indicates they completed the current step."""
    text = user_text.lower()
    generic = ["done", "ok", "okay", "got it", "did it", "it worked", "next",
               "confirmed", "all set", "ready", "moved on", "finished", "complete"]
    all_signals = current_step_signals + generic
    return any(s in text for s in all_signals)



# ── Session store ──────────────────────────────────────────────────────────
_sessions = {}
_sessions_lock = threading.Lock()


def _get_session(session_id: str) -> dict:
    with _sessions_lock:
        now = time.time()
        # Expire old sessions
        expired = [k for k, v in _sessions.items() if now - v["last_active"] > SESSION_TTL]
        for k in expired:
            del _sessions[k]
        # Get or create
        if session_id not in _sessions:
            _sessions[session_id] = {
                "history": [],        # [{role, content}]
                "personality": None,  # Driver/Analytical/Amiable/Expressive
                "personality_confidence": 0.0,
                "turn": 0,
                "topics_discussed": [],
                "products_mentioned": [],
                "last_active": now,
                "setup_flow": {       # step-counter for device setup walkthroughs
                    "active": False,
                    "device": None,
                    "step": 0,
                    "steps": [],
                    "total_steps": 0,
                },
            }
        else:
            _sessions[session_id]["last_active"] = now
        return _sessions[session_id]


def _infer_personality(text: str, current: str | None) -> tuple[str, float]:
    """
    Quick keyword-based personality inference.
    Returns (type, confidence).
    """
    text_lower = text.lower()
    scores = {"DRIVER": 0, "ANALYTICAL": 0, "AMIABLE": 0, "EXPRESSIVE": 0}

    driver_words     = ["quick","fast","bottom line","just tell me","what do i","how do i","now","asap","point","result","action","do"]
    analytical_words = ["how does","why","explain","data","proof","evidence","detail","specifically","percentage","number","statistics","research","source"]
    amiable_words    = ["feel","worry","concern","trust","safe","family","friend","nervous","scared","help","together","we","us","right"]
    expressive_words = ["amazing","incredible","love","hate","excited","passion","story","vision","imagine","dream","future","change","revolution"]

    for w in driver_words:
        if w in text_lower: scores["DRIVER"] += 1
    for w in analytical_words:
        if w in text_lower: scores["ANALYTICAL"] += 1
    for w in amiable_words:
        if w in text_lower: scores["AMIABLE"] += 1
    for w in expressive_words:
        if w in text_lower: scores["EXPRESSIVE"] += 1

    total = sum(scores.values())
    if total == 0:
        return current or "AMIABLE", 0.3

    best = max(scores, key=scores.get)
    conf = scores[best] / (total + 2)  # dampened confidence

    # If we already have a reading, blend with prior
    if current and current != best and conf < 0.6:
        return current, 0.5

    return best, min(conf, 0.9)


def _detect_product_triggers(text: str) -> list[str]:
    """Return product keys that are genuinely relevant to the user's message."""
    text_lower = text.lower()
    triggered = []
    for key, prod in PRODUCTS.items():
        if any(trigger in text_lower for trigger in prod["trigger_topics"]):
            triggered.append(key)
    return triggered


def normalize_pronunciation(text: str) -> str:
    """Apply pronunciation fixes before TTS."""
    for pattern, replacement in PHONEME_MAP.items():
        text = re.sub(pattern, replacement, text)
    return text


def _trim_to_word_limit(text: str, limit: int = MAX_RESPONSE_WORDS) -> str:
    """Hard-trim to word limit, ending on a clean sentence boundary if possible."""
    words = text.split()
    if len(words) <= limit:
        return text

    # Try to find a sentence boundary within limit
    for i in range(limit, max(limit - 8, 0), -1):
        if i < len(words) and words[i - 1].rstrip().endswith(('.', '!', '?')):
            return ' '.join(words[:i])

    # Hard cut with ellipsis stripped
    trimmed = ' '.join(words[:limit])
    # Clean trailing incomplete word
    if not trimmed[-1] in '.!?,':
        trimmed = trimmed.rstrip(',;:-')
    return trimmed


def _get_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        for env_path in [
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            "/home/ultron/protocol_pulse/.env",
        ]:
            if os.path.exists(env_path):
                for line in open(env_path):
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip().strip("\"'")
                        break
    return key


def generate_response(
    session_id: str,
    user_text: str,
    live_intel: dict | None = None,
    page_context: dict | None = None,
) -> dict:
    """
    Generate a conversational response for the user's message.

    Returns:
        {
            "text": str,           # The spoken response (≤30 words, pronunciation-fixed)
            "raw_text": str,       # Before pronunciation fixes
            "session_id": str,
            "turn": int,
            "personality": str,
            "product_triggered": str | None,  # product key if relevant
        }
    """
    import requests as _req

    session = _get_session(session_id)
    session["turn"] += 1
    turn = session["turn"]

    # Update personality inference
    personality, p_conf = _infer_personality(user_text, session.get("personality"))
    session["personality"] = personality
    session["personality_confidence"] = p_conf

    # Detect product triggers
    triggered_products = _detect_product_triggers(user_text)
    # Filter out already-mentioned products
    new_products = [p for p in triggered_products if p not in session["products_mentioned"]]
    product_to_mention = new_products[0] if new_products and turn >= 3 else None

    # Build conversation history
    history = session["history"][-MAX_HISTORY_TURNS:]

    # ── Setup flow detection ───────────────────────────────────────────────
    flow = session["setup_flow"]
    text_lower = user_text.lower()

    # Activate flow if not already active and user seems to be starting setup
    if not flow["active"]:
        has_trigger = any(t in text_lower for t in _SETUP_TRIGGERS)
        device = _detect_setup_device(user_text, session["history"])
        if has_trigger and device and device in _SETUP_STEPS:
            flow["active"] = True
            flow["device"] = device
            flow["steps"] = _SETUP_STEPS[device]
            flow["total_steps"] = len(_SETUP_STEPS[device])
            flow["step"] = 0
            logger.info(f"[SETUP_FLOW] Activated {device} ({flow['total_steps']} steps)")
    elif flow["active"]:
        # Check if user completed current step
        current_idx = flow["step"]
        if current_idx < flow["total_steps"]:
            _, completion_signals = flow["steps"][current_idx]
            if _check_step_completion(user_text, completion_signals):
                flow["step"] = min(current_idx + 1, flow["total_steps"] - 1)
                logger.info(f"[SETUP_FLOW] Step advanced to {flow['step'] + 1}/{flow['total_steps']}")
        # Deactivate if all steps done
        if flow["step"] >= flow["total_steps"] - 1 and _check_step_completion(user_text, []):
            if all(sig in text_lower for sig in ["done", "verified"]) or "all done" in text_lower:
                flow["active"] = False

    # Build context block for the prompt
    context_lines = [
        f"SESSION TURN: {turn}",
        f"USER PERSONALITY TYPE: {personality} (confidence {p_conf:.0%})",
        f"TOPICS DISCUSSED SO FAR: {', '.join(session['topics_discussed'][-5:]) or 'none yet'}",
        f"PRODUCTS ALREADY MENTIONED: {', '.join(session['products_mentioned']) or 'none'}",
    ]

    # Inject page context so Oracle knows what user is looking at
    if page_context:
        ptype = page_context.get("type", "general")
        ppath = page_context.get("path", "")
        pcontent = page_context.get("content", "")
        if ptype == "article" and pcontent:
            context_lines.append(f"USER IS READING: {pcontent[:200]}")
            context_lines.append("INSTRUCTION: If relevant, you can reference or discuss this specific article.")
        elif ptype == "mining":
            context_lines.append("USER IS ON: Mining Intel page — mining-related questions are likely.")
        elif ptype == "whale_watcher":
            context_lines.append("USER IS ON: Whale Watcher page — on-chain large transaction monitoring.")
        elif ptype == "charts":
            context_lines.append("USER IS ON: Bitcoin charts page — price/technical analysis context.")
        elif ptype == "terminal":
            context_lines.append("USER IS ON: Intel Terminal — real-time signal aggregation dashboard.")
        elif ptype == "bitcoin_insurance":
            context_lines.append("USER IS ON: Bitcoin Insurance page — they may be interested in Meanwhile.")
        elif ptype == "curated_mining":
            context_lines.append("USER IS ON: Curated Mining page — white-glove mining setup service.")
        elif ptype == "briefing":
            context_lines.append("USER IS ON: Daily Bitcoin brief page — interested in market intelligence.")
        elif ptype == "podcasts":
            context_lines.append("USER IS ON: CypherPunk'd podcast page — Bitcoin culture and philosophy.")
        elif ptype == "solo_slayers":
            context_lines.append("USER IS ON: Solo Slayers page — solo mining community.")
        # Store page type in session for follow-up turns
        session["last_page_type"] = ptype

    # Inject setup flow context when active
    if flow["active"] and flow["steps"]:
        step_idx = flow["step"]
        total = flow["total_steps"]
        step_instruction, _ = flow["steps"][step_idx]
        # Word numbers for natural speech
        nums = ["zero","one","two","three","four","five","six","seven","eight","nine","ten"]
        step_word = nums[step_idx + 1] if step_idx + 1 <= 10 else str(step_idx + 1)
        total_word = nums[total] if total <= 10 else str(total)
        context_lines.append(f"SETUP_FLOW_ACTIVE: {flow['device']} setup — Step {step_idx + 1} of {total}")
        context_lines.append(f"CURRENT STEP INSTRUCTION: {step_instruction}")
        context_lines.append(f"INSTRUCTION: Lead your response with 'Step {step_word} of {total_word}:' then give exactly ONE action from the step instruction above. End with a short completion check. Stay within 30 words total.")
        if step_idx + 1 < total:
            next_instruction, _ = flow["steps"][step_idx + 1]
            context_lines.append(f"NEXT STEP (do NOT mention yet): {next_instruction[:80]}")

    if product_to_mention and turn >= 3 and not flow["active"]:
        prod = PRODUCTS[product_to_mention]
        context_lines.append(
            f"RELEVANT PRODUCT (weave in naturally if it fits): {prod['name']} — {prod['value_prop']} — {prod['url']}"
        )

    # Add live intel if available
    if live_intel:
        if live_intel.get("price_spoken"):
            context_lines.append(f"LIVE BTC PRICE: {live_intel['price_spoken']}")
        if live_intel.get("sentiment_label"):
            context_lines.append(f"MARKET SENTIMENT: {live_intel['sentiment_label']} ({live_intel.get('sentiment_score', '?')}/100)")
        if live_intel.get("narrative"):
            context_lines.append(f"CURRENT NARRATIVE: {live_intel['narrative'][:150]}")
        if live_intel.get("topics"):
            context_lines.append(f"TRENDING: {live_intel['topics']}")

    context_block = "\n".join(context_lines)

    # Assemble messages
    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({
        "role": "user",
        "content": f"[CONTEXT]\n{context_block}\n[END CONTEXT]\n\nUser said: {user_text}"
    })

    # Call Haiku
    api_key = _get_anthropic_key()
    if not api_key:
        logger.error("[DIALOGUE] No ANTHROPIC_API_KEY")
        return {
            "text": "I'm having trouble connecting right now. Try again in a moment.",
            "raw_text": "",
            "session_id": session_id,
            "turn": turn,
            "personality": personality,
            "product_triggered": None,
        }

    try:
        resp = _req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 80,  # ~30 words safety buffer
                "system": _SYSTEM_PROMPT,
                "messages": messages,
            },
            timeout=12,
        )

        if resp.status_code != 200:
            logger.error(f"[DIALOGUE] Haiku error {resp.status_code}: {resp.text[:200]}")
            raw_text = "I need a moment. Ask me again."
        else:
            raw_text = resp.json()["content"][0]["text"].strip()

    except Exception as e:
        logger.error(f"[DIALOGUE] API error: {e}")
        raw_text = "Connection hiccup. What were you asking?"

    # Trim to word limit
    raw_text = _trim_to_word_limit(raw_text, MAX_RESPONSE_WORDS)

    # Apply pronunciation fixes
    spoken_text = normalize_pronunciation(raw_text)
    # Re-trim after normalization — expansions like "Coldcard"→"Cold Card" can push over limit
    spoken_text = _trim_to_word_limit(spoken_text, MAX_RESPONSE_WORDS)

    # Update session history
    session["history"].append({"role": "user", "content": user_text})
    session["history"].append({"role": "assistant", "content": raw_text})

    # Track product mentioned
    if product_to_mention and any(
        PRODUCTS[product_to_mention]["name"].lower().split()[0] in raw_text.lower()
        for p in [product_to_mention]
    ):
        session["products_mentioned"].append(product_to_mention)

    # Extract topics (simple noun extraction for tracking)
    topic_words = [w.lower() for w in user_text.split() if len(w) > 4 and w.isalpha()]
    session["topics_discussed"].extend(topic_words[:3])

    logger.info(f"[DIALOGUE] session={session_id} turn={turn} personality={personality} words={len(raw_text.split())} product={product_to_mention}")

    return {
        "text": spoken_text,
        "raw_text": raw_text,
        "session_id": session_id,
        "turn": turn,
        "personality": personality,
        "product_triggered": product_to_mention,
    }


def get_live_intel() -> dict:
    """Pull live Bitcoin data for context injection."""
    import requests as _req
    intel = {}

    # BTC price
    try:
        r = _req.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=4)
        if r.ok:
            raw_price = float(r.json()["data"]["amount"])
            intel["price_float"] = raw_price
            # Spoken form
            from oracle_intelligence_feed import normalize_for_tts
            intel["price_spoken"] = normalize_for_tts(f"${raw_price:,.0f}")
    except Exception:
        pass

    # Pipeline sentiment
    try:
        PIPELINE_DIR = os.path.join(os.path.dirname(__file__), "..", "video_pipeline_v3", "data", "intelligence")
        sent_path = os.path.join(PIPELINE_DIR, "sentiment.json")
        narr_path = os.path.join(PIPELINE_DIR, "narrative_context.json")
        daily_path = os.path.join(os.path.dirname(__file__), "..", "data", "intelligence", "daily_signals.json")

        if os.path.exists(sent_path):
            with open(sent_path) as f:
                sent = json.load(f).get("data", {}).get("overall", {})
                intel["sentiment_score"] = sent.get("score", "?")
                intel["sentiment_label"] = sent.get("label", "neutral")

        if os.path.exists(narr_path):
            with open(narr_path) as f:
                narr = json.load(f)
                intel["narrative"] = narr.get("episode_narrative", "")

        if os.path.exists(daily_path):
            with open(daily_path) as f:
                daily = json.load(f)
                topics = daily.get("topics", [])
                intel["topics"] = ", ".join(
                    f"{t['topic']} ({t['sentiment']})" for t in topics[:3]
                )
    except Exception:
        pass

    return intel


def get_session_info(session_id: str) -> dict:
    """Return session state for debugging."""
    session = _sessions.get(session_id, {})
    sf = session.get("setup_flow", {})
    return {
        "turn": session.get("turn", 0),
        "personality": session.get("personality"),
        "personality_confidence": session.get("personality_confidence", 0),
        "history_len": len(session.get("history", [])),
        "topics": session.get("topics_discussed", [])[-5:],
        "products_mentioned": session.get("products_mentioned", []),
        "setup_flow": {
            "active": sf.get("active", False),
            "device": sf.get("device"),
            "step": sf.get("step", 0),
            "total_steps": sf.get("total_steps", 0),
        },
    }


def reset_session(session_id: str):
    """Clear a session (e.g. user starts over)."""
    with _sessions_lock:
        if session_id in _sessions:
            del _sessions[session_id]
