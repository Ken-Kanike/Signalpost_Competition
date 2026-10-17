"""Integration tests for full pipeline execution and CitationValidator compliance."""

import asyncio
import unittest
from citation_validator import CitationValidator
from orchestrator import Orchestrator


class TestPipeline(unittest.TestCase):
    def test_full_pipeline_single_company(self):
        async def _run():
            orc = Orchestrator()
            envelopes, report = await orc.run_batch(["923609016"])
            self.assertEqual(len(envelopes), 1)
            env = envelopes[0]
            self.assertEqual(env.status, "available")
            self.assertEqual(env.organisation_number, "923609016")
            self.assertIsNotNone(env.synthesis)
            self.assertGreater(len(env.synthesis.claim_references), 0)

            # Validate envelope with CitationValidator
            val = CitationValidator()
            is_valid, errors = val.validate_envelope(env.model_dump())
            self.assertTrue(is_valid, f"Validation errors: {errors}")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
