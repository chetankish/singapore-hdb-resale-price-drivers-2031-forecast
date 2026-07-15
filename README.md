# Singapore HDB Resale Price Drivers and 2031 Forecast

## Project Overview

This project analyses Singapore HDB resale flat prices and explores what resale prices could look like by 2031.

The project started from a personal question: how much might I need to pay for an HDB resale flat in the future? From there, it became a broader analysis of HDB resale price drivers, affordability pressure and forecasting.

The analysis is split into two parts:

- Part 1 focuses on data preparation, market trends and price drivers.
- Part 2 focuses on regression analysis, model comparison and 2031 forecasting.

## Business Question

How have HDB resale prices changed across time, flat type, town and remaining lease, and what does this suggest about resale affordability pressure by 2031?

## Dataset

The dataset comes from the HDB resale flat price transactions collection on data.gov.sg.

Source: https://data.gov.sg/collections/189/view

The working dataset used for this project was updated as at 20 May 2026 and covers resale transactions from January 1990 to May 2026.

## Tools Used

- SQL for data cleaning, checks and feature engineering
- Python for analysis, charts and regression modelling
- HTML reports for presenting the final findings
- GitHub for organising the project files

## Project Workflow

1. Combined the HDB resale transaction files.
2. Checked data coverage, missing values, duplicates and invalid values.
3. Cleaned and standardised key fields such as town, flat type, floor area, resale price and remaining lease.
4. Created analysis variables such as price per square metre and million dollar transaction flag.
5. Analysed long term price trends, flat type differences, town patterns and remaining lease effects.
6. Built simple projection and regression based forecasts for 2031.
7. Compared model outputs and explained the limitations of each approach.

## Key Analysis Areas

- Long term HDB resale price trend
- Price per square metre comparison
- Million dollar resale transaction share
- Flat type comparison
- Town based price differences
- Remaining lease effect
- 2031 forecast sensitivity
- Regression based model comparison

## Repository Structure

```text
singapore-hdb-resale-price-drivers-2031-forecast/
│
├── README.md
├── data/
│   └── data_source_notes.md
│
├── sql/
│   ├── 01_data_checks.sql
│   ├── 02_cleaning_and_features.sql
│   ├── 03_part1_analysis_outputs.sql
│   └── 04_segment_analysis.sql
│
├── python/
├── reports/
└── charts/
