"""
SQLite database handling for ScrapMaster Desktop
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
import keyring

from app.database.models import (
    Job, JobStatus, ScrapedItem, JobResult, Settings, Template, WebScrapingSource,
    JobConfig, FieldConfig, PaginationConfig, ProxyConfig, BrowserConfig, ScheduleConfig
)
from app.utils.helpers import generate_unique_id
from app.utils.logger import get_logger

logger = get_logger()

# Database path
REPO_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = REPO_ROOT / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "scrapmaster.db"

# SQLAlchemy engine with connection pooling
engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    poolclass=StaticPool,  # Single connection for SQLite
    connect_args={"check_same_thread": False}  # Allow multi-thread access
)


def _parse_iso_datetime(value, default: Optional[datetime] = None) -> datetime:
    """Parse datetime values from modern/legacy DB rows safely."""
    if value in (None, ""):
        return default or datetime.now()
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return default or datetime.now()

def get_connection():
    """Get database connection"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return engine.connect()

def _table_columns(conn, table_name: str) -> List[str]:
    """Return the list of column names for a table."""
    cursor = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in cursor.fetchall()]

def _source_schema_mode(conn) -> str:
    """Detect whether the source table uses the current or legacy layout."""
    columns = set(_table_columns(conn, "web_scraping_sources"))
    if {"config", "enabled", "updated_at"}.issubset(columns):
        return "current"
    return "legacy"

def _build_default_source_config(source_url: str) -> JobConfig:
    """Build a generic source config that can extract useful article-like data."""
    return JobConfig(
        url=source_url,
        fields=[
            FieldConfig(name="title", selector="h1", selector_type="css", attribute="text"),
            FieldConfig(name="summary", selector="p", selector_type="css", attribute="text"),
            FieldConfig(name="link", selector="a[href]", selector_type="css", attribute="href"),
        ],
        root_selector="article, main, body",
    )

def _coerce_source_config(raw_config_value, fallback_url: str, use_default_fields: bool = True) -> JobConfig:
    """Normalize a source config from JSON/dict/legacy values."""
    if raw_config_value in (None, ""):
        return _build_default_source_config(fallback_url) if use_default_fields else JobConfig(url=fallback_url, fields=[])

    try:
        if isinstance(raw_config_value, str):
            config_dict = json.loads(raw_config_value)
        elif isinstance(raw_config_value, dict):
            config_dict = dict(raw_config_value)
        else:
            config_dict = json.loads(str(raw_config_value))
    except Exception:
        config_dict = {}

    if not isinstance(config_dict, dict):
        config_dict = {}

    if not config_dict.get("url") or not str(config_dict["url"]).strip():
        config_dict["url"] = fallback_url

    fields = config_dict.get("fields")
    if not fields:
        return _build_default_source_config(fallback_url) if use_default_fields else JobConfig(url=fallback_url, fields=[])

    try:
        config = JobConfig.model_validate(config_dict)
    except Exception:
        return _build_default_source_config(fallback_url) if use_default_fields else JobConfig(url=fallback_url, fields=[])

    if use_default_fields and not config.fields:
        return _build_default_source_config(fallback_url)

    return config

@contextmanager
def get_session():
    """Get database session context manager"""
    with engine.connect() as conn:
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise

def init_database():
    """Initialize database tables"""
    with get_session() as conn:
        # Jobs table
        sql = """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                template TEXT,
                config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                run_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        """
        conn.execute(text(sql))
        
        # Scraped items table
        sql = """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                data TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'success',
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """
        conn.execute(text(sql))
        
        # Job results table
        sql = """
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                items_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """
        conn.execute(text(sql))
        
        # Settings table
        sql = """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """
        conn.execute(text(sql))
        
        # Templates table
        sql = """
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                config TEXT NOT NULL,
                icon TEXT,
                created_at TEXT NOT NULL
            )
        """
        conn.execute(text(sql))
        
        # Web scraping sources table
        sql = """
            CREATE TABLE IF NOT EXISTS web_scraping_sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                config TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        conn.execute(text(sql))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_items_job_id ON items(job_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_results_job_id ON results(job_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"))
        
        logger.info("Database initialized successfully")

# Job operations
def create_job(job: Job) -> Job:
    """Create a new job"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT INTO jobs (id, name, description, template, config, status,
                           created_at, updated_at, last_run_at, next_run_at,
                           run_count, success_count, failure_count)
            VALUES (:id, :name, :description, :template, :config, :status,
                   :created_at, :updated_at, :last_run_at, :next_run_at,
                   :run_count, :success_count, :failure_count)
        """), {
            "id": job.id, "name": job.name, "description": job.description, "template": job.template,
            "config": job.config.model_dump_json(), "status": job.status.value,
            "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat(),
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "run_count": job.run_count, "success_count": job.success_count, "failure_count": job.failure_count
        })
    logger.info(f"Created job: {job.name}")
    return job

def get_job(job_id: str) -> Optional[Job]:
    """Get a job by ID"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM jobs WHERE id = :job_id"), {"job_id": job_id})
        row = cursor.fetchone()
        if row:
            return _row_to_job(row)
    return None

