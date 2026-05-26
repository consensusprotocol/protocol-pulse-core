#!/usr/bin/env python3
"""
Scheduled Job for Replit Scheduled Deployments
This script is designed to be run by Replit's Scheduled Deployment feature.

To set up:
1. Go to Publishing > Scheduled
2. Set Run Command: python3 scheduled_job.py
3. Set Schedule: Every 15 minutes (or */15 * * * *)
4. Deploy
"""
import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting scheduled article generation...")
    
    try:
        from app import app
        from pp_services.automation import generate_article_with_tracking
        
        with app.app_context():
            result = generate_article_with_tracking()
            
            print(json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'result': result
            }, indent=2))
            
            if result.get('success'):
                print(f"SUCCESS: Generated article #{result.get('article_id')}: {result.get('title')}")
                return 0
            elif result.get('skipped'):
                print("SKIPPED: Another process is running")
                return 0
            else:
                print(f"FAILED: {result.get('error')}")
                return 1
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
