import time
import multiprocessing
import json
import random
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('amazon_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("🚀 Amazon Search API module loaded")

# Create API router
router = APIRouter()

# Configuration
CONFIG = {
    'base_url': 'http://www.amazon.com/',
    'currency': 'USD',
    'max_workers': 10,
    'batch_size': 10,
    'headless_mode': True,
    'verbose_logging': False,
    'implicit_wait': 1,
    'explicit_wait': 1
}

# In-memory storage for background tasks
tasks: Dict[str, Dict[str, Any]] = {}

# Pydantic models
class SellerInfo(BaseModel):
    """Seller information model"""
    name: str
    url: Optional[str] = None

class RatingInfo(BaseModel):
    """Rating information model"""
    rating: Optional[float] = None
    rating_count: int = 0

class CategoriesInfo(BaseModel):
    """Categories information model"""
    text_path: str = ""
    url_path: str = ""

class DescriptionInfo(BaseModel):
    """Product description model"""
    full_text: str = ""
    features: List[Dict[str, str]] = []
    sections: Dict[str, str] = {}

class ProductData(BaseModel):
    """Product data model"""
    asin: str
    url: str
    title: str
    seller: SellerInfo
    price: Optional[float] = None
    ranks: Dict[str, int] = {}
    rating: RatingInfo
    details: Dict[str, Any] = {}
    categories: CategoriesInfo
    description: DescriptionInfo
    scraped_at: str

class SearchStatus(BaseModel):
    """Search task status model"""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    current_stage: str
    current_operation: str
    products_processed: int = 0
    total_products_found: Optional[int] = None
    current_product_title: Optional[str] = None
    elapsed_time_seconds: float = 0
    estimated_remaining_seconds: Optional[float] = None
    success_count: int = 0
    failure_count: int = 0
    last_updated: str
    results: Optional[List[ProductData]] = None


class AmazonScraper:
    def __init__(self, search_term, base_url=None, currency=None, max_products=10):
        self.base_url = base_url or CONFIG['base_url']
        self.search_term = search_term
        self.currency = currency or CONFIG['currency']
        self.max_products = max_products
        self.driver = None
        self.wait = None
        
    def _init_webdriver(self):
        """Initialize WebDriver only when needed"""
        if self.driver is not None:
            return
            
        # Setup webdriver
        options = webdriver.ChromeOptions()
        # Block notifications
        options.add_argument('--disable-notifications')
        # Block popups
        options.add_argument('--disable-popup-blocking')
        # Block cookie warnings
        options.add_argument('--disable-infobars')
        # Set language to English
        options.add_argument('--lang=en-US')
        # Set location to US
        options.add_argument('--geolocation=US')
        options.add_argument('--accept-lang=en-US,en;q=0.9')
        # Disable location services
        options.add_argument('--disable-location-services')
        # Disable geolocation
        options.add_argument('--disable-geolocation')
        # Set timezone
        options.add_argument('--timezone=America/New_York')
        # Disable save password prompts
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            # Disable location prompts
            "profile.default_content_setting_values.geolocation": 2,
            # Disable translation prompts
            "translate_whitelists": {},
            "translate.enabled": False,
            # Block third-party cookies
            "profile.block_third_party_cookies": True,
            # Disable 'Chrome is being controlled by automated software' banner
            "useAutomationExtension": False,
            # Accept cookies by default to avoid cookie prompts
            "profile.default_content_settings.cookies": 1,
            "profile.default_content_setting_values.cookies": 1,
            # Disable all permission prompts
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.protocol_handlers": 2,
            # Set default location to US
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_settings.geolocation": 1,
            # Set timezone
            "profile.default_content_setting_values.timezone": 1,
            "profile.default_content_settings.timezone": 1,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Add additional arguments for stability and speed
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-css')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--memory-pressure-off')
        # Set a custom user agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--incognito')
        
        # Add headless mode for speed
        if CONFIG['headless_mode']:
            options.add_argument('--headless')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, CONFIG['explicit_wait'])
        
    def log(self, message, level="info"):
        """Conditional logging based on VERBOSE_LOGGING setting"""
        if CONFIG['verbose_logging'] or level == "error" or level == "success":
            logger.info(message)
        
            
    def append_to_report(self, product):
        try:
            with open(self.report_file, 'a') as f:
                json.dump(product, f, indent=2)
                
        except Exception as e:
            print(f"Error appending to report: {e}")

    def is_sponsored_ad(self, product_element):
        """Check if a product element is a sponsored ad"""
        try:
            # Check for sponsored text in the element
            if "sponsored" in product_element.text.lower():
                return True
                
            return False
            
        except Exception as e:
            # If we can't determine, assume it's not an ad
            return False

    def run(self, use_parallel=True):
        links = self.get_products_links()
        if not links:
            return
        
        
        # Extract ASINs from links
        asins = []
        for link in links:
            asin = self.get_asin(link)
            if asin:
                asins.append(asin)
        
        if use_parallel and len(asins) > 1:
            self.process_products_parallel(asins)
        else:
            self.process_products_sequential(asins)
        
        self.driver.quit()
    
    def process_products_sequential(self, asins):
        """Process products one by one (original method)"""
        
        for i, asin in enumerate(asins, 1):
            try:
                product = self.get_single_product_info(asin)
                if product:
                    self.append_to_report(product)
            except Exception as e:
                continue
    
    def process_products_parallel(self, asins):
        """Process products in parallel using multiprocessing"""
        
        # Process in batches to avoid memory issues
        all_results = []
        for i in range(0, len(asins), BATCH_SIZE):
            batch = asins[i:i + BATCH_SIZE]
            
            # Create process pool
            with multiprocessing.Pool(processes=MAX_WORKERS) as pool:
                # Prepare arguments for each worker
                worker_args = [
                    (asin, self.search_term, self.base_url, self.currency)
                    for asin in batch
                ]
                
                # Process batch in parallel
                results = pool.starmap(process_single_product, worker_args)
                all_results.extend(results)
                
                # Process results and save successful ones
                successful_count = 0
                for result in results:
                    if result['success'] and result['data']:
                        self.append_to_report(result['data'])
                        successful_count += 1
                    else:
                        print(f"✗ Worker {result['worker_id']} failed {result['asin']}: {result.get('error', 'Unknown error')}")
                
        
        # Summary
        total_successful = sum(1 for r in all_results if r['success'])
        print(f"\n=== PARALLEL PROCESSING SUMMARY ===")
        print(f"Total products: {len(asins)}")
        print(f"Successful: {total_successful}")
        print(f"Failed: {len(asins) - total_successful}")
        print(f"Success rate: {total_successful/len(asins)*100:.1f}%")

    def get_products_links(self):
        self._init_webdriver()
        self.driver.get(self.base_url)
        
        self.check_and_click_continue_shopping()
        
        all_links = []
        ads_skipped = 0
        try:
            # Wait for search box and enter search term
            search_box = self.wait.until(
                EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
            )
            search_box.send_keys(self.search_term)
            search_box.send_keys(Keys.ENTER)
            # time.sleep(2)  # Short wait for search results


            page_num = 1
            max_pages = 50  # Safety limit to prevent infinite loops
            reached_last_page = False
            while page_num <= max_pages and not reached_last_page:
                # Wait for search results to load
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
                )

                # Get all product cards on current page
                products = self.driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
                
                # Debug: Print all elements with data-component-type to see what we're getting
                if len(products) == 0:
                    # Try alternative selectors for single products
                    alternative_products = self.driver.find_elements(By.CSS_SELECTOR, "[data-asin]")
                    
                    for i, alt_product in enumerate(alternative_products):
                        try:
                            asin = alt_product.get_attribute('data-asin')
                            
                            # Check if this alternative product is a sponsored ad
                            if self.is_sponsored_ad(alt_product):
                                ads_skipped += 1
                                continue
                            
                            # Try to find a link within this element
                            try:
                                link_element = alt_product.find_element(By.CSS_SELECTOR, "a[href*='/dp/']")
                                link = link_element.get_attribute('href')
                                if link:
                                    all_links.append(link)
                            except NoSuchElementException:
                                print(f"  ✗ No /dp/ link found in alternative product {i+1}")
                        except Exception as e:
                            print(f"  ✗ Error processing alternative product {i+1}: {e}")
                
                # Extract links from current page
                for i, product in enumerate(products):
                    # Check if we've reached the product limit
                    if self.max_products and len(all_links) >= self.max_products:
                        break
                        
                    try:
                        self.log(f"Processing product {i+1}...")
                        
                        # Check if this product is a sponsored ad
                        if self.is_sponsored_ad(product):
                            self.log(f"  ⚠️ Skipped product {i+1} - detected as sponsored ad", "success")
                            ads_skipped += 1
                            continue
                        
                        # Find the product link using the updated selector
                        link = product.find_element(
                            By.CSS_SELECTOR, 
                            "a.a-link-normal.s-line-clamp-2.s-link-style.a-text-normal"
                        ).get_attribute('href')
                        
                        if link and "/dp/" in link:  # Ensure it's a product link
                            all_links.append(link)
                            self.log(f"  ✓ Added product link {i+1}: {link[:50]}...", "success")
                        else:
                            self.log(f"  ✗ Skipped product {i+1} - not a valid product link")
                    except Exception as e:
                        # Try alternative link selectors for this product
                        try:
                            alt_link = product.find_element(By.CSS_SELECTOR, "a[href*='/dp/']").get_attribute('href')
                            if alt_link:
                                all_links.append(alt_link)
                        except NoSuchElementException:
                            print(f"  ✗ No alternative link found for product {i+1}")
                        continue

                # Check if we've reached the product limit after processing this page
                if self.max_products and len(all_links) >= self.max_products:
                    break
                
                # Try to construct next page URL manually
                current_url = self.driver.current_url
                
                # Check if URL already has page parameter
                if '&page=' in current_url or '?page=' in current_url:
                    # Extract current page number and increment
                    page_match = re.search(r'[?&]page=(\d+)', current_url)
                    if page_match:
                        current_page = int(page_match.group(1))
                        next_page = current_page + 1
                        
                        # Replace page number in URL
                        if '&page=' in current_url:
                            next_url = re.sub(r'&page=\d+', f'&page={next_page}', current_url)
                        else:
                            next_url = re.sub(r'\?page=\d+', f'?page={next_page}', current_url)
                        
                        
                        # Try to navigate to next page
                        try:
                            self.driver.get(next_url)
                            
                            # Check if we got new content (not an error page)
                            if "error" not in self.driver.title.lower() and "not found" not in self.driver.title.lower():
                                page_num += 1
                                continue
                            else:
                                break
                        except Exception as e:
                            break
                    else:
                        break
                else:
                    # No page parameter, try adding ?page=2
                    if '?' in current_url:
                        next_url = current_url + '&page=2'
                    else:
                        next_url = current_url + '?page=2'
                    
                    
                    try:
                        self.driver.get(next_url)
                        
                        # Check if we got new content
                        if "error" not in self.driver.title.lower() and "not found" not in self.driver.title.lower():
                            page_num += 1
                            continue
                        else:
                            break
                    except Exception as e:
                        break
                
                # If we reach here, we couldn't construct a valid next page URL
                break
            
            if page_num > max_pages:
                print(f"⚠️ Reached maximum page limit ({max_pages}) - stopping to prevent infinite loop")

            return all_links
        except Exception as e:
            return []

    def get_products_info(self, links):
        asins = self.get_asins(links)
        products = []
        for asin in asins:
            product = self.get_single_product_info(asin)
            if product:
                products.append(product)
        return products

    def get_asins(self, links):
        return [self.get_asin(link) for link in links if link]

    def get_product_details(self):
        try:
            details = {}
            
            # First try the bullet list format
            try:
                details_list = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "ul.a-unordered-list.a-nostyle.a-vertical.a-spacing-none.detail-bullet-list"
                )
                
                list_items = details_list.find_elements(By.CSS_SELECTOR, "li span.a-list-item")
                if list_items:  # Only process if we found items
                    for item in list_items:
                        try:
                            label_element = item.find_element(By.CSS_SELECTOR, "span.a-text-bold")
                            value_element = item.find_elements(By.CSS_SELECTOR, "span")[-1]
                            
                            label = label_element.text.strip().rstrip('‏:‎').strip()
                            
                            try:
                                value = value_element.find_element(By.CSS_SELECTOR, "a").text.strip()
                            except NoSuchElementException:
                                value = value_element.text.strip()
                            
                            if label and value:
                                details[label] = value
                                
                        except Exception as e:
                            continue
            except NoSuchElementException:
                # Bullet list format not found, continue to table format
                pass
            
            # If bullet list was empty or not found, try the table format
            if not details:
                try:
                    details_table = self.driver.find_element(
                        By.ID,
                        "productDetails_detailBullets_sections1"
                    )
                    
                    rows = details_table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        try:
                            # Get header (label) and data (value) cells
                            header = row.find_element(By.TAG_NAME, "th")
                            data = row.find_element(By.TAG_NAME, "td")
                            
                            # Special handling for Best Sellers Rank
                            if "Best Sellers Rank" in header.text:
                                ranks = {}
                                rank_items = data.find_elements(By.CSS_SELECTOR, "ul li span.a-list-item")
                                for rank_item in rank_items:
                                    try:
                                        rank_text = rank_item.text
                                        if '#' in rank_text:
                                            category = rank_text.split(' in ', 1)[1].split('(')[0].strip()
                                            rank_number = int(rank_text.split('#')[1].split(' in ')[0].replace(',', ''))
                                            ranks[category] = rank_number
                                    except Exception as e:
                                        continue
                                if ranks:
                                    details["Best Sellers Rank"] = ranks
                                continue
                            
                            # Special handling for Customer Reviews
                            if "Customer Reviews" in header.text:
                                continue  # Skip as we already handle this in get_rating_info()
                            
                            label = header.text.strip()
                            value = data.text.strip()
                            
                            # Try to find links in the value
                            try:
                                link = data.find_element(By.TAG_NAME, "a")
                                value = link.text.strip()
                            except NoSuchElementException:
                                pass
                            
                            if label and value:
                                details[label] = value
                                
                        except Exception as e:
                            continue
                            
                except NoSuchElementException:
                    print("Product details table not found")
                except Exception as e:
                    print(f"Error processing details table: {e}")
            
            return details if details else None
            
        except Exception as e:
            return None

    def get_categories(self):
        try:
            categories = {
                'text_path': '',
                'url_path': ''
            }
            
            # Find the breadcrumb navigation
            breadcrumb = self.driver.find_element(
                By.CSS_SELECTOR,
                "ul.a-unordered-list.a-horizontal.a-size-small"
            )
            
            # Get all category links (excluding dividers)
            category_items = breadcrumb.find_elements(
                By.CSS_SELECTOR,
                "li:not([class='a-breadcrumb-divider']) span.a-list-item a"
            )
            
            if category_items:
                # Build the category paths
                category_names = []
                category_urls = []
                
                for item in category_items:
                    try:
                        name = item.text.strip()
                        url = item.get_attribute('href')
                        if name and url:  # Only add if both name and url are present
                            category_names.append(name)
                            category_urls.append(url)
                    except Exception as e:
                        continue
                
                # Join the categories with '>'
                categories['text_path'] = ' > '.join(category_names)
                categories['url_path'] = ' > '.join(category_urls)
                
            return categories
            
        except NoSuchElementException:
            return {'text_path': '', 'url_path': ''}
        except Exception as e:
            return {'text_path': '', 'url_path': ''}

    def get_product_description(self):
        try:
            description = {
                'full_text': '',
                'features': [],
                'sections': {}
            }
            
            # Find the product description div
            desc_div = self.driver.find_element(
                By.ID,
                "productDescription"
            )
            
            if desc_div:
                # Get all paragraphs and lists
                elements = desc_div.find_elements(By.CSS_SELECTOR, "p, ul")
                
                current_section = "main"
                current_text = []
                
                for element in elements:
                    try:
                        # Handle different element types
                        if element.tag_name == 'ul':
                            # Get all list items
                            items = element.find_elements(By.CSS_SELECTOR, "li span.a-list-item")
                            for item in items:
                                try:
                                    # Try to get bold text (feature title) and regular text
                                    bold = item.find_element(By.CSS_SELECTOR, "span.a-text-bold").text.strip()
                                    text = item.text.replace(bold, '', 1).strip()
                                    
                                    # Add to features list
                                    description['features'].append({
                                        'title': bold.rstrip(' -'),
                                        'description': text.lstrip(' -')
                                    })
                                except NoSuchElementException:
                                    # If no bold text, just add the whole text as a feature
                                    text = item.text.strip()
                                    if text:
                                        description['features'].append({
                                            'title': '',
                                            'description': text
                                        })
                                except Exception as e:
                                    continue
                                    
                        elif element.tag_name == 'p':
                            # Process paragraph text
                            spans = element.find_elements(By.CSS_SELECTOR, "span")
                            for span in spans:
                                try:
                                    text = span.text.strip()
                                    if text:
                                        # Check if this is a section header
                                        class_attr = span.get_attribute('class') or ""
                                        is_bold = 'a-text-bold' in class_attr
                                        is_underlined = span.find_elements(By.TAG_NAME, "u")
                                        
                                        if is_bold and is_underlined:
                                            # This is a new section header
                                            if current_text:
                                                # Save the previous section
                                                description['sections'][current_section] = ' '.join(current_text).strip()
                                                current_text = []
                                            current_section = text.replace('\u200b', '').strip()
                                        else:
                                            # Add to current section text
                                            current_text.append(text)
                                            
                                except Exception as e:
                                    continue
                                    
                    except Exception as e:
                        continue
                
                # Save the last section
                if current_text:
                    description['sections'][current_section] = ' '.join(current_text).strip()
                
                # Create full text by combining all sections
                full_text_parts = []
                for section, text in description['sections'].items():
                    if section != "main":
                        full_text_parts.append(f"{section}\n{text}")
                    else:
                        full_text_parts.append(text)
                
                description['full_text'] = '\n\n'.join(full_text_parts)
                
            return description
            
        except NoSuchElementException:
            return {'full_text': '', 'features': [], 'sections': {}}
        except Exception as e:
            return {'full_text': '', 'features': [], 'sections': {}}

    def check_and_click_continue_shopping(self):
        """Fast continue shopping button check - only essential logging"""
        try:
            # Quick check for continue shopping form
            form = self.driver.find_element(By.CSS_SELECTOR, "form[action='/errors/validateCaptcha']")
            
            # Look for button with most common selector first
            try:
                button = form.find_element(By.CSS_SELECTOR, "button[alt='Continue shopping']")
                button.click()
                self.log("✓ Continue shopping button clicked", "success")
                return True
            except NoSuchElementException:
                pass
            
            # Try alternative selectors quickly
            alternative_selectors = [
                "button[type='submit'][alt='Continue shopping']",
                ".a-button-text[alt='Continue shopping']",
                "//button[@alt='Continue shopping']"
            ]
            
            for selector in alternative_selectors:
                try:
                    if selector.startswith("//"):
                        button = form.find_element(By.XPATH, selector)
                    else:
                        button = form.find_element(By.CSS_SELECTOR, selector)
                    button.click()
                    self.log("✓ Continue shopping button clicked", "success")
                    return True
                except:
                    continue
                    
        except NoSuchElementException:
            # No continue shopping needed - already on product page
            pass
        except Exception as e:
            self.log(f"✗ Error in continue shopping check: {e}", "error")
            
        return False

    def get_single_product_info(self, asin):
        self._init_webdriver()
        product_short_url = self.shorten_url(asin)
        self.driver.get(f'{product_short_url}?language=en_GB')
        # time.sleep(2)

        # Check for and click "Continue shopping" button if present
        self.check_and_click_continue_shopping()

        try:
            print("Step 1: Getting title...")
            title = self.get_title()
            print(f"Title result: {title}")
            
            print("Step 2: Getting seller...")
            seller_info = self.get_seller()
            print(f"Seller result: {seller_info}")
            
            print("Step 3: Getting price...")
            price = self.get_price()
            print(f"Price result: {price}")
            
            print("Step 4: Getting ranks...")
            ranks = self.get_ranks()
            print(f"Ranks result: {ranks}")
            
            print("Step 5: Getting rating info...")
            rating_info = self.get_rating_info()
            print(f"Rating result: {rating_info}")
            
            print("Step 6: Getting product details...")
            product_details = self.get_product_details()
            print(f"Product details result: {product_details}")
            
            print("Step 7: Getting categories...")
            categories = self.get_categories()
            print(f"Categories result: {categories}")
            
            print("Step 8: Getting description...")
            description = self.get_product_description()
            print(f"Description result: {description}")
            
            if title:  # Only require title, allow missing price
                product_info = {
                    'asin': asin,
                    'url': product_short_url,
                    'title': title,
                    'seller': seller_info or {'name': 'N/A', 'url': None},
                    'price': price,  # Can be None
                    'ranks': ranks or {},
                    'rating': rating_info or {'rating': None, 'rating_count': 0},
                    'details': product_details or {},
                    'categories': categories,
                    'description': description,
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                return product_info
            else:
                return None
        except Exception as e:
            print(f"✗ Error getting product info: {e}")
        return None

    def get_rating_info(self):
        try:
            # Try to find the rating information in different possible locations
            rating_elements = [
                (By.CSS_SELECTOR, "#averageCustomerReviews"),
                (By.CSS_SELECTOR, "#acrPopover"),
                (By.CSS_SELECTOR, "span[data-action='acrStarsLink-click-metrics']"),
            ]
            
            for by, selector in rating_elements:
                try:
                    element = self.driver.find_element(by, selector)
                    if element:
                        # Get the rating value
                        try:
                            rating_text = element.find_element(
                                By.CSS_SELECTOR, 
                                "span.a-icon-alt"
                            ).get_attribute('innerHTML')
                            
                            if not rating_text:
                                rating_text = element.find_element(
                                    By.CSS_SELECTOR,
                                    "i.a-icon-star"
                                ).get_attribute('class')
                            
                            rating = None
                            if rating_text:
                                # Extract the rating number
                                if 'out of 5' in rating_text:
                                    rating = float(rating_text.split('out of')[0].strip())
                                elif 'a-star-' in rating_text:
                                    # Extract number from class like 'a-icon a-icon-star a-star-4'
                                    rating_match = rating_text.split('a-star-')[-1].split()[0]
                                    try:
                                        rating = float(rating_match)
                                    except ValueError:
                                        pass
                            
                            # Get the review count
                            review_count_element = self.driver.find_element(
                                By.CSS_SELECTOR,
                                "#acrCustomerReviewText"
                            )
                            review_count_text = review_count_element.text.strip()
                            review_count = 0
                            
                            if review_count_text:
                                # Extract just the number from text like "196 ratings"
                                count_str = ''.join(c for c in review_count_text if c.isdigit())
                                try:
                                    review_count = int(count_str)
                                except ValueError:
                                    pass
                            
                            return {
                                'rating': rating,
                                'rating_count': review_count
                            }
                        except (NoSuchElementException, Exception) as e:
                            continue
                except NoSuchElementException:
                    continue
            
            return None
        except Exception as e:
            print(e)
            return None

    def get_ranks(self):
        try:
            ranks = {}
            
            # Try different possible locations for the rank information
            possible_selectors = [
                "#productDetails_detailBullets_sections1 tr",  # Standard product details table
                "#detailBulletsWrapper_feature_div li",       # Bullet-style details
                "div#detailBullets_feature_div span.a-list-item", # Another common format
                "div#dpx-amazon-sales-rank_feature_div"       # Direct sales rank div
            ]
            
            for selector in possible_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        text = element.text.strip()
                        # Look for text containing "Best Sellers Rank" or "Amazon Best Sellers Rank"
                        if "Best Sellers Rank" in text or "Amazon Best Sellers Rank" in text:
                            # Find all rank items within this element
                            rank_items = element.find_elements(By.CSS_SELECTOR, "li span.a-list-item, span.a-list-item")
                            if not rank_items:  # If no li items found, try to parse the text directly
                                rank_items = [element]
                            
                            for item in rank_items:
                                try:
                                    text = item.text.strip()
                                    if not text or '#' not in text:
                                        continue
                                        
                                    # Split the text at each '#' to handle multiple rankings in one string
                                    rank_sections = text.split('#')[1:]  # Skip the part before first '#'
                                    for rank_section in rank_sections:
                                        try:
                                            # Try to extract rank number and category
                                            if ' in ' in rank_section:
                                                parts = rank_section.split(' in ', 1)
                                                rank_num = parts[0].replace(',', '').strip()
                                                category = parts[1].split('(')[0].strip()
                                                
                                                try:
                                                    rank_num = int(rank_num)
                                                    ranks[category] = rank_num
                                                except ValueError:
                                                    print(f"Could not convert rank to number: {rank_num}")
                                        except Exception as e:
                                            print(f"Error processing rank section: {e}")
                                            continue
                                except Exception as e:
                                    print(f"Error processing rank item: {e}")
                                    continue
                                    
                    except Exception as e:
                        print(f"Error processing element: {e}")
                        continue
                        
                if ranks:  # If we found ranks using this selector, stop trying others
                    break
            
            return ranks if ranks else None
            
        except Exception as e:
            print(f"Error getting ranks: {e}")
            return None

    def get_title(self):
        try:
            return self.wait.until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            ).text.strip()
        except (TimeoutException, Exception) as e:
            print(f"Can't get title of a product - {self.driver.current_url}")
            print(e)
            return None

    def get_seller(self):
        try:
            # Try multiple possible seller element locations
            seller_elements = [
                # Try the new seller profile trigger first
                (By.CSS_SELECTOR, "#sellerProfileTriggerId"),
                # Try to find the seller in the "Sold by" div
                (By.CSS_SELECTOR, "div.a-row a[data-is-ubb='true']"),
                # Fallback to previous selectors
                (By.ID, "bylineInfo"),
                (By.CSS_SELECTOR, "#merchant-info a"),
                (By.CSS_SELECTOR, ".tabular-buybox-text[tabular-attribute-name='Sold by'] a"),
                # Additional backup selectors
                (By.CSS_SELECTOR, "#merchantInfo a"),
                (By.CSS_SELECTOR, "div.offer-display-feature-text a"),
            ]
            
            for by, selector in seller_elements:
                try:
                    element = self.driver.find_element(by, selector)
                    if element:
                        seller_text = element.text.strip()
                        seller_url = element.get_attribute('href')
                        
                        # Clean up the seller text
                        if seller_text:
                            # Remove common prefixes
                            prefixes_to_remove = [
                                "Sold by ",
                                "Brand: ",
                                "Visit the ",
                                " Store",
                                "Ships from and sold by ",
                                "Fulfilled by Amazon"
                            ]
                            for prefix in prefixes_to_remove:
                                seller_text = seller_text.replace(prefix, "")
                            
                            seller_text = seller_text.strip()
                            if seller_text:  # Only return if we have actual text after cleanup
                                # Clean up the URL
                                if seller_url:
                                    # Make sure URL is absolute
                                    if seller_url.startswith('/'):
                                        seller_url = f"{self.base_url.rstrip('/')}{seller_url}"
                                
                                print(f"Found seller: {seller_text} ({seller_url})")
                                return {
                                    'name': seller_text,
                                    'url': seller_url
                                }
                except NoSuchElementException:
                    continue
            
            # If no seller found with specific selectors, try to find any div containing "Sold by"
            try:
                divs = self.driver.find_elements(By.CSS_SELECTOR, "div.a-row")
                for div in divs:
                    text = div.text.strip()
                    if "Sold by" in text:
                        # Try to find the seller link within this div
                        try:
                            seller_link = div.find_element(By.TAG_NAME, "a")
                            seller_text = seller_link.text.strip()
                            seller_url = seller_link.get_attribute('href')
                            if seller_text:
                                # Clean up the URL
                                if seller_url and seller_url.startswith('/'):
                                    seller_url = f"{self.base_url.rstrip('/')}{seller_url}"
                                    
                                print(f"Found seller in div: {seller_text} ({seller_url})")
                                return {
                                    'name': seller_text,
                                    'url': seller_url
                                }
                        except NoSuchElementException:
                            # If no link found, try to extract seller from text
                            if ":" in text:
                                seller_text = text.split(":", 1)[1].strip()
                            else:
                                seller_text = text.replace("Sold by", "").strip()
                            if seller_text:
                                print(f"Found seller in text: {seller_text}")
                                return {
                                    'name': seller_text,
                                    'url': None
                                }
            except Exception as e:
                print(f"Error searching divs for seller: {e}")
            
            return None
        except Exception as e:
            return None

    def get_price(self):
        try:
            # Get the whole part
            whole_elem = self.driver.find_element(By.CSS_SELECTOR, ".a-price-whole")
            whole_text = whole_elem.text.strip()
            print(f"  Debug: Whole part: '{whole_text}'")
            
            # Get the fraction part
            fraction_elem = self.driver.find_element(By.CSS_SELECTOR, ".a-price-fraction")
            fraction_text = fraction_elem.text.strip()
            print(f"  Debug: Fraction part: '{fraction_text}'")
            
            # Combine them with a dot
            complete_price = f"{whole_text}.{fraction_text}"
            print(f"  Debug: Combined price: '{complete_price}'")
            
            # Convert to float
            # converted_price = self.convert_price(complete_price)
            # if converted_price is not None:
            #     print(f"  Debug: Successfully converted price: {converted_price}")
            #     return converted_price
            # else:
            #     print(f"  Debug: Price conversion failed for: {complete_price}")
            #     return None
            return float(complete_price)
                
        except Exception as e:
            return None

    @staticmethod
    def get_asin(product_link):
        if not product_link:
            return None
        try:
            start = product_link.find('/dp/') + 4
            end = product_link.find('/ref')
            if start > 3 and end > start:
                return product_link[start:end]
            return None
        except Exception:
            return None

    def shorten_url(self, asin):
        return self.base_url + 'dp/' + asin

    # def convert_price(self, price):
    #     if not price or not isinstance(price, str):
    #         print(f"Invalid price input: {price}")
    #         return None
            
    #     try:
    #         print(f"Original price string: '{price}'")
            
    #         # Remove any HTML entities and get just the number
    #         price = price.replace('&euro;', '€').replace('EUR', '€')
    #         print(f"After HTML entity replacement: '{price}'")
            
    #         # Try to extract the number after the currency symbol
    #         if self.currency in price:
    #             price = price.split(self.currency)[1]
    #         print(f"After currency split: '{price}'")
            
    #         # Remove any whitespace and convert commas to dots
    #         price = price.strip().replace(',', '.')
    #         print(f"After cleanup: '{price}'")
            
    #         # Remove any currency symbols or text, but preserve decimal points
    #         price = ''.join(c for c in price if c.isdigit() or c == '.')
    #         print(f"After removing non-numeric chars: '{price}'")
            
    #         # Handle multiple decimal points - keep only the first one
    #         if price.count('.') > 1:
    #             parts = price.split('.')
    #             price = parts[0] + '.' + ''.join(parts[1:])
    #             print(f"After handling multiple decimals: '{price}'")
            
    #         if not price:
    #             print("Price string is empty after processing")
    #             return None
                
    #         converted_price = float(price)
    #         if converted_price <= 0:
    #             print(f"Invalid price value: {converted_price}")
    #             return None
                
    #         return converted_price
    #     except Exception as e:
    #         return None


