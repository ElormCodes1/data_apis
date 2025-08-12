from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import asyncio
import json
import time
import uuid
import logging
import traceback
import requests
import aiohttp
import ssl
from datetime import datetime
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import cache
try:
    from redis_cache import cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    cache = None

async def resolve_domain(session: aiohttp.ClientSession, domain: str, name: str, task_id: str) -> Tuple[str, str]:
    """Resolve a single domain asynchronously"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        # If it's already a full URL, use it directly
        if domain.startswith('http'):
            url = domain
        else:
            url = f"https://{domain}"
            
        async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as response:
            final_url = str(response.url)
            resolved_domain = urlparse(final_url).netloc
            # Remove www. prefix from resolved domain
            clean_domain = resolved_domain.replace('www.', '') if resolved_domain else resolved_domain
            logger.info(f"✅ Task {task_id}: Resolved domain for {name}: {clean_domain}")
            return domain, clean_domain
    except Exception as e:
        logger.warning(f"⚠️ Task {task_id}: Failed to resolve domain for {name}: {domain}. Error: {str(e)}")
        return domain, domain

async def scrape_product_detail_for_domain(session: aiohttp.ClientSession, product_url: str, name: str, task_id: str) -> Tuple[str, str]:
    """Scrape a product detail page to extract the actual website domain from 'Visit website' button"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        async with session.get(product_url, headers=headers, timeout=15) as response:
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the "Visit website" button
            visit_button = soup.find('a', {'data-test': 'visit-website-button'})
            
            if visit_button and visit_button.get('href'):
                website_url = visit_button.get('href')
                # Extract domain from the URL and remove www. prefix
                domain = urlparse(website_url).netloc
                clean_domain = domain.replace('www.', '') if domain else domain
                logger.info(f"✅ Task {task_id}: Found domain for {name}: {clean_domain} (from {website_url})")
                return product_url, clean_domain
            else:
                logger.warning(f"⚠️ Task {task_id}: No 'Visit website' button found for {name} on {product_url}")
                return product_url, None
                
    except Exception as e:
        logger.warning(f"⚠️ Task {task_id}: Failed to scrape domain for {name} from {product_url}. Error: {str(e)}")
        return product_url, None

