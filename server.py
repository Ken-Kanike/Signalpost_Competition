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
REPORT_JSON = Path("profiles/report_1000.json")
INDEX_HTML = Path("index.html")

# In-memory index of profiles for ultra-fast search & filtering
_cached_profiles: list[dict[str, Any]] = []
_org_index: dict[str, dict[str, Any]] = {}


def _load_profile_index():
    global _cached_profiles, _org_index
    if _cached_profiles:
        return
    if PROFILES_JSONL.exists():
        logger.info(f"Loading profile index from {PROFILES_JSONL}...")
        try:
            with open(PROFILES_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            env = json.loads(line)
                            orgnr = env.get("organisation_number")
                            if orgnr:
                                _cached_profiles.append(env)
                                _org_index[orgnr] = env
                        except Exception:
                            pass
            logger.info(f"Indexed {len(_cached_profiles)} profiles in memory.")
        except Exception as e:
            logger.error(f"Failed to index profiles: {e}")


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
    """Retrieve aggregate completeness, compliance, and telemetry stats."""
    if REPORT_JSON.exists():
        try:
            with open(REPORT_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read report file: {e}")

    # Fallback compute from indexed profiles
    _load_profile_index()
    total = len(_cached_profiles)
    return {
        "total_companies": total,
        "successful_envelopes": total,
        "within_2000_request_limit": orchestrator.budget_tracker.total_requests_made <= 2000,
        "indexed_count": total,
    }


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
        results = [
            p
            for p in results
            if query in p.get("organisation_number", "").lower()
            or query
            in (
                p.get("sections", {})
                .get("legal_identity", {})
                .get("claims", {})
                .get("legal_name", {})
                .get("value", "")
                or ""
            ).lower()
        ]

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
        # Add to in-memory index
        global _cached_profiles, _org_index
        _org_index[clean] = result_dict
        if not any(p.get("organisation_number") == clean for p in _cached_profiles):
            _cached_profiles.insert(0, result_dict)

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
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
