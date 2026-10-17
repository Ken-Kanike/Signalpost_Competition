"""Configuration settings for Signalpost Norwegian Company Research Agent."""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
BASE_DIR = Path(__file__).resolve().parent
STORE_DIR = BASE_DIR / "store"
OUTPUT_DIR = BASE_DIR / "output"
PROFILES_DIR = BASE_DIR / "profiles"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"

# Ensure runtime directories exist
STORE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


class AgentConfig(BaseModel):
    """Runtime configuration for the agent pipeline."""

    # Public API Endpoints
    brreg_enheter_url: str = "https://data.brreg.no/enhetsregisteret/api/enheter"
    brreg_roller_url: str = "https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller"
    brreg_regnskap_url: str = "https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
    brreg_underenheter_url: str = "https://data.brreg.no/enhetsregisteret/api/underenheter"
    brreg_kunngjoringer_url: str = "https://data.brreg.no/enhetsregisteret/api/kunngjoringer"
    proff_base_url: str = "https://proff.no/selskap"
    finn_job_search_url: str = "https://www.finn.no/job/fulltime/search.html"

    # Competition Quotas & Limits
    max_daily_requests: int = 2000
    default_per_company_cap: int = 14
    min_per_company_cap: int = 2
    max_execution_minutes: int = 45
    per_host_min_interval_sec: float = 0.5  # Per-host rate limit: 1 request every 0.5s

    # Network settings
    request_timeout_sec: float = 12.0
    max_concurrent_workers: int = 15
    user_agent: str = (
        "SignalpostAgent/2.0 (Builderr Hackathon Contestant; Research bot; contact: contestant@builderr.ai)"
    )

    # Synthesis mode: 'template' (guaranteed zero hallucination, $0 cost)
    # or 'llm' (optional OpenAI GPT-4o-mini enrichment, keeps strict claim grounding)
    synthesis_mode: str = Field(
        default_factory=lambda: os.getenv("SYNTHESIS_MODE", "template").lower()
    )
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    openai_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )

    # Replay / Record modes for deterministic testing
    record_fixtures_dir: str = ""
    replay_fixtures_dir: str = ""

    # Known free mail providers to filter when extracting website candidates
    free_email_providers: set[str] = {
        "gmail.com",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "yahoo.com",
        "yahoo.no",
        "icloud.com",
        "me.com",
        "mac.com",
        "online.no",
        "broadpark.no",
        "getmail.no",
        "lyse.net",
        "proton.me",
        "protonmail.com",
        "mail.com",
        "zoho.com",
        "gmx.com",
        "telenor.no",
        "frisurf.no",
    }


default_config = AgentConfig()
