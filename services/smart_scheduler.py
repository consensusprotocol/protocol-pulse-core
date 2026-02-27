"""
INTELLIGENT SCHEDULING SYSTEM
================================
Smart scheduling for the daily Bitcoin news pipeline.

Features:
  - Optimal posting times based on Twitter engagement data
  - Market volatility awareness (publish faster during high-vol)
  - Content calendar (avoid overlap with scheduled events)
  - Timezone optimization for US audience
  - Weekend vs weekday content strategy
  - Breaking news interrupts (Pulse Alert integration)

Usage:
    from services.smart_scheduler import SmartScheduler
    scheduler = SmartScheduler()
    next_slot = scheduler.get_next_optimal_slot("daily_episode")
    scheduler.should_publish_breaking_news(urgency_score)
"""

import os
import json
import logging
from datetime import datetime, timedelta, time as dtime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import pytz

logger = logging.getLogger("SmartScheduler")

ET = pytz.timezone("America/New_York")
UTC = pytz.UTC

# ─── Engagement Windows ───
# Based on typical Bitcoin Twitter audience engagement patterns
# Each entry: (hour_et, engagement_weight)

WEEKDAY_ENGAGEMENT = {
    # Early morning (5-7 AM ET): Moderate — pre-market traders
    5: 0.4, 6: 0.6, 7: 0.7,
    # Morning peak (8-10 AM ET): High — market open, news cycle
    8: 0.85, 9: 0.95, 10: 0.9,
    # Late morning (11 AM - 12 PM ET): Good
    11: 0.8, 12: 0.75,
    # Afternoon (1-3 PM ET): Moderate
    13: 0.65, 14: 0.7, 15: 0.75,
    # Late afternoon (4-6 PM ET): Rising — market close + commute
    16: 0.8, 17: 0.85, 18: 0.8,
    # Evening (7-9 PM ET): Good — leisure browsing
    19: 0.75, 20: 0.7, 21: 0.6,
    # Night (10 PM - 4 AM ET): Low
    22: 0.4, 23: 0.3, 0: 0.2, 1: 0.15, 2: 0.1, 3: 0.1, 4: 0.2,
}

WEEKEND_ENGAGEMENT = {
    # Weekends: Later start, lower overall but more browsing
    5: 0.1, 6: 0.15, 7: 0.2,
    8: 0.3, 9: 0.5, 10: 0.65,
    11: 0.7, 12: 0.65,
    13: 0.6, 14: 0.55, 15: 0.5,
    16: 0.55, 17: 0.6, 18: 0.55,
    19: 0.5, 20: 0.45, 21: 0.35,
    22: 0.25, 23: 0.15, 0: 0.1, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.1,
}

# Content type → optimal windows (ET hours)
CONTENT_TYPE_WINDOWS = {
    "daily_episode": {
        "weekday": [(8, 10)],        # Morning market-open window
        "weekend": [(10, 12)],       # Later start
    },
    "breaking_news": {
        "weekday": [(7, 22)],        # Any waking hour
        "weekend": [(9, 21)],
    },
    "pulse_alert": {
        "weekday": [(0, 24)],        # 24/7 for breaking market moves
        "weekend": [(0, 24)],
    },
    "newsletter": {
        "weekday": [(6, 8)],         # Pre-market morning email
        "weekend": [(9, 11)],
    },
    "thread": {
        "weekday": [(9, 11), (17, 19)],  # Morning peak + evening
        "weekend": [(10, 13)],
    },
    "shorts": {
        "weekday": [(12, 14), (18, 20)],  # Lunch + evening
        "weekend": [(11, 15)],
    },
}


class MarketVolatilityTracker:
    """Track market volatility to adjust publishing frequency."""

    @staticmethod
    def get_current_volatility() -> float:
        """Get current market volatility indicator (0.0 = calm, 1.0 = extreme).

        Uses BTC price change percentage as a proxy.
        """
        try:
            import requests
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd",
                        "include_24hr_change": "true"},
                timeout=10
            )
            data = resp.json().get("bitcoin", {})
            change_24h = abs(data.get("usd_24h_change", 0))

            # Map percentage change to volatility score
            if change_24h > 10:
                return 1.0   # Extreme
            elif change_24h > 5:
                return 0.8   # Very high
            elif change_24h > 3:
                return 0.6   # High
            elif change_24h > 1.5:
                return 0.4   # Moderate
            elif change_24h > 0.5:
                return 0.2   # Low
            return 0.1       # Very calm

        except Exception as e:
            logger.warning(f"Volatility check failed, using default: {e}")
            return 0.3  # Default moderate

    @staticmethod
    def should_accelerate_publishing(volatility: float) -> bool:
        """Determine if we should publish faster due to market conditions."""
        return volatility >= 0.6


