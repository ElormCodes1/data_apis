"""
Facebook Marketplace Search Router
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import requests
import json
from typing import Optional

router = APIRouter()

def get_coordinates_from_location(city: str, country: str) -> tuple[float, float]:
    """
    Get coordinates from city and country using GPS coordinates API.
    
    Args:
        city (str): City name
        country (str): Country name
        
    Returns:
        tuple[float, float]: Latitude and longitude
    """
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.7',
        'priority': 'u=1, i',
        'referer': 'https://www.gps-coordinates.net/',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    
    # Handle cases where only city or only country is provided
    location_query = f"{city or ''}, {country or ''}".strip(', ')
    
    params = {
        'q': location_query,
        'language': 'en',
    }
    
    try:
        response = requests.get('https://www.gps-coordinates.net/geoproxy', params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('results') or len(data['results']) == 0:
            raise HTTPException(status_code=400, detail=f"Location '{location_query}' not found")
        
        lat = data['results'][0]['geometry']['lat']
        lon = data['results'][0]['geometry']['lng']
        
        return lat, lon
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error getting coordinates: {str(e)}")

def get_coordinates_from_ip(ip: str) -> tuple[float, float]:
    """
    Get coordinates from IP address using IP-API.
    
    Args:
        ip (str): IP address
        
    Returns:
        tuple[float, float]: Latitude and longitude
    """
    # Handle localhost/private IPs by using a default location
    if ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith('192.168.') or ip.startswith('10.'):
        # Use a default location (London) for localhost/private IPs
        return 51.5074, -0.1278  # London coordinates
    
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Origin': 'https://ip-api.com',
        'Referer': 'https://ip-api.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    
    try:
        response = requests.get(f'https://demo.ip-api.com/json/{ip}', headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get('status') == 'fail':
            raise HTTPException(status_code=400, detail=f"Invalid IP address: {ip}")
        
        lat = data['lat']
        lon = data['lon']
        
        return lat, lon
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error getting coordinates from IP: {str(e)}")

def search_facebook_marketplace(lat: float, lon: float, query: str = "bicycle", count: int = 48) -> dict:
    """
    Search Facebook Marketplace using coordinates.
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        query (str): Search query
        count (int): Number of results to return
        
    Returns:
        dict: Facebook Marketplace search results
    """
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.facebook.com',
        'priority': 'u=1, i',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-full-version-list': '"Not)A;Brand";v="8.0.0.0", "Chromium";v="138.0.7204.261", "Google Chrome";v="138.0.7204.261"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"15.6.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }
    
    data = {
        'variables': json.dumps({
            "buyLocation": {"latitude": lat, "longitude": lon},
            "contextual_data": None,
            "count": count,
            "cursor": None,
            "params": {
                "bqf": {
                    "callsite": "COMMERCE_MKTPLACE_WWW",
                    "query": query
                },
                "browse_request_params": {
                    "commerce_enable_local_pickup": True,
                    "commerce_enable_shipping": True,
                    "commerce_search_and_rp_available": True,
                    "commerce_search_and_rp_category_id": [],
                    "commerce_search_and_rp_condition": None,
                    "commerce_search_and_rp_ctime_days": None,
                    "filter_location_latitude": lat,
                    "filter_location_longitude": lon,
                    "filter_price_lower_bound": 0,
                    "filter_price_upper_bound": 214748364700,
                    "filter_radius_km": 250
                },
                "custom_request_params": {
                    "browse_context": None,
                    "contextual_filters": [],
                    "referral_code": None,
                    "referral_ui_component": None,
                    "saved_search_strid": None,
                    "search_vertical": "C2C",
                    "seo_url": None,
                    "serp_landing_settings": {"virtual_category_id": ""},
                    "surface": "SEARCH",
                    "virtual_contextual_filters": []
                }
            },
            "savedSearchID": None,
            "savedSearchQuery": "",
            "scale": 2,
            "shouldIncludePopularSearches": True
        }),
        'doc_id': '31187202734261751',
    }
    
    try:
        response = requests.post('https://www.facebook.com/api/graphql/', headers=headers, data=data)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Facebook API returned status {response.status_code}")
        
        data = response.json()
        return data
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error searching Facebook Marketplace: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON response from Facebook: {str(e)}")

def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers first (for proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host

@router.get("/search")
async def search_marketplace(
    request: Request,
    query: str = "bicycle",
    city: Optional[str] = None,
    country: Optional[str] = None,
    count: int = 24
):
    """
    Search Facebook Marketplace.
    
    Args:
        request: FastAPI request object
        query: Search query (default: "bicycle")
        city: Optional city name
        country: Optional country name
        count: Number of results to return (default: 24)
        
    Returns:
        JSON response with marketplace results
    """
    try:
        # Determine coordinates
        if city or country:
            # Use provided location (city, country, or both)
            location_query = f"{city or ''}, {country or ''}".strip(', ')
            lat, lon = get_coordinates_from_location(city or '', country or '')
            location_source = location_query
        else:
            # Use IP geolocation
            client_ip = get_client_ip(request)
            lat, lon = get_coordinates_from_ip(client_ip)
            location_source = f"IP: {client_ip}"
        
        # Search Facebook Marketplace
        marketplace_data = search_facebook_marketplace(lat, lon, query, count)
        
        # Extract and format results
        if 'data' not in marketplace_data or 'marketplace_search' not in marketplace_data['data']:
            raise HTTPException(status_code=500, detail="Invalid response from Facebook Marketplace")
        
        feed_units = marketplace_data['data']['marketplace_search']['feed_units']
        edges = feed_units.get('edges', [])
        
        results = []
        for item in edges:
            listing = item.get('node', {}).get('listing', {})
            
            result = {
                "name": listing.get('marketplace_listing_title', ''),
                "price": listing.get('listing_price', {}).get('formatted_amount', ''),
                "url": f"https://www.facebook.com/marketplace/item/{listing.get('id', '')}",
                "image": listing.get('primary_listing_photo', {}).get('image', {}).get('uri', ''),
                "delivery_types": listing.get('delivery_types', []),
                "location": listing.get('location', {}).get('reverse_geocode', {}).get('city_page', {}).get('display_name', '')
            }
            results.append(result)
        
        # Get pagination info
        page_info = feed_units.get('page_info', {})
        
        return {
            "success": True,
            "query": query,
            "location": {
                "source": location_source,
                "coordinates": {"latitude": lat, "longitude": lon}
            },
            "results": results,
            "pagination": {
                "has_next_page": page_info.get('has_next_page', False),
                "end_cursor": page_info.get('end_cursor'),
                "count": len(results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/")
async def facebook_marketplace_info():
    """Facebook Marketplace API information"""
    return {
        "service": "Facebook Marketplace Search",
        "description": "Search Facebook Marketplace by location or IP geolocation",
        "endpoints": {
            "/search": "Search Facebook Marketplace",
            "parameters": {
                "query": "Search query (optional, default: 'bicycle')",
                "city": "City name (optional)",
                "country": "Country name (optional)",
                "count": "Number of results (optional, default: 48)"
            },
            "location_logic": {
                "if_city_and_country_provided": "Use those coordinates",
                "if_neither_provided": "Use client IP for geolocation"
            }
        }
    }
