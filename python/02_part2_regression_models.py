"""
Singapore HDB Resale Price Drivers and 2031 Forecast

02_part2_regression_models.py

This script runs the main regression models used in Part 2.

It prepares:
1. Raw simple regression
2. Semi log regression
3. Lagged semi log regression
4. Hedonic regression
5. Model comparison output
6. 2031 forecast examples

Run this after the raw combined HDB resale data has been placed in the data folder.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "Raw Data Combined.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "part2"
TABLE_DIR = OUTPUT_DIR / "tables"

TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise column names so they are easier to use in Python.

    Example:
    'Year-Month' becomes 'year_month'
    'floor area sqm' becomes 'floor_area_sqm'
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
    Convert a column into numbers.
    """
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


def format_money(value: float) -> str:
    """
    Format a number as Singapore dollars.
    """
    return f"S${value:,.0f}"


def rmse(actual, predicted) -> float:
    """
    Root mean squared error.
    """
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mae(actual, predicted) -> float:
    """
    Mean absolute error.
    """
    return float(np.mean(np.abs(actual - predicted)))


def parse_remaining_lease(value):
    """
    Convert remaining lease text into years.

    Example:
    '61 years 04 months' becomes about 61.33
    """
    if pd.isna(value):
        return np.nan

    text = str(value).lower().strip()

    years = 0
    months = 0

    parts = text.split()

    for i, part in enumerate(parts):
        if part.startswith("year") and i > 0:
            years = int(parts[i - 1])
        if part.startswith("month") and i > 0:
            months = int(parts[i - 1])

    if years == 0 and months == 0:
        return np.nan

    return years + months / 12


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

required_columns = [
    "year",
    "resale_price",
    "floor_area_sqm",
    "town",
    "flat_type",
    "flat_model",
    "storey_range"
]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

df["year"] = to_number(df["year"]).astype("Int64")
df["resale_price"] = to_number(df["resale_price"])
df["floor_area_sqm"] = to_number(df["floor_area_sqm"])

for col in ["town", "flat_type", "flat_model", "storey_range"]:
    df[col] = df[col].astype(str).str.strip().str.upper()

# Create remaining lease years.
# If the raw remaining_lease column exists, use it.
# If not, estimate remaining lease from lease_commence_date.
if "remaining_lease" in df.columns:
    df["remaining_lease_years"] = df["remaining_lease"].apply(parse_remaining_lease)
else:
    df["lease_commence_date"] = to_number(df["lease_commence_date"])
    df["remaining_lease_years"] = 99 - (df["year"] - df["lease_commence_date"])

df["price_per_sqm"] = df["resale_price"] / df["floor_area_sqm"]
df["log_resale_price"] = np.log(df["resale_price"])

# Exclude 2026 because it is incomplete.
df_complete = df[
    (df["year"] <= 2025)
    & df["year"].notna()
    & df["resale_price"].notna()
    & df["floor_area_sqm"].notna()
    & df["remaining_lease_years"].notna()
    & (df["resale_price"] > 0)
    & (df["floor_area_sqm"] > 0)
].copy()


# ---------------------------------------------------------
# 4. Annual median data for time based models
# ---------------------------------------------------------

annual = (
    df_complete
    .groupby("year", as_index=False)
    .agg(
        transaction_count=("resale_price", "size"),
        median_price=("resale_price", "median")
    )
    .sort_values("year")
)

annual["log_median_price"] = np.log(annual["median_price"])
annual["lagged_log_median_price"] = annual["log_median_price"].shift(1)

annual.to_csv(TABLE_DIR / "annual_median_prices_for_regression.csv", index=False)


# ---------------------------------------------------------
# 5. Model 1: raw simple regression
# ---------------------------------------------------------

raw_model = smf.ols(
    formula="median_price ~ year",
    data=annual
).fit()

forecast_year = 2031

raw_forecast = raw_model.predict(
    pd.DataFrame({"year": [forecast_year]})
)[0]

