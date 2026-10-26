"""Normalizer & Claim ID Assignment Engine.
Transforms heterogeneous raw API/scrape data into auditable, schema-compliant
sections with sequential claim IDs (c001, c002, ...) and explicit source provenance.
"""

from typing import Any, Optional
from models import (
    Claim,
    SectionAnnouncements,
    SectionAnnualAccounts,
    SectionHiring,
    SectionLeadership,
    SectionLegalIdentity,
    SectionNews,
    SectionWebsite,
    SectionWorkplaces,
    SourceRecord,
)
from utils import (
    clean_org_number,
    get_current_date_str,
    normalize_norwegian_text,
)


class Normalizer:
    """Assigns deterministic claim IDs and formats all company profile sections."""

    def __init__(self):
        self.claim_counter = 0
        self.sources_map: dict[str, set[str]] = {}  # url -> set of claim_ids

    def _next_claim_id(self) -> str:
        self.claim_counter += 1
        return f"c{self.claim_counter:03d}"

    def _register_source(self, url: Optional[str], claim_id: str) -> None:
        if url:
            if url not in self.sources_map:
                self.sources_map[url] = set()
            self.sources_map[url].add(claim_id)

    def normalize(
        self,
        orgnr: str,
        enhet_raw: dict[str, Any],
        roller_raw: dict[str, Any],
        regnskap_raw: dict[str, Any],
        underenheter_raw: dict[str, Any],
        announcements_raw: dict[str, Any],
        website_raw: dict[str, Any],
        web_enrichment_raw: dict[str, Any],
        jobs_raw: dict[str, Any],
        news_raw: Optional[dict[str, Any]] = None,
        proff_raw: Optional[dict[str, Any]] = None,
    ) -> tuple[dict[str, Any], list[SourceRecord]]:
        """Normalize all collected raw data into typed envelope sections."""
        self.claim_counter = 0
        self.sources_map = {}
        today = get_current_date_str()
        clean_org = clean_org_number(orgnr)

        sections: dict[str, Any] = {}

        # 1. Legal Identity Section
        sections["legal_identity"] = self._normalize_legal_identity(
            enhet_raw, clean_org, today
        )

        # 2. Annual Accounts Section
        sections["annual_accounts"] = self._normalize_annual_accounts(
            regnskap_raw, clean_org, today
        )

        # 3. Leadership Section
        sections["leadership"] = self._normalize_leadership(
            roller_raw, clean_org, today, proff_raw=proff_raw
        )

        # 4. Workplaces Section
        sections["workplaces"] = self._normalize_workplaces(
            underenheter_raw, clean_org, today
        )

        # 5. Website Section
        sections["website"] = self._normalize_website(
            website_raw, web_enrichment_raw, clean_org, today
        )

        # 6. Hiring Section
        sections["hiring"] = self._normalize_hiring(jobs_raw, clean_org, today)

        # 7. Announcements Section
        sections["announcements"] = self._normalize_announcements(
            announcements_raw, clean_org, today
        )

        # 8. News Section
        sections["news"] = self._normalize_news(news_raw or {}, clean_org, today)

        # Build Source Records
        source_records: list[SourceRecord] = []
        for url, claims_set in self.sources_map.items():
            stype = "api" if "data.brreg.no" in url else "website"
            source_records.append(
                SourceRecord(
                    url=url,
                    type=stype,
                    retrieved_date=today,
                    claims_backed=sorted(list(claims_set)),
                )
            )

        return sections, source_records

    def _normalize_legal_identity(
        self, enhet_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        data = enhet_raw.get("data")
        source_url = enhet_raw.get("url") or f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"

        if not data:
            return {
                "status": "not_available",
                "claims": {},
                "reason": enhet_raw.get("error", "Entity not found in Enhetsregisteret"),
            }

        claims: dict[str, Any] = {}

        # Legal name
        cid = self._next_claim_id()
        self._register_source(source_url, cid)
        claims["legal_name"] = {
            "value": normalize_norwegian_text(data.get("navn")),
            "claim_id": cid,
            "source_url": source_url,
            "retrieved_date": today,
            "status": "available",
        }

        # Legal form (organisasjonsform)
        orgform = data.get("organisasjonsform", {})
        cid = self._next_claim_id()
        self._register_source(source_url, cid)
        claims["legal_form"] = {
            "value": orgform.get("kode"),
            "description": normalize_norwegian_text(orgform.get("beskrivelse")),
            "claim_id": cid,
            "source_url": source_url,
            "retrieved_date": today,
            "status": "available",
        }

        # Registration date
        reg_date = data.get("registreringsdatoEnhetsregisteret")
        if reg_date:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            claims["incorporation_date"] = {
                "value": reg_date,
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        # Address
        addr = data.get("forretningsadresse") or data.get("postadresse")
        if addr:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            streets = addr.get("adresse", [])
            street_val = ", ".join(streets) if isinstance(streets, list) else str(streets)
            claims["registered_address"] = {
                "value": {
                    "street": normalize_norwegian_text(street_val),
                    "postal_code": addr.get("postnummer"),
                    "city": normalize_norwegian_text(addr.get("poststed")),
                    "municipality": normalize_norwegian_text(addr.get("kommune")),
                    "country": addr.get("land", "Norge"),
                },
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        # Industry codes (NACE)
        nace = data.get("naeringskode1")
        if nace:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            claims["industry_codes"] = {
                "value": [
                    {
                        "code": nace.get("kode"),
                        "description": normalize_norwegian_text(nace.get("beskrivelse")),
                    }
                ],
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        # Employees
        emp_count = data.get("antallAnsatte")
        cid = self._next_claim_id()
        self._register_source(source_url, cid)
        claims["employee_count"] = {
            "value": emp_count if emp_count is not None else 0,
            "claim_id": cid,
            "source_url": source_url,
            "retrieved_date": today,
            "status": "available",
        }

        # Insolvency / Liquidation flags
        cid = self._next_claim_id()
        self._register_source(source_url, cid)
        claims["is_bankrupt"] = {
            "value": bool(data.get("konkurs", False)),
            "claim_id": cid,
            "source_url": source_url,
            "retrieved_date": today,
            "status": "available",
        }

        cid = self._next_claim_id()
        self._register_source(source_url, cid)
        claims["is_under_liquidation"] = {
            "value": bool(data.get("underAvvikling", False)),
            "claim_id": cid,
            "source_url": source_url,
            "retrieved_date": today,
            "status": "available",
        }

        # Former names
        former_names = data.get("tidligereNavn", [])
        if former_names:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            f_list = [
                normalize_norwegian_text(fn.get("navn"))
                for fn in former_names
                if fn.get("navn")
            ]
            claims["former_names"] = {
                "value": f_list,
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        # Share capital (innskuddskapital)
        kapital = data.get("kapital", {})
        share_cap = kapital.get("innskuddskapital") if isinstance(kapital, dict) else None
        if share_cap is not None:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            claims["share_capital"] = {
                "value": share_cap,
                "currency": kapital.get("valuta", "NOK"),
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        # VAT registration status (registrertIMvaregisteret)
        vat_reg = data.get("registrertIMvaregisteret")
        if vat_reg is not None:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            claims["vat_registered"] = {
                "value": bool(vat_reg),
                "claim_id": cid,
                "source_url": source_url,
                "retrieved_date": today,
                "status": "available",
            }

        return {
            "status": "available",
            "claims": claims,
        }

    def _normalize_annual_accounts(
        self, regnskap_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        data_raw = regnskap_raw.get("data")
        source_url = (
            regnskap_raw.get("url")
            or f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
        )

        if isinstance(data_raw, dict) and "_embedded" in data_raw:
            data_list = data_raw["_embedded"].get("regnskaper", [])
        elif isinstance(data_raw, dict) and any(
            k in data_raw for k in ["resultatregnskapResultat", "regnskapsperiode"]
        ):
            data_list = [data_raw]
        elif isinstance(data_raw, list):
            data_list = data_raw
        else:
            data_list = []

        if not data_list:
            return {
                "status": "not_available",
                "claims": {},
                "reason": "No filed annual financial accounts in Regnskapsregisteret",
                "source_url": source_url,
                "retrieved_date": today,
            }

        # Sort accounts by period descending
        sorted_accounts = sorted(
            data_list,
            key=lambda x: x.get("regnskapsperiode", {}).get("tilDato", ""),
            reverse=True,
        )

        latest = sorted_accounts[0]
        period = latest.get("regnskapsperiode", {})
        year = period.get("tilDato", "")[:4] or "latest"
        valuta = latest.get("valuta", "NOK")

        res_obj = latest.get("resultatregnskapResultat", {})
        driftsresultat_obj = res_obj.get("driftsresultat", {})
        driftsinntekter_obj = driftsresultat_obj.get("driftsinntekter", {})
        egenkapital_obj = latest.get("egenkapitalGjeld", {})
        eiendeler_obj = latest.get("eiendeler", {})

        # Extract primary metrics
        revenue_val = driftsinntekter_obj.get("sumDriftsinntekter")
        if revenue_val is None:
            revenue_val = driftsinntekter_obj.get("salgsinntekter")
        operating_res = driftsresultat_obj.get("driftsresultat")
        net_inc = res_obj.get("aarsresultat")
        assets = eiendeler_obj.get("sumEiendeler")
        equity = egenkapital_obj.get("egenkapital", {}).get("sumEgenkapital")
        debt = egenkapital_obj.get("gjeldOversikt", {}).get("sumGjeld")

        claims: dict[str, Any] = {}

        def _add_claim(name: str, val: Any):
            if val is not None:
                cid = self._next_claim_id()
                self._register_source(source_url, cid)
                claims[name] = {
                    "value": val,
                    "claim_id": cid,
                    "currency": valuta,
                    "status": "available",
                    "source_url": source_url,
                    "retrieved_date": today,
                }

        _add_claim("revenue", revenue_val)
        _add_claim("operating_result", operating_res)
        _add_claim("net_income", net_inc)
        _add_claim("total_assets", assets)
        _add_claim("equity", equity)
        _add_claim("total_debt", debt)

        # Store previous year account if available (for YoY calculation)
        if len(sorted_accounts) > 1:
            prev = sorted_accounts[1]
            prev_res = prev.get("resultatregnskapResultat", {}).get("driftsresultat", {}).get("driftsinntekter", {})
            prev_rev = prev_res.get("salgsinntekter") or prev_res.get("sumDriftsinntekter")
            if prev_rev is not None:
                cid = self._next_claim_id()
                self._register_source(source_url, cid)
                claims["previous_year_revenue"] = {
                    "value": prev_rev,
                    "claim_id": cid,
                    "currency": prev.get("valuta", "NOK"),
                    "status": "available",
                    "source_url": source_url,
                    "retrieved_date": today,
                }

        # Extract group figures if filed
        group_figures = None
        group_accounts = [a for a in sorted_accounts if a.get("regnskapstype") == "KONSERN"]
        if group_accounts:
            grp = group_accounts[0]
            g_drifts = grp.get("resultatregnskapResultat", {}).get("driftsresultat", {}).get("driftsinntekter", {})
            g_rev = g_drifts.get("salgsinntekter") or g_drifts.get("sumDriftsinntekter")
            if g_rev is not None:
                cid = self._next_claim_id()
                self._register_source(source_url, cid)
                group_figures = {
                    "status": "available",
                    "revenue": {
                        "value": g_rev,
                        "claim_id": cid,
                        "currency": grp.get("valuta", "NOK"),
                    },
                }

        return {
            "status": "available" if claims else "not_available",
            "reporting_period": year,
            "claims": claims,
            "group_figures": group_figures,
            "source_url": source_url,
            "retrieved_date": today,
        }

    def _normalize_leadership(
        self,
        roller_raw: dict[str, Any],
        orgnr: str,
        today: str,
        proff_raw: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        data = roller_raw.get("data")
        source_url = (
            roller_raw.get("url")
            or f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}/roller"
        )

        if isinstance(data, dict):
            rollegrupper = data.get("rollegrupper", [])
        elif isinstance(data, list):
            rollegrupper = data
        else:
            rollegrupper = []

        leadership_claims: list[dict[str, Any]] = []

        if rollegrupper:
            # Roles structure in BRREG: array of role groups (rollegrupper)
            for group in rollegrupper:
                roller_list = group.get("roller", [])
                for r in roller_list:
                    if r.get("avregistrert", False):
                        continue  # Skip deregistered/former roles

                    person = r.get("person", {})
                    forretningsforer = r.get("enhet", {})  # For legal entities acting as manager/board

                    if person and person.get("erDoed", False):
                        continue

                    full_name = None
                    if person:
                        fn = person.get("navn", {})
                        if isinstance(fn, dict):
                            parts = [
                                fn.get("fornavn", ""),
                                fn.get("mellomnavn", ""),
                                fn.get("etternavn", ""),
                            ]
                            full_name = " ".join(p for p in parts if p).strip()
                        elif isinstance(fn, str):
                            full_name = fn.strip()
                    elif forretningsforer:
                        full_name = forretningsforer.get("navn")

                    role_desc = r.get("type", {}).get("beskrivelse") or r.get("type", {}).get("kode")

                    if full_name and role_desc:
                        cid = self._next_claim_id()
                        self._register_source(source_url, cid)
                        leadership_claims.append({
                            "name": normalize_norwegian_text(full_name),
                            "role": normalize_norwegian_text(role_desc),
                            "claim_id": cid,
                        })

        # USP 6: If BRREG lists no roles (e.g. privacy redaction), check supplementary Proff.no
        if not leadership_claims and proff_raw and proff_raw.get("status") == "available":
            proff_url = proff_raw.get("url")
            for off in proff_raw.get("officers", []):
                off_name = off.get("name")
                off_role = off.get("role")
                if off_name and off_role:
                    cid = self._next_claim_id()
                    self._register_source(proff_url, cid)
                    leadership_claims.append({
                        "name": normalize_norwegian_text(off_name),
                        "role": normalize_norwegian_text(off_role),
                        "claim_id": cid,
                    })

        if not leadership_claims:
            return {
                "status": "not_available",
                "claims": [],
                "reason": "No roles registered in Rolleregisteret",
                "source_url": source_url,
                "retrieved_date": today,
            }

        return {
            "status": "available",
            "claims": leadership_claims[:12],  # Cap top 12 primary roles
            "source_url": source_url,
            "retrieved_date": today,
        }

    def _normalize_workplaces(
        self, underenheter_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        data = underenheter_raw.get("data", {})
        source_url = (
            underenheter_raw.get("url")
            or f"https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={orgnr}"
        )

        items = data.get("_embedded", {}).get("underenheter", []) if data else []
        if not items:
            return {
                "status": "not_available",
                "claims": [],
                "reason": "No subordinate workplaces registered in Underenhetsregisteret",
                "source_url": source_url,
                "retrieved_date": today,
            }

        workplaces: list[dict[str, Any]] = []
        for u in items[:10]:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            workplaces.append({
                "org_number": u.get("organisasjonsnummer"),
                "name": normalize_norwegian_text(u.get("navn")),
                "employee_count": u.get("antallAnsatte", 0),
                "municipality": u.get("beliggenhetsadresse", {}).get("kommune"),
                "claim_id": cid,
            })

        return {
            "status": "available",
            "claims": workplaces,
            "source_url": source_url,
            "retrieved_date": today,
        }

    def _normalize_website(
        self,
        website_raw: dict[str, Any],
        web_enrichment_raw: dict[str, Any],
        orgnr: str,
        today: str,
    ) -> dict[str, Any]:
        status = website_raw.get("status", "not_available")
        official_url = website_raw.get("official_website")

        if status != "available" or not official_url:
            return {
                "status": "not_available",
                "verification_method": website_raw.get("verification_method", "not_verified"),
                "official_website": None,
                "reason": website_raw.get("reason", "No verified website"),
            }

        cid = self._next_claim_id()
        self._register_source(official_url, cid)

        return {
            "status": "available",
            "verification_method": website_raw.get("verification_method"),
            "official_website": official_url,
            "claim_id": cid,
            "description": web_enrichment_raw.get("description"),
            "social_profiles": web_enrichment_raw.get("social_profiles", []),
            "contact_email": web_enrichment_raw.get("contact_email"),
            "contact_phone": web_enrichment_raw.get("contact_phone"),
            "reason": website_raw.get("reason"),
        }

    def _normalize_hiring(
        self, jobs_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        status = jobs_raw.get("status", "not_available")
        claims_list = jobs_raw.get("claims", [])
        source_url = jobs_raw.get("source_url")

        if status != "available" or not claims_list:
            return {
                "status": "not_available",
                "claims": [],
                "reason": jobs_raw.get("reason", "No open vacancies found"),
            }

        formatted_claims = []
        for j in claims_list:
            cid = self._next_claim_id()
            self._register_source(source_url or j.get("url"), cid)
            formatted_claims.append({
                "title": j.get("title"),
                "url": j.get("url"),
                "claim_id": cid,
            })

        return {
            "status": "available",
            "claims": formatted_claims,
            "source_url": source_url,
            "retrieved_date": today,
        }

    def _normalize_announcements(
        self, announcements_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        items = announcements_raw.get("items", [])
        source_url = (
            announcements_raw.get("url")
            or f"https://w2.brreg.no/kunngjoring/hent.jsp?orgnr={orgnr}"
        )

        if not items:
            return {
                "status": "not_available",
                "claims": [],
                "reason": announcements_raw.get("error") or "No published announcements",
            }

        claims: list[dict[str, Any]] = []
        for it in items[:6]:
            cid = self._next_claim_id()
            self._register_source(source_url, cid)
            claims.append({
                "date": it.get("date"),
                "type": it.get("type"),
                "description": it.get("description"),
                "claim_id": cid,
            })

        return {
            "status": "available",
            "claims": claims,
            "source_url": source_url,
            "retrieved_date": today,
        }

    def _normalize_news(
        self, news_raw: dict[str, Any], orgnr: str, today: str
    ) -> dict[str, Any]:
        status = news_raw.get("status", "not_available")
        claims_list = news_raw.get("claims", [])
        source_url = news_raw.get("source_url")

        if status != "available" or not claims_list:
            return {
                "status": "not_available",
                "claims": [],
                "reason": news_raw.get("reason", "No verified news articles found"),
            }

        formatted_claims = []
        for n in claims_list:
            cid = self._next_claim_id()
            self._register_source(source_url or n.get("url"), cid)
            formatted_claims.append({
                "title": n.get("title"),
                "url": n.get("url"),
                "published_date": n.get("published_date"),
                "claim_id": cid,
            })

        return {
            "status": "available",
            "claims": formatted_claims,
            "source_url": source_url,
            "retrieved_date": today,
        }
