"""
Main window for ScrapMaster Desktop
"""

import os
import sys
import customtkinter as ctk
from typing import Optional, Callable

from app.utils.logger import get_logger

logger = get_logger()

class MainWindow(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("ScrapMaster Desktop")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # State
        self.current_view = "dashboard"
        self._sidebar_frame = None
        self._content_frame = None
        
        # Create UI
        self._create_sidebar()
        self._create_content_area()
        
        # Show dashboard by default
        self.show_dashboard()
        
        logger.info("Main window initialized")
    
    def _create_sidebar(self):
        """Create sidebar navigation"""
        self._sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self._sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self._sidebar_frame.grid_rowconfigure(8, weight=1)
        
        # Logo/Title
        title_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="ScrapMaster",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="Desktop Web Scraper",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Navigation buttons
        nav_items = [
            ("dashboard", "🏠", "Dashboard"),
            ("new_job", "➕", "New Job"),
            ("my_jobs", "📋", "My Jobs"),
            ("results", "📊", "Results"),
            ("templates", "📄", "Templates"),
            ("sources", "🌐", "Sources"),
            ("ai_chat", "🤖", "AI Chat"),
            ("settings", "⚙️", "Settings"),
        ]
        
        self.nav_buttons = {}
        
        for idx, (view_id, icon, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self._sidebar_frame,
                text=f"  {icon} {label}",
                command=lambda v=view_id: self.navigate_to(v),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                height=45
            )
            btn.grid(row=2 + idx, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[view_id] = btn
        
        # Theme toggle at bottom
        self.theme_toggle = ctk.CTkSwitch(
            self._sidebar_frame,
            text="Dark Mode",
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light"
        )
        self.theme_toggle.grid(row=8, column=0, padx=20, pady=20, sticky="s")
        self.theme_toggle.select()
        
        # Version info
        version_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="v1.0.0",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        version_label.grid(row=9, column=0, padx=20, pady=(0, 10))
    
    def _create_content_area(self):
        """Create main content area"""
        self._content_frame = ctk.CTkFrame(self, corner_radius=0)
        self._content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._content_frame.grid_rowconfigure(0, weight=1)
        self._content_frame.grid_columnconfigure(0, weight=1)
    
    def navigate_to(self, view: str):
        """Navigate to a view"""
        self.current_view = view
        
        # Update button states
        for view_id, btn in self.nav_buttons.items():
            if view_id == view:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")
        
        # Show appropriate view
        if view == "dashboard":
            self.show_dashboard()
        elif view == "new_job":
            self.show_new_job()
        elif view == "my_jobs":
            self.show_my_jobs()
        elif view == "results":
            self.show_results()
        elif view == "templates":
            self.show_templates()
        elif view == "sources":
            self.show_sources()
        elif view == "ai_chat":
            self.show_ai_chat()
        elif view == "settings":
            self.show_settings()
    
    def show_dashboard(self):
        """Show dashboard view"""
        from app.gui.dashboard import DashboardView
        self._clear_content()
        DashboardView(self._content_frame).pack(fill="both", expand=True)
    
    def show_new_job(self):
        """Show new job view"""
        from app.gui.job_form import JobFormView
        self._clear_content()
        JobFormView(self._content_frame).pack(fill="both", expand=True)
    
    def show_my_jobs(self):
        """Show my jobs view"""
        from app.gui.job_list import JobListView
        self._clear_content()
        JobListView(self._content_frame).pack(fill="both", expand=True)
    
    def show_results(self):
        """Show results view"""
        from app.gui.results import ResultsView
        self._clear_content()
        ResultsView(self._content_frame).pack(fill="both", expand=True)
    
    def show_templates(self):
        """Show templates view"""
        from app.gui.templates import TemplatesView
        self._clear_content()
        TemplatesView(self._content_frame).pack(fill="both", expand=True)

    def show_sources(self):
        """Show sources view"""
        from app.gui.sources import SourcesView
        self._clear_content()
        SourcesView(self._content_frame).pack(fill="both", expand=True)

    def show_ai_chat(self):
        """Show AI chat - opens as popup"""
        from app.gui.ai_chat import AIChatPopup
        
        # Open as popup
        AIChatPopup(self)
    
    def show_settings(self):
        """Show settings view"""
        from app.gui.settings import SettingsView
        self._clear_content()
        SettingsView(self._content_frame).pack(fill="both", expand=True)
    
    def _clear_content(self):
        """Clear content area"""
        for widget in self._content_frame.winfo_children():
            widget.destroy()
    
    def _toggle_theme(self):
        """Toggle dark/light theme"""
        if self.theme_toggle.get() == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
    
    def run(self):
        """Run the application"""
        self.mainloop()


def main():
    """Main entry point"""
    try:
        app = MainWindow()
        
        # Create system tray icon
        import pystray
        from PIL import Image
        import threading
        
        def show_window(icon, item):
            app.deiconify()
            app.lift()
            app.focus_force()
        
        def hide_window(icon, item):
            app.withdraw()
        
        def quit_app(icon, item):
            icon.stop()
            app.quit()
        
        # Load icon (use a default if not found)
        try:
            icon_image = Image.open("app/assets/icon.png")
        except:
            # Create a simple icon
            icon_image = Image.new('RGB', (64, 64), color='blue')
        
        menu = pystray.Menu(
            pystray.MenuItem('Show', show_window),
            pystray.MenuItem('Hide', hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', quit_app)
        )
        
        icon = pystray.Icon("ScrapMaster", icon_image, "ScrapMaster Desktop", menu)
        
        # Start tray icon in background thread
        def run_tray():
            icon.run()
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        
        # Minimize to tray on close
        def on_closing():
            app.withdraw()
            return False  # Don't destroy
        
        app.protocol("WM_DELETE_WINDOW", on_closing)
        
        app.run()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()