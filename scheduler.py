"""Batch 5 validator: re-export auto_viral_reel so 'from scheduler import auto_viral_reel' works from project root."""
from services.scheduler import auto_viral_reel

__all__ = ["auto_viral_reel"]
