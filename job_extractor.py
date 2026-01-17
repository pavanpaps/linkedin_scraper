"""
job_extractor.py - Extract job details from LinkedIn pages
FIXED: H1-first extraction strategy (most reliable)
"""

import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobExtractor:
    """Extract job details from LinkedIn HTML - supports old and new interfaces"""
    
    def __init__(self, default_location="Location not specified"):
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
    
    def detect_search_type(self, url):
        """
        Detect which LinkedIn search interface is being used
        """
        if '/jobs/search-results/' in url:
            return 'new'
        elif '/jobs/search/' in url:
            return 'old'
        elif 'SEMANTIC_SEARCH' in url:
            return 'new'
        return 'old'
    
    def extract_from_details_panel(self, html_source, debug=False, search_type=None):
        """
        Extract job details from the job details panel
        STRATEGY: H1 FIRST (most reliable), then fallback to other methods
        """
        soup = BeautifulSoup(html_source, 'html.parser')
        
        # Auto-detect search type if not specified
        if not search_type:
            if soup.find('div', class_=re.compile('job-card-job-posting')):
                search_type = 'new'
            elif soup.find('div', class_=re.compile('semantic-search')):
                search_type = 'new'
            else:
                search_type = 'old'
        
        if debug:
            logger.info(f"🔍 Detected search type: {search_type.upper()}")
        
        # ===== TITLE: Try H1 FIRST (most reliable) =====
        title = self._extract_from_h1(soup, debug)
        
        # Fallback to artdeco only if H1 fails
        if not title or len(title) < 5:
            if debug:
                logger.info("H1 failed, trying artdeco title...")
            title = self._extract_artdeco_title(soup, debug)
        
        # Last resort: old-specific patterns
        if not title or len(title) < 5:
            if debug:
                logger.info("Artdeco failed, trying old-specific patterns...")
            details_panel = self._find_details_panel(soup)
            title = self._extract_title_old_specific(details_panel, soup, debug)
        
        # ===== COMPANY: Try multiple methods (artdeco can be stale) =====
        details_panel = self._find_details_panel(soup)
        
        # Try old-specific FIRST (more reliable for company)
        company = self._extract_company_old_specific(details_panel, debug)
        
        # Fallback to artdeco if old-specific fails
        if not company:
            company = self._extract_artdeco_company(soup, debug)
        
        # ===== LOCATION: Artdeco + fallbacks =====
        location = self._extract_artdeco_location(soup, debug)
        if not location:
            location = self._extract_location_old_specific(details_panel, debug)
        
        return {
            'title': title or "Title not found",
            'company': company or "Not specified",
            'location': location or self.default_location,
        }
    
    def _find_details_panel(self, soup):
        """Find the job details panel container"""
        return (
            soup.find('div', class_='jobs-details__main-content') or
            soup.find('section', class_='jobs-details__main-content') or
            soup.find('div', class_='jobs-unified-top-card') or
            soup.find('div', class_='job-details-jobs-unified-top-card') or
            soup.find('div', class_=re.compile('job-card-job-posting-card-wrapper')) or
            soup.find('div', class_=re.compile('job-posting-card')) or
            soup
        )
    
    # ========== H1 EXTRACTOR (MOST RELIABLE - USE FIRST!) ==========
    
    def _extract_from_h1(self, soup, debug=False):
        """
        Extract title from H1 tag - MOST RELIABLE METHOD
        This should ALWAYS be tried first!
        """
        # Find all H1 tags
        h1_tags = soup.find_all('h1', limit=10)
        
        for h1 in h1_tags:
            text = h1.get_text(separator=' ', strip=True)
            
            # Clean the text
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            text = ' '.join(text.split())
            text = self._clean_title_text(text)
            
            # Validate it's a real job title
            if self._is_valid_job_title(text):
                if debug:
                    logger.debug(f"✓ Title (H1): {text[:60]}")
                return text
        
        if debug:
            logger.debug("⚠ No valid H1 title found")
        return None
    
    # ========== ARTDECO EXTRACTORS ==========
    
    def _extract_artdeco_title(self, soup, debug=False):
        """Extract title from artdeco structure - USE ONLY AS FALLBACK"""
        title_elem = soup.find('div', class_='artdeco-entity-lockup__title')
        if not title_elem:
            if debug:
                logger.debug("⚠ No artdeco title element found")
            return None
        
        # Try aria-label first
        aria_label = title_elem.get('aria-label', '')
        if aria_label:
            text = re.sub(r'<!--.*?-->', '', aria_label, flags=re.DOTALL).strip()
            text = self._clean_title_text(text)
            if self._is_valid_job_title(text):
                if debug:
                    logger.debug(f"✓ Title (artdeco aria): {text[:60]}")
                return text
        
        # Try direct text
        text = title_elem.get_text(separator=' ', strip=True)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = ' '.join(text.split())
        text = self._clean_title_text(text)
        
        if self._is_valid_job_title(text):
            if debug:
                logger.debug(f"✓ Title (artdeco): {text[:60]}")
            return text
        
        # Try nested elements
        for tag in ['h1', 'h2', 'a']:
            elem = title_elem.find(tag)
            if elem:
                text = elem.get_text(strip=True)
                text = self._clean_title_text(text)
                if self._is_valid_job_title(text):
                    if debug:
                        logger.debug(f"✓ Title (artdeco {tag}): {text[:60]}")
                    return text
        
        if debug:
            logger.warning("⚠ Could not extract title (artdeco)")
        return None
    
    def _extract_artdeco_company(self, soup, debug=False):
        """Extract company from artdeco structure"""
        subtitle_elem = soup.find('div', class_='artdeco-entity-lockup__subtitle')
        if subtitle_elem:
            ltr_div = subtitle_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                text = ltr_div.get_text(strip=True)
            else:
                text = subtitle_elem.get_text(separator=' ', strip=True)
            
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            text = self._clean_company_name(text)
            
            if text and text != "Not specified":
                if debug:
                    logger.debug(f"✓ Company (artdeco): {text}")
                return text
        
        if debug:
            logger.debug("⚠ Could not extract company (artdeco)")
        return None
    
    def _extract_artdeco_location(self, soup, debug=False):
        """Extract location from artdeco structure"""
        caption_elem = soup.find('div', class_='artdeco-entity-lockup__caption')
        if caption_elem:
            ltr_div = caption_elem.find('div', {'dir': 'ltr'})
            if ltr_div:
                text = ltr_div.get_text(strip=True)
            else:
                text = caption_elem.get_text(separator=' ', strip=True)
            
            # Clean HTML comments and whitespace
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            text = ' '.join(text.split())
            
            if debug:
                logger.debug(f"Caption text found: '{text}'")
            
            if text and self._is_valid_location(text):
                if debug:
                    logger.debug(f"✓ Location (artdeco): {text}")
                return text
            elif text and debug:
                logger.debug(f"Caption text rejected by validation: '{text}'")
        
        if debug:
            logger.debug("⚠ Could not extract location (artdeco)")
        return None
    
    # ========== OLD-SPECIFIC EXTRACTORS ==========
    
    def _extract_title_old_specific(self, details_panel, full_soup, debug=False):
        """Extract title from OLD interface specific patterns"""
        if not details_panel:
            return None
            
        selectors = [
            ('h1', 'job-details-jobs-unified-top-card__job-title'),
            ('h1', 'jobs-unified-top-card__job-title'),
            ('h2', 't-24 t-bold'),
            ('h1', 't-24'),
        ]
        
        for tag, class_name in selectors:
            elem = details_panel.find(tag, class_=lambda x: x and class_name in str(x))
            if elem:
                text = elem.get_text(strip=True)
                text = self._clean_title_text(text)
                if self._is_valid_job_title(text):
                    if debug:
                        logger.debug(f"✓ Title (old {tag}): {text[:60]}")
                    return text
        
        if debug:
            logger.debug("⚠ Could not extract title (old-specific)")
        return None
    
    def _extract_company_old_specific(self, details_panel, debug=False):
        """Extract company from OLD interface specific patterns"""
        if not details_panel:
            return None
        
        # Strategy 1: Look for /company/ links FIRST (most reliable)
        for link in details_panel.find_all('a', href=True):
            href = link.get('href', '')
            if '/company/' in href:
                text = link.get_text(strip=True)
                text = self._clean_company_name(text)
                if text and len(text) > 2 and text != "Not specified":
                    if debug:
                        logger.debug(f"✓ Company (company link): {text}")
                    return text
        
        # Strategy 2: Specific class patterns
        patterns = [
            'job-details-jobs-unified-top-card__company-name',
            'jobs-unified-top-card__company-name',
            'topcard__org-name-link',
            'job-card-container__company-name',
        ]
        
        for pattern in patterns:
            elem = details_panel.find(['a', 'span', 'div'], class_=lambda x: x and pattern in str(x))
            if elem:
                text = elem.get_text(strip=True)
                text = self._clean_company_name(text)
                if text and text != "Not specified":
                    if debug:
                        logger.debug(f"✓ Company (old pattern): {text}")
                    return text
        
        if debug:
            logger.debug("⚠ Could not extract company (old-specific)")
        return None
    
    def _extract_location_old_specific(self, details_panel, debug=False):
        """Extract location from OLD interface specific patterns"""
        if not details_panel:
            return None
            
        selectors = [
            ('span', 'job-details-jobs-unified-top-card__bullet'),
            ('span', 'jobs-unified-top-card__bullet'),
            ('span', 'job-card-container__metadata-item'),
        ]
        
        for tag, class_name in selectors:
            elem = details_panel.find(tag, class_=lambda x: x and class_name in str(x))
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_location(text):
                    if debug:
                        logger.debug(f"✓ Location (old): {text}")
                    return text
        
        # Try to extract work type as location
        work_type = self._extract_work_type(details_panel)
        if work_type:
            if debug:
                logger.debug(f"✓ Work type (old): {work_type}")
            return work_type
        
        if debug:
            logger.debug("⚠ Could not extract location (old-specific)")
        return None
    
    # ========== VALIDATION & CLEANING ==========
    
    def _is_valid_job_title(self, text):
        """Validate if text is a real job title"""
        if not text or len(text) < 5 or len(text) > 300:
            return False
        
        text_lower = text.lower()
        
        # Reject common non-title artifacts
        invalid_indicators = [
            'notification',
            'followers',
            'with verification',
            'sign in',
            'join',
            'showing',
            'results',
            'filters',
            'are these results',
            'your profile',
            'about the job',
            'people you can reach',
            'see all',
            'company page',
        ]
        
        if any(ind in text_lower for ind in invalid_indicators):
            return False
        
        # Reject if it looks like a company profile
        if self._looks_like_company_profile(text):
            return False
        
        # Reject duplicate patterns like "Data Engineer IData Engineer I"
        if re.search(r'(\w+\s+\w+)\1', text, re.IGNORECASE):
            return False
        
        return True
    
    def _clean_title_text(self, text):
        """Clean extracted title text"""
        if not text:
            return text
        
        # Remove common artifacts at the end
        text = re.sub(r'with verification$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+\d+[\d,]+\s+followers?$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Finance$', '', text)  # Remove trailing "Finance" artifact
        text = re.sub(r'TeamFinance$', ' Team', text)  # Fix "TeamFinance" -> "Team"
        
        # Remove duplicate patterns (e.g., "Data Engineer IData Engineer I" -> "Data Engineer I")
        words = text.split()
        if len(words) > 2:
            # Check if second half duplicates first half
            mid = len(words) // 2
            first_half = ' '.join(words[:mid])
            second_half = ' '.join(words[mid:mid*2])
            if first_half.lower() == second_half.lower():
                text = first_half
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _looks_like_company_profile(self, text):
        """Check if text looks like a company profile"""
        if not text:
            return False
        
        text_lower = text.lower()
        indicators = [
            'followers',
            'verified',
            '@ ',
            ' is hiring',
            'see all jobs',
            'company page',
        ]
        
        return any(ind in text_lower for ind in indicators)
    
    def _clean_company_name(self, company):
        """Clean company name"""
        if not company:
            return "Not specified"
        
        company = ' '.join(company.split())
        company = company.split('·')[0].strip()
        company = company.split('\n')[0].strip()
        company = company.rstrip('.,;:')
        company = re.sub(r'\s*\(.*?\)\s*$', '', company)
        
        # Remove follower counts
        company = re.sub(r'\s+\d+[\d,]+\s+followers?$', '', company, flags=re.IGNORECASE)
        
        if len(company) < 2:
            return "Not specified"
        
        return company
    
    def _is_valid_location(self, text):
        """Validate if text is a real location"""
        if not text or len(text) < 2:
            return False
        
        text_lower = text.lower()
        
        invalid = ['school', 'college', 'university', 'alumni', 'hiring', 
                   'apply', 'save', 'share', 'week', 'ago', 'hour', 'day',
                   'month', 'promoted', 'reposted', 'followers']
        
        if any(kw in text_lower for kw in invalid):
            return False
        
        valid = [',', 'remote', 'hybrid', 'on-site', 'onsite', 'india', 
                'bangalore', 'bengaluru', 'mumbai', 'delhi', 'hyderabad', 
                'pune', 'chennai', 'karnataka', 'tamil nadu', 'maharashtra']
        
        if any(kw in text_lower for kw in valid):
            return True
        
        return 5 < len(text) < 150
    
    def _extract_work_type(self, soup):
        """Extract work type"""
        if not soup:
            return None
        text = soup.get_text()
        for work_type in ['Remote', 'Hybrid', 'On-site', 'Onsite']:
            if work_type in text:
                return work_type
        return None
    
    def debug_extraction(self, html_source, job_id, current_url=None):
        """Debug helper"""
        soup = BeautifulSoup(html_source, 'html.parser')
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 DEBUG: Job {job_id}")
        
        search_type = self.detect_search_type(current_url) if current_url else 'unknown'
        logger.info(f"🔍 Search Type: {search_type.upper()}")
        logger.info(f"{'='*70}")
        
        try:
            filename = f'debug_job_{job_id}_{search_type}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            logger.info(f"💾 Saved: {filename}")
        except Exception as e:
            logger.warning(f"Could not save HTML: {e}")
        
        logger.info("\n📋 H1 Tags:")
        h1_tags = soup.find_all('h1', limit=10)
        if h1_tags:
            for h1 in h1_tags:
                text = h1.get_text(strip=True)
                logger.info(f"  • {text[:70]}")
        else:
            logger.info("  ❌ No H1 tags found")
        
        logger.info("\n📋 ARTDECO Structure:")
        
        title_elem = soup.find('div', class_='artdeco-entity-lockup__title')
        if title_elem:
            logger.info(f"  ✅ Title: {title_elem.get_text(strip=True)[:60]}")
        else:
            logger.info(f"  ❌ No artdeco title")
        
        subtitle_elem = soup.find('div', class_='artdeco-entity-lockup__subtitle')
        if subtitle_elem:
            logger.info(f"  ✅ Subtitle: {subtitle_elem.get_text(strip=True)[:60]}")
        else:
            logger.info(f"  ❌ No artdeco subtitle")
        
        caption_elem = soup.find('div', class_='artdeco-entity-lockup__caption')
        if caption_elem:
            logger.info(f"  ✅ Caption: {caption_elem.get_text(strip=True)[:60]}")
        else:
            logger.info(f"  ❌ No artdeco caption")
        
        logger.info("\n📋 Company Links (/company/):")
        company_links = soup.find_all('a', href=lambda x: x and '/company/' in x, limit=10)
        if company_links:
            for i, link in enumerate(company_links, 1):
                text = link.get_text(strip=True)
                href = link.get('href', '')[:50]
                logger.info(f"  {i}. {text[:50]} → {href}")
        else:
            logger.info("  ❌ No company links found")
        
        logger.info("\n📋 Company Name Classes:")
        patterns = [
            'job-details-jobs-unified-top-card__company-name',
            'jobs-unified-top-card__company-name',
            'topcard__org-name-link',
        ]
        for pattern in patterns:
            elem = soup.find(['a', 'span', 'div'], class_=lambda x: x and pattern in str(x))
            if elem:
                logger.info(f"  ✅ {pattern}: {elem.get_text(strip=True)[:50]}")
            else:
                logger.info(f"  ❌ {pattern}: not found")
        
        logger.info(f"\n{'='*70}\n")