def get_all_jobs() -> List[Job]:
    """Get all jobs"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM jobs ORDER BY created_at DESC"))
        return [_row_to_job(row) for row in cursor.fetchall()]

def get_jobs_by_status(status: JobStatus) -> List[Job]:
    """Get jobs by status"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM jobs WHERE status = :status ORDER BY created_at DESC"), {"status": status.value})
        return [_row_to_job(row) for row in cursor.fetchall()]

def update_job(job: Job) -> Job:
    """Update a job"""
    job.updated_at = datetime.now()
    with get_session() as conn:
        conn.execute(text("""
            UPDATE jobs SET name=:name, description=:description, template=:template, config=:config, status=:status,
                         updated_at=:updated_at, last_run_at=:last_run_at, next_run_at=:next_run_at, run_count=:run_count,
                         success_count=:success_count, failure_count=:failure_count
            WHERE id=:id
        """), {
            "name": job.name, "description": job.description, "template": job.template,
            "config": job.config.model_dump_json(), "status": job.status.value,
            "updated_at": job.updated_at.isoformat(),
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "run_count": job.run_count, "success_count": job.success_count, "failure_count": job.failure_count,
            "id": job.id
        })
    logger.info(f"Updated job: {job.name}")
    return job

def delete_job(job_id: str) -> bool:
    """Delete a job"""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM jobs WHERE id = :job_id"), {"job_id": job_id})
    logger.info(f"Deleted job: {job_id}")
    return cursor.rowcount > 0

def _row_to_job(row) -> Job:
    """Convert database row to Job model"""
    config = _coerce_source_config(row[4], "http://example.com", use_default_fields=False)

    try:
        status = JobStatus(row[5]) if row[5] else JobStatus.DRAFT
    except Exception:
        status = JobStatus.DRAFT

    return Job(
        id=row[0],
        name=row[1],
        description=row[2],
        template=row[3],
        config=config,
        status=status,
        created_at=_parse_iso_datetime(row[6]),
        updated_at=_parse_iso_datetime(row[7]),
        last_run_at=_parse_iso_datetime(row[8], None) if row[8] else None,
        next_run_at=_parse_iso_datetime(row[9], None) if row[9] else None,
        run_count=row[10] if row[10] is not None else 0,
        success_count=row[11] if row[11] is not None else 0,
        failure_count=row[12] if row[12] is not None else 0
    )

# Item operations
def create_item(item: ScrapedItem) -> ScrapedItem:
    """Create a new scraped item"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT INTO items (id, job_id, data, url, created_at, status)
            VALUES (:id, :job_id, :data, :url, :created_at, :status)
        """), {
            "id": item.id, "job_id": item.job_id, "data": json.dumps(item.data), 
            "url": item.url, "created_at": item.created_at.isoformat(), "status": item.status
        })
    return item

def get_items_by_job(job_id: str, limit: int = None, offset: int = 0) -> List[ScrapedItem]:
    """Get items for a job with pagination"""
    with get_session() as conn:
        query = "SELECT * FROM items WHERE job_id = :job_id ORDER BY created_at DESC"
        params = {"job_id": job_id}
        if limit is not None:
            query += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
        cursor = conn.execute(text(query), params)
        return [_row_to_item(row) for row in cursor.fetchall()]

def get_items_count_by_job(job_id: str) -> int:
    """Get total count of items for a job"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT COUNT(*) FROM items WHERE job_id = :job_id"), {"job_id": job_id})
        row = cursor.fetchone()
        return row[0] if row else 0

def get_all_items() -> List[ScrapedItem]:
    """Get all scraped items"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM items ORDER BY created_at DESC"))
        return [_row_to_item(row) for row in cursor.fetchall()]

def delete_items_by_job(job_id: str) -> int:
    """Delete all items for a job"""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM items WHERE job_id = :job_id"), {"job_id": job_id})
    return cursor.rowcount

def delete_item(item_id: str) -> bool:
    """Delete a single scraped item."""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM items WHERE id = :item_id"), {"item_id": item_id})
    return cursor.rowcount > 0

