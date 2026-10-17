"""Utility helpers for rate-limiting, budget tracking, Unicode normalization, and logging."""

import asyncio
import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.logging import RichHandler

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
)
logger = logging.getLogger("signalpost")


def normalize_norwegian_text(text: Optional[str]) -> str:
    """Normalize text using Unicode NFC format, preserving Norwegian ÆØÅ æøå."""
    if not text:
        return ""
    # NFC normalization ensures consistent representation of combined characters
    normalized = unicodedata.normalize("NFC", str(text))
    # Strip excessive whitespace while preserving inner punctuation
    return " ".join(normalized.split())


def clean_org_number(orgnr_input: Any) -> str:
    """Clean and validate a 9-digit Norwegian organisation number."""
    if orgnr_input is None:
        return ""
    digits = re.sub(r"[^\d]", "", str(orgnr_input))
    if len(digits) == 9:
        return digits
    return digits.strip()


def is_valid_norwegian_orgnr(orgnr: str) -> bool:
    """Validate 9-digit Norwegian organisation number using Modulo 11 checksum.
    Weights: 3, 2, 7, 6, 5, 4, 3, 2
    """
    clean = clean_org_number(orgnr)
    if len(clean) != 9 or not clean.isdigit():
        return False
    
    weights = [3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(clean[i]) * weights[i] for i in range(8))
    remainder = total % 11
    
    if remainder == 0:
        control_digit = 0
    elif remainder == 1:
        # Remainder 1 cannot yield a valid control digit (would be 10)
        return False
    else:
        control_digit = 11 - remainder
        
    return int(clean[8]) == control_digit


from datetime import datetime, timezone

def get_current_date_str() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_current_iso_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PerHostRateLimiter:
    """Ensures no single host is requested faster than min_interval_sec."""

    def __init__(self, min_interval_sec: float = 0.5):
        self.min_interval_sec = min_interval_sec
        self.last_request_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, url: str) -> None:
        host = urlparse(url).netloc.lower() or "default"
        async with self._lock:
            now = time.monotonic()
            last_time = self.last_request_time.get(host, 0.0)
            elapsed = now - last_time
            if elapsed < self.min_interval_sec:
                sleep_duration = self.min_interval_sec - elapsed
                await asyncio.sleep(sleep_duration)
            self.last_request_time[host] = time.monotonic()


class RequestBudgetTracker:
    """Tracks and enforces outbound HTTP requests within daily competition limits."""

    def __init__(self, max_daily_budget: int = 2000, default_cap: int = 14, min_cap: int = 2):
        self.max_daily_budget = max_daily_budget
        self.default_cap = default_cap
        self.min_cap = min_cap
        self.total_requests_made = 0
        self.start_time = time.monotonic()
        self._lock = asyncio.Lock()

    async def record_request(self) -> bool:
        async with self._lock:
            if self.total_requests_made >= self.max_daily_budget:
                return False
            self.total_requests_made += 1
            return True

    def get_dynamic_cap(self, remaining_companies: int) -> int:
        """Dynamically compute request budget for the next company."""
        if remaining_companies <= 0:
            return self.default_cap
        remaining_budget = max(0, self.max_daily_budget - self.total_requests_made)
        proportional_cap = remaining_budget // remaining_companies
        # Clamp between min_cap and default_cap
        allocated = max(self.min_cap, min(self.default_cap, proportional_cap))
        return allocated

    def get_elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time

    def is_budget_depleted(self) -> bool:
        return self.total_requests_made >= self.max_daily_budget


class FixtureManager:
    """Manages offline fixture recording and replay for deterministic testing."""

    def __init__(self, record_dir: Optional[str] = None, replay_dir: Optional[str] = None):
        self.record_dir = Path(record_dir) if record_dir else None
        self.replay_dir = Path(replay_dir) if replay_dir else None

    def is_replaying(self) -> bool:
        return self.replay_dir is not None and self.replay_dir.exists()

    def is_recording(self) -> bool:
        return self.record_dir is not None

    def get_fixture_path(self, orgnr: str, endpoint_name: str) -> Path:
        base = self.replay_dir if self.is_replaying() else self.record_dir
        if not base:
            base = Path("tests/fixtures")
        return base / orgnr / f"{endpoint_name}.json"

    def load_fixture(self, orgnr: str, endpoint_name: str) -> Optional[Any]:
        if not self.is_replaying():
            return None
        path = self.get_fixture_path(orgnr, endpoint_name)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading fixture {path}: {e}")
        return None

    def save_fixture(self, orgnr: str, endpoint_name: str, data: Any) -> None:
        if not self.is_recording():
            return
        path = self.get_fixture_path(orgnr, endpoint_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Error saving fixture {path}: {e}")
