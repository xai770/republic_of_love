-- Add hash index on embeddings.text for fast equality lookups.
-- Without this, queries like:
--   WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = normalize_text_python(...))
-- do a full sequential scan of 318K rows for every posting (~178K postings).
-- A hash index is ideal here: equality-only, no size limit on the text value.

CREATE INDEX CONCURRENTLY IF NOT EXISTS embeddings_text_idx
    ON embeddings USING hash (text);
