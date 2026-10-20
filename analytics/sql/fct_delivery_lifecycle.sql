-- fct_delivery_lifecycle: Delivery stage dwell times and SLA compliance
SELECT
    delivery_id,
    shop_id,
    customer_id,
    rider_id,
    status,
    created_at,
    updated_at,
    sla_minutes
FROM silver_deliveries;