def process_single_product(asin, search_term, base_url, currency):
    """
    Worker function for processing a single product in parallel.
    Creates its own WebDriver instance to avoid conflicts.
    """
    driver = None
    try:
        # Create a new scraper instance for this worker
        scraper = AmazonScraper(search_term, base_url, currency)
        # WebDriver will be initialized when needed
        
        # Process the single product
        product_info = scraper.get_single_product_info(asin)
        driver = scraper.driver  # Get driver reference for cleanup
        
        return {
            'asin': asin,
            'success': product_info is not None,
            'data': product_info,
            'worker_id': multiprocessing.current_process().name
        }
        
    except Exception as e:
        print(f"✗ Worker error processing {asin}: {e}")
        return {
            'asin': asin,
            'success': False,
            'data': None,
            'error': str(e),
            'worker_id': multiprocessing.current_process().name
        }
    finally:
        # Clean up the driver
        if driver:
            try:
                driver.quit()
            except:
                pass


# API Endpoints
@router.get("/product", summary="Search Amazon Products (Async)")
async def search_amazon_products_async(
    background_tasks: BackgroundTasks,
    search_term: str = Query(..., description="Search term for Amazon products"),
    max_products: int = Query(default=10, description="Maximum number of products to scrape", ge=1, le=None)
):
    """
    Asynchronously search Amazon products and return detailed product information.
    
    Returns a task ID that can be used to check the status and get results.
    
    - **search_term**: Search term for Amazon products (e.g., "toy cars")
    - **max_products**: Maximum number of products to scrape (1-all, default: 10)
    """
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create simple task status
        tasks[task_id] = SearchStatus(
            task_id=task_id,
            status="pending",
            progress=0,
            message=f"Queued search for: {search_term}",
            current_stage="pending",
            current_operation="Task queued",
            products_processed=0,
            total_products_found=None,
            current_product_title=None,
            elapsed_time_seconds=0,
            estimated_remaining_seconds=None,
            success_count=0,
            failure_count=0,
            last_updated=datetime.now().isoformat()
        )
        
        # Add background task
        background_tasks.add_task(search_amazon_products_task, task_id, search_term, max_products)
        
        # Return immediately
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Search task queued successfully",
            "search_term": search_term,
            "max_products": max_products,
            "status_url": f"/amazon/status/{task_id}",
            "results_url": f"/amazon/results/{task_id}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting search task: {str(e)}"
        )

