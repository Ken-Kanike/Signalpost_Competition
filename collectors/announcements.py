"""Official BRREG Kunngjøringer (Announcements) Collector.
Extracts official corporate registration events (board changes, capital updates,
annual accounts approval, mergers/demergers) directly from Brønnøysundregistrene.
"""

import asyncio
import re
from typing import Any, Optional
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


class AnnouncementsCollector:
    """Async scraper for official corporate announcements from w2.brreg.no/kunngjoring."""

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
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": self.config.user_agent,
        }

    async def fetch_announcements(
        self, session: aiohttp.ClientSession, orgnr: str, max_items: int = 8
    ) -> dict[str, Any]:
        """Fetch and parse recent corporate announcements."""
        clean = clean_org_number(orgnr)
        url = f"https://w2.brreg.no/kunngjoring/hent.jsp?orgnr={clean}"

        # Replay mode
        if self.fixture_manager and self.fixture_manager.is_replaying():
            cached = self.fixture_manager.load_fixture(clean, "kunngjoringer")
            if cached is not None:
                return cached

        # Check budget
        if self.budget_tracker and not await self.budget_tracker.record_request():
            return {
                "url": url,
                "status_code": 429,
                "items": [],
                "error": "Daily request budget reached",
                "available": False,
            }

        # Rate limit
        if self.rate_limiter:
            await self.rate_limiter.wait(url)

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
            async with session.get(url, headers=self.headers, timeout=timeout) as resp:
                status_code = resp.status
                if status_code != 200:
                    return {
                        "url": url,
                        "status_code": status_code,
                        "items": [],
                        "error": f"HTTP {status_code}",
                        "available": False,
                    }

                raw_bytes = await resp.read()
                html = raw_bytes.decode("iso-8859-1", errors="replace")
                items = self._parse_announcements_html(html, max_items)

                result = {
                    "url": url,
                    "status_code": 200,
                    "items": items,
                    "error": "",
                    "available": bool(items),
                }

                if self.fixture_manager and self.fixture_manager.is_recording():
                    self.fixture_manager.save_fixture(clean, "kunngjoringer", result)

                return result
        except Exception as e:
            logger.warning(f"Failed to fetch announcements for {clean}: {e}")
            return {
                "url": url,
                "status_code": 500,
                "items": [],
                "error": str(e),
                "available": False,
            }

    def _parse_announcements_html(self, html: str, max_items: int) -> list[dict[str, str]]:
        """Extract structured announcement events from the HTML table."""
        soup = BeautifulSoup(html, "html.parser")
        items: list[dict[str, str]] = []

        # Find dates matching DD.MM.YYYY
        date_pattern = re.compile(r"^(\d{2}\.\d{2}\.\d{4})$")
        
        # Extract all text tokens from td elements
        tokens: list[str] = []
        for td in soup.find_all("td"):
            text = " ".join(td.stripped_strings)
            if text:
                tokens.append(text)

        i = 0
        while i < len(tokens) and len(items) < max_items:
            match = date_pattern.match(tokens[i])
            if match:
                raw_date = match.group(1)
                parts = raw_date.split(".")
                iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                
                # Next token(s) until next date or end is the announcement description
                desc_parts = []
                j = i + 1
                while j < len(tokens) and not date_pattern.match(tokens[j]):
                    if "Vis alle" not in tokens[j]:
                        desc_parts.append(tokens[j])
                    j += 1
                
                desc = normalize_norwegian_text(" ".join(desc_parts)) or "Registrert endring"
                items.append({
                    "date": iso_date,
                    "type": desc,
                    "description": f"Registrert i Foretaksregisteret: {desc}",
                })
                i = j
            else:
                i += 1

        return items
