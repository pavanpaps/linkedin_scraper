"""
notifications.py - Professional Telegram notification management
Production-ready design with clean formatting
"""

import requests
import logging
from datetime import datetime
from functools import wraps
import time

logger = logging.getLogger(__name__)


def retry(max_attempts=3, delay=2):
    """Retry decorator for handling transient failures"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    logger.warning(f"{func.__name__} attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


class TelegramNotifier:
    """Manage Telegram notifications with professional formatting"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    @retry(max_attempts=3, delay=2)
    def send_message(self, message, parse_mode='HTML', disable_preview=True):
        """
        Send message to Telegram
        
        Args:
            message: Message text
            parse_mode: 'HTML' or 'Markdown'
            disable_preview: Disable link preview
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_preview
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def send_job_notification(self, job):
        """
        Send professional job notification
        
        Args:
            job: Dictionary with job details
        
        Returns:
            True if successful
        """
        # Determine job type
        is_recommendation = job.get('is_recommendation', False)
        type_badge = "💡 RECOMMENDED" if is_recommendation else "🎯 DIRECT MATCH"
        
        # Format location
        location = job.get('location', 'Location not specified')
        if len(location) > 50:
            location = location[:47] + "..."
        
        # Format company
        company = job.get('company', 'Not specified')
        if company == 'Not specified':
            company = "Company not listed"
        
        # Build clean, professional message
        message = f"""<b>{job['title']}</b>

📍 {location}
🏢 {company}

{type_badge}

<a href="{job['url']}">→ View Job Details</a>

<i>Posted {self._format_time_ago()}</i>"""
        
        return self.send_message(message, disable_preview=True)
    
    def send_batch_notification(self, jobs, stats):
        """
        Send batch notification for multiple new jobs
        
        Args:
            jobs: List of job dictionaries
            stats: Run statistics
        """
        if not jobs:
            return False
        
        count = len(jobs)
        direct_matches = sum(1 for j in jobs if not j.get('is_recommendation', False))
        recommendations = count - direct_matches
        
        # Build header
        message = f"""<b>🔔 {count} New Job{'s' if count > 1 else ''} Found</b>

"""
        
        # Add stats
        if direct_matches > 0:
            message += f"🎯 Direct Matches: {direct_matches}\n"
        if recommendations > 0:
            message += f"💡 Recommendations: {recommendations}\n"
        
        message += "\n"
        
        # Add top jobs (max 5)
        message += "<b>Latest Opportunities:</b>\n\n"
        for i, job in enumerate(jobs[:5], 1):
            title = job['title']
            if len(title) > 45:
                title = title[:42] + "..."
            
            company = job.get('company', 'Not specified')
            if company == 'Not specified':
                company = "Company not listed"
            if len(company) > 30:
                company = company[:27] + "..."
            
            message += f"{i}. <b>{title}</b>\n"
            message += f"   🏢 {company}\n\n"
        
        if count > 5:
            message += f"<i>...and {count - 5} more</i>\n\n"
        
        message += f"<i>Scraped at {datetime.now().strftime('%H:%M, %b %d')}</i>"
        
        return self.send_message(message)
    
    def send_error_notification(self, error_msg):
        """Send clean error notification"""
        message = f"""<b>⚠️ Scraper Alert</b>

An error occurred:

<code>{error_msg}</code>

<i>{datetime.now().strftime('%H:%M, %b %d, %Y')}</i>"""
        
        try:
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Could not send error notification: {e}")
            return False
    
    def send_daily_summary(self, stats):
        """
        Send clean daily summary
        
        Args:
            stats: Dictionary with daily statistics
        """
        message = f"""<b>📊 Daily Summary</b>

<b>Jobs Discovered:</b> {stats.get('jobs_found', 0)}
<b>New Opportunities:</b> {stats.get('new_jobs', 0)}
<b>Notifications Sent:</b> {stats.get('notifications_sent', 0)}

<b>Top Companies:</b>
"""
        
        # Add top companies
        top_companies = stats.get('top_companies', [])
        for i, (company, count) in enumerate(top_companies[:5], 1):
            message += f"{i}. {company} ({count})\n"
        
        message += f"\n<i>{datetime.now().strftime('%B %d, %Y')}</i>"
        
        return self.send_message(message)
    
    def send_run_summary(self, stats):
        """
        Send concise run summary (only if significant activity)
        
        Args:
            stats: Dictionary with run statistics
        """
        # Only send if there are new jobs or it's been a while
        if stats.get('new_jobs', 0) == 0:
            return False
        
        duration = self._format_duration(stats.get('duration', 0))
        
        message = f"""<b>✅ Scrape Complete</b>

Found: {stats.get('jobs_found', 0)} jobs
New: {stats.get('new_jobs', 0)} opportunities
Pages: {stats.get('pages_scraped', 0)}
Time: {duration}

<i>{datetime.now().strftime('%H:%M')}</i>"""
        
        return self.send_message(message)
    
    def send_health_check(self, stats):
        """
        Send system health check notification
        
        Args:
            stats: Dictionary with scraper statistics
        """
        message = f"""<b>💚 System Status</b>

<b>Status:</b> Running
<b>Total Jobs:</b> {stats.get('total_jobs', 0)}
<b>Today:</b> {stats.get('jobs_today', 0)} new jobs
<b>Notifications:</b> {stats.get('total_notifications', 0)}

<i>Last check: {datetime.now().strftime('%H:%M')}</i>"""
        
        try:
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Could not send health check: {e}")
            return False
    
    def test_connection(self):
        """Test Telegram connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"Telegram bot connected: {bot_info['result']['first_name']}")
                
                # Send test message
                test_msg = f"""<b>✅ Bot Connected</b>

LinkedIn Job Scraper is ready.

<i>{datetime.now().strftime('%H:%M, %b %d, %Y')}</i>"""
                self.send_message(test_msg)
                return True
            else:
                logger.error(f"Telegram connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False
    
    def _format_time_ago(self):
        """Format current time as 'just now' or time"""
        return datetime.now().strftime('%H:%M today')
    
    def _format_duration(self, seconds):
        """Format duration in human readable form"""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = int(minutes / 60)
        mins = minutes % 60
        return f"{hours}h {mins}m"