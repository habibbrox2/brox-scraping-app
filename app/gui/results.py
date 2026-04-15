"""
Results view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import csv
import os
import webbrowser

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
        self._job_lookup = {}
        self.current_page = 0
        self.page_size = 50
        self.total_items = 0
        
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
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        
        title = ctk.CTkLabel(
            header_frame,
            text="Scraped Results",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=(0, 16))
        
        export_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        export_frame.pack(side="right")
        
        ctk.CTkButton(
            export_frame,
            text="Export CSV",
            command=self._export_csv,
            width=100,
            height=32
        ).pack(side="right", padx=6)
        
        ctk.CTkButton(
            export_frame,
            text="Export JSON",
            command=self._export_json,
            width=100,
            height=32
        ).pack(side="right", padx=6)
        
        ctk.CTkButton(
            export_frame,
            text="Export Excel",
            command=self._export_excel,
            width=100,
            height=32
        ).pack(side="right", padx=6)

    def _create_filters(self):
        """Create filters"""
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        
        ctk.CTkLabel(filter_frame, text="Filter by Job:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        
        self.job_var = ctk.StringVar(value="all")
        self.job_var.trace("w", self._on_job_change)
        
        self.job_combo = ctk.CTkComboBox(
            filter_frame,
            values=self._get_job_options(),
            variable=self.job_var,
            width=180
        )
        self.job_combo.pack(side="left", padx=8)
        
        ctk.CTkLabel(filter_frame, text="Search:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(16, 8))
        
        self.search_entry = ctk.CTkEntry(filter_frame, width=180, height=32)
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        self.filter_summary = ctk.CTkLabel(
            filter_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        self.filter_summary.pack(side="right", padx=16)
        
        ctk.CTkButton(
            filter_frame,
            text="Refresh",
            command=self._load_results,
            width=80,
            height=32
        ).pack(side="right", padx=8)
    
    def _create_results_table(self):
        """Create results table"""
        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.table = ctk.CTkScrollableFrame(table_frame, label_text="Data", padx=4, pady=4)
        self.table.grid(row=0, column=0, sticky="nsew")

        self.count_label = ctk.CTkLabel(
            table_frame,
            text="0 items",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        self.count_label.grid(row=1, column=0, pady=8)

        pagination_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        pagination_frame.grid(row=2, column=0, pady=8)

        self.prev_button = ctk.CTkButton(
            pagination_frame,
            text="Previous",
            command=self._prev_page,
            width=80,
            height=30
        )
        self.prev_button.pack(side="left", padx=4)

        self.page_label = ctk.CTkLabel(
            pagination_frame,
            text="Page 1 of 1",
            font=ctk.CTkFont(size=12)
        )
        self.page_label.pack(side="left", padx=16)

        self.next_button = ctk.CTkButton(
            pagination_frame,
            text="Next",
            command=self._next_page,
            width=80,
            height=30
        )
        self.next_button.pack(side="left", padx=4)
    
    def _get_job_options(self):
        """Get job filter options"""
        jobs = db.get_all_jobs()
        self._job_lookup = {}
        options = ["all"]
        for job in jobs:
            label = f"{job.name} ({job.id[:8]})"
            self._job_lookup[label] = job.id
            options.append(label)
        return options
    
    def _load_results(self):
        """Load results"""
        selected = self.job_var.get()
        if selected == "all":
            self.items = db.get_all_items()
        else:
            job_id = self._job_lookup.get(selected)
            self.items = db.get_items_by_job(job_id) if job_id else []
        self.current_page = 0
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply filters to items"""
        filtered = self.items

        # Search filter
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            filtered = [item for item in filtered if search_text in json.dumps(item.data).lower()]

        self.filtered_items = filtered
        self.current_page = 0
        active_job = self.job_var.get()
        self.filter_summary.configure(
            text=f"Active: {active_job} | Matched: {len(self.filtered_items)}"
        )
        self._update_pagination()
        self._display_page()

    def _on_job_change(self, *args):
        """Handle job filter change"""
        self._load_results()
    
    def _on_search(self, event):
        """Handle search input"""
        self._apply_filters()

    def _update_table(self):
        """Compatibility helper for refreshing the current page."""
        self._update_pagination()
        self._display_page()

    def _create_item_row(self, item: ScrapedItem, idx: int):
        """Create item row"""
        row = ctk.CTkFrame(self.table, fg_color=("gray85", "gray17") if idx % 2 else "transparent")
        row.pack(fill="x", pady=2, padx=4)
        
        job = db.get_job(item.job_id)
        job_name = job.name if job else "Unknown"
        
        id_label = ctk.CTkLabel(
            row,
            text=item.id[:8] + "...",
            font=ctk.CTkFont(size=10),
            width=70
        )
        id_label.pack(side="left", padx=4, pady=8)
        
        job_label = ctk.CTkLabel(
            row,
            text=job_name,
            font=ctk.CTkFont(size=10),
            width=90
        )
        job_label.pack(side="left", padx=4, pady=8)
        
        date_str = item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
        date_label = ctk.CTkLabel(
            row,
            text=date_str,
            font=ctk.CTkFont(size=10),
            width=100
        )
        date_label.pack(side="left", padx=4, pady=8)
        
        data_preview = json.dumps(item.data)[:50] + "..." if len(json.dumps(item.data)) > 50 else json.dumps(item.data)
        
        data_label = ctk.CTkLabel(
            row,
            text=data_preview,
            font=ctk.CTkFont(size=10),
            anchor="w"
        )
        data_label.pack(side="left", padx=4, pady=8, fill="x", expand=True)

        action_frame = ctk.CTkFrame(row, fg_color="transparent")
        action_frame.pack(side="right", padx=4)

        ctk.CTkButton(
            action_frame,
            text="View",
            command=lambda i=item: self._view_item(i),
            width=54,
            height=24
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            action_frame,
            text="Copy",
            command=lambda i=item: self._copy_item(i),
            width=54,
            height=24
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            action_frame,
            text="Open",
            command=lambda i=item: self._open_item_url(i),
            width=54,
            height=24
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            action_frame,
            text="Delete",
            command=lambda i=item: self._delete_item(i),
            width=60,
            height=24,
            fg_color=("#b91c1c", "#dc2626")
        ).pack(side="left", padx=2)
    
    def _view_item(self, item: ScrapedItem):
        """View item details"""
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

    def _copy_item(self, item: ScrapedItem):
        """Copy item JSON to the clipboard."""
        data_str = json.dumps(item.data, indent=2, ensure_ascii=False)
        self.clipboard_clear()
        self.clipboard_append(data_str)
        messagebox.showinfo("Copied", "Item JSON copied to clipboard")

    def _open_item_url(self, item: ScrapedItem):
        """Open the scraped URL in a browser."""
        if not item.url:
            messagebox.showwarning("No URL", "This item does not have a URL")
            return
        webbrowser.open(item.url)

    def _delete_item(self, item: ScrapedItem):
        """Delete a single scraped item."""
        if not messagebox.askyesno("Delete Item", "Delete this scraped item?"):
            return

        try:
            if db.delete_item(item.id):
                self._load_results()
                messagebox.showinfo("Deleted", "Item deleted successfully")
            else:
                messagebox.showwarning("Not Found", "Item was not found")
        except Exception as e:
            logger.error(f"Failed to delete item {item.id}: {e}")
            messagebox.showerror("Error", f"Failed to delete item:\n{e}")
    
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

    def _update_pagination(self):
        """Update pagination controls"""
        total_pages = max(1, (len(self.filtered_items) + self.page_size - 1) // self.page_size)
        self.page_label.configure(text=f"Page {self.current_page + 1} of {total_pages}")
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")

    def _display_page(self):
        """Display current page of results"""
        for widget in self.table.winfo_children():
            widget.destroy()

        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_items = self.filtered_items[start_idx:end_idx]

        self.count_label.configure(text=f"{len(self.filtered_items)} items (showing {len(page_items)})")

        if not page_items:
            empty_frame = ctk.CTkFrame(self.table, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=60)
            
            ctk.CTkLabel(
                empty_frame,
                text="📭",
                font=ctk.CTkFont(size=40)
            ).pack(pady=(0, 12))
            
            ctk.CTkLabel(
                empty_frame,
                text="No results found",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(pady=(0, 4))
            
            ctk.CTkLabel(
                empty_frame,
                text="Run a job to see scraped data here",
                font=ctk.CTkFont(size=12),
                text_color=("gray50", "gray60"),
            ).pack()
            return

        for i, item in enumerate(page_items):
            self._create_item_row(item, i)

    def _prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_pagination()
            self._display_page()

    def _next_page(self):
        """Go to next page"""
        total_pages = max(1, (len(self.filtered_items) + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._update_pagination()
            self._display_page()
