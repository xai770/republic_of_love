#!/bin/bash
# =============================================================================
# STATUS CHECK - Show current pipeline state
# =============================================================================

source "$(dirname "$0")/common.sh"

echo "=== NIGHTLY FETCH STATUS ==="
echo ""

# Check if running
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$PID" 2>/dev/null; then
        echo "🔄 Pipeline RUNNING (PID $PID)"
        echo ""
        echo "Active processes:"
        ps aux | grep -E "arbeitsagentur|deutsche_bank|job_description|embedding|extracted_summary" | grep -v grep | awk '{print "  " $11 " " $12 " " $13}'
        echo ""
    else
        echo "⏹️  Pipeline NOT running (stale lock file)"
    fi
else
    echo "⏹️  Pipeline NOT running"
fi

# DB stats
echo "📊 Database Status:"
python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings')
    total = cur.fetchone()['cnt']
    
    cur.execute(\"\"\"SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND job_description != '[EXTERNAL_PARTNER]' AND LENGTH(job_description) > 100\"\"\")
    with_desc = cur.fetchone()['cnt']
    
    cur.execute(\"\"\"SELECT COUNT(*) as cnt FROM postings WHERE job_description = '[EXTERNAL_PARTNER]'\"\"\")
    external_partner = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings WHERE source = 'arbeitsagentur' AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100) AND COALESCE(invalidated, false) = false''')
    missing_desc = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings_for_matching')
    eligible = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings_for_matching p WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = p.match_text)''')
    pending_embed = cur.fetchone()['cnt']
    
    print(f'   Total postings:       {total:,}')
    print(f'   With description:     {with_desc:,}')
    print(f'   External partner:     {external_partner:,}')
    print(f'   Missing description:  {missing_desc:,}')
    print(f'   Eligible for match:   {eligible:,}')
    print(f'   Pending embeddings:   {pending_embed}')
"
echo ""

# Recent log
if [ -f /var/log/ty_nightly.log ]; then
    echo "📜 Recent log (last 10 lines):"
    tail -10 /var/log/ty_nightly.log | sed 's/^/   /'
fi
