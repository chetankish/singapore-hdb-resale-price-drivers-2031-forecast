/*
Singapore HDB Resale Price Drivers and 2031 Forecast
SQL workflow for data preparation, checks and analysis outputs

Database: SQLite
Input table assumed: "Raw Data Combined"
*/

-- =========================================================
-- 1. Source coverage checks
-- =========================================================

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


DROP VIEW IF EXISTS qa_overall_coverage;

CREATE VIEW qa_overall_coverage AS
SELECT
    COUNT(*) AS total_transactions,
    MIN("Year-Month") AS first_month,
    MAX("Year-Month") AS last_month,
    MIN("Year") AS first_year,
    MAX("Year") AS last_year
FROM "Raw Data Combined";


-- =========================================================
-- 2. Data integrity checks
-- =========================================================

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


-- =========================================================
-- 3. Clean and standardise fields
-- =========================================================

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


CREATE INDEX IF NOT EXISTS idx_hdb_clean_year
ON hdb_resale_clean(transaction_year);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_flat_type
ON hdb_resale_clean(flat_type);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_town
ON hdb_resale_clean(town);

CREATE INDEX IF NOT EXISTS idx_hdb_clean_remaining_lease
ON hdb_resale_clean(remaining_lease_years);


-- =========================================================
-- 4. Annual market outputs, excluding incomplete 2026
-- =========================================================

DROP VIEW IF EXISTS analysis_annual_medians;

CREATE VIEW analysis_annual_medians AS
WITH
price_ranked AS (
    SELECT
        transaction_year,
        resale_price,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_year
            ORDER BY resale_price
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY transaction_year
        ) AS cnt
    FROM hdb_resale_clean
    WHERE transaction_year <= 2025
),

price_median AS (
    SELECT
        transaction_year,
        AVG(resale_price) AS median_resale_price
    FROM price_ranked
    WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY transaction_year
),

psqm_ranked AS (
    SELECT
        transaction_year,
        price_per_sqm,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_year
            ORDER BY price_per_sqm
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY transaction_year
        ) AS cnt
    FROM hdb_resale_clean
    WHERE transaction_year <= 2025
),

psqm_median AS (
    SELECT
        transaction_year,
        AVG(price_per_sqm) AS median_price_per_sqm
    FROM psqm_ranked
    WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY transaction_year
),

volume AS (
    SELECT
        transaction_year,
        COUNT(*) AS transaction_count
    FROM hdb_resale_clean
    WHERE transaction_year <= 2025
    GROUP BY transaction_year
)

SELECT
    v.transaction_year,
    v.transaction_count,
    ROUND(p.median_resale_price, 0) AS median_resale_price,
    ROUND(s.median_price_per_sqm, 0) AS median_price_per_sqm
FROM volume v
JOIN price_median p
    ON v.transaction_year = p.transaction_year
JOIN psqm_median s
    ON v.transaction_year = s.transaction_year
ORDER BY v.transaction_year;


-- =========================================================
-- 5. Simple projection sensitivity outputs
-- Used for Table 1 and Figure 2
-- =========================================================

DROP VIEW IF EXISTS analysis_2031_start_year_sensitivity;

CREATE VIEW analysis_2031_start_year_sensitivity AS
WITH
annual AS (
    SELECT *
    FROM analysis_annual_medians
),

base_2025 AS (
    SELECT
        median_resale_price AS price_2025,
        median_price_per_sqm AS psqm_2025
    FROM annual
    WHERE transaction_year = 2025
),

selected_start_years AS (
    SELECT *
    FROM annual
    WHERE transaction_year IN (
        1990, 1995, 2000, 2005, 2010,
        2015, 2020, 2021, 2022, 2023, 2024
    )
)

SELECT
    s.transaction_year AS start_year,
    ROUND(s.median_resale_price, 0) AS median_price,
    ROUND(s.median_price_per_sqm, 0) AS median_price_per_sqm,

    ROUND(
        ((b.price_2025 / s.median_resale_price) - 1) * 100,
        1
    ) AS price_change_to_2025_pct,

    ROUND(
        (
            POWER(
                b.price_2025 / s.median_resale_price,
                1.0 / (2025 - s.transaction_year)
            ) - 1
        ) * 100,
        2
    ) AS annualised_price_increase_pct,

    ROUND(
        ((b.psqm_2025 / s.median_price_per_sqm) - 1) * 100,
        1
    ) AS price_per_sqm_change_to_2025_pct,

    ROUND(
        (
            POWER(
                b.psqm_2025 / s.median_price_per_sqm,
                1.0 / (2025 - s.transaction_year)
            ) - 1
        ) * 100,
        2
    ) AS annualised_price_per_sqm_increase_pct,

    ROUND(
        b.price_2025
        * POWER(
            POWER(
                b.price_2025 / s.median_resale_price,
                1.0 / (2025 - s.transaction_year)
            ),
            6
        ),
        0
    ) AS forecast_2031

FROM selected_start_years s
CROSS JOIN base_2025 b
ORDER BY s.transaction_year;


DROP VIEW IF EXISTS analysis_2031_forecast_summary;

CREATE VIEW analysis_2031_forecast_summary AS
WITH
f AS (
    SELECT forecast_2031
    FROM analysis_2031_start_year_sensitivity
),

stats AS (
    SELECT
        MIN(forecast_2031) AS min_forecast,
        MAX(forecast_2031) AS max_forecast,
        AVG(forecast_2031) AS mean_forecast,
        COUNT(*) AS n
    FROM f
),

variance AS (
    SELECT
        AVG(
            (forecast_2031 - stats.mean_forecast)
            * (forecast_2031 - stats.mean_forecast)
        ) AS variance_forecast
    FROM f, stats
)