async def resolve_domains_batch(domains_data: List[Tuple[str, str, str]], task_id: str, batch_size: int = 100) -> Dict[str, str]:
    """Resolve multiple domains concurrently in batches"""
    resolved_domains = {}
    
    # If cache is available, check cache first
    if CACHE_AVAILABLE and cache:
        for domain, name, _ in domains_data:
            cached_domain = cache.get(f"domain:{domain}")
            if cached_domain:
                resolved_domains[domain] = cached_domain
                logger.info(f"🎯 Task {task_id}: Cache hit for domain: {domain}")
                domains_data = [d for d in domains_data if d[0] != domain]

    # Only proceed with HTTP requests if there are unresolved domains
    if domains_data:
        # Configure SSL context to handle certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds total timeout
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for i in range(0, len(domains_data), batch_size):
                batch = domains_data[i:i + batch_size]
                tasks = [resolve_domain(session, domain, name, task_id) for domain, name, _ in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (original_domain, resolved_domain) in results:
                    if isinstance(resolved_domain, Exception):
                        resolved_domains[original_domain] = original_domain
                    else:
                        resolved_domains[original_domain] = resolved_domain
                        # Cache the result if cache is available
                        if CACHE_AVAILABLE and cache:
                            try:
                                cache.set(f"domain:{original_domain}", resolved_domain, expire=86400)  # Cache for 24 hours
                            except Exception as e:
                                logger.warning(f"⚠️ Task {task_id}: Failed to cache domain {original_domain}: {str(e)}")
    
    return resolved_domains

async def scrape_category_product_domains_batch(product_urls_data: List[Tuple[str, str]], task_id: str, batch_size: int = 10) -> Dict[str, str]:
    """Scrape multiple product detail pages to extract actual website domains"""
    scraped_domains = {}
    
    # If cache is available, check cache first
    if CACHE_AVAILABLE and cache:
        for product_url, name in product_urls_data:
            cached_domain = cache.get(f"category_domain:{product_url}")
            if cached_domain:
                scraped_domains[product_url] = cached_domain
                logger.info(f"🎯 Task {task_id}: Cache hit for product URL: {product_url}")
                product_urls_data = [d for d in product_urls_data if d[0] != product_url]

    # Only proceed with HTTP requests if there are unresolved domains
    if product_urls_data:
        # Configure SSL context to handle certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds total timeout
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for i in range(0, len(product_urls_data), batch_size):
                batch = product_urls_data[i:i + batch_size]
                tasks = [scrape_product_detail_for_domain(session, product_url, name, task_id) for product_url, name in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for (product_url, domain) in results:
                    if isinstance(domain, Exception):
                        scraped_domains[product_url] = None
                    else:
                        scraped_domains[product_url] = domain
                        # Cache the result if cache is available
                        if CACHE_AVAILABLE and cache and domain:
                            try:
                                cache.set(f"category_domain:{product_url}", domain, expire=86400)  # Cache for 24 hours
                            except Exception as e:
                                logger.warning(f"⚠️ Task {task_id}: Failed to cache domain {product_url}: {str(e)}")
    
    return scraped_domains

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('producthunt_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# In-memory storage for task status and results (in production, use Redis or database)
task_status = {}
task_results = {}

class Product(BaseModel):
    id: str
    name: str
    slug: str
    tagline: str
    thumbnail_image_uuid: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    daily_rank: Optional[str] = None
    weekly_rank: Optional[str] = None
    monthly_rank: Optional[str] = None
    votes_count: Optional[int] = None
    comments_count: Optional[int] = None
    latest_score: Optional[int] = None
    launch_day_score: Optional[int] = None
    created_at: Optional[str] = None
    categories: Optional[str] = None


class UpcomingLaunchProduct(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    tagline: Optional[str] = None
    thumbnail_image_uuid: Optional[str] = None
    # domain: Optional[str] = None
    reviews_count: Optional[int] = None
    reviews_rating: Optional[float] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    categories: Optional[str] = None
    description: Optional[str] = None


class ProductHuntCategory(BaseModel):
    name: str
    url: str
    id: str
    slug: str


class CategoryProduct(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    tagline: Optional[str] = None
    thumbnail_image_uuid: Optional[str] = None
    domain: Optional[str] = None
    reviews_count: Optional[int] = None
    reviews_rating: Optional[float] = None
    url: Optional[str] = None
    categories: Optional[str] = None
    description: Optional[str] = None
    media_images: Optional[List[str]] = None
    featured_shoutouts_to_count: Optional[int] = None
    posts_count: Optional[int] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int = 0  # 0-100
    total_pages: int = 0
    current_page: int = 0
    products_found: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class ScrapingResult(BaseModel):
    task_id: str
    products: List[Product]
    total_products: int
    has_next_page: bool
    end_cursor: Optional[str] = None

def create_params(rank_type: str, date: str, cursor: Optional[str] = None) -> Dict[str, Any]:
    """Create GraphQL parameters for different ranking types"""
    
    if rank_type == 'daily':
        order = 'DAILY_RANK'
        sha256Hash = '2430ea344975fe59526515b0e4297d0207da261c59754804825540d73d00ac72'
        year, month, day = date.split('/')
        variables = {
            "featured": True,
            "year": int(year),
            "month": int(month),
            "day": int(day),
            "order": order,
            "cursor": cursor
        }
        operation_name = 'LeaderboardDailyPage'
        
    elif rank_type == 'weekly':
        order = 'WEEKLY_RANK'
        sha256Hash = '2359bcf6f6653ce61d3ae0b0336ead9adb31c8b3675bfcccd17fe0c894a5c213'
        year, week = date.split('/')
        variables = {
            "featured": True,
            "year": int(year),
            "week": int(week),
            "order": order,
            "cursor": cursor
        }
        operation_name = 'LeaderboardWeeklyPage'
        
    elif rank_type == 'monthly':
        order = 'MONTHLY_RANK'
        sha256Hash = 'add7d013633c07225ce8c27e9d0d30e8c877e46650a850170e5acede11d3bf2d'
        year, month = date.split('/')
        variables = {
            "featured": True,
            "year": int(year),
            "month": int(month),
            "order": order,
            "cursor": cursor
        }
        operation_name = 'LeaderboardMonthlyPage'
        
    elif rank_type == 'yearly':
        order = 'YEARLY_RANK'
        sha256Hash = '8fdb0b9699b5025e38aafd71f9602726cbbc0ba49f753ee3935ca8b69278ab06'
        variables = {
            "featured": True,
            "year": int(date),
            "order": order,
            "cursor": cursor
        }
        operation_name = 'LeaderboardYearlyPage'
        
    else:
        raise ValueError(f'Invalid rank type: {rank_type}')
    
    return {
        'operationName': operation_name,
        'variables': json.dumps(variables),
        'extensions': json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": sha256Hash
            }
        })
    }

def setup_chrome_driver():
    """Setup Chrome WebDriver with appropriate options"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=options)

def extract_product_data(product_node: Dict[str, Any]) -> Product:
    """Extract product data from a product node"""
    
    # Extract basic info with error handling
    name = product_node.get('name')
    slug = product_node.get('slug')
    tagline = product_node.get('tagline')
    
    # Extract thumbnail URL
    thumbnail_uuid = product_node.get('thumbnailImageUuid')
    thumbnail_image_uuid = f'https://ph-files.imgix.net/{thumbnail_uuid}' if thumbnail_uuid else None
    
    # Extract short URL
    short_url = product_node.get('shortenedUrl')
    domain = f'https://producthunt.com{short_url}' if short_url else None
    
    # Construct product URL
    url = f'https://producthunt.com/products/{slug}' if slug else None
    
    # Extract rankings
    daily_rank = product_node.get('dailyRank')
    weekly_rank = product_node.get('weeklyRank')
    monthly_rank = product_node.get('monthlyRank')
    
    # Extract engagement metrics
    votes_count = product_node.get('votesCount')
    comments_count = product_node.get('commentsCount')
    latest_score = product_node.get('latestScore')
    launch_day_score = product_node.get('launchDayScore')
    
    # Extract timestamps
    created_at = product_node.get('createdAt')
    
    # Extract categories
    categories = None
    try:
        topics = product_node.get('topics', {}).get('edges', [])
        if topics:
            category_names = [cat['node']['name'] for cat in topics if cat.get('node', {}).get('name')]
            categories = ', '.join(category_names)
    except Exception:
        categories = None
    
    return Product(
        id=product_node.get('id', ''),
        name=name or '',
        slug=slug or '',
        tagline=tagline or '',
        thumbnail_image_uuid=thumbnail_image_uuid,
        domain=domain,
        url=url,
        daily_rank=daily_rank,
        weekly_rank=weekly_rank,
        monthly_rank=monthly_rank,
        votes_count=votes_count,
        comments_count=comments_count,
        latest_score=latest_score,
        launch_day_score=launch_day_score,
        created_at=created_at,
        categories=categories
    )

def scrape_producthunt_data_task(task_id: str, rank_type: str, date: str, max_pages: int = 1000000):
    """Background task to scrape ProductHunt data with pagination"""
    
    logger.info(f"🚀 Starting background task {task_id} for {rank_type} rankings on {date}")
    
    try:
        # Update task status to running
        task_status[task_id].status = "running"
        task_status[task_id].created_at = datetime.now()
        logger.info(f"📊 Task {task_id} status set to running")
        
        all_products = []
        current_page = 0
        cursor = None
        has_next_page = True
        
        # List to store domains that need resolution
        domains_to_resolve = []  # Will store tuples of (domain, name, product_data)
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            while has_next_page and current_page < max_pages:
                current_page += 1
                logger.info(f"📄 Task {task_id}: Processing page {current_page} (max: {max_pages})")
                
                # Update progress (use a more reasonable estimate since we don't know total pages)
                task_status[task_id].current_page = current_page
                # Progress based on pages processed, with a cap at 95% until we know we're done
                progress = min(95, int((current_page / 20) * 100))  # Assume max 20 pages for progress calculation
                task_status[task_id].progress = progress
                
                # Create parameters
                params = create_params(rank_type, date, cursor)
                base_url = 'https://www.producthunt.com/frontend/graphql'
                url = base_url + '?' + urlencode(params)
                
                logger.info(f"🌐 Task {task_id}: Making request to {base_url} with cursor: {cursor}")
                
                # Make request
                driver.get(url)
                
                # Wait for page to load
                logger.info(f"⏳ Task {task_id}: Waiting for page to load...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                
                # Parse response
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                pre_content = soup.find('pre')
                
                if not pre_content:
                    logger.error(f"❌ Task {task_id}: No pre element found on the page")
                    raise Exception("No pre element found on the page")
                
                # Parse JSON response
                logger.info(f"📊 Task {task_id}: Parsing JSON response...")
                json_data = json.loads(pre_content.get_text())
                
                # Extract products from edges
                edges = json_data.get('data', {}).get('homefeedItems', {}).get('edges', [])
                logger.info(f"📋 Task {task_id}: Found {len(edges)} edges on page {current_page}")
                
                page_products = 0
                for i, edge in enumerate(edges):
                    node = edge.get('node', {})
                    if node.get('__typename') == 'Post':  # Skip ads
                        product = extract_product_data(node)
                        all_products.append(product)
                        
                        # Collect domain for batch resolution
                        if product.domain:
                            domains_to_resolve.append((product.domain, product.name, {'id': product.id, 'domain': product.domain}))
                        
                        page_products += 1
                        logger.debug(f"✅ Task {task_id}: Extracted product {product.name} (ID: {product.id})")
                    else:
                        logger.debug(f"⏭️  Task {task_id}: Skipping non-Post node: {node.get('__typename')}")
                
                logger.info(f"📊 Task {task_id}: Extracted {page_products} products from page {current_page}")
                
                # Update task status
                task_status[task_id].products_found = len(all_products)
                logger.info(f"📈 Task {task_id}: Total products so far: {len(all_products)}")
                
                # Get pagination info
                page_info = json_data.get('data', {}).get('homefeedItems', {}).get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                logger.info(f"📄 Task {task_id}: Page {current_page} - hasNextPage: {has_next_page}, endCursor: {cursor}")
                
                # Small delay to be respectful
                time.sleep(1)
                
        finally:
            logger.info(f"🧹 Task {task_id}: Closing Chrome WebDriver")
            driver.quit()
        
        # Resolve all domains in batches
        logger.info(f"🌐 Task {task_id}: Resolving {len(domains_to_resolve)} domains in batches")
        
        # Create event loop in the background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resolved_domains = loop.run_until_complete(resolve_domains_batch(domains_to_resolve, task_id))
        loop.close()
        
        # Create new product instances with resolved domains
        def update_product_domain(product_data):
            if product_data.domain in resolved_domains:
                resolved = resolved_domains[product_data.domain]
                logger.info(f"🔄 Updating domain for {product_data.name}: {product_data.domain} -> {resolved}")
                
                # Create new Product instance with updated domain
                data = product_data.dict()
                data['domain'] = resolved
                return Product(**data)
            return product_data

        # Update all products with resolved domains
        all_products = [update_product_domain(product) for product in all_products]
        
        # Update task status to completed
        task_status[task_id].status = "completed"
        task_status[task_id].progress = 100
        task_status[task_id].total_pages = current_page
        task_status[task_id].completed_at = datetime.now()
        
        logger.info(f"🎉 Task {task_id}: Completed successfully. Total products: {len(all_products)}, Total pages: {current_page}")
        
        # Store results
        task_results[task_id] = {
            "products": all_products,
            "has_next_page": has_next_page,
            "end_cursor": cursor
        }
        
        # Cache the results
        if CACHE_AVAILABLE and cache:
            # Convert Product objects to dictionaries for proper JSON serialization
            products_dict = [product.dict() for product in all_products]
            cache_data = {
                "products": products_dict,
                "has_next_page": has_next_page,
                "end_cursor": cursor,
                "total_products": len(all_products),
                "date": date,
                "rank_type": rank_type,
                "scraped_at": datetime.now().isoformat()
            }
            cache.set(f"{rank_type}_rankings", cache_data, date=date)
            logger.info(f"💾 Task {task_id}: Cached {rank_type} rankings for {date}")
        
        return all_products, has_next_page, cursor
        
    except Exception as e:
        logger.error(f"💥 Task {task_id}: Failed with error: {str(e)}")
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].error_message = str(e)
        task_status[task_id].completed_at = datetime.now()
        raise e


def scrape_todays_launches_task(task_id: str):
    """Background task to scrape today's ProductHunt launches"""
    
    logger.info(f"🚀 Starting background task {task_id} for today's launches")
    
    try:
        # Update task status to running
        task_status[task_id].status = "running"
        task_status[task_id].created_at = datetime.now()
        logger.info(f"📊 Task {task_id} status set to running")
        
        # List to store domains that need resolution
        domains_to_resolve = []  # Will store tuples of (domain, name, product_data)
        
        homepage_products = []  # Featured products from homepage
        graphql_products = []   # Additional products from GraphQL
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            # Method 1: Direct webpage scraping for homepage data (featured products first)
            logger.info(f"🌐 Task {task_id}: Scraping main ProductHunt page for homepage data")
            
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.6',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'sec-gpc': '1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            }
            
            # Use requests for the main page
            import requests
            response = requests.get('https://www.producthunt.com/', headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data from script tags
            json_content1 = None
            for script in soup.find_all('script'):
                content = script.get_text()
                if content and content.strip().startswith('(window[Symbol.for("ApolloSSRDataTransport")]'):
                    content = (content.replace('(window[Symbol.for("ApolloSSRDataTransport")] ??= []).push(', '').replace('undefined', 'null'))[:-1]
                    json_content1 = json.loads(content)
                    if json_content1:
                        logger.info(f"✅ Task {task_id}: Successfully extracted JSON content from homepage")
                        # with open('homepage_data.json', 'w') as f:
                        #     json.dump(json_content1, f)
                    break
            
            if json_content1 and 'events' in json_content1 and len(json_content1['events']) >= 1:
                event_data = json_content1['events'][1]['value']['data']['homefeed']
                
                # Get pagination info
                page_info = event_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                logger.info(f"📄 Task {task_id}: Page info - hasNextPage: {has_next_page}, cursor: {cursor}")
                
                # Extract products from webpage data
                edges = event_data.get('edges', [])
                if edges and 'node' in edges[0] and 'items' in edges[0]['node']:
                    products = edges[0]['node']['items']
                    logger.info(f"📋 Task {task_id}: Found {len(products)} products from homepage")
                    
                    for product in products:
                        try:
                            # Extract product data with error handling
                            name = product.get('name')
                            slug = product.get('slug')
                            tagline = product.get('tagline')
                            
                            # Extract thumbnail URL
                            thumbnail_uuid = product.get('thumbnailImageUuid')
                            thumbnail_image_uuid = f'https://ph-files.imgix.net/{thumbnail_uuid}' if thumbnail_uuid else None
                            
                            # Extract short URL
                            short_url = product.get('shortenedUrl')
                            domain = f'https://producthunt.com{short_url}' if short_url else None

                            if domain:
                                # Store the Product Hunt URL as key for resolution
                                domains_to_resolve.append((domain, name, {'id': product.get('id'), 'domain': domain}))

                            # headers = {
                            #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                            # } 

                            # try:
                            #     resp = requests.get(domain1, allow_redirects=True, headers=headers)

                            #     final_url = resp.url
                            #     domain = urlparse(final_url).netloc
                            # except:
                            #     domain = domain1
                            
                            # Construct product URL
                            url = f'https://producthunt.com/products/{slug}' if slug else None
                            
                            # Extract rankings
                            daily_rank = product.get('dailyRank')
                            weekly_rank = product.get('weeklyRank')
                            monthly_rank = product.get('monthlyRank')
                            
                            # Extract engagement metrics
                            votes_count = product.get('votesCount')
                            comments_count = product.get('commentsCount')
                            latest_score = product.get('latestScore')
                            launch_day_score = product.get('launchDayScore')
                            
                            # Extract timestamps
                            created_at = product.get('createdAt')
                            
                            # Extract categories
                            categories = None
                            try:
                                topics = product.get('topics', {}).get('edges', [])
                                if topics:
                                    category_names = [cat['node']['name'] for cat in topics if cat.get('node', {}).get('name')]
                                    categories = ', '.join(category_names)
                            except Exception:
                                categories = None
                            
                            product_data = Product(
                                id=product.get('id', ''),
                                name=name or '',
                                slug=slug or '',
                                tagline=tagline or '',
                                thumbnail_image_uuid=thumbnail_image_uuid,
                                domain=domain.replace('www.', '') if domain else None,
                                url=url,
                                daily_rank=daily_rank,
                                weekly_rank=weekly_rank,
                                monthly_rank=monthly_rank,
                                votes_count=votes_count,
                                comments_count=comments_count,
                                latest_score=latest_score,
                                launch_day_score=launch_day_score,
                                created_at=created_at,
                                categories=categories
                            )
                            
                            homepage_products.append(product_data)
                            logger.debug(f"✅ Task {task_id}: Extracted homepage product {product_data.name}")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Task {task_id}: Failed to extract product from homepage: {str(e)}")
                            continue
            # logger.info(f"✅ Task {task_id}: Extracted {homepage_products} products from homepage")
            
            # Method 2: GraphQL API call for unfeatured posts (secondary products)
            logger.info(f"🌐 Task {task_id}: Making GraphQL API call for unfeatured posts")
            
            params = {
                'operationName': 'UnfeaturedPosts',
                'variables': '{}',
                'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"96c4888ea89cb7a0ce6b621e09ec3a487a224ae73a77f578ceecbe5f4f2b5ac4"}}',
            }
            
            base_url = 'https://www.producthunt.com/frontend/graphql'
            url = base_url + '?' + urlencode(params)
            
            driver.get(url)
            
            # Wait for page to load
            logger.info(f"⏳ Task {task_id}: Waiting for GraphQL response...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            
            # Parse response
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pre_content = soup.find('pre')
            
            if pre_content:
                json_data = json.loads(pre_content.get_text())
                
                # Extract products from GraphQL response
                if 'data' in json_data and 'homefeed' in json_data['data']:
                    edges = json_data['data']['homefeed'].get('edges', [])
                    if edges and 'node' in edges[0] and 'items' in edges[0]['node']:
                        products = edges[0]['node']['items']
                        logger.info(f"📋 Task {task_id}: Found {len(products)} products from GraphQL")
                        
                        for product in products:
                            try:
                                # Extract product data with error handling
                                name = product.get('name')
                                slug = product.get('slug')
                                tagline = product.get('tagline')
                                
                                # Extract thumbnail URL
                                thumbnail_uuid = product.get('thumbnailImageUuid')
                                thumbnail_image_uuid = f'https://ph-files.imgix.net/{thumbnail_uuid}' if thumbnail_uuid else None
                                
                                # Extract short URL
                                short_url = product.get('shortenedUrl')
                                domain = f'https://producthunt.com{short_url}' if short_url else None

                                # Store domain for batch resolution
                                if domain:
                                    # Store the Product Hunt URL as key for resolution
                                    domains_to_resolve.append((domain, name, {'id': product.get('id'), 'domain': domain}))
                                
                                # Construct product URL
                                url = f'https://producthunt.com/products/{slug}' if slug else None
                                
                                # Extract rankings
                                daily_rank = product.get('dailyRank')
                                weekly_rank = product.get('weeklyRank')
                                monthly_rank = product.get('monthlyRank')
                                
                                # Extract engagement metrics
                                votes_count = product.get('votesCount')
                                comments_count = product.get('commentsCount')
                                latest_score = product.get('latestScore')
                                launch_day_score = product.get('launchDayScore')
                                
                                # Extract timestamps
                                created_at = product.get('createdAt')
                                
                                # Extract categories
                                categories = None
                                try:
                                    topics = product.get('topics', {}).get('edges', [])
                                    if topics:
                                        category_names = [cat['node']['name'] for cat in topics if cat.get('node', {}).get('name')]
                                        categories = ', '.join(category_names)
                                except Exception:
                                    categories = None
                                
                                product_data = Product(
                                    id=product.get('id', ''),
                                    name=name or '',
                                    slug=slug or '',
                                    tagline=tagline or '',
                                    thumbnail_image_uuid=thumbnail_image_uuid,
                                    domain=domain.replace('www.', '') if domain else None,
                                    url=url,
                                    daily_rank=daily_rank,
                                    weekly_rank=weekly_rank,
                                    monthly_rank=monthly_rank,
                                    votes_count=votes_count,
                                    comments_count=comments_count,
                                    latest_score=latest_score,
                                    launch_day_score=launch_day_score,
                                    created_at=created_at,
                                    categories=categories
                                )
                                
                                graphql_products.append(product_data)
                                logger.debug(f"✅ Task {task_id}: Extracted GraphQL product {product_data.name}")
                                
                            except Exception as e:
                                logger.warning(f"⚠️ Task {task_id}: Failed to extract product from GraphQL: {str(e)}")
                                continue
            
            # Combine products with homepage products first, then GraphQL products
            # Remove duplicates from GraphQL products that already exist in homepage
            homepage_ids = {p.id for p in homepage_products if p.id}
            homepage_names = {p.name for p in homepage_products if p.name and not p.id}
            
            # Filter out duplicates from GraphQL products
            unique_graphql_products = []
            for product in graphql_products:
                if product.id and product.id not in homepage_ids:
                    unique_graphql_products.append(product)
                elif product.name and product.name not in homepage_names:
                    unique_graphql_products.append(product)
                else:
                    logger.debug(f"⏭️ Task {task_id}: Skipped duplicate GraphQL product {product.name}")
            
            # Resolve all domains in batches
            logger.info(f"🌐 Task {task_id}: Resolving {len(domains_to_resolve)} domains in batches")
            
            # Create event loop in the background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resolved_domains = loop.run_until_complete(resolve_domains_batch(domains_to_resolve, task_id))
            loop.close()
            
            # Create new product instances with resolved domains
            def update_product_domain(product_data):
                if isinstance(product_data, dict):
                    # For raw dictionary data
                    domain = product_data.get('domain')
                else:
                    # For existing Product instances
                    domain = product_data.domain

                # Get the resolved domain if available
                if domain in resolved_domains:
                    resolved = resolved_domains[domain]
                    logger.info(f"🔄 Updating domain for {product_data.name if hasattr(product_data, 'name') else product_data.get('name')}: {domain} -> {resolved}")
                    
                    if isinstance(product_data, dict):
                        product_data['domain'] = resolved
                        return Product(**product_data)
                    else:
                        data = product_data.dict()
                        data['domain'] = resolved
                        return Product(**data)
                return product_data

            # Update domains in both lists
            homepage_products = [update_product_domain(product) for product in homepage_products]
            unique_graphql_products = [update_product_domain(product) for product in unique_graphql_products]
            
            # Combine: homepage products first, then unique GraphQL products
            all_products = homepage_products + unique_graphql_products
            
            logger.info(f"📊 Task {task_id}: Combined {len(homepage_products)} homepage products + {len(unique_graphql_products)} unique GraphQL products = {len(all_products)} total")
            
        finally:
            logger.info(f"🧹 Task {task_id}: Closing Chrome WebDriver")
            driver.quit()
        
        # Update task status to completed
        task_status[task_id].status = "completed"
        task_status[task_id].progress = 100
        task_status[task_id].total_pages = 1  # Today's launches is typically one page
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].products_found = len(all_products)
        
        logger.info(f"🎉 Task {task_id}: Completed successfully. Total products: {len(all_products)}")
        
        # Store results
        result_data = {
            "products": all_products,
            "has_next_page": False,  # Today's launches don't have pagination
            "end_cursor": None
        }
        
        task_results[task_id] = result_data
        
        # Cache the results (convert products to dictionaries for JSON serialization)
        if CACHE_AVAILABLE and cache:
            products_dict = [product.dict() for product in all_products]
            cache_data = {
                "products": products_dict,
                "has_next_page": False,
                "end_cursor": None
            }
            cache.set("todays_launches", cache_data)
            logger.info(f"💾 Cached today's launches data for task {task_id}")
        
        return all_products, False, None
        
    except Exception as e:
        logger.error(f"💥 Task {task_id}: Failed with error: {str(e)}")
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].error_message = str(e)
        task_status[task_id].completed_at = datetime.now()
        raise e


def scrape_upcoming_launches_task(task_id: str):
    """Background task to scrape ProductHunt upcoming launches"""
    
    logger.info(f"🚀 Starting background task {task_id} for upcoming launches")
    
    try:
        # Update task status to running
        task_status[task_id].status = "running"
        task_status[task_id].created_at = datetime.now()
        logger.info(f"📊 Task {task_id} status set to running")
        
        all_products = []
        current_page = 0
        has_next_page = True
        cursor = None
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            # Step 1: Get initial data from the coming-soon page
            logger.info("📡 Step 1: Fetching initial data from ProductHunt coming-soon page")
            
            params = {
                'ref': 'header_nav',
            }
            
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.6',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'sec-gpc': '1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            }
            
            response = requests.get('https://www.producthunt.com/coming-soon', params=params, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract JSON data from Apollo SSR data transport script
            json_content = None
            for script in soup.find_all('script'):
                content = script.get_text()
                if content and content.strip().startswith('(window[Symbol.for("ApolloSSRDataTransport")]'):
                    content = (content.replace('(window[Symbol.for("ApolloSSRDataTransport")] ??= []).push(', '').replace('undefined', 'null'))[:-1]
                    json_content = json.loads(content)
                    break
            
            if not json_content:
                raise Exception("Could not extract JSON data from ProductHunt page")
            
            # Extract initial data
            upcoming_events = json_content['events'][1]['value']['data']['upcomingEvents']
            has_next_page = upcoming_events['pageInfo']['hasNextPage']
            cursor = upcoming_events['pageInfo']['endCursor']
            
            logger.info(f"📊 Initial data extracted - has_next_page: {has_next_page}, cursor: {cursor}")
            
            # Process initial products
            for product in upcoming_events['edges']:
                try:
                    product_data = extract_upcoming_product_data(product['node'])
                    if product_data:
                        all_products.append(product_data)
                        logger.info(f"✅ Extracted product: {product_data.name}")
                except Exception as e:
                    logger.error(f"❌ Error extracting product data: {str(e)}")
                    continue
            
            current_page += 1
            task_status[task_id].current_page = current_page
            task_status[task_id].products_found = len(all_products)
            logger.info(f"📄 Page {current_page} completed - {len(all_products)} products found so far")
            
            # Step 2: Continue with GraphQL pagination
            while has_next_page:
                logger.info(f"📡 Fetching page {current_page + 1} with cursor: {cursor}")
                
                params = {
                    'operationName': 'ComingSoonPage',
                    'variables': f'{{"cursor":"{cursor}"}}',
                    'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"700b4bd479cd2238279f8cfa04af3cff1644ae202de24ff40fc678d731e0b647"}}',
                }
                
                base_url = 'https://www.producthunt.com/frontend/graphql'
                url = base_url + '?' + urlencode(params)
                
                driver.get(url)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                pre_content = soup.find('pre')
                
                if not pre_content:
                    logger.error("❌ Could not find pre content in response")
                    break
                
                json_data = json.loads(pre_content.get_text())
                upcoming_events = json_data['data']['upcomingEvents']
                has_next_page = upcoming_events['pageInfo']['hasNextPage']
                cursor = upcoming_events['pageInfo']['endCursor']
                
                logger.info(f"📊 Page {current_page + 1} data - has_next_page: {has_next_page}, cursor: {cursor}")
                
                # Process products from this page
                for product in upcoming_events['edges']:
                    try:
                        product_data = extract_upcoming_product_data(product['node'])
                        if product_data:
                            all_products.append(product_data)
                            logger.info(f"✅ Extracted product: {product_data.name}")
                    except Exception as e:
                        logger.error(f"❌ Error extracting product data: {str(e)}")
                        continue
                
                current_page += 1
                task_status[task_id].current_page = current_page
                task_status[task_id].products_found = len(all_products)
                task_status[task_id].progress = min(95, (current_page * 100) // 50)  # Estimate 50 pages max
                
                logger.info(f"📄 Page {current_page} completed - {len(all_products)} products found so far")
                
                # Safety check to prevent infinite loops
                if current_page > 100:
                    logger.warning("⚠️ Reached maximum page limit (100), stopping pagination")
                    break
        
        finally:
            driver.quit()
            logger.info("🔧 Chrome WebDriver closed")
        
        # Store results
        result_data = {
            "products": [product.dict() for product in all_products],
            "total_products": len(all_products),
            "has_next_page": has_next_page,
            "end_cursor": cursor
        }
        
        task_results[task_id] = result_data
        
        # Cache the results (convert products to dictionaries for JSON serialization)
        if CACHE_AVAILABLE and cache:
            products_dict = [product.dict() for product in all_products]
            cache_data = {
                "products": products_dict,
                "has_next_page": has_next_page,
                "end_cursor": cursor
            }
            cache.set("upcoming_launches", cache_data)
            logger.info(f"💾 Cached upcoming launches data for task {task_id}")
        
        # Update task status to completed
        task_status[task_id].status = "completed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].progress = 100
        task_status[task_id].total_pages = current_page
        task_status[task_id].products_found = len(all_products)
        
        logger.info(f"✅ Task {task_id} completed successfully with {len(all_products)} upcoming products")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"💥 TASK {task_id} ERROR")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].error_message = str(e)
        
        logger.error(f"❌ Task {task_id} failed: {str(e)}")


