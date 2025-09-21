"""
Zillow Real Estate Search Router

FastAPI router for searching Zillow real estate listings.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import requests
import json
from typing import Optional, List, Dict, Any
import logging
import uuid
import time
import csv
import io
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()
logger = logging.getLogger(__name__)

# Response models
class PropertyResult(BaseModel):
    zpid: Optional[str] = None
    address: Optional[str] = None
    price: Optional[str] = None
    beds: Optional[str] = None
    baths: Optional[str] = None
    sqft: Optional[str] = None
    property_type: Optional[str] = None
    listing_status: Optional[str] = None
    days_on_zillow: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RentalResult(BaseModel):
    zpid: Optional[str] = None
    address: Optional[str] = None
    price: Optional[str] = None
    beds: Optional[str] = None
    baths: Optional[str] = None
    sqft: Optional[str] = None
    property_type: Optional[str] = None
    listing_status: Optional[str] = None
    building_name: Optional[str] = None
    availability_count: Optional[int] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    units_available: Optional[int] = None
    is_building: Optional[bool] = None

class SearchResponse(BaseModel):
    success: bool
    location: str
    total_results: int
    total_available: Optional[int] = None
    pages_scraped: int
    search_parameters: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]]

class SimpleSearchResponse(BaseModel):
    success: bool
    location: str
    total_results: int
    max_price: int
    pages_scraped: int
    results: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    status: str
    service: str
    endpoints: List[str]

# Task status models
class ZillowTaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: int = 0  # 0-100
    message: str = ""
    current_stage: str = ""
    current_operation: str = ""
    pages_scraped: int = 0
    total_pages: Optional[int] = None
    results_found: int = 0
    elapsed_time_seconds: float = 0
    estimated_remaining_seconds: Optional[float] = None
    error_message: Optional[str] = None
    search_type: str = ""  # "sales" or "rentals"
    location: str = ""
    search_parameters: Dict[str, Any] = {}

# In-memory task storage (in production, use Redis or database)
tasks: Dict[str, ZillowTaskStatus] = {}
task_results: Dict[str, Dict[str, Any]] = {}

def update_task_status(task_id: str, **kwargs):
    """Update task status with detailed progress information"""
    if task_id in tasks:
        # Update timestamp
        kwargs['elapsed_time_seconds'] = 0
        if tasks[task_id].started_at:
            start_time = datetime.fromisoformat(tasks[task_id].started_at)
            elapsed = (datetime.now() - start_time).total_seconds()
            kwargs['elapsed_time_seconds'] = round(elapsed, 2)
        
        # Update the task with new information
        for key, value in kwargs.items():
            if hasattr(tasks[task_id], key):
                setattr(tasks[task_id], key, value)
        
        logger.debug(f"📊 Updated task {task_id}: {kwargs}")
    else:
        logger.warning(f"⚠️  Attempted to update non-existent task: {task_id}")

def convert_results_to_csv(results: List[Dict[str, Any]], search_type: str) -> str:
    """Convert Zillow results to CSV format"""
    if not results:
        return ""
    
    output = io.StringIO()
    
    # Get all possible fieldnames from all results
    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())
    
    fieldnames = sorted(list(fieldnames))
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in results:
        # Convert all values to strings and handle None values
        row = {}
        for key, value in result.items():
            if value is None:
                row[key] = ""
            elif isinstance(value, (dict, list)):
                row[key] = json.dumps(value)
            else:
                row[key] = str(value)
        writer.writerow(row)
    
    return output.getvalue()

def get_download_filename(location: str, file_type: str, search_type: str) -> str:
    """Generate download filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    location_clean = location.replace(" ", "_").replace(",", "").lower()
    return f"zillow_{search_type}_{location_clean}_{timestamp}.{file_type}"

# Zillow API headers
ZILLOW_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://www.zillow.com',
    'priority': 'u=1, i',
    'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
}

def get_coordinates_for_location(location: str) -> Dict[str, float]:
    """
    Get coordinates for a given location string.
    For now, returns default coordinates. In production, you'd want to use a geocoding service.
    """
    # Default coordinates for Austin, TX (from the original script)
    # In production, you'd want to use a geocoding service like Google Maps API
    default_coords = {
        'north': 30.519484,
        'south': 30.06787,
        'east': -97.541748,
        'west': -98.090558,
    }
    
    # You could add geocoding logic here
    # For now, return default coordinates
    return default_coords

