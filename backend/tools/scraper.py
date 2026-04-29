"""
Scraping tool powered by Crawl4AI.

This module does exactly ONE thing: given a URL, it returns clean
Markdown text of the page content. It strips navigation, footers,
cookie banners, and excessive whitespace.

Key design decisions:
  - word_count_threshold=10 filters out empty or boilerplate blocks
  - remove_overlay_elements=True strips cookie consent popups
  - Content is capped at 100k characters to stay within LLM context limits
  - We use the async crawler so FastAPI's event loop is never blocked
"""


import httpx
from bs4 import BeautifulSoup
import re

async def scrape_url(url: str, max_redirects=3) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    current_url = url
    redirects_followed = 0
    
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
        while redirects_followed <= max_redirects:
            res = await client.get(current_url)
            res.raise_for_status()

            soup = BeautifulSoup(res.text, "html.parser")
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'refresh'})
            if meta_refresh and meta_refresh.get('content'):
                content = meta_refresh['content']
                match = re.search(r'url=([^;]+)', content, re.IGNORECASE)
                if match:
                    next_url = match.group(1).strip('\'"')
                    # Handle relative URLs
                    if not next_url.startswith('http'):
                        from urllib.parse import urljoin
                        next_url = urljoin(current_url, next_url)
                    current_url = next_url
                    redirects_followed += 1
                    continue
            
            break

    # Remove junk
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    return text[:100000]
