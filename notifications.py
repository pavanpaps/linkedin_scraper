"""
notifications.py - Telegram notification management
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
    """Manage Telegram notifications"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    @retry(max_attempts=3, delay=2)
    def send_message(self, message, parse_mode='HTML', disable_preview=False):
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
        Send individual job notification
        
        Args:
            job: Dictionary with job details
        
        Returns:
            True if successful
        """
        job_type_emoji = "🔹" if job.get('is_recommendation', False) else "⭐"
        job_type_text = "Recommended Job" if job.get('is_recommendation', False) else "Direct Match"
        
        message = f"""
🎯 <b>New Data Engineer Job!</b>

{job_type_emoji} <b>Type:</b> {job_type_text}
📄 <b>Page:</b> {job.get('page', 1)}

<b>Title:</b> {job['title']}
<b>Company:</b> {job['company']}
<b>Location:</b> {job['location']}

🔗 <b>Apply:</b> <a href="{job['url']}">Click here</a>

⏰ Found: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_message(message)
    
    def send_error_notification(self, error_msg):
        """Send error notification"""
        message = f"""
❌ <b>Scraper Error</b>

{error_msg}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        try:
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Could not send error notification: {e}")
            return False
    
    def send_health_check(self, stats):
        """
        Send health check notification
        
        Args:
            stats: Dictionary with scraper statistics
        """
        message = f"""
🏥 <b>Scraper Health Check</b>

Status: Running ✅
Jobs tracked: {stats.get('total_jobs', 0)}
Jobs today: {stats.get('jobs_today', 0)}
Total notifications: {stats.get('total_notifications', 0)}
Errors: {stats.get('errors', 0)}
Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
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
                return True
            else:
                logger.error(f"Telegram connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False