def _row_to_item(row) -> ScrapedItem:
    """Convert database row to ScrapedItem model"""
    raw_data = row[2]
    if isinstance(raw_data, str):
        try:
            parsed_data = json.loads(raw_data)
        except Exception:
            parsed_data = {"raw": raw_data}
    elif isinstance(raw_data, dict):
        parsed_data = raw_data
    else:
        parsed_data = {"raw": str(raw_data)}

    return ScrapedItem(
        id=row[0],
        job_id=row[1],
        data=parsed_data,
        url=row[3],
        created_at=_parse_iso_datetime(row[4]),
        status=row[5]
    )

# Result operations
def create_result(result: JobResult) -> JobResult:
    """Create a new job result"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT INTO results (id, job_id, items_count, success_count, failure_count,
                               started_at, completed_at, error_message)
            VALUES (:id, :job_id, :items_count, :success_count, :failure_count,
                   :started_at, :completed_at, :error_message)
        """), {
            "id": result.id, "job_id": result.job_id, "items_count": result.items_count, 
            "success_count": result.success_count, "failure_count": result.failure_count,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "error_message": result.error_message
        })
    return result

def get_results_by_job(job_id: str) -> List[JobResult]:
    """Get all results for a job"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM results WHERE job_id = :job_id ORDER BY started_at DESC"), {"job_id": job_id})
        return [_row_to_result(row) for row in cursor.fetchall()]

def _row_to_result(row) -> JobResult:
    """Convert database row to JobResult model"""
    return JobResult(
        id=row[0],
        job_id=row[1],
        items_count=row[2],
        success_count=row[3],
        failure_count=row[4],
        started_at=_parse_iso_datetime(row[5]),
        completed_at=_parse_iso_datetime(row[6], None) if row[6] else None,
        error_message=row[7]
    )

# Settings operations
def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT value FROM settings WHERE key = :key"), {"key": key})
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
    return default

def set_setting(key: str, value: Any):
    """Set a setting value"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (:key, :value)
        """), {"key": key, "value": json.dumps(value)})
    logger.info(f"Setting updated: {key}")

def get_settings() -> Settings:
    """Get all settings"""
    return Settings(
        max_concurrent_jobs=get_setting("max_concurrent_jobs", 3),
        default_headless=get_setting("default_headless", False),
        default_delay_ms=get_setting("default_delay_ms", 1000),
        data_storage_path=get_setting("data_storage_path", "data"),
        auto_update_check=get_setting("auto_update_check", True),
        dark_mode=get_setting("dark_mode", True),
        log_level=get_setting("log_level", "INFO"),
        default_user_agent=get_setting("default_user_agent"),
        default_proxy=get_setting("default_proxy")
    )

def save_settings(settings: Settings):
    """Save all settings"""
    for key, value in settings.model_dump().items():
        set_setting(key, value)

# Template operations
def create_template(template: Template) -> Template:
    """Create a new template"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT INTO templates (id, name, description, category, config, icon, created_at)
            VALUES (:id, :name, :description, :category, :config, :icon, :created_at)
        """), {
            "id": template.id, "name": template.name, "description": template.description, 
            "category": template.category, "config": template.config.model_dump_json(), 
            "icon": template.icon, "created_at": template.created_at.isoformat()
        })
    logger.info(f"Created template: {template.name}")
    return template

def get_template(template_id: str) -> Optional[Template]:
    """Get a template by ID"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM templates WHERE id = :template_id"), {"template_id": template_id})
        row = cursor.fetchone()
        if row:
            return _row_to_template(row)
    return None

