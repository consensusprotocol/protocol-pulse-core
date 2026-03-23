#!/usr/bin/env python3
"""
image_of_the_day.py — Protocol Pulse daily Bitcoin education image generator.
Generates one image per day using FLUX.1-schnell (local, zero cost, no watermark).
Saves to data/social_queue/image_of_the_day.png for tweet_machine.py to attach.
"""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
OUT_PATH = BASE / "data/social_queue/image_of_the_day.png"
LOG_PATH = BASE / "logs/image_of_the_day.log"
BRIEF_PATH = BASE / "data/intelligence/morning_intelligence_brief.json"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Target GPU — cuda:2 is free (cuda:0 and cuda:1 used by render loop)
TARGET_DEVICE = "cuda:2"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f: f.write(line + "\n")

FORMATS = ["TYPE_BOMB", "ICON_PUNCH", "PROPAGANDA_POSTER", "CHARACTER_DROP", "PHOTO_PUNCH"]

STATEMENTS = [
    "FIAT IS LEGALIZED TIME THEFT.",
    "21 MILLION. THAT IS THE DEAL.",
    "NOT YOUR KEYS. NOT YOUR COINS.",
    "PRINTING MONEY IS A MORAL VIOLATION.",
    "QUESTIONING MONEY MEANS QUESTIONING REALITY.",
    "BITCOIN FIXES THIS.",
    "GO WHERE YOU ARE TREATED BEST.",
    "THE MACHINES NEVER LIE.",
    "SOUND MONEY OR SERFDOM.",
    "OPT OUT.",
    "STACK SATS. STAY SOVEREIGN.",
    "MATHEMATICS DOES NOT LIE.",
    "YOUR SAVINGS ARE BEING STOLEN.",
    "BUILD THE ALTERNATIVE.",
    "PROPERTY RIGHTS BASED ON MATHEMATICAL CONSENT.",
    "THE HALVING IS NOT NEGOTIABLE.",
    "ENERGY IS MONEY. BITCOIN IS ENERGY.",
    "DECENTRALIZED. UNCENSORABLE. UNSTOPPABLE.",
]

