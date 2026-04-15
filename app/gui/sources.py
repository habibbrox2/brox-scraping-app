"""
Sources view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import json
import re
import threading
from datetime import datetime

import keyring
import requests
from bs4 import BeautifulSoup

from app.database.models import WebScrapingSource, FieldConfig, JobConfig, Job, JobStatus
from app.database import db
from app.scraper.scraper_engine import scraper_engine
from app.utils.helpers import generate_unique_id
from app.utils.logger import get_logger

logger = get_logger()

OPENROUTER_MODEL = "google/gemini-flash-1.5"


def _get_openrouter_api_key() -> str:
    """Get the OpenRouter API key from keyring or environment."""
    return keyring.get_password("scrapmaster", "openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_html_snapshot(html: str) -> dict:
    """Build a compact page snapshot for selector suggestions."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    meta_desc = ""
    meta = soup.select_one("meta[name='description']")
    if meta and meta.get("content"):
        meta_desc = _clean_text(meta.get("content", ""))

    headings = []
    for selector in ("h1", "h2", "h3"):
        for node in soup.select(selector)[:10]:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                headings.append({"tag": selector, "text": text})

    links = []
    for node in soup.select("a[href]")[:20]:
        text = _clean_text(node.get_text(" ", strip=True))
        href = node.get("href") or ""
        if text or href:
            links.append({"text": text, "href": href})

    body_html = ""
    if soup.body:
        body_html = str(soup.body)
    else:
        body_html = str(soup)
    body_html = body_html[:14000]

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "links": links,
        "html": body_html,
    }


def _build_fallback_selector_config(source_url: str) -> JobConfig:
    """Build a safe fallback config for a source."""
    return JobConfig(
        url=source_url,
        fields=[
            FieldConfig(name="title", selector="h1", selector_type="css", attribute="text"),
            FieldConfig(name="summary", selector="p", selector_type="css", attribute="text"),
            FieldConfig(name="link", selector="a", selector_type="css", attribute="href"),
        ],
        root_selector="article, main, body",
    )


def _normalize_source_config_for_save(source_url: str, raw_json: str) -> JobConfig:
    """Normalize editor JSON into a safe, usable source config."""
    raw_json = (raw_json or "").strip()
    if not raw_json:
        return _build_fallback_selector_config(source_url)

    try:
        payload = json.loads(raw_json)
    except Exception:
        return _build_fallback_selector_config(source_url)

    if not isinstance(payload, dict):
        return _build_fallback_selector_config(source_url)

    if not payload.get("url"):
        payload["url"] = source_url

    if not payload.get("fields"):
        payload["fields"] = [field.model_dump() for field in _build_fallback_selector_config(source_url).fields]

    try:
        return JobConfig.model_validate(payload)
    except Exception:
        return _build_fallback_selector_config(source_url)


def _parse_ai_selector_response(content: str, source_url: str) -> JobConfig:
    """Parse AI response into a JobConfig."""
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1).replace("JSON\n", "", 1).strip()

    if not raw.startswith("{"):
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if match:
            raw = match.group(0)

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object")

    root_selector = data.get("root_selector") or data.get("container_selector") or ""
    fields_data = data.get("fields") or []
    normalized_fields = []

    for idx, field in enumerate(fields_data, start=1):
        if not isinstance(field, dict):
            continue

        name = _clean_text(str(field.get("name") or "")) or f"field_{idx}"
        selector = _clean_text(str(field.get("selector") or ""))
        selector_type = str(field.get("selector_type") or "css").lower()
        attribute = field.get("attribute")
        default_value = field.get("default_value")
        transform = field.get("transform")

        if selector_type not in {"css", "xpath"}:
            selector_type = "css"

        try:
            normalized_fields.append(
                FieldConfig(
                    name=name,
                    selector=selector,
                    selector_type=selector_type,
                    attribute=attribute if attribute not in ("", None) else None,
                    default_value=default_value if default_value not in ("", None) else None,
                    transform=transform if transform not in ("", None) else None,
                )
            )
        except Exception as exc:
            logger.debug(f"Skipping invalid AI field suggestion {name}: {exc}")

    if not normalized_fields:
        return _build_fallback_selector_config(source_url)

    if not root_selector:
        root_selector = "article"

    return JobConfig(
        url=source_url,
        fields=normalized_fields,
        root_selector=root_selector,
    )


