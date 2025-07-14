"""
Chrome Web Store Scraper API

FastAPI router for Chrome Web Store extensions scraping functionality.
Based on the exact working chromewebstore.py logic.
"""

import json
import logging
import os
import re
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any
import asyncio
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import csv
import io
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Configuration - matching the original script exactly
CONFIG = {
    'max_workers': 50,
    'output_dir': 'chrome_results'
}

# Chrome Web Store category URLs - comprehensive list
ALL_CATEGORY_URLS = {
    "productivity_developer": "https://chromewebstore.google.com/category/extensions/productivity/developer",
    "lifestyle_art": "https://chromewebstore.google.com/category/extensions/lifestyle/art",
    "productivity_communication": "https://chromewebstore.google.com/category/extensions/productivity/communication",
    "productivity_education": "https://chromewebstore.google.com/category/extensions/productivity/education",
    "lifestyle_entertainment": "https://chromewebstore.google.com/category/extensions/lifestyle/entertainment",
    "lifestyle_household": "https://chromewebstore.google.com/category/extensions/lifestyle/household",
    "lifestyle_travel": "https://chromewebstore.google.com/category/extensions/lifestyle/travel",
    "lifestyle_well_being": "https://chromewebstore.google.com/category/extensions/lifestyle/well_being",
    "make_chrome_yours_functionality": "https://chromewebstore.google.com/category/extensions/make_chrome_yours/functionality",
    "make_chrome_yours_privacy": "https://chromewebstore.google.com/category/extensions/make_chrome_yours/privacy",
    "productivity_tools": "https://chromewebstore.google.com/category/extensions/productivity/tools",
    "productivity_workflow": "https://chromewebstore.google.com/category/extensions/productivity/workflow",
    "lifestyle_games": "https://chromewebstore.google.com/category/extensions/lifestyle/games",
    "lifestyle_fun": "https://chromewebstore.google.com/category/extensions/lifestyle/fun",
    "lifestyle_news": "https://chromewebstore.google.com/category/extensions/lifestyle/news",
    "lifestyle_shopping": "https://chromewebstore.google.com/category/extensions/lifestyle/shopping",
    "lifestyle_social": "https://chromewebstore.google.com/category/extensions/lifestyle/social",
    "make_chrome_yours_accessibility": "https://chromewebstore.google.com/category/extensions/make_chrome_yours/accessibility",
}

# Default categories (currently active ones)
DEFAULT_CATEGORIES = ["lifestyle_well_being", "lifestyle_news"]

# For backward compatibility
CATEGORY_URLS = [ALL_CATEGORY_URLS[cat] for cat in DEFAULT_CATEGORIES]

# Category selection enum for Swagger UI
class ChromeWebStoreCategory(str, Enum):
    """Available Chrome Web Store categories"""
    productivity_developer = "productivity_developer"
    lifestyle_art = "lifestyle_art"
    productivity_communication = "productivity_communication"
    productivity_education = "productivity_education"
    lifestyle_entertainment = "lifestyle_entertainment"
    lifestyle_household = "lifestyle_household"
    lifestyle_travel = "lifestyle_travel"
    lifestyle_well_being = "lifestyle_well_being"
    make_chrome_yours_functionality = "make_chrome_yours_functionality"
    make_chrome_yours_privacy = "make_chrome_yours_privacy"
    productivity_tools = "productivity_tools"
    productivity_workflow = "productivity_workflow"
    lifestyle_games = "lifestyle_games"
    lifestyle_fun = "lifestyle_fun"
    lifestyle_news = "lifestyle_news"
    lifestyle_shopping = "lifestyle_shopping"
    lifestyle_social = "lifestyle_social"
    make_chrome_yours_accessibility = "make_chrome_yours_accessibility"

# Pydantic models
class ExtensionData(BaseModel):
    """Extension data model - matching original data structure"""
    email: Optional[str] = None
    website: Optional[str] = None
    url: str
    review: Optional[int] = None
    ratings: Optional[str] = None
    name: Optional[str] = None
    users: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    owner: Optional[str] = None
    scraped_time: str

