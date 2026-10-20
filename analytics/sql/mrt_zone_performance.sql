-- mrt_zone_performance: Daily volume, median duration, and failure rate per zone
SELECT
    dropoff_zone_id AS zone_id,
    CURRENT_DATE AS metric_date,
    COUNT(*) AS total_deliveries
FROM silver_deliveries
GROUP BY dropoff_zone_id;
