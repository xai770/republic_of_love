-- Simple Migration: Add batches table (Clean Version)
-- Date: 2025-10-05

-- Create batches table
CREATE TABLE batches (
    batch_id INTEGER PRIMARY KEY CHECK(batch_id BETWEEN 1 AND 5)
);

INSERT INTO batches (batch_id) VALUES (1), (2), (3), (4), (5);

-- Add batch_id to dishes and populate it
ALTER TABLE dishes ADD COLUMN batch_id INTEGER DEFAULT 1;

-- Assign batch numbers in a round-robin fashion based on ingredient_id and model_name
UPDATE dishes 
SET batch_id = ((ABS(RANDOM()) % 5) + 1)
WHERE batch_id IS NULL;