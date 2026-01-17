"""
job_filters.py - Job filtering and validation logic
"""

import logging

logger = logging.getLogger(__name__)


class JobFilter:
    """Filter jobs based on criteria"""
    
    def __init__(self, filters_config):
        """
        Initialize job filter
        
        Args:
            filters_config: Dictionary with filter configuration
        """
        self.exclude_keywords = [kw.lower() for kw in filters_config.get('exclude_keywords', [])]
        self.include_keywords = [kw.lower() for kw in filters_config.get('include_keywords', [])]
        self.exclude_companies = [comp.lower() for comp in filters_config.get('exclude_companies', [])]
    
    def should_notify(self, job):
        """
        Check if job matches filters and should be notified
        
        Args:
            job: Dictionary with job details
        
        Returns:
            True if job should be notified, False otherwise
        """
        title_lower = job['title'].lower()
        company_lower = job['company'].lower()
        
        # Check exclude keywords
        if self.exclude_keywords:
            for keyword in self.exclude_keywords:
                if keyword in title_lower:
                    logger.info(f"Filtered out (exclude keyword '{keyword}'): {job['title']}")
                    return False
        
        # Check exclude companies
        if self.exclude_companies:
            for company in self.exclude_companies:
                if company in company_lower:
                    logger.info(f"Filtered out (exclude company '{company}'): {job['company']}")
                    return False
        
        # Check include keywords (if specified)
        if self.include_keywords:
            has_include_keyword = any(kw in title_lower for kw in self.include_keywords)
            if not has_include_keyword:
                logger.info(f"Filtered out (missing include keyword): {job['title']}")
                return False
        
        return True
    
    def get_filter_summary(self):
        """Get summary of active filters"""
        summary = []
        
        if self.exclude_keywords:
            summary.append(f"Exclude keywords: {', '.join(self.exclude_keywords)}")
        
        if self.include_keywords:
            summary.append(f"Include keywords: {', '.join(self.include_keywords)}")
        
        if self.exclude_companies:
            summary.append(f"Exclude companies: {', '.join(self.exclude_companies)}")
        
        return summary if summary else ["No filters active"]