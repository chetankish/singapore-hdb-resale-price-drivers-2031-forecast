/*
Singapore HDB Resale Price Drivers and 2031 Forecast
04_segment_analysis.sql

This script creates the segment analysis outputs used in Part 1.
It uses the cleaned table created in 02_cleaning_and_features.sql.
Input table: hdb_resale_clean
*/


/*
Million dollar resale transactions by year.
The share is useful because counts alone can rise when total transaction volume rises.
*/

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


/*
Flat type comparison for 2025.
This supports the flat type discussion in Part 1.
*/

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


/*
Town comparison for 2025.
Town is used as a practical location signal because exact amenity distances are not in the dataset.
*/

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


/*
Remaining lease bands for 2025.
This supports the discussion that remaining lease matters because HDB flats have finite leases.
*/

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
