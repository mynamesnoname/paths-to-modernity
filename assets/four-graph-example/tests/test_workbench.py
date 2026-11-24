"""Verify spectral workbench session and 3-way technical triage."""

import unittest
from src.workbench_api import WorkbenchSession

class WorkbenchTests(unittest.TestCase):
    def test_provisional_bookmark_flow(self) -> None:
        ws = WorkbenchSession()
        out = ws.inspect_and_tag('PK-001', 532.0, 'not_understood_prototype')
        self.assertTrue(out['triage']['bookmark'])
