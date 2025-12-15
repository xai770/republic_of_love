"""Workflow Starter for Wave Runner
===================================

Minimal entry point to start workflow execution.
Creates workflow_run and seed interaction, then hands off to Wave Runner.

Usage:
    from core.wave_runner import start_workflow, WaveRunner
    
    result = start_workflow(workflow_id=3001, posting_id=176)
    runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
    runner.run(max_iterations=100)
"""

import psycopg2.extras
import json
from typing import Dict, List, Optional


def start_workflow(
    db_conn,
    workflow_id: int,
    posting_id: Optional[int] = None,
    batch_posting_ids: Optional[List[int]] = None,
    params: Optional[Dict] = None,
    start_conversation_id: Optional[int] = None
) -> Dict:
    """
    Start a workflow execution by creating workflow_run and seed interaction.
    
    Args:
        db_conn: Database connection
        workflow_id: Workflow to execute (e.g., 3001)
        posting_id: Single posting to process
        batch_posting_ids: Multiple postings to process (future enhancement)
        params: Workflow-specific parameters (e.g., user_id, max_jobs)
        start_conversation_id: Optional conversation to start from (default: first in workflow)
    
    Returns:
        {
            'workflow_run_id': int,
            'seed_interaction_id': int,
            'first_conversation_id': int,
            'first_conversation_name': str,
            'status': 'ready'
        }
    
    Raises:
        ValueError: If workflow doesn't exist or is disabled
    """
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # 1. Verify workflow exists and is enabled
    cursor.execute("""
        SELECT workflow_id, workflow_name, enabled
        FROM workflows 
        WHERE workflow_id = %s
    """, (workflow_id,))
    
    workflow = cursor.fetchone()
    if not workflow:
        raise ValueError(f"Workflow {workflow_id} does not exist")
    
    if not workflow['enabled']:
        raise ValueError(f"Workflow {workflow_id} ({workflow['workflow_name']}) is disabled")
    
    # 2. Find first conversation in workflow
    if start_conversation_id:
        # Use specified conversation
        cursor.execute("""
            SELECT 
                wc.conversation_id,
                wc.step_id,
                c.conversation_name,
                c.actor_id,
                a.actor_type,
                i.instruction_id
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN actors a ON c.actor_id = a.actor_id
            LEFT JOIN instructions i ON c.conversation_id = i.conversation_id 
                AND i.step_number = 1
            WHERE wc.workflow_id = %s AND wc.conversation_id = %s
        """, (workflow_id, start_conversation_id))
    else:
        # Use first conversation by execution_order
        cursor.execute("""
            SELECT 
                wc.conversation_id,
                wc.step_id,
                c.conversation_name,
                c.actor_id,
                a.actor_type,
                i.instruction_id
            FROM workflow_conversations wc
            JOIN conversations c ON wc.conversation_id = c.conversation_id
            JOIN actors a ON c.actor_id = a.actor_id
            LEFT JOIN instructions i ON c.conversation_id = i.conversation_id 
                AND i.step_number = 1
            WHERE wc.workflow_id = %s
            ORDER BY wc.execution_order
            LIMIT 1
        """, (workflow_id,))
    
    first_conv = cursor.fetchone()
    if not first_conv:
        if start_conversation_id:
            raise ValueError(f"Conversation {start_conversation_id} not found in workflow {workflow_id}")
        else:
            raise ValueError(f"Workflow {workflow_id} has no conversations defined")
    
    # 3. Create workflow_run
    cursor.execute("""
        INSERT INTO workflow_runs (
            workflow_id, 
            posting_id, 
            status, 
            environment
        )
        VALUES (%s, %s, 'running', 'dev')
        RETURNING workflow_run_id
    """, (workflow_id, posting_id))
    
    workflow_run_id = cursor.fetchone()['workflow_run_id']
    
    # 4. Prepare input for seed interaction
    # Get instruction prompt template
    cursor.execute("""
        SELECT prompt_template
        FROM instructions
        WHERE conversation_id = %s
          AND enabled = TRUE
        LIMIT 1
    """, (start_conversation_id,))
    
    instruction_result = cursor.fetchone()
    prompt_template = instruction_result['prompt_template'] if instruction_result else None
    
    # Build input based on actor type
    if first_conv['actor_type'] == 'script':
        # For script actors, prompt_template should be JSON - parse it
        if prompt_template:
            try:
                seed_input = json.loads(prompt_template)
                # Substitute {posting_id} placeholder
                prompt_json = json.dumps(seed_input)
                prompt_json = prompt_json.replace('{posting_id}', str(posting_id))
                seed_input = json.loads(prompt_json)
                
                # Merge with any additional params
                if params:
                    seed_input.update(params)
            except json.JSONDecodeError:
                # If not valid JSON, use params directly
                seed_input = params or {}
        else:
            # No prompt template, use params directly
            seed_input = params or {}
    else:
        # AI actors need a prompt
        if prompt_template:
            # Substitute placeholders in prompt
            prompt = prompt_template.replace('{posting_id}', str(posting_id))
            seed_input = {'prompt': prompt}
            if params:
                seed_input['params'] = params
        else:
            seed_input = {
                'prompt': 'Start workflow',  # Placeholder
                'params': params or {}
            }
    
    # 5. Create seed interaction
    cursor.execute("""
        INSERT INTO interactions (
            posting_id,
            workflow_run_id,
            conversation_id,
            actor_id,
            actor_type,
            status,
            execution_order,
            input,
            input_interaction_ids,
            instruction_id
        ) VALUES (
            %s, %s, %s, %s, %s,
            'pending',
            1,
            %s::jsonb,
            ARRAY[]::INT[],
            %s
        )
        RETURNING interaction_id
    """, (
        posting_id,
        workflow_run_id,
        first_conv['conversation_id'],
        first_conv['actor_id'],
        first_conv['actor_type'],
        json.dumps(seed_input),
        first_conv.get('instruction_id')
    ))
    
    seed_interaction_id = cursor.fetchone()['interaction_id']
    
    # 6. Link workflow_run to seed interaction
    cursor.execute("""
        UPDATE workflow_runs 
        SET seed_interaction_id = %s
        WHERE workflow_run_id = %s
    """, (seed_interaction_id, workflow_run_id))
    
    # Commit the transaction
    db_conn.commit()
    
    return {
        'workflow_run_id': workflow_run_id,
        'seed_interaction_id': seed_interaction_id,
        'first_conversation_id': first_conv['conversation_id'],
        'first_conversation_name': first_conv['conversation_name'],
        'status': 'ready'
    }
