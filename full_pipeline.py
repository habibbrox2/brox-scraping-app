"""
Complete Pipeline - Scrape + Enhance + Post
All-in-one data collection and publishing system
"""

import os
import sys
import json
import sqlite3
import requests
import asyncio
import httpx
from datetime import datetime
from selectolax.parser import HTMLParser
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scrapmaster.db")

# ======================
# Configuration
# ======================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]

# ======================
# Async Scraper
# ======================

class FastScraper:
    """Fast async scraper"""
    
    async def fetch(self, url: str) -> str:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
    
    async def scrape(self, url: str) -> list:
        html = await self.fetch(url)
        tree = HTMLParser(html)
        
        items = []
        for a in tree.css("a")[:20]:
            text = a.text()
            if text and len(text) > 10:
                items.append({
                    "title": text.strip()[:200],
                    "link": a.attributes.get("href", ""),
                    "scraped_at": datetime.now().isoformat()
                })
        
        return items

# ======================
# AI Enhancer
# ======================

class AIEnhancer:
    """OpenRouter AI enhancement"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"
    
    def enhance(self, items: list) -> list:
        if not self.api_key:
            return items  # No enhancement without key
        
        # Build prompt
        data_str = "\n".join([f"- {i['title']}" for i in items[:5]])
        
        prompt = f"""Analyze these news headlines and provide:
1. Categories (news/tech/business/sports)
2. Sentiment (positive/negative/neutral)  
3. Summary (1 sentence each)

Headlines:
{data_str}

Respond in JSON: [{{"title": "...", "category": "...", "sentiment": "...", "summary": "..."}}]"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000
        }
        
        try:
            resp = requests.post(self.url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # Parse JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                return json.loads(content)
        except:
            pass
        
        return items

# ======================
# Data Storage
# ======================

def save_items(items: list, source: str):
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    for item in items:
        conn.execute("""
            INSERT INTO scraped_data (id, source_id, data, url, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"{source}_{datetime.now().timestamp()}",
            source,
            json.dumps(item),
            item.get("link", ""),
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def save_enhanced(items: list):
    conn = sqlite3.connect(DB_PATH)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_data (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            original_data TEXT,
            enhanced_data TEXT,
            created_at TEXT
        )
    """)
    
    for item in items:
        conn.execute("""
            INSERT INTO enhanced_data (id, source_id, original_data, enhanced_data, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"enh_{datetime.now().timestamp()}",
            "auto",
            json.dumps(item.get("original", {})),
            json.dumps(item.get("enhanced", {})),
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

# ======================
# Main Pipeline
# ======================

async def run_pipeline(api_url: str = None, api_token: str = None, ai_key: str = None):
    """Run complete pipeline"""
    print("=" * 50)
    print("COMPLETE PIPELINE")
    print("Scraping → Enhancing → Posting")
    print("=" * 50)
    
    # Get sources
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM web_scraping_sources WHERE is_active = 1")
    sources = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n[1/3] Found {len(sources)} sources")
    
    # Scrape
    print("\n[2/3] Scraping...")
    scraper = FastScraper()
    all_items = []
    
    for source in sources[:10]:  # Limit for speed
        url = source["url"]
        name = source["name"]
        
        try:
            items = await scraper.scrape(url)
            for item in items:
                item["source"] = name
            
            if items:
                save_items(items, source["id"])
                all_items.extend(items)
                print(f"  ✓ {name}: {len(items)} items")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
    
    print(f"\nTotal scraped: {len(all_items)} items")
    
    # Enhance
    if ai_key and len(all_items) > 0:
        print("\n[3/3] Enhancing with AI...")
        enhancer = AIEnhancer(ai_key)
        enhanced = enhancer.enhance(all_items[:5])  # Limit for API cost
        
        if enhanced:
            save_enhanced([{
                "original": all_items[0],
                "enhanced": enhanced[0]
            }])
            print(f"  Enhanced {len(enhanced)} items")
    
    # Post to API
    if api_url and api_token and len(all_items) > 0:
        print("\nPosting to API...")
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        for item in all_items[:10]:
            try:
                resp = requests.post(api_url, json=item, headers=headers, timeout=30)
                if resp.status_code < 400:
                    print(f"  ✓ Posted: {item.get('title', '')[:30]}")
            except:
                pass
    
    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE!")
    print("=" * 50)

if __name__ == "__main__":
    # Get arguments
    api_url = sys.argv[1] if len(sys.argv) > 1 else None
    api_token = sys.argv[2] if len(sys.argv) > 2 else None
    ai_key = sys.argv[3] if len(sys.argv) > 3 else None
    
    if api_url:
        asyncio.run(run_pipeline(api_url, api_token, ai_key))
    else:
        asyncio.run(run_pipeline())