def get_all_templates() -> List[Template]:
    """Get all templates"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM templates ORDER BY name"))
        return [_row_to_template(row) for row in cursor.fetchall()]

def delete_template(template_id: str) -> bool:
    """Delete a template"""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM templates WHERE id = :template_id"), {"template_id": template_id})
    return cursor.rowcount > 0

def _row_to_template(row) -> Template:
    """Convert database row to Template model"""
    config = _coerce_source_config(row[4], "http://example.com", use_default_fields=True)

    created_at_value = row[6] if len(row) > 6 else None
    if created_at_value in (None, ""):
        created_at_value = datetime.now().isoformat()
    elif isinstance(created_at_value, datetime):
        created_at_value = created_at_value.isoformat()

    category_value = row[3] if len(row) > 3 else "general"
    if category_value in (None, ""):
        category_value = "general"

    return Template(
        id=row[0],
        name=row[1],
        description=row[2],
        category=str(category_value),
        config=config,
        icon=row[5],
        created_at=_parse_iso_datetime(created_at_value)
    )

# Web Scraping Sources
def create_source(source: WebScrapingSource):
    """Create a new web scraping source"""
    source.config = _coerce_source_config(source.config.model_dump(), source.url, use_default_fields=True)
    with get_session() as conn:
        if _source_schema_mode(conn) == "current":
            conn.execute(text("""
                INSERT INTO web_scraping_sources (id, name, url, description, category, config, enabled, created_at, updated_at)
                VALUES (:id, :name, :url, :description, :category, :config, :enabled, :created_at, :updated_at)
            """), {
                "id": source.id, "name": source.name, "url": source.url, "description": source.description,
                "category": source.category, "config": source.config.model_dump_json(),
                "enabled": source.enabled, "created_at": source.created_at.isoformat(),
                "updated_at": source.updated_at.isoformat()
            })
        else:
            conn.execute(text("""
                INSERT INTO web_scraping_sources (
                    id, name, url, type, category_id, selectors, advance_config, presets,
                    fetch_interval, is_active, last_fetched_at, created_at, content_type,
                    scrape_depth, use_browser, max_pages, delay, pagination_type,
                    pagination_selector, pagination_pattern, proxy_enabled, proxy_provider,
                    proxy_config, ssl_verify, timeout, connect_timeout
                )
                VALUES (
                    :id, :name, :url, :type, :category_id, :selectors, :advance_config, :presets,
                    :fetch_interval, :is_active, :last_fetched_at, :created_at, :content_type,
                    :scrape_depth, :use_browser, :max_pages, :delay, :pagination_type,
                    :pagination_selector, :pagination_pattern, :proxy_enabled, :proxy_provider,
                    :proxy_config, :ssl_verify, :timeout, :connect_timeout
                )
            """), _source_to_legacy_params(source))

def get_source(source_id: str) -> Optional[WebScrapingSource]:
    """Get a source by ID"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM web_scraping_sources WHERE id = :source_id"), {"source_id": source_id})
        row = cursor.fetchone()
        if row:
            return _row_to_source(row)
    return None