def search_zillow_rentals(
    location: str,
    min_price: int = 0,
    max_price: int = 5000,
    min_monthly_payment: int = 0,
    max_monthly_payment: int = 5000,
    max_pages: int = 10,
    sort_by: str = "globalrelevanceex"
) -> Dict[str, Any]:
    """
    Search Zillow rental listings with the given parameters.
    
    Args:
        location: Location to search (e.g., "Austin TX")
        min_price: Minimum rent price filter
        max_price: Maximum rent price filter
        min_monthly_payment: Minimum monthly payment filter
        max_monthly_payment: Maximum monthly payment filter
        max_pages: Maximum number of pages to fetch
        sort_by: Sort order for results
        
    Returns:
        Dictionary containing rental search results and metadata
    """
    try:
        # Get coordinates for the location
        coords = get_coordinates_for_location(location)
        
        full_data = []
        page = 1
        total_results = 0
        
        while page <= max_pages:
            json_data = {
                'searchQueryState': {
                    'isMapVisible': True,
                    'mapBounds': coords,
                    'mapZoom': 11,
                    'usersSearchTerm': location,
                    'filterState': {
                        'price': {
                            'min': min_price,
                            'max': max_price,
                        },
                        'monthlyPayment': {
                            'min': min_monthly_payment,
                            'max': max_monthly_payment,
                        },
                        'isForRent': {
                            'value': True,
                        },
                        'isForSaleByAgent': {
                            'value': False,
                        },
                        'isForSaleByOwner': {
                            'value': False,
                        },
                        'isNewConstruction': {
                            'value': False,
                        },
                        'isComingSoon': {
                            'value': False,
                        },
                        'isAuction': {
                            'value': False,
                        },
                        'isForSaleForeclosure': {
                            'value': False,
                        },
                    },
                    'isListVisible': True,
                    'pagination': {'currentPage': page},
                },
                'wants': {
                    'cat1': ['listResults'],
                },
                'requestId': page,
                'isDebugRequest': False,
            }
            
            response = requests.put(
                'https://www.zillow.com/async-create-search-page-state',
                headers=ZILLOW_HEADERS,
                json=json_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Zillow API returned status {response.status_code}")
                break
                
            data = response.json()
            
            # Check if we have results
            if 'cat1' not in data or 'searchResults' not in data['cat1']:
                logger.warning(f"No search results found in response for page {page}")
                break
                
            search_results = data['cat1']['searchResults']
            list_results = search_results.get('listResults', [])
            
            if len(list_results) == 0:
                logger.info(f"No more results found at page {page}")
                break
                
            # Get total count from first page
            if page == 1 and 'total' in data.get('cat2', {}):
                total_results = data['cat2']['total']
            
            full_data.extend(list_results)
            logger.info(f"Rental page {page} completed - {len(list_results)} results")
            page += 1
        
        # Process rental data to extract unit information
        processed_results = []
        for listing in full_data:
            # Extract unit information (rentals have units array)
            units = listing.get('units', [])
            if units:
                # Create a processed listing with unit data
                processed_listing = listing.copy()
                first_unit = units[0]
                processed_listing['unit_price'] = first_unit.get('price', 'N/A')
                processed_listing['unit_beds'] = first_unit.get('beds', 'N/A')
                processed_listing['unit_baths'] = first_unit.get('baths', 'N/A')
                processed_listing['unit_sqft'] = first_unit.get('sqft', 'N/A')
                processed_listing['units_count'] = len(units)
                processed_listing['all_units'] = units
            else:
                processed_listing = listing.copy()
                processed_listing['unit_price'] = listing.get('price', 'N/A')
                processed_listing['unit_beds'] = listing.get('beds', 'N/A')
                processed_listing['unit_baths'] = listing.get('baths', 'N/A')
                processed_listing['unit_sqft'] = listing.get('sqft', 'N/A')
                processed_listing['units_count'] = 0
                processed_listing['all_units'] = []
            
            processed_results.append(processed_listing)
        
        return {
            'success': True,
            'location': location,
            'total_results': len(processed_results),
            'total_available': total_results,
            'pages_scraped': page - 1,
            'search_parameters': {
                'min_price': min_price,
                'max_price': max_price,
                'min_monthly_payment': min_monthly_payment,
                'max_monthly_payment': max_monthly_payment,
                'sort_by': sort_by
            },
            'results': processed_results
        }
        
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching rental data from Zillow: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response from Zillow")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def search_zillow_listings(
    location: str,
    min_price: int = 0,
    max_price: int = 1000000,
    min_monthly_payment: int = 0,
    max_monthly_payment: int = 5000,
    max_pages: int = 10,
    sort_by: str = "globalrelevanceex"
) -> Dict[str, Any]:
    """
    Search Zillow listings with the given parameters.
    
    Args:
        location: Location to search (e.g., "Austin TX")
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_monthly_payment: Minimum monthly payment filter
        max_monthly_payment: Maximum monthly payment filter
        max_pages: Maximum number of pages to fetch
        sort_by: Sort order for results
        
    Returns:
        Dictionary containing search results and metadata
    """
    try:
        # Get coordinates for the location
        coords = get_coordinates_for_location(location)
        
        full_data = []
        page = 1
        total_results = 0
        
        while page <= max_pages:
            json_data = {
                'searchQueryState': {
                    'isMapVisible': False,
                    'mapBounds': coords,
                    'mapZoom': 4,
                    'usersSearchTerm': location,
                    'filterState': {
                        'sortSelection': {
                            'value': sort_by,
                        },
                        'price': {
                            'min': min_price,
                            'max': max_price,
                        },
                        'monthlyPayment': {
                            'min': min_monthly_payment,
                            'max': max_monthly_payment,
                        },
                    },
                    'isListVisible': True,
                    'pagination': {
                        'currentPage': page,
                    },
                },
                'wants': {
                    'cat1': ['listResults'],
                    'cat2': ['total'],
                },
                'requestId': page,
                'isDebugRequest': False,
            }
            
            response = requests.put(
                'https://www.zillow.com/async-create-search-page-state',
                headers=ZILLOW_HEADERS,
                json=json_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Zillow API returned status {response.status_code}")
                break
                
            data = response.json()
            
            # Check if we have results
            if 'cat1' not in data or 'searchResults' not in data['cat1']:
                logger.warning(f"No search results found in response for page {page}")
                break
                
            search_results = data['cat1']['searchResults']
            list_results = search_results.get('listResults', [])
            
            if len(list_results) == 0:
                logger.info(f"No more results found at page {page}")
                break
                
            # Get total count from first page
            if page == 1 and 'total' in data.get('cat2', {}):
                total_results = data['cat2']['total']
            
            full_data.extend(list_results)
            logger.info(f"Page {page} completed - {len(list_results)} results")
            page += 1
        
        return {
            'success': True,
            'location': location,
            'total_results': len(full_data),
            'total_available': total_results,
            'pages_scraped': page - 1,
            'search_parameters': {
                'min_price': min_price,
                'max_price': max_price,
                'min_monthly_payment': min_monthly_payment,
                'max_monthly_payment': max_monthly_payment,
                'sort_by': sort_by
            },
            'results': full_data
        }
        
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data from Zillow: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response from Zillow")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Background task functions
def run_sales_scraping_sync(task_id: str, location: str, min_price: int, max_price: int, 
                           min_monthly_payment: int, max_monthly_payment: int, 
                           max_pages: int, sort_by: str):
    """Synchronous sales scraping function to run in thread pool"""
    try:
        logger.info(f"🏠 Starting sales scraping for task {task_id}")
        
        # Get coordinates for the location
        coords = get_coordinates_for_location(location)
        
        full_data = []
        page = 1
        total_results = 0
        
        while page <= max_pages:
            update_task_status(
                task_id,
                current_stage="scraping",
                current_operation=f"Scraping page {page} of {max_pages}",
                pages_scraped=page-1,
                progress=int((page-1) / max_pages * 100)
            )
            
            json_data = {
                'searchQueryState': {
                    'isMapVisible': False,
                    'mapBounds': coords,
                    'mapZoom': 4,
                    'usersSearchTerm': location,
                    'filterState': {
                        'sortSelection': {'value': sort_by},
                        'price': {'min': min_price, 'max': max_price},
                        'monthlyPayment': {'min': min_monthly_payment, 'max': max_monthly_payment},
                    },
                    'isListVisible': True,
                    'pagination': {'currentPage': page},
                },
                'wants': {'cat1': ['listResults'], 'cat2': ['total']},
                'requestId': page,
                'isDebugRequest': False,
            }
            
            response = requests.put(
                'https://www.zillow.com/async-create-search-page-state',
                headers=ZILLOW_HEADERS,
                json=json_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Zillow API returned status {response.status_code}")
                break
                
            data = response.json()
            
            if 'cat1' not in data or 'searchResults' not in data['cat1']:
                logger.warning(f"No search results found in response for page {page}")
                break
                
            search_results = data['cat1']['searchResults']
            list_results = search_results.get('listResults', [])
            
            if len(list_results) == 0:
                logger.info(f"No more results found at page {page}")
                break
                
            if page == 1 and 'total' in data.get('cat2', {}):
                total_results = data['cat2']['total']
            
            full_data.extend(list_results)
            logger.info(f"Sales page {page} completed - {len(list_results)} results")
            page += 1
        
        # Store results
        task_results[task_id] = {
            "success": True,
            "location": location,
            "total_results": len(full_data),
            "total_available": total_results,
            "pages_scraped": page - 1,
            "search_parameters": {
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "sort_by": sort_by
            },
            "results": full_data
        }
        
        update_task_status(
            task_id,
            status="completed",
            completed_at=datetime.now().isoformat(),
            progress=100,
            current_stage="completed",
            current_operation="Scraping completed",
            pages_scraped=page-1,
            results_found=len(full_data)
        )
        
        logger.info(f"✅ Sales scraping completed for task {task_id}: {len(full_data)} results")
        
    except Exception as e:
        logger.error(f"❌ Sales scraping failed for task {task_id}: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e),
            current_stage="failed",
            current_operation="Scraping failed"
        )

def run_rentals_scraping_sync(task_id: str, location: str, min_price: int, max_price: int, 
                             min_monthly_payment: int, max_monthly_payment: int, 
                             max_pages: int, sort_by: str):
    """Synchronous rentals scraping function to run in thread pool"""
    try:
        logger.info(f"🏠 Starting rentals scraping for task {task_id}")
        
        # Get coordinates for the location
        coords = get_coordinates_for_location(location)
        
        full_data = []
        page = 1
        total_results = 0
        
        while page <= max_pages:
            update_task_status(
                task_id,
                current_stage="scraping",
                current_operation=f"Scraping page {page} of {max_pages}",
                pages_scraped=page-1,
                progress=int((page-1) / max_pages * 100)
            )
            
            json_data = {
                'searchQueryState': {
                    'isMapVisible': True,
                    'mapBounds': coords,
                    'mapZoom': 11,
                    'usersSearchTerm': location,
                    'filterState': {
                        'price': {'min': min_price, 'max': max_price},
                        'monthlyPayment': {'min': min_monthly_payment, 'max': max_monthly_payment},
                        'isForRent': {'value': True},
                        'isForSaleByAgent': {'value': False},
                        'isForSaleByOwner': {'value': False},
                        'isNewConstruction': {'value': False},
                        'isComingSoon': {'value': False},
                        'isAuction': {'value': False},
                        'isForSaleForeclosure': {'value': False},
                    },
                    'isListVisible': True,
                    'pagination': {'currentPage': page},
                },
                'wants': {'cat1': ['listResults']},
                'requestId': page,
                'isDebugRequest': False,
            }
            
            response = requests.put(
                'https://www.zillow.com/async-create-search-page-state',
                headers=ZILLOW_HEADERS,
                json=json_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Zillow API returned status {response.status_code}")
                break
                
            data = response.json()
            
            if 'cat1' not in data or 'searchResults' not in data['cat1']:
                logger.warning(f"No search results found in response for page {page}")
                break
                
            search_results = data['cat1']['searchResults']
            list_results = search_results.get('listResults', [])
            
            if len(list_results) == 0:
                logger.info(f"No more results found at page {page}")
                break
                
            if page == 1 and 'total' in data.get('cat2', {}):
                total_results = data['cat2']['total']
            
            # Process rental data to extract unit information
            processed_results = []
            for listing in list_results:
                units = listing.get('units', [])
                if units:
                    processed_listing = listing.copy()
                    first_unit = units[0]
                    processed_listing['unit_price'] = first_unit.get('price', 'N/A')
                    processed_listing['unit_beds'] = first_unit.get('beds', 'N/A')
                    processed_listing['unit_baths'] = first_unit.get('baths', 'N/A')
                    processed_listing['unit_sqft'] = first_unit.get('sqft', 'N/A')
                    processed_listing['units_count'] = len(units)
                    processed_listing['all_units'] = units
                else:
                    processed_listing = listing.copy()
                    processed_listing['unit_price'] = listing.get('price', 'N/A')
                    processed_listing['unit_beds'] = listing.get('beds', 'N/A')
                    processed_listing['unit_baths'] = listing.get('baths', 'N/A')
                    processed_listing['unit_sqft'] = listing.get('sqft', 'N/A')
                    processed_listing['units_count'] = 0
                    processed_listing['all_units'] = []
                
                processed_results.append(processed_listing)
            
            full_data.extend(processed_results)
            logger.info(f"Rental page {page} completed - {len(processed_results)} results")
            page += 1
        
        # Store results
        task_results[task_id] = {
            "success": True,
            "location": location,
            "total_results": len(full_data),
            "total_available": total_results,
            "pages_scraped": page - 1,
            "search_parameters": {
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "sort_by": sort_by
            },
            "results": full_data
        }
        
        update_task_status(
            task_id,
            status="completed",
            completed_at=datetime.now().isoformat(),
            progress=100,
            current_stage="completed",
            current_operation="Scraping completed",
            pages_scraped=page-1,
            results_found=len(full_data)
        )
        
        logger.info(f"✅ Rentals scraping completed for task {task_id}: {len(full_data)} results")
        
    except Exception as e:
        logger.error(f"❌ Rentals scraping failed for task {task_id}: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e),
            current_stage="failed",
            current_operation="Scraping failed"
        )

async def scrape_sales_task(task_id: str, location: str, min_price: int, max_price: int, 
                           min_monthly_payment: int, max_monthly_payment: int, 
                           max_pages: int, sort_by: str):
    """Background task for sales scraping"""
    logger.info(f"🚀 Starting background sales task {task_id}")
    
    try:
        update_task_status(
            task_id,
            status="running",
            started_at=datetime.now().isoformat(),
            current_stage="initializing",
            current_operation="Starting sales scraping"
        )
        
        # Run the synchronous scraping in a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(
                executor,
                run_sales_scraping_sync,
                task_id, location, min_price, max_price,
                min_monthly_payment, max_monthly_payment, max_pages, sort_by
            )
            
    except Exception as e:
        logger.error(f"❌ Background sales task {task_id} failed: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )

async def scrape_rentals_task(task_id: str, location: str, min_price: int, max_price: int, 
                             min_monthly_payment: int, max_monthly_payment: int, 
                             max_pages: int, sort_by: str):
    """Background task for rentals scraping"""
    logger.info(f"🚀 Starting background rentals task {task_id}")
    
    try:
        update_task_status(
            task_id,
            status="running",
            started_at=datetime.now().isoformat(),
            current_stage="initializing",
            current_operation="Starting rentals scraping"
        )
        
        # Run the synchronous scraping in a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(
                executor,
                run_rentals_scraping_sync,
                task_id, location, min_price, max_price,
                min_monthly_payment, max_monthly_payment, max_pages, sort_by
            )
            
    except Exception as e:
        logger.error(f"❌ Background rentals task {task_id} failed: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )

def run_sold_properties_scraping_sync(task_id: str, location: str, min_price: int, max_price: int, 
                                    min_monthly_payment: int, max_monthly_payment: int, 
                                    max_pages: int, sort_by: str):
    """Synchronous sold properties scraping function to run in thread pool"""
    try:
        logger.info(f"🏠 Starting sold properties scraping for task {task_id}")
        
        # Get coordinates for the location
        coords = get_coordinates_for_location(location)
        
        full_data = []
        page = 1
        total_results = 0
        
        while page <= max_pages:
            update_task_status(
                task_id,
                current_stage="scraping",
                current_operation=f"Scraping page {page} of {max_pages}",
                pages_scraped=page-1,
                progress=int((page-1) / max_pages * 100)
            )
            
            # Use the exact JSON structure you provided for sold properties
            json_data = {
                'searchQueryState': {
                    'isMapVisible': True,
                    'mapBounds': coords,
                    'mapZoom': 11,
                    'usersSearchTerm': location,
                    'filterState': {
                        'price': {
                            'min': min_price,
                            'max': max_price,
                        },
                        'monthlyPayment': {
                            'min': min_monthly_payment,
                            'max': max_monthly_payment,
                        },
                        'isForSaleByAgent': {
                            'value': False,
                        },
                        'isForSaleByOwner': {
                            'value': False,
                        },
                        'isNewConstruction': {
                            'value': False,
                        },
                        'isComingSoon': {
                            'value': False,
                        },
                        'isAuction': {
                            'value': False,
                        },
                        'isForSaleForeclosure': {
                            'value': False,
                        },
                        'isRecentlySold': {
                            'value': True,  # This is the key difference for sold properties
                        },
                        'sortSelection': {
                            'value': sort_by,
                        },
                    },
                    'isListVisible': True,
                    'pagination': {'currentPage': page},
                },
                'wants': {
                    'cat1': ['listResults'],
                },
                'requestId': page,
                'isDebugRequest': False,
            }
            
            response = requests.put(
                'https://www.zillow.com/async-create-search-page-state',
                headers=ZILLOW_HEADERS,
                json=json_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Zillow API returned status {response.status_code}")
                break
                
            data = response.json()
            
            if 'cat1' not in data or 'searchResults' not in data['cat1']:
                logger.warning(f"No search results found in response for page {page}")
                break
                
            search_results = data['cat1']['searchResults']
            list_results = search_results.get('listResults', [])
            
            if len(list_results) == 0:
                logger.info(f"No more results found at page {page}")
                break
                
            if page == 1 and 'total' in data.get('cat2', {}):
                total_results = data['cat2']['total']
            
            full_data.extend(list_results)
            logger.info(f"Sold properties page {page} completed - {len(list_results)} results")
            page += 1
        
        # Store results
        task_results[task_id] = {
            "success": True,
            "location": location,
            "total_results": len(full_data),
            "total_available": total_results,
            "pages_scraped": page - 1,
            "search_parameters": {
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "sort_by": sort_by
            },
            "results": full_data
        }
        
        update_task_status(
            task_id,
            status="completed",
            completed_at=datetime.now().isoformat(),
            progress=100,
            current_stage="completed",
            current_operation="Scraping completed",
            pages_scraped=page-1,
            results_found=len(full_data)
        )
        
        logger.info(f"✅ Sold properties scraping completed for task {task_id}: {len(full_data)} results")
        
    except Exception as e:
        logger.error(f"❌ Sold properties scraping failed for task {task_id}: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e),
            current_stage="failed",
            current_operation="Scraping failed"
        )

async def scrape_sold_properties_task(task_id: str, location: str, min_price: int, max_price: int, 
                                    min_monthly_payment: int, max_monthly_payment: int, 
                                    max_pages: int, sort_by: str):
    """Background task for sold properties scraping"""
    logger.info(f"🚀 Starting background sold properties task {task_id}")
    
    try:
        update_task_status(
            task_id,
            status="running",
            started_at=datetime.now().isoformat(),
            current_stage="initializing",
            current_operation="Starting sold properties scraping"
        )
        
        # Run the synchronous scraping in a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(
                executor,
                run_sold_properties_scraping_sync,
                task_id, location, min_price, max_price,
                min_monthly_payment, max_monthly_payment, max_pages, sort_by
            )
            
    except Exception as e:
        logger.error(f"❌ Background sold properties task {task_id} failed: {str(e)}")
        update_task_status(
            task_id,
            status="failed",
            completed_at=datetime.now().isoformat(),
            error_message=str(e)
        )

@router.get("/sales")
async def search_sales_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX', 'New York NY')"),
    min_price: int = Query(0, description="Minimum price filter"),
    max_price: int = Query(1000000, description="Maximum price filter"),
    min_monthly_payment: int = Query(0, description="Minimum monthly payment filter"),
    max_monthly_payment: int = Query(5000, description="Maximum monthly payment filter"),
    max_pages: int = Query(10, description="Maximum number of pages to fetch (1-50)"),
    sort_by: str = Query("globalrelevanceex", description="Sort order: globalrelevanceex, newest, lowestprice, highestprice")
):
    """
    Search Zillow properties for sale (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    Use the task ID to check status and get results when completed.
    
    Args:
        location: Location to search for properties for sale
        min_price: Minimum price filter (default: 0)
        max_price: Maximum price filter (default: 1,000,000)
        min_monthly_payment: Minimum monthly payment filter (default: 0)
        max_monthly_payment: Maximum monthly payment filter (default: 5,000)
        max_pages: Maximum number of pages to fetch (default: 10, max: 50)
        sort_by: Sort order for results (default: globalrelevanceex)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if min_price < 0:
        min_price = 0
    if max_price < min_price:
        raise HTTPException(status_code=400, detail="max_price must be greater than min_price")
        
    if min_monthly_payment < 0:
        min_monthly_payment = 0
    if max_monthly_payment < min_monthly_payment:
        raise HTTPException(status_code=400, detail="max_monthly_payment must be greater than min_monthly_payment")
    
    # Valid sort options
    valid_sorts = ["globalrelevanceex", "newest", "lowestprice", "highestprice"]
    if sort_by not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sorts)}")
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="sales",
            location=location,
            search_parameters={
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "max_pages": max_pages,
                "sort_by": sort_by
            },
            message=f"Queued sales search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_sales_task,
            task_id, location, min_price, max_price,
            min_monthly_payment, max_monthly_payment, max_pages, sort_by
        )
        
        logger.info(f"✅ Async sales task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Sales search task queued successfully",
            "location": location,
            "search_type": "sales",
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_sales_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/rentals")
async def search_rentals_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX')"),
    min_price: int = Query(0, description="Minimum rent price filter"),
    max_price: int = Query(5000, description="Maximum rent price filter"),
    min_monthly_payment: int = Query(0, description="Minimum monthly payment filter"),
    max_monthly_payment: int = Query(5000, description="Maximum monthly payment filter"),
    max_pages: int = Query(10, description="Maximum number of pages to fetch (1-50)"),
    sort_by: str = Query("globalrelevanceex", description="Sort order: globalrelevanceex, newest, lowestprice, highestprice")
):
    """
    Search Zillow rental properties (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    Use the task ID to check status and get results when completed.
    
    Args:
        location: Location to search for rental properties
        min_price: Minimum rent price filter (default: 0)
        max_price: Maximum rent price filter (default: 5,000)
        min_monthly_payment: Minimum monthly payment filter (default: 0)
        max_monthly_payment: Maximum monthly payment filter (default: 5,000)
        max_pages: Maximum number of pages to fetch (default: 10, max: 50)
        sort_by: Sort order for results (default: globalrelevanceex)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if min_price < 0:
        min_price = 0
    if max_price < min_price:
        raise HTTPException(status_code=400, detail="max_price must be greater than min_price")
        
    if min_monthly_payment < 0:
        min_monthly_payment = 0
    if max_monthly_payment < min_monthly_payment:
        raise HTTPException(status_code=400, detail="max_monthly_payment must be greater than min_monthly_payment")
    
    # Valid sort options
    valid_sorts = ["globalrelevanceex", "newest", "lowestprice", "highestprice"]
    if sort_by not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sorts)}")
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="rentals",
            location=location,
            search_parameters={
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "max_pages": max_pages,
                "sort_by": sort_by
            },
            message=f"Queued rentals search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_rentals_task,
            task_id, location, min_price, max_price,
            min_monthly_payment, max_monthly_payment, max_pages, sort_by
        )
        
        logger.info(f"✅ Async rentals task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Rentals search task queued successfully",
            "location": location,
            "search_type": "rentals",
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_rentals_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/rentals/simple")
async def search_rentals_simple_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX')"),
    max_price: int = Query(3000, description="Maximum rent price filter"),
    max_pages: int = Query(5, description="Maximum number of pages to fetch")
):
    """
    Simplified Zillow rental search (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    This is a simplified version with basic parameters for quick searches.
    
    Args:
        location: Location to search for rental properties
        max_price: Maximum rent price filter (default: 3,000)
        max_pages: Maximum number of pages to fetch (default: 5)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if max_price < 0:
        max_price = 0
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated simple rentals task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="rentals_simple",
            location=location,
            search_parameters={
                "min_price": 0,
                "max_price": max_price,
                "min_monthly_payment": 0,
                "max_monthly_payment": max_price,
                "max_pages": max_pages,
                "sort_by": "globalrelevanceex"
            },
            message=f"Queued simple rentals search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_rentals_task,
            task_id, location, 0, max_price,
            0, max_price, max_pages, "globalrelevanceex"
        )
        
        logger.info(f"✅ Async simple rentals task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Simple rentals search task queued successfully",
            "location": location,
            "search_type": "rentals_simple",
            "max_price": max_price,
            "max_pages": max_pages,
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_rentals_simple_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sales/simple")
async def search_sales_simple_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX')"),
    max_price: int = Query(500000, description="Maximum price filter"),
    max_pages: int = Query(5, description="Maximum number of pages to fetch")
):
    """
    Simplified Zillow property search (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    This is a simplified version with basic parameters for quick searches.
    
    Args:
        location: Location to search for properties for sale
        max_price: Maximum price filter (default: 500,000)
        max_pages: Maximum number of pages to fetch (default: 5)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if max_price < 0:
        max_price = 0
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated simple sales task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="sales_simple",
            location=location,
            search_parameters={
                "min_price": 0,
                "max_price": max_price,
                "min_monthly_payment": 0,
                "max_monthly_payment": max_price // 12,  # Convert to monthly
                "max_pages": max_pages,
                "sort_by": "globalrelevanceex"
            },
            message=f"Queued simple sales search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_sales_task,
            task_id, location, 0, max_price,
            0, max_price // 12, max_pages, "globalrelevanceex"
        )
        
        logger.info(f"✅ Async simple sales task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Simple sales search task queued successfully",
            "location": location,
            "search_type": "sales_simple",
            "max_price": max_price,
            "max_pages": max_pages,
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_sales_simple_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sold")
async def search_sold_properties_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX', 'New York NY')"),
    min_price: int = Query(0, description="Minimum price filter"),
    max_price: int = Query(1000000, description="Maximum price filter"),
    min_monthly_payment: int = Query(0, description="Minimum monthly payment filter"),
    max_monthly_payment: int = Query(5000, description="Maximum monthly payment filter"),
    max_pages: int = Query(10, description="Maximum number of pages to fetch (1-50)"),
    sort_by: str = Query("globalrelevanceex", description="Sort order: globalrelevanceex, newest, lowestprice, highestprice")
):
    """
    Search Zillow sold properties (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    This searches for recently sold properties in the specified location.
    
    Args:
        location: Location to search for sold properties
        min_price: Minimum price filter (default: 0)
        max_price: Maximum price filter (default: 1,000,000)
        min_monthly_payment: Minimum monthly payment filter (default: 0)
        max_monthly_payment: Maximum monthly payment filter (default: 5,000)
        max_pages: Maximum number of pages to fetch (default: 10, max: 50)
        sort_by: Sort order for results (default: globalrelevanceex)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if min_price < 0:
        min_price = 0
    if max_price < min_price:
        raise HTTPException(status_code=400, detail="max_price must be greater than min_price")
        
    if min_monthly_payment < 0:
        min_monthly_payment = 0
    if max_monthly_payment < min_monthly_payment:
        raise HTTPException(status_code=400, detail="max_monthly_payment must be greater than min_monthly_payment")
    
    # Valid sort options
    valid_sorts = ["globalrelevanceex", "newest", "lowestprice", "highestprice"]
    if sort_by not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sorts)}")
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated sold properties task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="sold",
            location=location,
            search_parameters={
                "min_price": min_price,
                "max_price": max_price,
                "min_monthly_payment": min_monthly_payment,
                "max_monthly_payment": max_monthly_payment,
                "max_pages": max_pages,
                "sort_by": sort_by
            },
            message=f"Queued sold properties search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_sold_properties_task,
            task_id, location, min_price, max_price,
            min_monthly_payment, max_monthly_payment, max_pages, sort_by
        )
        
        logger.info(f"✅ Async sold properties task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Sold properties search task queued successfully",
            "location": location,
            "search_type": "sold",
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_sold_properties_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sold/simple")
async def search_sold_properties_simple_async(
    background_tasks: BackgroundTasks,
    location: str = Query(..., description="Location to search (e.g., 'Austin TX')"),
    max_price: int = Query(800000, description="Maximum price filter"),
    max_pages: int = Query(5, description="Maximum number of pages to fetch")
):
    """
    Simplified Zillow sold properties search (Async).
    
    Returns a task ID immediately and runs scraping in the background.
    This is a simplified version with basic parameters for quick sold property searches.
    
    Args:
        location: Location to search for sold properties
        max_price: Maximum price filter (default: 800,000)
        max_pages: Maximum number of pages to fetch (default: 5)
        
    Returns:
        Task ID and status information
    """
    # Validate parameters
    if max_pages > 50:
        max_pages = 50
    if max_pages < 1:
        max_pages = 1
        
    if max_price < 0:
        max_price = 0
    
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 Generated simple sold properties task ID: {task_id}")
        
        # Create task status
        tasks[task_id] = ZillowTaskStatus(
            task_id=task_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            search_type="sold_simple",
            location=location,
            search_parameters={
                "min_price": 0,
                "max_price": max_price,
                "min_monthly_payment": 0,
                "max_monthly_payment": max_price // 12,  # Convert to monthly
                "max_pages": max_pages,
                "sort_by": "globalrelevanceex"
            },
            message=f"Queued simple sold properties search for: {location}",
            current_stage="pending",
            current_operation="Task queued"
        )
        
        # Add background task
        background_tasks.add_task(
            scrape_sold_properties_task,
            task_id, location, 0, max_price,
            0, max_price // 12, max_pages, "globalrelevanceex"
        )
        
        logger.info(f"✅ Async simple sold properties task {task_id} queued successfully for location: '{location}'")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Simple sold properties search task queued successfully",
            "location": location,
            "search_type": "sold_simple",
            "max_price": max_price,
            "max_pages": max_pages,
            "status_url": f"/zillow/status/{task_id}",
            "results_url": f"/zillow/results/{task_id}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in search_sold_properties_simple_async: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a Zillow scraping task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    # Calculate elapsed time
    elapsed_time = 0
    if task.started_at:
        start_time = datetime.fromisoformat(task.started_at)
        elapsed_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "progress": task.progress,
        "message": task.message,
        "current_stage": task.current_stage,
        "current_operation": task.current_operation,
        "pages_scraped": task.pages_scraped,
        "total_pages": task.total_pages,
        "results_found": task.results_found,
        "elapsed_time_seconds": round(elapsed_time, 2),
        "estimated_remaining_seconds": task.estimated_remaining_seconds,
        "error_message": task.error_message,
        "search_type": task.search_type,
        "location": task.location,
        "search_parameters": task.search_parameters
    }

@router.get("/results/{task_id}")
async def get_task_results(
    task_id: str,
    page: int = Query(1, description="Page number for pagination (starts from 1)", ge=1),
    page_size: int = Query(100, description="Number of results per page", ge=1, le=1000)
):
    """Get paginated results from a completed Zillow scraping task"""
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
    
    if task_id not in task_results:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for task {task_id}"
        )
    
    result_data = task_results[task_id]
    all_results = result_data.get("results", [])
    
    # Apply pagination
    total_items = len(all_results)
    total_pages = (total_items + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get page items
    page_results = all_results[start_idx:end_idx]
    
    # Generate download URLs
    download_urls = {
        "json": f"/zillow/download/{task_id}/json",
        "csv": f"/zillow/download/{task_id}/csv"
    }
    
    return {
        "task_id": task_id,
        "status": "completed",
        "search_type": task.search_type,
        "location": task.location,
        "total_results": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "results": page_results,
        "pagination": {
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None
        },
        "download_urls": download_urls,
        "search_parameters": task.search_parameters
    }

@router.get("/download/{task_id}/json")
async def download_results_json(task_id: str):
    """Download Zillow scraping results as JSON file"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed" or task_id not in task_results:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed or has no results"
        )
    
    result_data = task_results[task_id]
    
    # Generate filename
    filename = get_download_filename(task.location, "json", task.search_type)
    
    # Create download data
    download_data = {
        "task_id": task_id,
        "search_type": task.search_type,
        "location": task.location,
        "total_results": result_data.get("total_results", 0),
        "pages_scraped": result_data.get("pages_scraped", 0),
        "scraped_time": task.completed_at,
        "search_parameters": task.search_parameters,
        "results": result_data.get("results", []),
        "download_info": {
            "format": "JSON",
            "download_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "task_id": task_id
        }
    }
    
    return JSONResponse(
        content=download_data,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/json"
        }
    )

