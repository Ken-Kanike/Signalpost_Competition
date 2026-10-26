"""Unit tests for Derived Signals Engine."""

import unittest
from derived_signals import DerivedSignalsEngine


class TestDerivedSignals(unittest.TestCase):
    def test_derived_signals_yoy_revenue_and_equity(self):
        engine = DerivedSignalsEngine()

        mock_sections = {
            "legal_identity": {
                "claims": {
                    "employee_count": {"value": 250, "claim_id": "c006"},
                }
            },
            "annual_accounts": {
                "claims": {
                    "revenue": {"value": 115000000, "claim_id": "c011", "currency": "NOK"},
                    "previous_year_revenue": {"value": 100000000, "claim_id": "c011_prev", "currency": "NOK"},
                    "operating_result": {"value": 11500000, "claim_id": "c012", "currency": "NOK"},
                    "equity": {"value": 45000000, "claim_id": "c015", "currency": "NOK"},
                    "total_debt": {"value": 90000000, "claim_id": "c016", "currency": "NOK"},
                }
            }
        }

        signals = engine.compute_signals(mock_sections)

        # 1. YoY Revenue Change
        self.assertIn("yoy_revenue_change", signals)
        yoy = signals["yoy_revenue_change"]
        self.assertEqual(yoy["value"], 0.15)
        self.assertEqual(yoy["percentage"], "15.0%")
        self.assertIn("increased by 15.0%", yoy["description"])
        self.assertEqual(yoy["based_on"], ["c011", "c011_prev"])

        # 2. Negative Equity
        self.assertIn("negative_equity", signals)
        self.assertFalse(signals["negative_equity"]["value"])
        self.assertEqual(signals["negative_equity"]["based_on"], ["c015"])

        # 3. Operating Margin
        self.assertIn("operating_margin", signals)
        self.assertEqual(signals["operating_margin"]["percentage"], "10.0%")
        self.assertEqual(signals["operating_margin"]["based_on"], ["c011", "c012"])

        # 4. Workforce Scale
        self.assertIn("workforce_scale", signals)
        self.assertIn("Enterprise", signals["workforce_scale"]["classification"])
        self.assertEqual(signals["workforce_scale"]["based_on"], ["c006"])

        # 5. Debt to Equity Ratio
        self.assertIn("debt_to_equity", signals)
        self.assertEqual(signals["debt_to_equity"]["value"], 2.0)
        self.assertEqual(signals["debt_to_equity"]["ratio"], "2.00x")
        self.assertEqual(signals["debt_to_equity"]["based_on"], ["c016", "c015"])

    def test_negative_equity_detection(self):
        engine = DerivedSignalsEngine()
        mock_sections = {
            "annual_accounts": {
                "claims": {
                    "equity": {"value": -500000, "claim_id": "c020", "currency": "NOK"},
                }
            }
        }
        signals = engine.compute_signals(mock_sections)
        self.assertTrue(signals["negative_equity"]["value"])
        self.assertIn("solvency risk", signals["negative_equity"]["description"])


if __name__ == "__main__":
    unittest.main()