def _generate_selector_config(source_url: str, api_key: str, source_name: str = "", description: str = "") -> JobConfig:
    """Generate selector suggestions for a source URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    response = requests.get(source_url, headers=headers, timeout=30)
    response.raise_for_status()

    snapshot = _extract_html_snapshot(response.text)
    prompt = (
        "You are a web scraping selector expert.\n"
        "Analyze the provided page snapshot and return ONLY valid JSON.\n"
        "Goal: suggest a root selector and 2-5 field selectors that can extract useful structured data.\n"
        "Rules:\n"
        "- Return a JSON object with keys: root_selector, fields, notes.\n"
        "- fields must be an array of objects with name, selector, selector_type, attribute, default_value, transform.\n"
        "- Use CSS selectors unless XPath is clearly better.\n"
        "- If the page looks like a list, choose the repeating item container as root_selector.\n"
        "- Keep selectors practical and relatively general.\n"
        "- Use attributes like text, href, src only when appropriate.\n"
        "- Do not include markdown fences or explanations outside JSON.\n\n"
        f"Source name: {source_name}\n"
        f"Description: {description}\n"
        f"URL: {source_url}\n\n"
        f"Snapshot:\n{json.dumps(snapshot, indent=2, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You return only JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    ai_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    ai_response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json=payload,
        headers=ai_headers,
        timeout=90
    )
    ai_response.raise_for_status()
    result = ai_response.json()
    content = result["choices"][0]["message"]["content"]
    return _parse_ai_selector_response(content, source_url)

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

        self.batch_btn = ctk.CTkButton(
            header_frame,
            text="Auto Detect All",
            command=self._auto_detect_all_sources
        )
        self.batch_btn.pack(side="right", pady=10, padx=0)

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="Refresh",
            width=90,
            command=lambda: self._load_sources(self.sources_list_frame)
        )
        refresh_btn.pack(side="right", pady=10, padx=(0, 8))

        self.batch_status = ctk.CTkLabel(
            scrollable,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.batch_status.pack(anchor="w", padx=20, pady=(0, 10))

        self.summary_label = ctk.CTkLabel(
            scrollable,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70")
        )
        self.summary_label.pack(anchor="w", padx=20, pady=(0, 6))

        columns = ctk.CTkFrame(scrollable, fg_color="transparent")
        columns.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(columns, text="Source", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="left", padx=12)
        ctk.CTkLabel(columns, text="Status", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="left", padx=12)
        ctk.CTkLabel(columns, text="Actions", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="right", padx=20)

        # Dedicated container for the source rows so refreshing does not destroy the header.
        self.sources_list_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
        self.sources_list_frame.pack(fill="both", expand=True)

        # Load and display sources
        self._load_sources(self.sources_list_frame)

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

        enabled_count = len([s for s in sources if s.enabled])
        configured_count = len([s for s in sources if s.config and s.config.fields])
        self.summary_label.configure(
            text=f"Total: {len(sources)} | Enabled: {enabled_count} | Configured: {configured_count}"
        )

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

        fields_count = len(source.config.fields or [])
        ctk.CTkLabel(
            info_frame,
            text=f"Fields: {fields_count}  |  Root: {source.config.root_selector or 'auto'}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        ).pack(fill="x", pady=(3, 0))

        # Controls
        controls_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        controls_frame.pack(side="right", padx=20, pady=15)

        status_color = "#15803d" if source.enabled else "#6b7280"
        ctk.CTkLabel(
            controls_frame,
            text="ACTIVE" if source.enabled else "PAUSED",
            text_color="white",
            fg_color=status_color,
            corner_radius=6,
            font=ctk.CTkFont(size=10, weight="bold"),
            width=80
        ).pack(pady=(0, 6))

        # Enabled toggle
        enabled_var = ctk.BooleanVar(value=source.enabled)
        enabled_switch = ctk.CTkSwitch(
            controls_frame,
            text="Enabled",
            variable=enabled_var,
            command=lambda: self._toggle_source_enabled(source, enabled_var)
        )
        enabled_switch.pack(pady=5)

        run_btn = ctk.CTkButton(
            controls_frame,
            text="Run Now",
            width=90,
            command=lambda: self._quick_run_source(source)
        )
        run_btn.pack(pady=5)

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

    def _quick_run_source(self, source: WebScrapingSource):
        """Run this source immediately via a temporary job."""
        source_label = source.name.strip() if source.name and source.name.strip() else f"Source {source.id[:8]}"
        temp_job = Job(
            id=generate_unique_id(),
            name=f"Quick Run: {source_label}",
            description=f"Auto-generated from source: {source_label}",
            config=source.config,
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.create_job(temp_job)

        def run_async():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(scraper_engine.run_job(temp_job))
            finally:
                loop.close()

        threading.Thread(target=run_async, daemon=True).start()
        messagebox.showinfo("Quick Run Started", f"Source '{source_label}' is running")

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
                self._load_sources(self.sources_list_frame)
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
            self._load_sources(self.sources_list_frame)  # Refresh

    def _set_batch_state(self, text: str = "", enabled: bool = True):
        """Update batch auto-detect UI state."""
        self.batch_status.configure(text=text)
        self.batch_btn.configure(state="normal" if enabled else "disabled")

    def _auto_detect_all_sources(self):
        """Auto-detect selectors for all sources."""
        api_key = _get_openrouter_api_key()
        if not api_key:
            messagebox.showerror(
                "AI Not Configured",
                "No OpenRouter API key found.\nSet `scrapmaster/openrouter_api_key` in keyring or `OPENROUTER_API_KEY`."
            )
            return

        sources = db.get_all_sources()
        if not sources:
            messagebox.showinfo("No Sources", "There are no sources to update.")
            return

        if not messagebox.askyesno(
            "Auto Detect All Sources",
            "This will fetch each source URL, suggest selectors, and update every source in the database.\nContinue?"
        ):
            return

        self._set_batch_state(f"Queued {len(sources)} sources...", False)
        worker = threading.Thread(
            target=self._auto_detect_all_sources_worker,
            args=(sources, api_key),
            daemon=True
        )
        worker.start()

    def _auto_detect_all_sources_worker(self, sources, api_key: str):
        """Background worker for batch selector detection."""
        updated = 0
        fallback = 0
        failed = 0
        details = []

        for idx, source in enumerate(sources, start=1):
            try:
                self.after(0, lambda i=idx, total=len(sources), name=source.name: self._set_batch_state(
                    f"Processing {i}/{total}: {name}",
                    False
                ))

                config = _generate_selector_config(source.url, api_key, source.name, source.description or "")
                source.config = config
                source.updated_at = datetime.now()
                db.update_source(source)
                updated += 1
                details.append(f"{source.name}: updated")
            except Exception as e:
                logger.warning(f"AI selector detection failed for {source.name}: {e}")
                try:
                    source.config = _build_fallback_selector_config(source.url)
                    source.updated_at = datetime.now()
                    db.update_source(source)
                    fallback += 1
                    details.append(f"{source.name}: fallback")
                except Exception as inner:
                    failed += 1
                    details.append(f"{source.name}: failed ({inner})")

        def finish():
            self._set_batch_state(
                f"Done. Updated: {updated}, Fallback: {fallback}, Failed: {failed}",
                True
            )
            self._load_sources(self.sources_list_frame)
            messagebox.showinfo(
                "Auto Detect Complete",
                f"Updated: {updated}\nFallback applied: {fallback}\nFailed: {failed}\n\n" +
                "\n".join(details[:20])
            )

        self.after(0, finish)

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

        action_row = ctk.CTkFrame(config_frame, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(0, 8))

        self.suggest_btn = ctk.CTkButton(
            action_row,
            text="Suggest Selectors",
            command=self._suggest_selectors
        )
        self.suggest_btn.pack(side="left")

        self.suggest_status = ctk.CTkLabel(
            action_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.suggest_status.pack(side="left", padx=12)

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

    def _set_suggest_state(self, text: str = "", enabled: bool = True):
        """Update the selector suggestion UI state."""
        self.suggest_status.configure(text=text)
        self.suggest_btn.configure(state="normal" if enabled else "disabled")

    def _suggest_selectors(self):
        """Suggest selectors via AI for the current source URL."""
        source_url = self.url_entry.get().strip()
        if not source_url:
            messagebox.showerror("Error", "Please enter a URL first")
            return

        existing_config = self.config_text.get("1.0", "end").strip()
        if existing_config and not messagebox.askyesno(
            "Replace Config?",
            "This will replace the JSON currently shown in the editor with AI suggestions.\nContinue?"
        ):
            return

        api_key = _get_openrouter_api_key()
        if not api_key:
            messagebox.showerror(
                "AI Not Configured",
                "No OpenRouter API key found.\nSet `scrapmaster/openrouter_api_key` in keyring or `OPENROUTER_API_KEY`."
            )
            return

        self._set_suggest_state("Fetching page...", False)

        worker = threading.Thread(
            target=self._suggest_selectors_worker,
            args=(source_url, api_key),
            daemon=True
        )
        worker.start()

    def _suggest_selectors_worker(self, source_url: str, api_key: str):
        """Background worker for AI selector suggestions."""
        try:
            config = _generate_selector_config(source_url, api_key)
            config_json = json.dumps(config.model_dump(), indent=2, ensure_ascii=False)

            def apply():
                self.config_text.delete("1.0", "end")
                self.config_text.insert("1.0", config_json)
                self._set_suggest_state("Selector suggestions applied", True)
                messagebox.showinfo(
                    "AI Suggestions Ready",
                    "Selector suggestions have been inserted into the config editor.\nReview them, then click Save."
                )

            self.after(0, apply)

        except Exception as e:
            logger.error(f"Selector suggestion failed: {e}")

            def fallback():
                self._set_suggest_state("Using fallback preset", True)
                fallback_config = _build_fallback_selector_config(source_url)
                self.config_text.delete("1.0", "end")
                self.config_text.insert("1.0", json.dumps(fallback_config.model_dump(), indent=2, ensure_ascii=False))
                messagebox.showwarning(
                    "AI Unavailable",
                    f"AI selector suggestion failed and a fallback preset was inserted instead.\n\n{e}"
                )

            self.after(0, fallback)
        finally:
            self.after(0, lambda: self._set_suggest_state(enabled=True))

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
            from datetime import datetime as dt

            name = self.name_entry.get().strip()
            url = self.url_entry.get().strip()
            desc = self.desc_entry.get().strip()
            category = self.category_entry.get().strip()
            config_json = self.config_text.get("1.0", "end").strip()

            if not name or not url:
                messagebox.showerror("Error", "Name and URL are required")
                return

            config = _normalize_source_config_for_save(url, config_json)

            if self.source:
                # Update
                self.source.name = name
                self.source.url = url
                self.source.description = desc
                self.source.category = category
                self.source.config = config
                self.source.updated_at = dt.now()
                db.update_source(self.source)
            else:
                # Create
                from app.utils.helpers import generate_unique_id
                new_source = WebScrapingSource(
                    id=generate_unique_id(),
                    name=name,
                    url=url,
                    description=desc,
                    category=category,
                    config=config,
                    enabled=True,
                    created_at=dt.now(),
                    updated_at=dt.now()
                )
                db.create_source(new_source)

            self.saved = True
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save source:\n{str(e)}")
            logger.error(f"Save source error: {e}")
