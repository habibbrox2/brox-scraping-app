"""
Scraper Pipeline - Collects data from web sources
"""

import sqlite3
import os
import json
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scrapmaster.db")

def get_connection():
    """Get database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def get_sources():
    """Get all active sources"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM web_scraping_sources WHERE is_active = 1")
    sources = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sources

def scrape_source(source):
    """Scrape a single source"""
    url = source["url"]
    name = source["name"]
    use_browser = source["use_browser"]
    timeout = source.get("timeout", 30)
    delay = source.get("delay", 2)
    
    results = []
    error = None
    
    try:
        # Apply delay
        time.sleep(delay)
        
        # Simple request-based scraping
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # Extract basic data
        items = []
        
        # Try common article patterns
        articles = soup.select("article") or soup.select(".article") or soup.select("a[href*='/news']") or soup.select("a[href*='/article']")
        
        for i, article in enumerate(articles[:10]):  # Limit to 10 items
            item = {
                "source": name,
                "url": url,
                "title": article.get_text(strip=True)[:200] if article.get_text() else "",
                "link": article.get("href", ""),
                "scraped_at": datetime.now().isoformat()
            }
            
            # Try to get more details
            if article.select_one("time"):
                item["date"] = article.select_one("time").get("datetime", "")
            
            if article.select_one(".description") or article.select_one("p"):
                item["description"] = (article.select_one(".description") or article.select_one("p")).get_text(strip=True)[:500]
            
            if item["title"]:
                items.append(item)
        
        # If no articles found, get links
        if not items:
            links = soup.select("a")[:20]
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if href and (text and len(text) > 10):
                    items.append({
                        "source": name,
                        "url": url,
                        "title": text[:200],
                        "link": href,
                        "scraped_at": datetime.now().isoformat()
                    })
        
        results = items
        
    except Exception as e:
        error = str(e)
    
    return {
        "source_id": source["id"],
        "source_name": name,
        "url": url,
        "items": results,
        "count": len(results),
        "error": error
    }

def save_items(source_id, items):
    """Save scraped items"""
    conn = get_connection()
    
    for item in items:
        item_json = json.dumps(item)
        
        conn.execute("""
            INSERT INTO scraped_data (id, source_id, data, url, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"{source_id}_{datetime.now().timestamp()}",
            source_id,
            item_json,
            item.get("link", ""),
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def create_scraped_data_table():
    """Create scraped data table"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scraped_data (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            data TEXT NOT NULL,
            url TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def run_pipeline():
    """Run the complete pipeline"""
    print("=" * 50)
    print("SCRAPMASTER PIPELINE - Starting")
    print("=" * 50)
    
    # Create tables
    create_scraped_data_table()
    
    # Get sources
    sources = get_sources()
    print(f"\nFound {len(sources)} active sources")
    
    if not sources:
        print("No sources to scrape!")
        return
    
    # Scrape sources
    total_items = 0
    total_errors = 0
    
    for source in sources:
        print(f"\n[{source['name']}] Scraping...")
        
        result = scrape_source(source)
        
        if result["error"]:
            print(f"  ERROR: {result['error']}")
            total_errors += 1
        else:
            count = result["count"]
            print(f"  Scraped {count} items")
            total_items += count
            
            # Save items
            if result["items"]:
                save_items(source["id"], result["items"])
    
    print("\n" + "=" * 50)
    print(f"PIPELINE COMPLETE")
    print(f"Total items scraped: {total_items}")
    print(f"Total errors: {total_errors}")
    print("=" * 50)
    
    # Show recent items
    conn = get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM scraped_data")
    total = cursor.fetchone()[0]
    print(f"\nTotal items in database: {total}")
    conn.close()

if __name__ == "__main__":
    run_pipeline()