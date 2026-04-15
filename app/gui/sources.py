"""
Sources view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import json

from app.database.models import WebScrapingSource
from app.database import db
from app.utils.logger import get_logger

logger = get_logger()

class SourcesView(ctk.CTkFrame):
    """Sources view for managing web scraping sources"""

    def __init__(self, parent):
        super().__init__(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create UI
        self._create_sources()

        logger.debug("Sources view created")

    def _create_sources(self):
        """Create sources UI"""
        scrollable = ctk.CTkScrollableFrame(self, label_text="Web Scraping Sources")
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        # Header with add button
        header_frame = ctk.CTkFrame(scrollable)
        header_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_frame,
            text="Manage Web Scraping Sources",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", pady=10, padx=20)

        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Source",
            command=self._open_source_dialog
        )
        add_btn.pack(side="right", pady=10, padx=20)

        # Load and display sources
        self._load_sources(scrollable)

    def _load_sources(self, parent):
        """Load and display sources"""
        # Clear existing
        for widget in parent.winfo_children():
            widget.destroy()

        try:
            sources = db.get_all_sources()
        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
            messagebox.showerror("Error", f"Failed to load sources:\n{str(e)}")
            sources = []

        if not sources:
            empty_label = ctk.CTkLabel(
                parent,
                text="No sources configured yet.\nClick 'Add Source' to create your first source.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=40)
            return

        for source in sources:
            self._create_source_row(parent, source)

    def _create_source_row(self, parent, source: WebScrapingSource):
        """Create a row for a source"""
        row_frame = ctk.CTkFrame(parent)
        row_frame.pack(fill="x", pady=5)

        # Source info
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=20, pady=15)

        name_label = ctk.CTkLabel(
            info_frame,
            text=source.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x")

        url_label = ctk.CTkLabel(
            info_frame,
            text=source.url,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        url_label.pack(fill="x")

        desc_label = ctk.CTkLabel(
            info_frame,
            text=source.description or "No description",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        desc_label.pack(fill="x")

        # Controls
        controls_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=20, pady=15)

        # Enabled toggle
        enabled_var = ctk.BooleanVar(value=source.enabled)
        enabled_switch = ctk.CTkSwitch(
            controls_frame,
            text="Enabled",
            variable=enabled_var,
            command=lambda: self._toggle_source_enabled(source, enabled_var)
        )
        enabled_switch.pack(pady=5)

        # Edit button
        edit_btn = ctk.CTkButton(
            controls_frame,
            text="Edit",
            width=80,
            command=lambda: self._open_source_dialog(source)
        )
        edit_btn.pack(pady=5)

        # Delete button
        delete_btn = ctk.CTkButton(
            controls_frame,
            text="Delete",
            width=80,
            fg_color="red",
            command=lambda: self._delete_source(source)
        )
        delete_btn.pack(pady=5)

    def _toggle_source_enabled(self, source: WebScrapingSource, enabled_var):
        """Toggle source enabled status"""
        try:
            source.enabled = enabled_var.get()
            db.update_source(source)
            logger.info(f"Source {source.name} {'enabled' if source.enabled else 'disabled'}")
        except Exception as e:
            logger.error(f"Failed to update source: {e}")
            messagebox.showerror("Error", f"Failed to update source:\n{str(e)}")
            enabled_var.set(not enabled_var.get())  # Revert

    def _delete_source(self, source: WebScrapingSource):
        """Delete a source"""
        if messagebox.askyesno("Delete Source", f"Delete source '{source.name}'?"):
            try:
                db.delete_source(source.id)
                self._create_sources()  # Refresh
                messagebox.showinfo("Success", "Source deleted!")
                logger.info(f"Deleted source: {source.name}")
            except Exception as e:
                logger.error(f"Failed to delete source: {e}")
                messagebox.showerror("Error", f"Failed to delete source:\n{str(e)}")

    def _open_source_dialog(self, source: WebScrapingSource = None):
        """Open source edit dialog"""
        dialog = SourceDialog(self, source)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.saved:
            self._create_sources()  # Refresh

class SourceDialog(ctk.CTkToplevel):
    """Dialog for editing sources"""

    def __init__(self, parent, source: WebScrapingSource = None):
        super().__init__(parent)

        self.source = source
        self.saved = False

        self.title("Add Source" if source is None else f"Edit {source.name}")
        self.geometry("800x600")
        self.resizable(False, False)
        self.attributes('-topmost', True)
        self.lift()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create form
        self._create_form()

    def _create_form(self):
        """Create the form"""
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)

        # Basic info
        basic_frame = ctk.CTkFrame(scrollable)
        basic_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            basic_frame,
            text="Basic Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")

        # Name
        ctk.CTkLabel(basic_frame, text="Name:").pack(anchor="w", padx=20)
        self.name_entry = ctk.CTkEntry(basic_frame)
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))

        # URL
        ctk.CTkLabel(basic_frame, text="URL:").pack(anchor="w", padx=20)
        self.url_entry = ctk.CTkEntry(basic_frame)
        self.url_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Description
        ctk.CTkLabel(basic_frame, text="Description:").pack(anchor="w", padx=20)
        self.desc_entry = ctk.CTkEntry(basic_frame)
        self.desc_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Category
        ctk.CTkLabel(basic_frame, text="Category:").pack(anchor="w", padx=20)
        self.category_entry = ctk.CTkEntry(basic_frame)
        self.category_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Config - simplified, just load from file or paste JSON
        config_frame = ctk.CTkFrame(scrollable)
        config_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            config_frame,
            text="Job Configuration (JSON)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")

        self.config_text = ctk.CTkTextbox(config_frame, height=200)
        self.config_text.pack(fill="x", padx=20, pady=(0, 10))

        # Load from file button
        load_btn = ctk.CTkButton(
            config_frame,
            text="Load from File",
            command=self._load_config_from_file
        )
        load_btn.pack(pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(scrollable)
        btn_frame.pack(fill="x", pady=20)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            command=self._save
        )
        save_btn.pack(side="right", padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=10)

        # Load existing data
        if self.source:
            self.name_entry.insert(0, self.source.name)
            self.url_entry.insert(0, self.source.url)
            self.desc_entry.insert(0, self.source.description or "")
            self.category_entry.insert(0, self.source.category)
            self.config_text.insert("1.0", json.dumps(self.source.config.model_dump(), indent=2))

    def _load_config_from_file(self):
        """Load config from JSON file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.config_text.delete("1.0", "end")
                self.config_text.insert("1.0", json.dumps(config, indent=2))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load config:\n{str(e)}")

    def _save(self):
        """Save the source"""
        try:
            from app.database.models import JobConfig

            name = self.name_entry.get().strip()
            url = self.url_entry.get().strip()
            desc = self.desc_entry.get().strip()
            category = self.category_entry.get().strip()
            config_json = self.config_text.get("1.0", "end").strip()

            if not name or not url:
                messagebox.showerror("Error", "Name and URL are required")
                return

            try:
                config = JobConfig.model_validate_json(config_json)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid job configuration JSON: {str(e)}")
                return

            if self.source:
                # Update
                self.source.name = name
                self.source.url = url
                self.source.description = desc
                self.source.category = category
                self.source.config = config
                db.update_source(self.source)
            else:
                # Create
                from app.utils.helpers import generate_unique_id
                import datetime
                new_source = WebScrapingSource(
                    id=generate_unique_id(),
                    name=name,
                    url=url,
                    description=desc,
                    category=category,
                    config=config,
                    enabled=True,
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now()
                )
                db.create_source(new_source)

            self.saved = True
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save source:\n{str(e)}")
            logger.error(f"Save source error: {e}")