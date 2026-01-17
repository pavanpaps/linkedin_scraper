"""
pid_manager.py - Manage scraper PID for accurate status tracking
Add this to your linkedin_scraper.py
"""

import os
import atexit
import logging

logger = logging.getLogger(__name__)

PID_FILE = '.scraper.pid'


class PIDManager:
    """Manage PID file for scraper status tracking"""
    
    def __init__(self):
        self.pid_file = PID_FILE
        self.registered = False
    
    def create_pid_file(self):
        """Create PID file when scraper starts"""
        try:
            pid = os.getpid()
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))
            logger.info(f"Created PID file: {pid}")
            
            # Register cleanup on exit
            if not self.registered:
                atexit.register(self.remove_pid_file)
                self.registered = True
            
            return True
        except Exception as e:
            logger.warning(f"Could not create PID file: {e}")
            return False
    
    def remove_pid_file(self):
        """Remove PID file when scraper stops"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                logger.info("Removed PID file")
        except Exception as e:
            logger.warning(f"Could not remove PID file: {e}")
    
    def check_pid_file(self):
        """Check if PID file exists and is valid"""
        if not os.path.exists(self.pid_file):
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            import psutil
            try:
                psutil.Process(pid)
                return True
            except psutil.NoSuchProcess:
                # Stale PID file
                self.remove_pid_file()
                return False
        except:
            return False


# ===== HOW TO USE IN linkedin_scraper.py =====
# 
# Add this at the top of LinkedInScraper class __init__:
#
#     def __init__(self, config_file='config.json', headless=False, use_cookies=True):
#         # ... existing code ...
#         
#         # Add PID manager
#         from pid_manager import PIDManager
#         self.pid_manager = PIDManager()
#         self.pid_manager.create_pid_file()
#
# That's it! The PID file will be automatically created on start
# and removed on exit (even if Ctrl+C is pressed)