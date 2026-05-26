# Protocol Pulse Editorial Image Service
# GPT-4o native image generation with red/black brand overlay
import os, re, time, base64, logging, requests
from pathlib import Path
from PIL import Image, ImageDraw
from io import BytesIO

logger = logging.getLogger(__name__)
HEADERS_DIR = Path("static/images/headers")
HEADERS_DIR.mkdir(parents=True, exist_ok=True)

# NO MORE TOPIC_VISUALS — every image is unique, generated from the headline itself

def _match_visual(title):
    """Generate a unique visual concept from the article title.
    NEVER returns a generic Bitcoin coin image. Instead, interprets
    the STORY behind the headline as a cinematic editorial scene."""
    
    import hashlib
    h = hashlib.md5(title.encode()).hexdigest()
    
    # Extract the core story from the title
    title_lower = title.lower()
    
    # Map story themes to SCENES (not objects)
    # The key insight: show the METAPHOR, not the literal subject
    
    scenes = []
    
    # Mining/hashrate stories → industrial, labor, machinery
    if any(w in title_lower for w in ["mining", "hashrate", "hash rate", "miner", "difficulty"]):
        scenes = [
            "abandoned industrial factory floor with single shaft of light through broken ceiling, dust particles floating, photojournalistic",
            "lone figure standing before massive wall of blinking server lights in dark warehouse, silhouette editorial",
            "heavy machinery gears grinding to halt with sparks flying, dramatic macro photography",
            "aerial shot of industrial landscape transitioning from active to dormant, golden hour editorial",
            "close-up of calloused hands adjusting heavy equipment dials, dramatic side lighting, documentary style",
            "vast empty warehouse where machines once hummed, single overhead light swinging, cinematic noir",
            "power plant cooling towers releasing steam against dramatic stormy sky, wide angle editorial",
            "worker walking away from facility at dawn, long shadow stretching behind, editorial portrait",
        ]
    
    # Network/resilience stories → infrastructure, systems, connectivity
    elif any(w in title_lower for w in ["network", "resilience", "node", "protocol"]):
        scenes = [
            "vast underground cable tunnel stretching to vanishing point, emergency lighting casting red glow",
            "massive bridge structure enduring violent storm, long exposure showing motion blur of waves",
            "spider web covered in morning dew catching golden light, extreme macro showing structural perfection",
            "electrical grid substation at blue hour with all connections illuminated, industrial editorial",
            "roots of ancient tree exposed showing massive underground network, cross-section nature photography",
            "air traffic control room with multiple screens glowing in darkness, cinematic documentary",
            "massive dam holding back turbulent water, shot from below looking up, dramatic wide angle",
            "telephone wires converging at horizon against dramatic sunset, minimalist editorial landscape",
        ]
    
    # Price/market stories → tension, pressure, movement
    elif any(w in title_lower for w in ["price", "market", "rally", "crash", "correction", "floor", "bull", "bear"]):
        scenes = [
            "tightrope walker silhouette between two skyscrapers at dusk, dramatic editorial photography",
            "pressure gauge needle in red zone with steam escaping, industrial macro photography",
            "ocean wave frozen at peak moment before breaking, dramatic high-speed photography",
            "chess pieces mid-game with dramatic raking light across the board, editorial still life",
            "fault line in cracked earth with light emerging from below, dramatic landscape editorial",
            "boxing ring ropes with sweat droplets frozen mid-air, dramatic sports editorial",
            "pendulum at apex of swing, motion blur trails, scientific photography style",
            "sand dune ridge line with wind sculpting patterns, aerial desert photography",
        ]
    
    # Regulation/government stories → power, institutions, authority
    elif any(w in title_lower for w in ["regulation", "sec", "fed", "congress", "law", "policy", "ban", "government"]):
        scenes = [
            "grand marble corridor with light streaming through distant doorway, architectural editorial",
            "massive gavel shadow cast across documents on desk, dramatic overhead lighting",
            "iron gates slowly closing with light narrowing between them, cinematic noir",
            "scales of justice with one side tipping, dramatic chiaroscuro studio photography",
            "labyrinthine bureaucratic filing system stretching endlessly, wide angle editorial",
            "single red pen on stack of white papers, minimalist editorial still life",
            "grand staircase in government building with figure ascending, editorial portrait",
            "heavy curtains being drawn back revealing bright window, theatrical editorial",
        ]
    
    # Wall Street/institutional stories → suits, power, finance
    elif any(w in title_lower for w in ["institution", "wall street", "etf", "fund", "invest", "bank"]):
        scenes = [
            "empty trading floor after hours with screens still glowing, editorial architectural",
            "glass and steel corporate canyon looking straight up, dramatic architectural photography",
            "briefcase left on park bench in financial district at dawn, editorial still life",
            "elevator doors closing in marble lobby reflecting golden light, cinematic moment",
            "rooftop view of financial district at twilight with office lights creating grid pattern",
            "vintage stock ticker machine collecting dust next to modern screen, editorial contrast",
            "revolving door of major bank with blurred figures entering and exiting, long exposure",
            "safety deposit box vault corridor with one box pulled open, dramatic editorial",
        ]
    
    # Exodus/movement stories → departure, migration, journey
    elif any(w in title_lower for w in ["exodus", "flee", "leaving", "migration", "shift", "transition"]):
        scenes = [
            "empty chairs around boardroom table with one still warm coffee cup, editorial still life",
            "highway stretching to horizon at dawn with single vehicle, dramatic landscape editorial",
            "birds taking flight from industrial rooftop at golden hour, nature meets urban editorial",
            "last light turned off in office building seen from outside, urban night editorial",
            "footprints in sand being slowly erased by incoming tide, nature metaphor photography",
            "train platform with departed train visible in distance, lonely editorial moment",
            "moving boxes stacked in empty industrial space, documentary photography style",
            "bridge at golden hour with fog obscuring the far end, atmospheric landscape editorial",
        ]
    
    # Default: generate from title directly — NO COINS
    else:
        scenes = [
            "dramatic editorial photograph of an abstract concept: tension between old and new systems, dark moody cinematic",
            "solitary figure at crossroads under dramatic sky, editorial portrait photography",
            "massive clock mechanism exposed showing intricate gears, dramatic macro photography",
            "lighthouse beam cutting through thick fog at night, dramatic landscape editorial",
            "crack in massive concrete wall with light streaming through, architectural metaphor",
            "vintage compass on worn map with dramatic side lighting, editorial still life",
            "glass prism splitting single beam into spectrum, scientific photography noir style",
            "ancient tree standing alone in vast field under storm clouds, dramatic landscape",
        ]
    
    # Pick scene deterministically from title hash
    idx = int(h[:4], 16) % len(scenes)
    return scenes[idx]



