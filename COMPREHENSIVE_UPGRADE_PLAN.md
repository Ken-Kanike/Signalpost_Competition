# Signalpost — Comprehensive Engineering Upgrade & Action Plan
**Target:** 100/100 Evaluation Score + $500 JBOX Best UX Bonus  
**Submission Deadline:** 7 November, 23:59 IST  
**Document Purpose:** Detailed master plan, architectural specifications, file-by-file code blueprints, and execution prompt for autonomous execution via OpenCode.

---

## 1. Executive Summary & Reviewer Feedback Deconstruction

### 1.1 Reviewer Feedback Analysis (Email 1 — Soham Sinha, Nov 2)
The run was scored on 164 companies reached. The core strengths noted were:
- Summaries cite claim IDs accurately.
- Financial figures specify year (e.g., 2025/latest period) and YoY change.
- Clear reasons provided when sections are unavailable.
- High domain precision (9/10 verified websites correct, e.g., Senja Clean AS with orgnr and Total Apartments AS with Tromsø address).
- Explorer has unified search (name, orgnr, city, NACE), filter pills, sorting, and source/fetch time per claim.

#### Critical Flaws Identified by Reviewer:
1. **False Website Attribution (BQL AS vs. Bergen Quiltelag):**
   - *Problem:* `bql.no` was accepted for **BQL AS** (an Oslo company). In reality, `bql.no` belongs to Bergen Quiltelag (a club in Bergen).
   - *Root Cause:* Name token matching in `website_verifier.py` generated `bql.no` as a candidate domain and accepted it without cross-verifying the registered municipality/city (Oslo vs. Bergen) or verifying the company's full legal name on the page.
   - *Mandatory Fix:* Multi-factor site verification:
     - Candidate domains that match solely on short name tokens ($\le 4$ characters) or tier 3 name matching **must** verify the company's registered city/municipality or postal code on the page, or verify the 9-digit orgnr.
     - If the page explicitly mentions a conflicting Norwegian municipality (e.g. Bergen when registered in Oslo) and lacks the company's orgnr, it **must be rejected**.

2. **Misleading Summary Lines:**
   - *Issue A: Foreign Entities (NUF) & 0 Employees:*
     - A zero employee count on a foreign entity (e.g. NUF - Norsk avdeling av utenlandsk foretak) produced "No registered employees". Foreign companies often register branch entities in Norway where employee counts are tracked in their home country, or the register records 0/null.
     - *Rule:* If employee count is 0 or null, check the entity form (`organisasjonsform`). For NUF, foreign entities, or where `antallAnsatte == 0`, treat it as **unknown / not publicly filed** rather than claiming the company has zero employees.
   - *Issue B: Placeholder NACE Codes ("Uoppgitt (NACE 00.000)"):*
     - "Uoppgitt (NACE 00.000)" was passed directly into the summary and claims.
     - *Rule:* Treat NACE `00.000` or description `Uoppgitt` / `Ikke oppgitt` as **unknown / unassigned**. Do not emit misleading claims or include them in the synthesis.

3. **Viewer Layout & Clean Start 0-Company Failure:**
   - *Issue A: Fixed Full-Height Screen with No Mobile Layout:*
     - `height: 100vh; overflow: hidden` breaks on mobile and tablet screens, clipping content with no vertical scroll.
     - *Requirement:* Fully responsive layout with mobile breakpoints (`@media (max-width: 768px)`), collapsible drawer/bottom navigation, stacked comparison, and touch-friendly controls.
   - *Issue B: Hosted Copy Showed 0 Companies on Clean Start:*
     - In hosted static environments (e.g. GitHub Pages or static host), if backend API is not running or if `profiles_1000.jsonl` was not embedded into the static bundle or fetched via a reliable relative path, `RAW_DATA` defaulted to empty array `[]`.
     - *Requirement:* Resilient bootstrapping: embed a baseline verified dataset or include an automatic async fetch fallback to `./profiles/profiles_1000.jsonl` / `./output/envelopes.jsonl` / `./data.json` so the viewer loads instantaneously with 1,000 companies from a completely clean start on any static host.

