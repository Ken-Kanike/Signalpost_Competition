"""BRREG (Brønnøysundregistrene) Official API Collector.
Fetches official registry records from:
- Enhetsregisteret (entity identity, status, NACE, address, employees)
- Rolleregisteret (board, CEO, leadership roles)
- Regnskapsregisteret (annual financial statements, balance sheet, group/konsern accounts)
- Underenheter (registered branch workplaces)
"""

import asyncio
from typing import Any, Optional
import aiohttp

from config import AgentConfig, default_config
from utils import (
    FixtureManager,
    PerHostRateLimiter,
    RequestBudgetTracker,
    clean_org_number,
    logger,
    normalize_norwegian_text,
)


class BrregCollector:
    """Async client for official Norwegian registry data via BRREG Open APIs."""

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
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
        }

    async def _safe_fetch_json(
        self, session: aiohttp.ClientSession, url: str, orgnr: str, endpoint_key: str
    ) -> tuple[Optional[Any], int, str]:
        """Fetch JSON with rate limiting, budget check, and fixture support.
        Returns: (data_dict_or_list, status_code, error_message)
        """
        # Replay mode check
        if self.fixture_manager and self.fixture_manager.is_replaying():
            cached = self.fixture_manager.load_fixture(orgnr, endpoint_key)
            if cached is not None:
                return cached.get("data"), cached.get("status_code", 200), ""
            return None, 404, "Not found in replay fixture"

        # Check budget
        if self.budget_tracker and not await self.budget_tracker.record_request():
            return None, 429, "Daily request budget reached"

        # Rate limit
        if self.rate_limiter:
            await self.rate_limiter.wait(url)

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
            async with session.get(url, headers=self.headers, timeout=timeout) as resp:
                status_code = resp.status
                if status_code == 200:
                    data = await resp.json()
                    if self.fixture_manager and self.fixture_manager.is_recording():
                        self.fixture_manager.save_fixture(
                            orgnr, endpoint_key, {"status_code": status_code, "data": data}
                        )
                    return data, status_code, ""
                elif status_code == 404:
                    return None, 404, "Resource not found in registry"
                elif status_code == 410:
                    return None, 410, "Resource has been deregistered / removed"
                else:
                    text = await resp.text()
                    return None, status_code, f"HTTP {status_code}: {text[:200]}"
        except asyncio.TimeoutError:
            return None, 408, "Request timed out"
        except Exception as e:
            return None, 500, f"Exception: {str(e)}"

    async def fetch_enhet(
        self, session: aiohttp.ClientSession, orgnr: str
    ) -> dict[str, Any]:
        """Fetch primary entity details from Enhetsregisteret."""
        clean = clean_org_number(orgnr)
        url = f"{self.config.brreg_enheter_url}/{clean}"
        data, status_code, err = await self._safe_fetch_json(
            session, url, clean, "enheter"
        )
        return {
            "url": url,
            "status_code": status_code,
            "data": data,
            "error": err,
            "available": status_code == 200 and data is not None,
        }

    async def fetch_roller(
        self, session: aiohttp.ClientSession, orgnr: str
    ) -> dict[str, Any]:
        """Fetch leadership, board members, and auditors from Rolleregisteret."""
        clean = clean_org_number(orgnr)
        url = self.config.brreg_roller_url.format(orgnr=clean)
        data, status_code, err = await self._safe_fetch_json(
            session, url, clean, "roller"
        )
        return {
            "url": url,
            "status_code": status_code,
            "data": data,
            "error": err,
            "available": status_code == 200 and data is not None,
        }

    async def fetch_regnskap(
        self, session: aiohttp.ClientSession, orgnr: str
    ) -> dict[str, Any]:
        """Fetch annual financial statements from Regnskapsregisteret."""
        clean = clean_org_number(orgnr)
        url = self.config.brreg_regnskap_url.format(orgnr=clean)
        data, status_code, err = await self._safe_fetch_json(
            session, url, clean, "regnskap"
        )
        return {
            "url": url,
            "status_code": status_code,
            "data": data,
            "error": err,
            "available": status_code == 200 and bool(data),
        }

    async def fetch_underenheter(
        self, session: aiohttp.ClientSession, orgnr: str
    ) -> dict[str, Any]:
        """Fetch subordinate workplace units (underenheter/virksomheter)."""
        clean = clean_org_number(orgnr)
        url = f"{self.config.brreg_underenheter_url}?overordnetEnhet={clean}"
        data, status_code, err = await self._safe_fetch_json(
            session, url, clean, "underenheter"
        )
        return {
            "url": url,
            "status_code": status_code,
            "data": data,
            "error": err,
            "available": status_code == 200 and data is not None,
        }

    async def fetch_all(
        self, session: aiohttp.ClientSession, orgnr: str, fetch_budget_cap: int = 14
    ) -> dict[str, Any]:
        """Fetch all primary BRREG resources concurrently within allocated cap."""
        clean = clean_org_number(orgnr)

        # Core registry call first
        enhet_task = asyncio.create_task(self.fetch_enhet(session, clean))
        
        # Parallel tasks if cap permits
        roller_task = asyncio.create_task(self.fetch_roller(session, clean))
        regnskap_task = asyncio.create_task(self.fetch_regnskap(session, clean))
        underenheter_task = (
            asyncio.create_task(self.fetch_underenheter(session, clean))
            if fetch_budget_cap >= 4
            else None
        )

        enhet_res = await enhet_task
        roller_res = await roller_task
        regnskap_res = await regnskap_task
        underenheter_res = (
            await underenheter_task
            if underenheter_task
            else {
                "url": f"{self.config.brreg_underenheter_url}?overordnetEnhet={clean}",
                "status_code": 0,
                "data": None,
                "error": "Skipped due to request budget cap",
                "available": False,
            }
        )

        return {
            "organisation_number": clean,
            "enhet": enhet_res,
            "roller": roller_res,
            "regnskap": regnskap_res,
            "underenheter": underenheter_res,
        }
