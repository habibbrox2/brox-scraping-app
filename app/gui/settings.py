"""
Settings view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os

from app.database.models import Settings, WebScrapingSource
from app.database import db
from app.utils.logger import get_logger

logger = get_logger()

class SettingsView(ctk.CTkFrame):
    """Settings view"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Load settings
        self.settings = db.get_settings()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create UI
        self._create_settings()
        
        logger.debug("Settings view created")
    
    def _create_settings(self):
        """Create settings UI"""
        scrollable = ctk.CTkScrollableFrame(self, label_text="Settings")
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)
        
        # General settings
        general_frame = ctk.CTkFrame(scrollable)
        general_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            general_frame,
            text="General Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Max concurrent jobs
        self.concurrent_entry = self._create_input_field(
            general_frame,
            "Max Concurrent Jobs:",
            str(self.settings.max_concurrent_jobs)
        )
        
        # Auto update check
        self.auto_update_var = ctk.BooleanVar(value=self.settings.auto_update_check)
        ctk.CTkCheckBox(
            general_frame,
            text="Check for updates on startup",
            variable=self.auto_update_var
        ).pack(pady=10, padx=20, anchor="w")
        
        # Dark mode
        self.dark_mode_var = ctk.BooleanVar(value=self.settings.dark_mode)
        ctk.CTkCheckBox(
            general_frame,
            text="Dark Mode",
            variable=self.dark_mode_var,
            command=self._toggle_theme
        ).pack(pady=10, padx=20, anchor="w")
        
        # Browser settings
        browser_frame = ctk.CTkFrame(scrollable)
        browser_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            browser_frame,
            text="Browser Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Default headless
        self.headless_var = ctk.BooleanVar(value=self.settings.default_headless)
        ctk.CTkCheckBox(
            browser_frame,
            text="Default Headless Mode",
            variable=self.headless_var
        ).pack(pady=10, padx=20, anchor="w")
        
        # Default delay
        self.delay_entry = self._create_input_field(
            browser_frame,
            "Default Delay (ms):",
            str(self.settings.default_delay_ms)
        )
        
        # Default User-Agent
        self.ua_entry = self._create_input_field(
            browser_frame,
            "Default User-Agent:",
            self.settings.default_user_agent or ""
        )
        
        # Data storage settings
        storage_frame = ctk.CTkFrame(scrollable)
        storage_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            storage_frame,
            text="Data Storage",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Storage path
        path_frame = ctk.CTkFrame(storage_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=20)
        
        ctk.CTkLabel(
            path_frame,
            text="Data Storage Path:",
            width=150,
            anchor="w"
        ).pack(side="left", pady=10)
        
        self.path_entry = ctk.CTkEntry(path_frame)
        self.path_entry.insert(0, self.settings.data_storage_path)
        self.path_entry.pack(side="left", fill="x", expand=True, pady=10)
        
        ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self._browse_path,
            width=80
        ).pack(side="right", padx=10)
        
        # Logging settings
        log_frame = ctk.CTkFrame(scrollable)
        log_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            log_frame,
            text="Logging",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        self.log_level_var = ctk.StringVar(value=self.settings.log_level)
        log_combo = ctk.CTkComboBox(
            log_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self.log_level_var
        )
        log_combo.pack(pady=10, padx=20, anchor="w")
        
        # Web Scraping Sources
        sources_frame = ctk.CTkFrame(scrollable)
        sources_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            sources_frame,
            text="Web Scraping Sources",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Sources list
        self.sources_list = ctk.CTkScrollableFrame(sources_frame, height=200)
        self.sources_list.pack(fill="x", padx=20, pady=10)
        
        # Load sources
        self._load_sources()
        
        # Add source button
        ctk.CTkButton(
            sources_frame,
            text="➕ Add Source",
            command=self._add_source
        ).pack(pady=10, padx=20, anchor="w")
        
        # Save button
        button_frame = ctk.CTkFrame(scrollable)
        button_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="Save Settings",
            command=self._save_settings,
            width=200,
            height=40
        ).pack(pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_settings,
            width=200,
            height=35,
            fg_color="gray"
        ).pack(pady=10)
    
    def _create_input_field(self, parent, label: str, default: str = "") -> ctk.CTkEntry:
        """Create input field"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=20)
        
        ctk.CTkLabel(
            frame,
            text=label,
            width=150,
            anchor="w"
        ).pack(side="left", pady=10)
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, default)
        entry.pack(side="right", fill="x", expand=True, pady=10)
        
        return entry
    
    def _toggle_theme(self):
        """Toggle theme"""
        import customtkinter as ctk
        if self.dark_mode_var.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
    
    def _browse_path(self):
        """Browse for storage path"""
        path = filedialog.askdirectory(title="Select Data Storage Path")
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
    
    def _save_settings(self):
        """Save settings"""
        try:
            settings = Settings(
                max_concurrent_jobs=int(self.concurrent_entry.get() or "3"),
                default_headless=self.headless_var.get(),
                default_delay_ms=int(self.delay_entry.get() or "1000"),
                data_storage_path=self.path_entry.get(),
                auto_update_check=self.auto_update_var.get(),
                dark_mode=self.dark_mode_var.get(),
                log_level=self.log_level_var.get(),
                default_user_agent=self.ua_entry.get() or None
            )
            
            db.save_settings(settings)
            
            messagebox.showinfo("Success", "Settings saved!")
            logger.info("Settings saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            logger.error(f"Save settings error: {e}")
    
    def _reset_settings(self):
        """Reset to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.settings = Settings()
            db.save_settings(self.settings)
            
            # Refresh UI
            messagebox.showinfo("Success", "Settings reset to defaults!")
            self._create_settings()
    
    def _load_sources(self):
        """Load sources into the list"""
        # Clear current
        for widget in self.sources_list.winfo_children():
            widget.destroy()
        
        sources = db.get_all_sources()
        
        if not sources:
            empty_label = ctk.CTkLabel(
                self.sources_list,
                text="No sources yet. Add your first scraping source!",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            empty_label.pack(pady=20)
            return
        
        for source in sources:
            self._create_source_row(source)
    
    def _create_source_row(self, source: WebScrapingSource):
        """Create source row"""
        row = ctk.CTkFrame(self.sources_list)
        row.pack(fill="x", pady=2)
        
        # Name
        name_label = ctk.CTkLabel(
            row,
            text=source.name,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        name_label.pack(side="left", padx=10, pady=5)
        
        # URL
        url_label = ctk.CTkLabel(
            row,
            text=source.url,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        url_label.pack(side="left", padx=10, pady=5)
        
        # Enabled
        enabled_var = ctk.BooleanVar(value=source.enabled)
        enabled_cb = ctk.CTkCheckBox(
            row,
            text="",
            variable=enabled_var,
            command=lambda s=source, v=enabled_var: self._toggle_source_enabled(s, v)
        )
        enabled_cb.pack(side="right", padx=10)
        
        # Edit
        ctk.CTkButton(
            row,
            text="✏",
            width=30,
            height=25,
            command=lambda s=source: self._edit_source(s)
        ).pack(side="right", padx=5)
        
        # Delete
        ctk.CTkButton(
            row,
            text="🗑",
            width=30,
            height=25,
            fg_color="#c0392b",
            command=lambda s=source: self._delete_source(s)
        ).pack(side="right", padx=5)
    
    def _add_source(self):
        """Add new source"""
        self._open_source_dialog()
    
    def _edit_source(self, source: WebScrapingSource):
        """Edit source"""
        self._open_source_dialog(source)
    
    def _delete_source(self, source: WebScrapingSource):
        """Delete source"""
        if messagebox.askyesno("Delete Source", f"Delete source '{source.name}'?"):
            db.delete_source(source.id)
            self._load_sources()
            messagebox.showinfo("Success", "Source deleted!")
    
    def _toggle_source_enabled(self, source: WebScrapingSource, enabled_var):
        """Toggle source enabled"""
        source.enabled = enabled_var.get()
        source.updated_at = datetime.now()
        db.update_source(source)
    
    def _open_source_dialog(self, source: WebScrapingSource = None):
        """Open source edit dialog"""
        # Simple dialog for source editing
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Source" if source else "Add Source")
        dialog.geometry("600x700")
        
        # Create scrollable frame
        scrollable = ctk.CTkScrollableFrame(dialog)
        scrollable.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Basic Information
        basic_frame = ctk.CTkFrame(scrollable)
        basic_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            basic_frame,
            text="Basic Information",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # Name
        ctk.CTkLabel(basic_frame, text="Name:").pack(pady=5, anchor="w")
        name_entry = ctk.CTkEntry(basic_frame)
        name_entry.pack(fill="x", padx=20)
        if source:
            name_entry.insert(0, source.name)
        
        # URL
        ctk.CTkLabel(basic_frame, text="URL:").pack(pady=5, anchor="w")
        url_entry = ctk.CTkEntry(basic_frame)
        url_entry.pack(fill="x", padx=20)
        if source:
            url_entry.insert(0, source.url)
        
        # Description
        ctk.CTkLabel(basic_frame, text="Description:").pack(pady=5, anchor="w")
        desc_entry = ctk.CTkEntry(basic_frame)
        desc_entry.pack(fill="x", padx=20)
        if source:
            desc_entry.insert(0, source.description or "")
        
        # Category
        ctk.CTkLabel(basic_frame, text="Category:").pack(pady=5, anchor="w")
        category_entry = ctk.CTkEntry(basic_frame)
        category_entry.pack(fill="x", padx=20)
        if source:
            category_entry.insert(0, source.category)
        
        # API Configuration
        api_frame = ctk.CTkFrame(scrollable)
        api_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            api_frame,
            text="API Endpoint Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=20, anchor="w")
        
        # API Enabled
        api_enabled_var = ctk.BooleanVar(value=source.config.api.enabled if source else False)
        ctk.CTkCheckBox(
            api_frame,
            text="Enable API Posting",
            variable=api_enabled_var
        ).pack(pady=10, padx=20, anchor="w")
        
        # API URL
        ctk.CTkLabel(api_frame, text="API Endpoint URL:").pack(pady=5, anchor="w")
        api_url_entry = ctk.CTkEntry(api_frame)
        api_url_entry.pack(fill="x", padx=20)
        if source and source.config.api.url:
            api_url_entry.insert(0, source.config.api.url)
        
        # HTTP Method
        ctk.CTkLabel(api_frame, text="HTTP Method:").pack(pady=5, anchor="w")
        method_var = ctk.StringVar(value=source.config.api.method if source else "POST")
        method_combo = ctk.CTkComboBox(
            api_frame,
            values=["GET", "POST", "PUT", "PATCH"],
            variable=method_var
        )
        method_combo.pack(fill="x", padx=20)
        
        # Authentication Type
        ctk.CTkLabel(api_frame, text="Authentication Type:").pack(pady=5, anchor="w")
        auth_var = ctk.StringVar(value=source.config.api.auth_type if source else "none")
        auth_combo = ctk.CTkComboBox(
            api_frame,
            values=["none", "bearer", "basic", "api_key"],
            variable=auth_var
        )
        auth_combo.pack(fill="x", padx=20)
        
        # Auth Token (for Bearer)
        ctk.CTkLabel(api_frame, text="Bearer Token:").pack(pady=5, anchor="w")
        token_entry = ctk.CTkEntry(api_frame, show="*")
        token_entry.pack(fill="x", padx=20)
        if source and source.config.api.auth_token:
            token_entry.insert(0, source.config.api.auth_token)
        
        # Username (for Basic Auth)
        ctk.CTkLabel(api_frame, text="Username:").pack(pady=5, anchor="w")
        username_entry = ctk.CTkEntry(api_frame)
        username_entry.pack(fill="x", padx=20)
        if source and source.config.api.auth_username:
            username_entry.insert(0, source.config.api.auth_username)
        
        # Password (for Basic Auth)
        ctk.CTkLabel(api_frame, text="Password:").pack(pady=5, anchor="w")
        password_entry = ctk.CTkEntry(api_frame, show="*")
        password_entry.pack(fill="x", padx=20)
        if source and source.config.api.auth_password:
            password_entry.insert(0, source.config.api.auth_password)
        
        # API Key Header
        ctk.CTkLabel(api_frame, text="API Key Header:").pack(pady=5, anchor="w")
        api_key_header_entry = ctk.CTkEntry(api_frame)
        api_key_header_entry.pack(fill="x", padx=20)
        api_key_header_entry.insert(0, source.config.api.api_key_header if source else "X-API-Key")
        
        # Save button
        def save():
            try:
                from app.utils.helpers import generate_unique_id
                from datetime import datetime
                from app.database.models import APIConfig
                
                # Create API config
                api_config = APIConfig(
                    enabled=api_enabled_var.get(),
                    url=api_url_entry.get() if api_url_entry.get() else None,
                    method=method_var.get(),
                    auth_type=auth_var.get(),
                    auth_token=token_entry.get() if token_entry.get() else None,
                    auth_username=username_entry.get() if username_entry.get() else None,
                    auth_password=password_entry.get() if password_entry.get() else None,
                    api_key_header=api_key_header_entry.get()
                )
                
                # Update job config
                job_config = source.config if source else JobConfig(url=url_entry.get())
                job_config.api = api_config
                
                new_source = WebScrapingSource(
                    id=source.id if source else generate_unique_id(),
                    name=name_entry.get(),
                    url=url_entry.get(),
                    description=desc_entry.get() or None,
                    category=category_entry.get() or "general",
                    config=job_config,
                    enabled=source.enabled if source else True,
                    created_at=source.created_at if source else datetime.now(),
                    updated_at=datetime.now()
                )
                
                if source:
                    db.update_source(new_source)
                else:
                    db.create_source(new_source)
                
                self._load_sources()
                dialog.destroy()
                messagebox.showinfo("Success", "Source saved!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save source: {e}")
        
        ctk.CTkButton(scrollable, text="Save", command=save).pack(pady=20)