def build_editorial_prompt(title):
    """Build a noir cinematic editorial image prompt from the article title."""
    visual = _match_visual(title)

    return f"""Cinematic noir editorial photography. Dramatic lighting, high contrast, moody atmosphere. Scene depicting: {visual}. Professional photojournalism aesthetic. No text, no logos. 16:9.

ABSOLUTE REQUIREMENTS:
- ZERO TEXT IN THE IMAGE. No titles, no headlines, no words, no letters, no numbers, no captions, no watermarks, no logos.
- NO Bitcoin coins, tokens, or cryptocurrency symbols
- NO generic stock photo aesthetic
- NO digital screens showing charts or graphs
- Dark, moody atmosphere with masterful use of shadow and light
- If people appear, they should be anonymous (silhouettes, partial views, hands only)"""

def _apply_brand_overlay(img):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    # Bottom gradient: black fading up
    for y in range(h // 3, h):
        progress = (y - h // 3) / (h - h // 3)
        alpha = int(progress * 160)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    # Top-left: subtle red accent glow
    for y in range(h // 4):
        progress = 1 - (y / (h // 4))
        alpha = int(progress * 50)
        draw.line([(0, y), (w // 3, y)], fill=(180, 20, 20, alpha))
    # Right edge vignette
    for x in range(w * 3 // 4, w):
        progress = (x - w * 3 // 4) / (w - w * 3 // 4)
        alpha = int(progress * 80)
        for y in range(h):
            px = overlay.getpixel((x, y))
            new_alpha = min(255, px[3] + alpha)
            overlay.putpixel((x, y), (0, 0, 0, new_alpha))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return Image.alpha_composite(img, overlay).convert("RGB")

def generate_article_header_image(title, prompt_override=None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("No OpenAI API key for image generation")
        return None
    prompt = prompt_override if prompt_override else build_editorial_prompt(title)
    safe_title = re.sub(r"[^a-zA-Z0-9]", "_", title)[:60]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"header_{safe_title}_{timestamp}.jpg"
    filepath = HEADERS_DIR / filename
    try:
        resp = requests.post("https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1536x1024", "quality": "high"},
            timeout=90)
        img_bytes = None
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data") and data["data"][0].get("b64_json"):
                img_bytes = base64.b64decode(data["data"][0]["b64_json"])
            elif data.get("data") and data["data"][0].get("url"):
                img_bytes = requests.get(data["data"][0]["url"], timeout=30).content
        if not img_bytes:
            logger.info("gpt-image-1 unavailable, trying dall-e-3")
            resp2 = requests.post("https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1792x1024", "quality": "hd"},
                timeout=90)
            if resp2.status_code == 200:
                url = resp2.json()["data"][0]["url"]
                img_bytes = requests.get(url, timeout=30).content
        if not img_bytes:
            logger.error(f"All image gen failed for: {title[:50]}")
            return None
        img = Image.open(BytesIO(img_bytes))
        img = img.resize((1200, 630), Image.LANCZOS)
        img = _apply_brand_overlay(img)
        img.save(str(filepath), "JPEG", quality=92)
        logger.info(f"Generated editorial image: {filename}")
        filepath_check = f"static/images/headers/{filename}"
        if os.path.exists(filepath_check) and os.path.getsize(filepath_check) > 1000:
            return f"/static/images/headers/{filename}"
        else:
            logger.error(f"Image file not found after save: {filepath_check}")
            return "/static/images/default-header.png"
    except Exception as e:
        logger.error(f"Image gen error for \'{title[:40]}\': {e}")
        return None

class ImageGenerationService:
    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        if self.openai_key:
            logging.info("Image service initialized with GPT-4o editorial generation")
        else:
            logging.warning("No OpenAI key - image generation disabled")
    def generate_article_header_image(self, title, prompt_override=None):
        return generate_article_header_image(title, prompt_override=prompt_override)
    def _extract_keywords(self, title):
        return title
    def get_article_image(self, title):
        return generate_article_header_image(title)

# Module-level instance for backward compatibility
image_service = ImageGenerationService()



# ============================================================


def _generate_and_save_image(title, prompt):
    """Shared image generation and save logic."""
    import os, hashlib, logging, re
    from datetime import datetime
    logger = logging.getLogger("services.image_service")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        response = client.images.generate(
            model="dall-e-3",


            prompt=prompt + " unique composition " + __import__("hashlib").sha256((str(title) + str(__import__("time").time())).encode()).hexdigest()[:12] + ", cinematic lighting",
            size="1792x1024",
            quality="hd",
            n=1,
        )
        
        image_url = response.data[0].url
        
        import requests
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        
        safe_title = re.sub(r'[^a-zA-Z0-9_]', '_', title[:60])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"header_{safe_title}_{timestamp}.jpg"
        
        os.makedirs("static/images/headers", exist_ok=True)
        filepath = f"static/images/headers/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(img_resp.content)
        
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            logger.info(f"Generated editorial image: {filename}")
            return f"/static/images/headers/{filename}"
        else:
            logger.error(f"Image file not found after save: {filepath}")
            return "/static/images/default-header.png"
            
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return "/static/images/default-header.png"


# OPINION COLUMN IMAGE STYLE — noir photojournalism
# ============================================================
OPINION_SCENES = [
    "lone figure reading newspaper in dimly lit bar, film noir lighting, smoke curling in shaft of light",
    "typewriter on oak desk with scattered papers, single desk lamp, dramatic chiaroscuro lighting",
    "silhouette of journalist against rain-streaked window at night, city lights blurred below",
    "stack of classified folders on brushed steel desk, shallow focus, moody blue-grey tones",
    "empty press room with single glowing monitor, overhead fluorescent creating harsh shadows",
    "hand holding redacted document, dramatic side lighting, vintage photojournalism aesthetic",
    "whiskey glass beside open notebook with handwritten notes, warm tungsten light spilling across",
    "figure walking through fog under streetlamp, trenchcoat silhouette, 1970s thriller aesthetic",
    "closeup of hands on laptop keyboard in dark room, screen glow illuminating face partially",
    "abandoned newsroom at 3am, scattered coffee cups, one desk lamp still on, cinematic desolation",
    "vintage rotary phone beside ashtray on mahogany desk, Dutch angle, noir detective atmosphere",
    "shadow of window blinds falling across wall of pinned documents and red string connections",
]

def generate_opinion_header_image(title):
    """Generate a noir photojournalism header for opinion columns."""
    import hashlib
    title_hash = int(hashlib.md5(title.encode()).hexdigest(), 16)
    scene = OPINION_SCENES[title_hash % len(OPINION_SCENES)]
    
    perspectives = [
        "low angle looking up", "eye-level intimate", "overhead looking down",
        "Dutch angle 15 degrees", "extreme close-up detail", "wide establishing shot",
    ]
    perspective = perspectives[title_hash % len(perspectives)]
    
    gradings = [
        "desaturated with single warm accent color", "high contrast black and white with deep blacks",
        "cold blue-steel monochrome", "warm sepia undertones with crushed blacks",
        "Fincher-style teal shadows and amber highlights", "Gordon Willis underexposed darkness",
    ]
    grading = gradings[(title_hash >> 4) % len(gradings)]
    
    prompt = f"""Create a cinematic photograph for an investigative journalism column.

SCENE: {scene}

CINEMATOGRAPHY:
- {perspective}
- Color grading: {grading}
- Shallow depth of field, grain visible, shot on 35mm film or Leica M
- Atmosphere: secretive, informed, late-night intelligence

ABSOLUTE REQUIREMENTS:
- NO Bitcoin, cryptocurrency, coins, tokens, or tech symbols
- NO logos, text, watermarks, charts
- NO generic stock photo aesthetic
- Must feel like a film still from All the President's Men or The Insider
- Dark, moody, atmospheric — this is serious journalism
- If people appear: anonymous, partial views, silhouettes only"""

    from services.image_service import _generate_and_save_image
    return _generate_and_save_image(title, prompt)
