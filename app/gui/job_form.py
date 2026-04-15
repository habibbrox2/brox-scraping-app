"""
Job form view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox
import json
import re
from datetime import datetime

from app.database.models import (
    Job, JobConfig, FieldConfig, PaginationConfig, ProxyConfig, BrowserConfig, ScheduleConfig, JobStatus
)
from app.database import db
from app.utils.helpers import generate_unique_id
from app.utils.logger import get_logger
from app.scheduler import job_scheduler

logger = get_logger()

class JobFormView(ctk.CTkFrame):
    """Job creation/editing form view"""
    
    def __init__(self, parent, job: Job = None):
        super().__init__(parent)
        
        self.job = job
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create form
        self._create_form()
        
        logger.debug(f"Job form view created for: {job.name if job else 'new job'}")
    
    def _create_form(self):
        """Create job form"""
        # Scrollable frame
        scrollable = ctk.CTkScrollableFrame(self, label_text="Job Configuration")
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Basic info section
        basic_frame = ctk.CTkFrame(scrollable)
        basic_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            basic_frame,
            text="Basic Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Job name
        self.name_entry = self._create_input_field(
            basic_frame,
            "Job Name:",
            self.job.name if self.job else ""
        )
        
        # Description
        self.desc_entry = self._create_input_field(
            basic_frame,
            "Description:",
            self.job.description if self.job else ""
        )
        
        # URL section
        url_frame = ctk.CTkFrame(scrollable)
        url_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            url_frame,
            text="Target URLs",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Primary URL
        self.url_entry = self._create_input_field(
            url_frame,
            "URL:",
            self.job.config.url if self.job and self.job.config.url else ""
        )
        
        # Additional URLs (comma-separated)
        self.urls_entry = self._create_input_field(
            url_frame,
            "Additional URLs (comma-separated):",
            ",".join(self.job.config.urls) if self.job and self.job.config.urls else ""
        )
        
        # Fields section
        fields_frame = ctk.CTkFrame(scrollable)
        fields_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            fields_frame,
            text="Data Fields",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # JSON Schema editor
        self.fields_text = ctk.CTkTextbox(
            fields_frame,
            height=200,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.fields_text.pack(fill="x", padx=20, pady=10)
        
        # Default fields
        default_fields = [
            {"name": "title", "selector": "h3", "selector_type": "css", "attribute": "text"},
            {"name": "price", "selector": ".price", "selector_type": "css", "attribute": "text"},
            {"name": "description", "selector": ".description", "selector_type": "css", "attribute": "text"},
        ]
        
        if self.job and self.job.config.fields:
            default_fields = [f.model_dump() for f in self.job.config.fields]
        
        self.fields_text.insert("1.0", json.dumps(default_fields, indent=2))
        
        # Root selector
        self.root_selector_entry = self._create_input_field(
            fields_frame,
            "Root Element Selector:",
            self.job.config.root_selector if self.job else ""
        )
        
        # Browser settings section
        browser_frame = ctk.CTkFrame(scrollable)
        browser_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            browser_frame,
            text="Browser Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Headless mode
        self.headless_var = ctk.BooleanVar(value=self.job.config.browser.headless if self.job else True)
        ctk.CTkCheckBox(
            browser_frame,
            text="Headless Mode (no visible browser)",
            variable=self.headless_var
        ).pack(pady=5, padx=20, anchor="w")
        
        # Delay
        self.delay_entry = self._create_input_field(
            browser_frame,
            "Delay (ms):",
            str(self.job.config.browser.delay_ms if self.job else 1000)
        )
        
        # User Agent
        self.ua_entry = self._create_input_field(
            browser_frame,
            "Custom User-Agent:",
            self.job.config.browser.user_agent if self.job and self.job.config.browser.user_agent else ""
        )
        
        # Pagination section
        pagination_frame = ctk.CTkFrame(scrollable)
        pagination_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            pagination_frame,
            text="Pagination",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        self.pagination_enabled_var = ctk.BooleanVar(
            value=self.job.config.pagination.enabled if self.job else False
        )
        ctk.CTkCheckBox(
            pagination_frame,
            text="Enable Pagination",
            variable=self.pagination_enabled_var
        ).pack(pady=5, padx=20, anchor="w")
        
        self.max_pages_entry = self._create_input_field(
            pagination_frame,
            "Max Pages:",
            str(self.job.config.pagination.max_pages if self.job else 10)
        )
        
        # Schedule section
        schedule_frame = ctk.CTkFrame(scrollable)
        schedule_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            schedule_frame,
            text="Scheduling",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        self.schedule_enabled_var = ctk.BooleanVar(
            value=self.job.config.schedule.enabled if self.job and hasattr(self.job.config, 'schedule') else False
        )
        ctk.CTkCheckBox(
            schedule_frame,
            text="Enable Scheduled Runs",
            variable=self.schedule_enabled_var
        ).pack(pady=5, padx=20, anchor="w")
        
        self.interval_entry = self._create_input_field(
            schedule_frame,
            "Interval (minutes):",
            str(self.job.config.schedule.interval_minutes if self.job and self.job.config.schedule.interval_minutes is not None else 60)
        )
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            fg_color="gray"
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Save Job",
            command=self._save
        ).pack(side="right", padx=10)
    
    def _create_input_field(self, parent, label: str, default: str = "") -> ctk.CTkEntry:
        """Create input field"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            frame,
            text=label,
            width=180,
            anchor="w"
        ).pack(side="left", pady=10)
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, default)
        entry.pack(side="right", fill="x", expand=True, pady=10)
        
        return entry
    
    def _validate(self) -> bool:
        """Validate form inputs"""
        errors = []
        
        # Name
        name = self.name_entry.get().strip()
        if not name:
            errors.append("Job name is required")
        
        # URL
        url = self.url_entry.get().strip()
        if not url:
            errors.append("URL is required")
        elif not re.match(r'^https?://', url):
            errors.append("URL must start with http:// or https://")
        
        # Fields
        try:
            fields_data = json.loads(self.fields_text.get("1.0", "end"))
            if not fields_data:
                errors.append("At least one field is required")
            for i, f in enumerate(fields_data):
                if not f.get('name'):
                    errors.append(f"Field {i+1}: name is required")
                if not f.get('selector'):
                    errors.append(f"Field {i+1}: selector is required")
                selector_type = f.get('selector_type', 'css')
                if selector_type not in ['css', 'xpath']:
                    errors.append(f"Field {i+1}: selector_type must be 'css' or 'xpath'")
        except json.JSONDecodeError:
            errors.append("Fields must be valid JSON")
        
        # Delay
        try:
            delay = int(self.delay_entry.get() or "1000")
            if delay < 0:
                errors.append("Delay must be non-negative")
        except ValueError:
            errors.append("Delay must be a number")
        
        # Max pages
        try:
            max_pages = int(self.max_pages_entry.get() or "10")
            if max_pages < 1:
                errors.append("Max pages must be at least 1")
        except ValueError:
            errors.append("Max pages must be a number")
        
        # Interval
        try:
            interval = int(self.interval_entry.get() or "60")
            if interval < 1:
                errors.append("Interval must be at least 1 minute")
        except ValueError:
            errors.append("Interval must be a number")
        
        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True
    
    def _save(self):
        """Save job"""
        if not self._validate():
            return
        
        try:
            # Parse fields
            fields_data = json.loads(self.fields_text.get("1.0", "end"))
            fields = [FieldConfig(**f) for f in fields_data]
            
            # Build config
            config = JobConfig(
                url=self.url_entry.get(),
                urls=[u.strip() for u in self.urls_entry.get().split(",") if u.strip()],
                fields=fields,
                root_selector=self.root_selector_entry.get(),
                browser=BrowserConfig(
                    headless=self.headless_var.get(),
                    delay_ms=int(self.delay_entry.get() or "1000"),
                    user_agent=self.ua_entry.get() or None
                ),
                pagination=PaginationConfig(
                    enabled=self.pagination_enabled_var.get(),
                    max_pages=int(self.max_pages_entry.get() or "10")
                ),
                schedule=ScheduleConfig(
                    enabled=self.schedule_enabled_var.get(),
                    interval_minutes=int(self.interval_entry.get() or "60")
                )
            )
            
            # Create job
            job = Job(
                id=self.job.id if self.job else generate_unique_id(),
                name=self.name_entry.get(),
                description=self.desc_entry.get(),
                config=config,
                status=self.job.status if self.job else JobStatus.DRAFT,
                created_at=self.job.created_at if self.job else datetime.now(),
                updated_at=datetime.now()
            )
            
            if self.job:
                db.update_job(job)
                messagebox.showinfo("Success", "Job updated successfully!")
            else:
                db.create_job(job)
                messagebox.showinfo("Success", "Job created successfully!")
            
            # Handle scheduling
            if job.config.schedule.enabled and job.config.schedule.interval_minutes:
                job_scheduler.schedule_job(job.id, interval_minutes=job.config.schedule.interval_minutes)
            else:
                job_scheduler.unschedule_job(job.id)
            
            # Navigate to jobs list
            self.master.master.navigate_to("my_jobs")
            
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON in fields: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save job: {e}")
            logger.error(f"Save job error: {e}")
    
    def _cancel(self):
        """Cancel and go back"""
        self.master.master.navigate_to("my_jobs")
