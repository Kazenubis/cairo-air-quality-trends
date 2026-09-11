"""
Tests for aqi_data.py — categorization, dataset generation, rolling
average, top-N days, and summary stats.
"""

import unittest

import pandas as pd

from aqi_data import (
    categorize_aqi,
    category_breakdown,
    generate_cairo_aqi_data,
    rolling_average,
    summary_stats,
    top_n_days,
)


class TestCategorizeAqi(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(categorize_aqi(0), "Good")
        self.assertEqual(categorize_aqi(50), "Good")
        self.assertEqual(categorize_aqi(51), "Moderate")
        self.assertEqual(categorize_aqi(100), "Moderate")
        self.assertEqual(categorize_aqi(101), "Unhealthy for Sensitive Groups")
        self.assertEqual(categorize_aqi(150), "Unhealthy for Sensitive Groups")
        self.assertEqual(categorize_aqi(151), "Unhealthy")
        self.assertEqual(categorize_aqi(200), "Unhealthy")
        self.assertEqual(categorize_aqi(201), "Very Unhealthy")
        self.assertEqual(categorize_aqi(300), "Very Unhealthy")
        self.assertEqual(categorize_aqi(301), "Hazardous")
        self.assertEqual(categorize_aqi(500), "Hazardous")


class TestGenerateCairoAqiData(unittest.TestCase):
    def setUp(self):
        self.df = generate_cairo_aqi_data(year=2025, seed=42)

    def test_covers_every_day_of_the_year(self):
        self.assertEqual(len(self.df), 365)
        self.assertEqual(self.df["date"].min(), pd.Timestamp("2025-01-01"))
        self.assertEqual(self.df["date"].max(), pd.Timestamp("2025-12-31"))

    def test_generation_is_deterministic_given_a_seed(self):
        df_again = generate_cairo_aqi_data(year=2025, seed=42)
        pd.testing.assert_frame_equal(self.df, df_again)

    def test_different_seeds_give_different_data(self):
        df_other_seed = generate_cairo_aqi_data(year=2025, seed=99)
        self.assertFalse(self.df["aqi"].equals(df_other_seed["aqi"]))

    def test_aqi_values_stay_within_bounds(self):
        self.assertTrue((self.df["aqi"] >= 25).all())
        self.assertTrue((self.df["aqi"] <= 380).all())

    def test_black_cloud_season_is_worse_than_summer(self):
        # October/November (agricultural burning) should average
        # noticeably higher AQI than June/July/August.
        black_cloud = self.df[self.df["date"].dt.month.isin([10, 11])]["aqi"].mean()
        summer = self.df[self.df["date"].dt.month.isin([6, 7, 8])]["aqi"].mean()
        self.assertGreater(black_cloud, summer + 30)

    def test_category_column_matches_categorize_aqi(self):
        sample = self.df.sample(20, random_state=1)
        for _, row in sample.iterrows():
            self.assertEqual(row["category"], categorize_aqi(row["aqi"]))


class TestRollingAverage(unittest.TestCase):
    def test_smooths_a_single_spike(self):
        df = pd.DataFrame({"aqi": [100, 100, 100, 300, 100, 100, 100]})
        smoothed = rolling_average(df, window=3)
        # the spike itself should be pulled toward its neighbors, not
        # left at the raw 300
        self.assertLess(smoothed.iloc[3], 300)
        self.assertGreater(smoothed.iloc[3], 100)

    def test_first_value_is_not_nan_even_with_a_large_window(self):
        df = pd.DataFrame({"aqi": [120, 130, 140]})
        smoothed = rolling_average(df, window=7)
        self.assertFalse(smoothed.isna().any())


class TestTopNDays(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=5),
            "aqi": [80.0, 200.0, 50.0, 175.0, 120.0],
        })

    def test_worst_days_sorted_descending(self):
        worst = top_n_days(self.df, n=3, worst=True)
        self.assertEqual(list(worst["aqi"]), [200.0, 175.0, 120.0])

    def test_best_days_sorted_ascending(self):
        best = top_n_days(self.df, n=2, worst=False)
        self.assertEqual(list(best["aqi"]), [50.0, 80.0])


class TestCategoryBreakdownAndSummary(unittest.TestCase):
    def test_category_breakdown_includes_zero_count_categories(self):
        df = pd.DataFrame({"aqi": [30.0, 60.0], "category": ["Good", "Moderate"]})
        breakdown = category_breakdown(df)
        self.assertEqual(breakdown["Good"], 1)
        self.assertEqual(breakdown["Moderate"], 1)
        self.assertEqual(breakdown["Hazardous"], 0)  # present, just zero

    def test_summary_stats_are_correct(self):
        df = pd.DataFrame({"aqi": [100.0, 200.0, 50.0]})
        stats = summary_stats(df)
        self.assertEqual(stats["mean_aqi"], 116.7)
        self.assertEqual(stats["max_aqi"], 200.0)
        self.assertEqual(stats["min_aqi"], 50.0)
        self.assertEqual(stats["days_unhealthy_or_worse"], 1)
        self.assertEqual(stats["total_days"], 3)


if __name__ == "__main__":
    unittest.main()
