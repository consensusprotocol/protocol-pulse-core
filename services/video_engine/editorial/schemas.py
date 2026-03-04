"""
Pulse Check Content OS — Data Contracts
========================================
All AI outputs MUST validate against these schemas before proceeding.
Schema failure = retry once, then failover mode.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


# ── Stage 1: Grok Triage Output ──

class CandidateMoment(BaseModel):
    source_type: Literal["youtube", "spaces", "tweet", "article"]
    source_name: str
    source_id: str
    approx_start: str  # "MM:SS"
    approx_end: str    # "MM:SS"
    topic: str = Field(max_length=50)
    why_interesting: str = Field(max_length=200)
    speaker: Optional[str] = None
    content_type: Literal["insight", "news", "opinion", "data", "drama", "technical"]
    relevance_score: int = Field(ge=1, le=10)
    sentiment: Literal["bullish", "bearish", "neutral"] = "neutral"


class RejectedSegment(BaseModel):
    """Segments Grok explicitly rejects — prevents clipping ad reads, sponsor plugs, etc."""
    source_id: str
    approx_start: str
    approx_end: str
    reason: Literal["sponsor_read", "off_topic", "repeat", "altcoin_shill",
                     "needs_visual_context", "low_quality", "ad_read",
                     "pure_price_speculation", "price_speculation_without_thesis"]


class RiskFlag(BaseModel):
    """Claims that need evidence or softening before narrator reads them."""
    source_id: str
    claim: str
    risk_type: Literal["unverified_number", "regulatory_claim", "allegation",
                         "ath_claim", "prediction", "attribution"]
    approx_timestamp: str


class TriageOutput(BaseModel):
    candidates: List[CandidateMoment]
    rejected: List[RejectedSegment] = []
    risk_flags: List[RiskFlag] = []


# ── Stage 1.5: Clustering Output ──

class StoryCluster(BaseModel):
    cluster_id: str
    topic: str
    hero_candidates: List[str]   # candidate indices (best 1-2 per cluster)
    all_candidates: List[str]
    novelty_score: float = Field(ge=0, le=1)  # 0 = stale, 1 = fresh
    sources_represented: List[str]


class ClusterOutput(BaseModel):
    clusters: List[StoryCluster]
    dropped_as_stale: List[str] = []
    diversity_warnings: List[str] = []


# ── Stage 2: Claude Director ShowPlanV2 ──

class ClipDefinition(BaseModel):
    source_type: Literal["youtube", "spaces"]
    source_name: str
    source_id: str
    speaker: str
    clip_transcript: str   # EXACT text from transcript — used for timestamp matching
    approx_start: str
    approx_end: str
    why_this_clip: str
    intro_line: str        # Narrator says this BEFORE the clip plays
    starts_complete_sentence: bool = True
    ends_complete_sentence: bool = True
    thought_is_self_contained: bool = True


class TweetOverlay(BaseModel):
    author_handle: str = ""
    author_name: str = ""
    tweet_text: str = ""
    tweet_url: Optional[str] = None
    narrator_read: str = ""  # What narrator says while tweet is on screen


class ClaimWithEvidence(BaseModel):
    """Provenance tracking — every factual claim needs backing."""
    claim: str
    evidence: List[str]    # source_ids or URLs
    risk: Literal["low", "medium", "high"] = "low"


class Story(BaseModel):
    story_number: int = 0
    story_type: Literal["lead", "follow", "quick_hit"] = "quick_hit"
    story_mode: Literal["single_thread", "debate", "timeline", "mythbust"] = "single_thread"
    headline: str = ""
    narrator_intro_script: str = ""
    clips: List[ClipDefinition]
    tweet_overlays: List[TweetOverlay] = []
    narrator_bridge_script: Optional[str] = None
    narrator_wrap_script: Optional[str] = None
    claims: List[ClaimWithEvidence] = []
    broll_category: Literal["mining", "macro", "adoption", "dev",
                             "regulation", "community", "generic"] = "generic"
    emotion: Literal["calm", "urgent", "encouraging", "serious"] = "calm"


class SignalVsNoise(BaseModel):
    """The daily ritual segment that becomes the brand identity."""
    narrator_intro: str = "Signal versus noise, in 30 seconds."
    signal: str       # fundamentals/adoption/dev
    noise: str        # drama/altcoin bait/price-only take
    wildcard: str     # weird but important


class ShortPlan(BaseModel):
    """Claude plans each vertical short — not auto-generated from clips."""
    story_ref: int = 1        # which story number
    hook_text: str = Field(default="", max_length=40)  # bold text on screen first 3 sec
    short_intro_script: str = ""  # narrator setup (10-12 sec)
    clip_ref: int = 0         # which clip index in that story
    takeaway_script: str = "" # narrator wrap
    cta: str = "Full Pulse Check in bio."


class CommunityPulse(BaseModel):
    narrator_intro: str
    tweets: List[TweetOverlay]
    engagement_hook: str


class ShowPlanV2(BaseModel):
    episode_date: str
    episode_headline: str
    cold_open_script: str

    stories: List[Story]
    quick_hits: List[Story] = []
    signal_vs_noise: SignalVsNoise
    community_pulse: Optional[CommunityPulse] = None
    shorts_plan: List[ShortPlan] = []
    outro_script: str

    tomorrows_watchlist: List[str] = []  # hints for next episode's editorial memory
    estimated_duration_seconds: int
    dominant_theme: str
    tone: str = "informative"
    slow_news_mode: Optional[Literal["deep_dive", "week_in_review", "education"]] = None


# ── Stage 3: QA Report ──

class QAIssue(BaseModel):
    issue_type: Literal["clip_boundary", "duration", "diversity", "claim_risk",
                          "stale_topic", "missing_intro", "ethics", "schema"]
    detail: str
    fix_suggestion: str


class QAReport(BaseModel):
    approved: bool
    issues: List[QAIssue] = []
    suggested_edits: Optional[dict] = None
    retry_count: int = 0


# ── Assembly Manifest ──

class TimelineEntry(BaseModel):
    entry_type: Literal["branded_intro", "voiceover", "clip", "tweet_overlay",
                          "signal_vs_noise", "branded_outro", "transition"]
    audio_path: Optional[str] = None
    visual: Optional[str] = None       # "background_loop", "broll_mining", etc.
    source_video_path: Optional[str] = None
    start_time: Optional[str] = None   # seconds with decimals
    end_time: Optional[str] = None
    lower_third_name: Optional[str] = None
    lower_third_title: Optional[str] = None
    image_path: Optional[str] = None   # for tweet overlays
    duration_sec: Optional[float] = None
    transition_in: Literal["cut", "crossfade_0.5s", "crossfade_1s"] = "cut"
    # Metadata for overlays during host segments
    dialogue_text: Optional[str] = None      # raw text for stat/quote extraction
    host_name: Optional[str] = None          # for host lower third
    topic_label: Optional[str] = None        # current topic display


class AssemblyManifest(BaseModel):
    episode_date: str
    output_name: str
    timeline: List[TimelineEntry]
    audio_settings: dict = {
        "narrator_lufs": -16,
        "clip_lufs": -18,
        "music_lufs": -30,
    }


# ── Editorial Memory ──

class RunningStory(BaseModel):
    topic: str
    first_covered: str
    last_covered: str
    angles_used: List[str]
    times_covered: int
    sources_used: List[str]


class EditorialMemory(BaseModel):
    recent_episodes: List[dict] = []   # last 14 days
    running_stories: List[RunningStory] = []
    overused_sources: List[str] = []
    what_worked_yesterday: Optional[str] = None
    what_underperformed_yesterday: Optional[str] = None


# ── Cost Tracking ──

class RunCosts(BaseModel):
    episode_date: str
    grok_tokens_in: int = 0
    grok_tokens_out: int = 0
    claude_tokens_in: int = 0
    claude_tokens_out: int = 0
    elevenlabs_characters: int = 0
    whisper_minutes: float = 0
    total_runtime_seconds: float = 0
    estimated_cost_usd: float = 0
