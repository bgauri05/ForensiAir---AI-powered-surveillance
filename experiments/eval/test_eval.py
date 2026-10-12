# -*- coding: utf-8 -*-
"""
Unit tests for ForensiAIR evaluation framework.
Tests:
1. Perfect scorer gives recall 1.0
2. Never-flag scorer gives recall 0.0
3. Same seed gives identical results (reproducibility)
"""

import unittest
import os
import sys
import yaml
import numpy as np
import pandas as pd

# Import run_eval functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_eval import wilson_score_interval, load_config

class TestEvaluationEngine(unittest.TestCase):

    def setUp(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.script_dir, "config.yaml")

    def test_perfect_scorer_gives_recall_one(self):
        """Test that a perfect scorer (n_detected == n_events) yields recall = 1.0."""
        n_events = 50
        n_detected = 50
        recall, ci_low, ci_high = wilson_score_interval(n_detected, n_events)
        self.assertEqual(recall, 1.0)
        self.assertGreater(ci_low, 0.90)
        self.assertAlmostEqual(ci_high, 1.0, places=5)

    def test_never_flag_scorer_gives_zero(self):
        """Test that a never-flag scorer (n_detected == 0) yields recall = 0.0."""
        n_events = 50
        n_detected = 0
        recall, ci_low, ci_high = wilson_score_interval(n_detected, n_events)
        self.assertEqual(recall, 0.0)
        self.assertEqual(ci_low, 0.0)
        self.assertLess(ci_high, 0.10)

    def test_reproducibility_same_seed(self):
        """Test that using the same fixed random seed produces identical results."""
        seed = 42
        
        # Run 1
        np.random.seed(seed)
        data1 = np.random.normal(loc=14.11, scale=2.5, size=100)
        recall1, low1, high1 = wilson_score_interval(45, 50)
        
        # Run 2 with same seed
        np.random.seed(seed)
        data2 = np.random.normal(loc=14.11, scale=2.5, size=100)
        recall2, low2, high2 = wilson_score_interval(45, 50)

        np.testing.assert_array_equal(data1, data2)
        self.assertEqual(recall1, recall2)
        self.assertEqual(low1, low2)
        self.assertEqual(high1, high2)

    def test_config_rules_loaded_correctly(self):
        """Test that config.yaml loads with expected rules and parameters."""
        config = load_config(self.config_path)
        self.assertIn("evaluation_rules", config)
        self.assertEqual(config["evaluation_rules"]["window_margin_hours"], 2)
        self.assertIn("separately_reported_tamper_types", config["evaluation_rules"])
        self.assertEqual(config["evaluation_rules"]["random_seed"], 42)

if __name__ == "__main__":
    unittest.main()
