#!/usr/bin/env python3
"""
Background service to run the Protocol Pulse automated content scheduler.
This keeps the site fresh with new breaking news articles every 2 hours.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pp_services.scheduler import run_scheduler

if __name__ == '__main__':
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("📄 Protocol Pulse Scheduler stopped.")
    except Exception as e:
        print(f"💥 Scheduler crashed: {e}")
        sys.exit(1)