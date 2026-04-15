"""
Helper utilities for ScrapMaster Desktop
"""

import os
import re
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin

def generate_unique_id() -> str:
    """Generate a unique ID for jobs and items"""
    return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]

def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def normalize_url(url: str, base_url: str = "") -> str:
    """Normalize a URL, handling relative paths"""
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        if base_url:
            return urljoin(base_url, url)
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters
    text = text.strip()
    return text

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

def format_timestamp(timestamp: Any = None) -> str:
    """Format timestamp for display"""
    if timestamp is None:
        timestamp = datetime.now()
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except Exception:
            return timestamp
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def format_file_size(size_bytes: int) -> str:
    """Format file size for display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    # Remove invalid characters for Windows/macOS/Linux
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    return filename

def parse_json_safe(json_str: str) -> Dict:
    """Safely parse JSON string"""
    try:
        return json.loads(json_str)
    except Exception:
        return {}

def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

class ProxyManager:
    """Manage proxy list for scraping"""
    
    def __init__(self, proxies: List[str] = None):
        self.proxies = proxies or []
        self.current_index = 0
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def add_proxy(self, proxy: str):
        """Add a proxy to the list"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
    
    def remove_proxy(self, proxy: str):
        """Remove a proxy from the list"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
    
    def get_all(self) -> List[str]:
        """Get all proxies"""
        return self.proxies.copy()

class UserAgentRotator:
    """Rotate User-Agent strings"""
    
    DEFAULT_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, user_agents: List[str] = None):
        self.user_agents = user_agents or self.DEFAULT_UA
        self.current_index = 0
    
    def get_random(self) -> str:
        """Get a random User-Agent"""
        import random
        return random.choice(self.user_agents)
    
    def get_next(self) -> str:
        """Get next User-Agent in rotation"""
        ua = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return ua