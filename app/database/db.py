"""
SQLite database handling for ScrapMaster Desktop
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.database.models import (
    Job, JobStatus, ScrapedItem, JobResult, Settings, Template, WebScrapingSource,
    JobConfig, FieldConfig, PaginationConfig, ProxyConfig, BrowserConfig, ScheduleConfig
)
from app.utils.helpers import generate_unique_id
from app.utils.logger import get_logger

logger = get_logger()

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scrapmaster.db")

# SQLAlchemy engine with connection pooling
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    poolclass=StaticPool,  # Single connection for SQLite
    connect_args={"check_same_thread": False}  # Allow multi-thread access
)

def get_connection():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return engine.connect()

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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (
            job.id, job.name, job.description, job.template,
            job.config.model_dump_json(), job.status.value,
            job.created_at.isoformat(), job.updated_at.isoformat(),
            job.last_run_at.isoformat() if job.last_run_at else None,
            job.next_run_at.isoformat() if job.next_run_at else None,
            job.run_count, job.success_count, job.failure_count
        ))
    logger.info(f"Created job: {job.name}")
    return job

def get_job(job_id: str) -> Optional[Job]:
    """Get a job by ID"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM jobs WHERE id = ?"), (job_id,))
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
        cursor = conn.execute(text("SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC"), (status.value,))
        return [_row_to_job(row) for row in cursor.fetchall()]

def update_job(job: Job) -> Job:
    """Update a job"""
    job.updated_at = datetime.now()
    with get_session() as conn:
        conn.execute(text("""
            UPDATE jobs SET name=?, description=?, template=?, config=?, status=?,
                         updated_at=?, last_run_at=?, next_run_at=?, run_count=?,
                         success_count=?, failure_count=?
            WHERE id=?
        """), (
            job.name, job.description, job.template,
            job.config.model_dump_json(), job.status.value,
            job.updated_at.isoformat(),
            job.last_run_at.isoformat() if job.last_run_at else None,
            job.next_run_at.isoformat() if job.next_run_at else None,
            job.run_count, job.success_count, job.failure_count,
            job.id
        ))
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
    return Job(
        id=row[0],
        name=row[1],
        description=row[2],
        template=row[3],
        config=JobConfig.model_validate_json(row[4]),
        status=JobStatus(row[5]),
        created_at=datetime.fromisoformat(row[6]),
        updated_at=datetime.fromisoformat(row[7]),
        last_run_at=datetime.fromisoformat(row[8]) if row[8] else None,
        next_run_at=datetime.fromisoformat(row[9]) if row[9] else None,
        run_count=row[10],
        success_count=row[11],
        failure_count=row[12]
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

def get_items_by_job(job_id: str) -> List[ScrapedItem]:
    """Get all items for a job"""
    with get_session() as conn:
        cursor = conn.execute(text("SELECT * FROM items WHERE job_id = ? ORDER BY created_at DESC"), (job_id,))
        return [_row_to_item(row) for row in cursor.fetchall()]

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

def _row_to_item(row) -> ScrapedItem:
    """Convert database row to ScrapedItem model"""
    return ScrapedItem(
        id=row[0],
        job_id=row[1],
        data=json.loads(row[2]),
        url=row[3],
        created_at=datetime.fromisoformat(row[4]),
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
        started_at=datetime.fromisoformat(row[5]),
        completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
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
    return Template(
        id=row[0],
        name=row[1],
        description=row[2],
        category=row[3],
        config=JobConfig.model_validate_json(row[4]),
        icon=row[5],
        created_at=datetime.fromisoformat(row[6])
    )

# Web Scraping Sources
def create_source(source: WebScrapingSource):
    """Create a new web scraping source"""
    with get_session() as conn:
        conn.execute(text("""
            INSERT INTO web_scraping_sources (id, name, url, description, category, config, enabled, created_at, updated_at)
            VALUES (:id, :name, :url, :description, :category, :config, :enabled, :created_at, :updated_at)
        """), {
            "id": source.id, "name": source.name, "url": source.url, "description": source.description, 
            "category": source.category, "config": source.config.model_dump_json(), 
            "enabled": source.enabled, "created_at": source.created_at.isoformat(), 
            "updated_at": source.updated_at.isoformat()
        })

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
        return [_row_to_source(row) for row in cursor.fetchall()]

def update_source(source: WebScrapingSource):
    """Update a source"""
    with get_session() as conn:
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

def delete_source(source_id: str) -> bool:
    """Delete a source"""
    with get_session() as conn:
        cursor = conn.execute(text("DELETE FROM web_scraping_sources WHERE id = :source_id"), {"source_id": source_id})
    return cursor.rowcount > 0

def _row_to_source(row) -> WebScrapingSource:
    """Convert database row to WebScrapingSource model"""
    return WebScrapingSource(
        id=row[0],
        name=row[1],
        url=row[2],
        description=row[3],
        category=row[4],
        config=JobConfig.model_validate_json(row[5]),
        enabled=row[6],
        created_at=datetime.fromisoformat(row[7]),
        updated_at=datetime.fromisoformat(row[8])
    )

# Statistics
def get_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    with get_session() as conn:
        # Total jobs
        cursor = conn.execute(text("SELECT COUNT(*) as count FROM jobs"))
        total_jobs = cursor.fetchone()[0]
        
        # Jobs by status
        cursor = conn.execute(text("SELECT status, COUNT(*) as count FROM jobs GROUP BY status"))
        jobs_by_status = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total items
        cursor = conn.execute(text("SELECT COUNT(*) as count FROM items"))
        total_items = cursor.fetchone()[0]
        
        # Items today
        today = datetime.now().date().isoformat()
        cursor = conn.execute(text(f"SELECT COUNT(*) as count FROM items WHERE created_at LIKE '{today}%'"))
        items_today = cursor.fetchone()[0]
        
        # Success rate
        cursor = conn.execute(text("SELECT SUM(success_count) as total FROM jobs"))
        success_count = cursor.fetchone()[0] or 0
        cursor = conn.execute(text("SELECT SUM(failure_count) as total FROM jobs"))
        failure_count = cursor.fetchone()[0] or 0
        
        total_runs = success_count + failure_count
        success_rate = (success_count / total_runs * 100) if total_runs > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "jobs_by_status": jobs_by_status,
            "total_items": total_items,
            "items_today": items_today,
            "success_rate": round(success_rate, 1)
        }