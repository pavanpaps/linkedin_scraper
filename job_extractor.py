"""
job_extractor.py - Extract job details from LinkedIn pages
FIXED VERSION - Correctly extracts from job details panel
"""

import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobExtractor:
    """Extract job details from LinkedIn HTML"""
    
    def __init__(self, default_location="Bengaluru, Karnataka, India"):
        self.default_location = default_location
    
    def extract_job_id_from_url(self, url):
        """Extract job ID from LinkedIn URL"""
        match = re.search(r'currentJobId=(\d+)', url)
        if match:
            return match.group(1)
        
        match = re.search(r'/jobs/view/(\d+)', url)
        if match:
            return match.group(1)
        
        return None
    
    def extract_job_details(self, html_source, debug=False):
        """
        Extract job details from HTML source
        
        Args:
            html_source: HTML source code
            debug: Enable debug logging
        
        Returns:
            Dictionary with title, company, location, and metadata
        """
        soup = BeautifulSoup(html_source, 'html.parser')
        
        title = self._extract_title(soup, debug)
        company = self._extract_company(soup, title, debug)
        location = self._extract_location(soup, debug)
        metadata = self._extract_metadata(soup, debug)
        
        result = {
            'title': title,
            'company': company,
            'location': location,
        }
        
        if metadata:
            result.update(metadata)
        
        return result
    
    def extract_from_details_panel(self, html_source, debug=False):
        """
        Extract job details from the job details panel (right side of LinkedIn search)
        This isolates the job details panel to avoid extracting from search results
        
        Args:
            html_source: Full page HTML source
            debug: Enable debug logging
        
        Returns:
            Dictionary with title, company, location
        """
        soup = BeautifulSoup(html_source, 'html.parser')
        
        # Find the job details panel specifically (right side panel)
        details_panel = (
            soup.find('div', class_='jobs-details__main-content') or
            soup.find('section', class_='jobs-details__main-content') or
            soup.find('div', class_='jobs-unified-top-card') or
            soup.find('div', class_='job-details-jobs-unified-top-card') or
            soup.find('div', id='job-details')
        )
        
        if not details_panel:
            if debug:
                logger.warning("Could not find job details panel - using full page")
            # Fallback to full page extraction
            details_panel = soup
        else:
            if debug:
                logger.debug("✓ Found job details panel")
        
        # Extract from the isolated panel
        title = self._extract_title(details_panel, debug)
        company = self._extract_company(details_panel, title, debug)
        location = self._extract_location(details_panel, debug)
        metadata = self._extract_metadata(details_panel, debug)
        
        result = {
            'title': title,
            'company': company,
            'location': location,
        }
        
        if metadata:
            result.update(metadata)
        
        return result
    
    def extract_from_job_card(self, card_element, debug=False):
        """
        Extract job details from a single job card element in search results
        
        Args:
            card_element: BeautifulSoup element of the job card
            debug: Enable debug logging
        
        Returns:
            Dictionary with title, company, location
        """
        if isinstance(card_element, str):
            card_element = BeautifulSoup(card_element, 'html.parser')
        
        title = self._extract_title(card_element, debug)
        company = self._extract_company(card_element, title, debug, is_job_card=True)
        location = self._extract_location(card_element, debug)
        
        return {
            'title': title,
            'company': company,
            'location': location,
        }
    
    def _extract_title(self, soup, debug=False):
        """Extract job title"""
        # Strategy 1: artdeco-entity-lockup__title
        title_elem = soup.find('div', class_='artdeco-entity-lockup__title')
        if title_elem:
            ltr_div = title_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                title = ltr_div.text.strip()
                if title:
                    if debug:
                        logger.debug(f"✓ Found title: {title[:50]}")
                    return title
        
        # Strategy 2: Common title selectors
        title_selectors = [
            ('h1', {'class_': 'job-details-jobs-unified-top-card__job-title'}),
            ('h1', {'class_': 'jobs-unified-top-card__job-title'}),
            ('h2', {'class_': 't-24 t-bold'}),
            ('h1', {'class_': 't-24'}),
            ('h1', {'class_': 'topcard__title'}),
        ]
        
        for tag, attrs in title_selectors:
            title_elem = soup.find(tag, attrs)
            if title_elem:
                title = title_elem.text.strip()
                if title:
                    if debug:
                        logger.debug(f"✓ Found title from {tag}: {title[:50]}")
                    return title
        
        # Strategy 3: Generic h1/h2
        for tag in ['h1', 'h2']:
            elem = soup.find(tag)
            if elem:
                text = elem.text.strip()
                if text and len(text) > 3:
                    if debug:
                        logger.debug(f"✓ Found title from {tag}: {text[:50]}")
                    return text
        
        if debug:
            logger.warning("⚠ Could not extract job title")
        return None
    
    def _extract_company(self, soup, title, debug=False, is_job_card=False):
        """Extract company name"""
        company = None
        
        # Strategy 1: artdeco-entity-lockup__subtitle (most reliable)
        subtitle_elem = soup.find('div', class_='artdeco-entity-lockup__subtitle')
        if subtitle_elem:
            ltr_div = subtitle_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                text = ltr_div.text.strip()
                text = text.replace('<!--', '').replace('-->', '').strip()
                if text and len(text) > 1:
                    company = text
                    if debug:
                        logger.debug(f"✓ Found company from artdeco subtitle: {company}")
        
        # Strategy 2: Other subtitle patterns
        if not company:
            subtitle_patterns = [
                'job-details-jobs-unified-top-card__company-name',
                'jobs-unified-top-card__company-name',
                'job-card-job-posting-card-wrapper__subtitle',
                'jobs-unified-top-card__subtitle-primary-grouping',
                'job-card-container__primary-description'
            ]
            
            for pattern in subtitle_patterns:
                elem = soup.find(['div', 'span', 'a'], class_=lambda x: x and pattern in str(x))
                if elem:
                    # Try to find nested dir="ltr" first
                    ltr_div = elem.find('div', {'dir': 'ltr'})
                    text = ltr_div.text.strip() if ltr_div else elem.text.strip()
                    text = text.replace('<!--', '').replace('-->', '').strip()
                    
                    # Clean up text that might have location info
                    if '·' in text:
                        text = text.split('·')[0].strip()
                    elif '•' in text:
                        text = text.split('•')[0].strip()
                    
                    if text and 2 < len(text) < 100:
                        company = text
                        if debug:
                            logger.debug(f"✓ Found company from {pattern}: {company}")
                        break
        
        # Strategy 3: Company link
        if not company:
            company_elem = (
                soup.find('a', class_='topcard__org-name-link') or
                soup.find('a', {'data-tracking-control-name': 'public_jobs_topcard-org-name'}) or
                soup.find('a', href=lambda x: x and '/company/' in str(x))
            )
            
            if company_elem:
                text = company_elem.text.strip()
                if text and len(text) > 1:
                    company = text
                    if debug:
                        logger.debug(f"✓ Found company from link: {company}")
        
        # Strategy 4: Search dir="ltr" divs (last resort)
        if not company:
            ltr_divs = soup.find_all('div', {'dir': 'ltr'}, limit=20)
            for ltr_div in ltr_divs:
                text = ltr_div.text.strip().replace('<!--', '').replace('-->', '').strip()
                
                if text and 2 < len(text) < 100:
                    # Skip if it's the title
                    if title and text.lower() == title.lower():
                        continue
                    
                    # Skip locations (multiple commas or work type keywords)
                    if text.count(',') >= 2 or any(word in text for word in ['On-site', 'Remote', 'Hybrid']):
                        continue
                    
                    # Skip UI text
                    if text.lower() in ['apply', 'save', 'share', 'show more', 'show less', 'see more', 'see less']:
                        continue
                    
                    company = text
                    if debug:
                        logger.debug(f"✓ Found company from dir=ltr: {company}")
                    break
        
        # Clean up and validate
        if company:
            company = self._clean_company_name(company)
        
        if not company:
            company = "Not specified"
            if debug:
                logger.warning("⚠ Could not extract company name")
        else:
            if debug:
                logger.info(f"✅ Final company: {company}")
        
        return company
    
    def _clean_company_name(self, company):
        """Clean and normalize company name"""
        if not company:
            return "Not specified"
        
        # Remove extra whitespace
        company = ' '.join(company.split())
        
        # Remove common separators and extra text
        company = company.split('·')[0].strip()
        company = company.split('•')[0].strip()
        company = company.split('\n')[0].strip()
        company = company.rstrip('.,;:')
        
        # Validate
        if len(company) < 2 or company.lower() in ['hiring', 'new', 'jobs', 'apply']:
            return "Not specified"
        
        return company
    
    def _extract_location(self, soup, debug=False):
        """Extract job location"""
        location = None
        
        # Strategy 1: artdeco-entity-lockup__caption (most reliable)
        caption_elem = soup.find('div', class_='artdeco-entity-lockup__caption')
        if caption_elem:
            ltr_div = caption_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                text = ltr_div.text.strip()
                text = text.replace('<!--', '').replace('-->', '').strip()
                # Location has commas or work type keywords
                if text and (',' in text or any(word in text for word in ['On-site', 'Remote', 'Hybrid'])):
                    location = text
                    if debug:
                        logger.debug(f"✓ Found location: {location}")
        
        # Strategy 2: Traditional location selectors
        if not location:
            location_selectors = [
                ('span', {'class_': 'job-details-jobs-unified-top-card__bullet'}),
                ('span', {'class_': 'jobs-unified-top-card__bullet'}),
                ('span', {'class_': 'topcard__flavor topcard__flavor--bullet'}),
            ]
            
            for tag, attrs in location_selectors:
                location_elem = soup.find(tag, attrs)
                if location_elem:
                    text = location_elem.text.strip()
                    if text and ',' in text:
                        location = text
                        if debug:
                            logger.debug(f"✓ Found location from {tag}: {location}")
                        break
        
        # Strategy 3: Search dir="ltr" for location-like text
        if not location:
            ltr_divs = soup.find_all('div', {'dir': 'ltr'}, limit=30)
            for ltr_div in ltr_divs:
                text = ltr_div.text.strip().replace('<!--', '').replace('-->', '').strip()
                # Location has commas or work type indicators
                if text and (',' in text or any(word in text for word in ['On-site', 'Remote', 'Hybrid'])):
                    if 5 < len(text) < 150:
                        location = text
                        if debug:
                            logger.debug(f"✓ Found location from dir=ltr: {location}")
                        break
        
        # Fallback to default
        if not location:
            location = self.default_location
            if debug:
                logger.debug(f"Using default location: {location}")
        
        return location
    
    def _extract_metadata(self, soup, debug=False):
        """Extract additional job metadata"""
        metadata = {}
        
        # Extract job insights
        insight_elem = soup.find('div', class_=lambda x: x and 'job-insight' in str(x))
        if insight_elem:
            insight_text = insight_elem.text.strip()
            if insight_text:
                metadata['insight'] = insight_text
                if debug:
                    logger.debug(f"✓ Found insight: {insight_text[:60]}")
        
        # Extract work type
        text_content = soup.get_text()
        for work_type in ['Remote', 'On-site', 'Hybrid']:
            if work_type in text_content:
                metadata['work_type'] = work_type
                if debug:
                    logger.debug(f"✓ Found work type: {work_type}")
                break
        
        return metadata if metadata else None
    
    def debug_company_extraction(self, html_source, job_id):
        """Debug helper to show HTML structure"""
        soup = BeautifulSoup(html_source, 'html.parser')
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 DEBUG: Job extraction for {job_id}")
        logger.info(f"{'='*70}")
        
        # Check for details panel
        details_panel = (
            soup.find('div', class_='jobs-details__main-content') or
            soup.find('section', class_='jobs-details__main-content') or
            soup.find('div', class_='jobs-unified-top-card') or
            soup.find('div', class_='job-details-jobs-unified-top-card')
        )
        
        if details_panel:
            logger.info("✅ Found job details panel")
            soup = details_panel  # Focus on details panel
        else:
            logger.warning("⚠ No details panel found - analyzing full page")
        
        logger.info("\n📊 Artdeco Structure:")
        
        # Title
        title_elem = soup.find('div', class_='artdeco-entity-lockup__title')
        if title_elem:
            logger.info("  ✅ Title element found")
            ltr_div = title_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                logger.info(f"     {ltr_div.text.strip()[:60]}")
        else:
            logger.info("  ❌ No title element")
        
        # Company (subtitle)
        subtitle_elem = soup.find('div', class_='artdeco-entity-lockup__subtitle')
        if subtitle_elem:
            logger.info("  ✅ Subtitle (company) found")
            ltr_div = subtitle_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                logger.info(f"     {ltr_div.text.strip()}")
        else:
            logger.info("  ❌ No subtitle element")
        
        # Location (caption)
        caption_elem = soup.find('div', class_='artdeco-entity-lockup__caption')
        if caption_elem:
            logger.info("  ✅ Caption (location) found")
            ltr_div = caption_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                logger.info(f"     {ltr_div.text.strip()}")
        else:
            logger.info("  ❌ No caption element")
        
        # Show all dir="ltr" divs
        ltr_divs = soup.find_all('div', {'dir': 'ltr'}, limit=10)
        if ltr_divs:
            logger.info(f"\n📍 Found {len(ltr_divs)} dir=ltr elements:")
            for i, div in enumerate(ltr_divs, 1):
                text = div.text.strip().replace('<!--', '').replace('-->', '').strip()
                if text:
                    parent_class = div.parent.get('class', []) if div.parent else []
                    logger.info(f"  {i}. {text[:70]}")
                    if parent_class:
                        logger.info(f"     Parent: {parent_class}")
        
        logger.info(f"{'='*70}\n")