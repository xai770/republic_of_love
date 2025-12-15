# Gershon's Turing Cheat Sheet

**Version**: 1.1  
**Last Updated**: December 3, 2025  
**Purpose**: Quick reference for common Turing operations

---

## 🚀 Workflow Management

### Start/Resume Workflow 3001
```bash
# Resume pending work
python3 scripts/prod/run_workflow_3001.py --resume

# Fetch new jobs from Deutsche Bank API
python3 scripts/prod/run_workflow_3001.py --fetch --max-jobs 100

# Process specific posting
python3 scripts/prod/run_workflow_3001.py --posting-id 12345
```

### Monitor Workflow Progress
```bash
# Rainbow flowchart (detailed step-by-step)
python3 tools/_show_3001.py --once

# Continuous monitoring
python3 tools/_show_3001.py
```

### Check Logs
```bash
# Latest run log
tail -f logs/run_3001_resume.log
```

### Stop Workflow
```bash
pkill -f "run_workflow_3001"
```

---

## 🗄️ Database Operations

### Connect to Database
```bash
# PostgreSQL
psql -d turing

# Or using Python
python3 -c "
from core.database import get_connection, return_connection
conn = get_connection()
cursor = conn.cursor()
# ... your queries ...
return_connection(conn)
"
```

### Common Queries
```sql
-- Check workflow progress
SELECT 
    COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as with_summary,
    COUNT(*) FILTER (WHERE extracted_summary IS NULL) as no_summary,
    COUNT(*) as total
FROM postings 
WHERE enabled = TRUE;

-- Check posting state
SELECT 
    c.canonical_name,
    wc.execution_order,
    COUNT(*) as count
FROM posting_state_checkpoints psc
JOIN postings p ON psc.posting_id = p.posting_id
LEFT JOIN conversations c ON (psc.state_snapshot->>'current_conversation_id')::int = c.conversation_id
LEFT JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id AND wc.workflow_id = 3001
WHERE p.enabled = TRUE
  AND psc.checkpoint_id IN (SELECT MAX(checkpoint_id) FROM posting_state_checkpoints GROUP BY posting_id)
GROUP BY c.canonical_name, wc.execution_order
ORDER BY execution_order;

-- View recent checkpoints
SELECT 
    posting_id,
    conversation_id,
    execution_order,
    created_at
FROM posting_state_checkpoints
ORDER BY created_at DESC
LIMIT 20;
```

### Database Backups
```bash
# Create backup
pg_dump turing > backups/turing_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql turing < backups/turing_20251118_120000.sql
```

---

## 🔍 Quality Assurance

### Check for Hallucinations
```bash
# Run hallucination detection
python3 scripts/qa_check_hallucinations.py

# Check specific patterns
python3 scripts/qa_check_hallucinations.py --pattern "session_.*_output"
```

### Clear Bad Summaries
```bash
# Clear summaries for specific postings
python3 scripts/clear_bad_summaries.py --posting-ids 123,456,789

# Clear all summaries matching pattern
python3 scripts/clear_bad_summaries.py --pattern "based on session"
```

---

## 🐍 Python Environment

### Activate Virtual Environment
```bash
cd /home/xai/Documents/ty_learn
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Update Actor Code
```bash
# Sync actor code from disk to database
python3 tools/update_actor_code.py --actor-name extract_summary_gemma3

# Sync all actors
python3 tools/update_actor_code.py --all
```

---

## 📊 System Monitoring

### Check Running Processes
```bash
# Check if workflow is running
ps aux | grep wave_batch_processor | grep -v grep

# Check Python processes
ps aux | grep python3 | grep -v grep

# Check Ollama
systemctl status ollama
```

### Check GPU Usage
```bash
# Nvidia GPU
nvidia-smi

# Watch GPU in real-time
watch -n 2 nvidia-smi
```

### Check Disk Space
```bash
# Check overall disk usage
df -h

