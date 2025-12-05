"""
Data APIs Main Application

FastAPI application serving various data scraping and processing APIs.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import logging

# Import API routers
from gmaps_api import router as gmaps_router
from chrome_webstore_api import router as chrome_webstore_router
from twitter_api import router as twitter_router
from producthunt_api import router as producthunt_router
from amazon_search_api import router as amazon_router
from youtube_transcript_api import router as youtube_router
from facebook_marketplace_router import router as facebook_marketplace_router
from zillow_router import router as zillow_router
from crunchbase_api import router as crunchbase_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Data APIs",
    description="Collection of data scraping and processing APIs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now - configure specific domains in production
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gmaps_router, prefix="/gmaps", tags=["Google Maps"])
app.include_router(chrome_webstore_router, prefix="/chrome-webstore", tags=["Chrome Web Store"])
app.include_router(twitter_router, prefix="/twitter", tags=["Twitter"])
app.include_router(producthunt_router, prefix="/producthunt", tags=["ProductHunt"])
app.include_router(amazon_router, prefix="/amazon-search", tags=["Amazon"])
app.include_router(youtube_router, prefix="/youtube", tags=["YouTube"])
app.include_router(facebook_marketplace_router, prefix="/facebook-marketplace", tags=["Facebook Marketplace"])
app.include_router(zillow_router, prefix="/zillow", tags=["Zillow Real Estate"])
app.include_router(crunchbase_router, prefix="/crunchbase", tags=["Crunchbase"])

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Data APIs Service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "available_apis": [
            "/gmaps - Google Maps Business Scraper",
            "/chrome-webstore - Chrome Web Store Extensions Scraper",
            "/twitter - Twitter Data Scraper (includes list members)",
            "/producthunt - ProductHunt Rankings Scraper",
            "/amazon-search - Amazon Product Search Scraper",
            "/youtube - YouTube Transcript Extractor",
            "/facebook-marketplace - Facebook Marketplace Search",
            "/zillow - Zillow Real Estate Search (Sales & Rentals)",
            "/crunchbase - Crunchbase Company Information",
            "/docs - API Documentation",
            "/health - Health Check"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Data APIs"
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    ) 