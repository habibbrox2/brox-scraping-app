"""
Results view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import csv
import os

from app.database import db
from app.database.models import ScrapedItem
from app.utils.logger import get_logger

logger = get_logger()

class ResultsView(ctk.CTkFrame):
    """Results view for viewing scraped data"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.items = []
        self.filtered_items = []
        self.selected_job_id = None
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Create UI
        self._create_header()
        self._create_filters()
        self._create_results_table()
        
        # Load results
        self._load_results()
        
        logger.debug("Results view created")
    
    def _create_header(self):
        """Create header"""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            header_frame,
            text="Scraped Results",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=20)
        
        # Export buttons
        ctk.CTkButton(
            header_frame,
            text="📊 Export CSV",
            command=self._export_csv
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            header_frame,
            text="📋 Export JSON",
            command=self._export_json
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            header_frame,
            text="📗 Export Excel",
            command=self._export_excel
        ).pack(side="right", padx=10)
    
    def _create_filters(self):
        """Create filters"""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        # Job filter
        ctk.CTkLabel(filter_frame, text="Filter by Job:").pack(side="left", padx=10)
        
        self.job_var = ctk.StringVar(value="all")
        self.job_var.trace("w", self._on_job_change)
        
        self.job_combo = ctk.CTkComboBox(
            filter_frame,
            values=self._get_job_options(),
            variable=self.job_var
        )
        self.job_combo.pack(side="left", padx=10)
        
        # Search
        ctk.CTkLabel(filter_frame, text="Search:").pack(side="left", padx=20)
        
        self.search_entry = ctk.CTkEntry(filter_frame, width=200)
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        # Refresh
        ctk.CTkButton(
            filter_frame,
            text="🔄 Refresh",
            command=self._load_results
        ).pack(side="right", padx=10)
    
    def _create_results_table(self):
        """Create results table"""
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Scrollable frame for table
        self.table = ctk.CTkScrollableFrame(table_frame, label_text="Data")
        self.table.grid(row=0, column=0, sticky="nsew")
        
        # Results count
        self.count_label = ctk.CTkLabel(
            table_frame,
            text="0 items",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.count_label.grid(row=1, column=0, pady=10)
    
    def _get_job_options(self):
        """Get job filter options"""
        jobs = db.get_all_jobs()
        options = ["all"]
        options.extend([job.name for job in jobs])
        return options
    
    def _load_results(self):
        """Load results"""
        self.items = db.get_all_items()
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply filters to items"""
        filtered = self.items
        
        # Job filter
        job_name = self.job_var.get()
        if job_name != "all":
            job = db.get_job_by_name(job_name)
            if job:
                filtered = [item for item in filtered if item.job_id == job.id]
        
        # Search filter
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = [item for item in filtered if search_text in json.dumps(item.data).lower()]
        
        self.filtered_items = filtered
        self._update_table()
    
    def _on_job_change(self, *args):
        """Handle job filter change"""
        self._apply_filters()
    
    def _on_search(self, event):
        """Handle search input"""
        self._apply_filters()
    
    def _update_table(self):
        """Update results table"""
        # Clear current table
        for widget in self.table.winfo_children():
            widget.destroy()
        
        if not self.filtered_items:
            empty_label = ctk.CTkLabel(
                self.table,
                text="No results yet. Run a job to scrape data!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=40)
            self.count_label.configure(text="0 items")
            return
        
        # Show items
        for idx, item in enumerate(self.filtered_items[:100]):  # Limit to 100 for performance
            self._create_item_row(item, idx)
        
        self.count_label.configure(text=f"{len(self.filtered_items)} items")
    
    def _create_item_row(self, item: ScrapedItem, idx: int):
        """Create item row"""
        row = ctk.CTkFrame(self.table, fg_color=("gray85", "gray17") if idx % 2 else "transparent")
        row.pack(fill="x", pady=2)
        
        # Get job name
        job = db.get_job(item.job_id)
        job_name = job.name if job else "Unknown"
        
        # ID
        id_label = ctk.CTkLabel(
            row,
            text=item.id[:8] + "...",
            font=ctk.CTkFont(size=10),
            width=80
        )
        id_label.pack(side="left", padx=5, pady=5)
        
        # Job
        job_label = ctk.CTkLabel(
            row,
            text=job_name,
            font=ctk.CTkFont(size=10),
            width=100
        )
        job_label.pack(side="left", padx=5, pady=5)
        
        # Date
        date_str = item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
        date_label = ctk.CTkLabel(
            row,
            text=date_str,
            font=ctk.CTkFont(size=10),
            width=120
        )
        date_label.pack(side="left", padx=5, pady=5)
        
        # Data preview
        data_preview = json.dumps(item.data)[:60] + "..." if len(json.dumps(item.data)) > 60 else json.dumps(item.data)
        
        data_label = ctk.CTkLabel(
            row,
            text=data_preview,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        data_label.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # View button
        ctk.CTkButton(
            row,
            text="👁 View",
            command=lambda i=item: self._view_item(i),
            width=60,
            height=25
        ).pack(side="right", padx=5)
    
    def _view_item(self, item: ScrapedItem):
        """View item details"""
        from tkinter import simpledialog
        
        # Show item in dialog
        data_str = json.dumps(item.data, indent=2)
        
        # Simple dialog to show data
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Item: {item.id}")
        dialog.geometry("600x500")
        
        text = ctk.CTkTextbox(dialog, font=ctk.CTkFont(family="Courier", size=12))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", data_str)
        text.configure(state="disabled")
        
        ctk.CTkButton(
            dialog,
            text="Copy to Clipboard",
            command=lambda: self.master.clipboard_append(data_str)
        ).pack(pady=10)
        
        ctk.CTkButton(
            dialog,
            text="Close",
            command=dialog.destroy
        ).pack(pady=10)
    
    def _on_job_change(self, *args):
        """On job filter change"""
        selected = self.job_var.get()
        
        if selected == "all":
            self.filtered_items = self.items
        else:
            jobs = db.get_all_jobs()
            job = next((j for j in jobs if j.name == selected), None)
            if job:
                self.filtered_items = [i for i in self.items if i.job_id == job.id]
            else:
                self.filtered_items = []
        
        self._update_table()
    
    def _on_search(self, event):
        """On search"""
        search_text = self.search_entry.get().lower()
        
        if not search_text:
            self.filtered_items = self.items
        else:
            self.filtered_items = [
                i for i in self.items 
                if search_text in json.dumps(i.data).lower() or search_text in i.url.lower()
            ]
        
        self._update_table()
    
    def _export_csv(self):
        """Export to CSV"""
        self._export_file("csv")
    
    def _export_json(self):
        """Export to JSON"""
        self._export_file("json")
    
    def _export_excel(self):
        """Export to Excel"""
        self._export_file("xlsx")
    
    def _export_file(self, format_type: str):
        """Export to file"""
        if not self.filtered_items:
            messagebox.showwarning("No Data", "No results to export!")
            return
        
        # Ask for file path
        if format_type == "csv":
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
        elif format_type == "json":
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
        else:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")]
            )
        
        if not file_path:
            return
        
        try:
            if format_type == "csv":
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    if self.filtered_items:
                        # Get all keys
                        all_keys = set()
                        for item in self.filtered_items:
                            all_keys.update(item.data.keys())
                        
                        writer = csv.DictWriter(f, fieldnames=all_keys)
                        writer.writeheader()
                        
                        for item in self.filtered_items:
                            writer.writerow(item.data)
            
            elif format_type == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    data = [item.data for item in self.filtered_items]
                    json.dump(data, f, indent=2)
            
            elif format_type == "xlsx":
                try:
                    import pandas as pd
                    data = [item.data for item in self.filtered_items]
                    df = pd.DataFrame(data)
                    df.to_excel(file_path, index=False)
                except ImportError:
                    messagebox.showerror("Error", "pandas and openpyxl required for Excel export")
                    return
            
            messagebox.showinfo("Success", f"Exported {len(self.filtered_items)} items to {file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
            logger.error(f"Export error: {e}")