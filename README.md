# Turing - Wave Processing Workspace

> **👋 Hey Arden!**  
> You're in the **Wave Processing** workspace. Focus on: wave batch processor optimization, workflow execution, checkpoint recovery, GPU utilization, model loading/unloading, execution order grouping, and performance tuning. DON'T work on skill matching algorithms or profile-to-job matching here - those belong in the skill_matching workspace.

**Purpose**: Focused workspace for wave batch processing and workflow execution  
**Created**: November 17, 2025  
**Main Workspace**: `/home/xai/Documents/ty_learn`  
**Workspace Path**: `/home/xai/Documents/ty_wave`

---

## What This Workspace Is For

**Wave Processing Topics**:
- Wave batch processor (`core/wave_batch_processor.py`)
- Workflow execution (`workflows/`)
- Posting state management (`core/posting_state.py`)
- Checkpoint recovery (`core/checkpoint_manager.py`)
- Actor routing (`core/actor_router.py`)
- GPU optimization
- Performance tuning

**What to work on here**:
- ✅ Wave processing optimization
- ✅ Execution order grouping
- ✅ Checkpoint systems
- ✅ GPU utilization improvements
- ✅ Model loading/unloading efficiency
- ✅ Connection pooling
- ✅ Workflow design and debugging

**What NOT to work on here** (use main workspace or skill_matching):
- ❌ Skill matching algorithms
- ❌ Profile-to-job matching
- ❌ Taxonomy hierarchy
- ❌ Skill extraction

---

## Directory Structure

All directories are **symlinks** to main workspace:

```
ty_wave/
├── core/                  → Wave processor, database, actors
│   ├── wave_batch_processor.py (1314 lines - CURRENTLY RUNNING)
│   ├── wave_processor/    (modular version - not in use)
│   ├── actor_router.py
│   ├── database.py
│   └── ...
├── workflows/             → Workflow definitions
├── interrogators/         → LLM conversation handlers
├── scripts/               → Utility scripts
│   ├── qa_check_hallucinations.py
│   └── ...
├── tools/                 → Monitoring and debugging
│   ├── monitor_workflow.py
│   └── ...
├── logs/                  → Execution logs
├── docs/                  → Documentation
│   └── ARCHITECTURE.md
└── sql/                   → Database schema
```

---

## Quick Start

### 1. Monitor Running Workflow
```bash
python3 tools/monitor_workflow.py --workflow 3001
```

### 2. Check Wave Processing Logs
```bash
# Recent wave activity
grep "wave_batch_started" /tmp/workflow_3001.log | tail -20 | python3 -c "
import sys, json
for line in sys.stdin:
    data = json.loads(line)
    if 'execution_order' in data:
        print(f\"Wave {data['wave_number']}: exec_order {data['execution_order']}: {data['active_postings']} postings\")
"
```

### 3. Restart Workflow
```bash
pkill -f wave_batch_processor && sleep 2
nohup python3 -m core.wave_batch_processor --workflow 3001 > /tmp/workflow_3001.log 2>&1 &
```

---

## Key Files

**Wave Processor** (`core/wave_batch_processor.py`):
- Main execution loop
- Execution order grouping (Nov 17, 2025 optimization)
- Wave chunking (35 postings per chunk)
- Connection pooling
- GPU optimization

**Workflow Definition**:
- Database tables: `workflows`, `workflow_conversations`, `conversations`
- Execution order determines processing sequence
- Branching via `instruction_steps`

**Monitoring** (`tools/monitor_workflow.py`):
- Live progress updates
- Step completion tracking
- Recent activity display

---

## Recent Optimizations (Nov 17, 2025)

### ✅ Execution Order Grouping

**Problem**: Postings grouped only by conversation_id allowed mixing of steps 3, 4, 10 in same wave → excessive model loading/unloading

**Solution**: Two-level grouping (execution_order → conversation_id)

**Implementation** (`core/wave_batch_processor.py` lines 1200-1240):
```python
# Group by execution_order first
exec_order_groups = {}
for posting in postings:
    exec_order = workflow_definition['conversations'][conv_id]['execution_order']
    exec_order_groups[exec_order].append(posting)

# Process execution orders sequentially
for exec_order in sorted(exec_order_groups.keys()):
    # Further group by conversation_id within this order
    conv_groups = {}
    for posting in order_postings:
        conv_groups[conv_id].append(posting)
    
    # Process all conversations at this execution_order
    for conv_id, group_postings in conv_groups.items():
        self._process_wave(conv_id, group_postings)
```

**Result**:
- Wave processes ALL step 3 postings before ANY step 4 postings
- Model loads once per step for all postings
- GPU utilization more consistent

**Example Output**:
```
Wave 46: exec_order 2: 518 postings  ← ALL step 2
Wave 46: exec_order 3: 697 postings  ← THEN ALL step 3
Wave 46: exec_order 4: 453 postings  ← THEN ALL step 4
```

### 🔍 GPU Sawtooth Pattern (Expected Behavior)

**Observation**: GPU utilization still shows cycles (high → low → high)

**Explanation**: Different steps use different models:
- Step 3: gemma3:4b (697 postings) → load → process → unload
- Step 4: gemma2 (453 postings) → load → process → unload
- Step 5: qwen2.5 (190 postings) → load → process → unload

