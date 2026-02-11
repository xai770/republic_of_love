#!/bin/bash
# =============================================================================
# STEP 3: BERUFENET CLASSIFICATION
# =============================================================================
# SQL-bound: ~1 second for lookup, ~1 min for auto-matcher
#
# 3a. Fast lookup: beruf → berufenet (exact + synonym)
# 3b. Auto-matcher: Pattern + embedding for new professions
# =============================================================================

source "$(dirname "$0")/common.sh"

# 3a. Fast SQL lookup (instant)
log "[3a/6] Berufenet classification (fast lookup)..."
python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    # Exact match: beruf → berufenet.name
    cur.execute('''
        UPDATE postings p
        SET 
            berufenet_id = b.berufenet_id,
            berufenet_name = b.name,
            berufenet_kldb = b.kldb,
            berufenet_verified = 'lookup'
        FROM berufenet b
        WHERE LOWER(p.beruf) = LOWER(b.name)
          AND p.beruf IS NOT NULL
          AND p.berufenet_id IS NULL
    ''')
    exact = cur.rowcount
    
    # Synonym match: beruf → berufenet_synonyms → berufenet
    cur.execute('''
        UPDATE postings p
        SET 
            berufenet_id = bn.berufenet_id,
            berufenet_name = bn.name,
            berufenet_kldb = bn.kldb,
            berufenet_verified = 'synonym'
        FROM berufenet_synonyms s
        JOIN berufenet bn ON s.berufenet_id = bn.berufenet_id
        WHERE p.beruf = s.aa_beruf
          AND p.beruf IS NOT NULL
          AND p.berufenet_id IS NULL
    ''')
    synonym = cur.rowcount
    
    conn.commit()
    print(f'  Berufenet: {exact} exact + {synonym} synonym = {exact + synonym} classified')
"

# 3b. Auto-matcher for new professions
log "[3b/6] Auto-matching new professions..."
python3 tools/berufenet_auto_matcher.py --tier 1 </dev/null  # Pattern matching (instant)
python3 tools/berufenet_auto_matcher.py --tier 2 --limit 50 </dev/null  # Embedding matching (top 50)

log "Step 3 complete: classify"
