# SQL Workflow

This folder contains the SQL scripts used to check, clean and prepare the HDB resale dataset before analysis.

The scripts should be run in order:

1. `01_data_checks.sql`
2. `02_cleaning_and_features.sql`
3. `03_part1_analysis_outputs.sql`
4. `04_segment_analysis.sql`

## 01_data_checks.sql

Checks the raw combined dataset before cleaning.

This script checks:

- source file coverage
- overall date range
- missing values
- invalid numeric values
- duplicate rows
- remaining lease issues
- incomplete 2026 records

## 02_cleaning_and_features.sql

Creates the cleaned working table called `hdb_resale_clean`.

This script:

- standardises text fields such as town, flat type, street name and flat model
- creates transaction year and month fields
- creates storey midpoint
- creates price per square metre
- estimates remaining lease years where needed
- creates a million dollar transaction flag
- marks 2026 as an incomplete year

## 03_part1_analysis_outputs.sql

Creates the main annual outputs used in Part 1.

This script prepares:

- annual transaction counts
- annual median resale prices
- annual median price per square metre
- 2031 forecast sensitivity by starting year
- summary statistics for the 2031 forecast spread

## 04_segment_analysis.sql

Creates segment analysis outputs used in Part 1.

This script prepares:

- million dollar transaction share by year
- 2025 flat type comparison
- 2025 town comparison
- 2025 remaining lease band comparison

## Notes

The SQL scripts assume that the raw combined HDB resale data has already been imported into SQLite as a table named:

`Raw Data Combined`

The SQL workflow supports the data preparation and descriptive analysis sections of the report.
