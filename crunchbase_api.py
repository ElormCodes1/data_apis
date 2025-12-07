from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any
import urllib.parse
import json
import logging
from curl_cffi import requests as curl_requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Crunchbase cookies and headers (from testcrunch.py)
COOKIES = {
    'authcookie': 'eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI5MTEyMjE4Mi1hZjNkLTRhZTYtOTg3Ny04MGE5ZjlmZTYxMjciLCJpc3MiOiJ1c2Vyc2VydmljZV9kMWNkMTJlNl8xIiwic3ViIjoiY2EyZWEwYTgtYjBjNy00Y2E1LThkN2QtNWNkYzBkZDFhNjQ3IiwiZXhwIjoxNzY1MTMzNDg2LCJpYXQiOjE3NjUxMzMxODYsInByaXZhdGUiOiJYQW1UU3NleXp1bFo1bkROQU55STk0blIzaENNbTdML3M1cGhnUHpKRWQ3dlBpdDBudjNjL05OTWZlNmE1dUIyVDl4Qnd6Ty8rTWpyYTY5dEVnTlc2MVYvWXBGTUxHclJkR3Y0VFVKa2VtclQyU3pON2tnbE00elAxYUNpbUZsTFZZU0lYaEpxU240UGVPeXRVVXVjZWw4Vm8rR1NRbW1RQkpVaTNVcDY1eng2ZERqV2cwQVFTZ1NoMzB0aWErR1oxODQ0SHRUTTlUc2tPR1F4U2hHbXMwQ3AyRGFnTTkvOTFUdW81dDFKWHI0WkFEaEhyK2RkQ1VqVnhqam1YdkFNdjFTVndzT1BVOTVMZkI5d1g0K1paRjNCVFF6MzRqeDNaeFVuK1daRE44c2NsaDZ5NnJCbkpIU3d4Mm9odWhBVU9TdWVzRWtTbnMycFhvSDQ2SUg5cnJTQjRZQzhWd0w5eVRlTllHNnMwa009IiwicHVibGljIjp7InNlc3Npb25faGFzaCI6IjI1OTM5Nzk1NSJ9fQ.CNas6c-liH_BhcE9m1v7_t2qHIE8qY4zoXqY4e7gf6zIM41i_f_gWZSOGlLYY4emFjXPkUPnSjGeWyfjHHBixg',
    'trustcookie': 'eyJraWQiOiJjcnVuY2hiYXNlIiwiYWxnIjoiUlMyNTYifQ.eyJqdGkiOiI5MTEyMjE4Mi1hZjNkLTRhZTYtOTg3Ny04MGE5ZjlmZTYxMjciLCJpc3MiOiJ1c2Vyc2VydmljZV9kMWNkMTJlNl8xIiwic3ViIjoiY2EyZWEwYTgtYjBjNy00Y2E1LThkN2QtNWNkYzBkZDFhNjQ3IiwiZXhwIjoxNzY1MjE5NTg2LCJpYXQiOjE3NjUxMzMxODYsInNjciI6MH0.IKBFuj1EXk18UEkWLZjUe63VSvQxWafqTRGspWbsQhgb1TnfVoyxEDI71Y_AHjyGgfoAJs6YvbKXr-1T1qOAyUA4G0n6bddvPxM7EMM6m3qZ_C61RCkYCqU8v2SOfvsT3-gZK8NIx-HTriGUhRfsWMRBl8M2R415SdJIXxe7_BDZ6S0Q2-fjMaUtlw7hvzYu_FRlK0VTlK1-pKtQJSZ6l6BB-u-mdMjHfY301vZkBpKQUiRQziUqIhD3Yg4WXedoq9kNUXMV6OT0fltwowru6z5MVDMw5N0igpNEW0TdJ35GYu2Yvtp260biMVm1SnTb3KbQKFryFsq2VVzteUEGBA',
}

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'priority': 'u=1, i',
    'referer': 'https://www.crunchbase.com/organization/bito-ai',
    'sec-ch-ua': '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
    'sec-ch-ua-arch': '"arm"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version-list': '"Chromium";v="142.0.0.0", "Brave";v="142.0.0.0", "Not_A Brand";v="99.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"macOS"',
    'sec-ch-ua-platform-version': '"15.7.1"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    'x-cb-client-app-instance-id': '8233dacb-af4b-4ff8-8547-d00ff2f13c26',
    'x-requested-with': 'XMLHttpRequest',
}


def extract_domain(url_or_query: str) -> str:
    """
    Extract domain from URL or query string.
    Only strips https://www., https://, http://www., or http://.
    Keeps any paths/routes. Removes trailing slash only if it's a bare domain.
    """
    if not url_or_query:
        return ""
    
    url = url_or_query.strip()
    
    # Remove protocol if present (https://www., https://, http://www., http://)
    if url.lower().startswith('https://www.'):
        url = url[12:]  # Remove 'https://www.'
    elif url.lower().startswith('http://www.'):
        url = url[11:]  # Remove 'http://www.'
    elif url.lower().startswith('https://'):
        url = url[8:]   # Remove 'https://'
    elif url.lower().startswith('http://'):
        url = url[7:]   # Remove 'http://'
    
    # Remove trailing slash only if it's a bare domain (no path after domain)
    # After stripping protocol, check if there's a path
    # If url ends with '/' and the first '/' is at the end, it's a trailing slash on bare domain
    if url.endswith('/'):
        # Find the first '/' - if it's at the end (index == len-1), it's a trailing slash on bare domain
        first_slash_index = url.find('/')
        if first_slash_index == len(url) - 1:
            # The only '/' is at the end, so it's a trailing slash on bare domain - remove it
            url = url.rstrip('/')
        # Otherwise, there's a path before the trailing slash, so keep everything
    
    return url


