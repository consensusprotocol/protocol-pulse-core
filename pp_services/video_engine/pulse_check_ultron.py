"""
Pulse Check Pipeline v2 - Ultron GPU Edition

Content Strategy:
  - Full Episode (YouTube/Rumble): 5 clips × 90-120s + ElevenLabs transitions = 10-15 min
  - X Teaser (Twitter): Best ~20s from each clip stitched = ~1:45 trailer
  - Shorts (TikTok/IG/YT Shorts): Each clip as standalone 1-2 min vertical

Daily output: 1 full episode + 1 X teaser + 5 vertical shorts = 7 pieces of content
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from pp_services.video_engine.ultron_client import UltronClient

logger = logging.getLogger(__name__)

# ── Partner Channels ──────────────────────────────────────────────
PARTNER_CHANNELS = [
    {
        "name": "Bitcoin Magazine",
        "handle": "@BitcoinMagazine",
        "youtube_channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
    },
    {
        "name": "Simply Bitcoin",
        "handle": "@SimplyBitcoin",
        "youtube_channel_id": "UCEbyOaYhPkMmIbGR2MhAAHg",
    },
    {
        "name": "The Bitcoin Layer",
        "handle": "@TheBitcoinLayer",
        "youtube_channel_id": "UCwO2JcGAvqWTH0vMpNMfmNw",
    },
    {
        "name": "Coin Bureau",
        "handle": "@CoinBureau",
        "youtube_channel_id": "UCqK_GSMbpiV8spgD3ZGloSw",
    },
    {
        "name": "Anthony Pompliano",
        "handle": "@AnthonyPompliano",
        "youtube_channel_id": "UCevXpeL8cBtDnYYpMHvbOug",
    },
]

# ── Clip Duration Config ──────────────────────────────────────────
# Full episode clips: 90-120 seconds each
CLIP_DURATION_MIN = 90
CLIP_DURATION_MAX = 120

# X teaser: best 15-25 second moment from each full clip
TEASER_CLIP_MIN = 15
TEASER_CLIP_MAX = 25

# ── ElevenLabs Config ─────────────────────────────────────────────
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL = "eleven_monolingual_v1"

# ── Grok Prompts ──────────────────────────────────────────────────

# Main clip selection: find the best 90-120s segment
CLIP_SELECTION_PROMPT = """You are a Bitcoin news editor for "Pulse Check" - a daily highlight show.

Analyze this transcript from {channel_name} and find the SINGLE BEST clip segment.

Requirements:
- Clip must be {min_dur}-{max_dur} seconds long (STRICTLY enforced)
- Pick the most newsworthy, impactful, or insightful moment
- Must start and end at natural speech boundaries
- Prefer segments with clear analysis, breaking news, or strong opinions
- Avoid intros, outros, sponsor reads, and filler
- The segment should be self-contained and make sense without additional context

Transcript (with timestamps):
{transcript}

Respond in JSON format ONLY:
{{
    "start_time": <float seconds>,
    "end_time": <float seconds>,
    "duration": <float seconds>,
    "headline": "<short headline for this clip - max 10 words>",
    "summary": "<1 sentence describing what's said>",
    "relevance_score": <1-10>,
    "teaser_start": <float - the most viral/quotable 20s moment starts here>,
    "teaser_end": <float - teaser moment ends here>,
    "teaser_hook": "<the punchy one-liner or key statement in that 20s moment>"
}}
"""

# Transition script generation
TRANSITION_PROMPT = """You are the host of "Pulse Check" - a daily Bitcoin news show.
Write a SHORT, punchy transition script between two segments.

Previous segment: {prev_channel} - "{prev_headline}"
Next segment: {next_channel} - "{next_headline}"

Rules:
- 2-3 sentences MAX (will be read in ~15-20 seconds)
- Conversational, energetic tone - like a podcast host
- Bridge the topics naturally
- No fluff, no "stay tuned", no "let's dive in"
- Sound like you actually understand Bitcoin, not a generic host

