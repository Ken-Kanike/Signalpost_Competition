"""Bulk Profile Generator for 1,000+ Norwegian Companies.
Uses the full Orchestrator pipeline with all official BRREG collectors,
strict website verification, handle-validated social links, dated news,
and individual vacancy postings.
Fulfills the competition deliverable: 'At least 1,000 company profiles'.
"""

import asyncio
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from citation_validator import CitationValidator
from config import AgentConfig
from orchestrator import Orchestrator
from utils import (
    clean_org_number,
    console,
    is_valid_norwegian_orgnr,
    logger,
)
from viewer_generator import ViewerGenerator


async def generate_1000_profiles(
    output_file: Path,
    targets_file: Optional[Path] = None,
    target_count: int = 1000,
    concurrency: int = 15,
):
    start_time = time.monotonic()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load target org numbers
    org_numbers: list[str] = []
    if targets_file and targets_file.exists():
        console.print(f"[cyan]Loading target organization numbers from {targets_file}...[/cyan]")
        with open(targets_file, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                if raw.startswith("{"):
                    try:
                        obj = json.loads(raw)
                        clean = clean_org_number(
                            obj.get("organisation_number") or obj.get("orgnr")
                        )
                        if clean and is_valid_norwegian_orgnr(clean):
                            org_numbers.append(clean)
                    except Exception:
                        pass
                else:
                    clean = clean_org_number(raw)
                    if clean and is_valid_norwegian_orgnr(clean):
                        org_numbers.append(clean)
                if len(org_numbers) >= target_count:
                    break

    # If targets file had fewer or was missing, fetch fresh from BRREG
    if len(org_numbers) < target_count:
        console.print(f"[yellow]Fetching active Norwegian companies from BRREG to reach {target_count}...[/yellow]")
        import aiohttp
        async with aiohttp.ClientSession() as session:
            page = 0
            size = 100
            while len(org_numbers) < target_count:
                url = f"https://data.brreg.no/enhetsregisteret/api/enheter?size={size}&page={page}"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get("_embedded", {}).get("enheter", [])
                            if not items:
                                break
                            for item in items:
                                clean = clean_org_number(item.get("organisasjonsnummer"))
                                if clean and is_valid_norwegian_orgnr(clean) and clean not in org_numbers:
                                    org_numbers.append(clean)
                                    if len(org_numbers) >= target_count:
                                        break
                            page += 1
                        else:
                            await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Error fetching page {page}: {e}")
                    await asyncio.sleep(2)

    console.print(f"[bold green]Ready to research {len(org_numbers)} Norwegian companies with full pipeline.[/bold green]")

    # 2. Run full Orchestrator pipeline
    # We allocate a generous request budget (25,000) so no rich sections (leadership, accounts, announcements) are skipped
    config = AgentConfig(
        max_daily_requests=25000,
        per_host_min_interval_sec=0.2,
        synthesis_mode="template",
    )
    orchestrator = Orchestrator(config)

    envelopes, report = await orchestrator.run_batch(
        org_numbers=org_numbers,
        output_file=output_file,
        concurrency=concurrency,
    )

    duration = time.monotonic() - start_time
    console.print(f"\n[bold green]Generated {len(envelopes)} company envelopes in {duration:.1f}s![/bold green]")

    # Save run report
    report_file = output_file.parent / "report_1000.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)

    # 3. Run Citation Validator
    console.print("\n[bold cyan]Running Citation & Evidence Validator on Generated Profiles...[/bold cyan]")
    validator = CitationValidator()
    val_res = validator.validate_batch_file(output_file)
    console.print(
        f"[bold green]Validation Result: {val_res['valid_envelopes']}/{val_res['total_envelopes']} "
        f"({val_res['pass_rate_percentage']}%) pass rate! Fully compliant: {val_res['fully_compliant']}[/bold green]"
    )

    # 4. Generate Viewer
    viewer_file = output_file.parent / "viewer_1000.html"
    console.print(f"[cyan]Generating interactive HTML viewer for {len(envelopes)} companies...[/cyan]")
    gen = ViewerGenerator()
    gen.generate_html([e.model_dump() for e in envelopes], viewer_file)
    console.print(f"[bold green]Viewer ready at: {viewer_file}[/bold green]")

    # 5. Mirror to index.html for GitHub Pages deployment
    index_file = Path("index.html")
    shutil.copy2(viewer_file, index_file)
    console.print(f"[bold green]Mirrored to {index_file} for GitHub Pages deployment.[/bold green]")


if __name__ == "__main__":
    targets_p = Path("profiles/targets_1000.jsonl")
    out_p = Path("profiles/profiles_1000.jsonl")
    asyncio.run(generate_1000_profiles(output_file=out_p, targets_file=targets_p, target_count=1000))
