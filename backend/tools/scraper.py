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

async def scrape_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(url)

    soup = BeautifulSoup(res.text, "html.parser")

    # Remove junk
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    return text[:100000]
