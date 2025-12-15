-- Add Database Writer to Workflow 1124 (Fake Job Detector)
-- This conversation parses the HR Expert's final verdict and writes to postings table

-- 1. Create the conversation
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    context_strategy,
    enabled,
    canonical_name,
    conversation_type
)
SELECT
    'IHL Database Writer',
    'Parses HR Expert final verdict JSON and writes ihl_score to postings table',
    (SELECT actor_id FROM actors WHERE actor_name = 'Python Code Executor' LIMIT 1),
    'session_outputs',
    true,
    'ihl_database_writer',
    'action'
RETURNING conversation_id;

-- Store the conversation_id for later use
\gset ihl_writer_conv_

-- 2. Add the conversation to the workflow (as 4th step after HR Expert)
INSERT INTO workflow_steps (
    workflow_id,
    conversation_id,
    step_order,
    step_name,
    is_conditional,
    enabled
)
VALUES (
    1124,
    :ihl_writer_conv_id,
    4,
    'Write Score to Database',
    false,
    true
);

-- 3. Create the instruction for the database writer
INSERT INTO validated_prompts (
    prompt_name,
    prompt_text,
    conversation_id,
    enabled
)
VALUES (
    'IHL Database Writer - Save Score',
    E'Parse the HR Expert''s final verdict and write the IHL score to the database.

INPUTS:
- posting_id: {posting_id}
- hr_verdict: {session_r3_output}

TASK:
1. Extract ihl_score from the JSON in {session_r3_output}
2. UPDATE postings SET ihl_score = <score>, ihl_analyzed_at = NOW() WHERE posting_id = {posting_id}

EXPECTED OUTPUT:
```json
{
  "success": true,
  "posting_id": <id>,
  "ihl_score": <score>,
  "updated_at": "<timestamp>"
}
```

PYTHON CODE:
```python
import json
import re
import psycopg2
from datetime import datetime

# Database config
DB_CONFIG = {
    ''host'': ''localhost'',
    ''port'': 5432,
    ''database'': ''turing'',
    ''user'': ''base_admin'',
    ''password'': ''base_yoga_secure_2025''
}

# Parse HR verdict
hr_verdict = """{session_r3_output}"""
posting_id = {posting_id}

# Extract ihl_score from JSON
json_match = re.search(r''```json\s*(\{{.*?\}})\s*```'', hr_verdict, re.DOTALL)
if not json_match:
    json_match = re.search(r''\{{.*?\}}'', hr_verdict, re.DOTALL)

if json_match:
    json_str = json_match.group(1) if ''```'' in hr_verdict else json_match.group(0)
    data = json.loads(json_str)
    ihl_score = data.get(''ihl_score'') or data.get(''suggested_ihl_score'')
    
    if ihl_score is not None:
        # Write to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE postings 
            SET ihl_score = %s, ihl_analyzed_at = %s
            WHERE posting_id = %s
        """, (int(ihl_score), datetime.now(), posting_id))
        
        conn.commit()
        updated_at = datetime.now().isoformat()
        
        cur.close()
        conn.close()
        
        # Success output
        result = {
            "success": True,
            "posting_id": posting_id,
            "ihl_score": int(ihl_score),
            "updated_at": updated_at
        }
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"success": False, "error": "Could not extract ihl_score from verdict"}))
else:
    print(json.dumps({"success": False, "error": "Could not parse JSON from verdict"}))
```

[SUCCESS]',
    :ihl_writer_conv_id,
    true
);

-- 4. Show summary
SELECT 
    w.workflow_name,
    ws.step_order,
    ws.step_name,
    c.conversation_name
FROM workflows w
JOIN workflow_steps ws ON ws.workflow_id = w.workflow_id
JOIN conversations c ON c.conversation_id = ws.conversation_id
WHERE w.workflow_id = 1124
ORDER BY ws.step_order;
