#!/usr/bin/env python3
"""
Automation Worker - Entry point for Replit workflow
Runs article generation with locking and logging
Designed to be called by Replit workflow every 15 minutes
"""
import sys
import json
from datetime import datetime

# Add current directory to path
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from pp_services.automation import generate_article_with_tracking

def main():
    """Main entry point for automation worker"""
    print(json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'event': 'automation_start',
        'task': 'article_generation'
    }))
    
    with app.app_context():
        result = generate_article_with_tracking()
        
        print(json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'automation_complete',
            'result': result
        }))
        
        # Exit with appropriate code
        if result.get('success'):
            sys.exit(0)
        elif result.get('skipped'):
            sys.exit(0)  # Skipped is not an error
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
