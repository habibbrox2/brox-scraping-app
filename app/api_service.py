"""
API Service for posting collected data to external hosts
"""

import requests
import json
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.database import db
from app.utils.logger import get_logger

logger = get_logger()

class APIService:
    """Service for posting scraped data to external APIs"""
    
    def __init__(self):
        self._endpoints = {}
        self._running = False
    
    def register_endpoint(self, name: str, url: str, method: str = "POST", 
                    headers: Optional[Dict] = None, auth_type: str = "none",
                    auth_token: Optional[str] = None, auth_username: Optional[str] = None,
                    auth_password: Optional[str] = None, api_key_header: str = "X-API-Key",
                    enabled: bool = True):
        """Register an API endpoint"""
        self._endpoints[name] = {
            "url": url,
            "method": method,
            "headers": headers or {"Content-Type": "application/json"},
            "auth_type": auth_type,  # "none", "bearer", "basic", "api_key"
            "auth_token": auth_token,
            "auth_username": auth_username,
            "auth_password": auth_password,
            "api_key_header": api_key_header,
            "enabled": enabled
        }
        logger.info(f"Registered API endpoint: {name} -> {url}")
    
    def remove_endpoint(self, name: str):
        """Remove an API endpoint"""
        if name in self._endpoints:
            del self._endpoints[name]
            logger.info(f"Removed API endpoint: {name}")
    
    def get_endpoints(self) -> Dict[str, Dict]:
        """Get all registered endpoints"""
        return self._endpoints.copy()
    
    def post_item(self, endpoint_name: str, data: Dict[str, Any]) -> bool:
        """Post a single item to endpoint"""
        if endpoint_name not in self._endpoints:
            logger.error(f"Endpoint not found: {endpoint_name}")
            return False
        
        endpoint = self._endpoints[endpoint_name]
        if not endpoint["enabled"]:
            logger.warning(f"Endpoint disabled: {endpoint_name}")
            return False
        
        url = endpoint["url"]
        headers = endpoint["headers"].copy()
        
        # Add authentication
        auth_type = endpoint.get("auth_type", "none")
        if auth_type == "bearer" and endpoint.get("auth_token"):
            headers["Authorization"] = f"Bearer {endpoint['auth_token']}"
        elif auth_type == "basic" and endpoint.get("auth_username") and endpoint.get("auth_password"):
            import base64
            auth_str = f"{endpoint['auth_username']}:{endpoint['auth_password']}"
            headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        elif auth_type == "api_key" and endpoint.get("auth_token"):
            headers[endpoint.get("api_key_header", "X-API-Key")] = endpoint["auth_token"]
        
        try:
            if endpoint["method"] == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.put(url, json=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            logger.info(f"Posted item to {endpoint_name}: {response.status_code}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint_name}: {e}")
            return False
    
    def post_batch(self, endpoint_name: str, items: List[Dict[str, Any]], 
                 batch_size: int = 10) -> Dict[str, int]:
        """Post multiple items to endpoint"""
        results = {"success": 0, "failed": 0}
        
        for item in items:
            if self.post_item(endpoint_name, item):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def post_items_async(self, endpoint_name: str, items: List[Dict[str, Any]]):
        """Post items asynchronously in background"""
        thread = threading.Thread(
            target=self.post_batch,
            args=(endpoint_name, items),
            daemon=True
        )
        thread.start()
        logger.info(f"Started async posting to {endpoint_name}: {len(items)} items")
    
    def get_all_items_and_post(self, endpoint_name: str, job_id: Optional[str] = None):
        """Get items from database and post to endpoint"""
        if job_id:
            items = db.get_items_by_job(job_id)
        else:
            items = db.get_all_items()
        
        # Convert to dict list
        data = [item.data for item in items]
        
        if data:
            self.post_items_async(endpoint_name, data)
            logger.info(f"Queued {len(data)} items for posting to {endpoint_name}")
        else:
            logger.warning("No items to post")


class APIJobScheduler:
    """Schedule automatic posting of scraped data"""
    
    def __init__(self):
        self._api_service = APIService()
        self._schedules = {}
    
    def add_schedule(self, job_id: str, endpoint_name: str, on_complete: bool = True):
        """Add schedule to post job results when complete"""
        self._schedules[job_id] = {
            "endpoint_name": endpoint_name,
            "on_complete": on_complete
        }
        logger.info(f"Added schedule for job {job_id} -> {endpoint_name}")
    
    def remove_schedule(self, job_id: str):
        """Remove schedule"""
        if job_id in self._schedules:
            del self._schedules[job_id]
    
    def on_job_complete(self, job_id: str):
        """Called when a job completes"""
        if job_id in self._schedules and self._schedules[job_id]["on_complete"]:
            endpoint = self._schedules[job_id]["endpoint_name"]
            self._api_service.get_all_items_and_post(endpoint, job_id)


# Global instances
api_service = APIService()
api_scheduler = APIJobScheduler()


def setup_default_endpoints():
    """Setup default API endpoints from settings"""
    # Get API settings from database
    api_url = db.get_setting("api_url")
    api_token = db.get_setting("api_token")
    
    if api_url:
        api_service.register_endpoint(
            "default",
            api_url,
            auth_token=api_token
        )


# Example usage functions
def post_to_custom_host(url: str, data: Dict, token: Optional[str] = None) -> bool:
    """Post data to custom host"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Post failed: {e}")
        return False


def sync_all_data_to_api(api_url: str, api_token: str) -> Dict[str, int]:
    """Sync all scraped data to API"""
    items = db.get_all_items()
    
    if not items:
        return {"success": 0, "failed": 0}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    
    results = {"success": 0, "failed": 0}
    
    for item in items:
        try:
            response = requests.post(
                api_url, 
                json=item.data, 
                headers=headers, 
                timeout=30
            )
            if response.status_code < 400:
                results["success"] += 1
            else:
                results["failed"] += 1
        except Exception:
            results["failed"] += 1
    
    logger.info(f"Sync complete: {results}")
    return results