class ChromeWebStoreScrapeRequest(BaseModel):
    """Chrome Web Store scraping request model"""
    max_workers: Optional[int] = Field(default=50, description="Number of concurrent workers for details scraping", ge=1, le=100)
    page: Optional[int] = Field(default=1, description="Page number for pagination (starts from 1)", ge=1)
    page_size: Optional[int] = Field(default=100, description="Number of extensions per page", ge=1, le=1000)
    categories: Optional[List[ChromeWebStoreCategory]] = Field(
        default=None, 
        description="🔥 Select Chrome Web Store categories to scrape. Use exact strings from /categories endpoint. Examples: ['lifestyle_well_being'], ['productivity_tools', 'lifestyle_games']. Leave empty to scrape ALL categories."
    )

class ChromeWebStoreScrapeResponse(BaseModel):
    """Chrome Web Store scrape response model"""
    success: bool
    total_urls_collected: int
    total_processed: int
    successful_scrapes: int
    failed_scrapes: int
    execution_time_seconds: float
    extensions: List[ExtensionData]
    message: str
    # Pagination metadata
    pagination: Optional[Dict[str, Any]] = Field(default=None, description="Pagination information")
    # Download options
    download_urls: Optional[Dict[str, str]] = Field(default=None, description="URLs for downloading results")
    
class PaginationInfo(BaseModel):
    """Pagination information model"""
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None

class ScrapeStatus(BaseModel):
    """Enhanced scrape status model with detailed progress"""
    task_id: str
    status: str  # pending, collecting_urls, scraping_details, completed, failed
    stage: str  # current stage description
    progress: Optional[str] = None
    urls_collected: Optional[int] = None
    extensions_scraped: Optional[int] = None
    total_extensions: Optional[int] = None
    current_category: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    all_extensions_data: Optional[List[Dict[str, Any]]] = None  # Store full data for pagination

# In-memory task storage
tasks: Dict[str, ScrapeStatus] = {}

