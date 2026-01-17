"""
main.py - Main entry point for LinkedIn Job Scraper
Simple and clean - all logic is in modules
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Windows console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Import the main scraper
from linkedin_scraper import LinkedInScraper


def print_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        LinkedIn Job Scraper - Modular Edition                ║
║        With Database Storage & Smart Reporting               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Main function"""
    
    # Print banner
    print_banner()
    
    # Check if config exists
    if not os.path.exists('config.json'):
        logger.error("config.json not found!")
        logger.error("Please create config.json with your credentials")
        logger.error("See config.json.sample for template")
        sys.exit(1)
    
    # Settings
    CHECK_INTERVAL = 10  # minutes
    HEADLESS_MODE = False  # Set to True to hide browser
    USE_COOKIES = True  # Set to False to disable cookie reuse
    
    print("\n⚙️  Scraper Settings:")
    print("=" * 60)
    print(f"  Check Interval: {CHECK_INTERVAL} minutes")
    print(f"  Headless Mode: {HEADLESS_MODE}")
    print(f"  Use Cookies: {USE_COOKIES}")
    print(f"  Database: jobs.db (SQLite)")
    print(f"  Periodic Reports: Every 6 hours")
    print("=" * 60)
    
    print("\n🚀 Starting scraper...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Initialize scraper
        scraper = LinkedInScraper(
            config_file='config.json',
            headless=HEADLESS_MODE,
            use_cookies=USE_COOKIES
        )
        
        # Run the scraper
        scraper.run(interval_minutes=CHECK_INTERVAL)
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()