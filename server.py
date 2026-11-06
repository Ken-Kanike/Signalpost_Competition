"""Signalpost Real-Time API Server.
FastAPI application exposing on-demand company intelligence research,
querying cached profile envelopes, and serving the interactive corporate terminal.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import aiohttp
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from contextlib import asynccontextmanager
from citation_validator import CitationValidator
from config import AgentConfig, default_config
from orchestrator import Orchestrator
from utils import clean_org_number, is_valid_norwegian_orgnr, logger

# Global orchestrator instance
orchestrator = Orchestrator(default_config)
validator = CitationValidator()

PROFILES_JSONL = Path("profiles/profiles_1000.jsonl")
LIVE_PROFILES_JSONL = Path("profiles/live_profiles.jsonl")
REPORT_JSON = Path("profiles/report_1000.json")
INDEX_HTML = Path("index.html")

# In-memory index of profiles for ultra-fast search & filtering
_cached_profiles: list[dict[str, Any]] = []
_org_index: dict[str, dict[str, Any]] = {}


def _upsert_profile(env: dict[str, Any]) -> None:
    orgnr = env.get("organisation_number")
    if not orgnr:
        return
    if orgnr in _org_index:
        old = _org_index[orgnr]
        try:
            idx = next(i for i, p in enumerate(_cached_profiles) if p.get("organisation_number") == orgnr)
            _cached_profiles[idx] = env
        except StopIteration:
            _cached_profiles.insert(0, env)
    else:
        _cached_profiles.insert(0, env)
    _org_index[orgnr] = env


def _load_profile_index():
    global _cached_profiles, _org_index
    if _cached_profiles:
        return
    for path, label in ((PROFILES_JSONL, "base"), (LIVE_PROFILES_JSONL, "live")):
        if not path.exists():
            continue
        logger.info(f"Loading {label} profile index from {path}...")
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            env = json.loads(line)
                            _upsert_profile(env)
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Failed to index {label} profiles: {e}")
    logger.info(f"Indexed {len(_cached_profiles)} profiles in memory.")


def _count_claims(env: dict[str, Any]) -> int:
    count = 0
    for sec_name, sec in (env.get("sections") or {}).items():
        if not isinstance(sec, dict):
            continue
        claims = sec.get("claims")
        if isinstance(claims, dict):
            count += len(claims)
        elif isinstance(claims, list):
            count += len(claims)
        if sec_name == "website":
            if not claims and sec.get("claim_id"):
                count += 1
            count += len(sec.get("social_claims", []) or [])
    return count


def _compute_stats() -> dict[str, Any]:
    _load_profile_index()
    total = len(_cached_profiles)
    success = sum(1 for p in _cached_profiles if p.get("status") == "available")
    failed = total - success
    claim_total = sum(_count_claims(p) for p in _cached_profiles)
    source_total = sum(len(p.get("sources", []) or []) for p in _cached_profiles)

    section_names = (
        "legal_identity",
        "annual_accounts",
        "leadership",
        "workplaces",
        "website",
        "hiring",
        "announcements",
        "news",
    )
    section_availability = {name: 0 for name in section_names}
    registry_listed = 0
    http_verified = 0
    social = 0
    news = 0
    hiring = 0
    announcements = 0
    source_status_counts: dict[str, int] = {}
    dates: list[str] = []

    for profile in _cached_profiles:
        retrieved_at = profile.get("retrieved_at")
        if isinstance(retrieved_at, str) and len(retrieved_at) >= 10:
            dates.append(retrieved_at[:10])
        for name in section_names:
            section = (profile.get("sections") or {}).get(name, {})
            if isinstance(section, dict) and section.get("status") == "available":
                section_availability[name] += 1
        website = (profile.get("sections") or {}).get("website", {})
        if isinstance(website, dict) and website.get("status") == "available":
            if website.get("verification_method") == "registry_listed":
                registry_listed += 1
            else:
                http_verified += 1
            if website.get("social_profiles") or website.get("social_claims"):
                social += 1
        if (profile.get("sections", {}).get("news", {}) or {}).get("status") == "available":
            news += 1
        if (profile.get("sections", {}).get("hiring", {}) or {}).get("status") == "available":
            hiring += 1
        if (profile.get("sections", {}).get("announcements", {}) or {}).get("status") == "available":
            announcements += 1
        for source in profile.get("sources", []) or []:
            key = str(source.get("status_code")) if source.get("status_code") is not None else "unknown"
            source_status_counts[key] = source_status_counts.get(key, 0) + 1

    return {
        "total_companies": total,
        "successful_envelopes": success,
        "failed_envelopes": failed,
        "indexed_count": total,
        "average_claims_per_envelope": round(claim_total / success, 1) if success else 0.0,
        "average_sources_per_envelope": round(source_total / success, 1) if success else 0.0,
        "section_completeness": {
            name: round((count / total) * 100, 1) if total else 0.0
            for name, count in section_availability.items()
        },
        "registry_listed_websites": registry_listed,
        "http_verified_websites": http_verified,
        "profiles_with_social_links": social,
        "profiles_with_news": news,
        "profiles_with_hiring": hiring,
        "profiles_with_announcements": announcements,
        "source_status_counts": source_status_counts,
        "retrieved_range": {
            "earliest": min(dates) if dates else None,
            "latest": max(dates) if dates else None,
        },
        "budget_limit": default_config.max_daily_requests,
        "requests_made": orchestrator.budget_tracker.total_requests_made,
        "within_2000_request_limit": orchestrator.budget_tracker.total_requests_made <= default_config.max_daily_requests,
    }


def _persist_live_profile(env: dict[str, Any]) -> None:
    LIVE_PROFILES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(LIVE_PROFILES_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(env, ensure_ascii=False) + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_profile_index()
    yield


app = FastAPI(
    title="Signalpost Norwegian Corporate Intelligence API",
    version="2.0.0",
    description="Live on-demand research and verified profile intelligence for Norwegian registered entities.",
    lifespan=lifespan,
)

# Enable CORS for external dashboards and integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """System health check and pipeline status."""
    _load_profile_index()
    return {
        "status": "healthy",
        "agent": "Signalpost Autonomous Research Agent",
        "version": "2.0.0",
        "budget_limit": default_config.max_daily_requests,
        "requests_made": orchestrator.budget_tracker.total_requests_made,
        "indexed_profiles": len(_cached_profiles),
    }


@app.get("/api/stats")
async def get_stats():
    """Aggregate live statistics computed from the indexed profiles."""
    return _compute_stats()


@app.get("/api/profiles")
async def get_profiles(
    q: Optional[str] = Query(None, description="Search term for company name or org number"),
    status: Optional[str] = Query(None, description="Filter by status: available, not_found, blocked"),
    has_website: Optional[bool] = Query(None, description="Filter for companies with verified websites"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=100, description="Items per page"),
):
    """Search and paginate pre-compiled company intelligence profiles."""
    _load_profile_index()
    results = _cached_profiles

    if q:
        query = q.strip().lower()
        matches = []
        for profile in results:
            legal = ((profile.get("sections") or {}).get("legal_identity") or {})
            claims = legal.get("claims") or {}
            name = ((claims.get("legal_name") or {}).get("value") or "")
            address = ((claims.get("registered_address") or {}).get("value") or {})
            nace = (claims.get("industry_codes") or {}).get("value") or []
            form = claims.get("legal_form") or {}
            haystack = " ".join(
                [
                    str(profile.get("organisation_number") or ""),
                    str(name),
                    str(form.get("value") or ""),
                    str(form.get("description") or ""),
                    str(address.get("city") or ""),
                    str(address.get("municipality") or ""),
                    str(address.get("postal_code") or ""),
                    " ".join(
                        f"{item.get('code', '')} {item.get('description', '')}"
                        for item in nace
                        if isinstance(item, dict)
                    ),
                ]
            ).lower()
            if query in haystack:
                matches.append(profile)
        results = matches

    if status:
        results = [p for p in results if p.get("status") == status]

    if has_website is not None:
        results = [
            p
            for p in results
            if (p.get("sections", {}).get("website", {}).get("status") == "available")
            == has_website
        ]

    total_count = len(results)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_items = results[start_idx:end_idx]

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 1,
        "items": page_items,
    }


@app.get("/api/profile/{orgnr}")
async def get_profile(orgnr: str):
    """Retrieve intelligence profile for a specific Norwegian organisation number."""
    clean = clean_org_number(orgnr)
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid organization number format")

    _load_profile_index()
    if clean in _org_index:
        return _org_index[clean]

    # Check store directory
    prev = orchestrator.state_store.load_previous_state(clean)
    if prev:
        return prev

    raise HTTPException(status_code=404, detail=f"Company {clean} not found in pre-indexed profiles. Use POST /api/research/{clean} to run live research.")


@app.post("/api/research/{orgnr}")
async def research_company_live(orgnr: str):
    """Run live multi-stage research pipeline for an organization number on-demand."""
    clean = clean_org_number(orgnr)
    if not clean or not is_valid_norwegian_orgnr(clean):
        raise HTTPException(status_code=400, detail="Invalid Norwegian Modulo 11 organization number")

    try:
        timeout = aiohttp.ClientTimeout(total=20.0)
        connector = aiohttp.TCPConnector(limit=5)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            envelope = await orchestrator.process_company(session, clean, remaining_companies=1)

        result_dict = envelope.model_dump()
        if envelope.status == "blocked":
            return JSONResponse(
                status_code=429,
                content={"detail": "Daily request budget reached", "organisation_number": clean},
            )
        _upsert_profile(result_dict)
        _persist_live_profile(result_dict)
        return result_dict
    except Exception as e:
        logger.error(f"Error researching {clean}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")


@app.post("/api/validate")
async def validate_envelope(envelope_data: dict[str, Any]):
    """Validate citation grounding and schema integrity for any company envelope."""
    is_valid, errors = validator.validate_envelope(envelope_data)
    return {
        "is_valid": is_valid,
        "error_count": len(errors),
        "errors": errors,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the interactive Signalpost Corporate Intelligence Terminal."""
    if INDEX_HTML.exists():
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Signalpost Terminal</h1><p>index.html not generated yet.</p>")


if __name__ == "__main__":
    import asyncio
    import uvicorn

    raw_port = os.getenv("PORT")
    target_ports = {8000, 8080}
    if raw_port:
        try:
            target_ports.add(int(raw_port))
        except ValueError:
            pass

    async def _run_all_ports():
        servers = [
            uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=p, log_level="info")).serve()
            for p in sorted(target_ports)
        ]
        await asyncio.gather(*servers)

    asyncio.run(_run_all_ports())
