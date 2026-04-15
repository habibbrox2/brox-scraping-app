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

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.stat_value_labels = []
        
        header = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        header.grid(row=0, column=0, columnspan=3, padx=24, pady=(24, 8), sticky="w")
        
        self.stats = {"total_jobs": 0, "items_today": 0, "success_rate": 0.0}

        self._create_stat_cards()

        self._create_recent_activity()

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
                "color": "#3b82f6"
            },
            {
                "title": "Items Today",
                "value": str(self.stats.get("items_today", 0)),
                "icon": "📦",
                "color": "#10b981"
            },
            {
                "title": "Success Rate",
                "value": f"{self.stats.get('success_rate', 0):.1f}%",
                "icon": "✅",
                "color": "#8b5cf6"
            },
        ]

        for idx, card in enumerate(cards_data):
            if idx < len(self.stat_value_labels):
                self.stat_value_labels[idx].configure(text=card["value"])
            else:
                card_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray17"), corner_radius=12)
                card_frame.grid(row=1, column=idx, padx=16, pady=16, sticky="nsew")

                icon_label = ctk.CTkLabel(
                    card_frame,
                    text=card["icon"],
                    font=ctk.CTkFont(size=36)
                )
                icon_label.pack(pady=(24, 8))

                value_label = ctk.CTkLabel(
                    card_frame,
                    text=card["value"],
                    font=ctk.CTkFont(size=28, weight="bold")
                )
                value_label.pack(pady=4)
                self.stat_value_labels.append(value_label)

                title_label = ctk.CTkLabel(
                    card_frame,
                    text=card["title"],
                    font=ctk.CTkFont(size=13),
                    text_color=("gray50", "gray50")
                )
                title_label.pack(pady=(0, 16))
    
    def _create_recent_activity(self):
        """Create recent activity section"""
        activity_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray17"), corner_radius=12)
        activity_frame.grid(row=2, column=0, columnspan=3, padx=16, pady=16, sticky="nsew")
        
        title = ctk.CTkLabel(
            activity_frame,
            text="Recent Jobs",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(pady=(16, 8), padx=20, anchor="w")
        
        jobs = db.get_all_jobs()[:5]
        
        if not jobs:
            empty_frame = ctk.CTkFrame(activity_frame, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=24)
            
            ctk.CTkLabel(
                empty_frame,
                text="📭",
                font=ctk.CTkFont(size=32)
            ).pack(pady=(0, 8))
            
            ctk.CTkLabel(
                empty_frame,
                text="No jobs yet",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=(0, 4))
            
            ctk.CTkLabel(
                empty_frame,
                text="Create your first scraping job to get started",
                font=ctk.CTkFont(size=12),
                text_color=("gray50", "gray60"),
            ).pack()
        else:
            for job in jobs:
                job_frame = ctk.CTkFrame(activity_frame, fg_color="transparent")
                job_frame.pack(fill="x", padx=16, pady=4)
                
                name_label = ctk.CTkLabel(
                    job_frame,
                    text=job.name,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w"
                )
                name_label.pack(side="left", pady=8)
                
                status_label = ctk.CTkLabel(
                    job_frame,
                    text=f"Status: {job.status.value}",
                    font=ctk.CTkFont(size=11),
                    text_color=("gray50", "gray60")
                )
                status_label.pack(side="right", padx=12, pady=8)
        
        view_btn = ctk.CTkButton(
            activity_frame,
            text="View All Jobs",
            command=lambda: self.master.master.navigate_to("my_jobs"),
            width=120,
            height=32
        )
        view_btn.pack(pady=16)


def refresh_dashboard():
    """Refresh dashboard data"""
    # This can be called to refresh the dashboard
    logger.debug("Dashboard refreshed")