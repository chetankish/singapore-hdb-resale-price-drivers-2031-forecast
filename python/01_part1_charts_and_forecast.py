"""
Singapore HDB Resale Price Drivers and 2031 Forecast

01_part1_charts_and_forecast.py

This script creates the main Part 1 annual trend and baseline forecast outputs.

It prepares:
1. Annual median resale price
2. Annual median price per sqm
3. Table 1 forecast sensitivity by starting year
4. Table 2 forecast spread summary
5. Figure 1 annual median resale price chart
6. Figure 2 2031 forecast spread chart

Run this script after the raw combined HDB resale data has been placed in the data folder.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "Raw Data Combined.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "part1"
TABLE_DIR = OUTPUT_DIR / "tables"
CHART_DIR = OUTPUT_DIR / "charts"

TABLE_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise column names so that they are easier to use in Python.

    Example:
    ' resale_price ' becomes 'resale_price'
    'Year-Month' becomes 'year_month'
    ' price/sqm ' becomes 'price_sqm'
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^0-9a-z]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def to_number(series: pd.Series) -> pd.Series:
    """
    Convert a column into numeric values.

    This handles values that may contain commas, dollar signs or extra spaces.
    Example:
    ' 1,600,000.00 ' becomes 1600000.00
    """
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


def format_money(value: float) -> str:
    """Format a number as Singapore dollars."""
    return f"S${value:,.0f}"


def format_percent(value: float) -> str:
    """Format a decimal as a percentage."""
    return f"{value * 100:.1f}%"


# ---------------------------------------------------------
# 3. Load and prepare data
# ---------------------------------------------------------

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Data file not found: {DATA_PATH}\n"
        "Place 'Raw Data Combined.csv' inside the data folder, or update DATA_PATH."
    )

df = pd.read_csv(DATA_PATH, low_memory=False)
df = clean_column_names(df)

required_columns = ["year", "resale_price", "floor_area_sqm"]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

df["year"] = to_number(df["year"]).astype("Int64")
df["resale_price"] = to_number(df["resale_price"])
df["floor_area_sqm"] = to_number(df["floor_area_sqm"])

df["price_per_sqm"] = df["resale_price"] / df["floor_area_sqm"]

# 2026 is excluded because it is not a complete year.
df_complete = df[
    (df["year"] <= 2025)
    & df["year"].notna()
    & df["resale_price"].notna()
    & df["floor_area_sqm"].notna()
    & (df["floor_area_sqm"] > 0)
].copy()


# ---------------------------------------------------------
# 4. Annual median outputs
# ---------------------------------------------------------

annual = (
    df_complete
    .groupby("year", as_index=False)
    .agg(
        transaction_count=("resale_price", "size"),
        median_price=("resale_price", "median"),
        median_price_per_sqm=("price_per_sqm", "median")
    )
    .sort_values("year")
)

annual.to_csv(TABLE_DIR / "annual_medians.csv", index=False)


# ---------------------------------------------------------
# 5. Table 1: forecast sensitivity by starting year
# ---------------------------------------------------------

START_YEARS = [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2021, 2022, 2023, 2024]
END_YEAR = 2025
FORECAST_YEAR = 2031

annual_indexed = annual.set_index("year")

end_price = annual_indexed.loc[END_YEAR, "median_price"]
end_price_per_sqm = annual_indexed.loc[END_YEAR, "median_price_per_sqm"]

forecast_rows = []

for start_year in START_YEARS:
    start_price = annual_indexed.loc[start_year, "median_price"]
    start_price_per_sqm = annual_indexed.loc[start_year, "median_price_per_sqm"]

    years_between = END_YEAR - start_year
    years_forward = FORECAST_YEAR - END_YEAR

    price_change_to_2025 = (end_price / start_price) - 1
    price_cagr = (end_price / start_price) ** (1 / years_between) - 1

    price_per_sqm_change_to_2025 = (end_price_per_sqm / start_price_per_sqm) - 1
    price_per_sqm_cagr = (end_price_per_sqm / start_price_per_sqm) ** (1 / years_between) - 1

    forecast_2031 = end_price * (1 + price_cagr) ** years_forward

    forecast_rows.append({
        "start_year": start_year,
        "median_price": start_price,
        "median_price_per_sqm": start_price_per_sqm,
        "price_change_to_2025": price_change_to_2025,
        "annualised_price_increase": price_cagr,
        "price_per_sqm_change_to_2025": price_per_sqm_change_to_2025,
        "annualised_price_per_sqm_increase": price_per_sqm_cagr,
        "forecast_2031": forecast_2031
    })

forecast_table = pd.DataFrame(forecast_rows)

forecast_table.to_csv(TABLE_DIR / "table1_forecast_sensitivity.csv", index=False)


# ---------------------------------------------------------
# 6. Table 2: forecast spread summary
# ---------------------------------------------------------

forecasts = forecast_table["forecast_2031"]

forecast_summary = pd.DataFrame({
    "metric": [
        "Mean 2031 forecast",
        "Median 2031 forecast",
        "Minimum 2031 forecast",
        "Maximum 2031 forecast",
        "Standard deviation"
    ],
    "value": [
        forecasts.mean(),
        forecasts.median(),
        forecasts.min(),
        forecasts.max(),
        forecasts.std(ddof=0)
    ]
})

forecast_summary.to_csv(TABLE_DIR / "table2_forecast_spread_summary.csv", index=False)


# ---------------------------------------------------------
# 7. Figure 1: annual median resale price
# ---------------------------------------------------------

fig1 = go.Figure()

fig1.add_trace(
    go.Scatter(
        x=annual["year"],
        y=annual["median_price"],
        mode="lines+markers",
        name="Annual median resale price",
        hovertemplate=(
            "Year: %{x}<br>"
            "Median resale price: S$%{y:,.0f}"
            "<extra></extra>"
        )
    )
)

fig1.update_layout(
    title="Figure 1. Annual median HDB resale price, 1990 to 2025",
    template="plotly_white",
    height=460,
    showlegend=False,
    xaxis_title="Year",
    yaxis_title="Median resale price",
    margin=dict(l=60, r=30, t=70, b=50)
)

fig1.update_yaxes(tickprefix="S$", tickformat=",.0f")

fig1.write_html(
    CHART_DIR / "figure1_annual_median_resale_price.html",
    include_plotlyjs="cdn"
)


# ---------------------------------------------------------
# 8. Figure 2: forecast spread with mean and standard deviation lines
# ---------------------------------------------------------

mean_forecast = forecasts.mean()
sd_forecast = forecasts.std(ddof=0)

reference_lines = {
    "Mean": mean_forecast,
    "-1 SD": mean_forecast - sd_forecast,
    "+1 SD": mean_forecast + sd_forecast,
    "-2 SD": mean_forecast - 2 * sd_forecast,
    "+2 SD": mean_forecast + 2 * sd_forecast
}

# Small vertical offsets prevent the labels from overlapping too much.
y_offsets = [0.18, -0.12, -0.20, 0.10, 0.24, -0.08, 0.20, -0.18, 0.08, 0.16, -0.24]

fig2 = go.Figure()

fig2.add_trace(
    go.Scatter(
        x=forecast_table["forecast_2031"],
        y=y_offsets,
        mode="markers+text",
        text=forecast_table["forecast_2031"].apply(format_money),
        textposition="top center",
        customdata=forecast_table[["start_year"]],
        hovertemplate=(
            "Start year: %{customdata[0]}<br>"
            "2031 forecast: S$%{x:,.0f}"
            "<extra></extra>"
        ),
        showlegend=False
    )
)

# Main horizontal scale line
fig2.add_shape(
    type="line",
    x0=750000,
    x1=1050000,
    y0=0,
    y1=0,
    line=dict(width=2)
)

# Reference lines for mean and standard deviations
for label, x_value in reference_lines.items():
    fig2.add_shape(
        type="line",
        x0=x_value,
        x1=x_value,
        y0=-0.35,
        y1=0.35,
        line=dict(width=1, dash="dot")
    )

    fig2.add_annotation(
        x=x_value,
        y=0.39,
        text=label,
        showarrow=False,
        font=dict(size=11)
    )

fig2.update_layout(
    title="Figure 2. 2031 forecast spread from different starting years",
    template="plotly_white",
    height=460,
    showlegend=False,
    xaxis=dict(
        title="2031 forecast",
        range=[750000, 1050000],
        tickprefix="S$",
        tickformat=",.0f"
    ),
    yaxis=dict(
        visible=False,
        range=[-0.45, 0.45]
    ),
    margin=dict(l=50, r=30, t=80, b=55)
)

fig2.write_html(
    CHART_DIR / "figure2_2031_forecast_spread.html",
    include_plotlyjs="cdn"
)


# ---------------------------------------------------------
# 9. Print summary for checking
# ---------------------------------------------------------

print("Part 1 outputs created successfully.")
print()
print("Annual median output:")
print(TABLE_DIR / "annual_medians.csv")
print()
print("Forecast sensitivity table:")
print(TABLE_DIR / "table1_forecast_sensitivity.csv")
print()
print("Forecast spread summary:")
print(TABLE_DIR / "table2_forecast_spread_summary.csv")
print()
print("Charts:")
print(CHART_DIR / "figure1_annual_median_resale_price.html")
print(CHART_DIR / "figure2_2031_forecast_spread.html")
print()
print("Key forecast checks:")
print(f"Mean 2031 forecast: {format_money(mean_forecast)}")
print(f"Median 2031 forecast: {format_money(forecasts.median())}")
print(f"Lowest 2031 forecast: {format_money(forecasts.min())}")
print(f"Highest 2031 forecast: {format_money(forecasts.max())}")
print(f"Standard deviation: {format_money(sd_forecast)}")
