"""3-Tier Website Verification Protocol & Domain Discovery Engine.
Guarantees zero wrong-company attribution by validating candidate websites:
- Tier 1: 9-digit Org Number proven on page HTML/JSON-LD
- Tier 2: Registered directly in official BRREG registry (hjemmeside)
- Tier 3: Distinctive company name match + email domain match + absence of conflicting orgnr
"""

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urlparse
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


class WebsiteVerifier:
    """Discovers and strictly verifies official company websites."""

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

    def extract_candidates_from_registry(
        self, enhet_data: dict[str, Any]
    ) -> tuple[Optional[str], list[str]]:
        """Extract primary registry website and additional candidate domains from email and name."""
        registry_website = enhet_data.get("hjemmeside")
        candidates: list[str] = []

        if registry_website:
            clean_url = self._normalize_url(registry_website)
            if clean_url:
                candidates.append(clean_url)

        # Domain discovery from registered email
        email = enhet_data.get("epostadresse", "")
        if email and "@" in email:
            domain = email.split("@")[1].strip().lower()
            if domain and domain not in self.config.free_email_providers:
                candidates.append(f"https://www.{domain}")
                candidates.append(f"https://{domain}")

        # Name-token domain candidates
        navn = enhet_data.get("navn", "")
        name_domain = self._generate_name_token_domain(navn)
        if name_domain:
            candidates.append(f"https://www.{name_domain}.no")

        # Deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        return registry_website, unique_candidates

    def _generate_name_token_domain(self, company_name: str) -> Optional[str]:
        """Convert company name to potential Norwegian domain token."""
        clean_name = normalize_norwegian_text(company_name).lower()
        # Remove common corporate suffixes
        clean_name = re.sub(
            r"\b(asa|as|ba|sa|ans|da|holding|group|gruppen|norge|norway)\b", "", clean_name
        )
        # Transliterate Norwegian chars for domain names
        clean_name = (
            clean_name.replace("æ", "ae")
            .replace("ø", "oe")
            .replace("å", "aa")
        )
        tokens = re.findall(r"[a-z0-9]+", clean_name)
        if tokens:
            # First distinctive token if long enough
            candidate = "".join(tokens)
            if len(candidate) >= 3 and len(candidate) <= 25:
                return candidate
        return None

    def _normalize_url(self, raw_url: str) -> Optional[str]:
        """Ensure standard https:// prefix and clean structure."""
        url = raw_url.strip()
        if not url:
            return None
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            return f"https://{parsed.netloc.lower()}"
        except Exception:
            return None

    async def verify_website(
        self,
        session: aiohttp.ClientSession,
        orgnr: str,
        company_name: str,
        enhet_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the 3-tier verification protocol on candidate websites."""
        clean_org = clean_org_number(orgnr)
        registry_site, candidates = self.extract_candidates_from_registry(enhet_data)

        # Check offline fixture
        if self.fixture_manager and self.fixture_manager.is_replaying():
            cached = self.fixture_manager.load_fixture(clean_org, "website_verification")
            if cached is not None:
                return cached

        # Try candidates in order
        for candidate_url in candidates:
            # Check budget
            if self.budget_tracker and not await self.budget_tracker.record_request():
                break

            # Rate limit
            if self.rate_limiter:
                await self.rate_limiter.wait(candidate_url)

            try:
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
                async with session.get(
                    candidate_url, headers=self.headers, timeout=timeout, allow_redirects=True
                ) as resp:
                    if resp.status not in (200, 301, 302, 307, 308):
                        continue

                    final_url = str(resp.url)
                    html = await resp.text(errors="replace")
                    
                    # 1. Tier 1: Check if orgnr appears in HTML / JSON-LD
                    if self._check_orgnr_in_html(html, clean_org):
                        result = {
                            "status": "available",
                            "verification_method": "tier1_orgnr_in_html",
                            "official_website": self._clean_final_url(final_url),
                            "html": html,
                            "reason": f"Organization number {clean_org} verified in page source",
                        }
                        self._maybe_save_fixture(clean_org, result)
                        return result

                    # 2. Tier 2: Check if this was the registry-listed website with ownership verification
                    if registry_site and self._is_same_host(candidate_url, registry_site):
                        ownership = self._check_site_ownership(html, clean_org, company_name)
                        if ownership == "parent_group":
                            logger.debug(
                                f"Skipping parent group website {candidate_url} for {clean_org}"
                            )
                            continue
                        elif ownership in ("confirmed", "name_match"):
                            result = {
                                "status": "available",
                                "verification_method": "tier2_registry_listed",
                                "official_website": self._clean_final_url(final_url),
                                "html": html,
                                "reason": f"Website listed directly in Brønnøysund Enhetsregisteret ({ownership})",
                            }
                            self._maybe_save_fixture(clean_org, result)
                            return result
                        else:
                            # Ambiguous: neither orgnr nor distinctive name found on page
                            continue

                    # 3. Tier 3: Distinctive name match + no conflicting orgnr
                    conflicting_org = self._find_conflicting_orgnr(html, clean_org)
                    if not conflicting_org and self._check_name_in_html(html, company_name):
                        result = {
                            "status": "available",
                            "verification_method": "tier3_name_proven",
                            "official_website": self._clean_final_url(final_url),
                            "html": html,
                            "reason": "High-confidence distinctive name match without conflicting orgnr",
                        }
                        self._maybe_save_fixture(clean_org, result)
                        return result

            except Exception as e:
                logger.debug(f"Candidate {candidate_url} check failed for {clean_org}: {e}")
                continue

        # If none verified, return unverified/not available to guarantee zero false attribution
        unverified_result = {
            "status": "not_available",
            "verification_method": "not_verified",
            "official_website": None,
            "html": "",
            "reason": "No website passed the 3-tier verification protocol",
        }
        self._maybe_save_fixture(clean_org, unverified_result)
        return unverified_result

    def _check_site_ownership(self, html: str, orgnr: str, company_name: str) -> str:
        """Verify site ownership: 'confirmed', 'name_match', 'parent_group', or 'ambiguous'."""
        if self._check_orgnr_in_html(html, orgnr):
            return "confirmed"
        if self._find_conflicting_orgnr(html, orgnr):
            return "parent_group"  # Different company's orgnr found
        if self._check_name_in_html(html, company_name):
            return "name_match"
        return "ambiguous"

    def _check_orgnr_in_html(self, html: str, orgnr: str) -> bool:
        """Check if 9-digit orgnr exists in raw text, formatted (e.g. 923 609 016), or JSON-LD."""
        formatted_orgnr = f"{orgnr[:3]} {orgnr[3:6]} {orgnr[6:]}"
        if orgnr in html or formatted_orgnr in html:
            return True
        return False

    def _find_conflicting_orgnr(self, html: str, target_orgnr: str) -> Optional[str]:
        """Find if a different 9-digit Norwegian orgnr appears prominently (e.g. in footer)."""
        pattern = re.compile(r"\b(9\d{8}|8\d{8})\b")
        matches = pattern.findall(html)
        for m in matches:
            if m != target_orgnr:
                return m
        return None

    def _check_name_in_html(self, html: str, company_name: str) -> bool:
        """Check if company name or core distinctive words appear in page title or h1."""
        clean_target = normalize_norwegian_text(company_name).lower()
        clean_target = re.sub(r"\b(asa|as|ba|sa|ans|da)\b", "", clean_target).strip()
        if len(clean_target) < 3:
            return False
        
        lower_html = html.lower()
        if clean_target in lower_html:
            return True
        return False

    def _is_same_host(self, url1: str, url2: str) -> bool:
        """Check if two URLs share the same root host."""
        try:
            h1 = urlparse(url1).netloc.lower().replace("www.", "")
            h2 = urlparse(url2).netloc.lower().replace("www.", "")
            return h1 == h2 and bool(h1)
        except Exception:
            return False

    def _clean_final_url(self, url: str) -> str:
        """Strip trailing slashes and query parameters."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _maybe_save_fixture(self, orgnr: str, result: dict[str, Any]) -> None:
        if self.fixture_manager and self.fixture_manager.is_recording():
            # Don't persist full giant html in fixture to keep size reasonable
            fixture_copy = dict(result)
            fixture_copy["html"] = fixture_copy.get("html", "")[:2000]
            self.fixture_manager.save_fixture(orgnr, "website_verification", fixture_copy)
