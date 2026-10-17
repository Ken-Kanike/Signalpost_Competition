"""Jobs & Hiring Collector.
Collects active job listings from verified company careers pages and Norwegian job portals.
Returns 'not_available' safely when no verified job listings exist to prevent false claims.
"""

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urljoin
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


class JobsCollector:
    """Async collector for hiring signals and job openings."""

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

    async def fetch_jobs(
        self,
        session: aiohttp.ClientSession,
        orgnr: str,
        company_name: str,
        careers_url: Optional[str] = None,
        max_jobs: int = 5,
    ) -> dict[str, Any]:
        """Fetch job openings from verified careers page or return safe not_available status."""
        clean = clean_org_number(orgnr)

        if not careers_url:
            return {
                "status": "not_available",
                "claims": [],
                "source_url": None,
                "reason": "No careers page found on verified company website",
            }

        # Check offline fixture
        if self.fixture_manager and self.fixture_manager.is_replaying():
            cached = self.fixture_manager.load_fixture(clean, "jobs")
            if cached is not None:
                return cached

        # Check budget
        if self.budget_tracker and not await self.budget_tracker.record_request():
            return {
                "status": "blocked",
                "claims": [],
                "source_url": careers_url,
                "reason": "Request budget reached",
            }

        if self.rate_limiter:
            await self.rate_limiter.wait(careers_url)

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
            async with session.get(
                careers_url, headers=self.headers, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    return {
                        "status": "not_available",
                        "claims": [],
                        "source_url": careers_url,
                        "reason": f"Careers page returned HTTP {resp.status}",
                    }

                html = await resp.text(errors="replace")
                jobs = self._parse_careers_html(html, careers_url, max_jobs)

                if jobs:
                    result = {
                        "status": "available",
                        "claims": jobs,
                        "source_url": careers_url,
                        "reason": f"Discovered {len(jobs)} active job postings",
                    }
                else:
                    result = {
                        "status": "not_available",
                        "claims": [],
                        "source_url": careers_url,
                        "reason": "Careers page contains no identifiable open vacancies",
                    }

                if self.fixture_manager and self.fixture_manager.is_recording():
                    self.fixture_manager.save_fixture(clean, "jobs", result)

                return result

        except Exception as e:
            logger.debug(f"Failed to fetch careers page {careers_url}: {e}")
            return {
                "status": "failed",
                "claims": [],
                "source_url": careers_url,
                "reason": str(e),
            }

    def _parse_careers_html(
        self, html: str, base_url: str, max_jobs: int
    ) -> list[dict[str, Any]]:
        """Extract job titles and links from careers HTML."""
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[dict[str, Any]] = []

        # Common job title container classes or patterns
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = " ".join(a.stripped_strings)
            # Must look like an actual vacancy title
            if len(text) >= 6 and len(text) <= 90:
                if any(
                    k in href.lower() or k in text.lower()
                    for k in [
                        "job",
                        "stilling",
                        "vacancy",
                        "engineer",
                        "developer",
                        "konsulent",
                        "leder",
                        "manager",
                        "analyst",
                        "rådgiver",
                        "spesialist",
                    ]
                ):
                    full_link = urljoin(base_url, href)
                    clean_title = normalize_norwegian_text(text)
                    if not any(j["title"] == clean_title for j in jobs):
                        jobs.append({"title": clean_title, "url": full_link})
                        if len(jobs) >= max_jobs:
                            break

        return jobs