def extract_upcoming_product_data(product_node: Dict[str, Any]) -> Optional[UpcomingLaunchProduct]:
    """Extract upcoming product data from a product node"""
    
    try:
        # Extract basic info with error handling
        name = product_node.get('product', {}).get('name')
        slug = product_node.get('product', {}).get('slug')
        tagline = product_node.get('product', {}).get('tagline')
        
        # Extract thumbnail URL
        logo_uuid = product_node.get('product', {}).get('logoUuid')
        thumbnail_image_uuid = f'https://ph-files.imgix.net/{logo_uuid}' if logo_uuid else None
        
        # Extract short URL
        # product_id = product_node.get('product', {}).get('id')
        # domain = f'https://producthunt.com/r/p/{product_id}' if product_id else None
        
        # Extract reviews
        reviews_count = product_node.get('product', {}).get('reviewsCount')
        reviews_rating = product_node.get('product', {}).get('reviewsRating')
        
        # Extract URL and timestamps
        url = product_node.get('url')
        created_at = product_node.get('post', {}).get('createdAt')
        
        # Extract categories
        categories = None
        try:
            topics = product_node.get('product', {}).get('topics', {}).get('edges', [])
            if topics:
                category_names = [cat['node']['name'] for cat in topics if cat.get('node', {}).get('name')]
                categories = ', '.join(category_names)
        except Exception:
            categories = None
        
        # Extract description
        description = product_node.get('truncatedDescription')
        
        return UpcomingLaunchProduct(
            name=name,
            slug=slug,
            tagline=tagline,
            thumbnail_image_uuid=thumbnail_image_uuid,
            # domain=domain,
            reviews_count=reviews_count,
            reviews_rating=reviews_rating,
            url=url,
            created_at=created_at,
            categories=categories,
            description=description
        )
        
    except Exception as e:
        logger.error(f"❌ Error extracting upcoming product data: {str(e)}")
        return None