SELECT
    ROUND(stats.min_forecast, 0) AS minimum,
    ROUND(stats.max_forecast, 0) AS maximum,
    ROUND(stats.mean_forecast, 0) AS mean,

    (
        SELECT ROUND(AVG(forecast_2031), 0)
        FROM (
            SELECT
                forecast_2031,
                ROW_NUMBER() OVER (ORDER BY forecast_2031) AS rn,
                COUNT(*) OVER () AS cnt
            FROM f
        ) ranked
        WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    ) AS median,

    ROUND(variance.variance_forecast, 0) AS variance,
    ROUND(SQRT(variance.variance_forecast), 0) AS standard_deviation

FROM stats, variance;


-- =========================================================
-- 6. Market segment outputs
-- =========================================================

DROP VIEW IF EXISTS analysis_million_dollar_by_year;

CREATE VIEW analysis_million_dollar_by_year AS
SELECT
    transaction_year,
    COUNT(*) AS total_transactions,
    SUM(million_dollar_flag) AS million_dollar_transactions,
    ROUND(
        100.0 * SUM(million_dollar_flag) / COUNT(*),
        2
    ) AS million_dollar_share_pct
FROM hdb_resale_clean
WHERE transaction_year <= 2025
GROUP BY transaction_year
ORDER BY transaction_year;


DROP VIEW IF EXISTS analysis_flat_type_2025;

CREATE VIEW analysis_flat_type_2025 AS
WITH
ranked_price AS (
    SELECT
        flat_type,
        resale_price,
        ROW_NUMBER() OVER (
            PARTITION BY flat_type
            ORDER BY resale_price
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY flat_type
        ) AS cnt
    FROM hdb_resale_clean
    WHERE transaction_year = 2025
),

ranked_psqm AS (
    SELECT
        flat_type,
        price_per_sqm,
        ROW_NUMBER() OVER (
            PARTITION BY flat_type
            ORDER BY price_per_sqm
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY flat_type
        ) AS cnt
    FROM hdb_resale_clean
    WHERE transaction_year = 2025
),

volume AS (
    SELECT
        flat_type,
        COUNT(*) AS transaction_count
    FROM hdb_resale_clean
    WHERE transaction_year = 2025
    GROUP BY flat_type
)

SELECT
    v.flat_type,
    v.transaction_count,
    ROUND(AVG(rp.resale_price), 0) AS median_resale_price,
    ROUND(AVG(rs.price_per_sqm), 0) AS median_price_per_sqm
FROM volume v
JOIN ranked_price rp
    ON v.flat_type = rp.flat_type
   AND rp.rn IN ((rp.cnt + 1) / 2, (rp.cnt + 2) / 2)
JOIN ranked_psqm rs
    ON v.flat_type = rs.flat_type
   AND rs.rn IN ((rs.cnt + 1) / 2, (rs.cnt + 2) / 2)
GROUP BY
    v.flat_type,
    v.transaction_count
ORDER BY v.transaction_count DESC;


DROP VIEW IF EXISTS analysis_town_2025;

CREATE VIEW analysis_town_2025 AS
WITH
ranked AS (
    SELECT
        town,
        resale_price,
        price_per_sqm,

        ROW_NUMBER() OVER (
            PARTITION BY town
            ORDER BY resale_price
        ) AS price_rn,

        ROW_NUMBER() OVER (
            PARTITION BY town
            ORDER BY price_per_sqm
        ) AS psqm_rn,

        COUNT(*) OVER (
            PARTITION BY town
        ) AS cnt

    FROM hdb_resale_clean
    WHERE transaction_year = 2025
),

price_median AS (
    SELECT
        town,
        AVG(resale_price) AS median_resale_price
    FROM ranked
    WHERE price_rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY town
),

psqm_median AS (
    SELECT
        town,
        AVG(price_per_sqm) AS median_price_per_sqm
    FROM ranked
    WHERE psqm_rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
    GROUP BY town
),

volume AS (
    SELECT
        town,
        COUNT(*) AS transaction_count
    FROM hdb_resale_clean
    WHERE transaction_year = 2025
    GROUP BY town
)

SELECT
    v.town,
    v.transaction_count,
    ROUND(p.median_resale_price, 0) AS median_resale_price,
    ROUND(s.median_price_per_sqm, 0) AS median_price_per_sqm
FROM volume v
JOIN price_median p
    ON v.town = p.town
JOIN psqm_median s
    ON v.town = s.town
ORDER BY median_resale_price DESC;


DROP VIEW IF EXISTS analysis_remaining_lease_bands_2025;

CREATE VIEW analysis_remaining_lease_bands_2025 AS
SELECT
    CASE
        WHEN remaining_lease_years < 50 THEN '<50 years'
        WHEN remaining_lease_years BETWEEN 50 AND 59 THEN '50 to 59 years'
        WHEN remaining_lease_years BETWEEN 60 AND 69 THEN '60 to 69 years'
        WHEN remaining_lease_years BETWEEN 70 AND 79 THEN '70 to 79 years'
        WHEN remaining_lease_years BETWEEN 80 AND 89 THEN '80 to 89 years'
        ELSE '90 plus years'
    END AS remaining_lease_band,

    COUNT(*) AS transaction_count,
    ROUND(AVG(resale_price), 0) AS average_resale_price,
    ROUND(AVG(price_per_sqm), 0) AS average_price_per_sqm

FROM hdb_resale_clean
WHERE transaction_year = 2025
GROUP BY remaining_lease_band
ORDER BY MIN(remaining_lease_years);
