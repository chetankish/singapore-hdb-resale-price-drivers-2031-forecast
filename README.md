# Singapore HDB Resale Price Drivers and 2031 Forecast

## Project Overview

This project analyses Singapore HDB resale flat prices and explores what resale prices could look like by 2031.

The project started from a personal question: how much might I need to pay for an HDB resale flat in the future? From there, it became a broader analysis of HDB resale price drivers, affordability pressure and forecasting.

The analysis is split into two parts:

1. Part 1 focuses on data preparation, market trends and price drivers.
2. Part 2 focuses on regression analysis, model comparison and 2031 forecasting.

## Business Question

How have HDB resale prices changed across time, flat type, town and remaining lease, and what does this suggest about resale affordability pressure by 2031?

## Supporting Questions

This project answers three supporting questions:

1. Where is resale price pressure coming from?
2. Which market segments should stakeholders monitor?
3. What could resale prices look like by 2031 under different modelling assumptions?

## Dataset

The dataset comes from the HDB resale flat price transactions collection on data.gov.sg.

Source: https://data.gov.sg/collections/189/view

The working dataset used for this project was updated as at 20 May 2026 and covers resale transactions from January 1990 to May 2026.

The full raw dataset is not uploaded here to keep the repository lightweight. Users can download the latest official data directly from data.gov.sg.

## Tools Used

- SQL for data checks, data cleaning and feature engineering
- Python for charts, forecasting, regression modelling, backtesting and diagnostics
- Excel for initial file inspection
- HTML report output for interactive visualisation

## Repository Structure

```text
data/
  data_source_notes.md

sql/
  README.md
  01_data_checks.sql
  02_cleaning_and_features.sql
  03_part1_analysis_outputs.sql
  04_segment_analysis.sql

python/
  README.md
  01_part1_charts_and_forecast.py
  02_part2_regression_models.py
  03_backtesting_and_diagnostics.py

requirements.txt
README.md
```

## Code Workflow

The code is organised in the same order as the analysis.

First, the SQL scripts check and clean the raw HDB resale dataset. This creates a cleaner dataset for analysis.

After that, the Python scripts use the cleaned data to create charts, calculate forecasts, run regression models, backtest the models and check diagnostics.

The code files are arranged in this order:

1. `sql/01_data_checks.sql`

   Checks the raw data for source coverage, missing values, duplicates and possible data issues.

2. `sql/02_cleaning_and_features.sql`

   Cleans the dataset and creates useful fields such as price per sqm, remaining lease years and million dollar transaction flag.

3. `sql/03_part1_analysis_outputs.sql`

   Creates the annual summary outputs used in Part 1.

4. `sql/04_segment_analysis.sql`

   Creates the flat type, town, lease and million dollar transaction segment outputs used in Part 1.

5. `python/01_part1_charts_and_forecast.py`

   Creates the Part 1 charts and baseline forecast outputs.

6. `python/02_part2_regression_models.py`

   Runs the Part 2 regression models and creates model comparison outputs.

7. `python/03_backtesting_and_diagnostics.py`

   Checks model accuracy, residuals, Durbin Watson and VIF diagnostics.

## Python Requirements

The required Python packages are listed in:

```text
requirements.txt
```

Install them using:

```bash
pip install -r requirements.txt
```

## Main Analysis Sections

### Part 1: Market Context, Data Preparation and Price Drivers

Part 1 explains the dataset, cleaning workflow and major resale price trends.

It covers:

- long run HDB resale price movement
- annual median resale price
- price per sqm
- transaction volume
- million dollar resale transactions
- flat type differences
- town differences
- remaining lease differences
- simple 2031 forecast sensitivity by starting year

Part 1 shows that resale price pressure does not come from time alone. It is also linked to flat type, town, floor area, remaining lease and transaction mix.

### Part 2: Regression Analysis and 2031 Forecasting

Part 2 uses regression analysis to test the relationships more formally.

It covers:

- raw simple regression
- semi log regression
- lagged semi log regression
- hedonic regression
- model comparison
- backtesting
- regression diagnostics
- VIF multicollinearity checks
- 2031 forecast interpretation

The regression models are used to compare different ways of forecasting HDB resale prices. The goal is not to produce one perfect number, but to understand how forecast results change depending on the model and assumptions used.

## Key Methods

### Historical Growth Projection

Used as a simple first estimate based on past resale price growth.

### Semi Log Regression

Used because housing prices often grow in percentage terms rather than by the same dollar amount every year.

### Lagged Semi Log Regression

Used because resale prices are linked over time. This years price may be partly influenced by last years price.

### Hedonic Regression

Used because resale price depends on flat characteristics, not just time. These characteristics include flat type, town, floor area, storey range, flat model and remaining lease.

### Backtesting

Used to check how well the models perform on data that was not used to fit the model.

### VIF Diagnostics

Used to check whether independent variables in the hedonic regression are too strongly related to each other.

As a general rule, VIF values below 5 are usually acceptable, values between 5 and 10 should be interpreted carefully, and values above 10 suggest serious multicollinearity.

## Notes On Interpretation

The 2031 forecasts should not be treated as certain predictions.

They depend on assumptions about:

- housing policy
- interest rates
- income growth
- inflation
- resale supply
- buyer demand
- flat type mix
- town mix
- remaining lease mix

For this reason, the project treats the forecast as a range rather than one exact answer.

## Current Status

The SQL and Python workflow has been added to the repository.

The final HTML reports will be added after Part 1 and Part 2 are fully reviewed and finalised.

## Author

Chetan
