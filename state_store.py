"""Snapshot State Store & Change Detection Engine.
Saves company states to ./store/{orgnr}.json and performs strict field diffing
to identify genuine corporate updates while preventing false change hallucination.
"""

import json
from pathlib import Path
from typing import Any, Optional
from models import UpdateDiff
from utils import clean_org_number, logger


class StateStore:
    """Manages idempotent persistence and update diffing for company envelopes."""

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = store_dir or Path("store")
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, orgnr: str) -> Path:
        clean = clean_org_number(orgnr)
        return self.store_dir / f"{clean}.json"

    def load_previous_state(self, orgnr: str) -> Optional[dict[str, Any]]:
        """Load previously saved company envelope from disk."""
        path = self._get_path(orgnr)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read existing store for {orgnr}: {e}")
        return None

    def save_state(self, orgnr: str, envelope_data: dict[str, Any]) -> None:
        """Persist current company envelope to state store."""
        path = self._get_path(orgnr)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(envelope_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state for {orgnr}: {e}")

    def compute_diff(
        self, previous_envelope: Optional[dict[str, Any]], current_sections: dict[str, Any]
    ) -> UpdateDiff:
        """Diff current sections against previous snapshot to identify genuine updates."""
        if not previous_envelope:
            return UpdateDiff(
                is_updated=False,
                changed_fields=[],
                details={},
                previous_retrieved_at=None,
            )

        prev_sections = previous_envelope.get("sections", {})
        prev_retrieved_at = previous_envelope.get("retrieved_at")

        changed_fields: list[str] = []
        details: dict[str, Any] = {}

        # 1. Compare Legal Name
        curr_name = (
            current_sections.get("legal_identity", {})
            .get("claims", {})
            .get("legal_name", {})
            .get("value")
        )
        prev_name = (
            prev_sections.get("legal_identity", {})
            .get("claims", {})
            .get("legal_name", {})
            .get("value")
        )
        if curr_name and prev_name and curr_name != prev_name:
            changed_fields.append("legal_name")
            details["legal_name"] = {"previous": prev_name, "current": curr_name}

        # 2. Compare Employee Count
        curr_emp = (
            current_sections.get("legal_identity", {})
            .get("claims", {})
            .get("employee_count", {})
            .get("value")
        )
        prev_emp = (
            prev_sections.get("legal_identity", {})
            .get("claims", {})
            .get("employee_count", {})
            .get("value")
        )
        if curr_emp is not None and prev_emp is not None and curr_emp != prev_emp:
            changed_fields.append("employee_count")
            details["employee_count"] = {"previous": prev_emp, "current": curr_emp}

        # 3. Compare Insolvency Status
        curr_bankrupt = (
            current_sections.get("legal_identity", {})
            .get("claims", {})
            .get("is_bankrupt", {})
            .get("value")
        )
        prev_bankrupt = (
            prev_sections.get("legal_identity", {})
            .get("claims", {})
            .get("is_bankrupt", {})
            .get("value")
        )
        if (
            curr_bankrupt is not None
            and prev_bankrupt is not None
            and curr_bankrupt != prev_bankrupt
        ):
            changed_fields.append("is_bankrupt")
            details["is_bankrupt"] = {
                "previous": prev_bankrupt,
                "current": curr_bankrupt,
            }

        # 4. Compare Annual Accounts Period
        curr_period = current_sections.get("annual_accounts", {}).get("reporting_period")
        prev_period = prev_sections.get("annual_accounts", {}).get("reporting_period")
        if curr_period and prev_period and curr_period != prev_period:
            changed_fields.append("annual_accounts_period")
            details["annual_accounts_period"] = {
                "previous": prev_period,
                "current": curr_period,
            }

        # 5. Compare Revenue
        curr_rev = (
            current_sections.get("annual_accounts", {})
            .get("claims", {})
            .get("revenue", {})
            .get("value")
        )
        prev_rev = (
            prev_sections.get("annual_accounts", {})
            .get("claims", {})
            .get("revenue", {})
            .get("value")
        )
        if curr_rev is not None and prev_rev is not None and curr_rev != prev_rev:
            changed_fields.append("revenue")
            details["revenue"] = {"previous": prev_rev, "current": curr_rev}

        # 6. Compare Website
        curr_site = current_sections.get("website", {}).get("official_website")
        prev_site = prev_sections.get("website", {}).get("official_website")
        if curr_site and prev_site and curr_site != prev_site:
            changed_fields.append("official_website")
            details["official_website"] = {"previous": prev_site, "current": curr_site}

        return UpdateDiff(
            is_updated=bool(changed_fields),
            changed_fields=changed_fields,
            details=details,
            previous_retrieved_at=prev_retrieved_at,
        )
