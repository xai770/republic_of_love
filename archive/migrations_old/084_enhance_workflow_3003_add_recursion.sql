-- Migration 084: Workflow 3003 Enhancement - Add Recursive Organization
-- Purpose: Add iteration/looping to replicate recursive_organize_infinite.py behavior
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_actor_qwen INTEGER;
    v_conv_check_threshold INTEGER;
    v_conv_organize INTEGER;
    v_conv_write INTEGER;
    v_instr_check INTEGER;
    v_instr_organize INTEGER;
    v_step_organize_to_write INTEGER;
BEGIN
    -- Get actor
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b';
    
    -- Get existing conversations
    SELECT conversation_id INTO v_conv_organize FROM conversations WHERE canonical_name = 'w3003_c3_organize';
    SELECT conversation_id INTO v_conv_write FROM conversations WHERE canonical_name = 'w3003_c4_write';
    
    -- Create new conversation: Check if folder needs more organization
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_check_organization_threshold',
        'w3003_c6_check_threshold',
        'Check if any folder exceeds threshold and needs further organization (recursive zoom)',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_check_threshold;
    
    -- Add to workflow execution order (between organize and write)
    -- Delete and recreate to avoid unique constraint issues
    DELETE FROM workflow_conversations WHERE workflow_id = 3003;
    
    -- Re-insert all conversations with new ordering
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        (3003, 9149, 1, 'always', 'continue', 'stop', 2),  -- query
        (3003, 9150, 2, 'always', 'continue', 'stop', 2),  -- analyze
        (3003, 9151, 3, 'always', 'continue', 'stop', 2),  -- organize
        (3003, v_conv_check_threshold, 4, 'always', 'continue', 'stop', 1),  -- check threshold (NEW)
        (3003, 9152, 5, 'always', 'continue', 'stop', 1),  -- write
        (3003, 9153, 6, 'always', 'continue', 'stop', 1);  -- index
    
    -- Create instruction for threshold check
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_check_threshold,
        'Check Organization Threshold',
        1,
        'You are checking if any folder needs further organization (recursive zoom).

**FOLDER MAPPING:**
{{folder_mapping}}

**CURRENT ITERATION:** {{iteration_count}}

**THRESHOLDS:**
- Folder threshold: 15 (if a folder has >15 subfolders, needs organization)
- File threshold: 25 (if a folder has >25 .md files, needs organization)
- Max iterations: 20 (safety limit)

**TASK:** Analyze the folder structure and determine if any folder needs further organization.

**CHECK EACH FOLDER:**
1. Count subfolders in each folder
2. Count .md files in each folder
3. Check if ANY folder exceeds thresholds

**OUTPUT FORMAT:** JSON decision:
```json
{
  "needs_more_organization": true,
  "folders_to_organize": [
    {
      "path": "programming_languages/python/",
      "subfolder_count": 18,
      "file_count": 5,
      "reason": "18 subfolders exceeds threshold of 15"
    }
  ],
  "iteration_count": 1,
  "can_continue": true,
  "action": "ORGANIZE_MORE"
}
```

**POSSIBLE ACTIONS:**
- `ORGANIZE_MORE` - Need to organize folders that exceed threshold
- `COMPLETE` - All folders under threshold, organization complete
- `MAX_ITERATIONS` - Hit iteration limit, must stop

**RULES:**
- If iteration_count >= 20: action = "MAX_ITERATIONS"
- If no folders exceed thresholds: action = "COMPLETE"
- Otherwise: action = "ORGANIZE_MORE"

BEGIN YOUR RESPONSE WITH: ```json',
        600,
        true
    )
    RETURNING instruction_id INTO v_instr_check;
    
    -- Get organize instruction
    SELECT instruction_id INTO v_instr_organize 
    FROM instructions 
    WHERE conversation_id = v_conv_organize AND step_number = 1;
    
    -- Update organize instruction to accept iteration_count
    UPDATE instructions
    SET prompt_template = 'You are a file system organizer doing recursive organization (iteration {{iteration_count}}).

**CURRENT FOCUS:** {{folders_to_organize}}

**SKILLS DATA:**
{{skills_json}}

**TAXONOMY PLAN:**
{{taxonomy_plan}}

**TASK:** For folders that exceed thresholds, create sub-organization.

**EXAMPLE:** If "programming_languages/python/" has 18 subfolders, group them:
- frameworks/ (Django, Flask, FastAPI, etc.)
- data_science/ (Pandas, NumPy, Scikit-learn, etc.)  
- web_scraping/ (BeautifulSoup, Scrapy, Selenium, etc.)

**OUTPUT FORMAT:** JSON mapping with ONLY the reorganized folders:
```json
{
  "reorganized_folders": {
    "programming_languages/python/frameworks/": ["django.md", "flask.md", "fastapi.md"],
    "programming_languages/python/data_science/": ["pandas.md", "numpy.md", "sklearn.md"]
  },
  "iteration_complete": true
}
```

BEGIN YOUR RESPONSE WITH: ```json'
    WHERE instruction_id = v_instr_organize;
    
    -- Delete old organize → write step
    DELETE FROM instruction_steps 
    WHERE instruction_step_name = 'w3003_organize_to_write';
    
    -- Create new branching:
    -- 1. organize → check threshold
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_organize_to_check',
        v_instr_organize,
        'default',
        v_conv_check_threshold,
        1
    );
    
    -- 2. check threshold → LOOP BACK to organize if needed
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority,
        max_iterations
    ) VALUES (
        'w3003_check_loop_back',
        v_instr_check,
        'contains:ORGANIZE_MORE',
        v_conv_organize,
        1,
        20  -- Max 20 iterations (safety)
    );
    
    -- 3. check threshold → write files if complete
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_check_to_write',
        v_instr_check,
        'contains:COMPLETE',
        v_conv_write,
        2
    );
    
    -- 4. check threshold → stop if max iterations
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_check_max_iterations',
        v_instr_check,
        'contains:MAX_ITERATIONS',
        v_conv_write,
        3
    );
    
    RAISE NOTICE 'Enhanced Workflow 3003 with recursive organization capability';
    RAISE NOTICE 'Added conversation: check_threshold=%', v_conv_check_threshold;
    RAISE NOTICE 'Max iterations: 20 (configurable via max_iterations in instruction_steps)';
END $$;

COMMIT;

-- Verify new structure
SELECT 
    wc.execution_order,
    c.conversation_id,
    c.canonical_name,
    c.conversation_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3003
ORDER BY wc.execution_order;

-- Verify branching logic
SELECT 
    ist.instruction_step_name,
    i.instruction_name,
    c1.canonical_name as from_conv,
    ist.branch_condition,
    c2.canonical_name as to_conv,
    ist.max_iterations
FROM instruction_steps ist
JOIN instructions i ON ist.instruction_id = i.instruction_id
JOIN conversations c1 ON i.conversation_id = c1.conversation_id
LEFT JOIN conversations c2 ON ist.next_conversation_id = c2.conversation_id
WHERE c1.canonical_name LIKE 'w3003_%'
ORDER BY c1.canonical_name, ist.branch_priority;
