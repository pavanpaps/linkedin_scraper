"""
config.py - Configuration management for LinkedIn Job Scraper
UPDATED: Support for multiple search URLs
"""

import json
import os
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the scraper"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.search_urls = self.parse_search_urls()
    
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
                'search_urls': [],
                'filters': {}
            }
    
    def parse_search_urls(self):
        """
        Parse search URLs from config
        Supports:
        - Direct URLs list
        - Legacy job_config format (converted to URL)
        """
        urls = []
        
        # Method 1: Direct URLs (new way - RECOMMENDED)
        if 'search_urls' in self.config and self.config['search_urls']:
            urls = self.config['search_urls']
            logger.info(f"Loaded {len(urls)} search URLs from config")
            return urls
        
        # Method 2: Legacy job_config (backward compatibility)
        if 'job_config' in self.config:
            legacy_url = self.build_url_from_legacy_config()
            urls = [legacy_url]
            logger.info("Converted legacy job_config to search URL")
            return urls
        
        # Fallback: Default search
        default_url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Engineer&geoId=105214831&f_TPR=r86400&f_E=2"
        logger.warning("No search URLs found, using default")
        return [default_url]
    
    def build_url_from_legacy_config(self):
        """Build URL from old job_config format"""
        job_config = self.config.get('job_config', {})
        
        job_title = job_config.get('job_title', 'Data Engineer')
        experience_level = job_config.get('experience_level', '')
        location_id = job_config.get('location_id', '105214831')
        time_filter = job_config.get('time_filter', 'r86400')
        experience_filter = job_config.get('experience_filter', '2')
        
        keywords = f"{job_title} {experience_level}".strip()
        keywords_encoded = keywords.replace(' ', '%20')
        
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords_encoded}"
            f"&geoId={location_id}"
            f"&f_TPR={time_filter}"
            f"&f_E={experience_filter}"
        )
        
        return url
    
    def get_search_urls(self):
        """Get all search URLs to scrape"""
        return self.search_urls
    
    def add_pagination_to_url(self, base_url, page_num):
        """
        Add pagination to any LinkedIn URL
        Works with both old and new URL formats
        """
        separator = '&' if '?' in base_url else '?'
        
        # Remove existing start parameter if present
        if 'start=' in base_url:
            parts = base_url.split('&')
            parts = [p for p in parts if not p.startswith('start=')]
            base_url = '&'.join(parts)
        
        # Calculate start position (25 jobs per page)
        start = (page_num - 1) * 25
        
        return f"{base_url}{separator}start={start}"
    
    def get_url_description(self, url):
        """
        Extract human-readable description from LinkedIn URL
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            keywords = params.get('keywords', ['Unknown'])[0]
            location = params.get('location', [''])[0]
            
            desc = f"{keywords}"
            if location:
                desc += f" in {location}"
            
            return desc
        except:
            return "LinkedIn Job Search"
    
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
    
    def get_filters(self):
        """Get job filters"""
        return self.config.get('filters', {})
    
    def should_process_recommendations(self):
        """Check if should process recommendation jobs"""
        return self.config.get('process_recommendations', True)