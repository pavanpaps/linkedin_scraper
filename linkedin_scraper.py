"""
linkedin_scraper.py - Multi-URL LinkedIn Scraper
FIXED: Robust waiting for details panel to update with correct job
"""

import time
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import re

# Import modules
from config import Config
from web_driver import WebDriverManager
from job_extractor import JobExtractor
from notifications import TelegramNotifier
from job_filters import JobFilter
from storage import JobStorage
from database import JobDatabase
from reports import ReportGenerator
from pid_manager import PIDManager

logger = logging.getLogger(__name__)


def random_delay(min_sec=2, max_sec=5):
    """Random delay"""
    time.sleep(random.uniform(min_sec, max_sec))


class LinkedInScraper:
    """Main LinkedIn job scraper with multi-URL support"""
    
    def __init__(self, config_file='config.json', headless=False, use_cookies=True):
        # Load configuration
        self.pid_manager = PIDManager()
        self.pid_manager.create_pid_file()
        self.config = Config(config_file)
        
        # Initialize components
        self.web_driver = WebDriverManager(headless=headless, use_cookies=use_cookies)
        self.job_extractor = JobExtractor(default_location="Location not specified")
        
        telegram_config = self.config.get_telegram_config()
        self.notifier = TelegramNotifier(
            bot_token=telegram_config['bot_token'],
            chat_id=telegram_config['chat_id']
        )
        
        self.job_filter = JobFilter(self.config.get_filters())
        self.storage = JobStorage()
        
        # Initialize database
        self.db = JobDatabase()
        self.report_generator = ReportGenerator(self.db)
        
        # Settings
        self.process_recommendations = self.config.should_process_recommendations()
        
        # CSS selectors
        self.job_card_selectors = [
            "li.scaffold-layout__list-item",
            "li.jobs-search-results__list-item",
            "div.job-card-container",
        ]
        
        # Report tracking
        self.last_periodic_report = datetime.now()
        self.periodic_report_interval = 6
        
        # Get search URLs
        self.search_urls = self.config.get_search_urls()
        
        logger.info("=" * 70)
        logger.info("LinkedIn Scraper initialized")
        logger.info(f"Search URLs configured: {len(self.search_urls)}")
        for i, url in enumerate(self.search_urls, 1):
            desc = self.config.get_url_description(url)
            logger.info(f"  {i}. {desc}")
        logger.info(f"Filters: {self.job_filter.get_filter_summary()}")
        logger.info("=" * 70)
    
    def login(self):
        """Login to LinkedIn"""
        credentials = self.config.get_linkedin_credentials()
        return self.web_driver.login(
            email=credentials['email'],
            password=credentials['password'],
            error_callback=self.notifier.send_error_notification
        )
    
    def check_no_jobs_page(self, html_source):
        """Check if page shows 'No matching jobs found'"""
        try:
            soup = BeautifulSoup(html_source, 'html.parser')
            no_jobs_indicators = [
                soup.find('h1', string=re.compile(r'No matching jobs found', re.IGNORECASE)),
                soup.find('div', string=re.compile(r'No matching jobs found', re.IGNORECASE)),
            ]
            return any(no_jobs_indicators)
        except:
            return False
    
    def find_job_elements(self):
        """Find job card elements"""
        for selector in self.job_card_selectors:
            try:
                elements = self.web_driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} job elements")
                    return elements
            except Exception as e:
                logger.debug(f"Error with {selector}: {e}")
        return []
    
    def is_recommendation_divider(self, element_text):
        """Check if element is recommendations divider"""
        return ("We've found more results" in element_text or 
                "share similar criteria" in element_text)
    
    def wait_for_details_panel_update(self, expected_job_id, max_attempts=30):
        """
        Wait for details panel to update with the correct job
        Returns: (success, actual_job_id, html_source)
        """
        for attempt in range(max_attempts):
            try:
                time.sleep(0.5)  # Small delay between checks
                
                # Get current state
                current_url = self.web_driver.driver.current_url
                html_source = self.web_driver.get_page_source()
                
                # Extract job ID from URL
                url_job_id = self.job_extractor.extract_job_id_from_url(current_url)
                
                # Also verify the HTML contains the expected job ID
                soup = BeautifulSoup(html_source, 'html.parser')
                
                # Check if artdeco structure has loaded with new content
                title_elem = soup.find('div', class_='artdeco-entity-lockup__title')
                
                # Verify job ID matches both in URL and content
                if url_job_id == expected_job_id and title_elem:
                    # Additional verification: check if H1 tag exists with real content
                    h1_elem = soup.find('h1')
                    if h1_elem:
                        h1_text = h1_elem.get_text(strip=True)
                        # Make sure it's not a generic title
                        if len(h1_text) > 5 and 'notification' not in h1_text.lower():
                            logger.debug(f"✓ Panel loaded correctly (attempt {attempt + 1})")
                            return True, url_job_id, html_source
                
                logger.debug(f"Waiting for panel update... (attempt {attempt + 1}/{max_attempts})")
                
            except StaleElementReferenceException:
                logger.debug(f"Stale element, retrying...")
                continue
            except Exception as e:
                logger.debug(f"Error checking panel: {e}")
                continue
        
        logger.warning(f"Panel did not update after {max_attempts} attempts")
        return False, None, None
    
    def scrape_url_pages(self, base_url, url_index, max_pages=10):
        """
        Scrape all pages for a specific search URL
        FIXED: Robust waiting for details panel
        """
        url_desc = self.config.get_url_description(base_url)
        logger.info(f"\n{'='*70}")
        logger.info(f"SEARCH #{url_index}: {url_desc}")
        logger.info(f"{'='*70}")
        
        all_jobs = []
        page_num = 1
        
        while page_num <= max_pages:
            # Build paginated URL
            page_url = self.config.add_pagination_to_url(base_url, page_num)
            
            logger.info(f"\n{'─'*70}")
            logger.info(f"Search #{url_index} - Page {page_num}")
            logger.info(f"{'─'*70}")
            
            try:
                # Navigate to page
                logger.info("Loading page...")
                self.web_driver.navigate_to(page_url)
                time.sleep(8)
                
                html_source = self.web_driver.get_page_source()
                
                # Check if no jobs
                if self.check_no_jobs_page(html_source):
                    logger.info(f"No more jobs for this search")
                    break
                
                # Scroll to load all jobs
                for i in range(5):
                    self.web_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    random_delay(1.5, 2.5)
                
                # Find job elements
                job_elements = self.find_job_elements()
                
                if not job_elements:
                    logger.warning("No job elements found")
                    break
                
                logger.info(f"Processing {len(job_elements)} jobs...")
                
                page_jobs = []
                found_divider = False
                processed_job_ids = set()  # Track processed jobs to avoid duplicates
                
                for idx, job_element in enumerate(job_elements):
                    try:
                        # Check for recommendations
                        is_recommendation = False
                        try:
                            element_text = job_element.text
                            if self.is_recommendation_divider(element_text):
                                found_divider = True
                                if not self.process_recommendations:
                                    logger.info("Reached recommendations - stopping")
                                    return all_jobs + page_jobs
                                is_recommendation = True
                                continue
                            
                            if found_divider:
                                is_recommendation = True
                        except:
                            pass
                        
                        # Scroll into view
                        self.web_driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                            job_element
                        )
                        random_delay(0.8, 1.2)
                        
                        # Click the job card
                        try:
                            job_element.click()
                        except:
                            try:
                                link = job_element.find_element(By.CSS_SELECTOR, "a")
                                link.click()
                            except:
                                logger.debug(f"Could not click job {idx+1}")
                                continue
                        
                        # Wait a bit after click
                        time.sleep(1.5)
                        
                        # Get expected job ID from URL
                        current_url = self.web_driver.driver.current_url
                        expected_job_id = self.job_extractor.extract_job_id_from_url(current_url)
                        
                        if not expected_job_id:
                            logger.debug(f"Could not extract job ID from URL")
                            continue
                        
                        # Skip if already processed
                        if expected_job_id in processed_job_ids:
                            logger.debug(f"Job {expected_job_id} already processed, skipping")
                            continue
                        
                        # CRITICAL: Wait for details panel to update with correct job
                        success, actual_job_id, html_source = self.wait_for_details_panel_update(expected_job_id)
                        
                        if not success or actual_job_id != expected_job_id:
                            logger.debug(f"Failed to load correct job details for {expected_job_id}")
                            continue
                        
                        job_id = actual_job_id
                        job_url = f"https://www.linkedin.com/jobs/view/{job_id}"
                        
                        # Extra wait for content stabilization
                        time.sleep(1.0)
                        
                        # Get fresh HTML source one more time
                        html_source = self.web_driver.get_page_source()
                        
                        # Extract job details
                        enable_debug = (idx < 3 and page_num == 1)
                        
                        if enable_debug:
                            logger.info(f"\n🔍 DEBUGGING JOB #{idx+1}")
                            self.job_extractor.debug_extraction(
                                html_source, 
                                job_id,
                                current_url=current_url
                            )
                        
                        # Auto-detect search type from URL
                        search_type = self.job_extractor.detect_search_type(current_url)
                        
                        job_details = self.job_extractor.extract_from_details_panel(
                            html_source,
                            debug=enable_debug,
                            search_type=search_type
                        )
                        
                        # Validate extraction - skip if title is too short or contains artifacts
                        title = job_details.get('title', '')
                        if not title or len(title) < 5:
                            logger.debug(f"Invalid title extracted, skipping")
                            continue
                        
                        # Check for common extraction artifacts
                        title_lower = title.lower()
                        if any(artifact in title_lower for artifact in ['followers', 'with verification', 'data engineer i data engineer i']):
                            logger.debug(f"Title contains artifacts: {title}, skipping")
                            continue
                        
                        # Display
                        job_type = "[REC]" if is_recommendation else "[MATCH]"
                        company = job_details['company'] if job_details['company'] != 'Not specified' else ''
                        separator = ' @ ' if company else ''
                        logger.info(f"  [{len(page_jobs)+1}] {job_details['title'][:50]}{separator}{company[:25]} {job_type}")
                        
                        # Store
                        job_data = {
                            'url': job_url,
                            'title': job_details['title'],
                            'company': job_details['company'],
                            'location': job_details['location'],
                            'job_id': job_id,
                            'is_recommendation': is_recommendation,
                            'page': page_num,
                            'search_url': url_desc,
                            'scraped_at': datetime.now().isoformat()
                        }
                        
                        if 'work_type' in job_details:
                            job_data['work_type'] = job_details['work_type']
                        
                        page_jobs.append(job_data)
                        processed_job_ids.add(job_id)
                        
                    except Exception as e:
                        logger.debug(f"Error on job {idx+1}: {e}")
                        continue
                
                logger.info(f"Extracted {len(page_jobs)} jobs from page {page_num}")
                all_jobs.extend(page_jobs)
                
                # Stop if no jobs found
                if len(page_jobs) == 0:
                    logger.info("No jobs extracted - stopping pagination")
                    break
                
                # Continue to next page
                page_num += 1
                if page_num <= max_pages:
                    logger.info(f"Moving to page {page_num}...")
                    random_delay(3, 5)
                
            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break
        
        logger.info(f"\nSearch #{url_index} complete: {len(all_jobs)} total jobs")
        return all_jobs
    
    def scrape_all_urls(self):
        """
        Scrape all configured search URLs
        
        Returns:
            Tuple of (all_jobs, run_stats)
        """
        start_time = datetime.now()
        run_id = self.db.start_scrape_run()
        
        run_stats = {
            'jobs_found': 0,
            'new_jobs': 0,
            'notifications_sent': 0,
            'errors': 0,
            'pages_scraped': 0,
            'searches_completed': 0,
            'duration': 0
        }
        
        all_jobs = []
        
        try:
            # Login once
            if not self.web_driver.logged_in:
                if not self.login():
                    logger.error("Login failed")
                    self.db.complete_scrape_run(run_id, run_stats)
                    return [], run_stats
            
            # Scrape each URL
            for url_index, search_url in enumerate(self.search_urls, 1):
                logger.info(f"\n{'█'*70}")
                logger.info(f"STARTING SEARCH {url_index}/{len(self.search_urls)}")
                logger.info(f"{'█'*70}")
                
                url_jobs = self.scrape_url_pages(search_url, url_index)
                
                if url_jobs:
                    all_jobs.extend(url_jobs)
                    run_stats['searches_completed'] += 1
                    
                    # Process and notify jobs from this URL
                    new_count, notif_count = self.process_and_notify_jobs(url_jobs)
                    run_stats['new_jobs'] += new_count
                    run_stats['notifications_sent'] += notif_count
                
                # Delay between different searches
                if url_index < len(self.search_urls):
                    logger.info(f"\nPreparing next search...")
                    random_delay(5, 8)
            
            run_stats['jobs_found'] = len(all_jobs)
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            run_stats['errors'] += 1
        
        # Calculate duration
        end_time = datetime.now()
        run_stats['duration'] = (end_time - start_time).total_seconds()
        
        # Complete run
        self.db.complete_scrape_run(run_id, run_stats)
        
        logger.info(f"\n{'█'*70}")
        logger.info(f"ALL SEARCHES COMPLETE")
        logger.info(f"Total jobs: {len(all_jobs)}")
        logger.info(f"New jobs: {run_stats['new_jobs']}")
        logger.info(f"Duration: {run_stats['duration']:.1f}s")
        logger.info(f"{'█'*70}\n")
        
        return all_jobs, run_stats
    
    def process_and_notify_jobs(self, jobs):
        """Process and notify jobs"""
        new_jobs_count = 0
        notifications_sent = 0
        
        for job in jobs:
            # Filter
            if not self.job_filter.should_notify(job):
                continue
            
            # Save to DB
            is_new = self.db.add_job(job)
            
            if is_new and not self.storage.is_job_seen(job['url']):
                new_jobs_count += 1
                
                # Notify
                success = self.notifier.send_job_notification(job)
                
                if success:
                    notifications_sent += 1
                    self.storage.add_job_url(job['url'])
                    self.storage.update_stats(job)
                    self.storage.increment_notifications()
                    self.db.mark_notified(job['job_id'])
                    
                    company = job['company'] if job['company'] != 'Not specified' else ''
                    logger.info(f"  ✅ Notified: {job['title'][:35]} - {company[:20]}")
                
                random_delay(1.5, 2.5)
        
        return new_jobs_count, notifications_sent
    
    def send_reports(self, run_stats, jobs_data):
        """Send reports"""
        if jobs_data:
            try:
                report = self.report_generator.generate_run_report(run_stats, jobs_data)
                self.notifier.send_message(report, parse_mode='HTML')
                logger.info("✅ Run report sent")
            except Exception as e:
                logger.error(f"Failed to send run report: {e}")
        
        # Check periodic report
        hours_since = (datetime.now() - self.last_periodic_report).total_seconds() / 3600
        if hours_since >= self.periodic_report_interval:
            try:
                report = self.report_generator.generate_periodic_report(self.periodic_report_interval)
                if report:
                    self.notifier.send_message(report, parse_mode='HTML')
                    logger.info("✅ Periodic report sent")
                    self.last_periodic_report = datetime.now()
            except Exception as e:
                logger.error(f"Failed to send periodic report: {e}")
    
    def run(self, interval_minutes=30):
        """Main run loop"""
        logger.info("=" * 70)
        logger.info("Multi-URL LinkedIn Job Scraper")
        logger.info("=" * 70)
        logger.info(f"Configured searches: {len(self.search_urls)}")
        logger.info(f"Check interval: Every {interval_minutes} minutes")
        logger.info("=" * 70)
        
        try:
            while True:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"\n[{timestamp}] Starting scrape cycle...")
                
                try:
                    # Scrape all URLs
                    current_jobs, run_stats = self.scrape_all_urls()
                    
                    # Send reports
                    self.send_reports(run_stats, current_jobs)
                    
                    # Save data
                    self.storage.save_tracked_jobs()
                    self.storage.save_stats()
                    
                except Exception as e:
                    logger.error(f"Error: {e}")
                    self.notifier.send_error_notification(f"Error: {str(e)}")
                
                logger.info(f"\nNext check in {interval_minutes} minutes...")
                
                # Sleep
                for _ in range(interval_minutes * 60):
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Cleanup"""
        logger.info("Saving data...")
        self.storage.save_tracked_jobs()
        self.storage.save_stats()
        
        logger.info("Closing database...")
        self.db.close()
        
        logger.info("Closing browser...")
        self.web_driver.close()
        
        logger.info("Shutdown complete!")