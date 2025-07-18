from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import time
import uuid
import logging
import traceback
from datetime import datetime
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    daily_rank: Optional[str] = None
    weekly_rank: Optional[str] = None
    monthly_rank: Optional[str] = None
    votes_count: Optional[int] = None
    comments_count: Optional[int] = None
    latest_score: Optional[int] = None
    launch_day_score: Optional[int] = None
    featured_at: Optional[str] = None
    categories: Optional[str] = None

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
    featured_at = product_node.get('featuredAt')
    
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
        daily_rank=daily_rank,
        weekly_rank=weekly_rank,
        monthly_rank=monthly_rank,
        votes_count=votes_count,
        comments_count=comments_count,
        latest_score=latest_score,
        launch_day_score=launch_day_score,
        featured_at=featured_at,
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
        
        all_products = []
        
        logger.info(f"🔧 Initializing Chrome WebDriver for task {task_id}")
        driver = setup_chrome_driver()
        
        try:
            # Method 1: GraphQL API call for unfeatured posts
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
                                        category_names = [cat['name'] for cat in topics if cat.get('name')]
                                        categories = ', '.join(category_names)
                                except Exception:
                                    categories = None
                                
                                product_data = Product(
                                    id=product.get('id', ''),
                                    name=name or '',
                                    slug=slug or '',
                                    tagline=tagline or '',
                                    thumbnail_image_uuid=thumbnail_image_uuid,
                                    domain=domain,
                                    daily_rank=daily_rank,
                                    weekly_rank=weekly_rank,
                                    monthly_rank=monthly_rank,
                                    votes_count=votes_count,
                                    comments_count=comments_count,
                                    latest_score=latest_score,
                                    launch_day_score=launch_day_score,
                                    featured_at=created_at,
                                    categories=categories
                                )
                                
                                all_products.append(product_data)
                                logger.debug(f"✅ Task {task_id}: Extracted product {product_data.name} from GraphQL")
                                
                            except Exception as e:
                                logger.warning(f"⚠️ Task {task_id}: Failed to extract product from GraphQL: {str(e)}")
                                continue
            
            # Method 2: Direct webpage scraping for additional data
            logger.info(f"🌐 Task {task_id}: Scraping main ProductHunt page for additional data")
            
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
                    break
            
            if json_content1 and 'events' in json_content1 and len(json_content1['events']) > 4:
                event_data = json_content1['events'][4]['value']['data']['homefeed']
                
                # Get pagination info
                page_info = event_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                logger.info(f"📄 Task {task_id}: Page info - hasNextPage: {has_next_page}, cursor: {cursor}")
                
                # Extract products from webpage data
                edges = event_data.get('edges', [])
                if edges and 'node' in edges[0] and 'items' in edges[0]['node']:
                    products = edges[0]['node']['items']
                    logger.info(f"📋 Task {task_id}: Found {len(products)} products from webpage")
                    
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
                                    category_names = [cat['name'] for cat in topics if cat.get('name')]
                                    categories = ', '.join(category_names)
                            except Exception:
                                categories = None
                            
                            product_data = Product(
                                id=product.get('id', ''),
                                name=name or '',
                                slug=slug or '',
                                tagline=tagline or '',
                                thumbnail_image_uuid=thumbnail_image_uuid,
                                domain=domain,
                                daily_rank=daily_rank,
                                weekly_rank=weekly_rank,
                                monthly_rank=monthly_rank,
                                votes_count=votes_count,
                                comments_count=comments_count,
                                latest_score=latest_score,
                                launch_day_score=launch_day_score,
                                featured_at=created_at,
                                categories=categories
                            )
                            
                            # Check if product already exists (avoid duplicates)
                            existing_product = next((p for p in all_products if p.id == product_data.id), None)
                            if not existing_product:
                                all_products.append(product_data)
                                logger.debug(f"✅ Task {task_id}: Extracted product {product_data.name} from webpage")
                            else:
                                logger.debug(f"⏭️ Task {task_id}: Skipped duplicate product {product_data.name}")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Task {task_id}: Failed to extract product from webpage: {str(e)}")
                            continue
            
            # Remove duplicates based on ID
            unique_products = []
            seen_ids = set()
            for product in all_products:
                if product.id and product.id not in seen_ids:
                    unique_products.append(product)
                    seen_ids.add(product.id)
                elif not product.id:
                    # If no ID, use name as fallback
                    if product.name and product.name not in seen_ids:
                        unique_products.append(product)
                        seen_ids.add(product.name)
            
            all_products = unique_products
            
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
        task_results[task_id] = {
            "products": all_products,
            "has_next_page": False,  # Today's launches don't have pagination
            "end_cursor": None
        }
        
        return all_products, False, None
        
    except Exception as e:
        logger.error(f"💥 Task {task_id}: Failed with error: {str(e)}")
        # Update task status to failed
        task_status[task_id].status = "failed"
        task_status[task_id].error_message = str(e)
        task_status[task_id].completed_at = datetime.now()
        raise e

