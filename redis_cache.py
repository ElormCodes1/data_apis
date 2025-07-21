import redis
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class ProductHuntCache:
    """Redis cache implementation for ProductHunt API"""
    # os.getenv('REDIS_HOST_I') or
    def __init__(self):
        # Redis connection configuration
        self.redis_host = os.getenv('REDIS_HOST_I') or os.getenv('REDIS_HOST_P')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        self.redis_db = int(os.getenv('REDIS_DB', 1))
        
        # Cache duration mapping (in seconds)
        self.CACHE_DURATIONS = {
            # Date-based endpoints
            "daily_rankings_today": 0,           # No cache for today
            "daily_rankings_historical": 0,      # Permanent for other days
            "weekly_rankings_current": 86400,    # 24 hours for this week
            "weekly_rankings_historical": 0,     # Permanent for past weeks
            "monthly_rankings_current": 604800,  # 7 days for this month
            "monthly_rankings_historical": 0,    # Permanent for past months
            "yearly_rankings_current": 2592000,  # 30 days for this year
            "yearly_rankings_historical": 0,     # Permanent for past years
            
            # Non-date endpoints
            "todays_launches": 3600,             # 1 hour
            "upcoming_launches": 21600,          # 6 hours
            "categories": 2592000,               # 30 days
            "category_products": 86400,          # 24 hours
        }
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    def _generate_cache_key(self, endpoint: str, **params) -> str:
        """Generate cache key based on endpoint and parameters"""
        today = datetime.now()
        
        if endpoint == "todays_launches":
            return f"producthunt:todays_launches:{today.strftime('%Y-%m-%d')}:{today.hour}"
        
        elif endpoint == "upcoming_launches":
            return f"producthunt:upcoming_launches:{today.strftime('%Y-%m-%d')}:{today.hour // 6}"
        
        elif endpoint == "categories":
            return f"producthunt:categories:{today.strftime('%Y-%m')}"
        
        elif endpoint == "category_products":
            category_slug = params.get('category_slug', 'unknown')
            order = params.get('order', 'highest_rated')
            return f"producthunt:category_products:{category_slug}:{order}:{today.strftime('%Y-%m-%d')}"
        
        elif endpoint in ["daily_rankings", "weekly_rankings", "monthly_rankings", "yearly_rankings"]:
            rank_type = endpoint.replace("_rankings", "")
            date_str = params.get('date', '')
            
            # Check if it's current period
            if self._is_current_period(rank_type, date_str):
                return f"producthunt:rankings:{rank_type}:current:{date_str}"
            else:
                return f"producthunt:rankings:{rank_type}:historical:{date_str}"
        
        return f"producthunt:{endpoint}:{hash(str(params))}"
    

    
    def _is_historical_data(self, rank_type: str, date_str: str) -> bool:
        """Check if requested date is in the past relative to today"""
        today = datetime.now()
        
        try:
            if rank_type == "daily":
                requested_date = datetime.strptime(date_str, "%Y/%m/%d")
                return requested_date.date() < today.date()
            
            elif rank_type == "weekly":
                year, week = map(int, date_str.split("/"))
                # Convert to datetime for comparison
                requested_date = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
                current_week_start = datetime.strptime(f"{today.year}-W{today.isocalendar()[1]:02d}-1", "%Y-W%W-%w")
                return requested_date < current_week_start
            
            elif rank_type == "monthly":
                requested_date = datetime.strptime(date_str, "%Y/%m")
                current_month = datetime(today.year, today.month, 1)
                return requested_date < current_month
            
            elif rank_type == "yearly":
                requested_year = int(date_str)
                return requested_year < today.year
                
        except Exception:
            return False
        
        return False

    def _is_current_period(self, rank_type: str, date_str: str) -> bool:
        """Check if requested date is current period (today, this week, this month, this year)"""
        today = datetime.now()
        
        try:
            if rank_type == "daily":
                requested_date = datetime.strptime(date_str, "%Y/%m/%d")
                return requested_date.date() == today.date()
            
            elif rank_type == "weekly":
                year, week = map(int, date_str.split("/"))
                current_year, current_week, _ = today.isocalendar()
                return year == current_year and week == current_week
            
            elif rank_type == "monthly":
                requested_date = datetime.strptime(date_str, "%Y/%m")
                return requested_date.year == today.year and requested_date.month == today.month
            
            elif rank_type == "yearly":
                requested_year = int(date_str)
                return requested_year == today.year
                
        except Exception:
            return False
        
        return False

    def _get_cache_duration(self, endpoint: str, **params) -> int:
        """Get cache duration based on endpoint and parameters"""
        
        if endpoint == "todays_launches":
            return self.CACHE_DURATIONS["todays_launches"]
        
        elif endpoint == "upcoming_launches":
            return self.CACHE_DURATIONS["upcoming_launches"]
        
        elif endpoint == "categories":
            return self.CACHE_DURATIONS["categories"]
        
        elif endpoint == "category_products":
            return self.CACHE_DURATIONS["category_products"]
        
        elif endpoint in ["daily_rankings", "weekly_rankings", "monthly_rankings", "yearly_rankings"]:
            rank_type = endpoint.replace("_rankings", "")
            date_str = params.get('date', '')
            
            # Check if it's current period
            if self._is_current_period(rank_type, date_str):
                # Current period - use specific cache duration
                if rank_type == "daily":
                    return self.CACHE_DURATIONS["daily_rankings_today"]  # No cache for today
                else:
                    return self.CACHE_DURATIONS[f"{rank_type}_rankings_current"]
            else:
                # Historical period - permanent cache
                return self.CACHE_DURATIONS[f"{rank_type}_rankings_historical"]
        
        return 3600  # Default 1 hour
    
    def get(self, endpoint: str, **params) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        if not self.redis_client:
            logger.warning(f"⚠️ Redis client not available for {endpoint}")
            return None
        
        try:
            cache_key = self._generate_cache_key(endpoint, **params)
            logger.info(f"🔍 Looking for cache key: {cache_key}")
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"✅ Cache HIT for {endpoint} with key: {cache_key}")
                return data
            else:
                logger.info(f"❌ Cache MISS for {endpoint} with key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Cache get error for {endpoint}: {str(e)}")
            return None
    
    def set(self, endpoint: str, data: Dict[str, Any], **params) -> bool:
        """Set data in cache with Redis TTL"""
        if not self.redis_client:
            logger.warning(f"⚠️ Redis client not available for setting {endpoint}")
            return False
        
        try:
            cache_key = self._generate_cache_key(endpoint, **params)
            cache_duration = self._get_cache_duration(endpoint, **params)
            
            logger.info(f"💾 Setting cache for {endpoint} with key: {cache_key}, duration: {cache_duration}s")
            
            # Serialize data
            serialized_data = json.dumps(data, default=str)
            
            if cache_duration > 0:
                # Use SETEX for automatic expiration (Redis TTL)
                self.redis_client.setex(cache_key, cache_duration, serialized_data)
                logger.info(f"💾 Cached {endpoint} for {cache_duration}s with key: {cache_key} (auto-expires)")
            else:
                # Use SET for permanent storage (no expiration)
                self.redis_client.set(cache_key, serialized_data)
                logger.info(f"💾 Cached {endpoint} permanently with key: {cache_key} (no expiration)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache set error for {endpoint}: {str(e)}")
            return False
    
    def delete(self, endpoint: str, **params) -> bool:
        """Delete data from cache"""
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(endpoint, **params)
            result = self.redis_client.delete(cache_key)
            logger.info(f"🗑️ Deleted cache for {endpoint} with key: {cache_key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"❌ Cache delete error for {endpoint}: {str(e)}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all ProductHunt cache"""
        if not self.redis_client:
            return False
        
        try:
            pattern = "producthunt:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🗑️ Cleared {len(keys)} cache entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"error": "Redis not connected"}
        
        try:
            pattern = "producthunt:*"
            keys = self.redis_client.keys(pattern)
            
            stats = {
                "total_keys": len(keys),
                "memory_usage": self.redis_client.info()['used_memory_human'],
                "keys_by_pattern": {},
                "ttl_info": {}
            }
            
            # Count keys by pattern and get TTL info
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 2:
                    pattern_type = parts[1]
                    stats["keys_by_pattern"][pattern_type] = stats["keys_by_pattern"].get(pattern_type, 0) + 1
                
                # Get TTL for this key
                ttl = self.redis_client.ttl(key)
                if ttl == -1:
                    ttl_info = "permanent"
                elif ttl == -2:
                    ttl_info = "expired"
                else:
                    ttl_info = f"{ttl}s remaining"
                
                stats["ttl_info"][key] = ttl_info
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Cache stats error: {str(e)}")
            return {"error": str(e)}

    def get_key_ttl(self, cache_key: str) -> str:
        """Get TTL information for a specific key"""
        if not self.redis_client:
            return "Redis not connected"
        
        try:
            ttl = self.redis_client.ttl(cache_key)
            if ttl == -1:
                return "permanent (no expiration)"
            elif ttl == -2:
                return "expired or doesn't exist"
            else:
                return f"{ttl} seconds remaining"
        except Exception as e:
            return f"Error: {str(e)}"

# Global cache instance
cache = ProductHuntCache() 