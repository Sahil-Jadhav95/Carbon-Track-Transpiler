import unittest

from ctt.carbon_audit import run_audit


class TestJavaScriptCarbonAudit(unittest.TestCase):

    def test_run_audit_returns_report_for_javascript(self):
        source = "const x = 2 + 3; console.log(x);"
        optimized = "const x = 5; console.log(x);"
        report = run_audit(source, optimized, language="javascript")

        self.assertIsNotNone(report)
        self.assertTrue(hasattr(report, "energy_before_kwh"))
        self.assertTrue(hasattr(report, "energy_after_kwh"))


if __name__ == "__main__":
    unittest.main()
