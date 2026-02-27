"""
ALPHA SCHEDULER - Automated Data Collection
============================================
Runs data ingestion every 4 hours to build historical data.
After 30 days, backtests become meaningful.

SCHEDULE:
- Every 4 hours: Full data ingestion (price, derivatives, mempool, sentiment, macro)
- Every day at 9am: Generate newsletter sections
- Store all datapoints with timestamps for backtesting

RUN OPTIONS:
1. python3 services/alpha_scheduler.py daemon   - Run as background daemon
2. python3 services/alpha_scheduler.py once     - Run once and exit
3. python3 services/alpha_scheduler.py status   - Show collection status
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovereign_intel_terminal import SovereignIntelTerminal, get_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AlphaScheduler")


class AlphaScheduler:
    """
    Automated data collection scheduler.
    """
    
    def __init__(self):
        self.terminal = SovereignIntelTerminal()
        self.collection_interval_hours = 4
        self.status_file = "data/scheduler_status.json"
    
    def _load_status(self) -> Dict[str, Any]:
        """Load scheduler status."""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            "last_run": None,
            "total_runs": 0,
            "errors": 0,
            "started_at": None
        }
    
    def _save_status(self, status: Dict[str, Any]):
        """Save scheduler status."""
        os.makedirs("data", exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(status, f, indent=2, default=str)
    
    def run_collection(self) -> Dict[str, Any]:
        """Run a single data collection cycle."""
        logger.info("Starting data collection cycle...")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Run full analysis with macro if FRED key available
            if os.environ.get("FRED_API_KEY"):
                result = self.terminal.run_full_with_macro()
            else:
                result = self.terminal.run()
            
            # Update status
            status = self._load_status()
            status["last_run"] = start_time.isoformat()
            status["total_runs"] = status.get("total_runs", 0) + 1
            if not status.get("started_at"):
                status["started_at"] = start_time.isoformat()
            self._save_status(status)
            
            # Log summary
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Collection complete in {duration:.1f}s")
            logger.info(f"  Regime: {result.get('regime', 'N/A').upper()}")
            logger.info(f"  Signals: {result.get('signals_triggered', 0)}")
            
            return {
                "success": True,
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "regime": result.get("regime"),
                "signals": result.get("signals_triggered", 0)
            }
            
        except Exception as e:
            logger.error(f"Collection error: {e}")
            status = self._load_status()
            status["errors"] = status.get("errors", 0) + 1
            self._save_status(status)
            return {
                "success": False,
                "error": str(e),
                "timestamp": start_time.isoformat()
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about data collection."""
        conn = get_db()
        
        # Total datapoints
        cursor = conn.execute("SELECT COUNT(*) FROM datapoints")
        total_datapoints = cursor.fetchone()[0]
        
        # Unique metrics
        cursor = conn.execute("SELECT COUNT(DISTINCT metric) FROM datapoints")
        unique_metrics = cursor.fetchone()[0]
        
        # Date range
        cursor = conn.execute("SELECT MIN(ts_utc), MAX(ts_utc) FROM datapoints")
        date_range = cursor.fetchone()
        
        # Days of data
        if date_range[0] and date_range[1]:
            start = datetime.fromisoformat(date_range[0].replace('Z', '+00:00'))
            end = datetime.fromisoformat(date_range[1].replace('Z', '+00:00'))
            days_collected = (end - start).days + 1
        else:
            days_collected = 0
        
        # Datapoints per metric
        cursor = conn.execute("""
            SELECT metric, COUNT(*) as count 
            FROM datapoints 
            GROUP BY metric 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_metrics = [(row[0], row[1]) for row in cursor.fetchall()]
        
        conn.close()
        
        # Scheduler status
        status = self._load_status()
        
        return {
            "total_datapoints": total_datapoints,
            "unique_metrics": unique_metrics,
            "date_range": {
                "start": date_range[0],
                "end": date_range[1]
            },
            "days_collected": days_collected,
            "days_until_backtest": max(0, 30 - days_collected),
            "backtest_ready": days_collected >= 30,
            "top_metrics": top_metrics,
            "scheduler": status
        }
    
    def print_status(self):
        """Print collection status report."""
        stats = self.get_collection_stats()
        
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      ALPHA DATA COLLECTION STATUS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
        print(f"  Total Datapoints:    {stats['total_datapoints']:,}")
        print(f"  Unique Metrics:      {stats['unique_metrics']}")
        print(f"  Days Collected:      {stats['days_collected']}")
        print(f"  Date Range:          {stats['date_range']['start'][:10] if stats['date_range']['start'] else 'N/A'} to {stats['date_range']['end'][:10] if stats['date_range']['end'] else 'N/A'}")
        print()
        
        if stats['backtest_ready']:
            print(f"  ✅ BACKTEST READY - You have 30+ days of data!")
        else:
            print(f"  ⏳ Days until backtest ready: {stats['days_until_backtest']}")
            print(f"     Keep running collection every 4 hours")
        
        print()
        print("  Top Metrics by Datapoints:")
        for metric, count in stats['top_metrics'][:5]:
            print(f"    • {metric}: {count}")
        
        print()
        print("  Scheduler Status:")
        sched = stats['scheduler']
        print(f"    • Total Runs:     {sched.get('total_runs', 0)}")
        print(f"    • Last Run:       {sched.get('last_run', 'Never')}")
        print(f"    • Errors:         {sched.get('errors', 0)}")
        
        print("""
═══════════════════════════════════════════════════════════════════════════════
""")
    
    def run_daemon(self):
        """Run as background daemon, collecting every 4 hours."""
        logger.info("Starting Alpha Scheduler daemon...")
        logger.info(f"Collection interval: {self.collection_interval_hours} hours")
        
        status = self._load_status()
        status["started_at"] = datetime.now(timezone.utc).isoformat()
        self._save_status(status)
        
        while True:
            try:
                # Run collection
                self.run_collection()
                
                # Print status
                self.print_status()
                
                # Sleep until next collection
                sleep_seconds = self.collection_interval_hours * 3600
                logger.info(f"Next collection in {self.collection_interval_hours} hours...")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                # Wait 5 minutes before retrying on error
                time.sleep(300)


# ============================================================================
# REPLIT SCHEDULED TASK HELPER
# ============================================================================

def create_replit_scheduled_task():
    """
    Create instructions for Replit scheduled task.
    """
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REPLIT SCHEDULED TASK SETUP                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

To set up automated collection in Replit:

1. Go to your Replit project
2. Click on "Tools" in the left sidebar
3. Select "Scheduled" (or search for it)
4. Create a new scheduled task with:

   NAME: Alpha Data Collection
   
   COMMAND: 
   export FRED_API_KEY="33a1a9e72f4023e2ba4e75a3986faf28" && python3 services/alpha_scheduler.py once
   
   SCHEDULE: Every 4 hours
   (or use cron: 0 */4 * * *)

5. Create another task for daily newsletter generation:

   NAME: Daily Newsletter Alpha
   
   COMMAND:
   export FRED_API_KEY="33a1a9e72f4023e2ba4e75a3986faf28" && python3 services/newsletter_alpha_integration.py premium
   
   SCHEDULE: Every day at 9:00 AM
   (or use cron: 0 9 * * *)

═══════════════════════════════════════════════════════════════════════════════

Alternatively, run the daemon manually:

   python3 services/alpha_scheduler.py daemon

This will run continuously, collecting data every 4 hours.

═══════════════════════════════════════════════════════════════════════════════
""")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    scheduler = AlphaScheduler()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "daemon":
            scheduler.run_daemon()
        elif cmd == "once":
            result = scheduler.run_collection()
            print(json.dumps(result, indent=2))
        elif cmd == "status":
            scheduler.print_status()
        elif cmd == "setup":
            create_replit_scheduled_task()
        else:
            print("Usage: python3 alpha_scheduler.py [daemon|once|status|setup]")
    else:
        # Default: run once
        scheduler.run_collection()
        scheduler.print_status()
