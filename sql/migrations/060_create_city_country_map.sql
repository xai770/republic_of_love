-- Migration 060: Create city_country_map reference table
-- Date: 2025-12-02
-- Source: simplemaps worldcities basic v1.901

BEGIN;

-- Create reference table for city to country mapping
CREATE TABLE IF NOT EXISTS city_country_map (
    city_id BIGINT PRIMARY KEY,
    city TEXT NOT NULL,
    city_ascii TEXT NOT NULL,
    country TEXT NOT NULL,
    iso2 CHAR(2),
    iso3 CHAR(3),
    admin_name TEXT,
    lat NUMERIC(10, 6),
    lng NUMERIC(10, 6),
    population BIGINT
);

-- Create index for fast city lookup (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_city_country_map_city_ascii 
ON city_country_map (LOWER(city_ascii));

CREATE INDEX IF NOT EXISTS idx_city_country_map_city 
ON city_country_map (LOWER(city));

COMMIT;
