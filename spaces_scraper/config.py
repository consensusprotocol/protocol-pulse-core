"""
config.py — Configuration for X Spaces Scraper
All secrets loaded from environment; nothing hardcoded.
"""
import os

# ─── API Keys ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# X/Twitter API (optional — empty means fall back to guest token / Playwright)
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")

# X app-only bearer used for guest-token flow (public, not secret)
X_PUBLIC_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# ─── Target Accounts ────────────────────────────────────────────────────────
TARGET_ACCOUNTS = [
    "sabordebitcoin",
    "BitcoinMagazine",
    "thebitcoinlayer",
    "WhatBitcoinDid",
    "DocumentingBTC",
    "MartyBent",
    "PeterMcCormack",
    "gladstein",
    "FossGregfoss",
    "maxkeiser",
    "StephanLivera",
    "bitcoinmagazine",
    "BitcoinArchive",
    "LynAldenContact",
]

# ─── Detection ──────────────────────────────────────────────────────────────
# How often to poll for new live Spaces (seconds)
DETECTOR_POLL_INTERVAL = 60

# Space keywords to search for (X API v2 Spaces search, or topic filter)
SPACE_SEARCH_KEYWORDS = ["bitcoin", "btc", "lightning network", "sats"]

# ─── Audio Capture ──────────────────────────────────────────────────────────
# Max concurrent spaces to capture simultaneously
MAX_CONCURRENT_SPACES = 2

# Audio segment duration in seconds (pulled from HLS playlist)
SEGMENT_DURATION_S = 5

# ─── Whisper ────────────────────────────────────────────────────────────────
WHISPER_MODEL = "large-v3"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"
WHISPER_LANGUAGE = "en"
WHISPER_BEAM_SIZE = 5

# ─── Sentiment Analyzer ─────────────────────────────────────────────────────
# How often to re-run sentiment analysis on rolling transcript (seconds)
SENTIMENT_ANALYSIS_INTERVAL = 30

# Rolling window for transcript context (minutes)
TRANSCRIPT_WINDOW_MINUTES = 5

# Gemini model to use
GEMINI_MODEL = "gemini-2.0-flash"

# ─── API Server ─────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8210

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_FILE = "spaces_scraper.log"
LOG_LEVEL = "INFO"