class ContentCalendar:
    """Manage content calendar to avoid overlap."""

    CALENDAR_FILE = Path("state/content_calendar.json")

    @classmethod
    def load(cls) -> Dict:
        if cls.CALENDAR_FILE.exists():
            try:
                return json.loads(cls.CALENDAR_FILE.read_text())
            except Exception as e:
                logger.warning(f"ContentCalendar load failed, using empty: {e}")
        return {"events": [], "blackout_windows": []}

    @classmethod
    def save(cls, data: Dict):
        cls.CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.CALENDAR_FILE.write_text(json.dumps(data, indent=2, default=str))

    @classmethod
    def add_event(cls, title: str, dt: datetime, duration_minutes: int = 60,
                  content_type: str = "general"):
        """Add an event to the calendar."""
        cal = cls.load()
        cal["events"].append({
            "title": title,
            "datetime": dt.isoformat(),
            "duration_minutes": duration_minutes,
            "content_type": content_type,
        })
        # Keep only future events + last 7 days
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        cal["events"] = [e for e in cal["events"] if e["datetime"] > cutoff]
        cls.save(cal)

    @classmethod
    def check_conflict(cls, dt: datetime, content_type: str) -> Optional[str]:
        """Check if a proposed time conflicts with existing events.
        Returns conflict description or None.
        """
        cal = cls.load()
        proposed = dt.isoformat()

        for event in cal.get("events", []):
            event_dt = datetime.fromisoformat(event["datetime"])
            event_end = event_dt + timedelta(minutes=event.get("duration_minutes", 60))

            if event_dt <= dt <= event_end:
                return f"Conflicts with: {event['title']} ({event['content_type']})"

        # Check blackout windows
        for blackout in cal.get("blackout_windows", []):
            start = datetime.fromisoformat(blackout["start"])
            end = datetime.fromisoformat(blackout["end"])
            if start <= dt <= end:
                return f"In blackout window: {blackout.get('reason', 'scheduled maintenance')}"

        return None