@router.get("/status/{task_id}", response_model=SearchStatus, summary="Get Task Status")
async def get_task_status(task_id: str):
    """Get the status of a search task"""
    logger.info(f"🌐 API ENDPOINT: /status/{task_id}")
    logger.info(f"📥 Status check request for task: {task_id}")
    
    try:
        if task_id not in tasks:
            logger.warning(f"❌ Task {task_id} not found in task storage")
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        task_status = tasks[task_id]
        logger.info(f"✅ Task {task_id} status retrieved: {task_status.status}")
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting task status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting task status: {str(e)}"
        )

@router.get("/results/{task_id}", summary="Get Search Results")
async def get_search_results(task_id: str):
    """Get the results of a completed search task"""
    logger.info(f"🌐 API ENDPOINT: /results/{task_id}")
    logger.info(f"📥 Results request for task: {task_id}")
    
    try:
        if task_id not in tasks:
            logger.warning(f"❌ Task {task_id} not found in task storage")
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        task_status = tasks[task_id]
        
        if task_status.status != "completed":
            logger.warning(f"❌ Task {task_id} not completed yet: {task_status.status}")
            raise HTTPException(
                status_code=400,
                detail=f"Task not completed yet. Current status: {task_status.status}"
            )
        
        if not task_status.results:
            logger.warning(f"❌ No results available for task {task_id}")
            raise HTTPException(
                status_code=404,
                detail="No results available for this task"
            )
        
        logger.info(f"✅ Task {task_id} results retrieved: {len(task_status.results)} products")
        
        return {
            "task_id": task_id,
            "status": task_status.status,
            "total_products": len(task_status.results),
            "success_count": task_status.success_count,
            "failure_count": task_status.failure_count,
            "success_rate": (task_status.success_count / (task_status.success_count + task_status.failure_count) * 100) if (task_status.success_count + task_status.failure_count) > 0 else 0,
            "products": task_status.results,
            "scraped_at": task_status.last_updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting search results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting search results: {str(e)}"
        )

