"""Jobs & Hiring Collector.
Collects active job listings from verified company careers pages and Norwegian job portals.
Returns 'not_available' safely when no verified job listings exist to prevent false claims.
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

    GENERIC_LABELS = {
        "see all jobs", "alle stillinger", "ledige stillinger", "søk stilling", "sok stilling",
        "send open application", "åpen søknad", "apen soknad", "send åpen søknad", "send apen soknad",
        "les mer", "se mer", "apply now", "søk her", "sok her", "careers", "karriere", "work with us",
        "jobb hos oss", "bli en av oss", "view all", "open positions", "find a job", "working at",
        "our culture", "job openings", "se alle ledige stillinger", "se alle stillinger",
    }
    BLOCKED_HOSTS = {
        "nav.no", "finn.no", "jobbnorge.no", "seek.com", "indeed.com",
        "arbeidsplassen.nav.no", "webcruiter.no",
    }

    def _parse_careers_html(
        self, html: str, base_url: str, max_jobs: int
    ) -> list[dict[str, Any]]:
        """Extract individual job postings adhering to strict precision rules."""
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[dict[str, Any]] = []

        base_parsed = urlparse(base_url)
        base_clean = base_url.rstrip("/").lower()
        base_domain = base_parsed.netloc.lower().replace("www.", "")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = " ".join(a.stripped_strings)
            clean_title = normalize_norwegian_text(text)
            clean_lower = clean_title.lower()

            # Rule 5: Title length 10–80 chars
            if not (10 <= len(clean_title) <= 80):
                continue

            # Rule 4: No generic navigation labels or application prompts
            if (
                clean_lower in self.GENERIC_LABELS
                or any(g in clean_lower for g in ["åpen søknad", "apen soknad", "se alle", "see all", "apply now", "jobb hos oss"])
            ):
                continue

            full_link = urljoin(base_url, href)
            parsed_link = urlparse(full_link)

            # Rule 1: Link must differ from careers index page
            if full_link.rstrip("/").lower() == base_clean:
                continue

            # Rule 2: No external job portals
            if any(b in parsed_link.netloc.lower() for b in self.BLOCKED_HOSTS):
                continue

            # Rule 3: Same domain only (no external or parent redirects)
            link_domain = parsed_link.netloc.lower().replace("www.", "")
            if link_domain != base_domain:
                continue

            # Vacancy indicators in link or title
            if any(
                k in href.lower() or k in clean_lower
                for k in [
                    "job", "stilling", "vacancy", "engineer", "developer",
                    "konsulent", "leder", "manager", "analyst", "rådgiver",
                    "spesialist", "medarbeider", "lead", "officer", "technician",
                    "coordinator", "koordinator", "arkitekt", "director", "designer"
                ]
            ):
                if not any(j["title"] == clean_title for j in jobs):
                    jobs.append({"title": clean_title, "url": full_link})
                    if len(jobs) >= max_jobs:
                        break

        return jobs
