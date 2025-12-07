from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from webdata import get_website_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/website-info")
async def get_website_info(
    domain: str = Query(..., description="Domain to analyze (e.g., 'arcads.ai')"),
    from_date: Optional[str] = Query(None, description="Start date in format 'YYYY|MM|DD' (defaults to first day of previous month)"),
    to_date: Optional[str] = Query(None, description="End date in format 'YYYY|MM|DD' (defaults to last day of previous month)")
) -> Dict[str, Any]:
    """
    Get comprehensive website analytics data from SimilarWeb.
    
    Returns unified structured data including:
    - Metadata (title, description, category, etc.)
    - Rankings (global, country, category)
    - Traffic metrics (visits, device split, trends)
    - Engagement metrics (duration, pages per visit, bounce rate)
    - Traffic sources (organic, direct, social, paid, etc.)
    - Geography (top countries with engagement metrics)
    - Referrals (incoming and outgoing)
    - Competitors (similar sites)
    
    Args:
        domain: The domain to analyze
        from_date: Optional start date (defaults to previous month's first day)
        to_date: Optional end date (defaults to previous month's last day)
    
    Returns:
        Unified structured website data dictionary
    """
    try:
        logger.info(f"Fetching SimilarWeb data for domain: {domain}")
        
        # Get website data
        result = get_website_data(domain, from_date, to_date)
        
        if not result or not result.get("domain"):
            raise HTTPException(
                status_code=404,
                detail=f"No data found for domain: {domain}"
            )
        
        logger.info(f"Successfully fetched data for {domain}")
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching SimilarWeb data for {domain}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching website data: {str(e)}"
        )

