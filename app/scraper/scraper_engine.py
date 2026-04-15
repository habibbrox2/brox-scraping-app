"""
Scraper engine for ScrapMaster Desktop
"""

import asyncio
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading

import requests
from bs4 import BeautifulSoup
from lxml import html

from app.database.models import Job, JobConfig, FieldConfig, JobStatus, ScrapedItem, JobResult
from app.database import db
from app.utils.helpers import generate_unique_id, clean_text, normalize_url
from app.utils.logger import get_logger

logger = get_logger()

class ScraperEngine:
    """Main scraper engine with Playwright + BeautifulSoup fallback"""
    
    def __init__(self):
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._callbacks = {}
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for events"""
        self._callbacks[event] = callback
    
    def _emit(self, event: str, *args, **kwargs):
        """Emit an event"""
        if event in self._callbacks:
            try:
                self._callbacks[event](*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    async def run_job(self, job: Job, progress_callback: Optional[Callable] = None) -> JobResult:
        """Run a scraping job"""
        self._running = True
        result = JobResult(
            id=generate_unique_id(),
            job_id=job.id,
            started_at=datetime.now()
        )
        
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.last_run_at = datetime.now()
            job.run_count += 1
            db.update_job(job)
            
            self._emit("job_started", job.id)
            
            # Collect all URLs to scrape
            urls = job.config.urls or [job.config.url]
            all_items: List[Tuple[str, Dict[str, Any]]] = []
            
            for url_idx, url in enumerate(urls):
                if not self._running:
                    break
                
                self._emit("progress", job.id, url_idx + 1, len(urls), f"Scraping: {url}")
                
                try:
                    if job.config.pagination.enabled and job.config.pagination.type == "next_button":
                        pagination_items = await self._scrape_paginated_pages(
                            job,
                            job.config.pagination,
                            progress_callback,
                            start_url=url,
                        )
                        all_items.extend(pagination_items)
                        result.success_count += len(pagination_items)
                    else:
                        # Scrape URL
                        items = await self._scrape_url(job, url, progress_callback)
                        all_items.extend((url, item) for item in items)
                        result.success_count += len(items)

                        if job.config.pagination.enabled and job.config.pagination.type == "page_number":
                            pagination_items = await self._handle_pagination(job, url, progress_callback)
                            all_items.extend(pagination_items)
                            result.success_count += len(pagination_items)
                    
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    result.failure_count += 1
                
                # Update progress
                if progress_callback:
                    progress_callback(job.id, url_idx + 1, len(urls), f"Processed {url}")
             
            # Save items to database
            for item_url, item_data in all_items:
                item = ScrapedItem(
                    id=generate_unique_id(),
                    job_id=job.id,
                    data=item_data,
                    url=item_url
                )
                db.create_item(item)
            
            # Post items to API if configured
            if job.config.api.enabled and job.config.api.url:
                try:
                    await self._post_items_to_api(job, [item_data for _, item_data in all_items])
                    logger.info(f"Posted {len(all_items)} items to API for job {job.name}")
                except Exception as e:
                    logger.error(f"Failed to post items to API for job {job.name}: {e}")
            
            # Update result
            result.items_count = len(all_items)
            result.completed_at = datetime.now()
            
            # Update job status
            job.status = JobStatus.COMPLETED
            job.success_count += result.success_count
            db.update_job(job)
            
            db.create_result(result)
            
            self._emit("job_completed", job.id, result)
            
            logger.info(f"Job {job.name} completed: {result.success_count} items scraped")
            
        except Exception as e:
            logger.error(f"Job {job.name} failed: {e}")
            result.error_message = str(e)
            result.completed_at = datetime.now()
            
            job.status = JobStatus.FAILED
            job.failure_count += 1
            db.update_job(job)
            
            db.create_result(result)
            self._emit("job_failed", job.id, str(e))
        
        finally:
            self._running = False
        
        return result
    
    async def _scrape_url(self, job: Job, url: str, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Scrape a single URL"""
        items = []

        # Try Playwright first, fallback to requests
        try:
            items = await self._scrape_with_playwright(job, url)
        except RuntimeError as e:
            message = str(e).lower()
            if "browser binaries are not installed" in message or "executable doesn't exist" in message:
                pass
            else:
                logger.warning(f"Playwright failed, falling back to requests: {e}")
            items = await self._scrape_with_requests(job, url)
        except Exception as e:
            logger.warning(f"Playwright failed, falling back to requests: {e}")
            items = await self._scrape_with_requests(job, url)

        return items
    
    async def _scrape_with_playwright(self, job: Job, url: str) -> List[Dict[str, Any]]:
        """Scrape using Playwright"""
        from app.scraper.playwright_service import playwright_service
        
        items = []
        
        await playwright_service.initialize()
        
        browser = await playwright_service.launch_browser(
            headless=job.config.browser.headless,
            user_agent=job.config.browser.user_agent
        )
        
        context = await playwright_service.create_context(
            browser,
            viewport=(job.config.browser.viewport_width, job.config.browser.viewport_height),
            user_agent=job.config.browser.user_agent
        )
        
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Apply delay
            if job.config.browser.delay_ms > 0:
                await asyncio.sleep(job.config.browser.delay_ms / 1000)
            
            # Get page content
            content = await page.content()
            
            # Parse with BeautifulSoup
            items = self._parse_content(job, content, url)
            
        finally:
            await page.close()
            await context.close()
            await browser.close()
        
        return items
    
    async def _scrape_with_requests(self, job: Job, url: str) -> List[Dict[str, Any]]:
        """Scrape using requests + BeautifulSoup"""
        items = []

        headers = {"User-Agent": job.config.browser.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(self._executor, lambda: requests.get(url, headers=headers, timeout=30))
        response.raise_for_status()

        items = self._parse_content(job, response.text, response.url)

        return items

    def _parse_content(self, job: Job, content: str, page_url: str) -> List[Dict[str, Any]]:
        """Parse HTML content"""
        soup = BeautifulSoup(content, "lxml")
        
        items = []
        
        # Find root elements
        if job.config.root_selector:
            root_elements = soup.select(job.config.root_selector)
        else:
            root_elements = [soup]

        # If root selector is too strict, fall back to the full document.
        if not root_elements:
            root_elements = [soup]
        
        for element in root_elements:
            item = {}
            
            for field in job.config.fields:
                try:
                    value = self._extract_field(element, field)
                    item[field.name] = value
                except Exception as e:
                    logger.debug(f"Error extracting field {field.name}: {e}")
                    item[field.name] = field.default_value or ""
            
            # Keep item only when at least one field produced meaningful content.
            if any(str(v).strip() for v in item.values()):
                items.append(item)
        
        if not items:
            items.append(self._build_default_item(soup, page_url))
        
        return items

    def _build_default_item(self, soup: BeautifulSoup, page_url: str) -> Dict[str, Any]:
        """Build a generic fallback record when no custom fields are configured."""
        title = ""
        if soup.title and soup.title.get_text(strip=True):
            title = clean_text(soup.title.get_text(strip=True))

        description = ""
        meta_desc = soup.select_one("meta[name='description']")
        if meta_desc and meta_desc.get("content"):
            description = clean_text(meta_desc.get("content", ""))

        headline = ""
        h1 = soup.select_one("h1")
        if h1:
            headline = clean_text(h1.get_text(" ", strip=True))

        text_content = clean_text(soup.get_text(" ", strip=True))
        if len(text_content) > 8000:
            text_content = text_content[:8000]

        return {
            "source_url": page_url,
            "title": title,
            "headline": headline,
            "description": description,
            "text": text_content,
        }
    
    def _extract_field(self, element: BeautifulSoup, field: FieldConfig) -> str:
        """Extract a single field from element"""
        if field.selector_type == "css":
            selected = element.select_one(field.selector)
        elif field.selector_type == "xpath":
            # Use lxml for XPath support
            tree = html.fromstring(str(element))
            xpath_results = tree.xpath(field.selector)
            selected = xpath_results[0] if xpath_results else None
        else:
            selected = None
        
        if not selected:
            return field.default_value or ""
        
        # Get attribute or text
        if field.attribute == "text":
            value = selected.text_content() if hasattr(selected, 'text_content') else selected.get_text()
        elif field.attribute:
            value = selected.get(field.attribute) or ""
        else:
            value = selected.text_content() if hasattr(selected, 'text_content') else selected.get_text()
        
        # Apply transformations
        if field.transform:
            value = self._apply_transform(value, field.transform)
        
        return clean_text(value) if isinstance(value, str) else value
    
    def _apply_transform(self, value: str, transform: str) -> str:
        """Apply value transformation"""
        transforms = transform.split(",")
        
        for t in transforms:
            t = t.strip()
            if t == "strip":
                value = value.strip()
            elif t == "lowercase":
                value = value.lower()
            elif t == "uppercase":
                value = value.upper()
            elif t == "title":
                value = value.title()
            elif t == "int":
                value = int(re.sub(r"[^\d]", "", value)) if value else 0
            elif t == "float":
                value = float(re.sub(r"[^\d.]", "", value)) if value else 0.0
        
        return value
    
    async def _handle_pagination(self, job: Job, url: str, progress_callback: Optional[Callable] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """Handle pagination"""
        items = []
        
        pagination = job.config.pagination
        if not pagination.enabled:
            return items
        
        max_pages = pagination.max_pages
        start_page = pagination.start_page
        
        if pagination.type != "page_number":
            return items

        for page_num in range(start_page, start_page + max_pages):
            if not self._running or job.status == JobStatus.CANCELLED:
                break

            try:
                # Construct page URL
                page_url = self._construct_page_url(url, page_num)
                page_items = await self._scrape_url(job, page_url, progress_callback)
                items.extend((page_url, item) for item in page_items)

            except Exception as e:
                logger.debug(f"Pagination error on page {page_num}: {e}")
                break
        
        return items
    
    def _construct_page_url(self, base_url: str, page_num: int) -> str:
        """Construct URL for pagination"""
        if "?" in base_url:
            return f"{base_url}&page={page_num}"
        else:
            return f"{base_url}?page={page_num}"

    async def _scrape_paginated_pages(
        self,
        job: Job,
        pagination,
        progress_callback: Optional[Callable] = None,
        start_url: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Scrape multiple pages by clicking next button"""
        items = []

        from app.scraper.playwright_service import playwright_service

        try:
            await playwright_service.initialize()
            browser = await playwright_service.launch_browser(
                headless=job.config.browser.headless,
                user_agent=job.config.browser.user_agent
            )
        except RuntimeError as e:
            message = str(e).lower()
            if "browser binaries are not installed" in message or "executable doesn't exist" in message:
                page_items = await self._scrape_with_requests(job, start_url or job.config.url)
                return [(start_url or job.config.url, item) for item in page_items]
            raise

        context = await playwright_service.create_context(
            browser,
            viewport=(job.config.browser.viewport_width, job.config.browser.viewport_height),
            user_agent=job.config.browser.user_agent
        )

        page = await context.new_page()

        try:
            # Go to initial URL
            await page.goto(start_url or job.config.url, wait_until="networkidle", timeout=30000)
            current_url = page.url

            for page_num in range(pagination.max_pages):
                if not self._running:
                    break

                # Apply delay
                if job.config.browser.delay_ms > 0:
                    await asyncio.sleep(job.config.browser.delay_ms / 1000)

                # Scrape current page
                current_url = page.url
                content = await page.content()
                page_items = self._parse_content(job, content, current_url)
                items.extend((current_url, item) for item in page_items)

                # Try to click next button
                try:
                    next_button = page.locator(pagination.selector).first
                    if await next_button.is_visible(timeout=5000):
                        await next_button.click()
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    else:
                        logger.debug("Next button not found or not visible")
                        break
                except Exception as e:
                    logger.debug(f"Pagination click failed: {e}")
                    break

        finally:
            await page.close()
            await context.close()
            await browser.close()

        return items
    
    async def _post_items_to_api(self, job: Job, items: List[Dict[str, Any]]):
        """Post scraped items to configured API endpoint"""
        api_config = job.config.api

        # Prepare headers
        headers = api_config.headers.copy()

        # Add authentication
        if api_config.auth_type == "bearer" and api_config.auth_token:
            headers["Authorization"] = f"Bearer {api_config.auth_token}"
        elif api_config.auth_type == "basic" and api_config.auth_username and api_config.auth_password:
            import base64
            auth_string = base64.b64encode(f"{api_config.auth_username}:{api_config.auth_password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth_string}"
        elif api_config.auth_type == "api_key" and api_config.auth_token:
            headers[api_config.api_key_header] = api_config.auth_token

        # Post each item
        loop = asyncio.get_event_loop()
        for item in items:
            try:
                if api_config.method.upper() == "GET":
                    # For GET, send data as query parameters
                    response = await loop.run_in_executor(self._executor, lambda: requests.get(api_config.url, headers=headers, params=item, timeout=30))
                else:
                    # For POST/PUT/PATCH, send data as JSON body
                    response = await loop.run_in_executor(self._executor, lambda: requests.request(
                        api_config.method.upper(),
                        api_config.url,
                        headers=headers,
                        json=item,
                        timeout=30
                    ))

                response.raise_for_status()
                logger.debug(f"Successfully posted item to API: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to post item to API: {e}")
                raise
    
    def stop(self):
        """Stop running jobs"""
        self._running = False
        logger.info("Scraper engine stopped")


# Global instance
scraper_engine = ScraperEngine()
