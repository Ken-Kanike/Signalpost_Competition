"""Unit tests for Signalpost FastAPI server endpoints."""

import unittest
from fastapi.testclient import TestClient
from server import app


class TestServerEndpoints(unittest.TestCase):
    """Test suite for server API endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("version"), "2.0.0")

    def test_stats_endpoint(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_companies", data)

    def test_profiles_search_endpoint(self):
        resp = self.client.get("/api/profiles?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_validate_endpoint(self):
        # Valid dummy envelope format
        dummy_env = {
            "organisation_number": "923609016",
            "status": "available",
            "retrieved_at": "2026-10-26T12:00:00Z",
            "sections": {
                "legal_identity": {
                    "status": "available",
                    "claims": {
                        "legal_name": {
                            "value": "EQUINOR ASA",
                            "claim_id": "c001",
                            "status": "available",
                        }
                    },
                }
            },
            "sources": [
                {
                    "url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                    "source_name": "Brønnøysundregistrene (Enhetsregisteret)",
                    "retrieved_date": "2026-10-26",
                    "status_code": 200,
                    "claims_backed": ["c001"],
                }
            ],
            "synthesis": {
                "text": "EQUINOR ASA [c001] is registered.",
                "claim_references": ["c001"],
            },
        }
        resp = self.client.post("/api/validate", json=dummy_env)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("is_valid"))


if __name__ == "__main__":
    unittest.main()