annual["raw_predicted_price"] = raw_model.predict(annual)

raw_results = {
    "model": "Raw simple regression",
    "equation": "median resale price = year",
    "r_squared": raw_model.rsquared,
    "adjusted_r_squared": raw_model.rsquared_adj,
    "rmse": rmse(annual["median_price"], annual["raw_predicted_price"]),
    "mae": mae(annual["median_price"], annual["raw_predicted_price"]),
    "forecast_2031": raw_forecast,
    "year_coefficient": raw_model.params["year"],
    "year_p_value": raw_model.pvalues["year"],
    "f_statistic": raw_model.fvalue
}


# ---------------------------------------------------------
# 6. Model 2: semi log regression
# ---------------------------------------------------------

semi_log_model = smf.ols(
    formula="log_median_price ~ year",
    data=annual
).fit()

semi_log_forecast_log = semi_log_model.predict(
    pd.DataFrame({"year": [forecast_year]})
)[0]

semi_log_forecast = np.exp(semi_log_forecast_log)

annual["semi_log_predicted_price"] = np.exp(semi_log_model.predict(annual))

semi_log_results = {
    "model": "Semi log regression",
    "equation": "log(median resale price) = year",
    "r_squared": semi_log_model.rsquared,
    "adjusted_r_squared": semi_log_model.rsquared_adj,
    "rmse": rmse(annual["median_price"], annual["semi_log_predicted_price"]),
    "mae": mae(annual["median_price"], annual["semi_log_predicted_price"]),
    "forecast_2031": semi_log_forecast,
    "year_coefficient": semi_log_model.params["year"],
    "year_p_value": semi_log_model.pvalues["year"],
    "f_statistic": semi_log_model.fvalue
}


# ---------------------------------------------------------
# 7. Model 3: lagged semi log regression
# ---------------------------------------------------------

lagged_data = annual.dropna(subset=["lagged_log_median_price"]).copy()

lagged_model = smf.ols(
    formula="log_median_price ~ year + lagged_log_median_price",
    data=lagged_data
).fit()

# Forecast recursively from 2026 to 2031.
last_log_price = annual.loc[annual["year"] == 2025, "log_median_price"].iloc[0]

lagged_forecasts = []

for year in range(2026, 2032):
    forecast_log_price = lagged_model.predict(
        pd.DataFrame({
            "year": [year],
            "lagged_log_median_price": [last_log_price]
        })
    )[0]

    forecast_price = np.exp(forecast_log_price)

    lagged_forecasts.append({
        "year": year,
        "forecast_price": forecast_price
    })

    last_log_price = forecast_log_price

lagged_forecast_table = pd.DataFrame(lagged_forecasts)
lagged_forecast_2031 = lagged_forecast_table.loc[
    lagged_forecast_table["year"] == 2031,
    "forecast_price"
].iloc[0]

lagged_data["lagged_predicted_price"] = np.exp(lagged_model.predict(lagged_data))

lagged_results = {
    "model": "Lagged semi log regression",
    "equation": "log(price this year) = year + log(price last year)",
    "r_squared": lagged_model.rsquared,
    "adjusted_r_squared": lagged_model.rsquared_adj,
    "rmse": rmse(lagged_data["median_price"], lagged_data["lagged_predicted_price"]),
    "mae": mae(lagged_data["median_price"], lagged_data["lagged_predicted_price"]),
    "forecast_2031": lagged_forecast_2031,
    "year_coefficient": lagged_model.params["year"],
    "year_p_value": lagged_model.pvalues["year"],
    "lagged_log_price_coefficient": lagged_model.params["lagged_log_median_price"],
    "lagged_log_price_p_value": lagged_model.pvalues["lagged_log_median_price"],
    "f_statistic": lagged_model.fvalue
}


# ---------------------------------------------------------
# 8. Model 4: hedonic regression
# ---------------------------------------------------------