@router.get("/products/daily")
async def get_daily_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., description="Month (1-12)"),
    day: int = Query(..., description="Day (1-31)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get daily ProductHunt rankings for a specific date"""
    
    date = f"{year}/{month:02d}/{day:02d}"
    logger.info(f"📥 Received GET request for daily rankings: {date}")
    
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
        "message": "Scraping started", 
        "status": "pending",
        "date": date,
        "rank_type": "daily",
        "status_url": f"/producthunt/tasks/{task_id}"
    }

@router.get("/products/weekly")
async def get_weekly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    week: int = Query(..., description="Week number (1-52)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get weekly ProductHunt rankings for a specific year and week"""
    
    date = f"{year}/{week}"
    logger.info(f"📥 Received GET request for weekly rankings: {date}")
    
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
        "message": "Scraping started", 
        "status": "pending",
        "date": date,
        "rank_type": "weekly",
        "status_url": f"/producthunt/tasks/{task_id}"
    }

@router.get("/products/monthly")
async def get_monthly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., description="Month (1-12)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get monthly ProductHunt rankings for a specific year and month"""
    
    date = f"{year}/{month}"
    logger.info(f"📥 Received GET request for monthly rankings: {date}")
    
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
        "message": "Scraping started", 
        "status": "pending",
        "date": date,
        "rank_type": "monthly",
        "status_url": f"/producthunt/tasks/{task_id}"
    }

@router.get("/products/yearly")
async def get_yearly_rankings(
    year: int = Query(..., description="Year (e.g., 2024)"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Get yearly ProductHunt rankings for a specific year"""
    
    date = str(year)
    logger.info(f"📥 Received GET request for yearly rankings: {date}")
    
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
        "message": "Scraping started", 
        "status": "pending",
        "date": date,
        "rank_type": "yearly",
        "status_url": f"/producthunt/status/{task_id}"
    }

@router.get("/todays_launches")
async def get_todays_launches(background_tasks: BackgroundTasks = BackgroundTasks()):
    """Get today's ProductHunt launches"""
    
    logger.info(f"📥 Received GET request for today's launches")
    
    task_id = str(uuid.uuid4())
    task_status[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now()
    )
    
    logger.info(f"🆔 Created task {task_id} for today's launches")
    
    # Start background task
    background_tasks.add_task(scrape_todays_launches_task, task_id)
    
    logger.info(f"✅ Task {task_id} queued successfully for today's launches")
    
    return {
        "task_id": task_id, 
        "message": "Scraping today's launches started", 
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "rank_type": "todays_launches",
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
        all_products = result["products"]
        total_products = len(all_products)
        
        # Calculate pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        current_page_products = all_products[start_index:end_index]
        
        # Calculate pagination metadata
        total_pages = (total_products + limit - 1) // limit  # Ceiling division
        has_next_page = page < total_pages
        has_previous_page = page > 1
        
        logger.info(f"📊 Task {task_id} results - Page {page}/{total_pages}, Products {start_index+1}-{min(end_index, total_products)} of {total_products}")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_products": total_products,
                "products_per_page": limit,
                "has_next_page": has_next_page,
                "has_previous_page": has_previous_page,
                "start_index": start_index + 1,
                "end_index": min(end_index, total_products)
            },
            "scraping_info": {
                "total_pages_scraped": task.total_pages,
                "has_more_data": result["has_next_page"],
                "end_cursor": result["end_cursor"]
            },
            "products": current_page_products,
            "links": {
                "first_page": f"/producthunt/results/{task_id}?page=1&limit={limit}",
                "last_page": f"/producthunt/results/{task_id}?page={total_pages}&limit={limit}",
                "next_page": f"/producthunt/results/{task_id}?page={page+1}&limit={limit}" if has_next_page else None,
                "previous_page": f"/producthunt/results/{task_id}?page={page-1}&limit={limit}" if has_previous_page else None
            }
        }
    else:
        logger.warning(f"❌ Task {task_id} results not found")
        raise HTTPException(status_code=404, detail="Task results not found")

@router.get("/")
async def root():
    """ProductHunt API root endpoint"""
    return {
        "message": "ProductHunt Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "GET /products/daily?year=X&month=Y&day=Z": "Start daily rankings scraping",
            "GET /products/weekly?year=X&week=Y": "Start weekly rankings scraping",
            "GET /products/monthly?year=X&month=Y": "Start monthly rankings scraping",
            "GET /products/yearly?year=X": "Start yearly rankings scraping",
            "GET /todays_launches": "Get today's ProductHunt launches",
            "GET /status/{task_id}": "Get task status",
            "GET /results/{task_id}?page=1&limit=100": "Get paginated task results",
            "GET /health": "Health check endpoint"
        }
    }


@router.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint for ProductHunt API"""
    logger.info("🌐 API ENDPOINT: /health (Health Check)")
    logger.info("📥 Health check request received")
    
    health_status = {
        "status": "healthy",
        "service": "ProductHunt Scraper API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Service is running",
    }
    
    logger.info("✅ Health check completed successfully")
    
    return health_status