4. **Missing Social Links & Corporate News (Going Further):**
   - *Feedback:* "You published no social pages or news. Once a site is confirmed, read its footer for social links and its news section, and check each page names the company."
   - *Requirement:*
     - **Social Links:** Specifically parse the footer (`<footer>` or bottom 25% of DOM) of verified websites for Facebook, LinkedIn, Instagram, X/Twitter, and YouTube. Strictly verify that the company's name or distinctive token is present in the handle or link.
     - **News Section:** Identify news/press pages (`/nyheter`, `/aktuelt`, `/pressemeldinger`, `/blogg`), extract dated articles, and ensure each page/article names the company before assigning a claim ID.

---

### 1.2 Reviewer Feedback Analysis (Email 2 — $500 JBOX UX Bonus)
The bonus prize ($250 / $150 / $100) is awarded based on UX evaluated on laptop and phone:
- **Core User Journeys:**
  1. **Find a company:** Instant omni-search by name, 9-digit orgnr, city, municipality, and NACE code, plus filter pills and sorting.
  2. **Compare two companies:** A dedicated side-by-side comparison mode allowing users to pick two companies and compare legal form, workforce, revenue, operating profit, equity, solvency status, and verified website.
  3. **Check a source:** Click any factual claim chip (e.g., `[c001]`, `[c004]`) to open an interactive Source Inspection Modal showing the exact source URL, HTTP status, retrieval timestamp, backed claim IDs, and audited registry register.
  4. **Responsive UX on Laptop and Phone:** Works seamlessly without horizontal clipping or broken scrolling on mobile devices.

---

## 2. Architectural Blueprint & Technical Specifications

```
                     Signalpost Autonomous Architecture
                     
  [ Input Target: Orgnr or targets_1000.jsonl ]
                       │
                       ▼
            ┌──────────────────────┐
            │ Orchestrator Pipeline│ ◄── Dynamic Budget Tracker (≤2,000 req)
            └──────────┬───────────┘
                       │
     ┌─────────────────┼──────────────────┐
     ▼                 ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐
│ BRREG API    │ │Kunngjøringer │ │ 3-Tier Website Verifier  │
│ - Enheter    │ │- Announcements││ - Tier 0: BRREG Listed   │
│ - Roller     │ └──────────────┘ │ - Tier 1: Orgnr on Page  │
│ - Regnskap   │                  │ - Tier 2: Name + City    │
│ - Underenhet │                  │ - Bergen Quiltelag Guard │
└──────┬───────┘                  └────────────┬─────────────┘
       │                                       │ (Verified site only)
       │                                       ▼
       │                          ┌──────────────────────────┐
       │                          │ Web Enrichment & News    │
       │                          │ - Footer Social (Named)  │
       │                          │ - News (With Date & Name)│
       │                          └────────────┬─────────────┘
       └─────────────────┬─────────────────────┘
                         ▼
             ┌─────────────────────────┐
             │ Normalizer & Claims     │
             │ - c001, c002 Sequential │
             │ - NACE 00.000 Filter    │
             │ - NUF/Zero Emp Filter   │
             └───────────┬─────────────┘
                         ▼
             ┌─────────────────────────┐
             │ Derived Signals Engine  │
             │ - YoY Revenue Change    │
             │ - Negative Equity Flag  │
             │ - Workforce Scale (NUF) │
             └───────────┬─────────────┘
                         ▼
             ┌─────────────────────────┐
             │ Verifiable Synthesizer  │
             │ - Grounded [cXXX] Chips │
             │ - Zero Hallucinations   │
             └───────────┬─────────────┘
                         ▼
             ┌─────────────────────────┐
             │ State Store & Diffing   │
             └───────────┬─────────────┘
                         ▼
        ┌───────────────────────────────────┐
        │ Outputs & Delivery                │
        │ 1. envelopes.jsonl                │
        │ 2. report.json (telemetry)        │
        │ 3. index.html (Responsive Viewer) │
        │    - Find Company                 │
        │    - Compare Two Companies        │
        │    - Check Source Modal           │
        │    - Mobile + Laptop Layout       │
        └───────────────────────────────────┘
```

