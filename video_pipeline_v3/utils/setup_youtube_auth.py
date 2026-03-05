#!/usr/bin/env python3
"""Setup YouTube OAuth2 — interactive one-time setup.

Walks through Google OAuth2 flow for YouTube Data API v3 uploads.
Saves tokens to config/youtube_tokens.json.

Prerequisites:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth2 Client ID (Desktop application)
  3. Enable YouTube Data API v3 in your project
  4. Download or note the client_id and client_secret

Usage:
  python3 utils/setup_youtube_auth.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS_PATH = os.path.join(BASE, "config", "youtube_tokens.json")
CONFIG_DIR = os.path.join(BASE, "config")

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def setup():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    print("=" * 60)
    print("  YOUTUBE OAUTH2 SETUP — Protocol Pulse")
    print("=" * 60)
    print()
    print("This script sets up YouTube upload credentials.")
    print("You only need to run this once.")
    print()
    print("PREREQUISITES:")
    print("  1. Google Cloud project with YouTube Data API v3 enabled")
    print("  2. OAuth2 Client ID (Desktop application type)")
    print("  3. client_id and client_secret from the credentials page")
    print()

    # Check for existing tokens
    if os.path.exists(TOKENS_PATH):
        with open(TOKENS_PATH) as f:
            existing = json.load(f)
        if existing.get("refresh_token"):
            print(f"Existing tokens found at {TOKENS_PATH}")
            resp = input("Overwrite? (y/N): ").strip().lower()
            if resp != "y":
                print("Keeping existing tokens.")
                return

    client_id = input("Enter client_id: ").strip()
    if not client_id:
        print("ERROR: client_id is required.")
        sys.exit(1)

    client_secret = input("Enter client_secret: ").strip()
    if not client_secret:
        print("ERROR: client_secret is required.")
        sys.exit(1)

    # Build authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES.replace(' ', '%20')}"
        "&response_type=code"
        "&access_type=offline"
        "&prompt=consent"
    )

    print()
    print("=" * 60)
    print("  STEP 1: Open this URL in your browser:")
    print("=" * 60)
    print()
    print(auth_url)
    print()
    print("Sign in with the Google account that owns the YouTube channel.")
    print("After granting access, you'll get an authorization code.")
    print()

    auth_code = input("Enter the authorization code: ").strip()
    if not auth_code:
        print("ERROR: Authorization code is required.")
        sys.exit(1)

    # Exchange code for tokens
    print("\nExchanging code for tokens...")
    try:
        import requests
    except ImportError:
        print("ERROR: requests library required. Run: pip install requests")
        sys.exit(1)

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }, timeout=30)

    if resp.status_code != 200:
        print(f"ERROR: Token exchange failed: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    token_data = resp.json()

    if "refresh_token" not in token_data:
        print("ERROR: No refresh_token in response. Try again with prompt=consent.")
        sys.exit(1)

    # Save tokens
    tokens = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": token_data["refresh_token"],
        "access_token": token_data.get("access_token", ""),
    }

    with open(TOKENS_PATH, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(TOKENS_PATH, 0o600)

    print()
    print("=" * 60)
    print("  SUCCESS — YouTube OAuth2 configured!")
    print("=" * 60)
    print(f"  Tokens saved to: {TOKENS_PATH}")
    print()
    print("  Next steps:")
    print("  1. Set youtube_auto_upload to true in config/feature_flags.json")
    print("  2. First upload will be 'unlisted' — verify it looks correct")
    print("  3. Then switch to 'public' in utils/youtube_upload.py")
    print()


if __name__ == "__main__":
    setup()