class SmartScheduler:
    """Intelligent content scheduling engine."""

    def __init__(self):
        self.volatility_tracker = MarketVolatilityTracker()
        self.calendar = ContentCalendar()

    def get_next_optimal_slot(self, content_type: str,
                              after: datetime = None) -> Dict:
        """Find the next optimal publishing slot for content type.

        Returns:
            {
                "datetime_utc": "...",
                "datetime_et": "...",
                "engagement_score": 0.85,
                "reason": "Morning peak window",
                "volatility": 0.3,
                "accelerated": False
            }
        """
        now = after or datetime.now(ET)
        if now.tzinfo is None:
            now = ET.localize(now)

        is_weekend = now.weekday() >= 5
        windows = CONTENT_TYPE_WINDOWS.get(content_type, {})
        day_type = "weekend" if is_weekend else "weekday"
        time_windows = windows.get(day_type, [(8, 18)])

        engagement = WEEKEND_ENGAGEMENT if is_weekend else WEEKDAY_ENGAGEMENT

        # Find the next available slot in optimal windows
        best_slot = None
        best_score = -1

        for hour_start, hour_end in time_windows:
            for hour in range(hour_start, hour_end):
                candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if candidate <= now:
                    # Try tomorrow if past this hour
                    candidate += timedelta(days=1)
                    # Re-evaluate weekend status for tomorrow
                    if candidate.weekday() >= 5:
                        engagement = WEEKEND_ENGAGEMENT
                    else:
                        engagement = WEEKDAY_ENGAGEMENT

                score = engagement.get(hour, 0.3)

                # Check calendar conflicts
                conflict = self.calendar.check_conflict(candidate, content_type)
                if conflict:
                    score *= 0.3  # Penalize but don't fully block

                if score > best_score:
                    best_score = score
                    best_slot = candidate

        if not best_slot:
            # Fallback: next hour
            best_slot = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0)
            best_score = engagement.get(best_slot.hour, 0.3)

        # Check volatility
        volatility = self.volatility_tracker.get_current_volatility()
        accelerated = self.volatility_tracker.should_accelerate_publishing(volatility)

        if accelerated and content_type in ("breaking_news", "pulse_alert"):
            # During high volatility, publish ASAP
            best_slot = now + timedelta(minutes=5)
            best_score = 1.0

        # Convert to UTC
        utc_slot = best_slot.astimezone(UTC)

        # Determine reason
        hour = best_slot.hour
        if accelerated:
            reason = f"High volatility ({volatility:.1f}) — accelerated publishing"
        elif 8 <= hour <= 10:
            reason = "Morning market-open peak"
        elif 17 <= hour <= 19:
            reason = "Evening engagement window"
        elif 12 <= hour <= 14:
            reason = "Midday window"
        elif is_weekend:
            reason = "Weekend optimal window"
        else:
            reason = f"Scheduled window (engagement: {best_score:.0%})"

        return {
            "datetime_utc": utc_slot.isoformat(),
            "datetime_et": best_slot.isoformat(),
            "engagement_score": round(best_score, 2),
            "reason": reason,
            "volatility": round(volatility, 2),
            "accelerated": accelerated,
            "is_weekend": is_weekend,
            "content_type": content_type,
        }

    def should_publish_breaking_news(self, urgency_score: float = 0.0,
                                      content: str = "") -> Dict:
        """Determine if breaking news should interrupt the schedule.

        Args:
            urgency_score: 0.0 (routine) to 1.0 (critical market event)
            content: Brief description for logging

        Returns:
            {"publish": bool, "delay_minutes": int, "reason": str}
        """
        volatility = self.volatility_tracker.get_current_volatility()
        now_et = datetime.now(ET)
        hour = now_et.hour

        # Critical news always publishes immediately
        if urgency_score >= 0.9:
            return {
                "publish": True,
                "delay_minutes": 0,
                "reason": "Critical breaking news — immediate publish"
            }

        # High urgency + high volatility → quick publish
        if urgency_score >= 0.7 and volatility >= 0.5:
            return {
                "publish": True,
                "delay_minutes": 5,
                "reason": "High urgency + volatile market"
            }

        # During sleeping hours (11 PM - 6 AM ET), only publish if critical
        if hour < 6 or hour >= 23:
            if urgency_score >= 0.8:
                return {
                    "publish": True,
                    "delay_minutes": 0,
                    "reason": "Off-hours but critical urgency"
                }
            return {
                "publish": False,
                "delay_minutes": max(0, (6 - hour) * 60) if hour < 6 else (30 - hour) * 60,
                "reason": f"Queueing for morning — off-hours (urgency: {urgency_score:.1f})"
            }

        # Standard breaking news during waking hours
        if urgency_score >= 0.5:
            return {
                "publish": True,
                "delay_minutes": 10,
                "reason": "Standard breaking news — slight delay for QA"
            }

        # Low urgency → schedule normally
        return {
            "publish": False,
            "delay_minutes": 30,
            "reason": f"Low urgency ({urgency_score:.1f}) — scheduling in next window"
        }

    def get_daily_schedule(self, date: datetime = None) -> List[Dict]:
        """Generate the optimal content schedule for a day.

        Returns ordered list of scheduled content slots.
        """
        date = date or datetime.now(ET)
        if date.tzinfo is None:
            date = ET.localize(date)

        is_weekend = date.weekday() >= 5
        schedule = []

        # Define daily content plan
        if is_weekend:
            content_plan = [
                ("daily_episode", "Daily Bitcoin Pulse Check"),
                ("newsletter", "Weekend Intelligence Brief"),
                ("shorts", "Bitcoin Shorts Clip 1"),
                ("shorts", "Bitcoin Shorts Clip 2"),
                ("thread", "Weekend Analysis Thread"),
            ]
        else:
            content_plan = [
                ("newsletter", "Morning Intelligence Brief"),
                ("daily_episode", "Daily Bitcoin Pulse Check"),
                ("thread", "Market Analysis Thread"),
                ("shorts", "Bitcoin Shorts Clip 1"),
                ("shorts", "Bitcoin Shorts Clip 2"),
                ("shorts", "Bitcoin Shorts Clip 3"),
                ("thread", "Evening Recap Thread"),
            ]

        # Assign optimal times
        used_hours = set()
        for content_type, title in content_plan:
            slot = self.get_next_optimal_slot(content_type, after=date)

            # Avoid same-hour conflicts
            slot_hour = datetime.fromisoformat(
                slot["datetime_et"]).hour
            while slot_hour in used_hours:
                slot_hour += 1
            used_hours.add(slot_hour)

            schedule.append({
                "content_type": content_type,
                "title": title,
                **slot,
            })

        # Sort by time
        schedule.sort(key=lambda x: x.get("datetime_utc", ""))
        return schedule

    def get_posting_frequency(self) -> Dict:
        """Get recommended posting frequency based on current conditions."""
        volatility = self.volatility_tracker.get_current_volatility()
        now_et = datetime.now(ET)
        is_weekend = now_et.weekday() >= 5

        # Base frequencies (posts per day)
        base = {
            "tweets": 8 if not is_weekend else 4,
            "threads": 2 if not is_weekend else 1,
            "shorts": 3 if not is_weekend else 2,
            "articles": 4 if not is_weekend else 2,
        }

        # Adjust for volatility
        if volatility >= 0.8:
            multiplier = 2.0
            reason = "Extreme volatility — double output"
        elif volatility >= 0.6:
            multiplier = 1.5
            reason = "High volatility — 50% increase"
        elif volatility >= 0.4:
            multiplier = 1.2
            reason = "Moderate volatility — slight increase"
        else:
            multiplier = 1.0
            reason = "Normal conditions"

        adjusted = {k: int(v * multiplier) for k, v in base.items()}

        return {
            "base_frequency": base,
            "adjusted_frequency": adjusted,
            "multiplier": multiplier,
            "volatility": round(volatility, 2),
            "is_weekend": is_weekend,
            "reason": reason,
        }
