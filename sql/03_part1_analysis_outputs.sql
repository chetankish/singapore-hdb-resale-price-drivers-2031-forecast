/*
Singapore HDB Resale Price Drivers and 2031 Forecast
03_part1_analysis_outputs.sql

This script creates the main annual outputs used in Part 1.
It uses the cleaned table created in 02_cleaning_and_features.sql.
Input table: hdb_resale_clean
*/


/*
Annual median resale price and median price per sqm
2026 is excluded because it is not a complete year.
*/

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


/*
Starting year sensitivity table.
This supports Table 1 and Figure 2 in Part 1.
*/

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


/*
Summary statistics for the 2031 forecast spread.
This supports Table 2 and the mean and standard deviation markers in Figure 2.
*/

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
    ROUND(SQRT(variance.variance_forecast), 0) AS standard_deviation,

    ROUND(stats.mean_forecast - SQRT(variance.variance_forecast), 0) AS minus_1_sd,
    ROUND(stats.mean_forecast + SQRT(variance.variance_forecast), 0) AS plus_1_sd,
    ROUND(stats.mean_forecast - 2 * SQRT(variance.variance_forecast), 0) AS minus_2_sd,
    ROUND(stats.mean_forecast + 2 * SQRT(variance.variance_forecast), 0) AS plus_2_sd

FROM stats, variance;
