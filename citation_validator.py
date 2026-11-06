"""Citation & Schema Evidence Self-Validator.

Checks the evidence chain the viewer exposes:
- Modulo 11 checksum verification of organization number
- Every cited claim resolves to a declared claim
- Every available claim has an HTTP(S) source URL and retrieval date
- Claim source URLs match the envelope's source audit trail
- Source records carry dates and HTTP status codes
- Financial values are numeric, finite and currency-denominated
- Derived signals only reference existing claims
- Synthesis text and claim_references agree
"""

import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlparse

from utils import is_valid_norwegian_orgnr

_BLOCKED_HOSTS = {
    "example.com",
    "www.example.com",
    "example.org",
    "www.example.org",
    "example.net",
    "www.example.net",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "fake.com",
    "test.com",
}

_FINANCIAL_FIELDS = (
    "revenue",
    "operating_result",
    "net_income",
    "total_assets",
    "equity",
    "total_debt",
    "previous_year_revenue",
)


def _normalise_url(url: Any) -> str:
    if not isinstance(url, str):
        return ""
    return url.strip().rstrip("/").lower()


def _valid_http_url(url: Any) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if parsed.hostname and parsed.hostname.lower() in _BLOCKED_HOSTS:
        return False
    return True


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            parsed = date.fromisoformat(raw[:10])
        except ValueError:
            return False
    return parsed.year >= 1900 and parsed <= date.today()


def _valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and abs(float(value)) <= 1_000_000_000_000_000
    )


