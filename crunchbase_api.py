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
    'cid': 'CihaKWkxvlx0AAAWBcoXAg==',
    'featureFlagOverride': '%7B%7D',
    'profile_v3_opt_in': 'true',
    'cb_analytics_consent': 'denied',
    'g_state': '{"i_l":0,"i_ll":1764872638551,"i_b":"KZf+BBIVSM1uO3u4BvSkOux6ij4Hk4ILQ7fnDsLU430"}',
    'trustcookie': 'eyJraWQiOiJjcnVuY2hiYXNlIiwiYWxnIjoiUlMyNTYifQ.eyJqdGkiOiI0ZTJkNTZlMi03N2JiLTQ3M2ItOTAyYS1hZGZjODYwYjk5MjciLCJpc3MiOiJ1c2Vyc2VydmljZV9kMWNkMTJlNl8xIiwic3ViIjoiY2EyZWEwYTgtYjBjNy00Y2E1LThkN2QtNWNkYzBkZDFhNjQ3IiwiZXhwIjoxNzY1MDQ5MTIxLCJpYXQiOjE3NjQ5NjI3MjEsInNjciI6MH0.FbkMTtcdR2ct775lsa8jGDktYQtFtVIjnwi6qGy6aWFzguJC_oCGlVUvNqbanvpBhcH6CeRA0xX3qUH71zPp2i1fHfxGBleKFFmSIP30HiUcu68ZeyWd42_Viup7mnmZALc895LvwarHJUNRm1D-MzmBUKBbxa4TAtmP9Z54D2HHbILjdG4QWjACIfyz7uCwdbT5anBY2d2wTe3ZW5mqHAeqbj6qR586LtDpKDH-TquWHA1-9IJ9bR4RyvcSJ7NvhhLVa12Qka-aKr4Gwxdil1rlCLBcrBCXH892Flhvj6K_8IOpNAtOwx1f3MFToj9TFPuC8--Ohy7qRSI_e8JTcw',
    'authcookie': 'eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiI0ZTJkNTZlMi03N2JiLTQ3M2ItOTAyYS1hZGZjODYwYjk5MjciLCJpc3MiOiJ1c2Vyc2VydmljZV9kMWNkMTJlNl8xIiwic3ViIjoiY2EyZWEwYTgtYjBjNy00Y2E1LThkN2QtNWNkYzBkZDFhNjQ3IiwiZXhwIjoxNzY0OTYzMDIxLCJpYXQiOjE3NjQ5NjI3MjEsInByaXZhdGUiOiJYQW1UU3NleXp1bFo1bkROQU55STk0blIzaENNbTdML3M1cGhnUHpKRWQ3dlBpdDBudjNjL05OTWZlNmE1dUIyVDl4Qnd6Ty8rTWpyYTY5dEVnTlc2MVYvWXBGTUxHclJkR3Y0VFVKa2VtclQyU3pON2tnbE00elAxYUNpbUZsTFZZU0lYaEpxU240UGVPeXRVVXVjZWw4Vm8rR1NRbW1RQkpVaTNVcDY1eng2ZERqV2cwQVFTZ1NoMzB0aWErR1oxODQ0SHRUTTlUc2tPR1F4U2hHbXMwQ3AyRGFnTTkvOTFUdW81dDFKWHI0WkFEaEhyK2RkQ1VqVnhqam1YdkFNdjFTVndzT1BVOTVMZkI5d1g0K1paRjNCVFF6MzRqeDNaeFVuK1daRE44c2NsaDZ5NnJCbkpIU3d4Mm9odWhBVU9TdWVzRWtTbnMycFhvSDQ2SUg5cnJTQjRZQzhWd0w5eVRlTllHNnMwa009IiwicHVibGljIjp7InNlc3Npb25faGFzaCI6IjI1OTM5Nzk1NSJ9fQ.PMJslz7ZK6GU95gLdCqkQYiHEsjDRdc3z62tFuGGgMoOtLset2fhXC3GVR1sF4UwjAkkZ7V7kxVgIRoHHY5Piw',
    'cf_clearance': 'GBRe68sJWSAcxOcWpvvTWAmNfiXqLspLvCTM3Nj1DKs-1764962725-1.2.1.1-yis0I_dwKieix3FuEQHDFB2BtRAFr0yI90tJy.xi3cpoap1O7J5OXPLYS.27fXXXFRP1nh5OUFIrWNJ6.Y2LnPQXc.yj24QC7uGI.J7kZboAeMn.fQjaxftk8Lm1kA01cWjqKM8SQIA.TebzSQ7q1H1AyDV3lvzWA_RWFObbmuXs9eELsyBe47ADVDVSgg.MH70sB1fadgsIhiOr.5PEz2epGta4acBlId_YNrkY2Nk',
    '__cf_bm': 'Nt6RC7aZA0Ci2qG4zFnOwLopBKoleIp2KXOOB1F6kK4-1764962858.6898253-1.0.1.1-ikmbnDHcJ319PoOzWPGmW0qP_z2RP_HK3yIzmZXAIljdyNlXhvRiJ.FvG6aRmOxALxCEEwQMtfAYoGPMRvyD4XCLjqQq_sTE49Vu_E5_.yLDfG6TtEo6Gr7B6r5HuL5o',
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


@router.get("/crunchbase_info")
async def get_crunchbase_info(
    query: str = Query(..., description="Company name or identifier to search for")
) -> Dict[str, Any]:
    """
    Get Crunchbase company information by query.
    
    This endpoint:
    1. Searches for the company using Crunchbase autocomplete API
    2. Retrieves the company permalink
    3. Fetches detailed company information including competitors, employees, advisors, etc.
    
    Args:
        query: Company name or identifier (e.g., "bito.ai", "Apple", etc.)
    
    Returns:
        JSON response with company information (same structure as crunchcomp.json)
    """
    try:
        # Step 1: Search for company using autocomplete API
        logger.info(f"Searching for company: {query}")
        autocomplete_params = {
            'query': query,
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
            raise HTTPException(
                status_code=autocomplete_response.status_code,
                detail=f"Failed to search for company: {autocomplete_response.text}"
            )
        
        autocomplete_data = autocomplete_response.json()
        
        # Check if we have results
        if not autocomplete_data.get('entities') or len(autocomplete_data['entities']) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No company found matching query: {query}"
            )
        
        # Get the first result's permalink
        company_permalink = autocomplete_data['entities'][0]['identifier']['permalink']
        logger.info(f"Found company permalink: {company_permalink}")
        
        # Step 2: Fetch detailed company information
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
                "recommended_search"
            ],
            "layout_mode": "view_v3"
        }
        
        encoded_params = urllib.parse.urlencode({
            "field_ids": json.dumps(params["field_ids"]),
            "card_ids": json.dumps(params["card_ids"]),
            "layout_mode": params["layout_mode"]
        })
        
        url = f"{base_url}?{encoded_params}"
        
        logger.info(f"Fetching company details from: {url}")
        response = curl_requests.get(
            url,
            cookies=COOKIES,
            headers=HEADERS,
            impersonate="chrome",
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch company details: {response.text}"
            )
        
        # Parse and return the JSON response
        company_data = response.json()
        logger.info(f"Successfully fetched company information for: {query}")
        
        return company_data
        
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

