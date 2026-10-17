"""Unit tests for 3-Tier Website Verification Protocol & Domain Candidate Discovery."""

import unittest
from website_verifier import WebsiteVerifier
from utils import clean_org_number, is_valid_norwegian_orgnr


class TestWebsiteVerifier(unittest.TestCase):
    def test_modulo11_norwegian_orgnr_checksum(self):
        """Verify Norwegian Modulo 11 checksum calculation."""
        # Valid org numbers
        self.assertTrue(is_valid_norwegian_orgnr("923609016"))  # Equinor
        self.assertTrue(is_valid_norwegian_orgnr("984851006"))  # DNB
        self.assertTrue(is_valid_norwegian_orgnr("990888213"))  # Telenor

        # Invalid numbers
        self.assertFalse(is_valid_norwegian_orgnr("123456789"))
        self.assertFalse(is_valid_norwegian_orgnr("923609015"))
        self.assertFalse(is_valid_norwegian_orgnr("short"))
        self.assertFalse(is_valid_norwegian_orgnr(""))

    def test_domain_candidate_extraction_and_filtering(self):
        """Verify registry email filtering blocks free providers and keeps corporate domains."""
        verifier = WebsiteVerifier()

        # Case 1: Corporate email
        enhet_corp = {
            "navn": "NORSK HYDRO ASA",
            "hjemmeside": "www.hydro.com",
            "epostadresse": "contact@hydro.com",
        }
        reg_site, candidates = verifier.extract_candidates_from_registry(enhet_corp)
        self.assertEqual(reg_site, "www.hydro.com")
        self.assertIn("https://www.hydro.com", candidates)

        # Case 2: Free email provider (must NOT be used as company website)
        enhet_free = {
            "navn": "LARSEN CONSULTING AS",
            "hjemmeside": None,
            "epostadresse": "olav.larsen@gmail.com",
        }
        reg_site, candidates = verifier.extract_candidates_from_registry(enhet_free)
        self.assertFalse(any("gmail.com" in c for c in candidates))

    def test_orgnr_matching_in_html(self):
        """Verify detection of 9-digit orgnr in raw or formatted text."""
        verifier = WebsiteVerifier()
        html_raw = "<div>Foretaksregisteret Org nr: 923609016 MVA</div>"
        html_formatted = "<footer>Organisasjonsnummer 923 609 016</footer>"
        html_unrelated = "<div>Contact us at 987 654 321</div>"

        self.assertTrue(verifier._check_orgnr_in_html(html_raw, "923609016"))
        self.assertTrue(verifier._check_orgnr_in_html(html_formatted, "923609016"))
        self.assertFalse(verifier._check_orgnr_in_html(html_unrelated, "923609016"))

    def test_conflicting_orgnr_detection(self):
        """Verify detection of conflicting foreign orgnr on page to prevent wrong-company attribution."""
        verifier = WebsiteVerifier()
        html_same = "<div>Foretak 923609016</div>"
        html_conflict = "<div>Copyright 984851006 DNB Bank</div>"

        self.assertIsNone(verifier._find_conflicting_orgnr(html_same, "923609016"))
        self.assertEqual(verifier._find_conflicting_orgnr(html_conflict, "923609016"), "984851006")


if __name__ == "__main__":
    unittest.main()
