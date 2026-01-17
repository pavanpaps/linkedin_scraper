"""
linkedin_scraper.py - Core LinkedIn scraping logic
This is the main scraper that combines all modules
FIXED VERSION - Properly waits for job details panel to update
"""

import time
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re

# Import our modules
from config import Config
from web_driver import WebDriverManager
from job_extractor import JobExtractor
from notifications import TelegramNotifier
from job_filters import JobFilter
from storage import JobStorage
from database import JobDatabase
from reports import ReportGenerator

logger = logging.getLogger(__name__)


def random_delay(min_sec=2, max_sec=5):
    """Random delay to avoid detection"""
    time.sleep(random.uniform(min_sec, max_sec))


class LinkedInScraper:
    """Main LinkedIn job scraper"""
    
    def __init__(self, config_file='config.json', headless=False, use_cookies=True):
        # Load configuration
        self.config = Config(config_file)
        
        # Initialize components
        self.web_driver = WebDriverManager(headless=headless, use_cookies=use_cookies)
        self.job_extractor = JobExtractor(
            default_location=self.config.get_job_config().get('location', 'Bengaluru, Karnataka, India')
        )
        
        telegram_config = self.config.get_telegram_config()
        self.notifier = TelegramNotifier(
            bot_token=telegram_config['bot_token'],
            chat_id=telegram_config['chat_id']
        )
        
        self.job_filter = JobFilter(self.config.get_filters())
        self.storage = JobStorage()
        
        # Initialize database (enhanced feature)
        self.db = JobDatabase()
        self.report_generator = ReportGenerator(self.db)
        
        # Settings
        self.process_recommendations = self.config.should_process_recommendations()
        
        # CSS selectors for job cards
        self.job_card_selectors = [
            "li.scaffold-layout__list-item",
            "li.jobs-search-results__list-item",
            "div.job-card-container",
        ]
        
        # Periodic report tracking
        self.last_periodic_report = datetime.now()
        self.periodic_report_interval = 6  # hours
        
        logger.info("LinkedIn Scraper initialized")
        logger.info(f"Filters: {self.job_filter.get_filter_summary()}")
    
    def login(self):
        """Login to LinkedIn"""
        credentials = self.config.get_linkedin_credentials()
        return self.web_driver.login(
            email=credentials['email'],
            password=credentials['password'],
            error_callback=self.notifier.send_error_notification
        )
    
    def check_no_jobs_page(self, html_source):
        """Check if current page shows 'No matching jobs found'"""
        try:
            soup = BeautifulSoup(html_source, 'html.parser')
            
            no_jobs_indicators = [
                soup.find('h1', string=re.compile(r'No matching jobs found', re.IGNORECASE)),
                soup.find('div', string=re.compile(r'No matching jobs found', re.IGNORECASE)),
                soup.find(string=re.compile(r'Try removing filters or rephrasing your search', re.IGNORECASE))
            ]
            
            return any(no_jobs_indicators)
        except:
            return False
    
    def find_job_elements(self):
        """Find job card elements on the page"""
        for selector in self.job_card_selectors:
            try:
                elements = self.web_driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} job elements with: {selector}")
                    return elements
                else:
                    logger.debug(f"No elements with: {selector}")
            except Exception as e:
                logger.debug(f"Error with {selector}: {e}")
        return []
    
    def is_recommendation_divider(self, element_text):
        """Check if element is the recommendations divider"""
        return ("We've found more results" in element_text or 
                "share similar criteria" in element_text)
    
    def scrape_page(self, page_num):
        """
        Scrape a single page of job listings
        
        Returns:
            Tuple of (jobs_list, should_stop)
        """
        url = self.config.build_search_url(page_num)
        
        logger.info(f"{'='*70}")
        logger.info(f"SCRAPING PAGE {page_num}")
        logger.info(f"{'='*70}")
        
        try:
            logger.info(f"Navigating to page {page_num}...")
            self.web_driver.navigate_to(url)
            
            logger.info("Waiting for jobs to load...")
            time.sleep(8)
            
            html_source = self.web_driver.get_page_source()
            
            # Check if this is a "no jobs found" page
            if self.check_no_jobs_page(html_source):
                logger.info(f"No matching jobs found on page {page_num}")
                return [], True
            
            # Scroll to load all jobs
            logger.info("Scrolling to load all jobs...")
            for i in range(5):
                self.web_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                random_delay(1.5, 2.5)
            
            # Take screenshot for first page only
            if page_num == 1:
                self.web_driver.save_screenshot('linkedin_debug.png')
            
            # Find job elements
            logger.info("Searching for job card elements...")
            job_elements = self.find_job_elements()
            
            if not job_elements:
                logger.warning(f"No job elements found on page {page_num}")
                return [], True
            
            logger.info(f"Processing {len(job_elements)} jobs on page {page_num}...")
            
            page_jobs = []
            found_divider = False
            last_extracted_job_id = None  # Track to avoid duplicates
            
            for idx, job_element in enumerate(job_elements):
                try:
                    # Check for recommendation divider
                    is_recommendation = False
                    try:
                        element_text = job_element.text
                        if self.is_recommendation_divider(element_text):
                            found_divider = True
                            if not self.process_recommendations:
                                logger.info(f"Found 'more results' divider at position {idx+1}")
                                logger.info("Stopping - not processing recommendations")
                                break
                            else:
                                logger.info("Found 'more results' divider - continuing with recommendations...")
                                is_recommendation = True
                                continue
                        
                        if found_divider:
                            is_recommendation = True
                    except:
                        pass
                    
                    # Scroll job card into view
                    self.web_driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_element)
                    random_delay(0.3, 0.6)
                    
                    # Click the job card
                    try:
                        job_element.click()
                        random_delay(0.5, 0.8)
                    except:
                        try:
                            link = job_element.find_element(By.CSS_SELECTOR, "a")
                            link.click()
                            random_delay(0.5, 0.8)
                        except:
                            logger.debug(f"[{idx+1}] Could not click")
                            continue
                    
                    # Get job ID from URL
                    current_url = self.web_driver.driver.current_url
                    job_id = self.job_extractor.extract_job_id_from_url(current_url)
                    
                    if not job_id:
                        logger.debug(f"[{idx+1}] No job ID in URL")
                        continue
                    
                    # Skip if this is the same as the last job (panel didn't update)
                    if job_id == last_extracted_job_id:
                        logger.debug(f"[{idx+1}] Duplicate job ID {job_id} - skipping")
                        random_delay(0.5, 1.0)
                        continue
                    
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                    
                    # Wait for the correct job details to load
                    try:
                        # Wait for details panel to exist
                        WebDriverWait(self.web_driver.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.jobs-details, section.jobs-details__main-content"))
                        )
                        
                        # CRITICAL: Wait for URL to confirm it's the right job
                        panel_loaded = False
                        for retry in range(10):
                            time.sleep(0.3)
                            check_url = self.web_driver.driver.current_url
                            check_job_id = self.job_extractor.extract_job_id_from_url(check_url)
                            
                            if check_job_id == job_id:
                                panel_loaded = True
                                break
                        
                        if not panel_loaded:
                            logger.debug(f"[{idx+1}] Panel didn't load for job {job_id}")
                            continue
                        
                        # Extra delay for DOM stability
                        random_delay(0.3, 0.5)
                        
                        html_source = self.web_driver.get_page_source()
                        
                        # Extract from details panel
                        job_details = self.job_extractor.extract_from_details_panel(
                            html_source, 
                            debug=(idx < 3)
                        )
                        
                        # Verify we didn't get duplicate data
                        if len(page_jobs) > 0:
                            last_job = page_jobs[-1]
                            if (job_details['title'] == last_job['title'] and 
                                job_details['company'] == last_job['company'] and
                                job_id != last_job['job_id']):
                                logger.debug(f"[{idx+1}] Duplicate data detected - skipping")
                                continue
                        
                        # Debug if company not found
                        if job_details['company'] == 'Not specified' and idx < 3:
                            logger.warning(f"Company not found for job {job_id}")
                            self.job_extractor.debug_company_extraction(html_source, job_id)
                        
                        if not job_details['title'] or len(job_details['title']) < 5:
                            logger.debug(f"[{idx+1}] No valid title")
                            continue
                        
                        # Display
                        job_type = "[RECOMMENDATION]" if is_recommendation else "[DIRECT MATCH]"
                        company_display = f" at {job_details['company']}" if job_details['company'] != 'Not specified' else ""
                        logger.info(f"[{len(page_jobs)+1}] Found: {job_details['title'][:45]}{company_display}")
                        logger.info(f"     {job_type} | Job ID: {job_id}")
                        
                        # Store
                        job_data = {
                            'url': job_url,
                            'title': job_details['title'],
                            'company': job_details['company'],
                            'location': job_details['location'],
                            'job_id': job_id,
                            'is_recommendation': is_recommendation,
                            'page': page_num,
                            'scraped_at': datetime.now().isoformat()
                        }
                        
                        # Add metadata if available
                        if 'work_type' in job_details:
                            job_data['work_type'] = job_details['work_type']
                        if 'insight' in job_details:
                            job_data['insight'] = job_details['insight']
                        
                        page_jobs.append(job_data)
                        last_extracted_job_id = job_id  # Remember this job
                        
                    except TimeoutException:
                        logger.debug(f"[{idx+1}] Details panel timeout")
                        continue
                    
                except Exception as e:
                    logger.debug(f"[{idx+1}] Error: {e}")
                    continue
            
            logger.info(f"Page {page_num}: Processed {len(page_jobs)} jobs")
            
            # Return jobs and whether to continue
            should_continue = len(page_jobs) > 0
            return page_jobs, not should_continue
            
        except Exception as e:
            logger.error(f"Error on page {page_num}: {e}")
            self.storage.increment_errors()
            return [], True
    
    def process_and_notify_jobs(self, page_jobs, page_num):
        """
        Process jobs: filter, save to DB, and notify
        
        Returns:
            Tuple of (new_jobs_count, notifications_sent)
        """
        new_jobs_count = 0
        notifications_sent = 0
        
        for job in page_jobs:
            # Apply filters
            if not self.job_filter.should_notify(job):
                continue
            
            # Save to database
            is_new = self.db.add_job(job)
            
            if is_new and not self.storage.is_job_seen(job['url']):
                new_jobs_count += 1
                
                # Send notification
                success = self.notifier.send_job_notification(job)
                
                if success:
                    notifications_sent += 1
                    self.storage.add_job_url(job['url'])
                    self.storage.update_stats(job)
                    self.storage.increment_notifications()
                    self.db.mark_notified(job['job_id'])
                    
                    company = job['company'] if job['company'] != 'Not specified' else ''
                    logger.info(f"  ✅ Notified: {job['title'][:40]} - {company}")
                else:
                    logger.warning(f"  ❌ Failed to notify: {job['title'][:40]}")
                
                random_delay(1.5, 2.5)
        
        return new_jobs_count, notifications_sent
    
    def scrape_all_pages(self):
        """
        Scrape all pages until no more jobs found
        
        Returns:
            Tuple of (all_jobs, run_stats)
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
        page_num = 1
        
        while True:
            page_jobs, should_stop = self.scrape_page(page_num)
            all_jobs.extend(page_jobs)
            run_stats['pages_scraped'] = page_num
            run_stats['jobs_found'] += len(page_jobs)
            
            # Process and notify jobs from this page
            new_count, notif_count = self.process_and_notify_jobs(page_jobs, page_num)
            run_stats['new_jobs'] += new_count
            run_stats['notifications_sent'] += notif_count
            
            # Check if we should stop
            if should_stop:
                logger.info(f"Stopping pagination after page {page_num}")
                break
            
            # Move to next page
            logger.info(f"Moving to page {page_num + 1} in 3-5 seconds...")
            random_delay(3, 5)
            page_num += 1
        
        # Complete the run
        self.db.complete_scrape_run(run_id, run_stats)
        
        logger.info(f"{'='*70}")
        logger.info(f"TOTAL: {len(all_jobs)} jobs across {page_num} page(s)")
        logger.info(f"{'='*70}")
        
        return all_jobs, run_stats
    
    def send_reports(self, run_stats, jobs_data):
        """Send reports after scraping"""
        # Send run report
        if jobs_data:
            try:
                report = self.report_generator.generate_run_report(run_stats, jobs_data)
                self.notifier.send_message(report, parse_mode='HTML')
                logger.info("✅ Run report sent")
            except Exception as e:
                logger.error(f"Failed to send run report: {e}")
        
        # Check if periodic report is due
        hours_since_last = (datetime.now() - self.last_periodic_report).total_seconds() / 3600
        
        if hours_since_last >= self.periodic_report_interval:
            try:
                report = self.report_generator.generate_periodic_report(self.periodic_report_interval)
                if report:
                    self.notifier.send_message(report, parse_mode='HTML')
                    logger.info("✅ Periodic report sent")
                    self.last_periodic_report = datetime.now()
            except Exception as e:
                logger.error(f"Failed to send periodic report: {e}")
    
    def run(self, interval_minutes=30):
        """
        Main run loop
        
        Args:
            interval_minutes: Minutes between scrape runs
        """
        logger.info("=" * 70)
        logger.info("LinkedIn Job Scraper Started")
        logger.info("=" * 70)
        logger.info(f"Check interval: Every {interval_minutes} minutes")
        logger.info(f"Process recommendations: {self.process_recommendations}")
        logger.info(f"Database: {self.db.db_file}")
        logger.info("=" * 70)
        
        try:
            while True:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"\n[{timestamp}] Starting job search...")
                logger.info("-" * 70)
                
                try:
                    # Login if needed
                    if not self.web_driver.logged_in:
                        if not self.login():
                            logger.error("Login failed - will retry next cycle")
                            continue
                    
                    # Scrape all pages
                    current_jobs, run_stats = self.scrape_all_pages()
                    
                    # Send reports
                    self.send_reports(run_stats, current_jobs)
                    
                    # Save data
                    self.storage.save_tracked_jobs()
                    self.storage.save_stats()
                    
                except Exception as e:
                    logger.error(f"Error during scraping: {e}")
                    self.notifier.send_error_notification(f"Scraping error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                logger.info(f"\nNext check in {interval_minutes} minutes...")
                logger.info("-" * 70)
                
                # Sleep
                for _ in range(interval_minutes * 60):
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n\nShutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Saving data...")
        self.storage.save_tracked_jobs()
        self.storage.save_stats()
        
        logger.info("Closing database...")
        self.db.close()
        
        logger.info("Closing browser...")
        self.web_driver.close()
        
        logger.info("Shutdown complete!")