@router.get("/download/{task_id}/csv")
async def download_results_csv(task_id: str):
    """Download Zillow scraping results as CSV file"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed" or task_id not in task_results:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed or has no results"
        )
    
    result_data = task_results[task_id]
    results = result_data.get("results", [])
    
    # Convert to CSV
    csv_content = convert_results_to_csv(results, task.search_type)
    
    # Generate filename
    filename = get_download_filename(task.location, "csv", task.search_type)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv"
        }
    )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Zillow router"""
    return {
        "status": "healthy",
        "service": "Zillow Real Estate Search",
        "endpoints": [
            "GET /zillow/sales - Search properties for sale (Async)",
            "GET /zillow/sales/simple - Simple property sales search (Async)",
            "GET /zillow/rentals - Search rental properties (Async)",
            "GET /zillow/rentals/simple - Simple rental search (Async)",
            "GET /zillow/sold - Search sold properties (Async)",
            "GET /zillow/sold/simple - Simple sold properties search (Async)",
            "GET /zillow/status/{task_id} - Get task status",
            "GET /zillow/results/{task_id} - Get paginated results",
            "GET /zillow/download/{task_id}/json - Download results as JSON",
            "GET /zillow/download/{task_id}/csv - Download results as CSV",
            "GET /zillow/health - Health check"
        ]
    }
