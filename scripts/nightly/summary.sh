#!/bin/bash
# =============================================================================
# SUMMARY - Final stats after pipeline run
# =============================================================================

source "$(dirname "$0")/common.sh"

log "Pipeline complete. Summary:"
python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    cur.execute(\"SELECT COUNT(*) as cnt FROM postings WHERE source = 'arbeitsagentur'\")
    aa_postings = cur.fetchone()['cnt']
    
    cur.execute(\"SELECT COUNT(*) as cnt FROM postings WHERE source = 'deutsche_bank'\")
    db_postings = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings')
    total_postings = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND LENGTH(job_description) > 100')
    with_desc = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE extracted_summary IS NOT NULL')
    with_summary = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE berufenet_id IS NOT NULL')
    with_berufenet = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM embeddings')
    embeds = cur.fetchone()['cnt']
    
    cur.execute('''
        SELECT COUNT(*) as cnt FROM postings_for_matching p 
        WHERE NOT EXISTS (
            SELECT 1 FROM embeddings e 
            WHERE e.text = p.match_text
        )
    ''')
    pending = cur.fetchone()['cnt']
    
    beruf_pct = round(100 * with_berufenet / total_postings, 1) if total_postings > 0 else 0
    
    print(f'  AA postings:      {aa_postings:,}')
    print(f'  DB postings:      {db_postings:,}')
    print(f'  Total postings:   {total_postings:,}')
    print(f'  With description: {with_desc:,}')
    print(f'  With summary:     {with_summary:,}')
    print(f'  With berufenet:   {with_berufenet:,} ({beruf_pct}%)')
    print(f'  Embeddings:       {embeds:,}')
    print(f'  Pending embed:    {pending:,}')
"
