"""
Singapore HDB Resale Price Drivers and 2031 Forecast

03_backtesting_and_diagnostics.py

This script checks model accuracy and diagnostics for Part 2.

It prepares:
1. Backtesting results
2. RMSE and MAE comparison
3. Durbin Watson autocorrelation checks
4. VIF multicollinearity checks
5. Residual output tables

Run this after the raw combined HDB resale data has been placed in the data folder.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = PROJECT_ROOT / "data" / "Raw Data Combined.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "part2"
DIAGNOSTICS_DIR = OUTPUT_DIR / "diagnostics"

DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise column names.

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
    Convert a column into numeric values.
    """
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


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

df["resale_price"] = to_number(df["resale_price"])
df["floor_area_sqm"] = to_number(df["floor_area_sqm"])

for col in ["town", "flat_type", "flat_model", "storey_range"]:
    df[col] = df[col].astype(str).str.strip().str.upper()

if "remaining_lease" in df.columns:
    df["remaining_lease_years"] = df["remaining_lease"].apply(parse_remaining_lease)
else:
    df["lease_commence_date"] = to_number(df["lease_commence_date"])
    df["remaining_lease_years"] = 99 - (df["year"] - df["lease_commence_date"])

df["log_resale_price"] = np.log(df["resale_price"])

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
# 4. Annual data for time based models
# ---------------------------------------------------------

annual = (
    df_complete
    .groupby("year", as_index=False)
    .agg(median_price=("resale_price", "median"))
    .sort_values("year")
)

annual["log_median_price"] = np.log(annual["median_price"])
annual["lagged_log_median_price"] = annual["log_median_price"].shift(1)


# ---------------------------------------------------------
# 5. Backtesting setup
# ---------------------------------------------------------

# Train on 1990 to 2020, test on 2021 to 2025.
# This checks how the models perform on years that were not used for fitting.
train = annual[annual["year"] <= 2020].copy()
test = annual[(annual["year"] >= 2021) & (annual["year"] <= 2025)].copy()

backtest_rows = []


# ---------------------------------------------------------
# 6. Backtest Model 1: raw simple regression
# ---------------------------------------------------------

raw_model = smf.ols(
    formula="median_price ~ year",
    data=train
).fit()

test["raw_prediction"] = raw_model.predict(test)

backtest_rows.append({
    "model": "Raw simple regression",
    "test_period": "2021 to 2025",
    "rmse": rmse(test["median_price"], test["raw_prediction"]),
    "mae": mae(test["median_price"], test["raw_prediction"])
})


# ---------------------------------------------------------
# 7. Backtest Model 2: semi log regression
# ---------------------------------------------------------

semi_log_model = smf.ols(
    formula="log_median_price ~ year",
    data=train
).fit()

test["semi_log_prediction"] = np.exp(semi_log_model.predict(test))

backtest_rows.append({
    "model": "Semi log regression",
    "test_period": "2021 to 2025",
    "rmse": rmse(test["median_price"], test["semi_log_prediction"]),
    "mae": mae(test["median_price"], test["semi_log_prediction"])
})


# ---------------------------------------------------------
# 8. Backtest Model 3: lagged semi log regression
# ---------------------------------------------------------

train_lagged = train.dropna(subset=["lagged_log_median_price"]).copy()
test_lagged = annual[
    (annual["year"] >= 2021)
    & (annual["year"] <= 2025)
    & annual["lagged_log_median_price"].notna()
].copy()

lagged_model = smf.ols(
    formula="log_median_price ~ year + lagged_log_median_price",
    data=train_lagged
).fit()

test_lagged["lagged_prediction"] = np.exp(lagged_model.predict(test_lagged))

backtest_rows.append({
    "model": "Lagged semi log regression",
    "test_period": "2021 to 2025",
    "rmse": rmse(test_lagged["median_price"], test_lagged["lagged_prediction"]),
    "mae": mae(test_lagged["median_price"], test_lagged["lagged_prediction"])
})


# ---------------------------------------------------------
# 9. Save backtesting outputs
# ---------------------------------------------------------

backtesting_results = pd.DataFrame(backtest_rows)
backtesting_results.to_csv(
    DIAGNOSTICS_DIR / "backtesting_results_2021_to_2025.csv",
    index=False
)