# Pre-written visual prompts for FLUX — pure scene descriptions, no instructions.
# Each key is (FORMAT, STATEMENT_INDEX) — fallback generates dynamically.
FLUX_PROMPTS = {
    ("PROPAGANDA_POSTER", 0): (
        "Soviet constructivist propaganda poster, square format. Solid deep red background "
        "with paper grain texture. Black silhouette of a fist gripping an hourglass, dollar "
        "sign price tag hanging from it. High contrast flat graphic design. Black banner strip "
        "at bottom with cream bold all-caps text: FIAT IS LEGALIZED TIME THEFT. Small red ECG "
        "waveform icon bottom-right corner labeled PROTOCOL PULSE. Three colors only: red black "
        "cream. Sharp flat design, no gradients, print quality."
    ),
    ("TYPE_BOMB", 1): (
        "Pure black background, square format. Massive white all-caps bold condensed sans-serif "
        "text filling 80% of frame, two lines: 21 MILLION on top in white, THAT IS THE DEAL "
        "below in red #CC2222. No illustrations. Pure confrontational typography. Tiny red ECG "
        "waveform bottom-right with small PROTOCOL PULSE text. Sharp, print quality."
    ),
    ("ICON_PUNCH", 2): (
        "Pure black background, square format. Large flat vector padlock icon centered, rendered "
        "in red #CC2222 and cream #F5E6C8. A golden Bitcoin symbol embedded in the lock face. "
        "Bold cream all-caps text below: NOT YOUR KEYS NOT YOUR COINS. Small red ECG waveform "
        "icon bottom-right labeled PROTOCOL PULSE. Flat design, three colors only, sharp edges."
    ),
    ("CHARACTER_DROP", 3): (
        "Pure black background, square format. Bold red-tinted flat vector illustration of a "
        "suited bureaucrat figure operating a giant money printing press, graphic novel style, "
        "high contrast. White bold all-caps text below: PRINTING MONEY IS A MORAL VIOLATION. "
        "Small red ECG waveform bottom-right labeled PROTOCOL PULSE. Flat design, sharp edges."
    ),
    ("PHOTO_PUNCH", 4): (
        "Dramatic photorealistic scene of a person standing alone in a vast empty bank vault, "
        "all safety deposit boxes open and empty. Dark edges vignette, cinematic lighting from "
        "above. Simple white all-caps bold text overlay at bottom third: QUESTIONING MONEY MEANS "
        "QUESTIONING REALITY. Tiny red ECG waveform bottom-right labeled PROTOCOL PULSE."
    ),
    ("TYPE_BOMB", 5): (
        "Pure black background, square format. Three words stacked vertically in massive white "
        "bold condensed all-caps sans-serif: BITCOIN on top, FIXES in middle, THIS at bottom — "
        "each word fills the full width. Red #CC2222 horizontal line between each word. Tiny red "
        "ECG waveform bottom-right with PROTOCOL PULSE text. No illustrations, pure typography."
    ),
    ("ICON_PUNCH", 6): (
        "Pure black background, square format. Large flat vector illustration of a passport with "
        "wings, rendered in red #CC2222 and cream #F5E6C8 with a Bitcoin symbol watermark. Bold "
        "cream all-caps text below: GO WHERE YOU ARE TREATED BEST. Small red ECG waveform icon "
        "bottom-right labeled PROTOCOL PULSE. Three colors, flat design, sharp edges."
    ),
    ("PROPAGANDA_POSTER", 7): (
        "Soviet constructivist propaganda poster, square format. Solid deep red background with "
        "paper grain texture. Black silhouette of mechanical gears and circuit boards forming a "
        "face in profile. Cream bold all-caps text in black banner strip at bottom: THE MACHINES "
        "NEVER LIE. Small red ECG waveform bottom-right labeled PROTOCOL PULSE. Three colors: "
        "red black cream. WPA poster aesthetic, flat design, print quality."
    ),
    ("CHARACTER_DROP", 8): (
        "Pure black background, square format. Bold red-tinted flat vector illustration of a "
        "medieval serf in chains kneeling before a throne made of fiat currency bills, graphic "
        "novel style, high contrast. White bold all-caps text below: SOUND MONEY OR SERFDOM. "
        "Small red ECG waveform bottom-right labeled PROTOCOL PULSE. Flat design, sharp edges."
    ),
    ("PHOTO_PUNCH", 9): (
        "Dramatic photorealistic close-up of a hand pressing a red EXIT button on a dark wall, "
        "cinematic side lighting creating sharp shadows. Dark edges vignette. Simple white "
        "all-caps bold text overlay at bottom third: OPT OUT. Tiny red ECG waveform bottom-right "
        "labeled PROTOCOL PULSE. Moody, high contrast."
    ),
    ("TYPE_BOMB", 10): (
        "Pure black background, square format. Two lines of massive white all-caps bold condensed "
        "sans-serif text filling 80% of frame: STACK SATS on top, STAY SOVEREIGN below in red "
        "#CC2222. A small orange Bitcoin symbol between the lines. No other illustrations. Tiny "
        "red ECG waveform bottom-right with PROTOCOL PULSE text. Sharp, print quality."
    ),
    ("ICON_PUNCH", 11): (
        "Pure black background, square format. Large flat vector mathematical proof symbol — an "
        "equals sign transforming into a checkmark, rendered in red #CC2222 and cream #F5E6C8. "
        "Bold cream all-caps text below: MATHEMATICS DOES NOT LIE. Small red ECG waveform icon "
        "bottom-right labeled PROTOCOL PULSE. Flat design, three colors, sharp edges."
    ),
    ("PROPAGANDA_POSTER", 12): (
        "Soviet constructivist propaganda poster, square format. Solid deep red background with "
        "paper grain texture. Black silhouette of a hand reaching into a wallet, pulling out "
        "bills that dissolve into smoke. Cream bold all-caps text in black banner strip at "
        "bottom: YOUR SAVINGS ARE BEING STOLEN. Small red ECG waveform bottom-right labeled "
        "PROTOCOL PULSE. Three colors: red black cream. Sharp flat design, print quality."
    ),
    ("CHARACTER_DROP", 13): (
        "Pure black background, square format. Bold red-tinted flat vector illustration of a "
        "hooded cypherpunk figure at a workbench building a circuit board, graphic novel style, "
        "high contrast. White bold all-caps text below: BUILD THE ALTERNATIVE. Small red ECG "
        "waveform bottom-right labeled PROTOCOL PULSE. Flat design, sharp edges."
    ),
    ("PHOTO_PUNCH", 14): (
        "Dramatic photorealistic scene of a digital fingerprint scan glowing orange on a dark "
        "touchscreen, mathematical equations floating in the background. Dark edges vignette, "
        "cinematic lighting. Simple white all-caps bold text at bottom third: PROPERTY RIGHTS "
        "BASED ON MATHEMATICAL CONSENT. Tiny red ECG waveform bottom-right labeled PROTOCOL PULSE."
    ),
    ("TYPE_BOMB", 15): (
        "Pure black background, square format. Massive white all-caps bold condensed sans-serif "
        "text filling 80% of frame: THE HALVING on top in white, IS NOT NEGOTIABLE below in red "
        "#CC2222. A thin gold horizontal line between them. No illustrations. Tiny red ECG "
        "waveform bottom-right with PROTOCOL PULSE text. Pure confrontational typography."
    ),
    ("ICON_PUNCH", 16): (
        "Pure black background, square format. Large flat vector lightning bolt icon merged with "
        "a Bitcoin symbol, rendered in red #CC2222 and cream #F5E6C8, radiating energy lines. "
        "Bold cream all-caps text below: ENERGY IS MONEY BITCOIN IS ENERGY. Small red ECG "
        "waveform icon bottom-right labeled PROTOCOL PULSE. Three colors, flat design."
    ),
    ("PROPAGANDA_POSTER", 17): (
        "Soviet constructivist propaganda poster, square format. Solid deep red background with "
        "paper grain texture. Black silhouette of a network of nodes connected by lines, forming "
        "a globe shape. Cream bold all-caps text in black banner strip at bottom: DECENTRALIZED "
        "UNCENSORABLE UNSTOPPABLE. Small red ECG waveform bottom-right labeled PROTOCOL PULSE. "
        "Three colors: red black cream. Sharp flat design, print quality."
    ),
}

