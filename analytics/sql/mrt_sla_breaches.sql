-- mrt_sla_breaches: Deliveries that breached customer delivery SLA
SELECT
    delivery_id,
    shop_id,
    rider_id,
    sla_minutes
FROM silver_deliveries;
