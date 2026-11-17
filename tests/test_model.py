"""Checks that the Python model reproduces the submitted Excel model."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import model  # noqa: E402


class ReproducesExcel(unittest.TestCase):
    def setUp(self):
        self.cs = model.cost_structure(model.load_financials())

    def test_ebit_matches_10k_bridge(self):
        self.assertAlmostEqual(self.cs["2023"]["ebit"], 53_632, places=0)
        self.assertAlmostEqual(self.cs["2025"]["ebit"], 41_871, places=0)

    def test_leverage(self):
        self.assertAlmostEqual(self.cs["2025"]["dol"], 2.4304, places=3)
        self.assertAlmostEqual(self.cs["2025"]["margin_of_safety"], 0.3296, places=3)

    def test_wacc(self):
        self.assertAlmostEqual(model.wacc(), 0.0814, places=4)

    def test_scenario_npvs(self):
        self.assertAlmostEqual(model.valuation("Base")["npv"], 6_926.27, delta=1)
        self.assertAlmostEqual(model.valuation("Worst")["npv"], -32_825.85, delta=1)
        self.assertAlmostEqual(model.valuation("Best")["npv"], 42_596.14, delta=1)
        self.assertAlmostEqual(model.valuation("Base")["irr"], 0.0956, places=3)

    def test_sensitivities(self):
        self.assertAlmostEqual(model.valuation("Base", rate=0.09)["npv"], -581.75, delta=1)
        self.assertAlmostEqual(model.valuation("Base", terminal_synergy_share=0)["npv"], -1_953.96, delta=1)
        self.assertAlmostEqual(model.breakeven_wacc(), 0.0893, places=3)


if __name__ == "__main__":
    unittest.main()
