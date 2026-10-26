"""Web Enrichment Collector for Verified Company Websites & Proff.no.
Extracts business description, contact email/phone, social profiles, and industry insights
ONLY for websites that have passed the strict 3-tier verification protocol.
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


class WebEnricher:
    """Enriches verified company profiles with metadata, social links, and descriptions."""

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

    async def enrich_from_website(
        self,
        session: aiohttp.ClientSession,
        verified_url: Optional[str],
        prefetched_html: Optional[str] = None,
        company_name: str = "",
    ) -> dict[str, Any]:
        """Extract description, social profiles, and contact details from verified homepage."""
        if not verified_url:
            return {
                "status": "not_available",
                "description": None,
                "social_profiles": [],
                "contact_email": None,
                "contact_phone": None,
                "careers_url": None,
            }

        html = prefetched_html
        if not html:
            # Check budget
            if self.budget_tracker and not await self.budget_tracker.record_request():
                return {
                    "status": "blocked",
                    "reason": "Request budget reached",
                    "description": None,
                    "social_profiles": [],
                    "contact_email": None,
                    "contact_phone": None,
                    "careers_url": None,
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
                logger.debug(f"Failed to fetch homepage for enrichment: {e}")

        if not html:
            return {
                "status": "failed",
                "description": None,
                "social_profiles": [],
                "contact_email": None,
                "contact_phone": None,
                "careers_url": None,
            }

        return self._extract_metadata_from_html(html, verified_url, company_name)

    def _get_name_tokens(self, company_name: str) -> list[str]:
        """Extract lower-case distinctive name tokens from company name."""
        clean = normalize_norwegian_text(company_name).lower()
        stopwords = {
            "as", "asa", "ba", "sa", "ans", "da", "holding", "group", "norge",
            "norway", "nordic", "the", "og", "and", "avd", "filial", "eiendom",
        }
        words = re.findall(r"[a-zæøå0-9]+", clean)
        return [w for w in words if w not in stopwords and len(w) >= 3]

    def _is_company_social_account(self, url: str, company_name: str) -> bool:
        """Verify that a social link points to THIS company, not a generic button, agency, or theme."""
        if not url:
            return False
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return False

        # Block share / intent / widget URLs
        blocked_keywords = ["sharer", "share.php", "intent/tweet", "plugins", "widgets", "dialog"]
        if any(bk in url.lower() for bk in blocked_keywords):
            return False

        path_parts = [p for p in path.split("/") if p]
        if not path_parts:
            return False

        # LinkedIn: must be /company/{slug} or /school/{slug}
        if "linkedin.com" in parsed.netloc:
            if len(path_parts) >= 2 and path_parts[0] in ("company", "school"):
                slug = path_parts[1].lower().replace("-", " ").replace("_", " ")
            else:
                return False
        else:
            slug = path_parts[-1].lower().replace("-", " ").replace("_", " ")

        if not company_name:
            return True

        tokens = self._get_name_tokens(company_name)
        if not tokens:
            return True

        min_len = 4 if any(len(t) >= 4 for t in tokens) else 3
        return any(
            t in slug or slug in t
            for t in tokens
            if len(t) >= min_len
        )

    def _extract_metadata_from_html(
        self, html: str, base_url: str, company_name: str = ""
    ) -> dict[str, Any]:
        """Parse structured metadata, meta tags, and links from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # 1. Description from meta tags
        description = None
        for meta_name in ["description", "og:description", "twitter:description"]:
            meta = soup.find("meta", attrs={"name": meta_name}) or soup.find(
                "meta", attrs={"property": meta_name}
            )
            if meta and meta.get("content"):
                candidate = normalize_norwegian_text(meta["content"])
                if len(candidate) > 20:
                    description = candidate[:500]
                    break

        # 2. Social media profiles
        social_profiles: list[str] = []
        social_domains = [
            "linkedin.com/company",
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "youtube.com",
            "github.com",
        ]
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            for s_dom in social_domains:
                if s_dom in href:
                    if href.startswith("http://") or href.startswith("https://"):
                        clean_href = href.split("?")[0].rstrip("/")
                        if clean_href not in social_profiles and self._is_company_social_account(
                            clean_href, company_name
                        ):
                            social_profiles.append(clean_href)

        # 3. Contact Email
        contact_email = None
        mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mailto and mailto.get("href"):
            raw_mail = mailto["href"].replace("mailto:", "").split("?")[0].strip()
            if "@" in raw_mail:
                contact_email = raw_mail

        # 4. Contact Phone
        contact_phone = None
        tel = soup.find("a", href=re.compile(r"^tel:", re.I))
        if tel and tel.get("href"):
            raw_tel = tel["href"].replace("tel:", "").strip()
            contact_phone = raw_tel

        # 5. Careers URL detection
        careers_url = None
        for a in soup.find_all("a", href=True):
            href = a["href"].strip().lower()
            text = " ".join(a.stripped_strings).lower()
            if any(k in href or k in text for k in ["karriere", "careers", "jobb", "stilling", "work-with-us"]):
                full_careers_url = urljoin(base_url, a["href"].strip())
                careers_url = full_careers_url
                break

        return {
            "status": "available",
            "description": description,
            "social_profiles": social_profiles[:8],
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "careers_url": careers_url,
        }

    async def enrich_from_proff(
        self, session: aiohttp.ClientSession, orgnr: str
    ) -> dict[str, Any]:
        """Fetch supplementary enrichment from Proff.no (credit rating, officers).
        Respects budget and rate limits; Proff data is strictly supplementary to BRREG.
        """
        clean = clean_org_number(orgnr)
        url = f"{self.config.proff_base_url}/-/{clean}"

        # Replay mode
        if self.fixture_manager and self.fixture_manager.is_replaying():
            cached = self.fixture_manager.load_fixture(clean, "proff")
            if cached is not None:
                return cached

        # Check budget
        if self.budget_tracker and not await self.budget_tracker.record_request():
            return {
                "status": "not_available",
                "url": url,
                "reason": "Request budget limit reached",
                "credit_rating": None,
                "officers": [],
            }

        if self.rate_limiter:
            await self.rate_limiter.wait(url)

        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
            headers = {
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": self.config.user_agent,
            }
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return {
                        "status": "not_available",
                        "url": url,
                        "status_code": resp.status,
                        "reason": f"Proff.no returned HTTP {resp.status}",
                        "credit_rating": None,
                        "officers": [],
                    }
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract credit rating badge if available
                credit_rating = None
                rating_elem = soup.find(class_=re.compile(r"rating|credit", re.I))
                if rating_elem:
                    credit_rating = rating_elem.get_text(strip=True)

                # Extract officer names if listed
                officers = []
                for row in soup.find_all("tr"):
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) >= 2:
                        name, role = cells[0], cells[1]
                        if len(name) >= 3 and any(r in role.lower() for r in ["leder", "styre", "direktør"]):
                            officers.append({"name": name, "role": role})

                result = {
                    "status": "available" if (credit_rating or officers) else "not_available",
                    "url": url,
                    "status_code": 200,
                    "credit_rating": credit_rating,
                    "officers": officers[:5],
                }

                if self.fixture_manager and self.fixture_manager.is_recording():
                    self.fixture_manager.save_fixture(clean, "proff", result)

                return result
        except Exception as e:
            logger.debug(f"Proff.no enrichment skipped for {clean}: {e}")
            return {
                "status": "not_available",
                "url": url,
                "reason": str(e),
                "credit_rating": None,
                "officers": [],
            }
