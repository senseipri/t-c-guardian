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

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
import re


async def scrape_url(url: str) -> str:
    """
    Fetch a URL and return its content as clean Markdown.

    Args:
        url: The full URL to scrape (must start with http:// or https://)

    Returns:
        A string of cleaned Markdown, capped at 100,000 characters.

    Raises:
        Exception: If Crawl4AI reports a failed crawl, with the error message.
    """
    config = CrawlerRunConfig(
        word_count_threshold=10,
        exclude_external_links=True,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            raise Exception(f"Scrape failed: {result.error_message}")

        # Crawl4AI exposes content in different attributes depending
        # on version; we try the most specific first
        markdown = result.markdown or result.extracted_content or ""

        # Collapse runs of 3+ newlines down to 2 for readability
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Hard cap protects the LLM context window downstream
        return markdown[:100_000]