"""
Google Maps Scraper API

FastAPI router for Google Maps business scraping functionality.
"""

import json
import logging
import random
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import csv
import io
import re
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    WebDriverException,
    StaleElementReferenceException
)

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('gmaps_scraper.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("🚀 Google Maps API module loaded")

# Create API router
router = APIRouter()

# Configuration
CONFIG = {
    'base_url': 'https://www.google.com/maps/',
    'implicit_wait': 1,
    'explicit_wait': 3,
    'scroll_pause_min': 0.1,
    'scroll_pause_max': 0.5,
    'click_delay': 0.3,
    'max_results': 10000,
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # 'output_dir': 'gmaps_results',
    'retry_attempts': 3,
    'retry_delay': 0.5
}

# CSS Selectors
SELECTORS = {
    'search_input': 'input.searchboxinput',
    'results_container': 'div.Ntshyc',
    'scroll_container': 'div.e07Vkf.kA9KIf',
    'end_of_results': 'span.HlvSq',
    'business_items': [
        'div.Nv2PK.tH5CWc.THOPZb',
        'div.Nv2PK.Q2HXcd.THOPZb',
        'div.Nv2PK.THOPZb.CpccDe'
    ],
    'business_link': 'a.hfpxzc',
    'business_name': 'h1.DUwDvf.lfPIob',
    'average_rating': 'div.F7nice span span',
    'review_count': 'span.e4rVHe.fontBodyMedium',
    'business_type': 'button.DkEaL',
    'address': 'div.Io6YTe.fontBodyMedium.kR99db',
    'website': 'a.CsEnBe',
    'phone': 'span.UsdlK',
    'alt_website': 'a.lcr4fd.S9kvJb'
}

# Pydantic models
class BusinessData(BaseModel):
    """Business data model"""
    business_name: Optional[str] = None
    average_rating: Optional[str] = None
    review_count: Optional[int] = None
    business_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    scraped_time: str
    scraped_index: int

class ScrapeRequest(BaseModel):
    """Scrape request model"""
    query: str = Field(..., description="Search query (e.g., 'car companies in Takoradi')")
    max_results: Optional[int] = Field(default=100, description="Maximum number of results to scrape", ge=1, le=10000)

class ScrapeResponse(BaseModel):
    """Scrape response model"""
    success: bool
    query: str
    scraped_time: str
    total_results: int
    execution_time_seconds: float
    businesses: List[BusinessData]
    message: str
    # Download options
    download_urls: Optional[Dict[str, str]] = Field(default=None, description="URLs for downloading results")

class ScrapeStatus(BaseModel):
    """Enhanced scrape status model with detailed progress"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[ScrapeResponse] = None
    
    # Detailed progress information
    current_stage: Optional[str] = None  # navigation, search, filtering, scrolling, processing
    current_operation: Optional[str] = None  # specific operation being performed
    businesses_processed: Optional[int] = None
    total_businesses_found: Optional[int] = None
    current_business_name: Optional[str] = None
    elapsed_time_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None
    success_count: Optional[int] = None
    failure_count: Optional[int] = None
    last_updated: Optional[str] = None

# In-memory task storage (in production, use Redis or database)
tasks: Dict[str, ScrapeStatus] = {}

def update_task_status(task_id: str, **kwargs):
    """Update task status with detailed progress information"""
    if task_id in tasks:
        # Update timestamp
        kwargs['last_updated'] = datetime.now().isoformat()
        
        # Update elapsed time if task has started
        started_at = tasks[task_id].started_at
        if started_at is not None and 'elapsed_time_seconds' not in kwargs:
            start_time = datetime.fromisoformat(started_at)
            elapsed = (datetime.now() - start_time).total_seconds()
            kwargs['elapsed_time_seconds'] = round(elapsed, 2)
        
        # Update the task with new information
        for key, value in kwargs.items():
            if hasattr(tasks[task_id], key):
                setattr(tasks[task_id], key, value)
        
        logger.debug(f"📊 Updated task {task_id}: {kwargs}")
    else:
        logger.warning(f"⚠️  Attempted to update non-existent task: {task_id}")

def convert_businesses_to_csv(businesses: List[BusinessData]) -> str:
    """Convert business data to CSV format"""
    if not businesses:
        return "No data available"
    
    # Create CSV in memory
    output = io.StringIO()
    
    # Get field names from first business
    fieldnames = [
        'business_name',
        'average_rating', 
        'review_count',
        'business_type',
        'address',
        'phone',
        'website',
        'scraped_time',
        'scraped_index'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write business data
    for business in businesses:
        business_dict = business.dict()
        writer.writerow(business_dict)
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content

def get_download_filename(query: str, format_type: str, scraped_time: str) -> str:
    """Generate a friendly filename for downloads"""
    # Clean query for filename
    clean_query = re.sub(r'[^\w\s-]', '', query)
    clean_query = re.sub(r'[-\s]+', '_', clean_query)
    
    # Clean timestamp
    clean_time = scraped_time.replace(' ', '_').replace(':', '-')
    
    return f"gmaps_{clean_query}_{clean_time}.{format_type}"

class ChromeDriverManager:
    """Context manager for Chrome WebDriver"""
    
    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self.retry_count = 0
        self.max_retries = 3
        logger.info(f"🔧 ChromeDriverManager initialized (headless={headless})")
    
    def __enter__(self):
        """Initialize Chrome driver with retry logic"""
        logger.info("🚀 Starting Chrome WebDriver initialization")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Driver creation attempt {attempt + 1}/{self.max_retries}")
                self.driver = self._create_driver()
                logger.info(f"✅ Chrome WebDriver created successfully on attempt {attempt + 1}")
                return self.driver
            except Exception as e:
                logger.warning(f"❌ Driver creation attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.max_retries - 1:
                    logger.error("💥 Failed to create Chrome WebDriver after all retry attempts")
                    raise
                
                logger.info(f"⏳ Waiting 0.5s before retry attempt {attempt + 2}")
                time.sleep(0.5)  # Wait before retry
        
        raise Exception("Failed to initialize Chrome driver")
    
    def _create_driver(self):
        """Create Chrome driver using exact same options as working script"""
        logger.info("🔧 Configuring Chrome options")
        options = webdriver.ChromeOptions()
        
        # Use exact same options as the working script
        chrome_args = [
            "disable-cookies",
            "disable-extensions", 
            "disable-gpu",
            "disable-infobars",
            "disable-notifications",
            "disable-popup-blocking",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-ipc-flooding-protection",
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--remote-debugging-pipe",
            "--headless"
        ]
        
        for arg in chrome_args:
            options.add_argument(arg)
            logger.debug(f"   Added Chrome argument: {arg}")
        
        # Only add headless if requested
        if self.headless:
            options.add_argument("--headless")
            logger.info("🙈 Running in headless mode")
        else:
            logger.info("👁️  Running with visible browser")
        
        logger.info(f"📊 Total Chrome arguments configured: {len(chrome_args) + (1 if self.headless else 0)}")
        
        # Create driver with configured options
        logger.info("🚗 Creating Chrome WebDriver instance")
        driver = webdriver.Chrome(options=options)
        
        # Log driver capabilities
        logger.info(f"🏷️  Browser version: {driver.capabilities.get('browserVersion', 'Unknown')}")
        logger.info(f"🏷️  ChromeDriver version: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Unknown')}")
        
        return driver
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up Chrome driver"""
        if self.driver:
            try:
                logger.info("🧹 Cleaning up Chrome WebDriver")
                self.driver.quit()
                logger.info("✅ Chrome WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"⚠️  Error during driver cleanup: {str(e)}")
        else:
            logger.warning("⚠️  No driver instance to clean up")


class GoogleMapsScraper:
    """Google Maps business scraper following the exact working workflow"""
    
    def __init__(self, headless: bool = True):
        """Initialize the Google Maps scraper"""
        self.headless = headless
        
        # # Create output directory
        # self.output_dir = Path(CONFIG['output_dir'])
        # self.output_dir.mkdir(exist_ok=True)
        
        logger.info("🚀 Google Maps scraper initialized")
        # logger.info(f"📂 Output directory: {self.output_dir.absolute()}")
        logger.info(f"🎯 Max results limit: {CONFIG['max_results']}")
        logger.info(f"⏱️  Timing config - Implicit wait: {CONFIG['implicit_wait']}s, Explicit wait: {CONFIG['explicit_wait']}s")
        logger.info("🙈 Running in headless mode for optimal performance")
    
    def search_businesses(self, query: str, max_results: Optional[int] = None, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for businesses on Google Maps using the exact working workflow"""
        logger.info("=" * 60)
        logger.info(f"🎯 Starting Google Maps search for: '{query}'")
        
        max_results = max_results or CONFIG['max_results']
        logger.info(f"📊 Target max results: {max_results}")
        businesses = []
        
        scrape_start_time = time.time()
        
        try:
            with ChromeDriverManager(self.headless) as driver:
                wait = WebDriverWait(driver, 10)
                actions = ActionChains(driver)
                
                # Step 1: Navigate to Google Maps
                logger.info("🌐 Step 1: Navigating to Google Maps")
                if task_id:
                    update_task_status(task_id, 
                                     current_stage="navigation",
                                     current_operation="Loading Google Maps",
                                     progress="Navigating to Google Maps")
                
                nav_start = time.time()
                driver.get("https://www.google.com/maps/")
                logger.info(f"✅ Navigation completed in {time.time() - nav_start:.2f}s")
                
                # Step 2: Find search input and enter query
                logger.info(f"🔍 Step 2: Searching for '{query}'")
                if task_id:
                    update_task_status(task_id,
                                     current_stage="search",
                                     current_operation="Entering search query",
                                     progress=f"Searching for '{query}'")
                
                search_start = time.time()
                try:
                    input_element = driver.find_element(By.CSS_SELECTOR, "input.searchboxinput")
                    logger.info("✅ Found search input element")
                    input_element.send_keys(query)
                    logger.info(f"⌨️  Entered query: '{query}'")
                    input_element.send_keys(Keys.ENTER)
                    logger.info("🔍 Submitted search query")
                    time.sleep(5)
                    logger.info(f"✅ Search completed in {time.time() - search_start:.2f}s")
                except Exception as e:
                    logger.error(f"❌ Failed to perform search: {str(e)}")
                    raise
                
                # Step 3: Skipping rating filter - getting all businesses
                logger.info("📋 Step 3: Skipping rating filter to get all businesses")
                if task_id:
                    update_task_status(task_id,
                                     current_stage="preparing",
                                     current_operation="Preparing to load all businesses",
                                     progress="Skipping filters to get comprehensive results")
                
                logger.info("✅ No filtering applied - will scrape all available businesses")
                
                # Step 4: Start processing businesses immediately while scrolling as needed
                logger.info("🏢 Step 4: Processing businesses incrementally from top while scrolling")
                processing_start = time.time()
                successful_extractions = 0
                failed_extractions = 0
                business_index = 0
                processed_businesses = set()  # Track processed businesses by their text/identifier
                scroll_count = 0
                last_business_count = 0
                no_new_businesses_count = 0
                
                logger.info("🔍 Starting immediate business processing from top")
                
                if task_id:
                    update_task_status(task_id,
                                     current_stage="processing",
                                     current_operation="Starting immediate business data extraction",
                                     businesses_processed=0,
                                     success_count=0,
                                     failure_count=0,
                                     progress="Processing businesses from top while scrolling")
                
                while business_index < max_results:
                    # Find current available businesses (fresh query each time)
                    logger.debug(f"🔍 Looking for business #{business_index + 1}")
                    current_businesses = []
                    business_detection_errors = []
                    
                    # Try multiple selectors to find businesses with detailed error logging
                    for selector in ["div.Nv2PK.tH5CWc.THOPZb", "div.Nv2PK.Q2HXcd.THOPZb", "div.Nv2PK.THOPZb.CpccDe"]:
                        try:
                            found_businesses = driver.find_elements(By.CSS_SELECTOR, selector)
                            current_businesses.extend(found_businesses)
                            logger.debug(f"✅ Selector '{selector}' found {len(found_businesses)} businesses")
                        except Exception as e:
                            error_msg = f"❌ Selector '{selector}' failed: {type(e).__name__}: {str(e)}"
                            logger.debug(error_msg)
                            business_detection_errors.append(error_msg)
                    
                    # Log detailed information about business detection
                    logger.debug(f"📊 Total businesses found with all selectors: {len(current_businesses)}")
                    
                    # Check if we have any new businesses
                    if len(current_businesses) == last_business_count:
                        no_new_businesses_count += 1
                        
                        # If no new businesses for 3 consecutive checks, try scrolling
                        if no_new_businesses_count >= 3:
                            # Simple scroll limit to prevent infinite scrolling
                            if scroll_count >= 10:  # Stop after 15 scrolls
                                logger.info(f"🛑 Reached maximum scroll limit ({scroll_count} scrolls)")
                                logger.info(f"✅ Finished processing all available businesses")
                                break
                                
                            logger.info(f"📜 No new businesses found, scrolling to load more...")
                            scroll_count += 1
                            
                            try:
                                actions.send_keys(Keys.END).perform()
                                logger.debug(f"✅ Scroll action #{scroll_count} executed")
                            except Exception as e:
                                logger.error(f"❌ Scroll action #{scroll_count} failed: {type(e).__name__}: {str(e)}")
                                logger.error(f"📍 Scroll error traceback: {traceback.format_exc()}")
                            
                            # Wait a bit for new content to load
                            wait_time = random.randint(1, 3)
                            logger.debug(f"⏳ Waiting {wait_time}s after scroll #{scroll_count}")
                            time.sleep(wait_time)
                            
                            # Update status during scrolling
                            if task_id and scroll_count % 3 == 0:
                                update_task_status(task_id,
                                                 current_operation=f"Scrolling for more businesses... (scroll #{scroll_count})",
                                                 progress=f"Processed {business_index} businesses, scrolling for more...")
                            
                            # Check if we've reached the end with detailed logging
                            try:
                                end_marker = driver.find_element(By.CSS_SELECTOR, "span.HlvSq")
                                logger.info(f"🎯 Reached end of results: '{end_marker.text}'")
                                logger.info(f"✅ Finished processing all available businesses")
                                break
                            except Exception as e:
                                logger.debug(f"📄 No end marker found (continuing): {type(e).__name__}: {str(e)}")
                                # Continue scrolling if no end marker found
                                pass
                            
                            # Reset the counter after scrolling
                            no_new_businesses_count = 0
                            continue
                    else:
                        # We found new businesses, reset counter
                        last_business_count = len(current_businesses)
                        no_new_businesses_count = 0
                    
                    if not current_businesses:
                        # Log detailed error information about WHY no businesses were found
                        logger.error("=" * 80)
                        logger.error("💥 NO BUSINESSES FOUND - DETAILED ANALYSIS")
                        logger.error("=" * 80)
                        logger.error(f"🔍 Business detection attempted for position #{business_index + 1}")
                        logger.error(f"📊 Current business count: {len(current_businesses)}")
                        logger.error(f"📊 Last business count: {last_business_count}")
                        logger.error(f"📊 No new businesses count: {no_new_businesses_count}")
                        logger.error(f"📜 Scroll count: {scroll_count}")
                        logger.error(f"📋 Total processed businesses: {len(processed_businesses)}")
                        
                        if business_detection_errors:
                            logger.error("🚨 Business detection errors encountered:")
                            for error in business_detection_errors:
                                logger.error(f"  • {error}")
                        else:
                            logger.error("✅ No detection errors - selectors ran successfully but returned 0 businesses")
                        
                        # Try to get page source information for debugging
                        try:
                            page_url = driver.current_url
                            page_title = driver.title
                            logger.error(f"🌐 Current page URL: {page_url}")
                            logger.error(f"📄 Current page title: {page_title}")
                            
                            # Check if we're still on a maps page
                            if "google.com/maps" not in page_url:
                                logger.error(f"❌ NOT ON GOOGLE MAPS PAGE! Current URL: {page_url}")
                            
                            # Check for common error elements
                            try:
                                error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .no-results, .empty")
                                if error_elements:
                                    logger.error(f"🚨 Found {len(error_elements)} error/empty result elements on page")
                                    for elem in error_elements[:3]:  # Log first 3
                                        logger.error(f"  • Error element text: '{elem.text}'")
                            except:
                                pass
                                
                        except Exception as debug_error:
                            logger.error(f"❌ Could not get page debug info: {type(debug_error).__name__}: {str(debug_error)}")
                        
                        logger.error("📍 Full current stack trace:")
                        logger.error(''.join(traceback.format_stack()))
                        logger.error("=" * 80)
                        
                        logger.warning("📭 STOPPING: No businesses found on page after detailed analysis")
                        break

                        
                    logger.debug(f"✅ Found {len(current_businesses)} current businesses on page")
                    
                    # Find a business we haven't processed yet
                    current_item = None
                    business_identifier = None
                    
                    for idx, business_element in enumerate(current_businesses):
                        try:
                            # Create a unique identifier for this business to avoid duplicates
                            try:
                                business_link = business_element.find_element(By.CSS_SELECTOR, "a.hfpxzc")
                                business_identifier = business_link.get_attribute("href")
                            except:
                                # Fallback identifier using element text or position
                                business_identifier = f"business_{idx}_{business_element.text[:50] if business_element.text else 'unknown'}"
                            
                            # Skip if we've already processed this business
                            if business_identifier in processed_businesses:
                                continue
                                
                            # This is a new business we can process
                            current_item = business_element
                            break
                            
                        except Exception as e:
                            logger.debug(f"⚠️  Could not get identifier for business {idx}: {str(e)}")
                            continue
                    
                    if not current_item or not business_identifier:
                        # No new businesses found, continue to trigger scrolling logic
                        continue
                    
                    # Mark this business as being processed
                    processed_businesses.add(business_identifier)
                    business_start = time.time()
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            logger.info(f"🔄 Processing business #{business_index + 1} (attempt {retry_count + 1})")
                            
                            # Update status for current business
                            if task_id:
                                estimated_remaining = None
                                if business_index > 0:
                                    elapsed = time.time() - processing_start
                                    avg_time = elapsed / business_index
                                    remaining_businesses = max_results - business_index
                                    estimated_remaining = remaining_businesses * avg_time
                                
                                update_task_status(task_id,
                                                 current_operation=f"Processing business #{business_index + 1}",
                                                 businesses_processed=business_index,
                                                 success_count=successful_extractions,
                                                 failure_count=failed_extractions,
                                                 estimated_remaining_seconds=estimated_remaining,
                                                 progress=f"Extracting data from business #{business_index + 1}")
                            
                            # Extract basic info from listing first
                            logger.debug("📞 Extracting phone number")
                            try:
                                telephone = current_item.find_element(By.CSS_SELECTOR, "span.UsdlK").text
                                logger.debug(f"✅ Phone found: {telephone}")
                            except:
                                telephone = None
                                logger.debug("⚠️  No phone number found")
                                
                            logger.debug("🌐 Extracting website from listing")
                            try:
                                website = current_item.find_element(By.CSS_SELECTOR, "a.lcr4fd.S9kvJb").get_attribute("href")
                                logger.debug(f"✅ Website found: {website}")
                            except:
                                website = False
                                logger.debug("⚠️  No website found in listing")
                                
                            logger.debug("⭐ Extracting review count")
                            try:
                                reviews_text = current_item.find_element(By.CSS_SELECTOR, "span.e4rVHe.fontBodyMedium").text
                                reviews = reviews_text[reviews_text.index("(") + 1:reviews_text.index(")")].replace(",", "")
                                reviews = int(reviews) if reviews.isdigit() else None
                                logger.debug(f"✅ Reviews found: {reviews}")
                            except:
                                reviews = None
                                logger.debug("⚠️  No review count found")
                            
                            # Click on the business link with retry logic
                            logger.debug("🖱️  Clicking business link for details")
                            business_link = None
                            click_attempts = 0
                            max_click_attempts = 3
                            
                            while click_attempts < max_click_attempts:
                                try:
                                    business_link = current_item.find_element(By.CSS_SELECTOR, "a.hfpxzc")
                                    logger.debug("✅ Found business link")
                                    
                                    logger.debug("📜 Scrolling business link into view")
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", business_link)
                                    time.sleep(2)  # Wait for scroll to complete
                                    
                                    # Check if element is still attached to DOM
                                    business_link.tag_name  # Test for staleness
                                    
                                    logger.debug("🖱️  Clicking business link")
                                    driver.execute_script("arguments[0].click();", business_link)  # Use JavaScript click for reliability
                                    logger.debug("✅ Business link clicked successfully")
                                    break
                                    
                                except Exception as click_error:
                                    click_attempts += 1
                                    logger.warning(f"❌ Click attempt {click_attempts} failed: {str(click_error)}")
                                    
                                    if click_attempts >= max_click_attempts:
                                        logger.warning("❌ All click attempts failed")
                                        raise click_error
                                    
                                    # Wait and try to re-find the element
                                    time.sleep(1)
                                    logger.warning("⚠️  Will retry with fresh element search")
                            
                            logger.debug("⏳ Waiting 5s for business details to load")
                            time.sleep(5)  # Wait for details to load
                            
                            # Extract detailed information with error handling
                            logger.debug("📊 Extracting detailed business information")
                            
                            logger.debug("🏷️  Extracting business name")
                            try:
                                business_name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf.lfPIob").text
                                logger.debug(f"✅ Business name: {business_name}")
                            except:
                                business_name = None
                                logger.debug("⚠️  No business name found")
                                
                            logger.debug("⭐ Extracting average rating")
                            try:
                                average_star = driver.find_element(By.CSS_SELECTOR, "div.F7nice span span").text
                                logger.debug(f"✅ Average rating: {average_star}")
                            except:
                                average_star = None
                                logger.debug("⚠️  No average rating found")
                            
                            # Get website if not found in listing
                            if website == False:
                                logger.debug("🌐 Extracting website from details page")
                                try:
                                    website = driver.find_element(By.CSS_SELECTOR, "a.CsEnBe").get_attribute("href")
                                    logger.debug(f"✅ Website from details: {website}")
                                except:
                                    website = None
                                    logger.debug("⚠️  No website found in details")
                            
                            logger.debug("🏢 Extracting business type")
                            try:
                                business_type = driver.find_element(By.CSS_SELECTOR, "button.DkEaL").text
                                logger.debug(f"✅ Business type: {business_type}")
                            except:
                                business_type = None
                                logger.debug("⚠️  No business type found")
                                
                            logger.debug("📍 Extracting address")
                            try:
                                address = driver.find_element(By.CSS_SELECTOR, "div.Io6YTe.fontBodyMedium.kR99db").text
                                logger.debug(f"✅ Address: {address}")
                            except:
                                address = None
                                logger.debug("⚠️  No address found")
                            
                            # Create business data
                            business_details = {
                                "business_name": business_name,
                                "average_rating": average_star,
                                "review_count": reviews,
                                "business_type": business_type,
                                "address": address,
                                "phone": telephone,
                                "website": website,
                                "scraped_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "scraped_index": business_index + 1
                            }
                            
                            if business_name:  # Only add if we got the name
                                businesses.append(business_details)
                                successful_extractions += 1
                                business_time = time.time() - business_start
                                logger.info(f"✅ Successfully scraped '{business_name}' in {business_time:.2f}s")
                                
                                # Update status with current business name
                                if task_id:
                                    update_task_status(task_id,
                                                     current_business_name=business_name,
                                                     success_count=successful_extractions,
                                                     businesses_processed=business_index+1)
                                
                                # Log progress every 10 businesses
                                if successful_extractions % 10 == 0:
                                    elapsed = time.time() - processing_start
                                    avg_time = elapsed / (business_index + 1)
                                    remaining = max_results - (business_index + 1)
                                    eta = remaining * avg_time
                                    logger.info(f"📊 Progress: {successful_extractions} businesses scraped, ETA: {eta:.1f}s")
                            else:
                                failed_extractions += 1
                                logger.warning(f"⚠️  Skipping business #{business_index+1} - no name found")
                                
                                # Update failure count in status
                                if task_id:
                                    update_task_status(task_id,
                                                     failure_count=failed_extractions,
                                                     businesses_processed=business_index+1)
                            
                            # Successfully processed, break retry loop
                            logger.debug("🔙 Navigating back to search results for next business")
                            try:
                                # Go back to search results page to find next business
                                driver.back()
                                logger.debug("✅ Navigated back to search results")
                                
                                # Wait for search results to load
                                time.sleep(2)
                                
                                # Verify we're back on search results (not on a business page)
                                current_url = driver.current_url
                                if "/place/" in current_url:
                                    logger.warning("⚠️  Still on business page after back button, trying alternative navigation")
                                    # Alternative: reload the search URL
                                    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                                    driver.get(search_url)
                                    time.sleep(3)
                                    logger.debug(f"✅ Reloaded search results: {search_url}")
                                
                                logger.debug(f"🌐 Current URL after navigation: {driver.current_url}")
                                
                            except Exception as nav_error:
                                logger.error(f"❌ Navigation back to search results failed: {type(nav_error).__name__}: {str(nav_error)}")
                                logger.error(f"📍 Navigation error traceback: {traceback.format_exc()}")
                                # Try to recover by reloading search results
                                try:
                                    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                                    driver.get(search_url)
                                    time.sleep(3)
                                    logger.info(f"✅ Recovery: Reloaded search results: {search_url}")
                                except Exception as recovery_error:
                                    logger.error(f"❌ Recovery navigation also failed: {str(recovery_error)}")
                                    # This might be a fatal error for continuing
                                    raise recovery_error
                            
                            break
                            
                        except Exception as e:
                            retry_count += 1
                            logger.warning(f"❌ Error processing business #{business_index+1} (attempt {retry_count}): {str(e)}")
                            
                            if retry_count >= max_retries:
                                failed_extractions += 1
                                logger.warning(f"❌ Failed to process business #{business_index+1} after {max_retries} attempts")
                                
                                # Update failure count in status
                                if task_id:
                                    update_task_status(task_id,
                                                     failure_count=failed_extractions,
                                                     businesses_processed=business_index+1,
                                                     current_operation=f"Failed to process business #{business_index+1}")
                                break
                            else:
                                logger.info(f"🔄 Retrying business #{business_index+1} in 2 seconds...")
                                time.sleep(2)  # Wait before retry
                    
                    # Move to next business
                    business_index += 1
                
                # Processing complete
                total_processing_time = time.time() - processing_start
                logger.info("=" * 60)
                logger.info("🎯 SCRAPING SUMMARY")
                logger.info(f"✅ Successfully extracted: {successful_extractions} businesses")
                logger.info(f"❌ Failed extractions: {failed_extractions}")
                logger.info(f"📊 Success rate: {(successful_extractions/(successful_extractions + failed_extractions)*100):.1f}%")
                logger.info(f"⏱️  Processing time: {total_processing_time:.2f}s")
                logger.info(f"⚡ Average time per business: {total_processing_time/(successful_extractions + failed_extractions):.2f}s")
                
        except Exception as e:
            total_scrape_time = time.time() - scrape_start_time
            
            # Log full error details to terminal/logs for debugging
            logger.error("=" * 80)
            logger.error("💥 CRITICAL SCRAPING ERROR - FULL DETAILS BELOW")
            logger.error("=" * 80)
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error(f"❌ Error Message: {str(e)}")
            logger.error(f"🎯 Query: '{query}'")
            logger.error(f"⏱️  Time before failure: {total_scrape_time:.2f}s")
            logger.error(f"📊 Businesses scraped before failure: {len(businesses)}")
            logger.error(f"🔢 Business index when failed: {business_index if 'business_index' in locals() else 'Unknown'}")
            logger.error("📍 Full Traceback:")
            logger.error(traceback.format_exc())
            logger.error("=" * 80)
            
            # Raise a clean error for the API consumer
            raise Exception(f"Unable to complete scraping for '{query}'. Please try again or contact support if the issue persists.")
        
        total_scrape_time = time.time() - scrape_start_time
        logger.info("=" * 60)
        logger.info("🎉 SCRAPING COMPLETED SUCCESSFULLY")
        logger.info(f"🎯 Query: '{query}'")
        logger.info(f"📊 Total businesses scraped: {len(businesses)}")
        logger.info(f"⏱️  Total execution time: {total_scrape_time:.2f}s")
        logger.info(f"📈 Final success rate: {(len(businesses)/business_index*100):.1f}%" if business_index > 0 else "N/A")
        logger.info("=" * 60)
        
        return businesses
    


# Background task function
def scrape_businesses_task(task_id: str, request: ScrapeRequest):
    """Background task to scrape businesses"""
    logger.info(f"🚀 Starting background task {task_id}")
    logger.info(f"📋 Task parameters: query='{request.query}', max_results={request.max_results}")
    
    try:
        # Update task status
        logger.info(f"📊 Updating task {task_id} status to 'running'")
        tasks[task_id].status = "running"
        tasks[task_id].started_at = datetime.now().isoformat()
        
        start_time = time.time()
        
        # Initialize scraper and perform scraping (always headless)
        logger.info(f"🔧 Initializing GoogleMapsScraper for task {task_id} (headless mode)")
        scraper = GoogleMapsScraper(headless=True)
        
        logger.info(f"🎯 Starting scraping process for task {task_id}")
        businesses = scraper.search_businesses(
            query=request.query,
            max_results=request.max_results,
            task_id=task_id
        )
        
        execution_time = time.time() - start_time
        logger.info(f"✅ Task {task_id} scraping completed in {execution_time:.2f}s")
        
        # Check if no businesses were found
        if len(businesses) == 0:
            logger.info(f"📭 Task {task_id} completed but no listings found")
            
            # Still create a successful response but with specific message
            response = ScrapeResponse(
                success=True,
                query=request.query,
                scraped_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_results=0,
                execution_time_seconds=round(execution_time, 2),
                businesses=[],
                message=f"No listings found for '{request.query}'. Try a different search term or location."
            )
            
            # Update task with result
            update_task_status(task_id,
                             status="completed",
                             completed_at=datetime.now().isoformat(),
                             current_stage="completed",
                             current_operation="Search completed - no listings found",
                             progress=f"No businesses found for '{request.query}'",
                             businesses_processed=0,
                             total_businesses_found=0,
                             current_business_name=None,
                             estimated_remaining_seconds=0)
            tasks[task_id].result = response
            return
        
        # Generate download URLs for async task (only if businesses found)
        download_urls = {
            "json": f"/gmaps/download/{task_id}?format=json",
            "csv": f"/gmaps/download/{task_id}?format=csv"
        }
        
        # Create response
        response = ScrapeResponse(
            success=True,
            query=request.query,
            scraped_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_results=len(businesses),
            execution_time_seconds=round(execution_time, 2),
            businesses=[BusinessData(**business) for business in businesses],
            message=f"Successfully scraped {len(businesses)} businesses",
            download_urls=download_urls
        )
        
        # Update task with result
        logger.info(f"📊 Task {task_id} completed successfully - {len(businesses)} businesses scraped")
        logger.info(f"📥 Download URLs created - JSON: {download_urls['json']}, CSV: {download_urls['csv']}")
        update_task_status(task_id,
                         status="completed",
                         completed_at=datetime.now().isoformat(),
                         current_stage="completed",
                         current_operation="Scraping completed successfully",
                         progress=f"Successfully scraped {len(businesses)} businesses",
                         businesses_processed=len(businesses),
                         current_business_name=None,
                         estimated_remaining_seconds=0)
        tasks[task_id].result = response
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        # Log full error details to terminal/logs for debugging
        logger.error("=" * 80)
        logger.error(f"💥 BACKGROUND TASK {task_id} FAILED - FULL ERROR DETAILS")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error(f"🎯 Query: '{request.query}'")
        logger.error(f"🔢 Max Results: {request.max_results}")
        logger.error(f"⏱️  Execution time before failure: {execution_time:.2f}s")
        logger.error(f"📊 Task ID: {task_id}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Determine user-friendly error message based on error type
        if "No such element" in str(e) or "NoSuchElementException" in str(e):
            user_message = f"No listings found for '{request.query}'. The search might not have returned any results, or the page structure has changed. Please try a different search term."
        elif "TimeoutException" in str(e) or "timeout" in str(e).lower():
            user_message = f"The search for '{request.query}' took too long to complete. Please try again or use a more specific search term."
        elif "WebDriverException" in str(e):
            user_message = f"There was a technical issue with the browser while searching for '{request.query}'. Please try again in a few moments."
        elif "Unable to complete scraping" in str(e):
            user_message = str(e)  # This is already user-friendly from the search_businesses method
        else:
            user_message = f"We encountered an issue while searching for '{request.query}'. Please try again or contact support if the problem persists."
        
        update_task_status(task_id,
                         status="failed",
                         completed_at=datetime.now().isoformat(),
                         current_stage="failed",
                         current_operation="Scraping failed",
                         progress=user_message,
                         current_business_name=None,
                         estimated_remaining_seconds=0)
        
        tasks[task_id].result = ScrapeResponse(
            success=False,
            query=request.query,
            scraped_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_results=0,
            execution_time_seconds=round(execution_time, 2),
            businesses=[],
            message=user_message
        )

# API Endpoints
@router.get("/", summary="API Information")
async def get_api_info():
    """Get Google Maps scraper API information"""
    logger.info("🌐 API ENDPOINT: / (API Info)")
    logger.info("📥 API information request received")

    # Inline health status information (previously returned by /health)
    health_status = {
        "status": "healthy",
        "service": "Google Maps Business Scraper API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Service is running",
    }

    api_info = {
        "service": "Google Maps Business Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Start business scraping (asynchronous)",
            "/result/{task_id}": "Get task status or paginated scraping results",
            "/download/{task_id}": "Download full results as JSON or CSV file",
            "/health": "Health check endpoint",
        },
        "example_query": "car companies in London",
        # Example of the final result payload (ScrapeResponse) once scraping is complete
        "result_example_response": {
            "success": True,
            "query": "car companies in London",
            "scraped_time": "2025-01-01 12:00:00",
            "total_results": 2,
            "execution_time_seconds": 12.34,
            "businesses": [
                {
                    "business_name": "Prime Motors London",
                    "average_rating": "4.6",
                    "review_count": 124,
                    "business_type": "Car dealer",
                    "address": "221B Baker Street, London, UK",
                    "phone": "+44 20 0000 0000",
                    "website": "https://primemotors.example.com",
                    "scraped_time": "2025-01-01 12:00:00",
                    "scraped_index": 1,
                },
                {
                    "business_name": "City Auto London",
                    "average_rating": "4.2",
                    "review_count": 87,
                    "business_type": "Car dealer",
                    "address": "10 Downing Street, London, UK",
                    "phone": "+44 20 1111 1111",
                    "website": "https://cityauto.example.com",
                    "scraped_time": "2025-01-01 12:00:01",
                    "scraped_index": 2,
                },
            ],
            "message": "Successfully scraped 2 businesses",
            "download_urls": {
                "json": "/gmaps/download/{task_id}?format=json",
                "csv": "/gmaps/download/{task_id}?format=csv",
            },
        },
        "health": health_status,
    }
    
    logger.info("📤 API information response ready")
    return api_info

@router.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint for Google Maps API"""
    logger.info("🌐 API ENDPOINT: /health (Health Check)")
    logger.info("📥 Health check request received")

    health_status = {
        "status": "healthy",
        "service": "Google Maps Business Scraper API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Service is running",
    }

    logger.info("✅ Health check completed successfully")

    return health_status


@router.get("/search", summary="Scrape Businesses (Async)")
async def scrape_businesses_async(
    background_tasks: BackgroundTasks, 
    query: str = Query(..., description="Search query (e.g., 'hair salons in London')"),
    max_results: int = Query(default=100, description="Maximum number of results to scrape", ge=1, le=10000)
):
    """
    Asynchronously scrape businesses from Google Maps
    
    Returns a task ID that can be used to check the status and get results.
    
     - **query**: Search query (e.g., "hair salons in London")
     - **max_results**: Maximum number of results (1-10000)

    """
    logger.info("🌐 API ENDPOINT: /search (asynchronous GET)")
    logger.info(f"📥 Incoming async GET request: query='{query}', max_results={max_results}")
    
    try:
        import uuid
        
        # Create ScrapeRequest object from query parameters
        request = ScrapeRequest(query=query, max_results=max_results)
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated task ID: {task_id}")
        
        # Create task status
        logger.info(f"📊 Creating task status for {task_id}")
        tasks[task_id] = ScrapeStatus(
            task_id=task_id,
            status="pending",
            progress=f"Queued scraping for query: {request.query}",
            current_stage="pending",
            current_operation="Task queued",
            businesses_processed=0,
            total_businesses_found=None,
            current_business_name=None,
            elapsed_time_seconds=0,
            estimated_remaining_seconds=None,
            success_count=0,
            failure_count=0,
            last_updated=datetime.now().isoformat()
        )
        
        # Add background task
        logger.info(f"⏰ Adding background task {task_id} to queue")
        background_tasks.add_task(scrape_businesses_task, task_id, request)
        
        logger.info(f"✅ Async task {task_id} queued successfully for query: '{request.query}'")
        
        response = {
            "task_id": task_id,
            "status": "pending",
            "message": "Scraping task queued successfully",
            "query": request.query,
            "status_url": f"/gmaps/result/{task_id}"
        }
        
        logger.info(f"📤 Async response ready: task_id={task_id}")
        return response
        
    except Exception as e:
        # Log full error details to terminal
        logger.error("=" * 80)
        logger.error("💥 SCRAPE ENDPOINT ERROR - FAILED TO QUEUE TASK")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error(f"🎯 Query: '{query}'")
        logger.error(f"🔢 Max Results: {max_results}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Return user-friendly error
        raise HTTPException(
            status_code=500,
            detail=f"Unable to start scraping task for '{query}'. Please try again or contact support if the issue persists."
        )

@router.get("/result/{task_id}", summary="Get Task Result or Status (Paginated)")
async def get_task_result(
    task_id: str,
    page: int = Query(1, ge=1, description="Page number for paginated results"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of records per page"),
):
    """Get the status of a scraping task or paginated results if completed"""
    logger.info(f"🌐 API ENDPOINT: /result/{task_id}")
    logger.info(f"📥 Result request for task: {task_id}, page={page}, page_size={page_size}")
    
    try:
        if task_id not in tasks:
            logger.warning(f"❌ Task {task_id} not found in task storage")
            raise HTTPException(
                status_code=404,
                detail=f"Task '{task_id}' not found. Please check your task ID or start a new scraping task."
            )
        
        task_status = tasks[task_id]
        logger.info(f"📊 Task {task_id} status: {task_status.status}")
        
        # If task is not completed yet, return status-style payload with run stats
        if task_status.status != "completed" or not task_status.result:
            logger.info(f"⏳ Task {task_id} not completed yet - returning status")
            return {
                "task_id": task_status.task_id,
                "status": task_status.status,
                "progress": task_status.progress,
                "current_stage": task_status.current_stage,
                "current_operation": task_status.current_operation,
                "businesses_processed": task_status.businesses_processed,
                "total_businesses_found": task_status.total_businesses_found,
                "success_count": task_status.success_count,
                "failure_count": task_status.failure_count,
                "started_at": task_status.started_at,
                "completed_at": task_status.completed_at,
                "last_updated": task_status.last_updated,
            }
        
        # Task is completed - return paginated data
        result = task_status.result
        total_results = result.total_results or len(result.businesses)
        total_pages = (total_results + page_size - 1) // page_size if total_results else 1
        
        if page > total_pages and total_results != 0:
            logger.warning(f"❌ Page {page} out of range for task {task_id} (total_pages={total_pages})")
            raise HTTPException(
                status_code=400,
                detail=f"Page {page} is out of range. Total pages: {total_pages}."
            )
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        businesses_slice = result.businesses[start_idx:end_idx]
        
        logger.info(f"📦 Returning page {page}/{total_pages} for task {task_id}")
        
        return {
            "task_id": task_id,
            "status": task_status.status,
            "query": result.query,
            "scraped_time": result.scraped_time,
            "total_results": total_results,
            "execution_time_seconds": result.execution_time_seconds,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "results": [business.dict() for business in businesses_slice],
            "message": result.message,
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as is
        raise
    except Exception as e:
        # Log full error details to terminal
        logger.error("=" * 80)
        logger.error(f"💥 RESULT ENDPOINT ERROR for task {task_id}")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Return user-friendly error
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve task result. Please try again or contact support if the issue persists."
        )


@router.get("/download/{task_id}", summary="Download Full Results as JSON or CSV File")
async def download_results(
    task_id: str,
    format: str = Query("json", regex="^(json|csv)$", description="Download format: 'json' or 'csv'"),
):
    """Download full scraping results as a JSON or CSV file"""
    logger.info(f"🌐 API ENDPOINT: /download/{task_id}")
    logger.info(f"📥 Download request for task: {task_id}, format={format}")
    
    try:
        if task_id not in tasks:
            logger.warning(f"❌ Task {task_id} not found for download")
            raise HTTPException(
                status_code=404,
                detail=f"Task '{task_id}' not found. Please check your task ID."
            )
        
        task = tasks[task_id]
        
        if task.status != "completed" or not task.result:
            logger.warning(f"❌ Task {task_id} not completed or has no results")
            raise HTTPException(
                status_code=400,
                detail=f"Task '{task_id}' is not completed yet or has no results. Please check the task result first."
            )
        
        result = task.result
        
        # Generate filename
        filename = get_download_filename(result.query, format, result.scraped_time)
        
        if format == "json":
            # Convert to JSON
            businesses_data = [business.dict() for business in result.businesses]
            
            download_data = {
                "query": result.query,
                "scraped_time": result.scraped_time,
                "total_results": result.total_results,
                "execution_time_seconds": result.execution_time_seconds,
                "businesses": businesses_data,
                "download_info": {
                    "format": "JSON",
                    "download_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "task_id": task_id
                }
            }
            
            # Create JSON content
            json_content = json.dumps(download_data, indent=2, ensure_ascii=False)
            
            logger.info(f"📦 JSON download ready for task {task_id}: {len(result.businesses)} businesses")
            logger.info(f"📁 Filename: {filename}")
            
            # Return file response
            return Response(
                content=json_content,
                media_type='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'application/json; charset=utf-8'
                }
            )
        
        # CSV download
        csv_content = convert_businesses_to_csv(result.businesses)
        
        logger.info(f"📤 CSV download ready: {len(result.businesses)} businesses, filename: {filename}")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as is
        raise
    except Exception as e:
        # Log full error details to terminal
        logger.error("=" * 80)
        logger.error(f"💥 DOWNLOAD ENDPOINT ERROR for task {task_id}")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error(f"📊 Task ID: {task_id}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Return user-friendly error
        raise HTTPException(
            status_code=500,
            detail="Unable to generate download. Please try again or contact support if the issue persists."
        )

@router.delete("/tasks", summary="Clear Completed Tasks")
async def clear_tasks():
    """Clear all completed and failed tasks"""
    logger.info("🌐 API ENDPOINT: /tasks (DELETE)")
    logger.info("📥 Task cleanup request received")
    
    global tasks
    
    before_count = len(tasks)
    logger.info(f"📊 Tasks before cleanup: {before_count}")
    
    # Count tasks by status before cleanup
    status_counts = {}
    for task in tasks.values():
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
    logger.info(f"📊 Task breakdown: {status_counts}")
    
    tasks = {
        task_id: task for task_id, task in tasks.items()
        if task.status in ["pending", "running"]
    }
    after_count = len(tasks)
    cleared_count = before_count - after_count
    
    logger.info(f"🧹 Cleared {cleared_count} completed/failed tasks")
    logger.info(f"📊 Remaining active tasks: {after_count}")
    
    response = {
        "message": f"Cleared {cleared_count} completed/failed tasks",
        "remaining_tasks": after_count
    }
    
    logger.info("📤 Task cleanup response ready")
    return response 