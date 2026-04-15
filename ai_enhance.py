"""
OpenRouter AI Enhancement System
Enhance scraped data with AI before posting to API
"""

import os
import json
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openai/gpt-4o"  # or other models

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scrapmaster.db")

# ========== AI Enhancement ==========

class AIEnhancer:
    """Enhance data using OpenRouter AI"""
    
    def __init__(self, api_key: str = OPENROUTER_API_KEY, model: str = OPENROUTER_MODEL):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def _build_prompt(self, items: List[Dict]) -> str:
        """Build enhancement prompt"""
        prompt = """Analyze the following scraped news/data items and enhance them:

For each item, provide:
1. Summary (2-3 sentences)
2. Category (news/tech/business/sports/entertainment/etc)
3. Sentiment (positive/negative/neutral)
4. Key entities (people, places, organizations)
5. Quality score (1-10)

Data items:
"""
        for i, item in enumerate(items[:10]):  # Limit to 10 items per request
            data = item.get("data", {})
            title = data.get("title", "")
            link = data.get("link", "")
            prompt += f"\n{i+1}. Title: {title}\n   Link: {link}"
        
        prompt += "\n\nRespond in JSON format with enhanced data."
        
        return prompt
    
    def enhance(self, items: List[Dict]) -> Optional[List[Dict]]:
        """Enhance items with AI"""
        if not self.api_key:
            print("ERROR: OpenRouter API key not set")
            return None
        
        if not items:
            return []
        
        # Prepare items
        data_list = []
        for item in items:
            try:
                data = json.loads(item["data"]) if isinstance(item["data"], str) else item.get("data", {})
            except:
                data = item.get("data", {})
            data_list.append(data)
        
        prompt = self._build_prompt(data_list)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://scrapmaster.local",
            "X-Title": "ScrapMaster AI"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a data enhancement AI. Analyze and summarize scraped data."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}")
                return None
            
            result = response.json()
            
            # Extract enhanced content
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            enhanced = json.loads(content)
            
            return enhanced if isinstance(enhanced, list) else [enhanced]
            
        except Exception as e:
            print(f"Enhancement error: {e}")
            return None

# ========== Data Pipeline ==========

def get_items(limit: int = 20) -> List[Dict]:
    """Get scraped items"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM scraped_data ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def save_enhanced(items: List[Dict]):
    """Save enhanced items"""
    conn = sqlite3.connect(DB_PATH)
    
    for item in items:
        conn.execute("""
            INSERT INTO enhanced_data (id, source_id, original_data, enhanced_data, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"enhanced_{datetime.now().timestamp()}",
            item.get("source_id", ""),
            json.dumps(item.get("original", {})),
            json.dumps(item.get("enhanced", {})),
            item.get("url", ""),
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def create_enhanced_table():
    """Create enhanced data table"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_data (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            original_data TEXT,
            enhanced_data TEXT,
            url TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# ========== Main ==========

def run_enhancement(api_key: str = None):
    """Run AI enhancement"""
    print("=" * 50)
    print("AI ENHANCEMENT PIPELINE")
    print("=" * 50)
    
    # Create table
    create_enhanced_table()
    
    # Get items
    items = get_items(10)
    print(f"\nFound {len(items)} items to enhance")
    
    if not items:
        print("No items found!")
        return
    
    # Initialize AI
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    enhancer = AIEnhancer(api_key=api_key)
    
    print(f"Using model: {enhancer.model}")
    print("\nEnhancing...")
    
    # Enhance
    enhanced = enhancer.enhance(items)
    
    if enhanced:
        print(f"\nEnhanced {len(enhanced)} items")
        
        # Save
        save_enhanced(enhanced)
        print("Saved to enhanced_data table")
        
        # Show sample
        print("\n--- Sample Enhancement ---")
        if enhanced:
            print(json.dumps(enhanced[0], indent=2)[:500])
    else:
        print("Enhancement failed")

if __name__ == "__main__":
    import sys
    
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    run_enhancement(api_key)