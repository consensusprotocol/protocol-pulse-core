#!/usr/bin/env python3
"""
Start Protocol Pulse automation system
"""
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from pp_services.scheduler import generate_scheduled_article, run_social_monitoring

def start_content_generation():
    """Start generating content immediately"""
    print("🚀 Starting Protocol Pulse automation...")
    
    # Generate first breaking news article
    print("📰 Generating breaking news article...")
    generate_scheduled_article()
    
    # Run social monitoring
    print("📱 Running social media monitoring...")
    run_social_monitoring()
    
    print("✅ Content generation completed successfully!")

if __name__ == '__main__':
    start_content_generation()