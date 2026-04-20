"""Layer 2 — Crawl4AI + Camoufox: headless browser for JS-heavy sites."""
from typing import Optional


async def crawl_with_crawl4ai(url: str, max_pages: int = 500) -> list[dict]:
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        browser_config = BrowserConfig(
            browser_type="firefox",
            headless=True,
            use_managed_browser=True,
            extra_args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        crawl_config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=5,
                max_pages=max_pages,
                include_external=False,
            ),
            mean_delay=1.5,
            max_range=0.5,
            word_count_threshold=10,
            exclude_external_links=True,
            wait_for="networkidle",
            page_timeout=30000,
        )
        pages = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.arun(url=url, config=crawl_config)
            for result in (results if isinstance(results, list) else [results]):
                if result.success:
                    pages.append({
                        "url": result.url,
                        "html": result.html,
                        "markdown": getattr(getattr(result, "markdown", None), "raw_markdown", ""),
                        "status_code": result.status_code,
                        "source": "crawl4ai",
                    })
        return pages
    except ImportError:
        return []
    except Exception:
        return []


async def fetch_single_with_crawl4ai(url: str) -> Optional[dict]:
    pages = await crawl_with_crawl4ai(url, max_pages=1)
    return pages[0] if pages else None
