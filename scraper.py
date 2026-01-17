"""
scraper.py - Enhanced LinkedIn Job Scraper with database support
"""

import sys
import time
import random
import logging
from datetime import datetime, timedelta

# Import from your original modules
from database import JobDatabase
from reports import ReportGenerator

# Windows console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

logger = logging.getLogger(__name__)


class EnhancedJobScraper:
    """
    Enhanced wrapper that adds database and reporting functionality
    to your existing LinkedInJobScraper class
    """
    
    def __init__(self, base_scraper):
        """
        Initialize enhanced scraper
        
        Args:
            base_scraper: Instance of your original LinkedInJobScraper
        """
        self.scraper = base_scraper
        
        # Initialize database
        self.db = JobDatabase()
        
        # Initialize report generator
        self.report_generator = ReportGenerator(self.db)
        
        # Track report times
        self.last_periodic_report = datetime.now()
        self.periodic_report_interval = 6  # hours
        
        logger.info("Enhanced scraper initialized with database and reporting")
    
    def save_job_to_db(self, job_data):
        """
        Save job to database
        
        Args:
            job_data: Dictionary containing job information
        
        Returns:
            True if job is new, False if already exists
        """
        is_new = self.db.add_job(job_data)
        
        if is_new:
            self.scraper.seen_job_urls.add(job_data['url'])
        
        return is_new
    
    def process_page_jobs_enhanced(self, page_jobs, page_num):
        """
        Process jobs with database tracking and notifications
        
        Args:
            page_jobs: List of jobs found on the page
            page_num: Current page number
        
        Returns:
            Tuple of (new_jobs_count, notifications_sent)
        """
        new_jobs_count = 0
        notifications_sent = 0
        
        logger.info(f"Processing {len(page_jobs)} jobs from page {page_num}...")
        
        for job in page_jobs:
            # Apply filters
            if not self.scraper.should_notify_job(job):
                continue
            
            # Save to database
            is_new = self.save_job_to_db(job)
            
            if is_new:
                new_jobs_count += 1
                
                # Send notification
                success = self.scraper.send_telegram_notification(job)
                
                if success:
                    notifications_sent += 1
                    self.db.mark_notified(job['job_id'])
                    
                    company = job['company'] if job['company'] != 'Not specified' else ''
                    separator = ' - ' if company else ''
                    logger.info(f"  ✅ Notified: {job['title'][:40]}{separator}{company}")
                else:
                    logger.warning(f"  ❌ Failed to notify: {job['title'][:40]}")
                
                # Random delay between notifications
                time.sleep(random.uniform(1.5, 2.5))
        
        logger.info(f"Page {page_num}: {new_jobs_count} new jobs, {notifications_sent} notifications sent")
        
        return new_jobs_count, notifications_sent
    
    def scrape_with_tracking(self):
        """
        Run the scraper with database tracking
        
        Returns:
            Tuple of (jobs_list, run_stats)
        """
        # Start tracking this run
        run_id = self.db.start_scrape_run()
        
        run_stats = {
            'jobs_found': 0,
            'new_jobs': 0,
            'notifications_sent': 0,
            'errors': 0,
            'pages_scraped': 0,
            'duration': 0
        }
        
        all_jobs = []
        
        try:
            # Login if needed
            if not self.scraper.logged_in:
                if not self.scraper.linkedin_login():
                    logger.error("Cannot scrape without login")
                    self.db.complete_scrape_run(run_id, run_stats)
                    return [], run_stats
            
            page_num = 1
            
            # Scrape pages
            while True:
                logger.info(f"{'='*70}")
                logger.info(f"SCRAPING PAGE {page_num}")
                logger.info(f"{'='*70}")
                
                # Scrape the page using original scraper
                page_jobs, should_stop = self.scraper.scrape_page(page_num)
                
                all_jobs.extend(page_jobs)
                run_stats['pages_scraped'] = page_num
                run_stats['jobs_found'] += len(page_jobs)
                
                # Process jobs from this page with enhanced tracking
                new_count, notif_count = self.process_page_jobs_enhanced(page_jobs, page_num)
                run_stats['new_jobs'] += new_count
                run_stats['notifications_sent'] += notif_count
                
                # Check if we should stop
                if should_stop:
                    logger.info(f"Stopping pagination after page {page_num}")
                    break
                
                # Move to next page
                logger.info(f"Moving to page {page_num + 1} in 3-5 seconds...")
                time.sleep(random.uniform(3, 5))
                page_num += 1
            
            logger.info(f"{'='*70}")
            logger.info(f"TOTAL: {len(all_jobs)} jobs across {page_num} page(s)")
            logger.info(f"{'='*70}")
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            run_stats['errors'] += 1
            self.scraper.send_error_notification(f"Scraping error: {str(e)}")
        
        # Complete the run
        self.db.complete_scrape_run(run_id, run_stats)
        
        return all_jobs, run_stats
    
    def send_run_report(self, run_stats, jobs_data):
        """Send per-run report to Telegram"""
        try:
            report = self.report_generator.generate_run_report(run_stats, jobs_data)
            self.scraper.send_telegram_message(report, parse_mode='HTML')
            logger.info("✅ Run report sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send run report: {e}")
    
    def check_and_send_periodic_report(self):
        """Check if periodic report is due and send it"""
        hours_since_last = (datetime.now() - self.last_periodic_report).total_seconds() / 3600
        
        if hours_since_last >= self.periodic_report_interval:
            logger.info(f"Generating {self.periodic_report_interval}-hour periodic report...")
            
            report = self.report_generator.generate_periodic_report(self.periodic_report_interval)
            
            if report:
                try:
                    self.scraper.send_telegram_message(report, parse_mode='HTML')
                    logger.info("✅ Periodic report sent to Telegram")
                    
                    # Record in database
                    period_start = (datetime.now() - timedelta(hours=self.periodic_report_interval)).isoformat()
                    period_end = datetime.now().isoformat()
                    self.db.record_report_sent('periodic', period_start, period_end, 0)
                    
                except Exception as e:
                    logger.error(f"Failed to send periodic report: {e}")
            else:
                logger.info("No activity in period - skipping periodic report")
            
            self.last_periodic_report = datetime.now()
    
    def send_daily_summary_if_due(self):
        """Send daily summary at 9 AM"""
        now = datetime.now()
        
        # Check if it's around 9 AM (within the check interval)
        if now.hour == 9 and now.minute < 30:
            logger.info("Generating daily summary report...")
            
            try:
                report = self.report_generator.generate_daily_summary()
                self.scraper.send_telegram_message(report, parse_mode='HTML')
                logger.info("✅ Daily summary sent to Telegram")
                
                # Record in database
                period_start = (datetime.now() - timedelta(hours=24)).isoformat()
                period_end = datetime.now().isoformat()
                self.db.record_report_sent('daily', period_start, period_end, 0)
                
            except Exception as e:
                logger.error(f"Failed to send daily summary: {e}")
    
    def run(self, interval_minutes=30):
        """
        Main enhanced run loop
        
        Args:
            interval_minutes: Minutes between scrape runs
        """
        logger.info("=" * 70)
        logger.info("Enhanced LinkedIn Job Scraper Started")
        logger.info("=" * 70)
        logger.info(f"Database: {self.db.db_file}")
        logger.info(f"Check interval: Every {interval_minutes} minutes")
        logger.info(f"Periodic reports: Every {self.periodic_report_interval} hours")
        logger.info(f"Daily summary: 9:00 AM")
        logger.info("=" * 70)
        
        try:
            while True:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"\n[{timestamp}] Starting job search...")
                logger.info("-" * 70)
                
                try:
                    # Run scraper with tracking
                    current_jobs, run_stats = self.scrape_with_tracking()
                    
                    # Send run report
                    if current_jobs:
                        self.send_run_report(run_stats, current_jobs)
                    
                    # Check if periodic report is due
                    self.check_and_send_periodic_report()
                    
                    # Check if daily summary is due
                    self.send_daily_summary_if_due()
                    
                    # Save data (from original scraper)
                    self.scraper.save_tracked_jobs()
                    self.scraper.save_stats()
                    
                except Exception as e:
                    logger.error(f"Error during scraping: {e}")
                    self.scraper.send_error_notification(f"Scraping error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                logger.info(f"\nNext check in {interval_minutes} minutes...")
                logger.info(f"Press Ctrl+C to stop")
                logger.info("-" * 70)
                
                # Sleep with interrupt checking
                for _ in range(interval_minutes * 60):
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n\nKeyboard interrupt received - stopping scraper...")
            self.cleanup_and_exit()
        except Exception as e:
            logger.error(f"\nFatal error: {e}")
            self.scraper.send_error_notification(f"Fatal error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.cleanup_and_exit()
    
    def cleanup_and_exit(self):
        """Cleanup and exit gracefully"""
        logger.info("Saving data...")
        self.scraper.save_tracked_jobs()
        self.scraper.save_stats()
        
        logger.info("Closing database...")
        self.db.close()
        
        logger.info("Closing browser...")
        self.scraper.close_driver()
        
        logger.info("Shutdown complete. Goodbye!")
        sys.exit(0)