@router.delete("/tasks/{task_id}", summary="Delete Task")
async def delete_task(task_id: str):
    """Delete a search task and its results"""
    logger.info(f"🌐 API ENDPOINT: DELETE /tasks/{task_id}")
    logger.info(f"📥 Delete request for task: {task_id}")
    
    try:
        if task_id not in tasks:
            logger.warning(f"❌ Task {task_id} not found in task storage")
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        del tasks[task_id]
        logger.info(f"✅ Task {task_id} deleted successfully")
        
        return {"message": f"Task {task_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting task: {str(e)}"
        )

@router.get("/tasks", summary="List All Tasks")
async def list_tasks():
    """List all search tasks and their statuses"""
    logger.info(f"🌐 API ENDPOINT: /tasks")
    
    try:
        task_list = []
        for task_id, task_status in tasks.items():
            task_list.append({
                "task_id": task_id,
                "status": task_status.status,
                "progress": task_status.progress,
                "message": task_status.message,
                "products_processed": task_status.products_processed,
                "success_count": task_status.success_count,
                "failure_count": task_status.failure_count,
                "last_updated": task_status.last_updated
            })
        
        logger.info(f"✅ Listed {len(task_list)} tasks")
        
        return {
            "total_tasks": len(task_list),
            "tasks": task_list
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing tasks: {str(e)}"
        )