---

## 3. File-by-File Detailed Fix Specifications

### 3.1 `website_verifier.py`
#### Exact Problem Addressed:
`bql.no` is Bergen Quiltelag (club in Bergen), whereas BQL AS is an Oslo company. The candidate generator derived `bql.no` from the name token `bql` and verified it without checking geographic location or company name match.

#### Required Implementations:
1. **Pass Entity Metadata into Verification:**
   Ensure `enhet_data` includes `forretningsadresse` and `postadresse` to extract:
   - `registered_city`: e.g. "Oslo"
   - `registered_municipality`: e.g. "Oslo"
   - `registered_postal_code`: e.g. "0150"
   - `legal_form_code`: e.g. "AS"
2. **City & Municipality Cross-Validation (`_check_location_match`):**
   - When a site does not have the 9-digit orgnr (Tier 1), it cannot be accepted on a name match alone if the site mentions a different major Norwegian municipality.
   - For example: if target company is in **Oslo**, but the site's footer/contact page prominently mentions **Bergen** and does not mention **Oslo** or the org number, reject the site.
3. **Distinctive Name Token Length Guard:**
   - Short acronyms ($\le 3$ characters like `BQL`) cannot be accepted via synthetic domain generation (`bql.no`) without either:
     - 9-digit orgnr match on page (Tier 1), OR
     - Exact match of the full company name (e.g. "BQL AS") in `<title>`, `<h1>`, or footer text **and** location match.
4. **Negative Keyword Guard for Clubs and Associations:**
   - Detect if the site title, header, or footer contains words like `quiltelag`, `idrettslag`, `forening`, `klubb`, `borettslag`, `sameie` when the target is an `AS` (Aksjeselskap) or commercial business.

---

### 3.2 `normalizer.py` & `synthesizer.py`
#### Exact Problem Addressed:
1. "No registered employees" emitted for large foreign entities (NUF).
2. "Uoppgitt (NACE 00.000)" passed directly through into claims and synthesis.

#### Required Implementations in `normalizer.py`:
1. **Placeholder NACE Code Filter:**
   ```python
   # Filter out placeholder or unassigned NACE codes
   nace = data.get("naeringskode1")
   if nace:
       nace_code = (nace.get("kode") or "").strip()
       nace_desc = (nace.get("beskrivelse") or "").strip()
       if nace_code not in ("00.000", "00", "") and nace_desc.lower() not in ("uoppgitt", "ikke oppgitt", "unspecified"):
           cid = self._next_claim_id()
           self._register_source(source_url, cid)
           claims["industry_codes"] = {
               "value": [{"code": nace_code, "description": normalize_norwegian_text(nace_desc)}],
               "claim_id": cid,
               "source_url": source_url,
               "retrieved_date": today,
               "status": "available",
           }
   ```
2. **NUF & Zero Employee Normalization:**
   ```python
   orgform_code = (data.get("organisasjonsform", {}).get("kode") or "").upper()
   emp_count = data.get("antallAnsatte")
   
   # For foreign companies (NUF) or where employee count is not registered or 0
   is_foreign = orgform_code in ("NUF", "FLI", "UTL")
   if emp_count is None or (emp_count == 0 and is_foreign):
       claims["employee_count"] = {
           "value": None,
           "status": "not_applicable" if is_foreign else "not_available",
           "reason": "Employee count not registered in Norway (foreign entity / NUF)" if is_foreign else "No registered employees reported",
           "claim_id": self._next_claim_id(),
           "source_url": source_url,
           "retrieved_date": today,
       }
   else:
       cid = self._next_claim_id()
       self._register_source(source_url, cid)
       claims["employee_count"] = {
           "value": emp_count,
           "claim_id": cid,
           "source_url": source_url,
           "retrieved_date": today,
           "status": "available",
       }
   ```

