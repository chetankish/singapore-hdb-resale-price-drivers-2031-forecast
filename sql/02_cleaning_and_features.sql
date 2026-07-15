/*
Singapore HDB Resale Price Drivers and 2031 Forecast
02_cleaning_and_features.sql

This script creates the cleaned working table used for the analysis.
Input table: "Raw Data Combined"
*/

DROP TABLE IF EXISTS hdb_resale_clean;

CREATE TABLE hdb_resale_clean AS
SELECT
    source_period,

    "Year-Month" AS transaction_month,
    CAST("Year" AS INTEGER) AS transaction_year,
    CAST("Month" AS INTEGER) AS transaction_month_number,

    UPPER(TRIM(town)) AS town,
    UPPER(TRIM(flat_type)) AS flat_type,
    TRIM(CAST(block AS TEXT)) AS block,
    UPPER(TRIM(street_name)) AS street_name,
    UPPER(TRIM(storey_range)) AS storey_range,

    CAST(SUBSTR(storey_range, 1, 2) AS INTEGER) AS storey_min,
    CAST(SUBSTR(storey_range, 7, 2) AS INTEGER) AS storey_max,

    ROUND(
        (
            CAST(SUBSTR(storey_range, 1, 2) AS REAL)
            + CAST(SUBSTR(storey_range, 7, 2) AS REAL)
        ) / 2.0,
        1
    ) AS storey_mid,

    CAST(floor_area_sqm AS REAL) AS floor_area_sqm,
    UPPER(TRIM(flat_model)) AS flat_model,
    CAST(lease_commence_date AS INTEGER) AS lease_commence_year,
    CAST(resale_price AS REAL) AS resale_price,

    ROUND(
        CAST(resale_price AS REAL) / NULLIF(CAST(floor_area_sqm AS REAL), 0),
        2
    ) AS price_per_sqm,

    CAST(
        COALESCE(
            remaining_lease_years,
            99 - (CAST("Year" AS INTEGER) - CAST(lease_commence_date AS INTEGER))
        ) AS INTEGER
    ) AS remaining_lease_years,

    CASE
        WHEN resale_price >= 1000000 THEN 1
        ELSE 0
    END AS million_dollar_flag,

    CASE
        WHEN "Year" = 2026 THEN 1
        ELSE 0
    END AS incomplete_year_flag

FROM "Raw Data Combined"

WHERE resale_price > 0
  AND floor_area_sqm > 0
  AND lease_commence_date > 0
  AND "Year" BETWEEN 1990 AND 2026
  AND "Month" BETWEEN 1 AND 12;


/*
Indexes are added to make repeated filtering and grouping faster.
*/

CREATE INDEX IF NOT EXISTS idx_hdb_clean_year
ON hdb_resale_clean(transaction_year);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_flat_type
ON hdb_resale_clean(flat_type);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_town
ON hdb_resale_clean(town);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_remaining_lease
ON hdb_resale_clean(remaining_lease_years);


/*
Quick check of the cleaned table.
*/

DROP VIEW IF EXISTS qa_clean_table_summary;

CREATE VIEW qa_clean_table_summary AS
SELECT
    COUNT(*) AS cleaned_transactions,
    MIN(transaction_month) AS first_month,
    MAX(transaction_month) AS last_month,
    MIN(transaction_year) AS first_year,
    MAX(transaction_year) AS last_year,
    ROUND(MIN(resale_price), 0) AS min_resale_price,
    ROUND(MAX(resale_price), 0) AS max_resale_price,
    ROUND(AVG(price_per_sqm), 0) AS average_price_per_sqm
FROM hdb_resale_clean;
