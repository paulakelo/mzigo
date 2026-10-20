-- PostGIS initialization & Nairobi operational delivery zones seed script
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS zones (
    zone_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    polygon GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zones_polygon ON zones USING GIST (polygon);

-- Insert representative Nairobi operational zones
INSERT INTO zones (zone_id, name, polygon) VALUES
('ZONE_CBD', 'Nairobi Central Business District', ST_GeomFromText('POLYGON((36.815 -1.280, 36.830 -1.280, 36.830 -1.295, 36.815 -1.295, 36.815 -1.280))', 4326)),
('ZONE_WESTLANDS', 'Westlands & Parklands', ST_GeomFromText('POLYGON((36.790 -1.250, 36.820 -1.250, 36.820 -1.275, 36.790 -1.275, 36.790 -1.250))', 4326)),
('ZONE_KILIMANI', 'Kilimani & Kileleshwa', ST_GeomFromText('POLYGON((36.770 -1.280, 36.805 -1.280, 36.805 -1.310, 36.770 -1.310, 36.770 -1.280))', 4326)),
('ZONE_UPPERHILL', 'Upper Hill & Community', ST_GeomFromText('POLYGON((36.805 -1.295, 36.825 -1.295, 36.825 -1.315, 36.805 -1.315, 36.805 -1.295))', 4326)),
('ZONE_IND_AREA', 'Industrial Area', ST_GeomFromText('POLYGON((36.830 -1.300, 36.870 -1.300, 36.870 -1.340, 36.830 -1.340, 36.830 -1.300))', 4326)),
('ZONE_EASTLANDS', 'Eastlands (Buruburu / Donholm)', ST_GeomFromText('POLYGON((36.865 -1.270, 36.920 -1.270, 36.920 -1.320, 36.865 -1.320, 36.865 -1.270))', 4326)),
('ZONE_KAREN', 'Karen Suburb', ST_GeomFromText('POLYGON((36.680 -1.310, 36.740 -1.310, 36.740 -1.360, 36.680 -1.360, 36.680 -1.310))', 4326))
ON CONFLICT (zone_id) DO NOTHING;
