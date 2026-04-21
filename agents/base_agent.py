#!/usr/bin/env python3
"""base_agent.py — shared contract for every daemon in the Sovereign Agent Fleet.

Subclasses declare:
    name     — unique identifier, matches target_agent in event_bus
    consumes — list of event_type strings this agent handles (None = all)

Subclasses implement:
    handle(event) — process a single event dict from event_bus.consume()

BaseAgent.cycle() is the per-tick entry point the runner calls every POLL_INTERVAL.
It pulls pending events, dispatches to handle(), marks each complete or failed.
"""
import logging
import os
import sys
import traceback

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from event_bus import consume, complete_event, fail_event, pending_count


class BaseAgent:
    name = "base"
    consumes = None

    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.name}")

    def cycle(self):
        """One poll tick. Drain pending events, dispatch each to handle()."""
        events = consume(self.name, self.consumes, limit=10)
        if not events:
            return 0
        for event in events:
            ev_id = event["id"]
            try:
                self.handle(event)
                complete_event(ev_id)
                self.logger.info(f"handled event {ev_id} {event['type']} from {event['source']}")
            except Exception as exc:
                tb = traceback.format_exc(limit=3)
                fail_event(ev_id, f"{exc.__class__.__name__}: {exc}")
                self.logger.error(f"event {ev_id} failed: {exc}\n{tb}")
        return len(events)

    def handle(self, event):
        raise NotImplementedError(f"{self.name} must implement handle()")

    def backlog(self):
        return pending_count(self.name)
