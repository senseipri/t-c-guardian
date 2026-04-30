"""
Scraping tool powered by Crawl4AI.

This module does exactly ONE thing: given a URL, it returns clean
Markdown text of the page content. It strips navigation, footers,
cookie banners, and excessive whitespace.

Key design decisions:
  - Uses Crawl4AI's AsyncWebCrawler which runs a real headless browser
    (Playwright/Chromium) so sites that block simple HTTP clients with
    403 errors are handled transparently.
  - word_count_threshold=10 filters out empty or boilerplate blocks
  - Content is capped at 100k characters to stay within LLM context limits
  - The crawler runs in a separate thread with its own event loop to
    avoid the Windows/uvicorn subprocess-spawn issue with Playwright.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from crawl4ai import AsyncWebCrawler

# Dedicated thread pool for browser-based scraping
_executor = ThreadPoolExecutor(max_workers=2)


def _run_crawl(url: str) -> str:
    """
    Synchronous wrapper that creates a fresh event loop and runs
    the async crawler inside it.  This is necessary because Playwright
    cannot spawn browser sub-processes inside uvicorn's ProactorEventLoop
    on Windows.
    """
    loop = asyncio.new_event_loop()
    try:
        async def _crawl():
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    bypass_cache=True,
                )
                if not result.success:
                    raise RuntimeError(
                        f"Crawl4AI failed for {url}: {result.error_message}"
                    )
                return (result.markdown or "")[:100_000]

        return loop.run_until_complete(_crawl())
    finally:
        loop.close()


async def scrape_url(url: str) -> str:
    """
    Scrape a URL using a headless browser and return clean Markdown.

    Crawl4AI launches a real Chromium instance under the hood, which means:
      - JavaScript-rendered pages are supported
      - Cookie consent overlays are bypassed
      - 403 / bot-detection blocks are avoided (real browser fingerprint)

    The heavy lifting runs in a thread-pool so FastAPI's event loop
    is never blocked.

    Args:
        url: The page to scrape.

    Returns:
        Cleaned page text, capped at 100 000 characters.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_crawl, url)
