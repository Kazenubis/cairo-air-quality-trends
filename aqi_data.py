"""
Cairo Air Quality Trends — a synthetic-but-calibrated daily AQI dataset
for Cairo, since this environment has no network access to a real
historical air-quality API.

Cairo's air quality is a well-documented real problem: multiple
independent monitoring reports (IQAir's annual World Air Quality
Report among them) have placed its yearly average in the
"Unhealthy for Sensitive Groups" to "Unhealthy" band on the US AQI
scale (roughly 100-160), driven heavily by two seasonal spikes —
the October/November agricultural-waste-burning period locally known
as the "black cloud" season, and spring dust storms (locally,
"khamsin") from March through May. This generator is calibrated
against those two well-known, publicly reported patterns rather than
presenting arbitrary numbers as if they were pulled from a live feed.
"""

import random
from datetime import date, timedelta

import pandas as pd

SEED = 11
BASE_AQI = 105.0
BLACK_CLOUD_MONTHS = {10, 11}       # agricultural burning season
BLACK_CLOUD_BOOST = 55.0
DUST_STORM_MONTHS = {3, 4, 5}       # khamsin season
DUST_STORM_BOOST = 30.0
SUMMER_MONTHS = {6, 7, 8}
SUMMER_REDUCTION = 12.0
FRIDAY_REDUCTION = 10.0             # weekend in Egypt, lighter traffic
DAILY_NOISE_STD = 16.0
AQI_MIN = 25.0
AQI_MAX = 380.0

# US EPA-style AQI breakpoints, used for both the real scale (0-500)
# and this synthetic dataset.
AQI_CATEGORIES = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for Sensitive Groups"),
    (200, "Unhealthy"),
    (300, "Very Unhealthy"),
    (float("inf"), "Hazardous"),
]


def categorize_aqi(aqi):
    for threshold, label in AQI_CATEGORIES:
        if aqi <= threshold:
            return label
    return AQI_CATEGORIES[-1][1]


def generate_cairo_aqi_data(year=2025, seed=SEED):
    """Generates one synthetic daily AQI reading per day of `year`,
    calibrated to Cairo's well-documented seasonal pollution pattern."""
    rng = random.Random(seed)
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    rows = []
    day = start
    while day <= end:
        aqi = BASE_AQI

        if day.month in BLACK_CLOUD_MONTHS:
            aqi += BLACK_CLOUD_BOOST
        elif day.month in DUST_STORM_MONTHS:
            aqi += DUST_STORM_BOOST
        elif day.month in SUMMER_MONTHS:
            aqi -= SUMMER_REDUCTION

        if day.weekday() == 4:  # Friday
            aqi -= FRIDAY_REDUCTION

        aqi += rng.gauss(0, DAILY_NOISE_STD)
        aqi = max(AQI_MIN, min(AQI_MAX, aqi))

        rows.append({"date": day, "aqi": round(aqi, 1)})
        day += timedelta(days=1)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["category"] = df["aqi"].apply(categorize_aqi)
    return df


def rolling_average(df, window=7):
    """Returns a Series of the trailing rolling mean AQI, aligned to
    df's index. min_periods=1 so the first few days of the year still
    get a (shorter-window) average instead of NaN."""
    return df["aqi"].rolling(window=window, min_periods=1).mean()


def top_n_days(df, n=5, worst=True):
    return df.sort_values("aqi", ascending=not worst).head(n).reset_index(drop=True)


def category_breakdown(df):
    """Returns category -> day count, ordered by AQI severity (not by
    count) so a reader can see the full severity spectrum even for
    categories with zero days."""
    counts = df["category"].value_counts().to_dict()
    ordered_labels = [label for _, label in AQI_CATEGORIES]
    return {label: counts.get(label, 0) for label in ordered_labels}


def summary_stats(df):
    return {
        "mean_aqi": round(df["aqi"].mean(), 1),
        "median_aqi": round(df["aqi"].median(), 1),
        "max_aqi": round(df["aqi"].max(), 1),
        "min_aqi": round(df["aqi"].min(), 1),
        "days_unhealthy_or_worse": int((df["aqi"] > 150).sum()),
        "total_days": len(df),
    }
