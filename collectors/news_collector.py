"""News & Press Releases Collector.
Extracts verified, dated corporate news articles directly from verified company websites.
Strictly requires explicit <time datetime="YYYY-MM-DD..."> publication dates and individual
article URLs to prevent publishing navigation labels, modified feed dates, or fake news.
"""

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

from config import AgentConfig, default_config
from utils import (
    FixtureManager,
    PerHostRateLimiter,
    RequestBudgetTracker,
    clean_org_number,
    logger,
    normalize_norwegian_text,
)


class NewsCollector:
    """Async collector for dated corporate news articles."""

    GENERIC_TITLES = {
        "see more", "see more news", "les mer", "se mer", "nyheter",
        "se alle nyheter", "pressemeldinger", "aktuelt", "siste nytt",
        "news", "press releases", "latest news", "view all", "read more",
        "arkiv", "archive", "nyhetsarkiv",
    }

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        rate_limiter: Optional[PerHostRateLimiter] = None,
        budget_tracker: Optional[RequestBudgetTracker] = None,
        fixture_manager: Optional[FixtureManager] = None,
    ):
        self.config = config or default_config
        self.rate_limiter = rate_limiter or PerHostRateLimiter(
            min_interval_sec=self.config.per_host_min_interval_sec
        )
        self.budget_tracker = budget_tracker or RequestBudgetTracker(
            max_daily_budget=self.config.max_daily_requests
        )
        self.fixture_manager = fixture_manager or FixtureManager(
            record_dir=self.config.record_fixtures_dir,
            replay_dir=self.config.replay_fixtures_dir,
        )
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": self.config.user_agent,
        }

    async def fetch_news(
        self,
        session: aiohttp.ClientSession,
        orgnr: str,
        verified_url: Optional[str],
        prefetched_html: Optional[str] = None,
        max_items: int = 5,
    ) -> dict[str, Any]:
        """Fetch and extract verified, individually dated news articles."""
        clean = clean_org_number(orgnr)
        if not verified_url:
            return {
                "status": "not_available",
                "claims": [],
                "source_url": None,
                "reason": "Website not verified, skipping news collection",
            }

        html = prefetched_html
        if not html:
            if self.budget_tracker and not await self.budget_tracker.record_request():
                return {
                    "status": "blocked",
                    "claims": [],
                    "source_url": verified_url,
                    "reason": "Request budget limit reached",
                }

            if self.rate_limiter:
                await self.rate_limiter.wait(verified_url)

            try:
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
                async with session.get(
                    verified_url, headers=self.headers, timeout=timeout
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text(errors="replace")
            except Exception as e:
                logger.debug(f"Failed to fetch homepage for news: {e}")

        if not html:
            return {
                "status": "not_available",
                "claims": [],
                "source_url": verified_url,
                "reason": "Could not retrieve website HTML",
            }

        articles = self._parse_news_from_html(html, verified_url, max_items)
        return {
            "status": "available" if articles else "not_available",
            "claims": articles,
            "source_url": verified_url,
            "reason": "" if articles else "No dated news articles with explicit timestamps identified",
        }

    def _parse_news_from_html(
        self, html: str, base_url: str, max_items: int
    ) -> list[dict[str, str]]:
        """Extract individual news articles with strict explicit published date."""
        soup = BeautifulSoup(html, "html.parser")
        articles: list[dict[str, str]] = []

        base_clean = base_url.rstrip("/").lower()
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")

        # Look for containers with dates: <time>, <article>, or news item classes
        time_elements = soup.find_all("time")
        for t in time_elements:
            dt_raw = t.get("datetime") or t.get_text().strip()
            iso_date = self._parse_iso_date(dt_raw)
            if not iso_date:
                continue

            # Find parent article or enclosing container
            parent = t.find_parent(["article", "li", "div", "section"])
            if not parent:
                continue

            # Find heading or link
            link = parent.find("a", href=True)
            if not link:
                continue

            href = link["href"].strip()
            full_url = urljoin(base_url, href)
            parsed_link = urlparse(full_url)

            # Rule 1: Must not be homepage or index page itself
            if full_url.rstrip("/").lower() == base_clean:
                continue

            # Rule 2: Must be on the same domain
            if parsed_link.netloc.lower().replace("www.", "") != base_domain:
                continue

            # Extract title
            heading = parent.find(["h1", "h2", "h3", "h4", "h5"])
            title_text = heading.get_text().strip() if heading else link.get_text().strip()
            clean_title = normalize_norwegian_text(title_text)
            clean_lower = clean_title.lower()

            # Rule 3: Title length 15-200 chars
            if not (15 <= len(clean_title) <= 200):
                continue

            # Rule 4: Reject generic navigation titles
            if clean_lower in self.GENERIC_TITLES:
                continue

            # Deduplicate by title or URL
            if not any(a["title"] == clean_title or a["url"] == full_url for a in articles):
                articles.append({
                    "title": clean_title,
                    "url": full_url,
                    "published_date": iso_date,
                })
                if len(articles) >= max_items:
                    break

        return articles

    def _parse_iso_date(self, text: Optional[str]) -> Optional[str]:
        """Validate and parse ISO 8601 date (YYYY-MM-DD)."""
        if not text:
            return None
        # Match YYYY-MM-DD
        m = re.search(r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b", text)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # Match DD.MM.YYYY
        m2 = re.search(r"\b(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(20\d{2})\b", text)
        if m2:
            return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
        return None