@router.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint for Amazon API"""
    return {
        "status": "healthy",
        "service": "Amazon Search API",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(tasks)
    }

async def search_amazon_products_task(task_id: str, search_term: str, max_products: int):
    """Background task for searching Amazon products with retry logic"""
    start_time = time.time()
    max_retries = 5
    retry_count = 0
    
    try:
        logger.info(f"🚀 Starting background task {task_id} for search: {search_term}")
        
        # Update task status
        tasks[task_id].status = "running"
        tasks[task_id].progress = 10
        tasks[task_id].message = "Initializing scraper..."
        tasks[task_id].current_stage = "initializing"
        tasks[task_id].current_operation = "Setting up webdriver"
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        # Retry logic
        result = None
        while retry_count < max_retries:
            retry_count += 1
            
            # Update status for retry
            if retry_count > 1:
                tasks[task_id].message = f"Retry attempt {retry_count}/{max_retries} for search: {search_term}"
                tasks[task_id].current_operation = f"Retry {retry_count}/{max_retries}"
                tasks[task_id].last_updated = datetime.now().isoformat()
                logger.info(f"🔄 Retry attempt {retry_count}/{max_retries} for task {task_id}")
            
            # Run the synchronous scraping in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                # Run the entire scraping process in the thread pool
                result = await loop.run_in_executor(
                    executor, 
                    run_scraping_sync, 
                    task_id, 
                    search_term, 
                    max_products
                )
            
            # Check if we got results or if it was successful
            if result['success'] and result['successful_count'] > 0:
                logger.info(f"✅ Task {task_id} succeeded on attempt {retry_count}: {result['successful_count']} products")
                break
            elif result['success'] and result['successful_count'] == 0:
                logger.warning(f"⚠️ Task {task_id} returned zero results on attempt {retry_count}")
                if retry_count < max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.warning(f"⚠️ Task {task_id} failed after {max_retries} attempts - zero results")
                    break
            else:
                logger.warning(f"⚠️ Task {task_id} failed on attempt {retry_count}: {result.get('error', 'Unknown error')}")
                if retry_count < max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error(f"❌ Task {task_id} failed after {max_retries} attempts")
                    break
        
        # Update final status
        elapsed_time = time.time() - start_time
        tasks[task_id].elapsed_time_seconds = elapsed_time
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        if result and result['success'] and result['successful_count'] > 0:
            tasks[task_id].status = "completed"
            tasks[task_id].progress = 100
            tasks[task_id].message = f"Completed: {result['successful_count']}/{result['total_products']} products successful (attempt {retry_count})"
            tasks[task_id].current_stage = "completed"
            tasks[task_id].current_operation = "Task completed"
            tasks[task_id].results = result['products']
            logger.info(f"✅ Task {task_id} completed successfully: {result['successful_count']}/{result['total_products']} products after {retry_count} attempts")
        elif result and result['success'] and result['successful_count'] == 0:
            tasks[task_id].status = "completed"
            tasks[task_id].progress = 100
            tasks[task_id].message = f"No products found after {retry_count} attempts"
            tasks[task_id].current_stage = "completed"
            tasks[task_id].current_operation = "No results found"
            tasks[task_id].results = []
            logger.warning(f"⚠️ Task {task_id} completed with zero results after {retry_count} attempts")
        else:
            tasks[task_id].status = "failed"
            tasks[task_id].progress = 0
            tasks[task_id].message = f"Task failed after {retry_count} attempts: {result.get('error', 'Unknown error') if result else 'No result'}"
            tasks[task_id].current_stage = "failed"
            tasks[task_id].current_operation = "Error occurred"
            logger.error(f"❌ Task {task_id} failed after {retry_count} attempts")
        
    except Exception as e:
        logger.error(f"❌ Error in background task {task_id}: {e}")
        tasks[task_id].status = "failed"
        tasks[task_id].progress = 0
        tasks[task_id].message = f"Task failed after {retry_count} attempts: {str(e)}"
        tasks[task_id].current_stage = "failed"
        tasks[task_id].current_operation = "Error occurred"
        tasks[task_id].last_updated = datetime.now().isoformat()

def run_scraping_sync(task_id: str, search_term: str, max_products: int):
    """Synchronous scraping function to run in thread pool"""
    try:
        # Create scraper
        scraper = AmazonScraper(
            search_term=search_term,
            max_products=max_products
        )
        
        # Update status
        tasks[task_id].progress = 20
        tasks[task_id].message = "Searching for products..."
        tasks[task_id].current_stage = "searching"
        tasks[task_id].current_operation = "Getting product links"
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        # Get product links
        links = scraper.get_products_links()
        if not links:
            return {
                'success': True,
                'products': [],
                'successful_count': 0,
                'total_products': 0,
                'error': None
            }
        
        # Extract ASINs
        asins = []
        for link in links:
            asin = scraper.get_asin(link)
            if asin:
                asins.append(asin)
        
        tasks[task_id].total_products_found = len(asins)
        tasks[task_id].progress = 40
        tasks[task_id].message = f"Processing {len(asins)} products..."
        tasks[task_id].current_stage = "processing"
        tasks[task_id].current_operation = "Scraping product details"
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        # Process products
        products = []
        successful_count = 0
        
        for i, asin in enumerate(asins):
            try:
                # Update progress
                progress = 40 + (i / len(asins)) * 50
                tasks[task_id].progress = int(progress)
                tasks[task_id].message = f"Processing product {i+1}/{len(asins)}"
                tasks[task_id].current_product_title = f"ASIN: {asin}"
                tasks[task_id].products_processed = i + 1
                tasks[task_id].last_updated = datetime.now().isoformat()
                
                product = scraper.get_single_product_info(asin)
                if product:
                    # Convert to ProductData model
                    product_data = ProductData(
                        asin=product['asin'],
                        url=product['url'],
                        title=product['title'],
                        seller=SellerInfo(**product['seller']),
                        price=product['price'],
                        ranks=product['ranks'],
                        rating=RatingInfo(**product['rating']),
                        details=product['details'],
                        categories=CategoriesInfo(**product['categories']),
                        description=DescriptionInfo(**product['description']),
                        scraped_at=product['scraped_at']
                    )
                    products.append(product_data)
                    successful_count += 1
                    tasks[task_id].success_count = successful_count
                else:
                    tasks[task_id].failure_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing product {asin}: {e}")
                tasks[task_id].failure_count += 1
                continue
        
        # Clean up
        scraper.driver.quit()
        
        return {
            'success': True,
            'products': products,
            'successful_count': successful_count,
            'total_products': len(asins),
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error in sync scraping: {e}")
        return {
            'success': False,
            'products': [],
            'successful_count': 0,
            'total_products': 0,
            'error': str(e)
        }


if __name__ == '__main__':
    # Configuration
    USE_PARALLEL = True  # Set to False for sequential processing
    
    print(f"=== AMAZON SCRAPER CONFIGURATION ===")
    print(f"Search term: {NAME}")
    print(f"Parallel processing: {'Enabled' if USE_PARALLEL else 'Disabled'}")
    if USE_PARALLEL:
        print(f"Max workers: {MAX_WORKERS}")
        print(f"Batch size: {BATCH_SIZE}")
    print(f"Headless mode: {'Enabled' if HEADLESS_MODE else 'Disabled'}")
    print(f"Verbose logging: {'Enabled' if VERBOSE_LOGGING else 'Disabled'}")
    print(f"Product limit: {MAX_PRODUCTS if MAX_PRODUCTS else 'No limit'}")
    print("=" * 40)
    
    scraper = AmazonScraper(NAME, BASE_URL, CURRENCY)
    scraper.run(use_parallel=USE_PARALLEL)