Respond with ONLY the script text, no quotes or labels.
"""

# Intro script
INTRO_PROMPT = """You are the host of "Pulse Check" - a daily Bitcoin news show on Protocol Pulse.
Write the opening line for today's episode ({date_str}).

Today's headlines:
{headlines}

Rules:
- 2-3 sentences MAX (~15 seconds when spoken)
- Hook the viewer immediately with the biggest story
- Energetic but not cheesy
- End with something like "Let's get into it" or similar natural transition

Respond with ONLY the script text.
"""

# Outro script
OUTRO_PROMPT = """You are the host of "Pulse Check" wrapping up today's episode.

Today covered:
{headlines}

Write a closing line:
- 2 sentences MAX (~10 seconds)
- Quick recap energy, not a full summary
- End with a call to action: subscribe, follow @ProtocolPulse
- Keep it natural, not corporate

Respond with ONLY the script text.
"""


def get_latest_video_url(channel_id: str) -> str | None:
    """Get the latest video URL from a YouTube channel."""
    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        resp = requests.get(feed_url, timeout=15)
        if resp.status_code != 200:
            return None

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        entries = root.findall("atom:entry", ns)
        if not entries:
            return None

        video_id = entries[0].find("yt:videoId", ns)
        if video_id is not None:
            return f"https://www.youtube.com/watch?v={video_id.text}"
        return None

    except Exception as e:
        logger.error(f"Error fetching latest video for {channel_id}: {e}")
        return None


def call_grok(prompt: str, temperature: float = 0.3) -> str | None:
    """Call Grok-3 API and return the response text."""
    xai_key = os.environ.get("XAI_API_KEY")
    if not xai_key:
        logger.error("XAI_API_KEY not configured")
        return None

    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {xai_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=60,
        )

        if resp.status_code != 200:
            logger.error(f"Grok API error: {resp.status_code} - {resp.text}")
            return None

        return resp.json()["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"Grok call error: {e}")
        return None


def select_clip_segment(transcript: dict, channel_name: str) -> dict | None:
    """Use Grok-3 to find the best 90-120s clip AND the best 20s teaser moment."""
    try:
        # Format transcript with timestamps
        formatted = ""
        for seg in transcript.get("segments", []):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "").strip()
            formatted += f"[{start:.1f}s - {end:.1f}s] {text}\n"

        prompt = CLIP_SELECTION_PROMPT.format(
            channel_name=channel_name,
            min_dur=CLIP_DURATION_MIN,
            max_dur=CLIP_DURATION_MAX,
            transcript=formatted[:12000],
        )

        content = call_grok(prompt)
        if not content:
            return None

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        # Validate main clip duration
        duration = result.get("duration", 0)
        if duration < CLIP_DURATION_MIN - 10 or duration > CLIP_DURATION_MAX + 15:
            logger.warning(f"Clip duration {duration}s outside range, clamping...")
            result["end_time"] = result["start_time"] + CLIP_DURATION_MAX
            result["duration"] = CLIP_DURATION_MAX

        # Validate teaser duration
        teaser_dur = result.get("teaser_end", 0) - result.get("teaser_start", 0)
        if teaser_dur < TEASER_CLIP_MIN or teaser_dur > TEASER_CLIP_MAX + 5:
            # Default: take the first 20s of the main clip
            result["teaser_start"] = result["start_time"]
            result["teaser_end"] = result["start_time"] + 20

        return result

    except Exception as e:
        logger.error(f"Error selecting clip: {e}")
        return None


def generate_voiceover(script: str, output_path: str) -> bool:
    """Generate ElevenLabs voiceover from script text."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not set, skipping voiceover")
        return False

    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": script,
                "model_id": ELEVENLABS_MODEL,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=30,
        )

        if resp.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"  ✓ Voiceover: {output_path}")
            return True
        else:
            logger.error(f"ElevenLabs error: {resp.status_code}")
            return False

    except Exception as e:
        logger.error(f"Voiceover error: {e}")
        return False


