-- PostGIS initialization & Full Operational Schema for Mzigo OLTP
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. zones
CREATE TABLE IF NOT EXISTS zones (
    zone_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    polygon GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_zones_polygon ON zones USING GIST (polygon);

-- 2. shops
CREATE TABLE IF NOT EXISTS shops (
    shop_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    zone_id VARCHAR(50) REFERENCES zones(zone_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_hash VARCHAR(64) NOT NULL,
    zone_id VARCHAR(50) REFERENCES zones(zone_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. riders
CREATE TABLE IF NOT EXISTS riders (
    rider_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. deliveries
CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id VARCHAR(50) PRIMARY KEY,
    shop_id VARCHAR(50) NOT NULL REFERENCES shops(shop_id),
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    rider_id VARCHAR(50) REFERENCES riders(rider_id),
    pickup_point GEOMETRY(Point, 4326) NOT NULL,
    dropoff_point GEOMETRY(Point, 4326) NOT NULL,
    pickup_zone_id VARCHAR(50) REFERENCES zones(zone_id),
    dropoff_zone_id VARCHAR(50) REFERENCES zones(zone_id),
    status VARCHAR(30) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sla_minutes INT NOT NULL DEFAULT 45,
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_rider ON deliveries(rider_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_pickup_zone ON deliveries(pickup_zone_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_dropoff_zone ON deliveries(dropoff_zone_id);

-- Enforce REPLICA IDENTITY FULL for deliveries so CDC captures complete before images
ALTER TABLE deliveries REPLICA IDENTITY FULL;

-- 6. delivery_status_events
CREATE TABLE IF NOT EXISTS delivery_status_events (
    event_id VARCHAR(50) PRIMARY KEY,
    delivery_id VARCHAR(50) NOT NULL REFERENCES deliveries(delivery_id),
    from_status VARCHAR(30) NOT NULL,
    to_status VARCHAR(30) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_status_events_delivery ON delivery_status_events(delivery_id);

-- 7. rider_locations
CREATE TABLE IF NOT EXISTS rider_locations (
    ping_id VARCHAR(50) PRIMARY KEY,
    rider_id VARCHAR(50) NOT NULL REFERENCES riders(rider_id),
    delivery_id VARCHAR(50) REFERENCES deliveries(delivery_id),
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_locations_rider_time ON rider_locations(rider_id, recorded_at);

-- Seed Nairobi operational delivery zones
INSERT INTO zones (zone_id, name, polygon) VALUES
('ZONE_CBD', 'Nairobi Central Business District', ST_GeomFromText('POLYGON((36.815 -1.280, 36.830 -1.280, 36.830 -1.295, 36.815 -1.295, 36.815 -1.280))', 4326)),
('ZONE_WESTLANDS', 'Westlands & Parklands', ST_GeomFromText('POLYGON((36.790 -1.250, 36.820 -1.250, 36.820 -1.275, 36.790 -1.275, 36.790 -1.250))', 4326)),
('ZONE_KILIMANI', 'Kilimani & Kileleshwa', ST_GeomFromText('POLYGON((36.770 -1.280, 36.805 -1.280, 36.805 -1.310, 36.770 -1.310, 36.770 -1.280))', 4326)),
('ZONE_UPPERHILL', 'Upper Hill & Community', ST_GeomFromText('POLYGON((36.805 -1.295, 36.825 -1.295, 36.825 -1.315, 36.805 -1.315, 36.805 -1.295))', 4326)),
('ZONE_IND_AREA', 'Industrial Area', ST_GeomFromText('POLYGON((36.830 -1.300, 36.870 -1.300, 36.870 -1.340, 36.830 -1.340, 36.830 -1.300))', 4326)),
('ZONE_EASTLANDS', 'Eastlands (Buruburu / Donholm)', ST_GeomFromText('POLYGON((36.865 -1.270, 36.920 -1.270, 36.920 -1.320, 36.865 -1.320, 36.865 -1.270))', 4326)),
('ZONE_KAREN', 'Karen Suburb', ST_GeomFromText('POLYGON((36.680 -1.310, 36.740 -1.310, 36.740 -1.360, 36.680 -1.360, 36.680 -1.310))', 4326))
ON CONFLICT (zone_id) DO NOTHING;

-- Seed representative shops
INSERT INTO shops (shop_id, name, zone_id) VALUES
('SHOP_CBD_01', 'Nairobi Electronics Hub', 'ZONE_CBD'),
('SHOP_WEST_01', 'Westlands Fashion Boutique', 'ZONE_WESTLANDS'),
('SHOP_KIL_01', 'Kilimani Gourmet Grocers', 'ZONE_KILIMANI')
ON CONFLICT (shop_id) DO NOTHING;

-- Seed representative customers
INSERT INTO customers (customer_id, name, phone_hash, zone_id) VALUES
('CUST_001', 'Wanjiku Kamau', 'e3b0c44298fc1c149afbf4c8', 'ZONE_WESTLANDS'),
('CUST_002', 'Otieno Ochieng', 'f2ca1bb6c7e907d06dafe468', 'ZONE_KILIMANI'),
('CUST_003', 'Amina Mohamed', '88d4266fd4e6338d13b845fe', 'ZONE_CBD')
ON CONFLICT (customer_id) DO NOTHING;

-- Seed initial fleet of 20 boda-boda riders
INSERT INTO riders (rider_id, name, phone_hash, status) VALUES
('RIDER_01', 'Juma Mwangi', '9f86d081884c7d659a2feaa0', 'available'),
('RIDER_02', 'Kevin Kiprop', '5e884898da28047151d0e56f', 'available'),
('RIDER_03', 'Brian Omondi', '4b227777d4dd1fc61c6f884f', 'available'),
('RIDER_04', 'David Njoroge', 'ef2d127de37b942baad06145', 'available'),
('RIDER_05', 'Dennis Mutua', 'd4735e3a265e16eee03f5971', 'available'),
('RIDER_06', 'Evans Barasa', '6b86b273ff34fce19d6b804e', 'available'),
('RIDER_07', 'Francis Wekesa', 'd04b98f48e8f8bcc15c6ae5e', 'available'),
('RIDER_08', 'Geoffrey Maina', '7b52009b64fd0a2a49e6d8a9', 'available'),
('RIDER_09', 'Hassan Ali', 'bd96449f81b7e052063d8650', 'available'),
('RIDER_10', 'Ian Kariuki', 'c9f0f895fb98ab9159f51fd0', 'available'),
('RIDER_11', 'John Rotich', 'e1a4d95226c6d042bc6f9d3b', 'available'),
('RIDER_12', 'Joseph Kimani', '81b7a2d480e6080fae6e9683', 'available'),
('RIDER_13', 'Kennedy Musyoka', '2c624232cdd221771294dfdb', 'available'),
('RIDER_14', 'Lucas Wafula', '19581e27de7ced00ff1ce50b', 'available'),
('RIDER_15', 'Moses Cheruiyot', '53c234e5e8472b6ac51c1ae1', 'available'),
('RIDER_16', 'Patrick Otieno', '6048d0856093cbfa2efb0365', 'available'),
('RIDER_17', 'Peter Karanja', '112e4f07a4a2512f45db7cb9', 'available'),
('RIDER_18', 'Samuel Koech', 'b51233519d1bb828357a79a5', 'available'),
('RIDER_19', 'Victor Ndungu', 'ec5539fa9516631ad0c46644', 'available'),
('RIDER_20', 'Vincent Kibet', '92eb5ffee6ae2fec3ad71c77', 'available')
ON CONFLICT (rider_id) DO NOTHING;

-- Publication for Debezium CDC
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'mzigo_publication') THEN
        CREATE PUBLICATION mzigo_publication FOR TABLE zones, shops, customers, riders, deliveries, delivery_status_events, rider_locations;
    END IF;
END $$;
