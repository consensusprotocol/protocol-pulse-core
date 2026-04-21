#!/usr/bin/env python3
"""herald_agent.py — The Social Publisher.

Consumes: grade_complete (broadcast only when payload.broadcast_ready == True)

On each broadcast-ready A grade:
  1. Fires services/tweet_machine.py as a subprocess (no LLM call from here)
  2. Posts a Telegram alert announcing the episode
  3. Posts a streak banner when consecutive_a >= 5
  4. Saves {last_episode, last_grade, last_tweet_ts, lifetime_posts} state
  5. Logs per-run metrics (posts_fired, consecutive_a)

Budget: zero LLM calls. Pure orchestration.
"""
import logging
import os
import subprocess
import sys
import time

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from base_agent import BaseAgent
from event_bus import save_state, load_state, log_metric
import telegram

# Tweet machine lives under services/ of whichever repo root the agent runs from.
# Pick the first location that actually exists so both worktree and production resolve.
_REPO_ROOTS = [
    "/home/ultron/protocol_pulse",
    os.path.dirname(os.path.dirname(_AGENT_DIR)),  # parent of agents/
]
TWEET_MACHINE = None
for root in _REPO_ROOTS:
    candidate = os.path.join(root, "services", "tweet_machine.py")
    if os.path.exists(candidate):
        TWEET_MACHINE = candidate
        break


class HeraldAgent(BaseAgent):
    name = "herald"
    consumes = ["grade_complete"]

    def handle(self, event):
        payload = event.get("payload", {}) or {}
        if not payload.get("broadcast_ready"):
            self.logger.info(
                f"skip non-broadcast grade {payload.get('grade')} "
                f"({payload.get('score')}/100) — episode {payload.get('episode_date')}"
            )
            return

        grade = payload.get("grade", "?")
        score = payload.get("score", 0)
        consecutive_a = int(payload.get("consecutive_a", 0) or 0)
        episode_date = payload.get("episode_date", "")
        output_path = payload.get("output_path", "")

        prev = load_state(self.name) or {}
        lifetime = int(prev.get("lifetime_posts", 0)) + 1
        prev_consecutive_a = int(prev.get("last_consecutive_a", 0) or 0)

        # 1) Fire tweet_machine as a fire-and-forget subprocess
        posted = self._fire_tweet_machine()

        # 2) Episode broadcast alert
        telegram.send(
            f"✅ *Grade {grade}* ({score}/100) — Episode {episode_date} broadcast\n"
            f"Video: `{os.path.basename(output_path) if output_path else 'n/a'}`"
        )

        # 3) Streak banner (fire only when crossing into 5+ or on every new A past 5)
        if consecutive_a >= 5 and consecutive_a != prev_consecutive_a:
            telegram.send(f"🔥 *{consecutive_a}/10 consecutive A grades*")

        # 4) Metrics
        log_metric(self.name, "posts_fired", 1 if posted else 0, f"grade={grade} score={score}")
        log_metric(self.name, "consecutive_a", consecutive_a)

        # 5) State
        save_state(
            self.name,
            {
                "last_episode": episode_date,
                "last_grade": grade,
                "last_score": score,
                "last_output": output_path,
                "last_tweet_ts": time.time(),
                "last_tweet_posted": bool(posted),
                "last_consecutive_a": consecutive_a,
                "lifetime_posts": lifetime,
            },
            last_action=f"broadcast_{grade}_{score}",
            self_eval=1.0 if posted else 0.5,
            notes=f"posted={posted} streak={consecutive_a}",
        )

    def _fire_tweet_machine(self):
        """Fire tweet_machine.py as a detached subprocess. Returns True on spawn."""
        if not TWEET_MACHINE:
            self.logger.warning("tweet_machine.py not found on disk — skipping tweet fire")
            return False
        try:
            # Detached so a long-running tweet cycle never blocks the agent cycle.
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(TWEET_MACHINE)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            log_path = os.path.join(logs_dir, "herald_tweet_machine.log")
            with open(log_path, "ab") as log_fh:
                subprocess.Popen(
                    [sys.executable, TWEET_MACHINE],
                    cwd=os.path.dirname(os.path.dirname(TWEET_MACHINE)),
                    stdout=log_fh,
                    stderr=log_fh,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            self.logger.info(f"tweet_machine fired — log {log_path}")
            return True
        except Exception as exc:
            self.logger.error(f"tweet_machine fire failed: {exc}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")
    handled = HeraldAgent().cycle()
    print(f"herald: {handled} event(s) handled; tweet_machine={TWEET_MACHINE}")