def generate_transition_scripts(clips: list[dict], date_str: str) -> dict:
    """
    Generate all voiceover scripts and audio: intro, transitions, outro.

    Returns dict with paths to audio files:
      {
        "intro": "path/to/intro.mp3",
        "transitions": ["path/to/trans_1.mp3", ...],
        "outro": "path/to/outro.mp3"
      }
    """
    vo_dir = f"data/video_engine/voiceovers/{date_str}"
    os.makedirs(vo_dir, exist_ok=True)
    result = {"intro": None, "transitions": [], "outro": None}

    headlines = "\n".join(
        f"- {c['channel']}: {c['headline']}" for c in clips
    )

    # ── Intro ─────────────────────────────────────────────────────
    logger.info("Generating intro voiceover...")
    intro_script = call_grok(
        INTRO_PROMPT.format(date_str=date_str, headlines=headlines),
        temperature=0.7,
    )
    if intro_script:
        intro_path = f"{vo_dir}/intro.mp3"
        if generate_voiceover(intro_script, intro_path):
            result["intro"] = intro_path

    # ── Transitions between segments ──────────────────────────────
    for i in range(len(clips) - 1):
        logger.info(f"Generating transition {i+1}...")
        trans_script = call_grok(
            TRANSITION_PROMPT.format(
                prev_channel=clips[i]["channel"],
                prev_headline=clips[i]["headline"],
                next_channel=clips[i + 1]["channel"],
                next_headline=clips[i + 1]["headline"],
            ),
            temperature=0.7,
        )
        if trans_script:
            trans_path = f"{vo_dir}/transition_{i+1}.mp3"
            if generate_voiceover(trans_script, trans_path):
                result["transitions"].append(trans_path)
            else:
                result["transitions"].append(None)
        else:
            result["transitions"].append(None)

    # ── Outro ─────────────────────────────────────────────────────
    logger.info("Generating outro voiceover...")
    outro_script = call_grok(
        OUTRO_PROMPT.format(headlines=headlines),
        temperature=0.7,
    )
    if outro_script:
        outro_path = f"{vo_dir}/outro.mp3"
        if generate_voiceover(outro_script, outro_path):
            result["outro"] = outro_path

    return result


