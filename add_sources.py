"""
Add web scraping sources directly from SQL
"""

import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scrapmaster.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create connection
conn = sqlite3.connect(DB_PATH)

# Create table
conn.execute("""
    CREATE TABLE IF NOT EXISTS web_scraping_sources (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        type TEXT,
        category_id INTEGER,
        selectors TEXT,
        advance_config TEXT,
        presets TEXT,
        fetch_interval INTEGER,
        is_active INTEGER DEFAULT 1,
        last_fetched_at TEXT,
        created_at TEXT,
        content_type TEXT,
        scrape_depth INTEGER,
        use_browser INTEGER,
        max_pages INTEGER,
        delay INTEGER,
        pagination_type TEXT,
        pagination_selector TEXT,
        pagination_pattern TEXT,
        proxy_enabled INTEGER,
        proxy_provider TEXT,
        proxy_config TEXT,
        ssl_verify INTEGER,
        timeout INTEGER,
        connect_timeout INTEGER
    )
""")

# SQL statements from user
sql_statements = [
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('1', 'Prothom Alo Latest', 'https://www.prothomalo.com/collection/latest', 'html', '1', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:07', '2026-03-07 18:59:24', 'articles', '2', '1', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('7', 'Ittefaq', 'https://www.ittefaq.com.bd/', 'html', '1', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:11', '2026-03-07 18:59:24', 'articles', '1', '0', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('17', 'BBC Travel', 'https://www.bbc.com/travel', 'scrape', '4', NULL, NULL, NULL, '3600', '1', '2026-03-28 08:00:11', '2026-03-07 18:59:24', 'articles', '1', '0', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('18', 'BBC Food', 'https://www.bbc.com/food', 'scrape', '4', NULL, NULL, NULL, '3600', '1', '2026-03-28 08:00:11', '2026-03-07 18:59:24', 'articles', '1', '0', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('21', 'BBC Bangla', 'https://www.bbc.com/bengali', 'html', '1', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:11', '2026-03-07 20:43:27', 'articles', '1', '0', '50', '2', 'link', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('22', 'The Daily Star (Bangla) - Today''s News', 'https://bangla.thedailystar.net/todays-news', 'scrape', '1', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:15', '2026-03-07 20:43:27', 'articles', '2', '1', '50', '2', 'link', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('24', 'Jugantor', 'https://www.jugantor.com/latest', 'scrape', '6', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:19', '2026-03-07 20:43:27', 'articles', '2', '1', '50', '2', 'link', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('25', 'Ittefaq Latest', 'https://www.ittefaq.com.bd/latest-news', 'html', '1', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:22', '2026-03-07 20:43:27', 'articles', '1', '1', '50', '2', 'link', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('26', 'Samakal Latest', 'https://samakal.com/latest/news', 'scrape', '6', NULL, NULL, NULL, '1800', '1', '2026-03-28 08:00:26', '2026-03-07 20:43:27', 'articles', '1', '1', '50', '5', 'link', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('28', 'GSMArena BD Devices', 'https://www.gsmarena.com.bd/', 'scrape', '1', NULL, NULL, NULL, '600', '1', '2026-03-28 08:00:30', '2026-03-21 14:34:02', 'mobiles', '2', '1', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('29', 'GSMArena Latest Devices', 'https://www.gsmarena.com/', 'scrape', '12', NULL, NULL, NULL, '600', '1', '2026-03-28 08:00:31', '2026-03-21 14:34:49', 'mobiles', '2', '1', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('30', 'GSMArena News', 'https://www.gsmarena.com/', 'scrape', '1', NULL, NULL, NULL, '600', '1', '2026-03-28 08:00:31', '2026-03-21 14:36:59', 'articles', '2', '1', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('31', 'BD News 24', 'https://bangla.bdnews24.com/', 'scrape', '6', NULL, NULL, NULL, '3600', '1', '2026-03-28 08:00:36', '2026-03-22 15:01:26', 'articles', '2', '1', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('32', 'Teletalk Government Jobs', 'https://alljobs.teletalk.com.bd', 'html', NULL, NULL, NULL, NULL, '3600', '1', '2026-03-28 08:00:41', '2026-03-27 19:51:25', 'articles', '1', '0', '50', '2', 'none', NULL, NULL, '0', NULL, NULL, '0', '60', '20')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('35', 'GitHub Trending Repositories', 'https://github.com/trending', 'scrape', '3', '{\"repo_name\":\"h2 a\",\"description\":\"p\",\"language\":\".f6 .d-inline-block\",\"stars\":\".f6 .d-inline-block + .d-inline-block\"}', '{\"user_agent\":\"Mozilla\\/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit\\/537.36 (KHTML, like Gecko) Chrome\\/120.0.0.0 Safari\\/537.36\",\"timeout\":45,\"follow_redirects\":true,\"extract_dynamic\":true,\"wait_for_js\":3000}', NULL, '3600', '1', NULL, '2026-03-31 02:46:23', 'articles', '1', '1', '3', '5', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('36', 'Reddit Programming', 'https://www.reddit.com/r/programming/', 'scrape', '2', '{\"title\":\"h3\",\"content\":\"[data-click-id=\\\"text\\\"]\",\"score\":\".score\",\"comments\":\".comments\"}', '{\"user_agent\":\"Mozilla\\/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit\\/537.36 (KHTML, like Gecko) Chrome\\/120.0.0.0 Safari\\/537.36\",\"timeout\":60,\"follow_redirects\":true,\"extract_dynamic\":true,\"wait_for_js\":5000,\"proxy_enabled\":true}', NULL, '1800', '1', NULL, '2026-03-31 02:46:23', 'articles', '1', '1', '5', '10', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')",
    "INSERT INTO `web_scraping_sources` (`id`, `name`, `url`, `type`, `category_id`, `selectors`, `advance_config`, `presets`, `fetch_interval`, `is_active`, `last_fetched_at`, `created_at`, `content_type`, `scrape_depth`, `use_browser`, `max_pages`, `delay`, `pagination_type`, `pagination_selector`, `pagination_pattern`, `proxy_enabled`, `proxy_provider`, `proxy_config`, `ssl_verify`, `timeout`, `connect_timeout`) VALUES ('37', 'Stack Overflow Questions', 'https://stackoverflow.com/questions', 'scrape', '3', '{\"title\":\"h3 a\",\"tags\":\".tags .post-tag\",\"votes\":\".vote-count-post\",\"answers\":\".status strong\"}', '{\"user_agent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\", \"timeout\": 30, \"follow_redirects\": true, \"extract_dynamic\": false}', NULL, '3600', '1', NULL, '2026-03-31 02:46:23', 'articles', '1', '0', '10', '5', 'none', NULL, NULL, '0', NULL, NULL, '1', '30', '10')"
]

# Execute each SQL
count = 0
for sql in sql_statements:
    try:
        conn.execute(sql)
        count += 1
    except Exception as e:
        print(f"Error: {e}")
        break

conn.commit()

# Verify
cursor = conn.execute("SELECT COUNT(*) FROM web_scraping_sources")
total = cursor.fetchone()[0]

conn.close()

print(f"Added {count} web scraping sources (total: {total})")