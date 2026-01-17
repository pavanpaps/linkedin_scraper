"""
config.py - Configuration management for LinkedIn Job Scraper
"""

import json
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the scraper"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file or environment variables"""
        if os.path.exists(self.config_file):
            logger.info(f"Loading configuration from {self.config_file}")
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            logger.info("Loading configuration from environment variables")
            return {
                'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
                'linkedin_email': os.getenv('LINKEDIN_EMAIL'),
                'linkedin_password': os.getenv('LINKEDIN_PASSWORD'),
                'process_recommendations': os.getenv('PROCESS_RECOMMENDATIONS', 'true').lower() == 'true',
                'job_config': {},
                'filters': {}
            }
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def get_telegram_config(self):
        """Get Telegram configuration"""
        return {
            'bot_token': self.config['telegram_bot_token'],
            'chat_id': self.config['telegram_chat_id']
        }
    
    def get_linkedin_credentials(self):
        """Get LinkedIn credentials"""
        return {
            'email': self.config['linkedin_email'],
            'password': self.config['linkedin_password']
        }
    
    def get_job_config(self):
        """Get job search configuration"""
        return self.config.get('job_config', {})
    
    def get_filters(self):
        """Get job filters"""
        return self.config.get('filters', {})
    
    def should_process_recommendations(self):
        """Check if should process recommendation jobs"""
        return self.config.get('process_recommendations', True)
    
    def build_search_url(self, page_num=1):
        """Build LinkedIn search URL based on configuration"""
        job_config = self.get_job_config()
        
        job_title = job_config.get('job_title', 'Data Engineer')
        experience_level = job_config.get('experience_level', 'entry level junior 2 years experience')
        location_id = job_config.get('location_id', '105214831')
        time_filter = job_config.get('time_filter', 'r86400')
        experience_filter = job_config.get('experience_filter', '2')
        
        keywords = f"{job_title} {experience_level}".strip()
        keywords_encoded = keywords.replace(' ', '%20')
        start = (page_num - 1) * 25
        
        url = (
            f"https://www.linkedin.com/jobs/search-results/"
            f"?keywords={keywords_encoded}"
            f"&origin=SEMANTIC_SEARCH_HISTORY"
            f"&geoId={location_id}"
            f"&f_TPR={time_filter}"
            f"&f_E={experience_filter}"
            f"&start={start}"
        )
        
        return url