#### Required Implementations in `synthesizer.py`:
1. **Sentence 1 (Industry NACE):**
   - Check if `industry_codes` exists and is valid. If omitted, omit the NACE clause entirely rather than saying "operating within Uoppgitt (NACE 00.000)".
2. **Sentence 2 (Workforce):**
   - If `emp_count` is `None` or marked `not_applicable`, write:
     `"Workforce size is not publicly registered in Norwegian registers (foreign enterprise branch)."` or omit workforce claim if unverified.
   - Never write "The enterprise employs 0 workers" for large multinational NUFs.

---

### 3.3 `collectors/web_enricher.py` (Social Link Extraction)
#### Exact Problem Addressed:
"You published no social pages... Once a site is confirmed, read its footer for social links... and check each page names the company."

#### Required Implementations:
1. **Targeted Footer Parsing:**
   - Find footer elements: `soup.find_all(["footer", "div", "section"], class_=re.compile(r"footer|bottom|soc", re.I))` or parse `<a>` tags with `href` containing social domains.
2. **Social Profile Platforms:**
   - Supported platforms: LinkedIn, Facebook, Instagram, X (Twitter), YouTube, GitHub.
3. **Company Name Verification in Social URL & Anchor:**
   - Verify that the social handle/slug or anchor title contains the company name token (excluding generic agency links like `facebook.com/wix`, `wordpress`, `webdesign`, `cookiebot`).
4. **Store in Section Website:**
   - Populate `social_profiles: list[dict[str, str]]` with platform, URL, and confirmed handle.

---

### 3.4 `collectors/news_collector.py`
#### Exact Problem Addressed:
"Once a site is confirmed, read... its news section, and check each page names the company."

#### Required Implementations:
1. **Feed & HTML News Discovery:**
   - Probe RSS/Atom feeds and HTML pages matching `/nyheter`, `/aktuelt`, `/pressemeldinger`, `/news`.
2. **Verify Article Names the Company:**
   - For every candidate article headline or snippet:
     - Check that the text contains the target company's name or core distinctive token ($\ge 3$ chars).
     - Require explicit publication date (e.g. `<time datetime="...">` or valid RFC/ISO date).
     - Filter out generic corporate links or marketing fluff ("Les mer", "Nyheter", "Våre tjenester").
3. **Register Sources & Claim IDs:**
   - Each confirmed news item receives a dedicated claim ID backed by the article URL.

---

### 3.5 `viewer_generator.py` & `index.html` (The UX & JBOX Bonus Requirements)
#### Exact Problems Addressed:
1. Fixed full-height screen (`100vh; overflow: hidden`) with no mobile/phone layout.
2. Hosted copy showed 0 companies on clean start.
3. JBOX Bonus evaluation criteria: **Find a company**, **Compare two**, **Check a source**, on **laptop and phone**.

#### Required Implementations:

1. **Clean-Start Data Resilience (Fix 0-Company Bug):**
   - In `viewer_generator.py`, embed the dataset directly as `const RAW_DATA = [...]` (JSON-encoded).
   - In addition, add an asynchronous boot check:
     ```javascript
     if (!RAW_DATA || RAW_DATA.length === 0) {
       // Fetch relative data files
       fetch('profiles/profiles_1000.jsonl')
         .then(r => r.text())
         .then(txt => parseAndLoadJSONL(txt))
         .catch(() => {
           fetch('output/envelopes.jsonl')
             .then(r => r.text())
             .then(txt => parseAndLoadJSONL(txt));
         });
     }
     ```
   - This guarantees that whether opened locally via `file://`, hosted statically on GitHub Pages, or served via FastAPI, the terminal boots with all 1,000 companies.

