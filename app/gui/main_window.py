"""
Main window for ScrapMaster Desktop
"""

import sys
import customtkinter as ctk

from app.utils.logger import get_logger

logger = get_logger()


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("ScrapMaster Desktop")
        self.geometry("1440x920")
        self.minsize(1200, 720)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.current_view = "dashboard"
        self._sidebar_frame = None
        self._content_frame = None
        self._header_title = None
        self.nav_buttons = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_content_area()
        self._apply_palette()

        self.show_dashboard()
        self._update_header("dashboard", "Dashboard")

        logger.info("Main window initialized")

    def _apply_palette(self):
        """Apply a cohesive visual palette."""
        self.configure(fg_color=("#f4f6fb", "#0f172a"))
        if self._sidebar_frame:
            self._sidebar_frame.configure(fg_color=("#e9edf7", "#111827"))
        if self._content_frame:
            self._content_frame.configure(fg_color=("#f8fafc", "#0b1220"))

    def _create_sidebar(self):
        """Create sidebar navigation."""
        self._sidebar_frame = ctk.CTkFrame(self, width=270, corner_radius=0)
        self._sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self._sidebar_frame.grid_rowconfigure(12, weight=1)

        title_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="ScrapMaster",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=("#0f172a", "#f8fafc"),
        )
        title_label.grid(row=0, column=0, padx=20, pady=(24, 2), sticky="w")

        subtitle_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="Reliable Desktop Scraping",
            font=ctk.CTkFont(size=12),
            text_color=("#475569", "#94a3b8"),
        )
        subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        nav_items = [
            ("dashboard", "Dashboard"),
            ("new_job", "New Job"),
            ("my_jobs", "My Jobs"),
            ("results", "Results"),
            ("templates", "Templates"),
            ("sources", "Sources"),
            ("ai_chat", "AI Chat"),
            ("settings", "Settings"),
        ]

        for idx, (view_id, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self._sidebar_frame,
                text=label,
                command=lambda v=view_id: self.navigate_to(v),
                fg_color="transparent",
                text_color=("#1e293b", "#e2e8f0"),
                hover_color=("#dbe4f8", "#1f2937"),
                anchor="w",
                corner_radius=10,
                height=42,
                font=ctk.CTkFont(size=14, weight="bold"),
            )
            btn.grid(row=2 + idx, column=0, padx=14, pady=4, sticky="ew")
            self.nav_buttons[view_id] = btn

        self.theme_toggle = ctk.CTkSwitch(
            self._sidebar_frame,
            text="Dark Mode",
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light",
        )
        self.theme_toggle.grid(row=12, column=0, padx=20, pady=(14, 6), sticky="sw")
        self.theme_toggle.select()

        version_label = ctk.CTkLabel(
            self._sidebar_frame,
            text="v1.0.0",
            font=ctk.CTkFont(size=10),
            text_color=("#64748b", "#64748b"),
        )
        version_label.grid(row=13, column=0, padx=20, pady=(0, 14), sticky="sw")

    def _create_content_area(self):
        """Create main content area with a contextual header."""
        wrapper = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        wrapper.grid(row=0, column=1, sticky="nsew")
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(wrapper, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        self._header_title = ctk.CTkLabel(
            header,
            text="Dashboard",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#0f172a", "#f8fafc"),
        )
        self._header_title.pack(side="left", padx=20, pady=14)

        self._content_frame = ctk.CTkFrame(wrapper, corner_radius=0)
        self._content_frame.grid(row=1, column=0, sticky="nsew")
        self._content_frame.grid_rowconfigure(0, weight=1)
        self._content_frame.grid_columnconfigure(0, weight=1)

    def _set_nav_button_state(self, active_view: str):
        for view_id, btn in self.nav_buttons.items():
            if view_id == active_view:
                btn.configure(
                    fg_color=("#c9dafd", "#2563eb"),
                    text_color=("#0b1f44", "#f8fafc"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("#1e293b", "#e2e8f0"),
                )

    def _update_header(self, view_id: str, label: str):
        self.current_view = view_id
        if self._header_title:
            self._header_title.configure(text=label)
        self._set_nav_button_state(view_id)

    def navigate_to(self, view: str):
        """Navigate to a view."""
        routes = {
            "dashboard": ("Dashboard", self.show_dashboard),
            "new_job": ("New Job", self.show_new_job),
            "my_jobs": ("My Jobs", self.show_my_jobs),
            "results": ("Results", self.show_results),
            "templates": ("Templates", self.show_templates),
            "sources": ("Sources", self.show_sources),
            "ai_chat": ("AI Chat", self.show_ai_chat),
            "settings": ("Settings", self.show_settings),
        }

        label, handler = routes.get(view, ("Dashboard", self.show_dashboard))
        self._update_header(view, label)
        handler()

    def show_dashboard(self):
        from app.gui.dashboard import DashboardView
        self._clear_content()
        DashboardView(self._content_frame).pack(fill="both", expand=True)

    def show_new_job(self):
        from app.gui.job_form import JobFormView
        self._clear_content()
        JobFormView(self._content_frame).pack(fill="both", expand=True)

    def show_my_jobs(self):
        from app.gui.job_list import JobListView
        self._clear_content()
        JobListView(self._content_frame).pack(fill="both", expand=True)

    def show_results(self):
        from app.gui.results import ResultsView
        self._clear_content()
        ResultsView(self._content_frame).pack(fill="both", expand=True)

    def show_templates(self):
        from app.gui.templates import TemplatesView
        self._clear_content()
        TemplatesView(self._content_frame).pack(fill="both", expand=True)

    def show_sources(self):
        from app.gui.sources import SourcesView
        self._clear_content()
        SourcesView(self._content_frame).pack(fill="both", expand=True)

    def show_ai_chat(self):
        from app.gui.ai_chat import AIChatPopup
        AIChatPopup(self)

    def show_settings(self):
        from app.gui.settings import SettingsView
        self._clear_content()
        SettingsView(self._content_frame).pack(fill="both", expand=True)

    def _clear_content(self):
        for widget in self._content_frame.winfo_children():
            widget.destroy()

    def _toggle_theme(self):
        if self.theme_toggle.get() == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
        self._apply_palette()

    def run(self):
        self.mainloop()


def main():
    """Main entry point."""
    try:
        app = MainWindow()

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

        try:
            icon_image = Image.open("app/assets/icon.png")
        except Exception:
            icon_image = Image.new("RGB", (64, 64), color="#2563eb")

        menu = pystray.Menu(
            pystray.MenuItem("Show", show_window),
            pystray.MenuItem("Hide", hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        )

        icon = pystray.Icon("ScrapMaster", icon_image, "ScrapMaster Desktop", menu)

        def run_tray():
            icon.run()

        threading.Thread(target=run_tray, daemon=True).start()

        def on_closing():
            app.withdraw()
            return False

        app.protocol("WM_DELETE_WINDOW", on_closing)
        app.run()

    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
