"""Async Pipeline Orchestrator with Dynamic Request Budgeting.
Coordinates collectors, verifier, normalizer, signals, synthesizer, and state store
while strictly enforcing daily limits: 45 minutes, 2,000 requests, and $10 cost cap.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Optional, Union
import aiohttp
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from citation_validator import CitationValidator
from collectors.announcements import AnnouncementsCollector
from collectors.brreg import BrregCollector
from collectors.jobs_collector import JobsCollector
from collectors.web_enricher import WebEnricher
from config import AgentConfig, default_config
from derived_signals import DerivedSignalsEngine
from models import CompanyEnvelope, RunReport, UpdateDiff
from normalizer import Normalizer
from state_store import StateStore
from synthesizer import Synthesizer
from utils import (
    FixtureManager,
    PerHostRateLimiter,
    RequestBudgetTracker,
    clean_org_number,
    console,
    get_current_iso_timestamp,
    is_valid_norwegian_orgnr,
    logger,
)
from website_verifier import WebsiteVerifier


class Orchestrator:
    """Master orchestrator executing the high-performance async intelligence pipeline."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or default_config
        self.rate_limiter = PerHostRateLimiter(
            min_interval_sec=self.config.per_host_min_interval_sec
        )
        self.budget_tracker = RequestBudgetTracker(
            max_daily_budget=self.config.max_daily_requests,
            default_cap=self.config.default_per_company_cap,
            min_cap=self.config.min_cap if hasattr(self.config, "min_cap") else 2,
        )
        self.fixture_manager = FixtureManager(
            record_dir=self.config.record_fixtures_dir,
            replay_dir=self.config.replay_fixtures_dir,
        )

        # Components
        self.brreg = BrregCollector(
            self.config, self.rate_limiter, self.budget_tracker, self.fixture_manager
        )
        self.announcements = AnnouncementsCollector(
            self.config, self.rate_limiter, self.budget_tracker, self.fixture_manager
        )
        self.verifier = WebsiteVerifier(
            self.config, self.rate_limiter, self.budget_tracker, self.fixture_manager
        )
        self.web_enricher = WebEnricher(
            self.config, self.rate_limiter, self.budget_tracker, self.fixture_manager
        )
        self.jobs = JobsCollector(
            self.config, self.rate_limiter, self.budget_tracker, self.fixture_manager
        )
        self.normalizer = Normalizer()
        self.signals_engine = DerivedSignalsEngine()
        self.synthesizer = Synthesizer(
            mode=self.config.synthesis_mode,
            openai_api_key=self.config.openai_api_key,
            openai_model=self.config.openai_model,
        )
        self.state_store = StateStore()
        self.validator = CitationValidator()

    async def process_company(
        self,
        session: aiohttp.ClientSession,
        orgnr: str,
        remaining_companies: int = 1,
    ) -> CompanyEnvelope:
        """Process a single Norwegian company through the full intelligence pipeline."""
        clean_org = clean_org_number(orgnr)
        start_time = time.monotonic()

        # Check budget availability
        if self.budget_tracker.is_budget_depleted():
            return CompanyEnvelope(
                organisation_number=clean_org,
                status="blocked",
                retrieved_at=get_current_iso_timestamp(),
                sections={"error": {"status": "blocked", "reason": "Daily request budget reached"}},
            )

        budget_cap = self.budget_tracker.get_dynamic_cap(remaining_companies)

        # 1. Fetch BRREG registry data (Enheter, Roller, Regnskap, Underenheter)
        brreg_results = await self.brreg.fetch_all(session, clean_org, fetch_budget_cap=budget_cap)
        enhet_res = brreg_results.get("enhet", {})
        enhet_data = enhet_res.get("data")

        # Entity not found in registry
        if not enhet_res.get("available") or not enhet_data:
            return CompanyEnvelope(
                organisation_number=clean_org,
                status="not_found",
                retrieved_at=get_current_iso_timestamp(),
                sections={
                    "legal_identity": {
                        "status": "not_available",
                        "reason": enhet_res.get("error", "Entity not found in Brønnøysund Enhetsregisteret"),
                    }
                },
            )

        company_name = enhet_data.get("navn", "")

        # 2. Stage 2: Website Discovery & 3-Tier Verification Protocol
        website_verification_res = await self.verifier.verify_website(
            session, clean_org, company_name, enhet_data
        )

        # 3. Stage 3: Web Enrichment (Only on verified sites)
        web_enrichment_res: dict[str, Any] = {}
        jobs_res: dict[str, Any] = {}
        if website_verification_res.get("status") == "available":
            verified_url = website_verification_res.get("official_website")
            prefetched_html = website_verification_res.get("html")
            web_enrichment_res = await self.web_enricher.enrich_from_website(
                session, verified_url, prefetched_html
            )
            # Fetch jobs if careers URL found and cap allows
            careers_url = web_enrichment_res.get("careers_url")
            if careers_url and budget_cap >= 6:
                jobs_res = await self.jobs.fetch_jobs(
                    session, clean_org, company_name, careers_url
                )
            else:
                jobs_res = {
                    "status": "not_available",
                    "claims": [],
                    "reason": "No careers page identified on verified website",
                }
        else:
            web_enrichment_res = {
                "status": "not_available",
                "description": None,
                "social_profiles": [],
                "contact_email": None,
                "contact_phone": None,
            }
            jobs_res = {
                "status": "not_available",
                "claims": [],
                "reason": "Website not verified, skipping careers scraping",
            }

        # 4. Stage 4: Kunngjøringer (Official corporate announcements)
        announcements_res: dict[str, Any] = {}
        if budget_cap >= 5:
            announcements_res = await self.announcements.fetch_announcements(
                session, clean_org, max_items=6
            )
        else:
            announcements_res = {
                "url": f"https://w2.brreg.no/kunngjoring/hent.jsp?orgnr={clean_org}",
                "status_code": 0,
                "items": [],
                "error": "Skipped due to dynamic request budget cap",
                "available": False,
            }

        # 5. Stage 5: Normalization & Sequential Claim ID Assignment
        sections, source_records = self.normalizer.normalize(
            orgnr=clean_org,
            enhet_raw=enhet_res,
            roller_raw=brreg_results.get("roller", {}),
            regnskap_raw=brreg_results.get("regnskap", {}),
            underenheter_raw=brreg_results.get("underenheter", {}),
            announcements_raw=announcements_res,
            website_raw=website_verification_res,
            web_enrichment_raw=web_enrichment_res,
            jobs_raw=jobs_res,
        )

        # 6. Stage 6: Derived Signals Engine (YoY revenue change, equity status, workforce)
        derived_signals = self.signals_engine.compute_signals(sections)

        # 7. Stage 7: Verifiable Synthesis (Claim ID References)
        synthesis = self.synthesizer.synthesize(clean_org, sections, derived_signals)

        # 8. Stage 8: State Store Snapshot Diffing (Detect true updates)
        prev_snapshot = self.state_store.load_previous_state(clean_org)
        update_diff = self.state_store.compute_diff(prev_snapshot, sections)

        # 9. Stage 9: Envelope Assembly
        envelope = CompanyEnvelope(
            organisation_number=clean_org,
            status="available",
            retrieved_at=get_current_iso_timestamp(),
            sections=sections,
            derived_signals=derived_signals,
            synthesis=synthesis,
            sources=source_records,
            update_diff=update_diff,
        )

        # 10. Self-Validation Check
        envelope_dict = envelope.model_dump()
        is_valid, validation_errors = self.validator.validate_envelope(envelope_dict)
        if not is_valid:
            logger.warning(f"Envelope for {clean_org} has validation warnings: {validation_errors}")

        # 11. Persist to State Store for future update diffing
        self.state_store.save_state(clean_org, envelope_dict)

        return envelope

    async def run_batch(
        self,
        org_numbers: list[str],
        output_file: Optional[Path] = None,
        concurrency: int = 15,
    ) -> tuple[list[CompanyEnvelope], RunReport]:
        """Execute batch run over an array of company numbers with concurrency and progress bar."""
        start_time = time.monotonic()
        total_companies = len(org_numbers)
        envelopes: list[CompanyEnvelope] = []

        semaphore = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(limit=concurrency + 5, ttl_dns_cache=300)

        # Prepare output file if specified
        out_f = None
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            out_f = open(output_file, "w", encoding="utf-8")

        total_claims_count = 0
        total_sources_count = 0
        success_count = 0
        fail_count = 0

        async with aiohttp.ClientSession(connector=connector) as session:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task(
                    f"[cyan]Researching Norwegian Companies...[/cyan]",
                    total=total_companies,
                )

                async def _worker(orgnr: str, idx: int):
                    nonlocal success_count, fail_count, total_claims_count, total_sources_count
                    async with semaphore:
                        remaining = total_companies - idx
                        env = await self.process_company(session, orgnr, remaining)
                        envelopes.append(env)

                        # Write streaming JSONL immediately
                        if out_f:
                            out_f.write(json.dumps(env.model_dump(), ensure_ascii=False) + "\n")
                            out_f.flush()

                        if env.status == "available":
                            success_count += 1
                            # Count claims
                            for sec in env.sections.values():
                                if isinstance(sec, dict):
                                    claims = sec.get("claims")
                                    if isinstance(claims, dict):
                                        total_claims_count += len(claims)
                                    elif isinstance(claims, list):
                                        total_claims_count += len(claims)
                            total_sources_count += len(env.sources)
                        else:
                            fail_count += 1

                        progress.advance(task_id)

                # Launch async tasks
                tasks = [
                    asyncio.create_task(_worker(orgnr, i))
                    for i, orgnr in enumerate(org_numbers)
                ]
                await asyncio.gather(*tasks)

        if out_f:
            out_f.close()

        duration = time.monotonic() - start_time
        avg_claims = (total_claims_count / success_count) if success_count > 0 else 0.0
        avg_sources = (total_sources_count / success_count) if success_count > 0 else 0.0

        # Calculate estimated cost
        # Default template synthesis uses $0 external model cost
        cost_usd = 0.0
        if self.config.synthesis_mode == "llm":
            # ~0.0002 USD per summary with gpt-4o-mini
            cost_usd = round(success_count * 0.0002, 4)

        report = RunReport(
            total_companies=total_companies,
            successful_envelopes=success_count,
            failed_envelopes=fail_count,
            total_outbound_requests=self.budget_tracker.total_requests_made,
            total_duration_seconds=round(duration, 2),
            estimated_cost_usd=cost_usd,
            average_claims_per_envelope=round(avg_claims, 1),
            average_sources_per_envelope=round(avg_sources, 1),
            compliance_checks={
                "within_2000_request_limit": self.budget_tracker.total_requests_made <= 2000,
                "within_45_minute_limit": duration <= (45 * 60),
                "within_10_dollar_cost_limit": cost_usd <= 10.0,
            },
        )

        return envelopes, report