# The hedonic model uses transaction level data.
# It controls for flat characteristics instead of using time only.
hedonic_data = df_complete[
    [
        "log_resale_price",
        "resale_price",
        "year",
        "floor_area_sqm",
        "remaining_lease_years",
        "town",
        "flat_type",
        "flat_model",
        "storey_range"
    ]
].dropna().copy()

hedonic_formula = (
    "log_resale_price ~ year + floor_area_sqm + remaining_lease_years "
    "+ C(town) + C(flat_type) + C(flat_model) + C(storey_range)"
)

hedonic_model = smf.ols(
    formula=hedonic_formula,
    data=hedonic_data
).fit()

hedonic_data["hedonic_predicted_price"] = np.exp(hedonic_model.predict(hedonic_data))

# Example controlled forecast:
# 93 sqm 4 ROOM Model A flat in 2031.
# Town is set to TAMPINES as a mainstream example.
controlled_example = pd.DataFrame({
    "year": [2031],
    "floor_area_sqm": [93],
    "remaining_lease_years": [70],
    "town": ["TAMPINES"],
    "flat_type": ["4 ROOM"],
    "flat_model": ["MODEL A"],
    "storey_range": ["07 TO 09"]
})

controlled_forecast_2031 = np.exp(
    hedonic_model.predict(controlled_example)
)[0]

hedonic_results = {
    "model": "Hedonic regression",
    "equation": "log(resale price) = year + flat characteristics + location controls",
    "r_squared": hedonic_model.rsquared,
    "adjusted_r_squared": hedonic_model.rsquared_adj,
    "rmse": rmse(hedonic_data["resale_price"], hedonic_data["hedonic_predicted_price"]),
    "mae": mae(hedonic_data["resale_price"], hedonic_data["hedonic_predicted_price"]),
    "forecast_2031": controlled_forecast_2031,
    "year_coefficient": hedonic_model.params["year"],
    "year_p_value": hedonic_model.pvalues["year"],
    "f_statistic": hedonic_model.fvalue
}


# ---------------------------------------------------------
# 9. Save model comparison outputs
# ---------------------------------------------------------

model_comparison = pd.DataFrame([
    raw_results,
    semi_log_results,
    lagged_results,
    hedonic_results
])

model_comparison.to_csv(TABLE_DIR / "model_comparison.csv", index=False)

lagged_forecast_table.to_csv(
    TABLE_DIR / "lagged_semi_log_forecast_2026_to_2031.csv",
    index=False
)

controlled_example["forecast_2031"] = controlled_forecast_2031

controlled_example.to_csv(
    TABLE_DIR / "hedonic_controlled_2031_forecast_example.csv",
    index=False
)


# ---------------------------------------------------------
# 10. Save coefficient summaries
# ---------------------------------------------------------

raw_model.summary2().tables[1].to_csv(TABLE_DIR / "raw_simple_regression_coefficients.csv")
semi_log_model.summary2().tables[1].to_csv(TABLE_DIR / "semi_log_regression_coefficients.csv")
lagged_model.summary2().tables[1].to_csv(TABLE_DIR / "lagged_semi_log_regression_coefficients.csv")
hedonic_model.summary2().tables[1].to_csv(TABLE_DIR / "hedonic_regression_coefficients.csv")


# ---------------------------------------------------------
# 11. Print summary for checking
# ---------------------------------------------------------

print("Part 2 regression outputs created successfully.")
print()
print("Model comparison:")
print(model_comparison[["model", "r_squared", "adjusted_r_squared", "rmse", "mae", "forecast_2031"]])
print()
print("Key 2031 forecasts:")
print(f"Raw simple regression: {format_money(raw_forecast)}")
print(f"Semi log regression: {format_money(semi_log_forecast)}")
print(f"Lagged semi log regression: {format_money(lagged_forecast_2031)}")
print(f"Hedonic controlled example: {format_money(controlled_forecast_2031)}")
print()
print("Outputs saved in:")
print(TABLE_DIR)
