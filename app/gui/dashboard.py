"""
Dashboard view for ScrapMaster Desktop
"""

import customtkinter as ctk
from datetime import datetime
import tkinter.messagebox as messagebox
import threading

from app.database import db
from app.utils.logger import get_logger

logger = get_logger()

class DashboardView(ctk.CTkFrame):
    """Dashboard statistics view"""

    def __init__(self, parent):
        super().__init__(parent)

        # Configure grid
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Stat card value labels
        self.stat_value_labels = []
        
        # Create header
        header = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        header.grid(row=0, column=0, columnspan=3, padx=30, pady=(30, 10), sticky="w")
        
        # Initialize stats
        self.stats = {"total_jobs": 0, "items_today": 0, "success_rate": 0.0}

        # Create stat cards (will be updated when stats load)
        self._create_stat_cards()

        # Create recent activity
        self._create_recent_activity()

        # Load stats in background
        self._load_stats_async()
        
        logger.debug("Dashboard view created")

    def _load_stats_async(self):
        """Load stats in background thread"""
        def load_stats():
            try:
                stats = db.get_stats()
                # Update on main thread
                self.after(0, lambda: self._update_stats(stats))
            except Exception as e:
                logger.error(f"Failed to load dashboard stats: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load dashboard statistics:\n{str(e)}"))

        thread = threading.Thread(target=load_stats, daemon=True)
        thread.start()

    def _update_stats(self, stats):
        """Update stats on UI"""
        self.stats = stats
        # Refresh stat cards
        self._create_stat_cards()

    def _create_stat_cards(self):
        """Create or update statistic cards"""
        cards_data = [
            {
                "title": "Total Jobs",
                "value": str(self.stats.get("total_jobs", 0)),
                "icon": "📋",
                "color": "#3498db"
            },
            {
                "title": "Items Today",
                "value": str(self.stats.get("items_today", 0)),
                "icon": "📦",
                "color": "#2ecc71"
            },
            {
                "title": "Success Rate",
                "value": f"{self.stats.get('success_rate', 0):.1f}%",
                "icon": "✅",
                "color": "#9b59b6"
            },
        ]

        for idx, card in enumerate(cards_data):
            if idx < len(self.stat_value_labels):
                # Update existing label
                self.stat_value_labels[idx].configure(text=card["value"])
            else:
                # Create new card
                card_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray17"))
                card_frame.grid(row=1, column=idx, padx=20, pady=20, sticky="nsew")

                # Icon
                icon_label = ctk.CTkLabel(
                    card_frame,
                    text=card["icon"],
                    font=ctk.CTkFont(size=40)
                )
                icon_label.pack(pady=(20, 10))

                # Value
                value_label = ctk.CTkLabel(
                    card_frame,
                    text=card["value"],
                    font=ctk.CTkFont(size=32, weight="bold")
                )
                value_label.pack(pady=5)
                self.stat_value_labels.append(value_label)

                # Title
                title_label = ctk.CTkLabel(
                    card_frame,
                    text=card["title"],
                    font=ctk.CTkFont(size=14),
                    text_color="gray"
                )
                title_label.pack(pady=(0, 20))
    
    def _create_recent_activity(self):
        """Create recent activity section"""
        activity_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray17"))
        activity_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")
        
        # Title
        title = ctk.CTkLabel(
            activity_frame,
            text="Recent Jobs",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")
        
        # Get recent jobs
        jobs = db.get_all_jobs()[:5]
        
        if not jobs:
            no_jobs_label = ctk.CTkLabel(
                activity_frame,
                text="No jobs yet. Create your first scraping job!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_jobs_label.pack(pady=40)
        else:
            # Jobs list
            for job in jobs:
                job_frame = ctk.CTkFrame(activity_frame, fg_color="transparent")
                job_frame.pack(fill="x", padx=20, pady=5)
                
                # Job name
                name_label = ctk.CTkLabel(
                    job_frame,
                    text=job.name,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                name_label.pack(side="left", pady=10)
                
                # Status
                status_label = ctk.CTkLabel(
                    job_frame,
                    text=f"Status: {job.status.value}",
                    font=ctk.CTkFont(size=12),
                    text_color="gray"
                )
                status_label.pack(side="right", padx=10)
        
        # View all button
        view_btn = ctk.CTkButton(
            activity_frame,
            text="View All Jobs",
            command=lambda: self.master.master.navigate_to("my_jobs")
        )
        view_btn.pack(pady=20)


def refresh_dashboard():
    """Refresh dashboard data"""
    # This can be called to refresh the dashboard
    logger.debug("Dashboard refreshed")