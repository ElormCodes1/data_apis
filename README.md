# Data APIs

A FastAPI-based collection of data scraping and processing APIs.

## APIs Available

### 1. Google Maps Business Scraper API (`/gmaps`)
Scrapes business information from Google Maps including:
- Business name and type
- Ratings and review counts  
- Contact information (phone, website)
- Address
- And more...

### 2. Chrome Web Store Extensions Scraper API (`/chrome-webstore`)
Scrapes Chrome extension information including:
- Extension name and description
- Developer information (name, email, website)
- Ratings and review counts
- User counts and categories
- And more...

## Quick Start

1. **Install dependencies:**
```bash
cd "data apis"
pip install -r requirements.txt
```

2. **Start the API server:**
```bash
python start_api.py
```

3. **Access the API:**
- Interactive docs: http://localhost:8000/docs
- Google Maps API: http://localhost:8000/gmaps
- Chrome Web Store API: http://localhost:8000/chrome-webstore
- Health check: http://localhost:8000/health

## Google Maps API Examples

### Synchronous Scraping
```bash
curl -X POST "http://localhost:8000/gmaps/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "hair salons in Takoradi",
       "max_results": 50,
       "headless": true
     }'
```

### Asynchronous Scraping with Enhanced Status Tracking
```bash
# Start async task
curl -X POST "http://localhost:8000/gmaps/scrape-async" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "restaurants in Accra", 
       "max_results": 500,
       "headless": true
     }'

# Check detailed task status (use task_id from response)
curl "http://localhost:8000/gmaps/status/{task_id}"
```

**Enhanced Status Response:**
```json
{
  "task_id": "12345-67890",
  "status": "running",
  "current_stage": "processing",
  "current_operation": "Processing business 15/50",
  "progress": "Extracting data from business 15 of 50",
  "businesses_processed": 15,
  "total_businesses_found": 50,
  "current_business_name": "Golden Hair Salon",
  "success_count": 14,
  "failure_count": 1,
  "elapsed_time_seconds": 125.3,
  "estimated_remaining_seconds": 287.5,
  "last_updated": "2024-01-15T10:32:15.123456"
}
```

### Download Results in Multiple Formats

Once scraping is completed, both sync and async endpoints provide download URLs in the response:

```json
{
  "success": true,
  "query": "hair salons in Takoradi",
  "total_results": 25,
  "businesses": [...],
  "download_urls": {
    "json": "/gmaps/download/{task_id}/json",
    "csv": "/gmaps/download/{task_id}/csv"
  }
}
```

**Download as JSON:**
```bash
curl -O -J "http://localhost:8000/gmaps/download/{task_id}/json"
```

**Download as CSV:**
```bash
curl -O -J "http://localhost:8000/gmaps/download/{task_id}/csv"
```

The downloaded files include:
- All scraped business data
- Query and execution metadata
- Download timestamp and format information
- Automatic filename generation (e.g., `gmaps_hair_salons_in_Takoradi_2024-01-15_10-30-15.csv`)

## Chrome Web Store API Examples

### Complete Scraping with Category Selection

**Scrape Specific Categories:**
```bash
# Scrape specific categories only
curl -X POST "http://localhost:8000/chrome-webstore/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "max_workers": 50,
       "page": 1,
       "page_size": 100,
       "categories": ["lifestyle_well_being", "productivity_tools"]
     }'

# Scrape single category
curl -X POST "http://localhost:8000/chrome-webstore/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "max_workers": 30,
       "categories": ["lifestyle_games"]
     }'
```

**Scrape All Categories (Default):**
```bash
# When categories is empty or not provided, all categories are scraped
curl -X POST "http://localhost:8000/chrome-webstore/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "max_workers": 50,
       "page": 1,
       "page_size": 100
     }'
```

### Complete Scraping (Asynchronous with Pagination)
```bash
# Start async scraping task
curl -X POST "http://localhost:8000/chrome-webstore/scrape-async" \
     -H "Content-Type: application/json" \
     -d '{
       "max_workers": 50,
       "page": 1,
       "page_size": 100
     }'

# Check task status (use task_id from response)
curl "http://localhost:8000/chrome-webstore/status/{task_id}"

# Get paginated results from completed task
curl "http://localhost:8000/chrome-webstore/results/{task_id}?page=1&page_size=50"
curl "http://localhost:8000/chrome-webstore/results/{task_id}?page=2&page_size=25"
```

### Browse Through Pages
```bash
# Get different pages from completed async task
curl "http://localhost:8000/chrome-webstore/results/{task_id}?page=1&page_size=20"
curl "http://localhost:8000/chrome-webstore/results/{task_id}?page=2&page_size=20"
curl "http://localhost:8000/chrome-webstore/results/{task_id}?page=3&page_size=20"
```

### Download Complete Results in Multiple Formats

