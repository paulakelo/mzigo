-- mrt_rider_scorecard: Daily performance metrics per boda-boda rider
SELECT
    rider_id,
    CURRENT_DATE AS metric_date,
    COUNT(*) AS total_deliveries
FROM silver_deliveries
GROUP BY rider_id;
