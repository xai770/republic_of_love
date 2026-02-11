#!/bin/bash
# =============================================================================
# STEP 2: BACKFILL JOB DESCRIPTIONS
# =============================================================================
# Network-bound with parallelism: ~2 hours for 50K
# 
# 2a. AA backfill: Fetch job_description from arbeitsagentur.de
#     - 200 workers, VPN rotation, ~35K/hr
# 2b. Partner scrapers: External sites (jobvector, helixjobs, etc.)
#     - HTTP-first, ~500 postings in 10 min
# 2c. Invalidate: Mark postings we can't get descriptions for
# =============================================================================

source "$(dirname "$0")/common.sh"

# 2a. AA backfill (parallel HTTP fetch)
log "[2a/6] Backfilling missing job descriptions..."
setsid python3 actors/postings__aa_backfill_U.py \
    --include-partners \
    --batch-size 500 \
    --order newest \
    --limit 50000 \
    --workers 200 </dev/null

# 2b. External partner scrapers
log "[2b/6] Scraping external partner job descriptions..."
python3 actors/postings__external_partners_U.py --batch 500 </dev/null

# 2c. Invalidate postings we can't process
log "[2c/6] Invalidating postings without descriptions..."
python3 << 'PYEOF'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    dbname=os.environ.get('DB_NAME', 'turing'),
    user=os.environ.get('DB_USER', 'base_admin'),
    password=os.environ.get('DB_PASS', '${DB_PASSWORD}')
)
cur = conn.cursor()

# External partner jobs explicitly marked
cur.execute("""
    UPDATE postings 
    SET invalidated = true,
        invalidated_reason = 'no_description_external_partner',
        invalidated_at = NOW()
    WHERE job_description = '[EXTERNAL_PARTNER]'
      AND COALESCE(invalidated, false) = false
""")
partner_count = cur.rowcount

# Jobs with NULL description that have external URLs (no scraper available)
cur.execute("""
    UPDATE postings 
    SET invalidated = true,
        invalidated_reason = 'no_scraper_for_partner_site',
        invalidated_at = NOW()
    WHERE job_description IS NULL
      AND external_url IS NOT NULL
      AND external_url NOT LIKE %s
      AND COALESCE(invalidated, false) = false
""", ('%arbeitsagentur.de/jobsuche/jobdetail/%',))
no_scraper_count = cur.rowcount

# Jobs with NULL description on AA (old postings never backfilled, >7 days)
cur.execute("""
    UPDATE postings 
    SET invalidated = true,
        invalidated_reason = 'no_description_null',
        invalidated_at = NOW()
    WHERE (job_description IS NULL OR job_description = '')
      AND COALESCE(invalidated, false) = false
      AND first_seen_at < NOW() - INTERVAL '7 days'
      AND (external_url LIKE %s OR external_url IS NULL)
""", ('%arbeitsagentur.de/jobsuche/jobdetail/%',))
null_count = cur.rowcount

conn.commit()
conn.close()
print(f'  Invalidated: {partner_count} [EXTERNAL_PARTNER], {no_scraper_count} no scraper, {null_count} null/empty >7d')
PYEOF

log "Step 2 complete: backfill"
