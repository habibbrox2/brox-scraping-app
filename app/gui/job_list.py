"""
Job list view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox
import threading

from app.database import db
from app.database.models import Job, JobStatus
from app.scraper.scraper_engine import scraper_engine
from app.utils.logger import get_logger

logger = get_logger()

class JobListView(ctk.CTkFrame):
    """Job list view"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Create UI
        self._create_header()
        self._create_job_list()
        
        # Load jobs
        self.jobs = []
        self._load_jobs_async()
        
        logger.debug("Job list view created")
    
    def _create_header(self):
        """Create header"""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))

        title = ctk.CTkLabel(
            header_frame,
            text="My Jobs",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=(20, 16))

        self.summary_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70")
        )
        self.summary_label.pack(side="left", padx=8)

        ctk.CTkLabel(header_frame, text="Quick Run:").pack(side="left", padx=(30, 8))

        self.source_var = ctk.StringVar(value="")
        self.source_combo = ctk.CTkComboBox(
            header_frame,
            values=self._get_source_options(),
            variable=self.source_var,
            width=280
        )
        self.source_combo.pack(side="left", padx=8)

        ctk.CTkButton(
            header_frame,
            text="▶ Run Source",
            command=self._run_from_source,
            width=100,
            height=32
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self._load_jobs,
            width=90,
            height=32
        ).pack(side="right", padx=8)

        ctk.CTkButton(
            header_frame,
            text="+ New Job",
            command=self._new_job,
            width=110,
            height=32,
            fg_color=("#2563eb", "#3b82f6")
        ).pack(side="right", padx=8)
    
    def _get_source_options(self):
        """Get source options for combo"""
        sources = db.get_all_sources()
        return [f"{s.name} - {s.url}" for s in sources if s.enabled]
    
    def _run_from_source(self):
        """Run job from selected source"""
        source_name = self.source_var.get()
        if not source_name:
            messagebox.showwarning("No Source", "Please select a source to run")
            return
        
        # Find source
        sources = db.get_all_sources()
        source = next((s for s in sources if f"{s.name} - {s.url}" == source_name), None)
        if not source:
            messagebox.showerror("Error", "Source not found")
            return
        
        # Create temporary job from source config
        from app.database.models import Job, JobStatus
        from app.utils.helpers import generate_unique_id
        from datetime import datetime
        
        temp_job = Job(
            id=generate_unique_id(),
            name=f"Quick Run: {source.name}",
            description=f"Auto-generated from source: {source.name}",
            config=source.config,
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save temp job
        db.create_job(temp_job)
        
        # Run it
        self._run_job(temp_job)
        
        # Refresh combo
        self.source_combo.configure(values=self._get_source_options())
    
    def _cancel_job(self, job: Job):
        """Cancel running job"""
        if messagebox.askyesno("Cancel Job", f"Cancel running job '{job.name}'?"):
            job.status = JobStatus.CANCELLED
            db.update_job(job)
            self._load_jobs()
            messagebox.showinfo("Job Cancelled", f"Job '{job.name}' has been cancelled!")
    
    def _create_job_list(self):
        """Create job list"""
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Jobs")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
    
    def _load_jobs_async(self):
        """Load jobs from database in background"""
        def load_jobs():
            try:
                jobs = db.get_all_jobs()
                # Update on main thread
                self.after(0, lambda: self._update_jobs(jobs))
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load jobs:\n{str(e)}"))
                self.after(0, lambda: self._update_jobs([]))

        thread = threading.Thread(target=load_jobs, daemon=True)
        thread.start()

    def _update_jobs(self, jobs):
        """Update jobs on UI"""
        self.jobs = jobs
        self._refresh_jobs_ui()

    def _load_jobs(self):
        """Load jobs from database (legacy name for refresh)"""
        self._refresh_jobs_ui()

    def _refresh_jobs_ui(self):
        """Refresh the jobs UI"""
        # Clear current list
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.jobs:
            empty_label = ctk.CTkLabel(
                self.list_frame,
                text="No jobs yet. Create your first scraping job!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=40)
            return

        # Create job cards
        for job in self.jobs:
            self._create_job_card(job)
    
    def _create_job_card(self, job: Job):
        """Create job card"""
        card = ctk.CTkFrame(self.list_frame)
        card.pack(fill="x", pady=5)
        
        # Job info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=20, pady=15)
        
        # Name
        name_label = ctk.CTkLabel(
            info_frame,
            text=job.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x")
        
        # Description
        if job.description:
            desc_label = ctk.CTkLabel(
                info_frame,
                text=job.description,
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w"
            )
            desc_label.pack(fill="x")
        
        # Stats
        stats_text = f"Run: {job.run_count} | Success: {job.success_count} | Failed: {job.failure_count}"
        stats_label = ctk.CTkLabel(
            info_frame,
            text=stats_text,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        stats_label.pack(fill="x")
        
        # Status badge
        status_colors = {
            JobStatus.DRAFT: ("gray", "gray"),
            JobStatus.SCHEDULED: ("blue", "blue"),
            JobStatus.RUNNING: ("orange", "orange"),
            JobStatus.COMPLETED: ("green", "green"),
            JobStatus.FAILED: ("red", "red"),
            JobStatus.PAUSED: ("yellow", "yellow"),
            JobStatus.CANCELLED: ("gray", "gray"),
        }
        
        status_color = status_colors.get(job.status, ("gray", "gray"))
        status_label = ctk.CTkLabel(
            card,
            text=job.status.value.upper(),
            text_color="white",
            fg_color=status_color[0],
            corner_radius=5,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        status_label.pack(side="right", padx=10, pady=10)
        
        # Actions
        action_frame = ctk.CTkFrame(card, fg_color="transparent")
        action_frame.pack(side="right", padx=10)
        
        # Run button
        if job.status != JobStatus.RUNNING:
            ctk.CTkButton(
                action_frame,
                text="▶ Run",
                command=lambda j=job: self._run_job(j),
                width=80,
                height=30
            ).pack(pady=2)
        else:
            ctk.CTkButton(
                action_frame,
                text="⏹ Cancel",
                command=lambda j=job: self._cancel_job(j),
                width=80,
                height=30,
                fg_color="#e74c3c"
            ).pack(pady=2)
        
        # Edit button
        ctk.CTkButton(
            action_frame,
            text="✏ Edit",
            command=lambda j=job: self._edit_job(j),
            width=80,
            height=30
        ).pack(pady=2)
        
        # Delete button
        ctk.CTkButton(
            action_frame,
            text="🗑 Delete",
            command=lambda j=job: self._delete_job(j),
            width=80,
            height=30,
            fg_color="#c0392b"
        ).pack(pady=2)
    
    def _new_job(self):
        """Create new job"""
        self.master.master.navigate_to("new_job")
    
    def _edit_job(self, job: Job):
        """Edit job"""
        # Import here to avoid circular import
        from app.gui.job_form import JobFormView
        
        # Clear content and show form
        for widget in self.master.winfo_children():
            widget.destroy()
        
        JobFormView(self.master, job=job).pack(fill="both", expand=True)
    
    def _delete_job(self, job: Job):
        """Delete job"""
        if messagebox.askyesno("Delete Job", f"Delete job '{job.name}'?"):
            try:
                db.delete_job(job.id)
                db.delete_items_by_job(job.id)
                self._load_jobs()
                messagebox.showinfo("Success", "Job deleted!")
            except Exception as e:
                logger.error(f"Failed to delete job: {e}")
                messagebox.showerror("Error", f"Failed to delete job:\n{str(e)}")
    
    def _run_job(self, job: Job):
        """Run job"""
        # Update status
        job.status = JobStatus.RUNNING
        db.update_job(job)
        self._load_jobs()
        
        # Run in background
        import threading
        import asyncio
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(scraper_engine.run_job(job))
            finally:
                loop.close()
            # Update GUI from main thread
            self.after(0, self._load_jobs)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        
        messagebox.showinfo("Job Started", f"Job '{job.name}' is now running!")