def convert_extensions_to_csv(extensions: List[ExtensionData]) -> str:
    """Convert extension data to CSV format"""
    if not extensions:
        return "No data available"
    
    # Create CSV in memory
    output = io.StringIO()
    
    # Get field names from ExtensionData model
    fieldnames = [
        'name',
        'owner',
        'email',
        'website',
        'url',
        'description',
        'category',
        'users',
        'ratings',
        'review',
        'scraped_time'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write extension data
    for extension in extensions:
        extension_dict = extension.dict()
        writer.writerow(extension_dict)
    
    csv_content = output.getvalue()
    output.close()
    
    return csv_content

def get_download_filename(task_id: str, format_type: str, scraped_time: str) -> str:
    """Generate a friendly filename for downloads"""
    # Clean timestamp
    clean_time = scraped_time.replace(' ', '_').replace(':', '-')
    
    return f"chrome_webstore_extensions_{task_id}_{clean_time}.{format_type}"

def paginate_results(data: List[Dict[str, Any]], page: int = 1, page_size: int = 100) -> Dict[str, Any]:
    """
    Paginate a list of results and return paginated data with metadata
    """
    total_items = len(data)
    total_pages = max(1, (total_items + page_size - 1) // page_size)  # Ceiling division
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate start and end indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get paginated data
    paginated_data = data[start_idx:end_idx]
    
    # Create pagination info
    pagination_info = {
        "current_page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
        "next_page": page + 1 if page < total_pages else None,
        "previous_page": page - 1 if page > 1 else None
    }
    
    return {
        "data": paginated_data,
        "pagination": pagination_info
    }

def scrape_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape a single extension URL - EXACT SAME LOGIC as original script
    """
    data = {}

    try:
        name = website = description = category = users = ratings = review = owner = email = None

        html = requests.get(url)
        soup = BeautifulSoup(html.text, "html.parser")

        try:
            email = soup.find("div", {"class": "AxYQf"}).get_text()
        except:
            email = None
        try:
            website = soup.find("a", {"class": "Gztlsc"}).get("href")
        except:
            website = None
        try:
            ratings = soup.find("span", {"class": "Vq0ZA"}).get_text()
        except:
            ratings = None
        try:
            review = soup.find("p", {"class": "xJEoWe"}).get_text().split(" ")[0]
            if "K" in review:
                review = int(float(review.replace("K", ""))) * 1000
        except:
            review = None
        try:
            name = soup.find("h1", {"class": "Pa2dE"}).get_text()
        except:
            name = None
        try:
            users_text = soup.find("div", {"class": "F9iKBc"}).get_text()
            users = re.findall(r'\d{1,3}(?:,\d{3})*|\d+', users_text)[0]
            if "," in users:
                users = users.replace(",", "")
        except:
            users = None
        try:
            description = soup.select_one("div[jsname='ij8cu'] p").get_text(strip=True)
        except:
            description = None
        try:
            category = soup.find("a", {"class": "gqpEIe bgp7Ye"}).get_text()
        except:
            category = None
        try:
            owner = soup.find("div", {"class": "Fm8Cnb"}).get_text().split("\n")[0].strip()
            name_match = re.match(r"^[^\d]+", owner)
            owner = name_match.group(0).strip() if name_match else None
        except:
            owner = None
        
        SCRAPING_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

        data = {
            "email": email,
            "website": website,
            "url": url,
            "review": review,
            "ratings": ratings,
            "name": name,
            "users": users,
            "description": description,
            "category": category,
            "owner": owner,
            "scraped_time": SCRAPING_DATE,
        }
        logger.debug(f"Scraped data: {data}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")

    return data

def run_concurrently(urls: List[str], max_workers: int = 50, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run scraper concurrently - EXACT SAME LOGIC as original script
    """
    results = []
    completed_count = 0
    
    if task_id:
        tasks[task_id].total_extensions = len(urls)
        tasks[task_id].extensions_scraped = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_url, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            completed_count += 1
            
            try:
                data = future.result()
                if data:  # Only add if data is not empty - same logic as original
                    results.append(data)
                    logger.info(f"Successfully scraped {url} ({completed_count}/{len(urls)})")
                else:
                    logger.warning(f"No data returned for {url}")
                    
                if task_id:
                    tasks[task_id].extensions_scraped = completed_count
                    tasks[task_id].progress = f"{completed_count}/{len(urls)} extensions processed"
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                completed_count += 1
                
                if task_id:
                    tasks[task_id].extensions_scraped = completed_count
                    tasks[task_id].progress = f"{completed_count}/{len(urls)} extensions processed"

    return results

def collect_urls_and_scrape(max_workers: int = 50, task_id: Optional[str] = None, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Complete scraping process following EXACT SAME PATTERN as original script:
    1. Create ONE driver instance (global)
    2. Collect URLs from all categories using same driver
    3. Write URLs to file
    4. Read URLs from file
    5. Run concurrent scraping
    """
    
    # Step 1: Create Chrome driver with EXACT same options as original
    opt = webdriver.ChromeOptions()
    opt.add_argument("disable-cookies")
    opt.add_argument("disable-extensions")
    opt.add_argument("disable-gpu")
    opt.add_argument("disable-infobars")
    opt.add_argument("disable-notifications")
    opt.add_argument("disable-popup-blocking")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opt.add_argument("--remote-debugging-pipe")
    opt.add_argument("--headless")

    try:
        driver = webdriver.Chrome(options=opt)
        logger.info(f"Chrome driver created successfully with version: {driver.capabilities['browserVersion']}")
    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {e}")
        raise ValueError(f"Chrome driver initialization failed: {str(e)}")
    
    try:
        # Step 2: URL Collection Phase - Use selected categories or default
        if categories:
            # Convert category names to URLs
            links = [ALL_CATEGORY_URLS[cat] for cat in categories if cat in ALL_CATEGORY_URLS]
            logger.info(f"Using selected categories: {categories}")
        else:
            # Use all available categories when none selected
            links = list(ALL_CATEGORY_URLS.values())
            logger.info("No categories specified, using all available categories")
        
        if task_id:
            tasks[task_id].status = "collecting_urls"
            tasks[task_id].stage = "Starting URL collection"
            tasks[task_id].progress = f"0/{len(links)} categories processed"
        
        # Create temporary file for this task with absolute path
        import os
        temp_file = os.path.abspath(f"chrome-apps-api-{task_id or 'sync'}.txt")
        
        # Clear the file first
        with open(temp_file, "w") as f:
            f.write("")
        
        for i, link in enumerate(links, 1):
            if task_id:
                tasks[task_id].current_category = link
                tasks[task_id].stage = f"Collecting URLs from category {i}/{len(links)}"
                tasks[task_id].progress = f"{i-1}/{len(links)} categories completed"
            
            logger.info(f"Scraping category: {link}")
            allcaturls = []

            driver.get(link)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, "span.mUIrbf-vQzf8d")
                load_more_button.click()
            except:
                logger.warning(f"No load more button found for {link}")
                continue

            # EXACT same while loop logic as original
            while load_more_button is not None:
                page_height_1 = driver.execute_script("return document.body.scrollHeight")
                logger.debug(f"page height 1 is {page_height_1}")
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                load_more_button = (
                    driver.find_element(By.CSS_SELECTOR, "span.mUIrbf-vQzf8d")
                    if driver.find_elements(By.CSS_SELECTOR, "span.mUIrbf-vQzf8d")
                    else None
                )
                
                if load_more_button is None:
                    break
                    
                load_more_button.click()
                
                try:
                    allcaturls.append([
                        url.get_attribute("href")
                        for url in driver.find_elements(By.CSS_SELECTOR, "a.UvhDdd")
                    ])
                except:
                    break
                    
                if len(allcaturls) > 2:
                    allcaturls.pop(0)
                    
                page_height_2 = driver.execute_script("return document.body.scrollHeight")
                logger.debug(f"page height 2 is {page_height_2}")
                
                if page_height_2 < page_height_1:
                    break
            
            # Write URLs to file - EXACT same logic as original
            if allcaturls:
                urls_to_write = allcaturls[-1]
                logger.info(f"Found {len(urls_to_write)} URLs for category {link}")
                
                with open(temp_file, "a") as f:
                    f.write("\n".join(urls_to_write))
                    f.write("\n")  # Add newline for separation
                
                if task_id:
                    # Count current URLs in file
                    with open(temp_file, "r") as f:
                        current_urls = [line.strip() for line in f if line.strip()]
                    tasks[task_id].urls_collected = len(current_urls)
                    logger.info(f"Total URLs collected so far: {len(current_urls)}")
            else:
                logger.warning(f"No URLs found for category {link}")

    finally:
        # Close the driver after URL collection
        driver.quit()
    
    # Step 3: Read URLs from file - EXACT same logic as original
    try:
        with open(temp_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"URL file {temp_file} not found")
        urls = []
    
    if task_id:
        tasks[task_id].stage = "URL collection completed"
        tasks[task_id].progress = f"{len(links)}/{len(links)} categories processed"
        tasks[task_id].urls_collected = len(urls)
        tasks[task_id].status = "scraping_details"
        tasks[task_id].stage = "Starting extension details scraping"
    
    # Step 4: Run concurrent scraping - EXACT same logic as original
    extensions = run_concurrently(urls, max_workers, task_id)
    
    # Clean up temp file
    try:
        os.remove(temp_file)
    except:
        pass
    
    return {
        "urls_collected": len(urls),
        "extensions_scraped": extensions,
        "total_processed": len(urls),
        "successful_scrapes": len(extensions),
        "failed_scrapes": len(urls) - len(extensions)
    }

def complete_scraping_task(task_id: str, request: ChromeWebStoreScrapeRequest):
    """Background task using the exact same pattern as original script"""
    try:
        tasks[task_id].started_at = datetime.datetime.now().isoformat()
        start_time = time.time()
        
        # Convert enum categories to strings if provided
        selected_categories = None
        if request.categories:
            selected_categories = [cat.value for cat in request.categories]
        
        result = collect_urls_and_scrape(
            max_workers=request.max_workers or CONFIG['max_workers'],
            task_id=task_id,
            categories=selected_categories
        )
        
        execution_time = time.time() - start_time
        
        # Store full results in task for later pagination
        full_response = ChromeWebStoreScrapeResponse(
            success=True,
            total_urls_collected=result["urls_collected"],
            total_processed=result["total_processed"],
            successful_scrapes=result["successful_scrapes"],
            failed_scrapes=result["failed_scrapes"],
            execution_time_seconds=round(execution_time, 2),
            extensions=[ExtensionData(**ext) for ext in result["extensions_scraped"]],
            pagination=None,  # Will be set when paginating
            message=f"Successfully completed scraping: {result['urls_collected']} URLs collected, {result['successful_scrapes']} extensions scraped"
        )
        
        # Store all extensions data for later pagination access
        tasks[task_id].all_extensions_data = result["extensions_scraped"]
        
        # Apply pagination to the response we return
        page = request.page or 1
        page_size = request.page_size or 100
        paginated_result = paginate_results(result["extensions_scraped"], page, page_size)
        
        # Generate download URLs
        download_urls = {
            "json": f"/chrome-webstore/download/{task_id}/json",
            "csv": f"/chrome-webstore/download/{task_id}/csv"
        }

        response = ChromeWebStoreScrapeResponse(
            success=True,
            total_urls_collected=result["urls_collected"],
            total_processed=result["total_processed"],
            successful_scrapes=result["successful_scrapes"],
            failed_scrapes=result["failed_scrapes"],
            execution_time_seconds=round(execution_time, 2),
            extensions=[ExtensionData(**ext) for ext in paginated_result["data"]],
            pagination=paginated_result["pagination"],
            message=f"Successfully completed scraping: {result['urls_collected']} URLs collected, {result['successful_scrapes']} extensions scraped. Showing page {page} of {paginated_result['pagination']['total_pages']} ({len(paginated_result['data'])} items)",
            download_urls=download_urls
        )
        
        tasks[task_id].status = "completed"
        tasks[task_id].stage = "Scraping completed successfully"
        tasks[task_id].completed_at = datetime.datetime.now().isoformat()
        tasks[task_id].result = response
        
        logger.info(f"Scraping task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Scraping task {task_id} failed: {e}")
        tasks[task_id].status = "failed"
        tasks[task_id].stage = f"Failed: {str(e)}"
        tasks[task_id].completed_at = datetime.datetime.now().isoformat()
        tasks[task_id].result = ChromeWebStoreScrapeResponse(
            success=False,
            total_urls_collected=tasks[task_id].urls_collected or 0,
            total_processed=0,
            successful_scrapes=0,
            failed_scrapes=0,
            execution_time_seconds=0,
            extensions=[],
            message=f"Scraping failed: {str(e)}"
        )

# API Endpoints
@router.get("/", summary="API Information")
async def get_api_info():
    """Get Chrome Web Store scraper API information"""
    return {
        "service": "Chrome Web Store Extensions Scraper API",
        "version": "1.0.0",
        "description": "Following the exact same pattern as the working chromewebstore.py script",
        "endpoints": {
            # "/scrape": "Complete scraping process (URLs + details) - synchronous with pagination",
            "/scrape": "Complete scraping process (URLs + details) - asynchronous with pagination and category selection",
            "/status/{task_id}": "Get detailed scraping task status",
            "/results/{task_id}": "Get paginated results from completed async task",
            "/categories": "Get available categories with selection examples",
            "/download/{task_id}/json": "Download full results as JSON file",
            "/download/{task_id}/csv": "Download full results as CSV file"
            # "/config": "Get scraper configuration"
        },
        "total_categories": len(CATEGORY_URLS),
        "process": [
            "1. Create ONE Chrome driver instance",
            "2. Collect extension URLs from ALL hardcoded categories",
            "3. Write URLs to temporary file",
            "4. Read URLs from file",
            "5. Run concurrent scraping on URLs"
        ]
    }

@router.get("/categories", summary="Get Categories")
async def get_categories():
    """Get all available Chrome Web Store categories with exact string values for API usage"""
    return {
        "available_categories": {
            "productivity_developer": {
                "name": "Developer",
                "url": ALL_CATEGORY_URLS["productivity_developer"],
                "string": "productivity_developer"
            },
            "lifestyle_art": {
                "name": "Art",
                "url": ALL_CATEGORY_URLS["lifestyle_art"],
                "string": "lifestyle_art"
            },
            "productivity_communication": {
                "name": "Communication",
                "url": ALL_CATEGORY_URLS["productivity_communication"],
                "string": "productivity_communication"
            },
            "productivity_education": {
                "name": "Education",
                "url": ALL_CATEGORY_URLS["productivity_education"],
                "string": "productivity_education"
            },
            "lifestyle_entertainment": {
                "name": "Entertainment",
                "url": ALL_CATEGORY_URLS["lifestyle_entertainment"],
                "string": "lifestyle_entertainment"
            },
            "lifestyle_household": {
                "name": "Household",
                "url": ALL_CATEGORY_URLS["lifestyle_household"],
                "string": "lifestyle_household"
            },
            "lifestyle_travel": {
                "name": "Travel",
                "url": ALL_CATEGORY_URLS["lifestyle_travel"],
                "string": "lifestyle_travel"
            },
            "lifestyle_well_being": {
                "name": "Well Being",
                "url": ALL_CATEGORY_URLS["lifestyle_well_being"],
                "string": "lifestyle_well_being"
            },
            "make_chrome_yours_functionality": {
                "name": "Functionality",
                "url": ALL_CATEGORY_URLS["make_chrome_yours_functionality"],
                "string": "make_chrome_yours_functionality"
            },
            "make_chrome_yours_privacy": {
                "name": "Privacy",
                "url": ALL_CATEGORY_URLS["make_chrome_yours_privacy"],
                "string": "make_chrome_yours_privacy"
            },
            "productivity_tools": {
                "name": "Tools",
                "url": ALL_CATEGORY_URLS["productivity_tools"],
                "string": "productivity_tools"
            },
            "productivity_workflow": {
                "name": "Workflow",
                "url": ALL_CATEGORY_URLS["productivity_workflow"],
                "string": "productivity_workflow"
            },
            "lifestyle_games": {
                "name": "Games",
                "url": ALL_CATEGORY_URLS["lifestyle_games"],
                "string": "lifestyle_games"
            },
            "lifestyle_fun": {
                "name": "Fun",
                "url": ALL_CATEGORY_URLS["lifestyle_fun"],
                "string": "lifestyle_fun"
            },
            "lifestyle_news": {
                "name": "News",
                "url": ALL_CATEGORY_URLS["lifestyle_news"],
                "string": "lifestyle_news"
            },
            "lifestyle_shopping": {
                "name": "Shopping",
                "url": ALL_CATEGORY_URLS["lifestyle_shopping"],
                "string": "lifestyle_shopping"
            },
            "lifestyle_social": {
                "name": "Social",
                "url": ALL_CATEGORY_URLS["lifestyle_social"],
                "string": "lifestyle_social"
            },
            "make_chrome_yours_accessibility": {
                "name": "Accessibility",
                "url": ALL_CATEGORY_URLS["make_chrome_yours_accessibility"],
                "string": "make_chrome_yours_accessibility"
            }
        },
        "total_categories": len(ALL_CATEGORY_URLS),
        "default_categories": DEFAULT_CATEGORIES,
        "usage": {
            "description": "🔥 Use the 'string' value from each category in the 'categories' field in Swagger UI",
            "example_single": ["lifestyle_well_being"],
            "example_multiple": ["lifestyle_well_being", "lifestyle_news", "productivity_tools"],
            "all_categories": "Leave categories field empty or null to scrape all available categories",
            "swagger_instruction": "Copy the 'string' values from the categories above and paste them into the 'categories' field in Swagger UI"
        }
    }

@router.post("/scrape", summary="Scrape Chrome Extensions (Async)")
async def scrape_chrome_webstore_async(background_tasks: BackgroundTasks, request: ChromeWebStoreScrapeRequest):
    """Complete Chrome Web Store scraping process - asynchronous"""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = ScrapeStatus(
        task_id=task_id,
        status="pending",
        stage="Queued complete scraping task",
        progress="Waiting to start..."
    )
    
    background_tasks.add_task(complete_scraping_task, task_id, request)
    
    logger.info(f"Queued async Chrome Web Store scraping task {task_id}")
    
    return {
        "task_id": task_id,
        "status": "pending", 
        "message": "Complete scraping task queued successfully",
        "status_url": f"/chrome-webstore/status/{task_id}",
    }

@router.get("/status/{task_id}", summary="Get Detailed Task Status")
async def get_task_status(task_id: str):
    """Get detailed status of a scraping task with progress information"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    # If task is completed, include preview of results
    if task.status == "completed" and task.all_extensions_data:
        # Get preview of first 10 results
        preview_data = task.all_extensions_data[:10]
        preview_extensions = [ExtensionData(**ext) for ext in preview_data]
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "stage": task.stage,
            "progress": task.progress,
            "urls_collected": task.urls_collected,
            "extensions_scraped": task.extensions_scraped,
            "total_extensions": task.total_extensions,
            "current_category": task.current_category,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "preview_results": {
                "showing": f"Preview of first 10 results (out of {len(task.all_extensions_data)} total)",
                "extensions": [ext.dict() for ext in preview_extensions],
                "message": "🎉 Scraping completed successfully! Use the endpoints below to get full data."
            },
            "full_data_endpoints": {
                "paginated_results": f"/chrome-webstore/results/{task_id}?page=1&page_size=100",
                "download_json": f"/chrome-webstore/download/{task_id}/json", 
                "download_csv": f"/chrome-webstore/download/{task_id}/csv"
            },
            "usage_instructions": {
                "get_full_results": f"GET /chrome-webstore/results/{task_id}?page=1&page_size=100",
                "download_complete_json": f"GET /chrome-webstore/download/{task_id}/json",
                "download_complete_csv": f"GET /chrome-webstore/download/{task_id}/csv",
                "browse_pages": "Use page=1,2,3... and page_size=50,100,500... to browse through results"
            }
        }
    
    # For non-completed tasks, return the standard status
    return {
        "task_id": task.task_id,
        "status": task.status,
        "stage": task.stage,
        "progress": task.progress,
        "urls_collected": task.urls_collected,
        "extensions_scraped": task.extensions_scraped,
        "total_extensions": task.total_extensions,
        "current_category": task.current_category,
        "started_at": task.started_at,
        "completed_at": task.completed_at
    }

@router.get("/results/{task_id}", response_model=ChromeWebStoreScrapeResponse, summary="Get Paginated Results")
async def get_task_results(
    task_id: str,
    page: int = Query(1, description="Page number for pagination (starts from 1)", ge=1),
    page_size: int = Query(100, description="Number of extensions per page", ge=1, le=1000)
):
    """Get paginated results from a completed scraping task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed yet. Status: {task.status}"
        )
    
    if not task.result:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for task {task_id}"
        )
    
    # Get the original response data
    original_response = task.result
    
    # Get the full extensions data from task storage
    if task.all_extensions_data:
        all_extensions_data = task.all_extensions_data
    else:
        # Fallback - extract from response if available
        if hasattr(original_response, 'extensions'):
            all_extensions_data = [ext.dict() for ext in original_response.extensions]
        else:
            all_extensions_data = []
    
    # Apply new pagination
    paginated_result = paginate_results(all_extensions_data, page, page_size)
    
    # Generate download URLs for full dataset
    download_urls = {
        "json": f"/chrome-webstore/download/{task_id}/json",
        "csv": f"/chrome-webstore/download/{task_id}/csv"
    }

    # Return new paginated response
    return ChromeWebStoreScrapeResponse(
        success=original_response.success,
        total_urls_collected=original_response.total_urls_collected,
        total_processed=original_response.total_processed,
        successful_scrapes=original_response.successful_scrapes,
        failed_scrapes=original_response.failed_scrapes,
        execution_time_seconds=original_response.execution_time_seconds,
        extensions=[ExtensionData(**ext) for ext in paginated_result["data"]],
        pagination=paginated_result["pagination"],
        message=f"Results for task {task_id}. Showing page {page} of {paginated_result['pagination']['total_pages']} ({len(paginated_result['data'])} items)",
        download_urls=download_urls
    )

@router.get("/download/{task_id}/json", summary="Download Results as JSON")
async def download_results_json(task_id: str):
    """Download Chrome Web Store scraping results as JSON file"""
    logger.info(f"🌐 API ENDPOINT: /download/{task_id}/json")
    logger.info(f"📥 JSON download request for task: {task_id}")
    
    if task_id not in tasks:
        logger.warning(f"❌ Task {task_id} not found for JSON download")
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed" or not task.all_extensions_data:
        logger.warning(f"❌ Task {task_id} not completed or has no results")
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed or has no results"
        )
    
    # Convert to JSON
    extensions_data = [ExtensionData(**ext).dict() for ext in task.all_extensions_data]
    
    download_data = {
        "total_extensions": len(extensions_data),
        "scraped_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": task_id,
        "extensions": extensions_data,
        "download_info": {
            "format": "JSON",
            "downloaded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task_id": task_id
        }
    }
    
    # Generate filename
    filename = get_download_filename(task_id, "json", download_data["scraped_time"])
    
    logger.info(f"📤 JSON download ready: {len(extensions_data)} extensions, filename: {filename}")
    
    return JSONResponse(
        content=download_data,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/json"
        }
    )

@router.get("/download/{task_id}/csv", summary="Download Results as CSV")
async def download_results_csv(task_id: str):
    """Download Chrome Web Store scraping results as CSV file"""
    logger.info(f"🌐 API ENDPOINT: /download/{task_id}/csv")
    logger.info(f"📥 CSV download request for task: {task_id}")
    
    if task_id not in tasks:
        logger.warning(f"❌ Task {task_id} not found for CSV download")
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed" or not task.all_extensions_data:
        logger.warning(f"❌ Task {task_id} not completed or has no results")
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed or has no results"
        )
    
    # Convert to CSV
    extensions_obj = [ExtensionData(**ext) for ext in task.all_extensions_data]
    csv_content = convert_extensions_to_csv(extensions_obj)
    
    # Generate filename
    scraped_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = get_download_filename(task_id, "csv", scraped_time)
    
    logger.info(f"📤 CSV download ready: {len(extensions_obj)} extensions, filename: {filename}")
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv"
        }
    )

@router.delete("/tasks", summary="Clear Completed Tasks")
async def clear_tasks():
    """Clear all completed and failed tasks"""
    global tasks
    
    before_count = len(tasks)
    tasks = {
        task_id: task for task_id, task in tasks.items()
        if task.status in ["pending", "collecting_urls", "scraping_details"]
    }
    after_count = len(tasks)
    cleared_count = before_count - after_count
    
    return {
        "message": f"Cleared {cleared_count} completed/failed tasks",
        "remaining_tasks": after_count
    } 