def get_all_sources() -> List[WebScrapingSource]:
    """Get all sources"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM web_scraping_sources ORDER BY name"))
        sources = []
        for row in cursor.fetchall():
            try:
                sources.append(_row_to_source(row))
            except Exception as e:
                logger.debug(f"Skipping invalid source row: {e}")
        return sources

def update_source(source: WebScrapingSource):
    """Update a source"""
    source.config = _coerce_source_config(source.config.model_dump(), source.url, use_default_fields=True)
    with get_session() as conn:
        if _source_schema_mode(conn) == "current":
            conn.execute(text("""
                UPDATE web_scraping_sources
                SET name = :name, url = :url, description = :description, category = :category,
                    config = :config, enabled = :enabled, updated_at = :updated_at
                WHERE id = :id
            """), {
                "name": source.name, "url": source.url, "description": source.description,
                "category": source.category, "config": source.config.model_dump_json(),
                "enabled": source.enabled, "updated_at": source.updated_at.isoformat(), "id": source.id
            })
        else:
            conn.execute(text("""
                UPDATE web_scraping_sources
                SET name = :name, url = :url, type = :type, category_id = :category_id,
                    selectors = :selectors, advance_config = :advance_config, presets = :presets,
                    fetch_interval = :fetch_interval, is_active = :is_active,
                    last_fetched_at = :last_fetched_at, created_at = :created_at,
                    content_type = :content_type, scrape_depth = :scrape_depth,
                    use_browser = :use_browser, max_pages = :max_pages, delay = :delay,
                    pagination_type = :pagination_type, pagination_selector = :pagination_selector,
                    pagination_pattern = :pagination_pattern, proxy_enabled = :proxy_enabled,
                    proxy_provider = :proxy_provider, proxy_config = :proxy_config,
                    ssl_verify = :ssl_verify, timeout = :timeout, connect_timeout = :connect_timeout
                WHERE id = :id
            """), _source_to_legacy_params(source))

def delete_source(source_id: str) -> bool:
    """Delete a source"""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM web_scraping_sources WHERE id = :source_id"), {"source_id": source_id})
    return cursor.rowcount > 0

def _row_to_source(row) -> WebScrapingSource:
    """Convert database row to WebScrapingSource model"""
    mapping = getattr(row, "_mapping", {})

    def _value(keys, index=None, default=None):
        if isinstance(keys, str):
            keys = (keys,)

        for key in keys:
            if key in mapping and mapping[key] is not None:
                return mapping[key]

        if index is not None:
            try:
                value = row[index]
                if value is not None:
                    return value
            except Exception:
                pass

        return default

    raw_config = _value(("config", "advance_config", "selectors", "proxy_config"), 5, None)
    enabled_value = _value(("enabled", "is_active"), 6, True)
    created_at_value = _value(("created_at",), 7, datetime.now().isoformat())
    updated_at_value = _value(("updated_at", "last_fetched_at", "created_at"), 8, created_at_value)
    source_url = str(_value(("url",), 2, "http://example.com") or "http://example.com")
    category_value = _value(("category", "category_id"), 4, "general")
    if category_value in (None, ""):
        category_value = "general"
    category_value = str(category_value)

    config = _coerce_source_config(raw_config, source_url, use_default_fields=True)

    return WebScrapingSource(
        id=str(_value(("id",), 0)),
        name=_value(("name",), 1, ""),
        url=source_url,
        description=_value(("description",), 3, None),
        category=category_value,
        config=config,
        enabled=bool(enabled_value),
        created_at=_parse_iso_datetime(created_at_value),
        updated_at=_parse_iso_datetime(updated_at_value, _parse_iso_datetime(created_at_value))
    )

def _source_to_legacy_params(source: WebScrapingSource) -> Dict[str, Any]:
    """Map the current source model to the legacy database columns."""
    return {
        "id": source.id,
        "name": source.name,
        "url": source.url,
        "type": "html",
        "category_id": 0,
        "selectors": json.dumps([field.model_dump() for field in source.config.fields]),
        "advance_config": source.config.model_dump_json(),
        "presets": None,
        "fetch_interval": source.config.schedule.interval_minutes,
        "is_active": 1 if source.enabled else 0,
        "last_fetched_at": source.updated_at.isoformat(),
        "created_at": source.created_at.isoformat(),
        "content_type": "articles",
        "scrape_depth": 1,
        "use_browser": 0 if source.config.browser.headless else 1,
        "max_pages": source.config.pagination.max_pages,
        "delay": max(0, source.config.browser.delay_ms // 1000),
        "pagination_type": source.config.pagination.type,
        "pagination_selector": source.config.pagination.selector or None,
        "pagination_pattern": None,
        "proxy_enabled": 1 if source.config.proxy.enabled else 0,
        "proxy_provider": None,
        "proxy_config": json.dumps(source.config.proxy.model_dump()) if source.config.proxy else None,
        "ssl_verify": 1,
        "timeout": 30,
        "connect_timeout": 10
    }

# Secure storage using keyring
def get_secure_value(service: str, username: str) -> Optional[str]:
    """Get a secure value from keyring"""
    try:
        return keyring.get_password(service, username)
    except Exception as e:
        logger.warning(f"Failed to get secure value: {e}")
        return None

def set_secure_value(service: str, username: str, password: str):
    """Set a secure value in keyring"""
    try:
        keyring.set_password(service, username, password)
    except Exception as e:
        logger.error(f"Failed to set secure value: {e}")

def delete_secure_value(service: str, username: str):
    """Delete a secure value from keyring"""
    try:
        keyring.delete_password(service, username)
    except Exception as e:
        logger.warning(f"Failed to delete secure value: {e}")

# Statistics
def get_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    with get_session() as conn:
        # Total jobs
        cursor = conn.execute(text("SELECT COUNT(*) as count FROM jobs"))
        row = cursor.fetchone()
        total_jobs = row[0] if row else 0

        # Jobs by status
        cursor = conn.execute(text("SELECT status, COUNT(*) as count FROM jobs GROUP BY status"))
        jobs_by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Total items
        cursor = conn.execute(text("SELECT COUNT(*) as count FROM items"))
        row = cursor.fetchone()
        total_items = row[0] if row else 0

        # Items today
        today = datetime.now().date().isoformat()
        cursor = conn.execute(text("SELECT COUNT(*) as count FROM items WHERE created_at LIKE :today"), {"today": f"{today}%"})
        row = cursor.fetchone()
        items_today = row[0] if row else 0

        # Success rate
        cursor = conn.execute(text("SELECT SUM(success_count) as total FROM jobs"))
        row = cursor.fetchone()
        success_count = row[0] if row and row[0] else 0
        cursor = conn.execute(text("SELECT SUM(failure_count) as total FROM jobs"))
        row = cursor.fetchone()
        failure_count = row[0] if row and row[0] else 0

        total_runs = success_count + failure_count
        success_rate = (success_count / total_runs * 100) if total_runs > 0 else 0

        return {
            "total_jobs": total_jobs,
            "jobs_by_status": jobs_by_status,
            "total_items": total_items,
            "items_today": items_today,
            "success_rate": round(success_rate, 1)
        }
