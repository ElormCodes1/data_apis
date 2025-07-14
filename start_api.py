#!/usr/bin/env python3
"""
Data APIs Startup Script

Simple script to start the FastAPI server with proper configuration.
"""

import uvicorn
import logging

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Data APIs Server...")
    print("📋 Available endpoints:")
    print("   - API Documentation: http://localhost:8001/docs")
    print("   - Google Maps API: http://localhost:8001/gmaps")
    print("   - Health Check: http://localhost:8001/health")
    print("\n🔥 Server starting on http://localhost:8001")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8001,
        reload=True,
        log_level="info",
        access_log=True
    ) 