# Check directory sizes
du -sh /home/xai/Documents/ty_learn/*

# Find large files
find /home/xai/Documents/ty_learn -type f -size +100M -exec ls -lh {} \;
```

---

## 🔧 Development Workflow

### Git Operations
```bash
# Status
git status

# Commit changes
git add -A
git commit -m "Description of changes"

# Push to remote
git push origin master

# Pull latest
git pull origin master
```

### Testing Changes
```bash
# Run specific workflow test
python3 test_workflow_3001_debug.py

# Test database connection
python3 -c "from core.database import test_connection; test_connection()"

# Test actor execution
python3 -c "
from core.actor_router import execute_instruction
result = execute_instruction(instruction_id=123, posting=posting, workflow_definition=wd)
print(result)
"
```

---

## 📁 File Locations

### Important Directories
```
/home/xai/Documents/ty_learn/
├── actors/              # Actor script code (disk source)
├── core/                # Core system (wave_batch_processor, database, etc.)
├── docs/                # Documentation
│   ├── architecture/    # Modular architecture docs
│   └── logs/            # Session logs
├── interrogators/       # LLM conversation handlers
├── logs/                # Execution logs
├── scripts/             # Utility scripts
├── sql/                 # Database schema and functions
├── tools/               # Monitoring and deployment tools
├── workflows/           # Workflow JSON definitions
└── venv/                # Python virtual environment
```

### Key Files
```
docs/ARCHITECTURE.md                    # Complete system architecture
docs/architecture/README.md             # Architecture documentation index
docs/___ARDEN_CHEAT_SHEET.md           # Arden's quick reference
docs/__xai_cheat_sheet.md              # This file!
core/wave_batch_processor.py           # Main workflow engine
core/database.py                        # Database connection pooling
tools/monitor_workflow.py               # Workflow monitoring
scripts/restart_workflow.sh             # Workflow restart script
```

### Log Files
```
/tmp/workflow_3001.log                  # Current workflow log
logs/workflow_3001_*.log                # Historical workflow logs
logs/arden_log_*.md                     # Arden session logs
```

---

## 🛠️ Troubleshooting

### Workflow Won't Start
```bash
# 1. Check if already running
ps aux | grep wave_batch_processor

# 2. Check for errors in log
tail -50 /tmp/workflow_3001.log

# 3. Test Python import
python3 -c "from core.wave_batch_processor import WaveBatchProcessor"

# 4. Verify database connection
python3 -c "from core.database import get_connection; conn = get_connection(); print('OK')"
```

### Workflow Stuck/Slow
```bash
# Check current progress
python3 tools/monitor_workflow.py --workflow 3001 --mode snapshot

# Check for circuit breaker
grep "circuit_breaker" /tmp/workflow_3001.log | tail -20

# Check database connections
psql -d turing -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'turing';"
```

### Database Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check connection pooling
python3 -c "
from core.database import pool
print(f'Pool: minconn={pool.minconn}, maxconn={pool.maxconn}')
print(f'Active: {len([c for c in pool._pool if c])}')
"
```

### Ollama Issues
```bash
# Check Ollama status
systemctl status ollama

# Restart Ollama
sudo systemctl restart ollama

# List loaded models
curl http://localhost:11434/api/tags

# Check model loading
journalctl -u ollama --since "10 minutes ago" | grep -i "load"
```

---

## 🎯 Quick Wins

### One-Liners
```bash
# Restart everything
pkill -f wave_batch_processor && sleep 2 && ./scripts/restart_workflow.sh 3001

# Check progress quickly
python3 -c "from core.database import get_connection, return_connection; conn = get_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as done, COUNT(*) as total FROM postings WHERE enabled = TRUE'); r = cursor.fetchone(); print(f'{r[0]}/{r[1]} postings complete ({r[0]*100//r[1]}%)'); return_connection(conn)"

# Find postings needing summaries
psql -d turing -c "SELECT posting_id, job_title FROM postings WHERE enabled = TRUE AND extracted_summary IS NULL LIMIT 10;"

# Count checkpoints
psql -d turing -c "SELECT COUNT(*) FROM posting_state_checkpoints;"
```

---

## 📚 Documentation Quick Links

- **Architecture Overview**: `docs/ARCHITECTURE.md`
- **Database Schema**: `docs/architecture/DATABASE_SCHEMA.md`
- **Workflow Execution**: `docs/architecture/WORKFLOW_EXECUTION.md`
- **Checkpoint System**: `docs/architecture/CHECKPOINT_SYSTEM.md`
- **Debugging Guide**: `docs/WORKFLOW_DEBUGGING_GUIDE.md`
- **Migration Guide**: `docs/PYTHON_TO_TURING_MIGRATION_GUIDE.md`
- **Skill Matching**: `docs/SKILL_MATCHING.md`

---

## 🤖 Working with Arden

### Arden's Context
```bash
# Arden reads this cheat sheet: docs/___ARDEN_CHEAT_SHEET.md
# Show Arden recent work:
tail -500 docs/logs/arden_log_20251118*.md

# Common Arden requests:
# - "Read the architecture docs and tell me what needs updating"
# - "Check workflow 3001 progress"
# - "Review recent git changes"
# - "Help me debug why summaries are missing"
```

### Sandy (Wave Processing Workspace)
```bash
# Sandy's workspace: /home/xai/Documents/ty_wave_processing
# Sandy focuses on: wave processing, GPU optimization, checkpoint recovery
# Sandy reads: WORKFLOW_EXECUTION.md, CHECKPOINT_SYSTEM.md
```

---

**Quick Help**:
- Workflow won't start? → Check `ps aux | grep wave_batch` and `/tmp/workflow_3001.log`
- Database errors? → `systemctl status postgresql` and check connection pool
- Slow progress? → Check GPU usage (`nvidia-smi`) and Ollama status
- Hallucinations? → Run `python3 scripts/qa_check_hallucinations.py`

**Last Updated**: November 18, 2025 by Arden
