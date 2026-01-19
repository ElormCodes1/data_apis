"""
Realtor.com Real Estate Search Router
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import curl_cffi
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

# Base headers - common across all requests
BASE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://www.realtor.com',
    'priority': 'u=1, i',
    'rdc-client-version': '3.0.2540',
    'sec-ch-ua': '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    'x-is-bot': 'false',
    'x-rdc-visitor-id': '56b86d6e-6ba8-46d7-93e4-c9088c7e3a12',
}

# Search type configurations
SEARCH_CONFIGS = {
    'for_sale': {
        'rdc-ab-test-client': 'rdc-search-for-sale',
        'rdc-client-name': 'RDC_WEB_SRP_FS_PAGE',
        'referer': 'https://www.realtor.com/realestateandhomes-search/New-York',
        'status': ['for_sale', 'ready_to_build'],
        'has_primary': True,
    },
    'for_rent': {
        'rdc-ab-test-client': 'rdc-search-for-rent',
        'rdc-client-name': 'RDC_WEB_SRP_FR_PAGE',
        'referer': 'https://www.realtor.com/apartments/California/pg-2',
        'status': ['for_rent'],
        'has_primary': True,
    },
    'sold': {
        'rdc-ab-test-client': 'rdc-search-for-sale',
        'rdc-client-name': 'RDC_WEB_SRP_FS_PAGE',
        'referer': 'https://www.realtor.com/realestateandhomes-search/New-York/show-recently-sold',
        'status': ['sold'],
        'has_primary': False,
    }
}

# GraphQL query for for_sale
graphql_query_for_sale = """
query ConsumerSearchQuery($query: HomeSearchCriteria!, $limit: Int, $offset: Int, $search_promotion: SearchPromotionInput, $sort: [SearchAPISort], $sort_type: SearchSortType, $client_data: JSON, $bucket: SearchAPIBucket, $mortgage_params: MortgageParamsInput, $photosLimit: Int) {
  home_search: home_search(
    query: $query
    sort: $sort
    limit: $limit
    offset: $offset
    sort_type: $sort_type
    client_data: $client_data
    bucket: $bucket
    search_promotion: $search_promotion
    mortgage_params: $mortgage_params
  ) {
    count
    total
    search_promotion {
      names
      slots
      promoted_properties {
        id
        from_other_page
      }
    }
    mortgage_params {
      interest_rate
    }
    properties: results {
      property_id
      list_price
      rmn_listing_attribution
      search_promotions {
        name
        asset_id
      }
      primary_photo(https: true) {
        href
      }
      listing_id
      matterport
      virtual_tours {
        href
      }
      status
      products {
        products
        brand_name
      }
      source {
        id
        name
        type
        spec_id
        plan_id
        listing_id
      }
      lead_attributes {
        show_contact_an_agent
        market_type
        lead_type
        is_veterans_united_eligible
      }
      community {
        description {
          name
        }
        property_id
        permalink
        advertisers {
          office {
            hours
            phones {
              type
              number
              primary
              trackable
            }
          }
        }
        promotions {
          description
          href
          headline
          promotion_type
        }
      }
      permalink
      price_reduced_amount
      description {
        name
        beds
        baths_consolidated
        sqft
        lot_sqft
        baths_max
        baths_min
        beds_min
        beds_max
        sqft_min
        sqft_max
        type
        sub_type
        sold_price
        sold_date
        year_built
        garage
      }
      location {
        street_view_url
        address {
          line
          postal_code
          state
          state_code
          city
          coordinate {
            lat
            lon
          }
        }
        county {
          name
          fips_code
        }
      }
      open_houses {
        start_date
        end_date
        description
        time_zone
        dst
      }
      branding {
        type
        name
        photo
      }
      flags {
        is_coming_soon
        is_new_listing(days: 14)
        is_price_reduced(days: 30)
        is_foreclosure
        is_new_construction
        is_pending
        is_contingent
      }
      list_date
      photos(limit: $photosLimit, https: true) {
        href
      }
      advertisers {
        type
        fulfillment_id
        name
        builder {
          name
          href
          logo
          fulfillment_id
        }
        email
        office {
          name
        }
        phones {
          number
        }
      }
    }
    sort_model
    experiment {
      experiment_name
      experiment_variant
      experiment_key
    }
  }
  commute_polygon: get_commute_polygon(query: $query) {
    areas {
      id
      breakpoints {
        width
        height
        zoom
      }
      radius
      center {
        lat
        lng
      }
    }
    boundary
  }
}
""".strip()

# GraphQL query for for_rent
graphql_query_for_rent = """
query ConsumerSearchQuery($query: HomeSearchCriteria!, $limit: Int, $offset: Int, $sort: [SearchAPISort], $sort_type: SearchSortType, $bucket: SearchAPIBucket, $search_promotion: SearchPromotionInput) {
  home_search(
    query: $query
    sort: $sort
    limit: $limit
    offset: $offset
    bucket: $bucket
    search_promotion: $search_promotion
    sort_type: $sort_type
  ) {
    costar_counts {
      costar_total
      non_costar_total
    }
    total
    count
    sort_model
    search_promotion {
      name
      names
      slots
      promoted_properties {
        id
        from_other_page
      }
    }
    properties: results {
      property_id
      listing_id
      list_price
      list_price_max
      list_price_min
      permalink
      price_reduced_amount
      matterport
      has_specials
      application_url
      status
      list_date
      available_date_change_timestamp
      branding {
        type
        photo
        name
      }
      source {
        id
        community_id
        type
        feed_type
      }
      details {
        category
        text
      }
      products {
        products
        brand_name
      }
      rentals_application_eligibility {
        estimated_status
      }
      flags {
        is_pending
        is_new_listing
        has_new_availability
      }
      photos(limit: 3, https: true) {
        href
      }
      primary_photo(https: true) {
        href
      }
      search_promotions {
        name
        asset_id
      }
      virtual_tours {
        href
      }
      lead_attributes {
        lead_type
        is_premium_ldp
        is_schedule_a_tour
      }
      pet_policy {
        cats
        dogs
        dogs_small
        dogs_large
      }
      description {
        beds
        beds_max
        beds_min
        baths_min
        baths_max
        baths_consolidated
        baths
        sqft
        sqft_max
        sqft_min
        name
        sub_type
        type
      }
      other_listings {
        rdc {
          listing_id
          status
        }
      }
      advertisers {
        type
        office {
          name
        }
        rental_management {
          logo
        }
      }
      location {
        address {
          line
          city
          coordinate {
            lat
            lon
          }
          country
          state_code
          postal_code
        }
        county {
          name
        }
      }
      units {
        availability {
          date
        }
        description {
          baths_consolidated
          baths
          beds
          sqft
        }
        list_price
      }
    }
  }
}
""".strip()


def get_headers(search_type: str) -> dict:
    """Get headers for the specified search type"""
    config = SEARCH_CONFIGS.get(search_type)
    if not config:
        raise ValueError(f"Invalid search_type: {search_type}")
    
    headers = BASE_HEADERS.copy()
    headers['rdc-ab-test-client'] = config['rdc-ab-test-client']
    headers['rdc-client-name'] = config['rdc-client-name']
    headers['referer'] = config['referer']
    return headers


def get_graphql_query(search_type: str) -> str:
    """Get GraphQL query for the specified search type"""
    if search_type == 'for_sale':
        return graphql_query_for_sale
    elif search_type == 'for_rent':
        return graphql_query_for_rent
    elif search_type == 'sold':
        return graphql_query_for_sale  # Sold uses the same query as for_sale
    else:
        raise ValueError(f"Invalid search_type: {search_type}")


def search_realtor_properties(
    location: str,
    search_type: str = 'for_sale',
    limit: int = 64,
    page: int = 1,
    sort_type: str = "relevant",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_beds: Optional[int] = None,
    max_beds: Optional[int] = None,
    min_baths: Optional[float] = None,
    max_baths: Optional[float] = None,
    min_sqft: Optional[int] = None,
    max_sqft: Optional[int] = None,
    property_type: Optional[str] = None,
    min_year_built: Optional[int] = None,
    max_year_built: Optional[int] = None,
    min_sold_date: Optional[str] = None,
    max_sold_date: Optional[str] = None
) -> dict:
    """
    Base function to search Realtor.com properties using GraphQL API.
    
    Args:
        location: Location to search (e.g., "New York", "Austin TX")
        search_type: Type of search - 'for_sale', 'for_rent', or 'sold' (default: 'for_sale')
        limit: Maximum number of results to return per page (default: 64)
        page: Page number for pagination (default: 1)
        sort_type: Sort order (default: "relevant")
        min_price: Minimum price filter
        max_price: Maximum price filter
        min_beds: Minimum number of bedrooms
        max_beds: Maximum number of bedrooms
        min_baths: Minimum number of bathrooms
        max_baths: Maximum number of bathrooms
        min_sqft: Minimum square footage
        max_sqft: Maximum square footage
        property_type: Property type (e.g., "condos", "single_family", "townhomes")
        min_year_built: Minimum year built
        max_year_built: Maximum year built
        min_sold_date: Minimum sold date (ISO format, e.g., "2025-07-19T19:58:49.868Z")
        max_sold_date: Maximum sold date (ISO format, e.g., "2025-07-19T19:58:49.868Z")
        
    Returns:
        Dictionary containing properties array and metadata
    """
    # Get search configuration
    config = SEARCH_CONFIGS.get(search_type)
    if not config:
        raise ValueError(f"Invalid search_type: {search_type}. Must be 'for_sale', 'for_rent', or 'sold'")
    
    status_list = config['status']
    has_primary = config.get('has_primary', True)
    photos_limit = 3
    
    # Calculate offset based on page number
    offset = limit * (page - 1)
    
    # Build query object with filters
    query_obj = {
        'status': status_list,
            'search_location': {
            'location': location,
        },
    }
    
    # Add primary flag only for for_sale and for_rent
    if has_primary:
        query_obj['primary'] = True
    
    # Add price filters if provided
    if min_price is not None or max_price is not None:
        query_obj['price'] = {}
        if min_price is not None:
            query_obj['price']['min'] = min_price
        if max_price is not None:
            query_obj['price']['max'] = max_price
    
    # Add bedroom filters if provided
    if min_beds is not None or max_beds is not None:
        query_obj['beds'] = {}
        if min_beds is not None:
            query_obj['beds']['min'] = min_beds
        if max_beds is not None:
            query_obj['beds']['max'] = max_beds
    
    # Add bathroom filters if provided
    if min_baths is not None or max_baths is not None:
        query_obj['baths'] = {}
        if min_baths is not None:
            query_obj['baths']['min'] = min_baths
        if max_baths is not None:
            query_obj['baths']['max'] = max_baths
    
    # Add square footage filters if provided
    if min_sqft is not None or max_sqft is not None:
        query_obj['sqft'] = {}
        if min_sqft is not None:
            query_obj['sqft']['min'] = min_sqft
        if max_sqft is not None:
            query_obj['sqft']['max'] = max_sqft
    
    # Add property type filter if provided
    if property_type:
        query_obj['type'] = property_type
    
    # Add year built filters if provided (only for for_sale and sold)
    if search_type in ['for_sale', 'sold'] and (min_year_built is not None or max_year_built is not None):
        query_obj['year_built'] = {}
        if min_year_built is not None:
            query_obj['year_built']['min'] = min_year_built
        if max_year_built is not None:
            query_obj['year_built']['max'] = max_year_built
    
    # Add sold date filters (required for sold, always include at least min)
    if search_type == 'sold':
        query_obj['sold_date'] = {}
        if min_sold_date is not None:
            query_obj['sold_date']['min'] = min_sold_date
        else:
            # Default to a date in the past if not provided (e.g., 1 year ago)
            default_min_date = (datetime.now() - timedelta(days=365)).isoformat() + 'Z'
            query_obj['sold_date']['min'] = default_min_date
        if max_sold_date is not None:
            query_obj['sold_date']['max'] = max_sold_date
    
    # Build variables based on search type
    variables = {
        'query': query_obj,
        'limit': limit,
        'offset': offset,
    }
    
    # Add search type specific variables
    if search_type == 'for_sale':
        variables['photosLimit'] = photos_limit
        variables['sort_type'] = sort_type
        variables['client_data'] = {
            'device_data': {
                'device_type': 'desktop',
            },
        }
    elif search_type == 'for_rent':
        variables['sort_type'] = sort_type
        variables['bucket'] = {
            'sort': 'fractal_v6.2.1_fr',
        }
    elif search_type == 'sold':
        variables['photosLimit'] = photos_limit
        variables['client_data'] = {
            'device_data': {
                'device_type': 'desktop',
            },
        }
        # Always include sort for sold: sold_date desc, photo_count desc
        # Note: sold requests use 'sort' instead of 'sort_type'
        variables['sort'] = [
            {
                'field': 'sold_date',
                'direction': 'desc',
            },
            {
                'field': 'photo_count',
                'direction': 'desc',
            },
        ]
    
    json_data = {
        'operationName': 'ConsumerSearchQuery',
        'variables': variables,
        'query': get_graphql_query(search_type),
    }
    
    try:
        headers = get_headers(search_type)
        response = curl_cffi.post(
            'https://www.realtor.com/frontdoor/graphql',
            headers=headers,
            json=json_data,
            timeout=30
        )
        response.raise_for_status()
        
        response_data = response.json()
        
        # Check for errors in response
        if 'errors' in response_data:
            error_messages = [err.get('message', 'Unknown error') for err in response_data.get('errors', [])]
            logger.error(f"GraphQL errors: {error_messages}")
            raise HTTPException(status_code=500, detail=f"GraphQL errors: {', '.join(error_messages)}")
        
        # Extract properties and metadata from the response
        data = response_data.get('data')
        if data is None:
            logger.error(f"Response data is None. Full response: {response_data}")
            raise HTTPException(status_code=500, detail="Invalid response from Realtor.com: missing data")
        
        home_search = data.get('home_search')
        if home_search is None:
            logger.error(f"home_search is None. Full response data: {data}")
            raise HTTPException(status_code=500, detail="Invalid response from Realtor.com: missing home_search")
        
        properties = home_search.get('properties', [])
        
        # Calculate pagination info
        total_results = home_search.get('total', 0)
        total_pages = (total_results + limit - 1) // limit if total_results > 0 else 0
        
        return {
            'success': True,
            'search_type': search_type,
            'location': location,
            'count': home_search.get('count', 0),
            'total': total_results,
            'page': page,
            'limit': limit,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'properties': properties,
            'search_parameters': {
                'sort_type': sort_type,
                'status': status_list,
                'filters': {
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_beds': min_beds,
                    'max_beds': max_beds,
                    'min_baths': min_baths,
                    'max_baths': max_baths,
                    'min_sqft': min_sqft,
                    'max_sqft': max_sqft,
                    'property_type': property_type,
                    'min_year_built': min_year_built if search_type in ['for_sale', 'sold'] else None,
                    'max_year_built': max_year_built if search_type in ['for_sale', 'sold'] else None,
                    'min_sold_date': min_sold_date if search_type == 'sold' else None,
                    'max_sold_date': max_sold_date if search_type == 'sold' else None,
                }
            }
        }
        
    except curl_cffi.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data from Realtor.com: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid response from Realtor.com")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/for-sale")
async def search_for_sale(
    location: str = Query(..., description="Location to search (e.g., 'New York', 'Austin TX')"),
    limit: int = Query(64, description="Maximum number of results per page", ge=1, le=200),
    page: int = Query(1, description="Page number for pagination (starts from 1)", ge=1),
    sort_type: str = Query("relevant", description="Sort order: relevant, price_asc, price_desc, newest"),
    min_price: Optional[int] = Query(None, description="Minimum price filter", ge=0),
    max_price: Optional[int] = Query(None, description="Maximum price filter", ge=0),
    min_beds: Optional[int] = Query(None, description="Minimum number of bedrooms", ge=0),
    max_beds: Optional[int] = Query(None, description="Maximum number of bedrooms", ge=0),
    min_baths: Optional[float] = Query(None, description="Minimum number of bathrooms", ge=0),
    max_baths: Optional[float] = Query(None, description="Maximum number of bathrooms", ge=0),
    min_sqft: Optional[int] = Query(None, description="Minimum square footage", ge=0),
    max_sqft: Optional[int] = Query(None, description="Maximum square footage", ge=0),
    property_type: Optional[str] = Query(None, description="Property type (e.g., 'condos', 'single_family', 'townhomes')"),
    min_year_built: Optional[int] = Query(None, description="Minimum year built", ge=1800),
    max_year_built: Optional[int] = Query(None, description="Maximum year built", ge=1800)
):
    """
    Search Realtor.com properties for sale with advanced filters.
    """
    try:
        result = search_realtor_properties(
            location=location,
            search_type='for_sale',
            limit=limit,
            page=page,
            sort_type=sort_type,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            max_beds=max_beds,
            min_baths=min_baths,
            max_baths=max_baths,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            property_type=property_type,
            min_year_built=min_year_built,
            max_year_built=max_year_built
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in search_for_sale: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/for-rent")
async def search_for_rent(
    location: str = Query(..., description="Location to search (e.g., 'New York', 'Austin TX')"),
    limit: int = Query(64, description="Maximum number of results per page", ge=1, le=200),
    page: int = Query(1, description="Page number for pagination (starts from 1)", ge=1),
    sort_type: str = Query("relevant", description="Sort order: relevant, price_asc, price_desc, newest"),
    min_price: Optional[int] = Query(None, description="Minimum price filter", ge=0),
    max_price: Optional[int] = Query(None, description="Maximum price filter", ge=0),
    min_beds: Optional[int] = Query(None, description="Minimum number of bedrooms", ge=0),
    max_beds: Optional[int] = Query(None, description="Maximum number of bedrooms", ge=0),
    min_baths: Optional[float] = Query(None, description="Minimum number of bathrooms", ge=0),
    max_baths: Optional[float] = Query(None, description="Maximum number of bathrooms", ge=0),
    min_sqft: Optional[int] = Query(None, description="Minimum square footage", ge=0),
    max_sqft: Optional[int] = Query(None, description="Maximum square footage", ge=0),
    property_type: Optional[str] = Query(None, description="Property type (e.g., 'condos', 'single_family', 'townhomes')")
):
    """
    Search Realtor.com properties for rent with advanced filters.
    """
    try:
        result = search_realtor_properties(
            location=location,
            search_type='for_rent',
            limit=limit,
            page=page,
            sort_type=sort_type,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            max_beds=max_beds,
            min_baths=min_baths,
            max_baths=max_baths,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            property_type=property_type
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in search_for_rent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/sold")
async def search_sold(
    location: str = Query(..., description="Location to search (e.g., 'New York', 'Austin TX')"),
    limit: int = Query(64, description="Maximum number of results per page", ge=1, le=200),
    page: int = Query(1, description="Page number for pagination (starts from 1)", ge=1),
    sort_type: str = Query("relevant", description="Sort order: relevant, price_asc, price_desc, newest"),
    min_price: Optional[int] = Query(None, description="Minimum price filter", ge=0),
    max_price: Optional[int] = Query(None, description="Maximum price filter", ge=0),
    min_beds: Optional[int] = Query(None, description="Minimum number of bedrooms", ge=0),
    max_beds: Optional[int] = Query(None, description="Maximum number of bedrooms", ge=0),
    min_baths: Optional[float] = Query(None, description="Minimum number of bathrooms", ge=0),
    max_baths: Optional[float] = Query(None, description="Maximum number of bathrooms", ge=0),
    min_sqft: Optional[int] = Query(None, description="Minimum square footage", ge=0),
    max_sqft: Optional[int] = Query(None, description="Maximum square footage", ge=0),
    property_type: Optional[str] = Query(None, description="Property type (e.g., 'condos', 'single_family', 'townhomes')"),
    min_year_built: Optional[int] = Query(None, description="Minimum year built", ge=1800),
    max_year_built: Optional[int] = Query(None, description="Maximum year built", ge=1800),
    min_sold_date: Optional[str] = Query(None, description="Minimum sold date (ISO format, e.g., '2025-07-19T19:58:49.868Z')"),
    max_sold_date: Optional[str] = Query(None, description="Maximum sold date (ISO format, e.g., '2025-07-19T19:58:49.868Z')")
):
    """
    Search Realtor.com sold properties with advanced filters.
    """
    try:
        result = search_realtor_properties(
            location=location,
            search_type='sold',
            limit=limit,
            page=page,
            sort_type=sort_type,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            max_beds=max_beds,
            min_baths=min_baths,
            max_baths=max_baths,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            property_type=property_type,
            min_year_built=min_year_built,
            max_year_built=max_year_built,
            min_sold_date=min_sold_date,
            max_sold_date=max_sold_date
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in search_sold: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/")
async def realtor_info():
    """Realtor.com API information"""
    return {
        "service": "Realtor.com Real Estate Search",
        "description": "Search Realtor.com properties by location with advanced filters",
        "endpoints": {
            "/for-sale": "Search Realtor.com properties for sale",
            "/for-rent": "Search Realtor.com properties for rent",
            "/sold": "Search Realtor.com sold properties",
            "common_parameters": {
                "location": "Location to search (required, e.g., 'New York', 'Austin TX')",
                "limit": "Maximum number of results per page (optional, default: 64, max: 200)",
                "page": "Page number for pagination (optional, default: 1)",
                "sort_type": "Sort order (optional, default: 'relevant')",
                "min_price": "Minimum price filter (optional)",
                "max_price": "Maximum price filter (optional)",
                "min_beds": "Minimum number of bedrooms (optional)",
                "max_beds": "Maximum number of bedrooms (optional)",
                "min_baths": "Minimum number of bathrooms (optional)",
                "max_baths": "Maximum number of bathrooms (optional)",
                "min_sqft": "Minimum square footage (optional)",
                "max_sqft": "Maximum square footage (optional)",
                "property_type": "Property type (optional, e.g., 'condos', 'single_family', 'townhomes')"
            },
            "for_sale_and_sold_parameters": {
                "min_year_built": "Minimum year built (optional)",
                "max_year_built": "Maximum year built (optional)"
            },
            "sold_only_parameters": {
                "min_sold_date": "Minimum sold date (ISO format, optional)",
                "max_sold_date": "Maximum sold date (ISO format, optional)"
            }
        }
    }