def run_pulse_check(date_str: str = None) -> dict:
    """
    Run the full Pulse Check pipeline.

    Returns dict with:
        - success: bool
        - full_episode: filename of 10-15 min video
        - x_teaser: filename of ~1:45 X trailer
        - clips: list of clip info (with teaser timestamps)
        - voiceovers: paths to voiceover audio
        - errors: list of errors
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"═══ Starting Pulse Check v2 for {date_str} ═══")

    ultron = UltronClient()
    results = {
        "success": False,
        "date": date_str,
        "full_episode": None,
        "x_teaser": None,
        "clips": [],
        "voiceovers": None,
        "errors": [],
    }

    # Check Ultron health
    if not ultron.health_check():
        results["errors"].append("Ultron server not reachable")
        logger.error("Ultron health check failed!")
        return results

    logger.info("✓ Ultron is online")

    # ── Process each partner channel ────────────────────────────
    clip_files = []
    teaser_clip_files = []

    for channel in PARTNER_CHANNELS:
        channel_name = channel["name"]
        logger.info(f"\n── Processing: {channel_name} ──")

        try:
            # Step 1: Get latest video
            video_url = get_latest_video_url(channel["youtube_channel_id"])
            if not video_url:
                logger.warning(f"No recent video found for {channel_name}")
                results["errors"].append(f"No video: {channel_name}")
                continue

            logger.info(f"  Found video: {video_url}")

            # Step 2: Download video on Ultron
            video_id = video_url.split("v=")[-1].split("&")[0]
            dl_result = ultron.download_video(video_url)
            if not dl_result or not dl_result.get("success"):
                logger.warning(f"  Download failed for {channel_name}")
                results["errors"].append(f"Download failed: {channel_name}")
                continue

            logger.info(f"  ✓ Downloaded: {dl_result.get('filename', 'unknown')}")

            # Step 3: Transcribe
            trans_result = ultron.transcribe_async(video_id)
            if not trans_result:
                results["errors"].append(f"Transcription start failed: {channel_name}")
                continue

            # Poll for completion
            for attempt in range(60):
                status = ultron.transcribe_status(video_id)
                if status and status.get("status") == "completed":
                    break
                if status and status.get("status") == "error":
                    raise Exception(f"Transcription error: {status.get('error')}")
                time.sleep(5)
            else:
                results["errors"].append(f"Transcription timeout: {channel_name}")
                continue

            logger.info(f"  ✓ Transcribed")

            # Step 4: Get transcript and select clip + teaser
            transcript = ultron.get_transcript(video_id)
            if not transcript:
                results["errors"].append(f"Transcript fetch failed: {channel_name}")
                continue

            clip_info = select_clip_segment(transcript, channel_name)
            if not clip_info:
                results["errors"].append(f"Clip selection failed: {channel_name}")
                continue

            logger.info(
                f"  ✓ Selected: {clip_info['headline']} "
                f"({clip_info['duration']:.0f}s, "
                f"teaser: {clip_info.get('teaser_hook', 'N/A')[:50]})"
            )

            # Step 5: Extract FULL clip (90-120s) for episode
            clip_filename = f"pulse_{date_str}_{channel_name.lower().replace(' ', '_')}.mp4"
            extract_result = ultron.extract_clip(
                video_id=video_id,
                start_time=clip_info["start_time"],
                end_time=clip_info["end_time"],
                output_filename=clip_filename,
            )

            if not extract_result or not extract_result.get("success"):
                results["errors"].append(f"Clip extraction failed: {channel_name}")
                continue

            logger.info(
                f"  ✓ Full clip: {clip_filename} "
                f"({extract_result.get('size_mb', '?')} MB)"
            )

            # Step 6: Extract TEASER clip (~20s) for X trailer
            teaser_filename = f"teaser_{date_str}_{channel_name.lower().replace(' ', '_')}.mp4"
            teaser_result = ultron.extract_clip(
                video_id=video_id,
                start_time=clip_info["teaser_start"],
                end_time=clip_info["teaser_end"],
                output_filename=teaser_filename,
            )

            if teaser_result and teaser_result.get("success"):
                teaser_clip_files.append(teaser_filename)
                logger.info(f"  ✓ Teaser clip: {teaser_filename}")
            else:
                logger.warning(f"  Teaser extraction failed (non-fatal)")

            clip_files.append(clip_filename)
            results["clips"].append(
                {
                    "channel": channel_name,
                    "handle": channel["handle"],
                    "headline": clip_info["headline"],
                    "summary": clip_info["summary"],
                    "duration": clip_info["duration"],
                    "filename": clip_filename,
                    "teaser_filename": teaser_filename if teaser_result else None,
                    "teaser_hook": clip_info.get("teaser_hook", ""),
                    "teaser_start": clip_info.get("teaser_start"),
                    "teaser_end": clip_info.get("teaser_end"),
                    "video_url": video_url,
                }
            )

        except Exception as e:
            logger.error(f"  Error processing {channel_name}: {e}")
            results["errors"].append(f"Error {channel_name}: {str(e)}")
            continue

    # ── Generate voiceovers ─────────────────────────────────────
    if len(clip_files) >= 2:
        logger.info(f"\n── Generating voiceovers ──")
        results["voiceovers"] = generate_transition_scripts(
            results["clips"], date_str
        )

        # Upload voiceovers to Ultron
        vo = results["voiceovers"]
        vo_files_to_upload = []

        if vo.get("intro"):
            vo_files_to_upload.append(("intro", vo["intro"]))
        for i, t in enumerate(vo.get("transitions", [])):
            if t:
                vo_files_to_upload.append((f"transition_{i+1}", t))
        if vo.get("outro"):
            vo_files_to_upload.append(("outro", vo["outro"]))

        for label, path in vo_files_to_upload:
            try:
                ultron.upload_asset(path, f"voiceovers/{date_str}/{os.path.basename(path)}")
                logger.info(f"  ✓ Uploaded {label} to Ultron")
            except Exception as e:
                logger.warning(f"  Failed to upload {label}: {e}")

    # ── Assemble FULL EPISODE (10-15 min) ───────────────────────
    if len(clip_files) < 2:
        logger.error("Not enough clips to assemble (need at least 2)")
        results["errors"].append("Insufficient clips for assembly")
        return results

    logger.info(f"\n── Assembling full episode ({len(clip_files)} clips) ──")

    episode_filename = f"pulse_check_{date_str}_full.mp4"

    # Build assembly manifest with voiceovers between clips
    assembly_parts = []
    vo = results.get("voiceovers", {})

    # Intro voiceover
    if vo and vo.get("intro"):
        assembly_parts.append({
            "type": "voiceover",
            "file": f"voiceovers/{date_str}/intro.mp3",
        })

    # Clips with transitions
    for i, clip_file in enumerate(clip_files):
        assembly_parts.append({
            "type": "clip",
            "file": clip_file,
        })

        # Add transition after each clip (except the last)
        if i < len(clip_files) - 1:
            transitions = vo.get("transitions", []) if vo else []
            if i < len(transitions) and transitions[i]:
                assembly_parts.append({
                    "type": "voiceover",
                    "file": f"voiceovers/{date_str}/transition_{i+1}.mp3",
                })

    # Outro voiceover
    if vo and vo.get("outro"):
        assembly_parts.append({
            "type": "voiceover",
            "file": f"voiceovers/{date_str}/outro.mp3",
        })

    assemble_result = ultron.assemble_video(
        clip_files=clip_files,
        output_filename=episode_filename,
        include_tag=True,
        assembly_parts=assembly_parts,
    )

    if assemble_result and assemble_result.get("success"):
        results["full_episode"] = episode_filename
        logger.info(
            f"✓ Full episode: {episode_filename} "
            f"({assemble_result.get('size_mb', '?')} MB, "
            f"{assemble_result.get('duration', '?')}s)"
        )
    else:
        results["errors"].append("Full episode assembly failed")
        logger.error("Full episode assembly failed!")

        # Fallback: assemble without voiceovers
        logger.info("Attempting assembly without voiceovers...")
        fallback_result = ultron.assemble_video(
            clip_files=clip_files,
            output_filename=episode_filename,
            include_tag=True,
        )
        if fallback_result and fallback_result.get("success"):
            results["full_episode"] = episode_filename
            logger.info(f"✓ Full episode (no voiceovers): {episode_filename}")

    # ── Assemble X TEASER (~1:45) ───────────────────────────────
    if teaser_clip_files:
        logger.info(f"\n── Assembling X teaser ({len(teaser_clip_files)} clips) ──")

        teaser_filename = f"pulse_check_{date_str}_teaser.mp4"
        teaser_result = ultron.assemble_video(
            clip_files=teaser_clip_files,
            output_filename=teaser_filename,
            include_tag=True,
        )

        if teaser_result and teaser_result.get("success"):
            results["x_teaser"] = teaser_filename
            logger.info(
                f"✓ X teaser: {teaser_filename} "
                f"({teaser_result.get('size_mb', '?')} MB, "
                f"{teaser_result.get('duration', '?')}s)"
            )
        else:
            results["errors"].append("X teaser assembly failed")
    else:
        results["errors"].append("No teaser clips available")

    results["success"] = results["full_episode"] is not None
    return results


def run_and_distribute(date_str: str = None) -> dict:
    """Run Pulse Check and distribute to all platforms."""
    from pp_services.video_engine.pulse_distributor import PulseDistributor

    result = run_pulse_check(date_str)

    if not result["success"]:
        logger.error(f"Pipeline failed: {result['errors']}")
        return result

    distributor = PulseDistributor()
    dist_result = distributor.distribute_all(result)
    result["distribution"] = dist_result

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    result = run_and_distribute()
    print(json.dumps(result, indent=2, default=str))