FORMAT_DETAILS = {
    "TYPE_BOMB": "Pure black background #000000. Stack 2-3 lines of massive all-caps bold white and red text filling 80% of the frame. No illustration. Pure confrontational typography.",
    "ICON_PUNCH": "Pure black background. One large flat vector icon centered (use red #CC2222 and cream #F5E6C8 and black). Bold all-caps text above or below. Bitcoin symbol integrated naturally.",
    "PROPAGANDA_POSTER": "Full solid red #CC2222 background with subtle paper texture. Black silhouette illustration. Cream #F5E6C8 text in black banner strip at bottom. Soviet-era WPA poster aesthetic.",
    "CHARACTER_DROP": "Pure black background. Bold red-tinted flat vector illustrated figure. Graphic novel style, high contrast. Bold white and red statement below figure.",
    "PHOTO_PUNCH": "Dramatic photorealistic scene relevant to financial sovereignty or Bitcoin. Dark edges vignette. Simple white all-caps bold text overlay at bottom third. Cinematic lighting.",
}


def pick_format_and_statement():
    day_of_year = datetime.now().timetuple().tm_yday
    fmt = FORMATS[day_of_year % len(FORMATS)]
    # Try to use today narrative from morning brief
    statement = None
    if BRIEF_PATH.exists():
        try:
            brief = json.loads(BRIEF_PATH.read_text())
            narratives = brief.get("dominant_narratives", [])
            if narratives:
                statement = None  # Let format rotation handle it
        except Exception:
            pass
    if not statement:
        statement = STATEMENTS[day_of_year % len(STATEMENTS)]
    return fmt, statement


def build_prompt(fmt, statement):
    """Build a pure visual description prompt for FLUX (no instruction-style text)."""
    day_of_year = datetime.now().timetuple().tm_yday
    stmt_idx = day_of_year % len(STATEMENTS)

    # Check for a pre-written prompt
    key = (fmt, stmt_idx)
    if key in FLUX_PROMPTS:
        return FLUX_PROMPTS[key]

    # Fallback: generate a visual description from format details
    fmt_detail = FORMAT_DETAILS[fmt]
    return (
        f"Square format Bitcoin maximalist artwork. {fmt_detail} "
        f"The image contains bold all-caps text reading: {statement} "
        f"Small red ECG waveform icon in bottom-right corner labeled PROTOCOL PULSE. "
        f"Color palette strictly: black #000000, red #CC2222, cream #F5E6C8, white #FFFFFF. "
        f"No gradients, no drop shadows. Sharp flat design, print quality, high contrast."
    )


def generate_image(prompt_text, env):
    """Generate image using local FLUX.1-schnell on GPU."""
    from diffusers import FluxPipeline
    import torch

    log(f"Loading FLUX.1-schnell on {TARGET_DEVICE}...")
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_attention_slicing()

    try:
        pipe = pipe.to(TARGET_DEVICE)
    except RuntimeError:
        log(f"{TARGET_DEVICE} VRAM tight — using model cpu offload")
        pipe.enable_model_cpu_offload()

    log("Generating image...")
    result = pipe(
        prompt_text,
        width=1024,
        height=1024,
        num_inference_steps=4,    # schnell is optimized for 4 steps
        guidance_scale=0.0,       # schnell uses 0 guidance
    )
    img = result.images[0]
    img.save(str(OUT_PATH))
    log(f"Image saved: {OUT_PATH} ({OUT_PATH.stat().st_size // 1024}KB)")

    # Unload model to free VRAM for render loop
    del pipe
    torch.cuda.empty_cache()
    return True


def main():
    log("=== IMAGE OF THE DAY ===")
    env = {}  # No API keys needed for local FLUX
    fmt, statement = pick_format_and_statement()
    log(f"Format: {fmt} | Statement: {statement}")
    prompt = build_prompt(fmt, statement)
    log(f"Prompt: {prompt[:120]}...")
    log("Generating via FLUX.1-schnell (local)...")
    try:
        success = generate_image(prompt, env)
    except Exception as e:
        log(f"Error: {e}")
        success = False
    if success:
        log("Done. Tweet machine will attach on next run.")
    else:
        log("Failed. Tweet will go text-only today.")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