Once Chrome Web Store scraping is completed, both paginated results and async task completion provide download URLs:

```json
{
  "success": true,
  "total_urls_collected": 500,
  "successful_scrapes": 485,
  "extensions": [...],
  "pagination": {...},
  "download_urls": {
    "json": "/chrome-webstore/download/{task_id}/json",
    "csv": "/chrome-webstore/download/{task_id}/csv"
  }
}
```

**Download Full Dataset as JSON:**
```bash
curl -O -J "http://localhost:8000/chrome-webstore/download/{task_id}/json"
```

**Download Full Dataset as CSV:**
```bash
curl -O -J "http://localhost:8000/chrome-webstore/download/{task_id}/csv"
```

The downloaded files include:
- **All scraped extension data** (not just the current page)
- Extension details: name, owner, email, website, description, category
- User metrics: ratings, review counts, user counts
- Download metadata and timestamps
- Automatic filename generation (e.g., `chrome_webstore_extensions_{task_id}_2024-01-15_10-30-15.csv`)

### Get Available Categories
```bash
curl "http://localhost:8000/chrome-webstore/categories"
```

**🔥 For Swagger UI Users:**
1. **Quick way:** Visit `http://localhost:8000/chrome-webstore/categories/help` for formatted category strings
2. **API way:** Go to `http://localhost:8000/chrome-webstore/categories` for JSON data
3. **Copy the exact strings** from the `string` field of each category  
4. **Paste them into Swagger UI** categories field

**Available Category Strings (COPY THESE EXACTLY):**
```
"productivity_developer"     (Developer)
"lifestyle_art"              (Art)
"productivity_communication" (Communication)
"productivity_education"     (Education)
"lifestyle_entertainment"    (Entertainment)
"lifestyle_household"        (Household)
"lifestyle_travel"           (Travel)
"lifestyle_well_being"       (Well Being)
"make_chrome_yours_functionality" (Functionality)
"make_chrome_yours_privacy"  (Privacy)
"productivity_tools"         (Tools)
"productivity_workflow"      (Workflow)
"lifestyle_games"            (Games)
"lifestyle_fun"              (Fun)
"lifestyle_news"             (News)
"lifestyle_shopping"         (Shopping)
"lifestyle_social"           (Social)
"make_chrome_yours_accessibility" (Accessibility)
```

**Category Selection Examples:**
```json
{
  "categories": ["lifestyle_well_being"]                           // Single category
  "categories": ["lifestyle_well_being", "productivity_tools"]     // Multiple categories  
  "categories": null                                               // All categories (default)
}
```

**Swagger UI Instructions:**
1. Visit `/chrome-webstore/categories` endpoint to get the exact strings
2. Each category shows its `string` value - use these exact strings
3. In the scrape endpoint, click on the `categories` field  
4. Manually type or paste the category strings from above
5. Leave empty to scrape all categories

## Features

✅ **Synchronous & Asynchronous Processing**  
✅ **Comprehensive Business Data**  
✅ **Robust Error Handling**  
✅ **Performance Optimized**  
✅ **Task Management**  
✅ **Enhanced Status Tracking** (Real-time progress monitoring)
✅ **Detailed Progress Information** (Current stage, business names, ETAs)
✅ **Comprehensive Logging** (Console + file output with emojis)
✅ **Multiple Download Formats** (JSON & CSV with auto filenames)
✅ **Pagination Support** (Chrome Web Store API)  
✅ **Flexible Page Sizes** (1-1000 items per page)  
✅ **Multi-page Result Browsing**  

## Testing

Run the test suites:
```bash
# Test Google Maps API
python test_api.py

# Test detailed status monitoring (Google Maps)
python status_monitoring_example.py

# Test download functionality (Google Maps)
python test_download.py

# Test Chrome Web Store API with pagination
python test_chrome_webstore_api.py

# Test Chrome Web Store download functionality
python test_chrome_webstore_downloads.py

# Run pagination examples
python pagination_examples.py

# Run Python client examples
python chrome_webstore_client.py
```

## File Structure
```
data apis/
├── main.py                      # Main FastAPI application
├── gmaps_api.py                 # Google Maps scraper API with enhanced logging & status
├── chrome_webstore_api.py       # Chrome Web Store scraper API with pagination
├── start_api.py                 # Startup script
├── test_api.py                  # Google Maps API test suite
├── status_monitoring_example.py # Enhanced status monitoring demo
├── test_download.py             # Download functionality test suite (Google Maps)
├── test_chrome_webstore_api.py  # Chrome Web Store API test suite with pagination
├── test_chrome_webstore_downloads.py # Chrome Web Store download test suite
├── chrome_webstore_client.py    # Chrome Web Store Python client examples
├── pagination_examples.py       # Pagination usage examples
├── get_categories.py            # Helper script to get category strings
├── requirements.txt             # Dependencies
└── README.md                   # This file
```