#!/usr/bin/env python3
"""Safely exports ANTHROPIC_API_KEY from .env to a shell-sourceable file"""
from pathlib import Path
from dotenv import dotenv_values
vals = dotenv_values(Path.home() / "protocol_pulse/.env")
key = vals.get("ANTHROPIC_API_KEY","")
if not key:
    raise SystemExit("ERROR: ANTHROPIC_API_KEY not found in .env")
# Write to a clean single-line export file
out = Path("/tmp/cc_api_key.sh")
out.write_text(f"export ANTHROPIC_API_KEY='{key}'\n")
out.chmod(0o600)
print(f"Exported key ({len(key)} chars) to {out}")
