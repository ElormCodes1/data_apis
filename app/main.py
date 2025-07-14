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
    allow_origins=["*"],  # Configure as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gmaps_router, prefix="/gmaps", tags=["Google Maps"])
app.include_router(chrome_webstore_router, prefix="/chrome-webstore", tags=["Chrome Web Store"])
app.include_router(twitter_router, prefix="/twitter", tags=["Twitter"])

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
            "/twitter - Twitter Data Scraper",
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