class CitationValidator:
    """Offline validation engine ensuring envelopes meet all evidence criteria."""

    def validate_envelope(self, envelope: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a single company envelope against published evidence requirements."""
        errors: list[str] = []

        # 1. Organisation number
        orgnr = str(envelope.get("organisation_number", ""))
        if not orgnr or not is_valid_norwegian_orgnr(orgnr):
            errors.append(f"Invalid Norwegian organization number or checksum failed: '{orgnr}'")

        # 2. Envelope retrieval timestamp
        retrieved_at = envelope.get("retrieved_at")
        if not retrieved_at:
            errors.append("Missing 'retrieved_at' ISO timestamp")
        elif not _valid_iso_date(retrieved_at):
            errors.append(f"Invalid 'retrieved_at' timestamp: '{retrieved_at}'")

        # 3. Index every declared claim, including website/social/contact claims
        sections = envelope.get("sections", {})
        known_claims: dict[str, dict[str, Any]] = {}
        claim_section: dict[str, str] = {}
        claim_sources: dict[str, str] = {}
        claim_dates: dict[str, str] = {}
        duplicate_claims: set[str] = set()

        def add_claim(cid: Any, cinfo: dict[str, Any], section_name: str, section: dict[str, Any]) -> None:
            if not isinstance(cid, str) or not re.fullmatch(r"c\d{3,}", cid):
                errors.append(f"Section '{section_name}' has invalid claim_id: {cid!r}")
                return
            if cid in known_claims and claim_section.get(cid) != section_name:
                duplicate_claims.add(cid)
                errors.append(
                    f"Claim ID {cid} is declared in both '{claim_section.get(cid)}' and '{section_name}'"
                )
                return
            known_claims[cid] = cinfo
            claim_section[cid] = section_name

            source = cinfo.get("source_url")
            if not source and section_name == "website":
                source = cinfo.get("official_website") or section.get("official_website")
            if not source:
                source = section.get("source_url")
            if source:
                claim_sources[cid] = source

            claim_date = cinfo.get("retrieved_date") or section.get("retrieved_date")
            if claim_date:
                claim_dates[cid] = claim_date

        for sec_name, sec_data in sections.items():
            if not isinstance(sec_data, dict):
                continue
            claims_container = sec_data.get("claims")
            if isinstance(claims_container, dict):
                for _, cinfo in claims_container.items():
                    if isinstance(cinfo, dict) and "claim_id" in cinfo:
                        add_claim(cinfo.get("claim_id"), cinfo, sec_name, sec_data)
            elif isinstance(claims_container, list):
                for item in claims_container:
                    if isinstance(item, dict) and "claim_id" in item:
                        add_claim(item.get("claim_id"), item, sec_name, sec_data)
            if sec_name == "website":
                if sec_data.get("claim_id"):
                    add_claim(sec_data.get("claim_id"), sec_data, sec_name, sec_data)
                for item in sec_data.get("social_claims", []) or []:
                    if isinstance(item, dict) and "claim_id" in item:
                        add_claim(item.get("claim_id"), item, sec_name, sec_data)

        # 4. Source audit trail
        sources = envelope.get("sources", [])
        source_by_url: dict[str, dict[str, Any]] = {}
        if not sources:
            errors.append("Envelope missing 'sources' audit trail")
        else:
            for source in sources:
                if not isinstance(source, dict):
                    errors.append("Source entry must be an object")
                    continue
                source_url = source.get("url")
                if not _valid_http_url(source_url):
                    errors.append(f"Source has invalid or placeholder URL: {source_url!r}")
                    continue
                normalised = _normalise_url(source_url)
                if normalised in source_by_url:
                    errors.append(f"Duplicate source URL in audit trail: {source_url}")
                source_by_url[normalised] = source

                if not _valid_iso_date(source.get("retrieved_date")):
                    errors.append(f"Source {source_url} missing or invalid retrieved_date")
                status = source.get("status_code")
                if source.get("claims_backed"):
                    if status is None:
                        errors.append(f"Source {source_url} backs claims but has no status_code")
                    elif not isinstance(status, int) or not (200 <= status < 400):
                        errors.append(f"Source {source_url} has non-success HTTP status: {status}")

        # 5. Claim integrity: available claims need source URL, date, and a matching source record
        for cid, cinfo in known_claims.items():
            status = cinfo.get("status", "available")
            source_url = claim_sources.get(cid)
            has_value = cinfo.get("value") is not None
            if not has_value and any(
                cinfo.get(key) not in (None, "", [])
                for key in ("official_website", "url", "name", "title", "description", "date", "platform")
            ):
                has_value = True

            if status == "available" and not has_value:
                errors.append(f"Claim {cid} is 'available' but has no value")
            if status == "available" and not source_url:
                errors.append(f"Claim {cid} is 'available' but has no source URL")
            if source_url:
                if not _valid_http_url(source_url):
                    errors.append(f"Claim {cid} has invalid or placeholder source URL: {source_url!r}")
                normalised_source = _normalise_url(source_url)
                if source_by_url and normalised_source not in source_by_url:
                    errors.append(f"Claim {cid} source URL is not present in sources: {source_url}")
                elif normalised_source in source_by_url:
                    backing = source_by_url[normalised_source].get("claims_backed") or []
                    if cid not in backing:
                        errors.append(
                            f"Claim {cid} is not listed in claims_backed for source {source_url}"
                        )
                if not _valid_iso_date(claim_dates.get(cid)):
                    errors.append(f"Claim {cid} missing or invalid retrieved_date")
            elif status == "available":
                errors.append(f"Claim {cid} is 'available' but has no evidence date")

        # 6. Synthesis citations
        synthesis = envelope.get("synthesis", {})
        if synthesis:
            syn_text = synthesis.get("text", "")
            syn_refs = synthesis.get("claim_references", [])
            if not isinstance(syn_text, str) or not syn_text.strip():
                errors.append("Synthesis text is empty")
            if not isinstance(syn_refs, list) or not all(isinstance(x, str) for x in syn_refs):
                errors.append("Synthesis claim_references must be a list of claim IDs")
                syn_refs = []
            if len(syn_refs) != len(set(syn_refs)):
                errors.append("Synthesis claim_references contains duplicate claim IDs")

            text_cited = set(re.findall(r"\[(c\d{3,})\]", syn_text))
            syn_ref_set = set(syn_refs)
            for cid in sorted(text_cited):
                if cid not in known_claims:
                    errors.append(f"Synthesis text cites unknown claim ID: [{cid}]")
            unlisted = text_cited - syn_ref_set
            if unlisted:
                errors.append(
                    f"Claims cited in text but missing from claim_references: {sorted(unlisted)}"
                )
            uncited = syn_ref_set - text_cited
            if uncited:
                errors.append(
                    f"claim_references not cited in synthesis text: {sorted(uncited)}"
                )

        # 7. Financial sanity
        accounts = sections.get("annual_accounts", {})
        if accounts.get("status") == "available":
            aclaims = accounts.get("claims", {})
            for field in _FINANCIAL_FIELDS:
                if field not in aclaims:
                    continue
                cinfo = aclaims[field]
                val = cinfo.get("value")
                if not _valid_number(val):
                    errors.append(f"Financial field '{field}' must be a finite numeric value")
                if not cinfo.get("currency"):
                    errors.append(f"Financial field '{field}' missing currency indicator")
                if cinfo.get("status") == "available" and not cinfo.get("source_url"):
                    errors.append(f"Financial field '{field}' missing source_url")

        # 8. Derived signals
        signals = envelope.get("derived_signals", {})
        for sname, sdata in signals.items():
            if not isinstance(sdata, dict):
                continue
            for bid in sdata.get("based_on", []) or []:
                if bid not in known_claims:
                    errors.append(
                        f"Derived signal '{sname}' references non-existent claim ID: {bid}"
                    )
            value = sdata.get("value")
            if sname == "yoy_revenue_change" and value is not None and not _valid_number(value):
                errors.append("Derived signal 'yoy_revenue_change' has a non-numeric value")
            if sname == "operating_margin" and value is not None and not _valid_number(value):
                errors.append("Derived signal 'operating_margin' has a non-numeric value")
            if sname == "debt_to_equity" and value is not None and not _valid_number(value):
                errors.append("Derived signal 'debt_to_equity' has a non-numeric value")
            if sname == "negative_equity" and value is not None and not isinstance(value, bool):
                errors.append("Derived signal 'negative_equity' must be boolean")

        return len(errors) == 0, errors

    def validate_batch_file(self, jsonl_path: Union[str, Path]) -> dict[str, Any]:
        """Validate an entire JSONL batch file and return full compliance metrics."""
        path = Path(jsonl_path)
        if not path.exists():
            return {"valid": False, "error": f"File not found: {path}"}

        total = 0
        valid_count = 0
        invalid_count = 0
        all_errors: list[dict[str, Any]] = []

        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                total += 1
                try:
                    envelope = json.loads(clean_line)
                    is_valid, errors = self.validate_envelope(envelope)
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                        all_errors.append({
                            "line": line_no,
                            "orgnr": envelope.get("organisation_number"),
                            "errors": errors,
                        })
                except Exception as e:
                    invalid_count += 1
                    all_errors.append({
                        "line": line_no,
                        "orgnr": "unknown",
                        "errors": [f"JSON Parse Error: {str(e)}"],
                    })

        pass_rate = (valid_count / total * 100) if total > 0 else 0.0

        return {
            "total_envelopes": total,
            "valid_envelopes": valid_count,
            "invalid_envelopes": invalid_count,
            "pass_rate_percentage": round(pass_rate, 2),
            "fully_compliant": invalid_count == 0,
            "errors": all_errors[:25],
        }


if __name__ == "__main__":
    import sys

    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("profiles/profiles_1000.jsonl")
    validator = CitationValidator()
    result = validator.validate_batch_file(target_path)
    print(f"Validation Target: {target_path}")
    print(f"Total Envelopes:   {result['total_envelopes']}")
    print(f"Valid Envelopes:   {result['valid_envelopes']}")
    print(f"Invalid Envelopes: {result['invalid_envelopes']}")
    print(f"Pass Rate:         {result['pass_rate_percentage']}%")
    print(f"Fully Compliant:   {result['fully_compliant']}")
    if result["errors"]:
        print("\nErrors Found:")
        for err in result["errors"]:
            print(f"  Line {err['line']} (orgnr: {err['orgnr']}): {err['errors']}")
    sys.exit(0 if result["fully_compliant"] else 1)
