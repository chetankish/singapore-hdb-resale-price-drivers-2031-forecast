"""
Singapore HDB Resale Price Drivers and 2031 Forecast

02_part2_regression_models.py

This script runs the main regression models used in Part 2.

It prepares:
1. Raw simple regression
2. Semi log regression
3. Lagged semi log regression
4. Hedonic regression using a year balanced sample
5. Model comparison output
6. Controlled 2031 town forecast
7. Controlled 2031 remaining lease forecast

Run this after the raw combined HDB resale data has been placed in the data folder.
"""

from pathlib import Path

import numpy as np
import pandas as pd
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
    parts = text.split()

    years = 0
    months = 0

    for i, part in enumerate(parts):
        if part.startswith("year") and i > 0:
            years = int(parts[i - 1])
        if part.startswith("month") and i > 0:
            months = int(parts[i - 1])

    if years == 0 and months == 0:
        return np.nan

    return years + months / 12


def add_year_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a year column if it does not already exist.
    """
    df = df.copy()

    if "year" in df.columns:
        df["year"] = to_number(df["year"]).astype("Int64")
        return df

    if "month" in df.columns:
        df["year"] = df["month"].astype(str).str[:4].astype("Int64")
        return df

    if "year_month" in df.columns:
        df["year"] = df["year_month"].astype(str).str[:4].astype("Int64")
        return df

    raise ValueError("No year, month or year_month column found.")


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
df = add_year_column(df)

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
# A year balanced sample is used so that each year from 1990 to 2025
# contributes the same number of transactions to the regression.
# 1,500 rows per year x 36 years = 54,000 transactions.

SAMPLE_PER_YEAR = 1500
RANDOM_STATE = 42

available_years = sorted(df_complete["year"].dropna().unique())

low_count_years = (
    df_complete
    .groupby("year")
    .size()
    .reset_index(name="transaction_count")
    .query("transaction_count < @SAMPLE_PER_YEAR")
)

if not low_count_years.empty:
    raise ValueError(
        "At least one year has fewer than 1,500 transactions. "
        "Reduce SAMPLE_PER_YEAR or check the dataset."
    )

hedonic_sample = (
    df_complete
    .groupby("year", group_keys=False)
    .apply(lambda g: g.sample(n=SAMPLE_PER_YEAR, random_state=RANDOM_STATE))
    .reset_index(drop=True)
)

hedonic_sample.to_csv(
    TABLE_DIR / "hedonic_year_balanced_sample_54000_rows.csv",
    index=False
)

hedonic_data = hedonic_sample[
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

# Controlled baseline used for the hedonic forecast examples.
# This matches the report controls:
# 93 sqm, 4 ROOM, Model A, 10 TO 12 storey range.
CONTROL_YEAR = 2031
CONTROL_FLOOR_AREA = 93
CONTROL_REMAINING_LEASE = 75
CONTROL_FLAT_TYPE = "4 ROOM"
CONTROL_FLAT_MODEL = "MODEL A"
CONTROL_STOREY_RANGE = "10 TO 12"
CONTROL_TOWN = "TAMPINES"

controlled_example = pd.DataFrame({
    "year": [CONTROL_YEAR],
    "floor_area_sqm": [CONTROL_FLOOR_AREA],
    "remaining_lease_years": [CONTROL_REMAINING_LEASE],
    "town": [CONTROL_TOWN],
    "flat_type": [CONTROL_FLAT_TYPE],
    "flat_model": [CONTROL_FLAT_MODEL],
    "storey_range": [CONTROL_STOREY_RANGE]
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
    "f_statistic": hedonic_model.fvalue,
    "sample_rows": len(hedonic_data)
}


# ---------------------------------------------------------
# 9. Table 10: controlled town forecast
# ---------------------------------------------------------

towns = [
    "WOODLANDS",
    "CHOA CHU KANG",
    "PUNGGOL",
    "TAMPINES",
    "QUEENSTOWN",
    "BISHAN",
    "BUKIT MERAH"
]

town_forecast_rows = []

for town in towns:
    example = pd.DataFrame({
        "year": [CONTROL_YEAR],
        "floor_area_sqm": [CONTROL_FLOOR_AREA],
        "remaining_lease_years": [CONTROL_REMAINING_LEASE],
        "town": [town],
        "flat_type": [CONTROL_FLAT_TYPE],
        "flat_model": [CONTROL_FLAT_MODEL],
        "storey_range": [CONTROL_STOREY_RANGE]
    })

    predicted_price = np.exp(hedonic_model.predict(example))[0]

    town_forecast_rows.append({
        "town": town,
        "year": CONTROL_YEAR,
        "floor_area_sqm": CONTROL_FLOOR_AREA,
        "remaining_lease_years": CONTROL_REMAINING_LEASE,
        "flat_type": CONTROL_FLAT_TYPE,
        "flat_model": CONTROL_FLAT_MODEL,
        "storey_range": CONTROL_STOREY_RANGE,
        "predicted_2031_price": predicted_price
    })

town_forecast_table = pd.DataFrame(town_forecast_rows)

town_forecast_table.to_csv(
    TABLE_DIR / "table10_controlled_town_forecast.csv",
    index=False
)


# ---------------------------------------------------------
# 10. Table 11: controlled remaining lease forecast
# ---------------------------------------------------------

lease_values = [45, 55, 65, 75, 85]

lease_forecast_rows = []

for lease_years in lease_values:
    example = pd.DataFrame({
        "year": [CONTROL_YEAR],
        "floor_area_sqm": [CONTROL_FLOOR_AREA],
        "remaining_lease_years": [lease_years],
        "town": [CONTROL_TOWN],
        "flat_type": [CONTROL_FLAT_TYPE],
        "flat_model": [CONTROL_FLAT_MODEL],
        "storey_range": [CONTROL_STOREY_RANGE]
    })

    predicted_price = np.exp(hedonic_model.predict(example))[0]

    lease_forecast_rows.append({
        "remaining_lease_years": lease_years,
        "year": CONTROL_YEAR,
        "town": CONTROL_TOWN,
        "floor_area_sqm": CONTROL_FLOOR_AREA,
        "flat_type": CONTROL_FLAT_TYPE,
        "flat_model": CONTROL_FLAT_MODEL,
        "storey_range": CONTROL_STOREY_RANGE,
        "predicted_2031_price": predicted_price
    })

lease_forecast_table = pd.DataFrame(lease_forecast_rows)

lease_forecast_table.to_csv(
    TABLE_DIR / "table11_controlled_remaining_lease_forecast.csv",
    index=False
)


# ---------------------------------------------------------
# 11. Save model comparison outputs
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
# 12. Save coefficient summaries
# ---------------------------------------------------------

raw_model.summary2().tables[1].to_csv(
    TABLE_DIR / "raw_simple_regression_coefficients.csv"
)

semi_log_model.summary2().tables[1].to_csv(
    TABLE_DIR / "semi_log_regression_coefficients.csv"
)

lagged_model.summary2().tables[1].to_csv(
    TABLE_DIR / "lagged_semi_log_regression_coefficients.csv"
)

hedonic_model.summary2().tables[1].to_csv(
    TABLE_DIR / "hedonic_regression_coefficients.csv"
)


# ---------------------------------------------------------
# 13. Print summary for checking
# ---------------------------------------------------------

print("Part 2 regression outputs created successfully.")
print()
print("Hedonic sample check:")
print(f"Rows used in hedonic model: {len(hedonic_data):,}")
print(f"Rows per year: {SAMPLE_PER_YEAR:,}")
print(f"Years sampled: {len(available_years)}")
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
print("Controlled town forecast table:")
print(town_forecast_table[["town", "predicted_2031_price"]])
print()
print("Controlled remaining lease forecast table:")
print(lease_forecast_table[["remaining_lease_years", "predicted_2031_price"]])
print()
print("Outputs saved in:")
print(TABLE_DIR)
