"""
Playwright service for ScrapMaster Desktop
"""

import asyncio
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from app.utils.logger import get_logger

logger = get_logger()

class PlaywrightService:
    """Playwright browser service"""
    
    _instance = None
    _playwright = None
    _browser: Optional[Browser] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright")
        self._initialized = False
    
    async def initialize(self):
        """Initialize Playwright"""
        if self._initialized:
            return
        
        try:
            self._playwright = await async_playwright().start()
            self._initialized = True
            logger.info("Playwright initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise
    
    async def launch_browser(self, headless: bool = False, user_agent: Optional[str] = None, 
                           proxy: Optional[str] = None) -> Browser:
        """Launch a browser instance"""
        if not self._initialized:
            await self.initialize()
        
        # Browser launch options
        launch_options = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox"
            ]
        }
        
        # Proxy configuration
        if proxy:
            launch_options["proxy"] = {"server": proxy}
        
        self._browser = await self._playwright.chromium.launch(**launch_options)
        logger.info(f"Browser launched (headless={headless})")
        return self._browser
    
    async def create_context(self, browser: Browser, viewport: tuple = (1920, 1080),
                           user_agent: Optional[str] = None) -> BrowserContext:
        """Create a new browser context"""
        context_options = {
            "viewport": {"width": viewport[0], "height": viewport[1]},
            "ignore_https_errors": True,
            "java_script_enabled": True,
        }
        
        if user_agent:
            context_options["user_agent"] = user_agent
        
        context = await browser.new_context(**context_options)
        logger.debug("New browser context created")
        return context
    
    async def create_page(self, context: BrowserContext, url: str) -> Page:
        """Create a new page and navigate to URL"""
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        logger.debug(f"Navigated to: {url}")
        return page
    
    async def get_page_screenshot(self, page: Page) -> bytes:
        """Get page screenshot"""
        return await page.screenshot()
    
    async def close_browser(self):
        """Close the browser"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")
    
    async def cleanup(self):
        """Cleanup Playwright"""
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self._initialized = False
            logger.info("Playwright cleaned up")


# Synchronous wrapper for easier use
class SyncPlaywrightService:
    """Synchronous wrapper for Playwright service"""
    
    def __init__(self):
        self._async_service = PlaywrightService()
        self._loop = None
        self._thread = None
    
    def _run_async(self, coro):
        """Run async coroutine in new event loop"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            return self._loop.run_until_complete(coro)
        finally:
            if self._loop:
                self._loop.close()
                self._loop = None
    
    def initialize(self):
        """Initialize Playwright"""
        return self._run_async(self._async_service.initialize())
    
    def launch_browser(self, headless: bool = False, user_agent: Optional[str] = None,
                   proxy: Optional[str] = None):
        """Launch browser"""
        return self._run_async(self._async_service.launch_browser(headless, user_agent, proxy))
    
    def create_context(self, browser, viewport: tuple = (1920, 1080), user_agent: Optional[str] = None):
        """Create browser context"""
        return self._run_async(self._async_service.create_context(browser, viewport, user_agent))
    
    def create_page(self, context, url: str):
        """Create page"""
        return self._run_async(self._async_service.create_page(context, url))
    
    def get_screenshot(self, page):
        """Get page screenshot"""
        return self._run_async(self._async_service.get_page_screenshot(page))
    
    def close_browser(self):
        """Close browser"""
        return self._run_async(self._async_service.close_browser())
    
    def cleanup(self):
        """Cleanup"""
        return self._run_async(self._async_service.cleanup())


# Global instance
playwright_service = PlaywrightService()