test.to_csv(
    DIAGNOSTICS_DIR / "backtesting_predictions_time_models.csv",
    index=False
)

test_lagged.to_csv(
    DIAGNOSTICS_DIR / "backtesting_predictions_lagged_model.csv",
    index=False
)


# ---------------------------------------------------------
# 10. Full sample diagnostics for time based models
# ---------------------------------------------------------

raw_full = smf.ols(
    formula="median_price ~ year",
    data=annual
).fit()

semi_log_full = smf.ols(
    formula="log_median_price ~ year",
    data=annual
).fit()

lagged_full_data = annual.dropna(subset=["lagged_log_median_price"]).copy()

lagged_full = smf.ols(
    formula="log_median_price ~ year + lagged_log_median_price",
    data=lagged_full_data
).fit()

diagnostic_rows = [
    {
        "model": "Raw simple regression",
        "durbin_watson": durbin_watson(raw_full.resid),
        "r_squared": raw_full.rsquared,
        "adjusted_r_squared": raw_full.rsquared_adj
    },
    {
        "model": "Semi log regression",
        "durbin_watson": durbin_watson(semi_log_full.resid),
        "r_squared": semi_log_full.rsquared,
        "adjusted_r_squared": semi_log_full.rsquared_adj
    },
    {
        "model": "Lagged semi log regression",
        "durbin_watson": durbin_watson(lagged_full.resid),
        "r_squared": lagged_full.rsquared,
        "adjusted_r_squared": lagged_full.rsquared_adj
    }
]

diagnostics = pd.DataFrame(diagnostic_rows)

diagnostics.to_csv(
    DIAGNOSTICS_DIR / "time_model_diagnostics.csv",
    index=False
)


# ---------------------------------------------------------
# 11. Save residuals for checking
# ---------------------------------------------------------

annual["raw_residual"] = raw_full.resid
annual["semi_log_residual_original_dollars"] = (
    annual["median_price"] - np.exp(semi_log_full.predict(annual))
)

lagged_full_data["lagged_residual_original_dollars"] = (
    lagged_full_data["median_price"] - np.exp(lagged_full.predict(lagged_full_data))
)

annual.to_csv(
    DIAGNOSTICS_DIR / "raw_and_semi_log_residuals.csv",
    index=False
)

lagged_full_data.to_csv(
    DIAGNOSTICS_DIR / "lagged_model_residuals.csv",
    index=False
)


# ---------------------------------------------------------
# 12. VIF check for hedonic regression numeric variables
# ---------------------------------------------------------

# VIF checks whether predictors are strongly related to each other.
# As a general rule:
# below 5 = usually acceptable
# 5 to 10 = interpret carefully
# above 10 = serious multicollinearity concern
#
# This check focuses on the main numeric predictors in the hedonic model.
# Categorical variables are handled with reference categories in the regression.

vif_data = df_complete[
    ["year", "floor_area_sqm", "remaining_lease_years"]
].dropna().copy()

vif_data = vif_data.astype(float)

vif_data_with_constant = vif_data.copy()
vif_data_with_constant["constant"] = 1.0

vif_rows = []

for i, column in enumerate(vif_data_with_constant.columns):
    if column == "constant":
        continue

    vif_value = variance_inflation_factor(
        vif_data_with_constant.values,
        i
    )

    if vif_value < 5:
        interpretation = "Usually acceptable"
    elif vif_value < 10:
        interpretation = "Interpret carefully"
    else:
        interpretation = "Serious multicollinearity concern"

    vif_rows.append({
        "variable": column,
        "vif": vif_value,
        "interpretation": interpretation
    })

vif_results = pd.DataFrame(vif_rows)

vif_results.to_csv(
    DIAGNOSTICS_DIR / "vif_numeric_predictors.csv",
    index=False
)


# ---------------------------------------------------------
# 13. Print summary for checking
# ---------------------------------------------------------

print("Backtesting and diagnostics outputs created successfully.")
print()
print("Backtesting results:")
print(backtesting_results)
print()
print("Time model diagnostics:")
print(diagnostics)
print()
print("VIF results:")
print(vif_results)
print()
print("Outputs saved in:")
print(DIAGNOSTICS_DIR)