**Conclusion**: This is **optimal** - we MUST complete all step 3 before step 4. The model swapping between steps is unavoidable and correct. The win is processing 697 postings per model load instead of scattered 4-posting batches.

---

## Current Status (Nov 17, 2025)

**Workflow 3001**:
- Total postings: 2,028
- Summaries: 70 (3%)
- Skills: 1,700 (83%)
- IHL scores: 1,875 (92%)

**Active Processing**:
- Currently: ~1,900 postings in pipeline
- Step 3 (gemma3_extract): 1,022 postings pending
- Recent activity: 4-36 postings per step per wave

**Architecture**:
- **Running**: `core/wave_batch_processor.py` (monolithic, 1314 lines)
- **Not Running**: `core/wave_processor/` (modular refactor from Nov 14)
- **Reason**: `python3 -m core.wave_batch_processor` loads .py file, not package __init__.py

---

## Common Tasks

### Monitor Workflow Progress
```bash
# Live dashboard (refreshes every 5s)
python3 tools/monitor_workflow.py --workflow 3001

# One-time snapshot
python3 tools/monitor_workflow.py --workflow 3001 --mode snapshot
```

### Check Execution Order Processing
```bash
# See execution orders being processed
grep "wave_batch_started" /tmp/workflow_3001.log | tail -20 | \
python3 -c "
import sys, json
for line in sys.stdin:
    data = json.loads(line)
    print(f\"Wave {data['wave_number']:2}: exec_order {data['execution_order']}: {data['active_postings']:3} postings\")
"
```

### View Ollama Model Loading
```bash
# Check which models are being loaded
journalctl -u ollama --since "30 minutes ago" --no-pager | \
grep -E "(llama runner started|offloaded|model buffer)" | tail -20
```

### Debug Posting State
```python
from core.database import get_connection, return_connection

conn = get_connection()
cursor = conn.cursor()

# Where are postings without summaries?
cursor.execute("""
    SELECT 
        c.canonical_name,
        wc.execution_order,
        COUNT(*) as count
    FROM posting_state_checkpoints psc
    JOIN postings p ON psc.posting_id = p.posting_id
    LEFT JOIN conversations c ON (psc.state_snapshot->>'current_conversation_id')::int = c.conversation_id
    LEFT JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id AND wc.workflow_id = 3001
    WHERE p.enabled = TRUE
      AND p.extracted_summary IS NULL
      AND psc.checkpoint_id IN (SELECT MAX(checkpoint_id) FROM posting_state_checkpoints GROUP BY posting_id)
    GROUP BY c.canonical_name, wc.execution_order
    ORDER BY execution_order
""")

for row in cursor.fetchall():
    print(f"Step {row['execution_order']:2}: {row['canonical_name']:30} - {row['count']:4} postings")

return_connection(conn)
```

---

## Architecture Decisions

### Template Substitution vs Direct Checkpoint Queries (Nov 18, 2025)

**Decision**: Migrated from template substitution to direct checkpoint queries

**Problem**: Template substitution (`{session_9_output}`) breaks in multi-wave workflows when `posting.conversation_outputs` dict isn't restored from checkpoints → literal placeholders appear in LLM prompts → hallucinations

**Solution**: Query `posting_state_checkpoints` directly instead of relying on in-memory dict

**Pattern**:
```python
from core.checkpoint_utils import get_conversation_output

# Get specific conversation output
summary = get_conversation_output(posting_id, '3341')

# Or get all outputs efficiently
from core.checkpoint_utils import get_conversation_outputs_from_checkpoint
outputs = get_conversation_outputs_from_checkpoint(posting_id, workflow_run_id)
```

**See**: `docs/TEMPLATE_VS_QUERY_ARCHITECTURE.md` for full analysis

---

## Architecture Notes

### Connection Pooling (Nov 13, 2025 Fix)

**Critical Bug**: `conn.close()` does NOT return connections to pool!

**Correct Pattern**:
```python
from core.database import get_connection, return_connection

conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
finally:
    return_connection(conn)  # Uses pool.putconn(), not conn.close()!
```

**Impact**: Prevented pool exhaustion, improved checkpoint speed from 20-50ms → 8ms

### Wave Chunking

**Chunk Size**: 35 postings per chunk (not 140!)

**Why?** Connections are **reused**, not held concurrently:
- Posting 1: get_connection() → query → return_connection()
- Posting 2: get_connection() (reuses same conn) → query → return_connection()

**Real bottleneck**: Processing time (~3-5s per posting), not connection count

**Benefits**:
- Prevents queue timeout (35 postings process in ~2-3 seconds)
- Better progress monitoring
- Smooth GPU utilization

---

## Cross-References

**Related Workspaces**:
- **Skill Matching**: `/home/xai/Documents/ty_skill_matching`
- **Main Workspace**: `/home/xai/Documents/ty_learn`

**Related Docs**:
- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/___ARDEN_CHEAT_SHEET.md` - Quick reference
- `docs/WORKFLOW_CREATION_COOKBOOK.md` - How to build workflows

---

**Start VS Code Here**:
```bash
code /home/xai/Documents/ty_wave
```

**System**: Turing (universal workflow engine)  
**Product**: Talent.Yoga (career portal)  
**Database**: turing (PostgreSQL)
