"""Test web_scraper real HTTP"""
import sys; sys.path.insert(0, '.')
from modules.web_scraper import WebScraper
m = WebScraper()

# Real HTTP test
r = m.quick_scrape('https://httpbin.org/html')
print(f"Single page: status={r.get('status')}, pages={r.get('pages')}, title={r.get('title','')[:50]}")

# Execute top-level
import asyncio
r2 = asyncio.run(m.execute("quick_scrape", {"url": "https://httpbin.org/html"}))
print(f"Execute: status={r2.get('status')}, pages={r2.get('pages')}")

# List actions
r3 = m._extract_links('<a href="https://example.com">link</a><a href="/page">rel</a>', 'https://base.com')
print(f"Links: {len(r3)} extracted")

# New import verification
import requests
print(f"requests: {requests.__version__}")

try:
    from bs4 import BeautifulSoup
    print(f"bs4: available")
except ImportError:
    print(f"bs4: NOT available (using regex fallback)")

print("ALL OK")
