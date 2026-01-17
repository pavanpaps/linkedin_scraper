"""
web_driver.py - Selenium WebDriver management
"""

import pickle
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class WebDriverManager:
    """Manage Selenium WebDriver for LinkedIn automation"""
    
    def __init__(self, headless=False, use_cookies=True):
        self.headless = headless
        self.use_cookies = use_cookies
        self.driver = None
        self.cookies_file = 'linkedin_cookies.pkl'
        self.logged_in = False
    
    def init_driver(self):
        """Initialize Chrome WebDriver"""
        if self.driver:
            return
        
        logger.info("Initializing Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            chrome_options.add_argument('--headless')
            logger.info("Running in headless mode")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            raise
    
    def save_cookies(self):
        """Save cookies for future sessions"""
        if not self.use_cookies:
            return
        
        try:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.driver.get_cookies(), f)
            logger.debug("Cookies saved")
        except Exception as e:
            logger.warning(f"Could not save cookies: {e}")
    
    def load_cookies(self):
        """Load saved cookies"""
        if not self.use_cookies:
            return False
        
        try:
            if os.path.exists(self.cookies_file):
                self.driver.get('https://www.linkedin.com')
                time.sleep(2)
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                return True
        except Exception as e:
            logger.warning(f"Could not load cookies: {e}")
        return False
    
    def login(self, email, password, error_callback=None):
        """
        Login to LinkedIn
        
        Args:
            email: LinkedIn email
            password: LinkedIn password
            error_callback: Function to call on error (optional)
        
        Returns:
            True if login successful, False otherwise
        """
        if self.logged_in:
            return True
        
        self.init_driver()
        logger.info("Logging into LinkedIn...")
        
        # Try loading saved cookies (if enabled)
        if self.use_cookies and self.load_cookies():
            self.driver.get('https://www.linkedin.com/feed/')
            time.sleep(3)
            if 'feed' in self.driver.current_url:
                logger.info("Logged in using saved cookies")
                self.logged_in = True
                return True
            else:
                logger.warning("Cookies didn't work, attempting fresh login...")
        
        # Fresh login
        try:
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(2)
            
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(email)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            time.sleep(5)
            
            if 'checkpoint' in self.driver.current_url:
                logger.warning("Security checkpoint detected - please verify manually")
                if error_callback:
                    error_callback("LinkedIn security checkpoint - manual verification required")
                time.sleep(60)
            
            if 'feed' in self.driver.current_url or 'jobs' in self.driver.current_url:
                logger.info("Successfully logged in")
                self.logged_in = True
                
                # Save cookies only if enabled
                if self.use_cookies:
                    self.save_cookies()
                else:
                    logger.info("Cookie saving disabled - will use fresh login next time")
                
                return True
            else:
                logger.error(f"Login failed - URL: {self.driver.current_url}")
                if error_callback:
                    error_callback("LinkedIn login failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            if error_callback:
                error_callback(f"Login error: {e}")
            return False
    
    def navigate_to(self, url):
        """Navigate to a URL"""
        if not self.driver:
            self.init_driver()
        self.driver.get(url)
    
    def get_page_source(self):
        """Get current page HTML source"""
        if self.driver:
            return self.driver.page_source
        return None
    
    def execute_script(self, script, *args):
        """Execute JavaScript"""
        if self.driver:
            return self.driver.execute_script(script, *args)
    
    def find_elements(self, by, value):
        """Find elements on page"""
        if self.driver:
            return self.driver.find_elements(by, value)
        return []
    
    def save_screenshot(self, filename):
        """Save screenshot"""
        try:
            if self.driver:
                self.driver.save_screenshot(filename)
                logger.debug(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.warning(f"Could not save screenshot: {e}")
    
    def close(self):
        """Close WebDriver"""
        if self.driver:
            logger.info("Closing WebDriver...")
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.logged_in = False