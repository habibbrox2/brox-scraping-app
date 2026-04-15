"""
Database models for ScrapMaster Desktop
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
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

class Template(BaseModel):
    """Template model"""
    id: str
    name: str
    description: str
    category: str
    config: JobConfig
    icon: str = "📄"
    created_at: datetime = Field(default_factory=datetime.now)

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