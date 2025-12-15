# Wave Runner V2 - Quick Start Guide

## Running Workflow 3001 (Job Processing Pipeline)

### Prerequisites

1. **Database:** PostgreSQL with `turing` database running
2. **Ollama:** Running with models installed:
   ```bash
   ollama pull gemma3:1b
   ollama pull gemma2:latest
   ollama pull qwen2.5:7b
   ollama pull phi3:latest
   ```
3. **Python:** 3.8+ with psycopg2 and python-dotenv

### Quick Start (3 Lines of Code!)

```python
from wave_runner_v2.workflow_starter import start_workflow
from wave_runner_v2.runner import WaveRunner

# Start workflow 3001 for posting 176, starting from extraction
result = start_workflow(conn, workflow_id=3001, posting_id=176, start_conversation_id=3335)

# Run it!
WaveRunner(conn, workflow_run_id=result['workflow_run_id']).run(max_iterations=20)
```

### Using the Example Script

```bash
# Run full pipeline from extraction step
python examples/run_workflow_3001.py --posting-id 176 --start-from extract

# Start from IHL scoring
python examples/run_workflow_3001.py --posting-id 176 --start-from ihl

# Run from beginning (includes fetch)
python examples/run_workflow_3001.py --posting-id 176
```

## What Happens When You Run It?

### Step-by-Step Execution

1. **workflow_starter** creates:
   - `workflow_run` record (status: 'running')
   - Seed `interaction` record (status: 'pending', with prompt in `input.prompt`)

2. **WaveRunner** loops:
   - Claims pending interactions (atomic update with PID lock)
   - Executes them:
     - AI actors: Call Ollama API with prompt from `input.prompt`
     - Script actors: Execute Python script with params from `input`
   - Stores output in `output.response`
   - Checks branching conditions in `output.response` (e.g., `[PASS]`, `[FAIL]`)
   - Creates child interactions for next steps
   - Repeats until no pending interactions remain

3. **Result:** Complete pipeline execution with all outputs stored in database

## Example: Workflow 3001 Full Pipeline

**Posting:** 176 (Deutsche Bank Auditor position)  
**Duration:** 126 seconds  
**Interactions:** 13 total  

### Execution Flow

```
Extract (gemma3)
    ↓
[FAIL] → Grade (gemma2) + Grade (qwen2.5)
    ↓
[FAIL] → Improve (qwen2.5)
    ↓
Create Ticket
    ↓
[FAIL] → Regrade (qwen2.5)
    ↓
Create Ticket
    ↓
Format Standardization (phi3)
    ↓
Extract Skills (qwen2.5)
    ↓
Create Ticket
    ↓
IHL Scoring Chain:
  - Analyst (qwen2.5) → "GENUINE", score: 1
  - Skeptic (gemma2) → "GENUINE", score: 1
  - HR Expert (qwen2.5) → "BORDERLINE", IHL: 5
```

### Results Stored

- **Extracted Summary:** 3,741 chars (gemma3 output)
- **Improved Summary:** 1,213 chars (qwen2.5 after [FAIL] feedback)
- **Formatted Summary:** 6,357 chars (phi3 standardized)
- **Skills:** `["Python", "SQL", "AWS", "Leadership", "Communication", "Finance"]`
- **IHL Score:** 5 (BORDERLINE)
- **Tickets:** 3 error tickets created for grading issues

## Architecture Highlights

### Database-Driven Execution

```sql
-- Prompts stored BEFORE execution
INSERT INTO interactions (workflow_run_id, conversation_id, input, status)
VALUES (67, 3335, '{"prompt": "Extract key details from this job..."}', 'pending');

-- Wave Runner retrieves and executes
SELECT * FROM interactions WHERE status = 'pending' FOR UPDATE SKIP LOCKED LIMIT 1;

-- Output stored after execution
UPDATE interactions SET output = '{"response": "**Role:** Auditor..."}', status = 'completed';

-- Children created based on branching logic
INSERT INTO interactions (workflow_run_id, conversation_id, input, input_interaction_ids)
VALUES (67, 3336, '{"prompt": "Grade this summary..."}', ARRAY[105]);
```

### Key Tables

- **workflows:** Workflow definitions (3001 = Job Processing Pipeline)
- **workflow_conversations:** Conversation order in workflow
- **conversations:** AI or script tasks
- **instructions:** Prompts for each conversation
- **instruction_steps:** Branching logic (`[PASS]`, `[FAIL]`, etc.)
- **workflow_runs:** Execution instances
- **interactions:** Individual task executions (with prompts and outputs)

## Monitoring Execution

### Check Progress

```sql
-- See all interactions in a workflow_run
SELECT 
    i.interaction_id,
    i.execution_order,
    c.conversation_name,
    a.actor_name,
    i.status,
    LENGTH(i.output->>'response') as output_len
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.workflow_run_id = 67
ORDER BY i.execution_order;
```

### Check Specific Output

```sql
-- See AI response
SELECT output->>'response' 
FROM interactions 
WHERE interaction_id = 105;

-- See skills extracted
SELECT output->>'response' 
FROM interactions 
WHERE conversation_id = 3350 AND workflow_run_id = 67;

-- See IHL score
SELECT output->>'ihl_score', output->>'verdict'
FROM interactions
WHERE conversation_id = 9163 AND workflow_run_id = 67;
```

## Troubleshooting

### No Ollama Models

```bash
# Check installed models
ollama list

# Install missing models
ollama pull gemma3:1b
ollama pull gemma2:latest
ollama pull qwen2.5:7b
ollama pull phi3:latest
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -h localhost -U base_admin -d turing -c "SELECT version();"

# Check .env file has credentials
cat .env | grep DB_
```

### Interactions Stuck in Pending

```python
# Check for errors
cursor.execute("""
    SELECT interaction_id, error_message, error_trace
    FROM interactions
    WHERE workflow_run_id = 67 AND status = 'failed'
""")
```

## Next Steps

1. **Batch Processing:** Process multiple postings
2. **Error Handling:** Add retry logic for rate limits
3. **Data Persistence:** Save results back to `postings` table
4. **Monitoring:** Build dashboard for workflow execution

## See Also

- [Proof of Concept](PROOF_OF_CONCEPT_NOV24.md) - Test results
- [Workflow 3001 Documentation](3001_complete_job_processing_pipeline%20(serial%20grader).md) - Full pipeline details
- [Examples](../examples/README.md) - Usage examples
