-- Haversine distance macro for DuckDB (calculates great-circle distance in kilometers)
CREATE OR REPLACE MACRO haversine_km(lat1, lon1, lat2, lon2) AS (
    6371.0 * 2.0 * atan2(
        sqrt(
            sin(radians(lat2 - lat1) / 2.0) ^ 2 +
            cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2.0) ^ 2
        ),
        sqrt(
            1.0 - (
                sin(radians(lat2 - lat1) / 2.0) ^ 2 +
                cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2.0) ^ 2
            )
        )
    )
);
