"""
storage.py - Data storage and persistence
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class JobStorage:
    """Manage job data storage (JSON files)"""
    
    def __init__(self, jobs_file='tracked_jobs.json', stats_file='stats.json'):
        self.jobs_file = jobs_file
        self.stats_file = stats_file
        self.seen_job_urls = self.load_tracked_jobs()
        self.stats = self.load_stats()
    
    def load_tracked_jobs(self):
        """Load previously seen job URLs from file"""
        try:
            if os.path.exists(self.jobs_file):
                with open(self.jobs_file, 'r') as f:
                    data = json.load(f)
                    job_urls = set(data.get('job_urls', []))
                    logger.info(f"Loaded {len(job_urls)} tracked jobs from {self.jobs_file}")
                    return job_urls
        except Exception as e:
            logger.warning(f"Could not load tracked jobs: {e}")
        return set()
    
    def save_tracked_jobs(self):
        """Save seen job URLs to file"""
        try:
            with open(self.jobs_file, 'w') as f:
                json.dump({
                    'job_urls': list(self.seen_job_urls),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
            logger.debug(f"Saved {len(self.seen_job_urls)} tracked job URLs")
        except Exception as e:
            logger.error(f"Could not save tracked jobs: {e}")
    
    def add_job_url(self, url):
        """Add job URL to tracked set"""
        self.seen_job_urls.add(url)
    
    def is_job_seen(self, url):
        """Check if job URL has been seen before"""
        return url in self.seen_job_urls
    
    def load_stats(self):
        """Load statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                    logger.debug(f"Loaded stats from {self.stats_file}")
                    return stats
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")
        
        return {
            'total_jobs_seen': 0,
            'total_notifications_sent': 0,
            'jobs_by_company': {},
            'jobs_by_date': {},
            'last_run': None,
            'errors_count': 0
        }
    
    def save_stats(self):
        """Save statistics to file"""
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            logger.debug(f"Stats saved to {self.stats_file}")
        except Exception as e:
            logger.error(f"Could not save stats: {e}")
    
    def update_stats(self, job):
        """Update statistics with new job data"""
        today = datetime.now().date().isoformat()
        
        self.stats['total_jobs_seen'] += 1
        
        # Track by company
        company = job.get('company', 'Unknown')
        self.stats['jobs_by_company'][company] = self.stats['jobs_by_company'].get(company, 0) + 1
        
        # Track by date
        self.stats['jobs_by_date'][today] = self.stats['jobs_by_date'].get(today, 0) + 1
        
        self.stats['last_run'] = datetime.now().isoformat()
    
    def increment_notifications(self):
        """Increment notification counter"""
        self.stats['total_notifications_sent'] += 1
    
    def increment_errors(self):
        """Increment error counter"""
        self.stats['errors_count'] += 1
    
    def get_stats_summary(self):
        """Get statistics summary"""
        today = datetime.now().date().isoformat()
        
        return {
            'total_jobs': len(self.seen_job_urls),
            'jobs_today': self.stats['jobs_by_date'].get(today, 0),
            'total_notifications': self.stats['total_notifications_sent'],
            'errors': self.stats['errors_count']
        }