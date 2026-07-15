-- Singapore HDB Resale Price Drivers and 2031 Forecast
-- 01_data_checks.sql
-- This script checks the raw combined HDB resale dataset before cleaning.
-- Input table: "Raw Data Combined"

-- Check how many records came from each source period
DROP VIEW IF EXISTS qa_source_coverage;

CREATE VIEW qa_source_coverage AS
SELECT
    source_period,
    COUNT(*) AS transaction_count,
    MIN("Year-Month") AS first_month,
    MAX("Year-Month") AS last_month
FROM "Raw Data Combined"
GROUP BY source_period
ORDER BY first_month;


-- Check the overall time coverage of the combined dataset
DROP VIEW IF EXISTS qa_overall_coverage;

CREATE VIEW qa_overall_coverage AS
SELECT
    COUNT(*) AS total_transactions,
    MIN("Year-Month") AS first_month,
    MAX("Year-Month") AS last_month,
    MIN("Year") AS first_year,
    MAX("Year") AS last_year
FROM "Raw Data Combined";


-- Check missing values in important columns
DROP VIEW IF EXISTS qa_missing_values;

CREATE VIEW qa_missing_values AS
SELECT 'source_period' AS column_name, COUNT(*) AS missing_count
FROM "Raw Data Combined"
WHERE source_period IS NULL OR TRIM(source_period) = ''

UNION ALL
SELECT 'Year-Month', COUNT(*)
FROM "Raw Data Combined"
WHERE "Year-Month" IS NULL OR TRIM("Year-Month") = ''

UNION ALL
SELECT 'Year', COUNT(*)
FROM "Raw Data Combined"
WHERE "Year" IS NULL

UNION ALL
SELECT 'Month', COUNT(*)
FROM "Raw Data Combined"
WHERE "Month" IS NULL

UNION ALL
SELECT 'town', COUNT(*)
FROM "Raw Data Combined"
WHERE town IS NULL OR TRIM(town) = ''

UNION ALL
SELECT 'flat_type', COUNT(*)
FROM "Raw Data Combined"
WHERE flat_type IS NULL OR TRIM(flat_type) = ''

UNION ALL
SELECT 'storey_range', COUNT(*)
FROM "Raw Data Combined"
WHERE storey_range IS NULL OR TRIM(storey_range) = ''

UNION ALL
SELECT 'floor_area_sqm', COUNT(*)
FROM "Raw Data Combined"
WHERE floor_area_sqm IS NULL

UNION ALL
SELECT 'flat_model', COUNT(*)
FROM "Raw Data Combined"
WHERE flat_model IS NULL OR TRIM(flat_model) = ''

UNION ALL
SELECT 'lease_commence_date', COUNT(*)
FROM "Raw Data Combined"
WHERE lease_commence_date IS NULL

UNION ALL
SELECT 'resale_price', COUNT(*)
FROM "Raw Data Combined"
WHERE resale_price IS NULL

UNION ALL
SELECT 'remaining_lease_years', COUNT(*)
FROM "Raw Data Combined"
WHERE remaining_lease_years IS NULL;


-- Check impossible or invalid numeric values
DROP VIEW IF EXISTS qa_invalid_numeric_values;

CREATE VIEW qa_invalid_numeric_values AS
SELECT
    COUNT(*) AS invalid_numeric_records
FROM "Raw Data Combined"
WHERE resale_price <= 0
   OR floor_area_sqm <= 0
   OR lease_commence_date <= 0
   OR "Year" < 1990
   OR "Month" NOT BETWEEN 1 AND 12;


-- Check exact duplicate rows
DROP VIEW IF EXISTS qa_duplicate_rows;

CREATE VIEW qa_duplicate_rows AS
SELECT
    source_period,
    "Year-Month",
    town,
    flat_type,
    block,
    street_name,
    storey_range,
    floor_area_sqm,
    flat_model,
    lease_commence_date,
    resale_price,
    COUNT(*) AS duplicate_count
FROM "Raw Data Combined"
GROUP BY
    source_period,
    "Year-Month",
    town,
    flat_type,
    block,
    street_name,
    storey_range,
    floor_area_sqm,
    flat_model,
    lease_commence_date,
    resale_price
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;


-- Check remaining lease values
DROP VIEW IF EXISTS qa_remaining_lease_issues;

CREATE VIEW qa_remaining_lease_issues AS
SELECT
    "Year-Month" AS transaction_month,
    town,
    flat_type,
    lease_commence_date,
    remaining_lease_years
FROM "Raw Data Combined"
WHERE remaining_lease_years IS NULL
   OR remaining_lease_years <= 0
   OR remaining_lease_years > 99;


-- Check that 2026 is incomplete
DROP VIEW IF EXISTS qa_incomplete_2026_check;

CREATE VIEW qa_incomplete_2026_check AS
SELECT
    "Year" AS transaction_year,
    MIN("Year-Month") AS first_month,
    MAX("Year-Month") AS last_month,
    COUNT(*) AS transaction_count,
    ROUND(AVG(resale_price), 0) AS average_resale_price
FROM "Raw Data Combined"
WHERE "Year" = 2026
GROUP BY "Year";
