"""
Database models for ScrapMaster Desktop
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse
import re
from enum import Enum

class JobStatus(str, Enum):
    """Job status enumeration"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class ScheduleType(str, Enum):
    """Schedule type enumeration"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class FieldConfig(BaseModel):
    """Field configuration model"""
    name: str
    selector: str
    selector_type: str = "css"  # css, xpath, json
    attribute: Optional[str] = None  # text, href, src, etc.
    default_value: Optional[str] = None
    transform: Optional[str] = None  # strip, lowercase, etc.

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Field name cannot be empty')
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError('Field name must be a valid identifier')
        return v

    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v):
        if not v or not v.strip():
            raise ValueError('Selector cannot be empty')
        # Basic XSS prevention - no script tags, etc.
        if '<' in v or '>' in v or 'javascript:' in v.lower():
            raise ValueError('Invalid selector content')
        return v

class PaginationConfig(BaseModel):
    """Pagination configuration model"""
    enabled: bool = False
    type: str = "next_button"  # next_button, page_number, scroll
    selector: str = ""
    max_pages: int = 10
    start_page: int = 1

class ProxyConfig(BaseModel):
    """Proxy configuration model"""
    enabled: bool = False
    proxy_list: List[str] = []
    rotate: bool = False

class BrowserConfig(BaseModel):
    """Browser configuration model"""
    headless: bool = False
    user_agent: Optional[str] = None
    delay_ms: int = 1000
    stealth: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080

class ScheduleConfig(BaseModel):
    """Schedule configuration model"""
    enabled: bool = False
    type: ScheduleType = ScheduleType.ONCE
    interval_minutes: Optional[int] = None
    datetime: Optional[datetime] = None
    day_of_week: Optional[int] = None  # 0-6 for weekly
    day_of_month: Optional[int] = None  # 1-31 for monthly

class APIConfig(BaseModel):
    """API configuration model"""
    enabled: bool = False
    url: Optional[str] = None
    method: str = "POST"
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    auth_type: str = "none"  # "none", "bearer", "basic", "api_key"
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    api_key_header: str = "X-API-Key"

    @field_validator('url')
    @classmethod
    def validate_api_url(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError('Invalid API URL format')
        return v

    @field_validator('method')
    @classmethod
    def validate_method(cls, v):
        allowed = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if v.upper() not in allowed:
            raise ValueError(f'Method must be one of {allowed}')
        return v.upper()

class JobConfig(BaseModel):
    """Job configuration model"""
    url: str
    urls: List[str] = []
    fields: List[FieldConfig] = []
    pagination: PaginationConfig = PaginationConfig()
    proxy: ProxyConfig = ProxyConfig()
    browser: BrowserConfig = BrowserConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    api: APIConfig = APIConfig()
    base_url: Optional[str] = None
    root_selector: Optional[str] = None

    @field_validator('url', 'base_url')
    @classmethod
    def validate_url(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None  # Allow empty to be None
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError('Invalid URL format')
            # Prevent localhost/private IPs for security
            host = parsed.hostname or ""
            if host in ['localhost', '127.0.0.1', '0.0.0.0']:
                raise ValueError('Local/private URLs not allowed')
            try:
                import ipaddress
                ip_addr = ipaddress.ip_address(host)
            except ValueError:
                # Non-IP hosts are allowed; only actual private IPs are blocked.
                return v
            if ip_addr.is_private:
                raise ValueError('Local/private URLs not allowed')
        return v

    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v):
        for url in v:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f'Invalid URL in list: {url}')
        return v

    @field_validator('root_selector')
    @classmethod
    def validate_root_selector(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None  # Normalize empty to None
            if '<' in v or '>' in v or 'javascript:' in v.lower():
                raise ValueError('Invalid selector content')
        return v

class Job(BaseModel):
    """Job model"""
    id: str
    name: str
    description: Optional[str] = None
    template: Optional[str] = None
    config: JobConfig
    status: JobStatus = JobStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0

class ScrapedItem(BaseModel):
    """Scraped item model"""
    id: str
    job_id: str
    data: Dict[str, Any]
    url: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "success"

class JobResult(BaseModel):
    """Job result model"""
    id: str
    job_id: str
    items_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class Settings(BaseModel):
    """Application settings model"""
    max_concurrent_jobs: int = 3
    default_headless: bool = False
    default_delay_ms: int = 1000
    data_storage_path: str = "data"
    auto_update_check: bool = True
    dark_mode: bool = True
    log_level: str = "INFO"
    default_user_agent: Optional[str] = None
    default_proxy: Optional[str] = None

    # AI settings
    ai_enabled: bool = True
    ai_default_model: str = "google/gemini-flash-1.5"
    ai_tool_calling: bool = True

class Template(BaseModel):
    """Template model"""
    id: str
    name: str
    description: str
    category: str
    config: JobConfig
    icon: str = "📄"
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('category', mode='before')
    @classmethod
    def coerce_category(cls, v):
        if v is None:
            return "general"
        return str(v)

class WebScrapingSource(BaseModel):
    """Web scraping source model"""
    id: str
    name: str
    url: str
    description: Optional[str] = None
    category: str = "general"
    config: JobConfig
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('category', mode='before')
    @classmethod
    def coerce_category(cls, v):
        if v is None:
            return "general"
        return str(v)