def search_and_match_entities(search_query: str, match_domain: str) -> Dict[str, Any]:
    """
    Helper function to search for entities and find a match based on domain.
    
    Args:
        search_query: The query to search with (domain or name)
        match_domain: The domain to match against entity websites
    
    Returns:
        Company data if match found, empty dict otherwise
    """
    logger.info(f"Searching with query: {search_query}, matching against domain: {match_domain}")
    
    autocomplete_params = {
        'query': search_query,
        'collection_ids': 'organizations',
        'limit': '25',
        'source': 'topSearch',
    }
    
    autocomplete_response = curl_requests.get(
        'https://www.crunchbase.com/v4/data/autocompletes',
        params=autocomplete_params,
        cookies=COOKIES,
        headers=HEADERS,
        impersonate="chrome"
    )
    
    if autocomplete_response.status_code != 200:
        logger.warning(f"Failed to search for company: {autocomplete_response.status_code}")
        return {}
    
    autocomplete_data = autocomplete_response.json()
    
    # Check if we have results
    entities = autocomplete_data.get('entities', [])
    if not entities or len(entities) == 0:
        logger.info(f"No entities found for query: {search_query}")
        return {}
    
    logger.info(f"Found {len(entities)} entities to check")
    
    # Loop through each entity and check if website domain matches
    for entity in entities:
        identifier = entity.get('identifier', {})
        company_permalink = identifier.get('permalink')
        
        if not company_permalink:
            logger.warning(f"Skipping entity without permalink: {entity.get('value', 'unknown')}")
            continue
        
        logger.info(f"Checking entity with permalink: {company_permalink}")
        
        # Fetch detailed company information for this entity
        base_url = f"https://www.crunchbase.com/v4/data/entities/organizations/{company_permalink}"
        
        params = {
            "field_ids": [
                "identifier",
                "layout_id",
                "facet_ids",
                "title",
                "short_description",
                "is_locked",
                "rank_delta_d90",
                "investor_identifiers"
            ],
            "card_ids": [
                "competitors_list",
                "org_similarity_org_list",
                "current_employees_summary",
                "advisors_summary",
                "alumni_summary",
                "recommended_search",
                "company_about_fields2"
            ],
            "layout_mode": "view_v3"
        }
        
        encoded_params = urllib.parse.urlencode({
            "field_ids": json.dumps(params["field_ids"]),
            "card_ids": json.dumps(params["card_ids"]),
            "layout_mode": params["layout_mode"]
        })
        
        url = f"{base_url}?{encoded_params}"
        
        try:
            response = curl_requests.get(
                url,
                cookies=COOKIES,
                headers=HEADERS,
                impersonate="chrome",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch company details for {company_permalink}: {response.status_code}")
                continue
            
            # Parse the JSON response
            company_data = response.json()
            
            # Get the website from company_about_fields2.website.value
            cards = company_data.get("cards", {})
            company_about = cards.get("company_about_fields2", {})
            website_obj = company_about.get("website", {})
            website_url = website_obj.get("value", "")
            
            if not website_url:
                logger.info(f"No website found for entity {company_permalink}")
                continue
            
            # Extract domain from website URL
            website_domain = extract_domain(website_url)
            logger.info(f"Entity {company_permalink} website domain: {website_domain}")
            
            # Compare match domain with website domain
            if match_domain == website_domain:
                logger.info(f"Domain match found! Match domain '{match_domain}' matches website domain '{website_domain}' for entity {company_permalink}")
                return company_data
            else:
                logger.info(f"Domain mismatch for {company_permalink}. Match: '{match_domain}', Website: '{website_domain}'")
                
        except Exception as e:
            logger.warning(f"Error fetching details for entity {company_permalink}: {str(e)}")
            continue
    
    # No match found across all entities
    logger.info(f"No matching domain found. Match domain '{match_domain}' did not match any entity website domains.")
    return {}


@router.get("/crunchbase_info")
async def get_crunchbase_info(
    domain: str = Query(..., description="Company domain to search and match against"),
    name: str = Query(..., description="Company name to search with if domain search fails")
) -> Dict[str, Any]:
    """
    Get Crunchbase company information by domain and name.
    
    This endpoint:
    1. First searches using the domain parameter and checks if any entity's website matches
    2. If no match found, searches using the name parameter and checks for matches
    3. Returns the first entity where the website domain matches the provided domain
    
    Args:
        domain: Company domain to match against (e.g., "bito.ai")
        name: Company name to search with as fallback (e.g., "Bito")
    
    Returns:
        JSON response with company information (same structure as crunchcomp.json) or empty {} if no match
    """
    try:
        # Extract and normalize the domain
        match_domain = extract_domain(domain)
        logger.info(f"Match domain: {match_domain}")
        
        if not match_domain:
            logger.info("Could not extract domain from domain parameter")
            return {}
        
        # Step 1: Try searching with domain first
        logger.info("Attempting search with domain parameter...")
        result = search_and_match_entities(domain, match_domain)
        
        if result:
            logger.info("Match found using domain search")
            return result
        
        # Step 2: If no match with domain, try searching with name
        logger.info("No match with domain search, attempting search with name parameter...")
        result = search_and_match_entities(name, match_domain)
        
        if result:
            logger.info("Match found using name search")
            return result
        
        # No match found with either approach
        logger.info("No match found with either domain or name search")
        return {}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Crunchbase data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for Crunchbase API"""
    return {
        "status": "healthy",
        "service": "Crunchbase API"
    }

