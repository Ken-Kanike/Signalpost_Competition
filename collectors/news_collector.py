"""News & Press Releases Collector.
Extracts verified, dated corporate news articles from verified company websites.

Strategy:
  1. RSS/Atom feed first — probes common feed paths for authoritative pub dates
  2. WordPress JSON REST API (/wp-json/wp/v2/posts)
  3. HTML <time datetime="YYYY-MM-DD"> fallback (original behavior)

All three paths enforce: individual article URLs, explicit publish dates,
non-generic titles (15–200 chars), and same-domain links.
"""

import asyncio
import json
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
    """Async collector for dated corporate news articles.
    Uses RSS/Atom feeds first (most reliable), falls back to HTML <time datetime> scraping.
    """

    GENERIC_TITLES = {
        "see more", "see more news", "les mer", "se mer", "nyheter",
        "se alle nyheter", "pressemeldinger", "aktuelt", "siste nytt",
        "news", "press releases", "latest news", "view all", "read more",
        "arkiv", "archive", "nyhetsarkiv",
    }

    # Common RSS/Atom/WordPress feed paths to probe on verified company websites
    RSS_FEED_PATHS = [
        "/feed",
        "/feed.xml",
        "/rss",
        "/rss.xml",
        "/atom.xml",
        "/nyheter/feed",
        "/news/feed",
        "/pressemeldinger/feed",
        "/aktuelt/feed",
        "/blog/feed",
        "/feed/rss",
        "/wp-json/wp/v2/posts",  # WordPress REST API (returns JSON array)
    ]

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
        """Fetch and extract verified, individually dated news articles.
        Strategy: RSS/Atom feed first (most reliable dates), then HTML <time datetime> fallback.
        """
        clean = clean_org_number(orgnr)
        if not verified_url:
            return {
                "status": "not_available",
                "claims": [],
                "source_url": None,
                "reason": "Website not verified, skipping news collection",
            }

        # Stage 1: Try RSS/Atom/WP-JSON feed paths
        rss_articles = await self._try_rss_feeds(session, verified_url, max_items)
        if rss_articles:
            return {
                "status": "available",
                "claims": rss_articles,
                "source_url": verified_url,
                "reason": f"Discovered {len(rss_articles)} articles from RSS/Atom feed",
            }

        # Stage 2: Fallback to HTML <time datetime> scraping
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

    async def _try_rss_feeds(
        self, session: aiohttp.ClientSession, base_url: str, max_items: int
    ) -> list[dict[str, str]]:
        """Probe common RSS/Atom feed paths. Returns articles on first successful feed found."""
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")

        for feed_path in self.RSS_FEED_PATHS:
            feed_url = f"{base_url.rstrip('/')}{feed_path}"

            if self.budget_tracker and not await self.budget_tracker.record_request():
                break
            if self.rate_limiter:
                await self.rate_limiter.wait(feed_url)

            try:
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
                rss_headers = {
                    "Accept": (
                        "application/rss+xml,application/atom+xml,"
                        "application/xml,text/xml,application/json,*/*"
                    ),
                    "User-Agent": self.config.user_agent,
                }
                async with session.get(
                    feed_url, headers=rss_headers, timeout=timeout, allow_redirects=True
                ) as resp:
                    if resp.status != 200:
                        continue
                    content_type = resp.headers.get("Content-Type", "").lower()
                    raw_bytes = await resp.read()
                    text = raw_bytes.decode("utf-8", errors="replace")

                    # Detect feed vs regular HTML page
                    is_feed = (
                        "xml" in content_type
                        or "rss" in content_type
                        or "atom" in content_type
                        or "json" in content_type
                        or text.strip().startswith("<?xml")
                        or "<rss" in text[:500]
                        or "<feed" in text[:500]
                        or (text.strip().startswith("[") and '"link"' in text[:1000])
                    )
                    if not is_feed:
                        continue

                    articles = self._parse_feed(text, base_url, base_domain, max_items)
                    if articles:
                        logger.debug(
                            f"RSS feed found at {feed_url}: {len(articles)} articles"
                        )
                        return articles

            except Exception as e:
                logger.debug(f"RSS probe failed {feed_url}: {e}")
                continue

        return []

    def _parse_feed(
        self,
        text: str,
        base_url: str,
        base_domain: str,
        max_items: int,
    ) -> list[dict[str, str]]:
        """Parse RSS, Atom, or WordPress JSON feed content into article dicts."""
        articles: list[dict[str, str]] = []

        # ---- WordPress JSON API (array of post objects) ----
        stripped = text.strip()
        if stripped.startswith("["):
            try:
                posts = json.loads(text)
                if isinstance(posts, list):
                    for post in posts[: max_items * 2]:
                        title = post.get("title", {})
                        if isinstance(title, dict):
                            title = title.get("rendered", "")
                        link = post.get("link", "")
                        date_str = post.get("date") or post.get("date_gmt", "")
                        iso_date = self._parse_iso_date(date_str)
                        clean_title = normalize_norwegian_text(
                            re.sub(r"<[^>]+>", "", str(title))
                        )
                        if iso_date and link and 15 <= len(clean_title) <= 200:
                            parsed = urlparse(link)
                            link_domain = parsed.netloc.lower().replace("www.", "")
                            if link_domain == base_domain or not link_domain:
                                if clean_title.lower() not in self.GENERIC_TITLES:
                                    articles.append(
                                        {
                                            "title": clean_title,
                                            "url": link,
                                            "published_date": iso_date,
                                        }
                                    )
                        if len(articles) >= max_items:
                            break
                    return articles
            except Exception:
                pass  # Not valid JSON, fall through to XML parser

        # ---- XML RSS / Atom ----
        try:
            soup = BeautifulSoup(text, "xml")

            # Atom: <entry> elements
            entries = soup.find_all("entry")
            if entries:
                for entry in entries:
                    t_tag = entry.find("title")
                    l_tag = entry.find("link")
                    d_tag = entry.find("published") or entry.find("updated")
                    if not (t_tag and l_tag and d_tag):
                        continue
                    link_href = l_tag.get("href") or l_tag.get_text()
                    iso_date = self._parse_iso_date(d_tag.get_text(strip=True))
                    clean_title = normalize_norwegian_text(t_tag.get_text(strip=True))
                    if iso_date and link_href and 15 <= len(clean_title) <= 200:
                        full_url = urljoin(base_url, link_href)
                        if (
                            urlparse(full_url).netloc.lower().replace("www.", "") == base_domain
                            and clean_title.lower() not in self.GENERIC_TITLES
                        ):
                            articles.append(
                                {"title": clean_title, "url": full_url, "published_date": iso_date}
                            )
                    if len(articles) >= max_items:
                        break
                return articles

            # RSS: <item> elements
            items = soup.find_all("item")
            for item in items:
                t_tag = item.find("title")
                l_tag = item.find("link")
                d_tag = (
                    item.find("pubDate")
                    or item.find("dc:date")
                    or item.find("published")
                )
                if not (t_tag and d_tag):
                    continue
                if l_tag:
                    link_href = l_tag.get_text(strip=True) or l_tag.get("href", "")
                else:
                    guid = item.find("guid")
                    link_href = guid.get_text(strip=True) if guid else ""
                raw_title = t_tag.get_text(strip=True)
                iso_date = self._parse_iso_date(d_tag.get_text(strip=True))
                clean_title = normalize_norwegian_text(re.sub(r"<[^>]+>", "", raw_title))
                if iso_date and link_href and 15 <= len(clean_title) <= 200:
                    full_url = urljoin(base_url, link_href)
                    parsed = urlparse(full_url)
                    link_domain = parsed.netloc.lower().replace("www.", "")
                    if (link_domain == base_domain or not link_domain) and (
                        clean_title.lower() not in self.GENERIC_TITLES
                    ):
                        articles.append(
                            {"title": clean_title, "url": full_url, "published_date": iso_date}
                        )
                if len(articles) >= max_items:
                    break

        except Exception as e:
            logger.debug(f"XML feed parse error: {e}")

        return articles

    def _parse_news_from_html(
        self, html: str, base_url: str, max_items: int
    ) -> list[dict[str, str]]:
        """Extract individual news articles with strict explicit published date from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        articles: list[dict[str, str]] = []

        base_clean = base_url.rstrip("/").lower()
        base_domain = urlparse(base_url).netloc.lower().replace("www.", "")

        time_elements = soup.find_all("time")
        for t in time_elements:
            dt_raw = t.get("datetime") or t.get_text().strip()
            iso_date = self._parse_iso_date(dt_raw)
            if not iso_date:
                continue

            parent = t.find_parent(["article", "li", "div", "section"])
            if not parent:
                continue

            link = parent.find("a", href=True)
            if not link:
                continue

            href = link["href"].strip()
            full_url = urljoin(base_url, href)
            parsed_link = urlparse(full_url)

            if full_url.rstrip("/").lower() == base_clean:
                continue
            if parsed_link.netloc.lower().replace("www.", "") != base_domain:
                continue

            heading = parent.find(["h1", "h2", "h3", "h4", "h5"])
            title_text = heading.get_text().strip() if heading else link.get_text().strip()
            clean_title = normalize_norwegian_text(title_text)
            clean_lower = clean_title.lower()

            if not (15 <= len(clean_title) <= 200):
                continue
            if clean_lower in self.GENERIC_TITLES:
                continue

            if not any(a["title"] == clean_title or a["url"] == full_url for a in articles):
                articles.append(
                    {"title": clean_title, "url": full_url, "published_date": iso_date}
                )
                if len(articles) >= max_items:
                    break

        return articles

    def _parse_iso_date(self, text: Optional[str]) -> Optional[str]:
        """Validate and parse ISO 8601, DD.MM.YYYY, or RFC 2822 date (RSS pubDate)."""
        if not text:
            return None
        # ISO YYYY-MM-DD (also handles datetime: 2026-10-20T...)
        m = re.search(
            r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])(?!\d)", text
        )
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # Norwegian DD.MM.YYYY
        m2 = re.search(
            r"\b(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(20\d{2})\b", text
        )
        if m2:
            return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
        # RFC 2822: "Mon, 20 Oct 2026 10:00:00 +0000"
        m3 = re.search(
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})\b",
            text,
            re.IGNORECASE,
        )
        if m3:
            month_map = {
                "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                "may": "05", "jun": "06", "jul": "07", "aug": "08",
                "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            }
            return f"{m3.group(3)}-{month_map[m3.group(2).lower()]}-{m3.group(1).zfill(2)}"
        return None
