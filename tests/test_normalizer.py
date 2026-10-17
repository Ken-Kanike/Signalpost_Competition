"""Unit tests for Normalizer & Claim ID Assignment."""

import unittest
from normalizer import Normalizer


class TestNormalizer(unittest.TestCase):
    def test_normalizer_sequential_claim_ids_and_sources(self):
        normalizer = Normalizer()

        enhet_raw = {
            "url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
            "available": True,
            "data": {
                "navn": "EQUINOR ASA",
                "organisasjonsform": {"kode": "ASA", "beskrivelse": "Allmennaksjeselskap"},
                "registreringsdatoEnhetsregisteret": "2007-10-01",
                "antallAnsatte": 21000,
                "forretningsadresse": {
                    "adresse": ["Forusbeen 50"],
                    "postnummer": "4035",
                    "poststed": "STAVANGER",
                    "kommune": "STAVANGER",
                },
            },
        }

        roller_raw = {"available": False, "data": []}
        regnskap_raw = {"available": False, "data": []}
        underenheter_raw = {"available": False, "data": {}}
        announcements_raw = {"available": False, "items": []}
        website_raw = {"status": "available", "official_website": "https://www.equinor.com", "verification_method": "tier1"}
        web_enrichment_raw = {"description": "Leading global energy company", "social_profiles": []}
        jobs_raw = {"status": "not_available", "claims": []}

        sections, sources = normalizer.normalize(
            orgnr="923609016",
            enhet_raw=enhet_raw,
            roller_raw=roller_raw,
            regnskap_raw=regnskap_raw,
            underenheter_raw=underenheter_raw,
            announcements_raw=announcements_raw,
            website_raw=website_raw,
            web_enrichment_raw=web_enrichment_raw,
            jobs_raw=jobs_raw,
        )

        legal_claims = sections["legal_identity"]["claims"]
        self.assertEqual(legal_claims["legal_name"]["claim_id"], "c001")
        self.assertEqual(legal_claims["legal_name"]["value"], "EQUINOR ASA")
        self.assertEqual(legal_claims["legal_form"]["claim_id"], "c002")
        self.assertEqual(legal_claims["incorporation_date"]["claim_id"], "c003")
        self.assertEqual(legal_claims["registered_address"]["claim_id"], "c004")
        self.assertEqual(legal_claims["employee_count"]["claim_id"], "c005")

        # Website claim
        self.assertTrue(sections["website"]["claim_id"].startswith("c"))

        # Sources
        self.assertGreaterEqual(len(sources), 2)
        enhet_source = next(s for s in sources if "data.brreg.no" in s.url)
        self.assertIn("c001", enhet_source.claims_backed)


if __name__ == "__main__":
    unittest.main()