2. **Responsive Mobile & Laptop Layout:**
   - Replace fixed `100vh` and rigid two-column grid with a responsive container:
     - On desktop (`min-width: 1024px`): Split-pane Explorer (sidebar list 380px + main stage 1fr).
     - On tablet (`768px - 1023px`): Collapsible drawer or toggle between feed and details.
     - On mobile (`max-width: 767px`):
       - Full-width stacked layout.
       - Mobile bottom navigation bar: **Find / Explorer**, **Compare (2)**, **Live Studio**, **Audit**.
       - Selecting a company in Explorer automatically scrolls to or switches to the Details view with a "Back to List" button.
       - Tables wrap with horizontal scroll (`overflow-x: auto`) and touch card layouts.

3. **Feature: "Compare Two Companies" Mode ($500 JBOX UX Feature):**
   - Add a dedicated **Compare** button on each company card and a "Compare" tab in the navigation.
   - Users can select Company A and Company B (or pick from recent searches / search within comparison view).
   - Side-by-side comparison table showing:
     - Legal Name & Status
     - Organization Number & City
     - NACE Industry Sector
     - Workforce Scale & Employee Count
     - Revenue & Operating Profit (with YoY trend)
     - Total Equity & Solvency Status (Negative Equity flag)
     - Verified Website with direct link
     - Completeness & Confidence Score
   - Side-by-side comparison works seamlessly on both mobile (swipable or stacked) and laptop (2 columns).

4. **Feature: "Check a Source" Interactive Inspector:**
   - Clicking any `[cXXX]` chip anywhere in the summary or tables opens a **Source Provenance Modal**:
     - Shows the Claim ID (e.g. `c001`).
     - Shows the Claimed Fact Value.
     - Shows the Exact Source URL (clickable hyperlink).
     - Shows the Register Authority (e.g., *Brønnøysundregistrene - Enhetsregisteret*).
     - Shows the Retrieval Timestamp & HTTP Status Code.
     - Shows all other facts backed by this exact same source URL.

---

## 4. Comprehensive Testing & Verification Plan

### Test Suite Additions in `tests/test_reviewer_fixes.py`:
1. `test_bql_oslo_vs_bergen_rejected`:
   - Simulate BQL AS (Oslo orgnr) testing `bql.no` (which mentions Bergen and quiltelag). Must return `status: "not_available"`.
2. `test_nace_00000_placeholder_filtered`:
   - Pass entity data with NACE `00.000` or `Uoppgitt`. Assert that `industry_codes` is not emitted and synthesis does not contain "00.000" or "Uoppgitt".
3. `test_nuf_zero_employees_handled_as_unknown`:
   - Pass NUF entity with `antallAnsatte: 0`. Assert synthesis says workforce not registered in Norway, not "No registered employees".
4. `test_footer_social_links_extraction`:
   - Provide HTML with footer containing valid company LinkedIn/Facebook links. Assert social profiles extracted with name verification.
5. `test_news_collector_company_name_validation`:
   - Feed news items. Assert articles that don't name the company are discarded.
6. `test_viewer_clean_start_has_companies`:
   - Verify generated `index.html` has non-zero dataset embedded and loads without JavaScript exceptions.

---

## 5. Master Prompt for OpenCode Execution

