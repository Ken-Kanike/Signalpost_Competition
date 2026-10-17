"""Data models for Signalpost Company Envelopes using Pydantic v2."""

from datetime import datetime, date
from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class Claim(BaseModel):
    """An atomic, auditable fact tied to an exact source URL and date."""

    value: Any = None
    claim_id: str
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    status: str = "available"  # available, not_available, blocked, not_applicable, ambiguous, failed
    description: Optional[str] = None
    currency: Optional[str] = None


class SectionLegalIdentity(BaseModel):
    status: str = "available"
    claims: dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class SectionAnnualAccounts(BaseModel):
    status: str = "available"
    reporting_period: Optional[str] = None
    claims: dict[str, Any] = Field(default_factory=dict)
    group_figures: Optional[dict[str, Any]] = None
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    reason: Optional[str] = None


class SectionLeadership(BaseModel):
    status: str = "available"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    reason: Optional[str] = None


class SectionWorkplaces(BaseModel):
    status: str = "available"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    reason: Optional[str] = None


class SectionWebsite(BaseModel):
    status: str = "available"
    verification_method: Optional[str] = None  # registry_listed, orgnr_in_html, email_domain_proven, not_verified
    official_website: Optional[str] = None
    claim_id: Optional[str] = None
    description: Optional[str] = None
    social_profiles: list[str] = Field(default_factory=list)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    reason: Optional[str] = None


class SectionHiring(BaseModel):
    status: str = "available"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    reason: Optional[str] = None


class SectionAnnouncements(BaseModel):
    status: str = "available"
    claims: list[dict[str, Any]] = Field(default_factory=list)
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    reason: Optional[str] = None


class DerivedSignal(BaseModel):
    value: Any
    description: Optional[str] = None
    based_on: list[str] = Field(default_factory=list)
    status: str = "available"


class Synthesis(BaseModel):
    text: str
    claim_references: list[str] = Field(default_factory=list)


class SourceRecord(BaseModel):
    url: str
    type: str = "api"  # api, website, scraping
    retrieved_date: str
    claims_backed: list[str] = Field(default_factory=list)


class UpdateDiff(BaseModel):
    is_updated: bool = False
    changed_fields: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    previous_retrieved_at: Optional[str] = None


from datetime import datetime, date, timezone

class CompanyEnvelope(BaseModel):
    """The master Signalpost Company Envelope representing full audited company intelligence."""

    organisation_number: str
    status: str = "available"  # available, not_found, blocked, failed
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    sections: dict[str, Any] = Field(default_factory=dict)
    derived_signals: dict[str, Any] = Field(default_factory=dict)
    synthesis: Optional[Synthesis] = None
    sources: list[SourceRecord] = Field(default_factory=list)
    update_diff: Optional[UpdateDiff] = None


class RunReport(BaseModel):
    """Execution telemetry and audit statistics for the batch run."""

    total_companies: int = 0
    successful_envelopes: int = 0
    failed_envelopes: int = 0
    total_outbound_requests: int = 0
    total_duration_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    average_claims_per_envelope: float = 0.0
    average_sources_per_envelope: float = 0.0
    compliance_checks: dict[str, bool] = Field(default_factory=dict)
