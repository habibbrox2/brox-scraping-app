"""
Post collected data to external API
"""

import sqlite3
import os
import json
import requests
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scrapmaster.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_items(limit=100):
    """Get recent scraped items"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM scraped_data ORDER BY created_at DESC LIMIT ?", (limit,))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def post_to_api(api_url, api_token, items):
    """Post items to API"""
    if not items:
        print("No items to post")
        return 0
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    
    success = 0
    failed = 0
    
    for item in items:
        try:
            # Parse data JSON
            data = json.loads(item["data"])
            data["source_id"] = item["source_id"]
            data["scraped_at"] = item["created_at"]
            
            response = requests.post(api_url, json=data, headers=headers, timeout=30)
            
            if response.status_code < 400:
                success += 1
            else:
                failed += 1
                print(f"  Error {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            failed += 1
            print(f"  Error: {e}")
    
    return {"success": success, "failed": failed}

def run_post(api_url, api_token, limit=50):
    """Post data to API"""
    print("=" * 50)
    print("POST PIPELINE - Starting")
    print("=" * 50)
    
    items = get_items(limit)
    print(f"\nFound {len(items)} items to post")
    
    if not items:
        print("No items found!")
        return
    
    print(f"Posting to: {api_url}")
    
    result = post_to_api(api_url, api_token, items)
    
    print(f"\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Failed: {result['failed']}")
    print("=" * 50)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python post_data.py <api_url> <api_token>")
        print("Example: python post_data.py https://myapi.com/data your_token_here")
        sys.exit(1)
    
    api_url = sys.argv[1]
    api_token = sys.argv[2]
    
    run_post(api_url, api_token)