```markdown
================================================================================
OPENCODE MASTER EXECUTION INSTRUCTION: SIGNALPOST UPGRADE & PRODUCTION POLISH
================================================================================

You are an expert systems engineer and frontend architect. Your mission is to implement all required fixes and features detailed in `COMPREHENSIVE_UPGRADE_PLAN.md` for the Signalpost repository.

### STRICT RULES:
1. NO MOCKING OR FAKING: Every API integration, verification check, normalizer rule, and UI control must be real, functional, and fully grounded in code.
2. DO NOT BREAK EXISTING PASSING TESTS: Run `python -m pytest tests/` before and after changes. All tests must pass 100%.
3. STRICT BUDGET COMPLIANCE: Outbound request limit is ≤2,000 requests across 1,000 companies.

### TASK 1: Fix Website Verification False Positives (`website_verifier.py`)
- In `verify_website`, extract `registered_city` and `registered_municipality` from `enhet_data`.
- Implement `_check_location_mismatch(html, registered_city, registered_municipality)`.
- If candidate website is based on short name tokens (e.g. 'bql') and does not have the 9-digit orgnr, reject if it mentions a conflicting major Norwegian municipality or club keywords ('quiltelag', 'idrettslag', 'klubb') without mentioning the company's city or full name.
- Write unit tests in `tests/test_reviewer_fixes.py` verifying `bql.no` is rejected for BQL AS.

### TASK 2: Clean Up Summaries & Normalizer (`normalizer.py` & `synthesizer.py`)
- In `normalizer.py`:
  * If NACE is `00.000` or description is `Uoppgitt`/`Ikke oppgitt`, omit `industry_codes` from claims.
  * If entity is a foreign enterprise (`NUF`) or employee count is 0/None, do not claim '0 registered employees'. Mark as unknown or foreign-registered.
- In `synthesizer.py`:
  * Never emit "Uoppgitt (NACE 00.000)".
  * For NUF/foreign entities with 0 or missing employees, state that Norwegian workforce size is not registered, or omit the workforce claim.

### TASK 3: Enrich Footer Social Links & News with Name Verification
- In `collectors/web_enricher.py`:
  * Specifically parse the footer (`<footer>` or footer classes) of verified websites for LinkedIn, Facebook, Instagram, Twitter/X, and YouTube.
  * Verify that the social handle/path contains company name tokens.
- In `collectors/news_collector.py`:
  * When scraping news from verified sites, ensure the headline or summary contains the company name.

### TASK 4: Overhaul HTML Viewer (`viewer_generator.py`) for Mobile, Comparison, and Source Inspector
- Ensure `RAW_DATA` is embedded directly from `profiles/profiles_1000.jsonl` with an async fallback fetch so hosted static copies NEVER show 0 companies.
- Mobile Responsive CSS:
  * Remove rigid `100vh; overflow:hidden` on small screens.
  * Add `@media (max-width: 768px)` rules for fluid scrolling, touch navigation, and collapsible sections.
  * Add a mobile navigation bar (Explorer, Compare, Studio, Audit).
- Feature 1: "Compare Two Companies" Mode ($500 JBOX UX requirement):
  * Allow users to select two companies side-by-side.
  * Compare Legal Identity, Financials (Revenue, Profit, Equity), Workforce, Website, and Solvency status.
- Feature 2: "Check a Source" Interactive Inspector:
  * Clicking any `[cXXX]` chip opens a modal showing the exact source URL, HTTP status, retrieval date, register name, and backed claims.

### TASK 5: Regenerate `index.html` & Validate
- Run `python generate_1000_profiles.py` or `python viewer_generator.py profiles/profiles_1000.jsonl index.html`.
- Run `python -m pytest tests/ -v`.
- Ensure all tests pass with 0 errors.
================================================================================
```

---

## 6. Verification & Delivery Checklist
- [ ] `bql.no` false positive blocked via city + club keyword guard.
- [ ] Placeholder `NACE 00.000` completely excluded from normalizer and synthesis.
- [ ] Foreign entity / NUF zero employee count handled as unknown / foreign registered.
- [ ] Footer social links extracted with strict company name matching.
- [ ] News articles require publish dates and company name confirmation.
- [ ] Viewer boots cleanly with 1,000 companies on any static or cloud host (0-company bug eradicated).
- [ ] Responsive layout on phone (375px - 768px) and laptop (1024px+).
- [ ] Side-by-side comparison feature fully interactive.
- [ ] "Check a source" modal highlights exact backing URL and retrieval date for every claim chip.
- [ ] All pytest unit tests pass with zero warnings or errors.

