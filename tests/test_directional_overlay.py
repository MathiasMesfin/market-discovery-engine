import unittest
import sys
import os

# Add parent directory to path so we can import directional_overlay
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from directional_overlay import calculate_directional_overlay

class TestDirectionalOverlay(unittest.TestCase):

    def test_neutral_setup(self):
        # Default neutral setup
        res = calculate_directional_overlay(
            expectation_setup=50,
            run_up_risk=50,
            cf_score=50,
            guidance_sensitivity=50,
            research_priority=50,
            ret_30d=5,
            ret_60d=10
        )
        self.assertEqual(res["Directional_Probability_Score"], 46.0)
        self.assertEqual(res["Directional_Edge_Score_V1"], 46.0)
        self.assertEqual(res["Directional_Bias"], "Neutral / unclear")
        self.assertEqual(res["Directional_Archetype"], "Neutral Directional Setup")

    def test_extreme_bullish(self):
        # Maximum bullish components
        res = calculate_directional_overlay(
            expectation_setup=100,      # high (percentile ~79.9)
            run_up_risk=15,            # low
            cf_score=85,               # high
            guidance_sensitivity=30,   # neutral
            research_priority=75,      # high (percentile ~100.0)
            ret_30d=-10.0,              # cooled off (percentile ~18%)
            ret_60d=30.0               # strong 60D momentum (percentile ~90%)
        )
        # Score = 0.40 * 90.0 + 0.25 * (100 - 18.0) + 0.20 * 79.9 + 0.15 * 100.0 = 87.0
        self.assertEqual(res["Directional_Probability_Score"], 87.0)
        self.assertEqual(res["Directional_Edge_Score_V1"], 87.0)
        self.assertEqual(res["Directional_Bias"], "Strong bullish directional bias")
        self.assertEqual(res["Directional_Archetype"], "Spring-Loaded Value Winner")

    def test_extreme_bearish(self):
        # Maximum bearish components
        res = calculate_directional_overlay(
            expectation_setup=10,      # low
            run_up_risk=80,            # high
            cf_score=20,               # poor
            guidance_sensitivity=70,   # combined guidance/run-up
            research_priority=30,      # low
            ret_30d=5.0,               # not cooled off (percentile ~65%)
            ret_60d=-25.0              # low 60D momentum (percentile ~10.5%)
        )
        # Score = 0.40 * 10.5 + 0.25 * (100 - 65.5) + 0.20 * 1.88 + 0.15 * 0.1 = 13.2
        self.assertEqual(res["Directional_Probability_Score"], 13.2)
        self.assertEqual(res["Directional_Edge_Score_V1"], 13.2)
        self.assertEqual(res["Directional_Bias"], "Strong bearish directional bias")
        # Guidance sensitivity >= 60 and runup >= 60 is Guidance-Sensitive Underdog
        self.assertEqual(res["Directional_Archetype"], "Guidance-Sensitive Underdog")

    def test_exhausted_hype_collapse(self):
        # Run-Up >= 60, CF <= 40, 30D Return > 10%
        res = calculate_directional_overlay(
            expectation_setup=30,
            run_up_risk=70,
            cf_score=30,
            guidance_sensitivity=40,
            research_priority=45,
            ret_30d=15.0,
            ret_60d=10.0
        )
        self.assertEqual(res["Directional_Archetype"], "Exhausted Hype Collapse")
        # Score is ~35.9: in the bearish lean band (35-40) under the recalibrated tiers
        self.assertLess(res["Directional_Probability_Score"], 40.0)
        self.assertLess(res["Directional_Edge_Score_V1"], 40.0)
        self.assertEqual(res["Directional_Bias"], "Bearish directional lean")

    def test_none_values(self):
        # Graceful handling of None values
        res = calculate_directional_overlay(
            expectation_setup=None,
            run_up_risk=None,
            cf_score=None,
            guidance_sensitivity=None,
            research_priority=None,
            ret_30d=None,
            ret_60d=None
        )
        self.assertEqual(res["Directional_Probability_Score"], 50.0)
        self.assertEqual(res["Directional_Edge_Score_V1"], 50.0)
        self.assertEqual(res["Directional_Bias"], "Neutral / unclear")
        self.assertEqual(res["Directional_Archetype"], "Neutral Directional Setup")

    # ------------------------------------------------------------------
    # Recalibrated 5-tier bias label tests (forensic audit 2026-06-21)
    # ------------------------------------------------------------------

    def test_bias_strong_bullish(self):
        """Score ~83 (>= 60) -> Strong bullish directional bias.

        Strong 60D runner (+20%) that pulled back 30D (-10%) with max
        Expectation_Setup and high Research_Priority.
        Empirically: top ~10% of all historical readings.
        """
        res = calculate_directional_overlay(
            expectation_setup=100,   # max expectation
            run_up_risk=20,
            cf_score=70,
            guidance_sensitivity=30,
            research_priority=60,    # high research score -> pct ~92
            ret_30d=-10.0,           # pulled back (bearish 30D = bullish signal)
            ret_60d=20.0,            # strong 60D runner
        )
        # Score: ~33.2 + 20.0 + 16.0 + 13.8 = ~83
        self.assertGreaterEqual(res["Directional_Edge_Score_V1"], 60.0)
        self.assertEqual(res["Directional_Bias"], "Strong bullish directional bias")

    def test_bias_bullish_lean(self):
        """Score ~59.6 (>= 55 and < 60) -> Bullish directional lean.

        Moderate 60D gain (+8%) with slight positive 30D drift (+3%),
        max Expectation_Setup, and neutral Research_Priority.
        """
        res = calculate_directional_overlay(
            expectation_setup=100,   # max expectation -> pct ~79.9
            run_up_risk=40,
            cf_score=60,
            guidance_sensitivity=40,
            research_priority=50,    # median research -> pct ~45
            ret_30d=3.0,             # mild positive 30D
            ret_60d=8.0,             # moderate 60D
        )
        # Score: ~26.7 + 10.2 + 16.0 + 6.75 = ~59.6
        self.assertGreaterEqual(res["Directional_Edge_Score_V1"], 55.0)
        self.assertLess(res["Directional_Edge_Score_V1"], 60.0)
        self.assertEqual(res["Directional_Bias"], "Bullish directional lean")

    def test_bias_neutral(self):
        """Score ~41.0 (>= 40 and < 55) -> Neutral / unclear.

        Near-flat momentum on both windows with median Expectation and
        Research scores — a typical screener candidate.
        """
        res = calculate_directional_overlay(
            expectation_setup=50,
            run_up_risk=50,
            cf_score=50,
            guidance_sensitivity=50,
            research_priority=50,
            ret_30d=3.0,
            ret_60d=2.0,
        )
        # Score: ~21.6 + 10.2 + 2.4 + 6.75 = ~41
        self.assertGreaterEqual(res["Directional_Edge_Score_V1"], 40.0)
        self.assertLess(res["Directional_Edge_Score_V1"], 55.0)
        self.assertEqual(res["Directional_Bias"], "Neutral / unclear")

    def test_bias_bearish_lean(self):
        """Score ~36 (>= 35 and < 40) -> Bearish directional lean.

        Small positive 60D gain offset by meaningful positive 30D
        momentum (stock still running hot), with low Expectation and
        Research scores.
        """
        res = calculate_directional_overlay(
            expectation_setup=60,   # modest expectation
            run_up_risk=60,
            cf_score=50,
            guidance_sensitivity=50,
            research_priority=47,   # low research -> pct ~29
            ret_30d=8.0,            # running hot 30D (reduces score)
            ret_60d=2.0,            # small 60D gain
        )
        # Score: ~21.6 + 6.6 + 3.4 + 4.35 = ~36
        self.assertGreaterEqual(res["Directional_Edge_Score_V1"], 35.0)
        self.assertLess(res["Directional_Edge_Score_V1"], 40.0)
        self.assertEqual(res["Directional_Bias"], "Bearish directional lean")

    def test_bias_strong_bearish(self):
        """Score ~17 (< 35) -> Strong bearish directional bias.

        Negative 60D return, strongly positive 30D run-up, and very
        low Expectation and Research scores.
        """
        res = calculate_directional_overlay(
            expectation_setup=20,   # very low expectation
            run_up_risk=80,
            cf_score=20,
            guidance_sensitivity=70,
            research_priority=42,   # low research -> pct ~9
            ret_30d=15.0,           # running very hot 30D
            ret_60d=-10.0,          # negative 60D momentum
        )
        # Score: ~11.6 + 3.6 + 0.73 + 1.4 = ~17.3
        self.assertLess(res["Directional_Edge_Score_V1"], 35.0)
        self.assertEqual(res["Directional_Bias"], "Strong bearish directional bias")


if __name__ == "__main__":
    unittest.main()