def scrape_categories_task(task_id: str):
    """Background task to scrape ProductHunt categories"""
    
    logger.info(f"🚀 Starting background task {task_id} for categories")
    
    try:
        # Update task status to running
        task_status[task_id].status = "running"
        task_status[task_id].created_at = datetime.now()
        logger.info(f"📊 Task {task_id} status set to running")
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            # Make GraphQL API call for categories
            logger.info("📡 Fetching ProductHunt categories via GraphQL API")
            
            params = {
                'operationName': 'HeaderDesktopProductsNavigationQuery',
                'variables': '{}',
                'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"fd37cb954d265af3f43315fe547c112ca5e1c8e0ef70d1cec6b1601f01c7aa08"}}',
            }
            
            base_url = 'https://www.producthunt.com/frontend/graphql'
            url = base_url + '?' + urlencode(params)
            
            driver.get(url)
            
            # Wait for page to load
            logger.info(f"⏳ Task {task_id}: Waiting for GraphQL response...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            
            # Parse response
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pre_content = soup.find('pre')
            
            if not pre_content:
                raise Exception("Could not find pre content in response")
            
            json_data = json.loads(pre_content.get_text())
            logger.info(f"📊 Task {task_id}: Successfully parsed GraphQL response")
            
            # Extract categories
            category_list = []
            product_categories = json_data.get('data', {}).get('productCategories', {}).get('edges', [])
            
            logger.info(f"📋 Task {task_id}: Found {len(product_categories)} main categories")
            
            for category in product_categories:
                try:
                    # Extract major category first
                    major_category_node = category['node']
                    major_url_path = major_category_node['path']
                    major_slug = major_url_path.split('/')[-1] if major_url_path else ""
                    
                    major_category_data = ProductHuntCategory(
                        name=major_category_node['name'],
                        url="https://producthunt.com" + major_category_node['path'],
                        id=major_category_node['id'],
                        slug=major_slug
                    )
                    category_list.append(major_category_data)
                    logger.info(f"✅ Extracted major category: {major_category_data.name} (slug: {major_slug})")
                    
                    # Extract subcategories
                    sub_categories = major_category_node['subCategories']['nodes']
                    logger.info(f"📂 Processing subcategories for: {major_category_node.get('name', 'Unknown')} with {len(sub_categories)} subcategories")
                    
                    for sub_category in sub_categories:
                        try:
                            # Extract slug from URL path
                            url_path = sub_category['path']
                            slug = url_path.split('/')[-1] if url_path else ""
                            
                            category_data = ProductHuntCategory(
                                name=sub_category['name'],
                                url="https://producthunt.com" + sub_category['path'],
                                id=sub_category['id'],
                                slug=slug
                            )
                            category_list.append(category_data)
                            logger.info(f"✅ Extracted subcategory: {category_data.name} (slug: {slug})")
                        except Exception as e:
                            logger.error(f"❌ Error extracting subcategory data: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"❌ Error processing category: {str(e)}")
                    continue
            
            logger.info(f"📊 Task {task_id}: Successfully extracted {len(category_list)} categories")
            
            # Update task status
            task_status[task_id].current_page = 1
            task_status[task_id].products_found = len(category_list)
            task_status[task_id].progress = 100
            
        finally:
            driver.quit()
            logger.info("🔧 Chrome WebDriver closed")
        
        # Store results
        result_data = {
            "categories": [category.dict() for category in category_list],
            "total_categories": len(category_list),
            "has_next_page": False,  # Categories don't have pagination
            "end_cursor": None
        }
        
        task_results[task_id] = result_data
        
        # Cache the results
        if CACHE_AVAILABLE and cache:
            cache.set("categories", result_data)
            logger.info(f"💾 Cached categories data for task {task_id}")
        
        # Update task status to completed
        task_status[task_id].status = "completed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].total_pages = 1
        task_status[task_id].products_found = len(category_list)
        
        logger.info(f"✅ Task {task_id} completed successfully with {len(category_list)} categories")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"💥 TASK {task_id} ERROR")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].error_message = str(e)
        
        logger.error(f"❌ Task {task_id} failed: {str(e)}")


