"""
Templates view for ScrapMaster Desktop
"""

import customtkinter as ctk
from tkinter import messagebox

from app.database.models import Template, JobConfig, FieldConfig, Job, JobStatus
from app.database import db
from app.utils.helpers import generate_unique_id
from app.utils.logger import get_logger

logger = get_logger()

class TemplatesView(ctk.CTkFrame):
    """Templates view for built-in templates"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Create header
        self._create_header()
        
        # Create template list
        self._create_template_list()
        
        # Load templates
        self._load_templates()
        
        logger.debug("Templates view created")
    
    def _create_header(self):
        """Create header"""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Built-in Templates",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left", padx=20)
        
        ctk.CTkButton(
            header_frame,
            text="🔄 Refresh",
            command=self._load_templates
        ).pack(side="right", padx=20)
    
    def _create_template_list(self):
        """Create template list"""
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Templates")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
    
    def _load_templates(self):
        """Load templates"""
        # Clear current list
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        # Get templates
        templates = db.get_all_templates()
        
        if not templates:
            # Create default templates
            self._create_default_templates()
            templates = db.get_all_templates()
        
        # Create template cards
        for template in templates:
            self._create_template_card(template)
    
    def _create_template_card(self, template: Template):
        """Create template card"""
        card = ctk.CTkFrame(self.list_frame)
        card.pack(fill="x", pady=5)
        
        # Icon
        icon_label = ctk.CTkLabel(
            card,
            text=template.icon,
            font=ctk.CTkFont(size=30)
        )
        icon_label.pack(side="left", padx=20, pady=20)
        
        # Info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=10)
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=template.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(fill="x")
        
        desc_label = ctk.CTkLabel(
            info_frame,
            text=template.description,
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        desc_label.pack(fill="x")
        
        category_label = ctk.CTkLabel(
            info_frame,
            text=f"Category: {template.category}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        category_label.pack(fill="x")
        
        # Use button
        ctk.CTkButton(
            card,
            text="Use Template",
            command=lambda t=template: self._use_template(t),
            width=120,
            height=35
        ).pack(side="right", padx=20)
    
    def _use_template(self, template: Template):
        """Use template to create job"""
        from app.gui.job_form import JobFormView
        
        # Create job from template
        job = Job(
            id=generate_unique_id(),
            name=f"{template.name} - Copy",
            description=template.description,
            template=template.id,
            config=template.config,
            status=JobStatus.DRAFT
        )
        
        db.create_job(job)
        
        messagebox.showinfo("Success", f"Job created from template '{template.name}'!")
        
        # Navigate to jobs
        self.master.master.navigate_to("my_jobs")
    
    def _create_default_templates(self):
        """Create default templates"""
        default_templates = [
            {
                "id": "amazon_products",
                "name": "Amazon Product Scraper",
                "description": "Scrape product listings from Amazon search results",
                "category": "E-commerce",
                "icon": "🛒",
                "config": {
                    "url": "https://www.amazon.com/s?k=laptops",
                    "fields": [
                        {"name": "title", "selector": "h2", "selector_type": "css", "attribute": "text"},
                        {"name": "price", "selector": ".a-price-whole", "selector_type": "css", "attribute": "text"},
                        {"name": "rating", "selector": ".a-icon-alt", "selector_type": "css", "attribute": "text"},
                        {"name": "reviews", "selector": "[aria-label*='stars']", "selector_type": "css", "attribute": "text"}
                    ],
                    "root_selector": "[data-component-type='s-search-results'] .s-result-item",
                    "pagination": {"enabled": True, "max_pages": 5}
                }
            },
            {
                "id": "books_toscrape",
                "name": "BooksToScrape Demo",
                "description": "Demo scraper for books.toscrape.com - perfect for testing",
                "category": "Demo",
                "icon": "📚",
                "config": {
                    "url": "https://books.toscrape.com/",
                    "fields": [
                        {"name": "title", "selector": "h3 a", "selector_type": "css", "attribute": "title"},
                        {"name": "price", "selector": ".price_color", "selector_type": "css", "attribute": "text"},
                        {"name": "rating", "selector": ".star-rating", "selector_type": "css", "attribute": "class"}
                    ],
                    "root_selector": ".product_pod",
                    "pagination": {"enabled": True, "max_pages": 10}
                }
            },
            {
                "id": "google_shopping",
                "name": "Google Shopping",
                "description": "Scrape product listings from Google Shopping",
                "category": "E-commerce",
                "icon": "🛍️",
                "config": {
                    "url": "https://www.google.com/search?q=headphones&tbm=shop",
                    "fields": [
                        {"name": "title", "selector": "h3", "selector_type": "css", "attribute": "text"},
                        {"name": "price", "selector": ".a8Hoocc", "selector_type": "css", "attribute": "text"},
                        {"name": "store", "selector": ".aXOdab", "selector_type": "css", "attribute": "text"}
                    ],
                    "root_selector": ".sh-DqNVb"
                }
            },
            {
                "id": "news_article",
                "name": "News Article Scraper",
                "description": "Scrape news articles from any news website",
                "category": "News",
                "icon": "📰",
                "config": {
                    "url": "",
                    "fields": [
                        {"name": "title", "selector": "h1", "selector_type": "css", "attribute": "text"},
                        {"name": "author", "selector": "[rel='author']", "selector_type": "css", "attribute": "text"},
                        {"name": "date", "selector": "time", "selector_type": "css", "attribute": "datetime"},
                        {"name": "content", "selector": "article p", "selector_type": "css", "attribute": "text"}
                    ],
                    "root_selector": "article"
                }
            },
            {
                "id": "ecommerce_general",
                "name": "E-commerce General",
                "description": "Generic e-commerce product scraper",
                "category": "E-commerce",
                "icon": "🏪",
                "config": {
                    "url": "",
                    "fields": [
                        {"name": "product_name", "selector": ".product-title", "selector_type": "css", "attribute": "text"},
                        {"name": "price", "selector": ".product-price", "selector_type": "css", "attribute": "text"},
                        {"name": "image", "selector": "img", "selector_type": "css", "attribute": "src"},
                        {"name": "description", "selector": ".product-description", "selector_type": "css", "attribute": "text"}
                    ],
                    "root_selector": ".product-item"
                }
            },
            {
                "id": "linkedin_public",
                "name": "LinkedIn Profile (Public)",
                "description": "Scrape public LinkedIn profile information",
                "category": "Social",
                "icon": "💼",
                "config": {
                    "url": "",
                    "fields": [
                        {"name": "name", "selector": "h1", "selector_type": "css", "attribute": "text"},
                        {"name": "headline", "selector": ".headline", "selector_type": "css", "attribute": "text"},
                        {"name": "about", "selector": "#about + div", "selector_type": "css", "attribute": "text"}
                    ],
                    "root_selector": ".profile-detail"
                }
            }
        ]
        
        for t in default_templates:
            try:
                config = JobConfig.model_validate(t["config"])
                template = Template(
                    id=t["id"],
                    name=t["name"],
                    description=t["description"],
                    category=t["category"],
                    config=config,
                    icon=t["icon"]
                )
                db.create_template(template)
                logger.info(f"Created default template: {t['name']}")
            except Exception as e:
                logger.error(f"Error creating template {t['name']}: {e}")