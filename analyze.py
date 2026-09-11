"""
Cairo Air Quality Trends — CLI: prints a summary, the 5 worst/best days
of the year, the category breakdown, and (optionally) saves a trend
chart with the top-5 worst days highlighted.
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from aqi_data import category_breakdown, generate_cairo_aqi_data, rolling_average, summary_stats, top_n_days

CATEGORY_COLORS = {
    "Good": "#2fae63",
    "Moderate": "#d8b93a",
    "Unhealthy for Sensitive Groups": "#e08a3c",
    "Unhealthy": "#d3453f",
    "Very Unhealthy": "#9b3fae",
    "Hazardous": "#6b1f2a",
}


def plot_trend(df, output_path):
    fig, ax = plt.subplots(figsize=(11, 5.5))

    ax.plot(df["date"], df["aqi"], color="#c9c9c9", linewidth=0.8, alpha=0.6, label="Daily AQI")
    ax.plot(df["date"], rolling_average(df, window=7), color="#2f6fa6", linewidth=2.2, label="7-day average")

    worst = top_n_days(df, n=5, worst=True)
    ax.scatter(worst["date"], worst["aqi"], color="#d3453f", zorder=5, s=45, label="Top 5 worst days")

    ax.axhline(150, color="#999999", linestyle="--", linewidth=1, alpha=0.7)
    ax.text(df["date"].iloc[3], 153, "Unhealthy threshold (150)", fontsize=8, color="#666666")

    ax.set_title("Cairo Daily AQI, 2025 (synthetic, calibrated to real seasonal patterns)")
    ax.set_ylabel("AQI")
    ax.legend(loc="upper left", fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=130)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Cairo Air Quality Trends")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--chart", default=None, help="Path to save a trend chart PNG")
    args = parser.parse_args()

    df = generate_cairo_aqi_data(year=args.year)

    stats = summary_stats(df)
    print(f"=== Cairo AQI summary, {args.year} ===")
    print(f"Mean AQI: {stats['mean_aqi']}  Median: {stats['median_aqi']}")
    print(f"Range: {stats['min_aqi']} - {stats['max_aqi']}")
    print(f"Days at Unhealthy or worse (AQI > 150): {stats['days_unhealthy_or_worse']} / {stats['total_days']}")

    print("\n=== Category breakdown ===")
    for category, count in category_breakdown(df).items():
        print(f"  {category:<32} {count:>3} days")

    print("\n=== Top 5 worst days ===")
    for _, row in top_n_days(df, n=5, worst=True).iterrows():
        print(f"  {row['date'].date()}  AQI {row['aqi']:.1f}  ({row['category']})")

    print("\n=== Top 5 best days ===")
    for _, row in top_n_days(df, n=5, worst=False).iterrows():
        print(f"  {row['date'].date()}  AQI {row['aqi']:.1f}  ({row['category']})")

    if args.chart:
        plot_trend(df, args.chart)
        print(f"\nSaved trend chart to {args.chart}")


if __name__ == "__main__":
    main()