def scrape_category_products_task(task_id: str, category_slug: str, order: str = "highest_rated"):
    """Background task to scrape ProductHunt category products"""
    
    logger.info(f"🚀 Starting background task {task_id} for category products")
    logger.info(f"📊 Category Slug: {category_slug}, Order: {order}")
    
    try:
        # Update task status to running
        task_status[task_id].status = "running"
        task_status[task_id].created_at = datetime.now()
        logger.info(f"📊 Task {task_id} status set to running")
        
        all_products = []
        current_page = 0
        has_next_page = True
        cursor = None
        
        # List to store product URLs for domain scraping
        product_urls_to_scrape = []  # Will store tuples of (product_url, name)
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            # Step 1: Get initial data from the category page
            logger.info("📡 Step 1: Fetching initial data from ProductHunt category page")
            
            # Build the category URL using slug and order
            category_url = f'https://www.producthunt.com/categories/{category_slug}?order={order}'
            
            logger.info(f"🌐 Fetching category page: {category_url}")
            
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.5',
                'cache-control': 'max-age=0',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'sec-gpc': '1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            }
            
            response = requests.get(category_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract JSON data from Apollo SSR data transport script
            json_content = None
            for script in soup.find_all('script'):
                content = script.get_text()
                if content and content.strip().startswith('(window[Symbol.for("ApolloSSRDataTransport")]'):
                    content = (content.replace('(window[Symbol.for("ApolloSSRDataTransport")] ??= []).push(', '').replace('undefined', 'null'))[:-1]
                    json_content = json.loads(content)
                    break
            
            if not json_content:
                raise Exception("Could not extract JSON data from ProductHunt category page")
            
            # Extract initial data
            product_category = json_content['events'][1]['value']['data']['productCategory']
            products_data = product_category['products']
            has_next_page = products_data['pageInfo']['hasNextPage']
            cursor = products_data['pageInfo']['endCursor']
            
            logger.info(f"📊 Initial data extracted - has_next_page: {has_next_page}, cursor: {cursor}")
            
            # Process initial products
            for product in products_data['edges']:
                try:
                    product_data = extract_category_product_data(product['node'])
                    if product_data:
                        all_products.append(product_data)
                        # Collect product URL for domain scraping
                        if product_data.url:
                            product_urls_to_scrape.append((product_data.url, product_data.name))
                        logger.info(f"✅ Extracted product: {product_data.name}")
                except Exception as e:
                    logger.error(f"❌ Error extracting product data: {str(e)}")
                    continue
            
            current_page += 1
            task_status[task_id].current_page = current_page
            task_status[task_id].products_found = len(all_products)
            logger.info(f"📄 Page {current_page} completed - {len(all_products)} products found so far")
            
            # Step 2: Continue with GraphQL pagination
            while has_next_page:
                logger.info(f"📡 Fetching page {current_page + 1} with cursor: {cursor}")
                
                params = {
                    'operationName': 'CategoryPageQuery',
                    'variables': f'{{"featuredOnly":false,"slug":"{category_slug}","cursor":"{cursor}","order":"{order}"}}',
                    'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"ee0d68a735f6a7ccc4e4463c827dcca56c67251489e394cf7da3ed2eae5a8d8b"}}',
                }
                
                base_url = 'https://www.producthunt.com/frontend/graphql'
                url = base_url + '?' + urlencode(params)
                
                driver.get(url)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                pre_content = soup.find('pre')
                
                if not pre_content:
                    logger.error("❌ Could not find pre content in response")
                    break
                
                json_data = json.loads(pre_content.get_text())
                products_data = json_data['data']['productCategory']['products']
                has_next_page = products_data['pageInfo']['hasNextPage']
                cursor = products_data['pageInfo']['endCursor']
                
                logger.info(f"📊 Page {current_page + 1} data - has_next_page: {has_next_page}, cursor: {cursor}")
                
                # Process products from this page
                for product in products_data['edges']:
                    try:
                        product_data = extract_category_product_data(product['node'])
                        if product_data:
                            all_products.append(product_data)
                            # Collect product URL for domain scraping
                            if product_data.url:
                                product_urls_to_scrape.append((product_data.url, product_data.name))
                            logger.info(f"✅ Extracted product: {product_data.name}")
                    except Exception as e:
                        logger.error(f"❌ Error extracting product data: {str(e)}")
                        continue
                
                current_page += 1
                task_status[task_id].current_page = current_page
                task_status[task_id].products_found = len(all_products)
                task_status[task_id].progress = min(95, (current_page * 100) // 50)  # Estimate 50 pages max
                
                logger.info(f"📄 Page {current_page} completed - {len(all_products)} products found so far")
                
                # Safety check to prevent infinite loops
                if current_page > 100:
                    logger.warning("⚠️ Reached maximum page limit (100), stopping pagination")
                    break
        
        finally:
            driver.quit()
            logger.info("🔧 Chrome WebDriver closed")
        
        # Scrape actual domains from product detail pages
        logger.info(f"🌐 Task {task_id}: Scraping domains from {len(product_urls_to_scrape)} product detail pages")
        
        # Create event loop in the background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scraped_domains = loop.run_until_complete(scrape_category_product_domains_batch(product_urls_to_scrape, task_id))
        loop.close()
        
        # Update product instances with scraped domains
        def update_category_product_domain(product_data):
            if product_data.url in scraped_domains and scraped_domains[product_data.url]:
                resolved_domain = scraped_domains[product_data.url]
                logger.info(f"🔄 Updating domain for {product_data.name}: {product_data.domain} -> {resolved_domain}")
                
                # Create new CategoryProduct instance with updated domain
                data = product_data.dict()
                data['domain'] = resolved_domain
                return CategoryProduct(**data)
            return product_data
        
        # Update all products with scraped domains
        all_products = [update_category_product_domain(product) for product in all_products]
        
        # Store results with updated domains
        result_data = {
            "products": [product.dict() for product in all_products],
            "total_products": len(all_products),
            "has_next_page": has_next_page,
            "end_cursor": cursor
        }
        
        task_results[task_id] = result_data
        
        # Cache the results (convert products to dictionaries for JSON serialization)
        if CACHE_AVAILABLE and cache:
            products_dict = [product.dict() for product in all_products]
            cache_data = {
                "products": products_dict,
                "has_next_page": has_next_page,
                "end_cursor": cursor
            }
            cache.set("category_products", cache_data, category_slug=category_slug, order=order)
            logger.info(f"💾 Cached category products data for task {task_id} - {category_slug} (order: {order})")
        
        # Update task status to completed
        task_status[task_id].status = "completed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].progress = 100
        task_status[task_id].total_pages = current_page
        task_status[task_id].products_found = len(all_products)
        
        logger.info(f"✅ Task {task_id} completed successfully with {len(all_products)} category products")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"💥 TASK {task_id} ERROR")
        logger.error("=" * 80)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        logger.error("📍 Full Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].completed_at = datetime.now()
        task_status[task_id].error_message = str(e)
        
        logger.error(f"❌ Task {task_id} failed: {str(e)}")


def extract_category_product_data(product_node: Dict[str, Any]) -> Optional[CategoryProduct]:
    """Extract category product data from a product node"""
    
    try:
        # Extract basic info with error handling
        name = product_node.get('name')
        slug = product_node.get('slug')
        tagline = product_node.get('tagline')
        
        # Extract thumbnail URL
        logo_uuid = product_node.get('logoUuid')
        thumbnail_image_uuid = f'https://ph-files.imgix.net/{logo_uuid}' if logo_uuid else None
        
        # Extract short URL
        product_id = product_node.get('id')
        domain = f'https://producthunt.com/r/p/{product_id}' if product_id else None
        
        # Extract reviews
        reviews_count = product_node.get('reviewsCount')
        reviews_rating = product_node.get('reviewsRating')
        
        # Extract URL
        path = product_node.get('path')
        url = f"https://producthunt.com{path}" if path else None
        
        # Extract categories
        categories = None
        try:
            if product_node.get('categories'):
                categories = ', '.join([cat['name'] for cat in product_node['categories']])
        except Exception:
            categories = None
        
        # Extract description
        description = product_node.get('description')
        
        # Extract media images
        media_images = None
        try:
            media_images_data = product_node.get('mediaImages', [])
            if media_images_data:
                media_images = [f'https://ph-files.imgix.net/{img["imageUuid"]}' for img in media_images_data if img.get('imageUuid')]
        except Exception:
            media_images = None
        
        # Extract additional metrics
        featured_shoutouts_to_count = product_node.get('featuredShoutoutsToCount')
        posts_count = product_node.get('postsCount')
        
        return CategoryProduct(
            name=name,
            slug=slug,
            tagline=tagline,
            thumbnail_image_uuid=thumbnail_image_uuid,
            domain=domain,
            reviews_count=reviews_count,
            reviews_rating=reviews_rating,
            url=url,
            categories=categories,
            description=description,
            media_images=media_images,
            featured_shoutouts_to_count=featured_shoutouts_to_count,
            posts_count=posts_count
        )
        
    except Exception as e:
        logger.error(f"❌ Error extracting category product data: {str(e)}")
        return None


@router.get("/products/daily")
async def get_daily_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., description="Month (1-12)"),
    day: int = Query(..., description="Day (1-31)"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get daily ProductHunt rankings for a specific date"""
    
    date = f"{year}/{month:02d}/{day:02d}"
    logger.info(f"📥 Received GET request for daily rankings: {date}")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("daily_rankings", date=date)
        if cached_data:
            logger.info("✅ Returning cached data for daily rankings")
            
            # Get all products from cache
            all_products = cached_data.get("products", [])
            total_products = len(all_products)
            
            # Calculate pagination
            total_pages = (total_products + limit - 1) // limit
            start_index = (page - 1) * limit
            end_index = min(start_index + limit, total_products)
            
            # Get products for current page
            page_products = all_products[start_index:end_index]
            
            # Calculate pagination info
            has_next_page = page < total_pages
            has_previous_page = page > 1
            
            return {
                "products": page_products,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_products": total_products,
                    "has_next_page": has_next_page,
                    "has_previous_page": has_previous_page,
                    "start_index": start_index,
                    "end_index": end_index
                },
                "navigation": {
                    "next_page": f"/producthunt/products/daily?year={year}&month={month}&day={day}&page={page+1}&limit={limit}" if has_next_page else None,
                    "previous_page": f"/producthunt/products/daily?year={year}&month={month}&day={day}&page={page-1}&limit={limit}" if has_previous_page else None,
                    "first_page": f"/producthunt/products/daily?year={year}&month={month}&day={day}&page=1&limit={limit}",
                    "last_page": f"/producthunt/products/daily?year={year}&month={month}&day={day}&page={total_pages}&limit={limit}"
                },
                "date": date,
                "rank_type": "daily",
                "scraped_at": cached_data.get("scraped_at")
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for daily rankings on {date}")
    
    # Start background task
    background_tasks.add_task(scrape_producthunt_data_task, task_id, "daily", date)
    
    logger.info(f"✅ Task {task_id} queued successfully for daily rankings")
    
    return {
        "task_id": task_id, 
        "status": "pending",
        "date": date,
        "rank_type": "daily",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/products/weekly")
async def get_weekly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    week: int = Query(..., description="Week number (1-52)"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get weekly ProductHunt rankings for a specific year and week"""
    
    date = f"{year}/{week}"
    logger.info(f"📥 Received GET request for weekly rankings: {date}")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("weekly_rankings", date=date)
        if cached_data:
            logger.info("✅ Returning cached data for weekly rankings")
            
            # Get all products from cache
            all_products = cached_data.get("products", [])
            total_products = len(all_products)
            
            # Calculate pagination
            total_pages = (total_products + limit - 1) // limit
            start_index = (page - 1) * limit
            end_index = min(start_index + limit, total_products)
            
            # Get products for current page
            page_products = all_products[start_index:end_index]
            
            # Calculate pagination info
            has_next_page = page < total_pages
            has_previous_page = page > 1
            
            return {
                "products": page_products,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_products": total_products,
                    "has_next_page": has_next_page,
                    "has_previous_page": has_previous_page,
                    "start_index": start_index,
                    "end_index": end_index
                },
                "navigation": {
                    "next_page": f"/producthunt/products/weekly?year={year}&week={week}&page={page+1}&limit={limit}" if has_next_page else None,
                    "previous_page": f"/producthunt/products/weekly?year={year}&week={week}&page={page-1}&limit={limit}" if has_previous_page else None,
                    "first_page": f"/producthunt/products/weekly?year={year}&week={week}&page=1&limit={limit}",
                    "last_page": f"/producthunt/products/weekly?year={year}&week={week}&page={total_pages}&limit={limit}"
                },
                "date": date,
                "rank_type": "weekly",
                "scraped_at": cached_data.get("scraped_at")
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for weekly rankings on {date}")
    
    # Start background task
    background_tasks.add_task(scrape_producthunt_data_task, task_id, "weekly", date)
    
    logger.info(f"✅ Task {task_id} queued successfully for weekly rankings")
    
    return {
        "task_id": task_id, 
        "status": "pending",
        "date": date,
        "rank_type": "weekly",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/products/monthly")
async def get_monthly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., description="Month (1-12)"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get monthly ProductHunt rankings for a specific year and month"""
    
    date = f"{year}/{month}"
    logger.info(f"📥 Received GET request for monthly rankings: {date}")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("monthly_rankings", date=date)
        if cached_data:
            logger.info("✅ Returning cached data for monthly rankings")
            
            # Get all products from cache
            all_products = cached_data.get("products", [])
            total_products = len(all_products)
            
            # Calculate pagination
            total_pages = (total_products + limit - 1) // limit
            start_index = (page - 1) * limit
            end_index = min(start_index + limit, total_products)
            
            # Get products for current page
            page_products = all_products[start_index:end_index]
            
            # Calculate pagination info
            has_next_page = page < total_pages
            has_previous_page = page > 1
            
            return {
                "products": page_products,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_products": total_products,
                    "has_next_page": has_next_page,
                    "has_previous_page": has_previous_page,
                    "start_index": start_index,
                    "end_index": end_index
                },
                "navigation": {
                    "next_page": f"/producthunt/products/monthly?year={year}&month={month}&page={page+1}&limit={limit}" if has_next_page else None,
                    "previous_page": f"/producthunt/products/monthly?year={year}&month={month}&page={page-1}&limit={limit}" if has_previous_page else None,
                    "first_page": f"/producthunt/products/monthly?year={year}&month={month}&page=1&limit={limit}",
                    "last_page": f"/producthunt/products/monthly?year={year}&month={month}&page={total_pages}&limit={limit}"
                },
                "date": date,
                "rank_type": "monthly",
                "scraped_at": cached_data.get("scraped_at")
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for monthly rankings on {date}")
    
    # Use higher max_pages for monthly data since it can be larger
    background_tasks.add_task(scrape_producthunt_data_task, task_id, "monthly", date, 100)
    
    logger.info(f"✅ Task {task_id} queued successfully for monthly rankings")
    
    return {
        "task_id": task_id, 
        "status": "pending",
        "date": date,
        "rank_type": "monthly",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/products/yearly")
async def get_yearly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get yearly ProductHunt rankings for a specific year"""
    
    date = str(year)
    logger.info(f"📥 Received GET request for yearly rankings: {date}")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("yearly_rankings", date=date)
        if cached_data:
            logger.info("✅ Returning cached data for yearly rankings")
            
            # Get all products from cache
            all_products = cached_data.get("products", [])
            total_products = len(all_products)
            
            # Calculate pagination
            total_pages = (total_products + limit - 1) // limit
            start_index = (page - 1) * limit
            end_index = min(start_index + limit, total_products)
            
            # Get products for current page
            page_products = all_products[start_index:end_index]
            
            # Calculate pagination info
            has_next_page = page < total_pages
            has_previous_page = page > 1
            
            return {
                "products": page_products,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_products": total_products,
                    "has_next_page": has_next_page,
                    "has_previous_page": has_previous_page,
                    "start_index": start_index,
                    "end_index": end_index
                },
                "navigation": {
                    "next_page": f"/producthunt/products/yearly?year={year}&page={page+1}&limit={limit}" if has_next_page else None,
                    "previous_page": f"/producthunt/products/yearly?year={year}&page={page-1}&limit={limit}" if has_previous_page else None,
                    "first_page": f"/producthunt/products/yearly?year={year}&page=1&limit={limit}",
                    "last_page": f"/producthunt/products/yearly?year={year}&page={total_pages}&limit={limit}"
                },
                "date": date,
                "rank_type": "yearly",
                "scraped_at": cached_data.get("scraped_at")
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for yearly rankings on {date}")
    
    # Start background task
    background_tasks.add_task(scrape_producthunt_data_task, task_id, "yearly", date)
    
    logger.info(f"✅ Task {task_id} queued successfully for yearly rankings")
    
    return {
        "task_id": task_id, 
        "status": "pending",
        "date": date,
        "rank_type": "yearly",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/todays_launches")
async def get_todays_launches(
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get today's ProductHunt launches"""
    
    logger.info(f"📥 Received GET request for today's launches (page={page}, limit={limit})")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("todays_launches")
        if cached_data and "products" in cached_data:
            logger.info("✅ Returning cached data for today's launches")
            
            # Get cached products
            cached_products = cached_data["products"]
            total_products = len(cached_products)
            
            # Calculate pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_products = cached_products[start_idx:end_idx]
            
            # Calculate pagination metadata
            total_pages = (total_products + limit - 1) // limit
            has_next_page = page < total_pages
            has_prev_page = page > 1
            
            # Create navigation URLs
            base_url = "/producthunt/todays_launches"
            next_url = f"{base_url}?page={page + 1}&limit={limit}" if has_next_page else None
            prev_url = f"{base_url}?page={page - 1}&limit={limit}" if has_prev_page else None
            first_url = f"{base_url}?page=1&limit={limit}" if has_prev_page else None
            last_url = f"{base_url}?page={total_pages}&limit={limit}" if has_next_page else None
            
            # Products are already dictionaries from cache, no need to convert
            products_data = paginated_products
            
            return {
                "products": products_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_products": total_products,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page
                },
                "navigation": {
                    "next_url": next_url,
                    "prev_url": prev_url,
                    "first_url": first_url,
                    "last_url": last_url
                }
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now(),
        progress=0,
        total_pages=1,
        current_page=0
    )
    
    # Start background task immediately
    background_tasks.add_task(scrape_todays_launches_task, task_id)
    
    logger.info(f"✅ Task {task_id} queued successfully for today's launches")
    
    # Return immediately with task ID
    return {
        "task_id": task_id,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rank_type": "todays_launches",
        "status_url": f"/producthunt/status/{task_id}"
    }


@router.get("/upcoming_launches")
async def get_upcoming_launches(
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get ProductHunt upcoming launches"""
    
    logger.info(f"📥 Received GET request for upcoming launches (page={page}, limit={limit})")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("upcoming_launches")
        if cached_data and "products" in cached_data:
            logger.info("✅ Returning cached data for upcoming launches")
            
            # Get cached products
            cached_products = cached_data["products"]
            total_products = len(cached_products)
            
            # Calculate pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_products = cached_products[start_idx:end_idx]
            
            # Calculate pagination metadata
            total_pages = (total_products + limit - 1) // limit
            has_next_page = page < total_pages
            has_prev_page = page > 1
            
            # Create navigation URLs
            base_url = "/producthunt/upcoming_launches"
            next_url = f"{base_url}?page={page + 1}&limit={limit}" if has_next_page else None
            prev_url = f"{base_url}?page={page - 1}&limit={limit}" if has_prev_page else None
            first_url = f"{base_url}?page=1&limit={limit}" if has_prev_page else None
            last_url = f"{base_url}?page={total_pages}&limit={limit}" if has_next_page else None
            
            # Products are already dictionaries from cache, no need to convert
            products_data = paginated_products
            
            return {
                "products": products_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_products": total_products,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page
                },
                "navigation": {
                    "next_url": next_url,
                    "prev_url": prev_url,
                    "first_url": first_url,
                    "last_url": last_url
                }
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for upcoming launches")
    
    # Start background task
    background_tasks.add_task(scrape_upcoming_launches_task, task_id)
    
    logger.info(f"✅ Task {task_id} queued successfully for upcoming launches")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rank_type": "upcoming_launches",
        "status_url": f"/producthunt/status/{task_id}"
    }


@router.get("/categories")
async def get_categories():
    """Get ProductHunt categories (synchronous response)"""
    
    logger.info(f"📥 Received GET request for categories")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("categories")
        if cached_data:
            logger.info("✅ Returning cached data for categories")
            return {
                "status": "completed",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "rank_type": "categories",
                "cached": True,
                "categories": cached_data.get("categories", []),
                "total_categories": cached_data.get("total_categories", 0)
            }
    
    # If no cache, scrape categories directly
    logger.info("🚀 Starting direct category scraping")
    
    try:
        logger.info("🔧 Initializing Chrome WebDriver for categories")
        driver = setup_chrome_driver()
        
        try:
            # Make GraphQL API call for categories
            logger.info("📡 Fetching ProductHunt categories via GraphQL API")
            
            params = {
                'operationName': 'HeaderDesktopProductsNavigationQuery',
                'variables': '{}',
                'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"fd37cb954d265af3f43315fe547c112ca5e1c8e0ef70d1cec6b1601f01c7aa08"}}',
            }
            
            base_url = 'https://www.producthunt.com/frontend/graphql'
            url = base_url + '?' + urlencode(params)
            
            driver.get(url)
            
            # Wait for page to load
            logger.info("⏳ Waiting for GraphQL response...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            
            # Parse response
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pre_content = soup.find('pre')
            
            if not pre_content:
                raise Exception("Could not find pre content in response")
            
            json_data = json.loads(pre_content.get_text())
            logger.info("📊 Successfully parsed GraphQL response")
            
            # Extract categories
            category_list = []
            product_categories = json_data.get('data', {}).get('productCategories', {}).get('edges', [])
            
            logger.info(f"📋 Found {len(product_categories)} main categories")
            
            for category in product_categories:
                try:
                    # Extract major category first
                    major_category_node = category['node']
                    major_url_path = major_category_node['path']
                    major_slug = major_url_path.split('/')[-1] if major_url_path else ""
                    
                    major_category_data = ProductHuntCategory(
                        name=major_category_node['name'],
                        url="https://producthunt.com" + major_category_node['path'],
                        id=major_category_node['id'],
                        slug=major_slug
                    )
                    category_list.append(major_category_data)
                    logger.info(f"✅ Extracted major category: {major_category_data.name} (slug: {major_slug})")
                    
                    # Extract subcategories
                    sub_categories = major_category_node['subCategories']['nodes']
                    logger.info(f"📂 Processing subcategories for: {major_category_node.get('name', 'Unknown')} with {len(sub_categories)} subcategories")
                    
                    for sub_category in sub_categories:
                        try:
                            # Extract slug from URL path
                            url_path = sub_category['path']
                            slug = url_path.split('/')[-1] if url_path else ""
                            
                            category_data = ProductHuntCategory(
                                name=sub_category['name'],
                                url="https://producthunt.com" + sub_category['path'],
                                id=sub_category['id'],
                                slug=slug
                            )
                            category_list.append(category_data)
                            logger.info(f"✅ Extracted subcategory: {category_data.name} (slug: {slug})")
                        except Exception as e:
                            logger.error(f"❌ Error extracting subcategory data: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"❌ Error processing category: {str(e)}")
                    continue
            
            logger.info(f"📊 Successfully extracted {len(category_list)} categories")
            
            # Prepare result data
            result_data = {
                "categories": [category.dict() for category in category_list],
                "total_categories": len(category_list),
                "scraped_at": datetime.now().isoformat()
            }
            
            # Cache the results
            if CACHE_AVAILABLE and cache:
                cache.set("categories", result_data)
                logger.info("💾 Cached categories data")
            
            logger.info(f"✅ Completed successfully with {len(category_list)} categories")
            
            return {
                "status": "completed",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "rank_type": "categories",
                "cached": False,
                "categories": result_data["categories"],
                "total_categories": result_data["total_categories"]
            }
            
        finally:
            driver.quit()
            logger.info("🔧 Chrome WebDriver closed")
            
    except Exception as e:
        logger.error(f"💥 Categories scraping failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to scrape categories: {str(e)}")


@router.get("/category_products")
async def get_category_products(
    category_slug: str = Query(..., description="Category slug (e.g., ai-notetakers)"),
    order: str = Query(default="highest_rated", description="Order: highest_rated, top_free, best_rated, recent_launches, trending"),
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 300)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get ProductHunt products from a specific category with specified ordering"""
    
    # Validate order parameter
    valid_orders = ["highest_rated", "top_free", "best_rated", "recent_launches", "trending"]
    if order not in valid_orders:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid order parameter. Must be one of: {', '.join(valid_orders)}"
        )
    
    logger.info(f"📥 Received GET request for category products - Slug: {category_slug}, Order: {order} (page={page}, limit={limit})")
    
    # Check cache first
    if CACHE_AVAILABLE and cache:
        cached_data = cache.get("category_products", category_slug=category_slug, order=order)
        if cached_data and "products" in cached_data:
            logger.info(f"✅ Returning cached data for category products - {category_slug}")
            
            # Get cached products
            cached_products = cached_data["products"]
            total_products = len(cached_products)
            
            # Calculate pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_products = cached_products[start_idx:end_idx]
            
            # Calculate pagination metadata
            total_pages = (total_products + limit - 1) // limit
            has_next_page = page < total_pages
            has_prev_page = page > 1
            
            # Create navigation URLs
            base_url = f"/producthunt/category_products?category_slug={category_slug}&order={order}"
            next_url = f"{base_url}&page={page + 1}&limit={limit}" if has_next_page else None
            prev_url = f"{base_url}&page={page - 1}&limit={limit}" if has_prev_page else None
            first_url = f"{base_url}&page=1&limit={limit}" if has_prev_page else None
            last_url = f"{base_url}&page={total_pages}&limit={limit}" if has_next_page else None
            
            # Products are already dictionaries from cache, no need to convert
            products_data = paginated_products
            
            return {
                "products": products_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_products": total_products,
                    "total_pages": total_pages,
                    "has_next_page": has_next_page,
                    "has_prev_page": has_prev_page
                },
                "navigation": {
                    "next_url": next_url,
                    "prev_url": prev_url,
                    "first_url": first_url,
                    "last_url": last_url
                },
                "category_slug": category_slug,
                "order": order
            }
    
    # If no cache, start scraping
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for category products")
    
    # Start background task
    background_tasks.add_task(scrape_category_products_task, task_id, category_slug, order)
    
    logger.info(f"✅ Task {task_id} queued successfully for category products")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "category_slug": category_slug,
        "order": order,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rank_type": "category_products",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a scraping task"""
    
    logger.info(f"📊 Status request for task {task_id}")
    
    if task_id not in task_status:
        logger.warning(f"❌ Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_status[task_id]
    logger.info(f"📈 Task {task_id} status: {task.status}, products: {task.products_found}, pages: {task.current_page}/{task.total_pages}")
    
    # Add more detailed status information
    status_response = {
        "task_id": task_id,
        "status": task.status,
        "progress": task.progress,
        "total_pages": task.total_pages,
        "current_page": task.current_page,
        "products_found": task.products_found,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result_url": f"/producthunt/results/{task_id}" if task.status == "completed" else None
    }
    
    return status_response

@router.get("/results/{task_id}")
async def get_task_result(
    task_id: str,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(default=100, ge=1, le=300, description="Number of products per page (max 100)")
):
    """Get the result of a completed scraping task with pagination"""
    
    logger.info(f"📥 Results request for task {task_id} - page {page}, limit {limit}")
    
    if task_id not in task_status:
        logger.warning(f"❌ Task {task_id} not found for results")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_status[task_id]
    
    if task.status == "pending":
        raise HTTPException(status_code=202, detail="Task still pending")
    elif task.status == "running":
        raise HTTPException(status_code=202, detail="Task still running")
    elif task.status == "failed":
        raise HTTPException(status_code=500, detail=f"Task failed: {task.error_message}")
    
    # For completed tasks, return the actual results with pagination
    if task_id in task_results:
        result = task_results[task_id]
        
        # Handle both products and categories
        if "products" in result:
            # Product results
            all_items = result["products"]
            total_items = len(all_items)
            item_type = "products"
            total_items_key = "total_products"
            items_per_page_key = "products_per_page"
        elif "categories" in result:
            # Category results
            all_items = result["categories"]
            total_items = len(all_items)
            item_type = "categories"
            total_items_key = "total_categories"
            items_per_page_key = "categories_per_page"
        else:
            logger.error(f"❌ Task {task_id} results contain neither 'products' nor 'categories' key")
            raise HTTPException(status_code=500, detail="Invalid result format")
        
        # Calculate pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        current_page_items = all_items[start_index:end_index]
        
        # Calculate pagination metadata
        total_pages = (total_items + limit - 1) // limit  # Ceiling division
        has_next_page = page < total_pages
        has_previous_page = page > 1
        
        logger.info(f"📊 Task {task_id} results - Page {page}/{total_pages}, {item_type.title()} {start_index+1}-{min(end_index, total_items)} of {total_items}")
        
        response_data = {
            "task_id": task_id,
            "status": "completed",
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                total_items_key: total_items,
                items_per_page_key: limit,
                "has_next_page": has_next_page,
                "has_previous_page": has_previous_page,
                "start_index": start_index + 1,
                "end_index": min(end_index, total_items)
            },
            "info": {
                "total_pages": task.total_pages,
                "has_more_data": result.get("has_next_page", False),
                "end_cursor": result.get("end_cursor")
            },
            item_type: current_page_items,
            "links": {
                "first_page": f"/producthunt/results/{task_id}?page=1&limit={limit}",
                "last_page": f"/producthunt/results/{task_id}?page={total_pages}&limit={limit}",
                "next_page": f"/producthunt/results/{task_id}?page={page+1}&limit={limit}" if has_next_page else None,
                "previous_page": f"/producthunt/results/{task_id}?page={page-1}&limit={limit}" if has_previous_page else None
            }
        }
        
        return response_data
    else:
        logger.warning(f"❌ Task {task_id} results not found")
        raise HTTPException(status_code=404, detail="Task results not found")

@router.get("/")
async def root():
    """ProductHunt API root endpoint"""
    return {
        "message": "ProductHunt Scraper API",
        "version": "1.0.0",
        "cache_available": CACHE_AVAILABLE and cache is not None,
        "endpoints": {
            "GET /products/daily?year=X&month=Y&day=Z": "Start daily rankings scraping",
            "GET /products/weekly?year=X&week=Y": "Start weekly rankings scraping",
            "GET /products/monthly?year=X&month=Y": "Start monthly rankings scraping",
            "GET /products/yearly?year=X": "Start yearly rankings scraping",
            "GET /todays_launches": "Get today's ProductHunt launches (cached)",
            "GET /upcoming_launches": "Get ProductHunt upcoming launches (cached)",
            "GET /categories": "Get ProductHunt categories (cached)",
            "GET /category_products?category_slug=X": "Get products from specific category (cached)",
            "GET /status/{task_id}": "Get task status",
            "GET /results/{task_id}?page=1&limit=100": "Get paginated task results",
            "GET /health": "Health check endpoint",
            "GET /cache/stats": "Get cache statistics",
            "DELETE /cache/clear": "Clear all cache"
        }
    }


@router.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint for ProductHunt API"""
    logger.info("🌐 API ENDPOINT: /health (Health Check)")
    logger.info("📥 Health check request received")
    
    cache_status = "available" if CACHE_AVAILABLE and cache and cache.redis_client else "unavailable"
    
    health_status = {
        "status": "healthy",
        "service": "ProductHunt Scraper API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Service is running",
        "cache": cache_status
    }
    
    logger.info("✅ Health check completed successfully")
    
    return health_status

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    logger.info("🌐 API ENDPOINT: /cache/stats")
    
    if not CACHE_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    stats = cache.get_cache_stats()
    logger.info("✅ Cache stats retrieved successfully")
    
    return {
        "cache_stats": stats,
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cache"""
    logger.info("🌐 API ENDPOINT: /cache/clear")
    
    if not CACHE_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    success = cache.clear_all()
    logger.info(f"✅ Cache clear {'completed' if success else 'failed'}")
    
    return {
        "message": "Cache cleared successfully" if success else "Failed to clear cache",
        "success": success,
        "timestamp": datetime.now().isoformat()
    }
