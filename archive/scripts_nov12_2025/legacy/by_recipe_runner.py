#!/usr/bin/env python3
"""
BY Recipe Runner - PostgreSQL Version
=====================================

PURPOSE:
    Main execution engine for Base Yoga (BY) workflows. A recipe is a multi-step
    AI workflow that processes input data (job postings, profiles, etc.) through
    various LLM actors to extract structured information.

WHAT IS A RECIPE?
    A recipe consists of:
    - Recipe: Container with metadata (name, description, max runs)
    - Sessions: Ordered execution steps within a recipe
    - Instructions: Individual prompts sent to LLM actors within each conversation
    - Actors: LLMs that execute instructions (qwen2.5:7b, phi3:latest, etc.)
    
    Example Recipe 1121 (Hybrid Job Skills Extraction):
    - Session 1 → Instruction 1 → Qwen extracts skills with metadata
    - Output: JSON array of skills with importance/proficiency/years/reasoning

HOW IT WORKS:
    1. Fetches recipe structure from PostgreSQL (workflows, conversations, instructions)
    2. Creates a recipe_run to track execution
    3. Executes each conversation in order
    4. For each conversation, executes each instruction
    5. Renders prompt templates with placeholders ({variations_param_1}, {session_N_output})
    6. Sends rendered prompts to appropriate LLM actor
    7. Stores results in instruction_runs and conversation_runs
    8. Automatically saves outputs to postings/profiles tables based on content

KEY FEATURES:
    - Generic output detection: Detects skill data by JSON structure (no hardcoded recipe IDs)
    - Placeholder system: {variations_param_1} for input, {session_N_output} for chaining
    - Actor routing: Each instruction can use different actors (delegate_actor_id)
    - Batch tracking: Supports multiple runs with testing/production modes
    - Auto-save: Detects skill arrays and saves to appropriate table

USAGE:
    # Extract skills from a job posting
    python3 by_recipe_runner.py --recipe-id 1121 --job-id TEST_ORACLE_DBA_001 --execution-mode production
    
    # Extract skills from a profile
    python3 by_recipe_runner.py --recipe-id 1122 --profile-id 1001 --execution-mode testing
    
    # Run with custom test data
    python3 by_recipe_runner.py --recipe-id 1121 --test-data "Job description text..." --execution-mode testing

CRITICAL DESIGN DECISIONS:
    - Saves outputs BEFORE updating recipe_run status (avoids unique constraint crashes)
    - Detects skill data by checking for 'skill' key in JSON (no hardcoded conversation numbers)
    - Uses {variations_param_1} placeholder for input data (stored in variations.test_data->>'param_1')
    - Supports conversation output chaining via {session_N_output} placeholders
    
DATABASE TABLES:
    - workflows: Recipe definitions
    - conversations: Steps within workflows
    - instructions: Prompts within conversations
    - workflow_runs: Execution tracking
    - conversation_runs: Session execution tracking
    - instruction_runs: Individual instruction results
    - variations: Input data variations (test_data stored as JSONB)
    - postings: Job postings (target for job skill extraction)
    - profiles: Candidate profiles (target for profile skill extraction)

RELATED SCRIPTS:
    - batch_extract_job_skills.py: Batch process all jobs
    - save_batch_skills.py: Recovery script for retroactive saves
    - recipe_3_matching.py: LLM-guided skill matching
    - hybrid_profile_skill_extraction.py: Profile extraction with taxonomy mapping

AUTHOR: Base Yoga Team
UPDATED: October 30, 2025 - Added generic skill detection and auto-save
"""

import psycopg2
import psycopg2.extras
import subprocess
import time
import argparse
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'turing',  # Updated from base_yoga
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

class BYRecipeRunner:
    """
    Recipe Execution Engine
    
    Orchestrates multi-step LLM workflows defined in PostgreSQL database.
    Handles conversation ordering, prompt rendering, actor routing, and result storage.
    
    Key Responsibilities:
    - Create and track workflow_runs for execution monitoring
    - Execute conversations in order (with support for branching)
    - Render prompt templates with dynamic placeholders
    - Route instructions to appropriate LLM actors
    - Store results and auto-save to target tables
    """
    
    def __init__(self):
        """Initialize runner with database connection pool"""
        self.conn = None
    
    def get_connection(self):
        """
        Get or create database connection with RealDictCursor
        
        Returns:
            psycopg2.connection: Database connection with dict-like row access
        """
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)
        return self.conn
    
    def log_llm_interaction(self, workflow_run_id: int, conversation_run_id: int, 
                           actor_id: int, execution_order: int, prompt_sent: str, 
                           response_received: str, latency_ms: int, status: str,
                           instruction_id: int = None, dialogue_step_run_id: int = None,
                           error_message: str = None) -> int:
        """
        Log an LLM interaction to llm_interactions table
        
        This creates a unified log entry for every AI model call, regardless of
        workflow type (single-actor, multi-turn, multi-actor dialogue).
        
        Args:
            workflow_run_id: Which workflow execution
            conversation_run_id: Which conversation within the workflow
            actor_id: Which AI actor was called
            execution_order: Order within the conversation (1, 2, 3, ...)
            prompt_sent: The actual prompt sent to LLM (after placeholder replacement)
            response_received: The response from the LLM
            latency_ms: Time taken in milliseconds
            status: SUCCESS, TIMEOUT, ERROR, etc.
            instruction_id: For single-actor/multi-turn (NULL for multi-actor dialogues)
            dialogue_step_run_id: For multi-actor dialogues (NULL for single-actor)
            error_message: If status is ERROR, the error details
            
        Returns:
            interaction_id: The ID of the created interaction log
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO llm_interactions (
                workflow_run_id, conversation_run_id, dialogue_step_run_id,
                actor_id, instruction_id, execution_order,
                prompt_sent, response_received, latency_ms,
                status, error_message, started_at, completed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP - (%s || ' milliseconds')::INTERVAL, 
                    CURRENT_TIMESTAMP)
            RETURNING interaction_id
        """, (
            workflow_run_id, conversation_run_id, dialogue_step_run_id,
            actor_id, instruction_id, execution_order,
            prompt_sent, response_received, latency_ms,
            status, error_message, latency_ms
        ))
        
        interaction_id = cursor.fetchone()['interaction_id']
        conn.commit()
        return interaction_id
    
    def log_interaction_lineage(self, downstream_interaction_id: int, 
                                upstream_interaction_id: int, influence_type: str,
                                placeholder_used: str = None):
        """
        Log a causation relationship between two interactions
        
        Records that downstream_interaction was influenced by upstream_interaction.
        This builds the dependency graph for lineage tracking and impact analysis.
        
        Args:
            downstream_interaction_id: The interaction that reads/depends on upstream
            upstream_interaction_id: The interaction that provides input
            influence_type: How upstream influenced downstream
                'direct_read' - explicitly read via placeholder
                'sequential' - previous step in conversation
                'dialogue_context' - multi-actor dialogue reading previous turn
                'parallel_sync' - waited for parallel group
                'conditional' - branching logic
            placeholder_used: Which placeholder was used (e.g., 'session_1_output')
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interaction_lineage (
                downstream_interaction_id, upstream_interaction_id,
                influence_type, placeholder_used
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (downstream_interaction_id, upstream_interaction_id, influence_type) 
            DO NOTHING
        """, (downstream_interaction_id, upstream_interaction_id, influence_type, placeholder_used))
        
        conn.commit()
    
    def get_or_create_test_case(self, workflow_id: int, test_data: str, difficulty_level: int = 1, job_id: str = None) -> int:
        """
        Get existing test case or create new one
        
        A "test case" represents input data for a workflow. The same workflow can run
        on different inputs (e.g., different job postings). This method finds or
        creates a test_case record for the given test_data.
        
        Args:
            workflow_id: Workflow to create test case for
            test_data: Input data (job description, profile text, etc.)
            difficulty_level: Complexity level (default: 1)
            job_id: Optional job_id to link in test case metadata
            
        Returns:
            test_case_id: Database ID of the test case
            
        Note:
            test_data is stored as JSONB with key "param_1" to match the
            {variations_param_1} placeholder used in prompt templates (kept for backward compatibility).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Convert test_data to JSONB format - use param_1 to match template expectations
        import json
        test_data_json = {"param_1": test_data}
        if job_id:
            test_data_json["job_id"] = job_id
        test_data_json_str = json.dumps(test_data_json)
        
        # Try to find existing test case
        cursor.execute("""
            SELECT test_case_id FROM test_cases 
            WHERE workflow_id = %s AND test_data = %s::jsonb
        """, (workflow_id, test_data_json_str))
        
        existing = cursor.fetchone()
        if existing:
            return existing['test_case_id']
        
        # Create new test case
        cursor.execute("""
            INSERT INTO test_cases (
                test_case_name, workflow_id, test_data, difficulty_level, enabled
            )
            VALUES (%s, %s, %s::jsonb, %s, TRUE)
            RETURNING test_case_id
        """, (f"test_case_{workflow_id}_{int(time.time())}", workflow_id, test_data_json_str, difficulty_level))
        
        test_case_id = cursor.fetchone()['test_case_id']
        conn.commit()
        
        print(f"✅ Created test case {test_case_id} for workflow {workflow_id}")
        if job_id:
            print(f"   Linked to job_id: {job_id}")
        return test_case_id
    
    def create_workflow_run(self, workflow_id: int, test_case_id: int, batch_id: int = 1, execution_mode: str = 'production', target_batch_count: int = 1) -> int:
        """Create a new recipe_run record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get recipe info
        cursor.execute("""
            SELECT workflow_name, max_total_session_runs 
            FROM workflows WHERE workflow_id = %s
        """, (workflow_id,))
        recipe = cursor.fetchone()
        
        if not recipe:
            raise ValueError(f"Recipe {workflow_id} not found")
        
        # Count total conversations
        cursor.execute("""
            SELECT COUNT(*) as count FROM workflow_conversations 
            WHERE workflow_id = %s
        """, (workflow_id,))
        total_sessions = cursor.fetchone()['count']
        
        # Determine batch_number (how many times has this variation been run?)
        cursor.execute("""
            SELECT COUNT(*) + 1 as batch_number
            FROM workflow_runs
            WHERE workflow_id = %s 
              AND test_case_id = %s
              AND execution_mode = %s
        """, (workflow_id, test_case_id, execution_mode))
        batch_number = cursor.fetchone()['batch_number']
        
        # Create recipe_run
        cursor.execute("""
            INSERT INTO workflow_runs (
                workflow_id, test_case_id, batch_id, 
                total_sessions, status, started_at,
                execution_mode, target_batch_count, batch_number
            )
            VALUES (%s, %s, %s, %s, 'PENDING', CURRENT_TIMESTAMP, %s, %s, %s)
            RETURNING workflow_run_id
        """, (workflow_id, test_case_id, batch_id, total_sessions, execution_mode, target_batch_count, batch_number))
        
        workflow_run_id = cursor.fetchone()['workflow_run_id']
        conn.commit()
        
        print(f"✅ Created workflow_run {workflow_run_id} for workflow {workflow_id}")
        print(f"   Mode: {execution_mode}, Batch: {batch_number}/{target_batch_count}")
        return workflow_run_id
    
    def get_recipe_sessions(self, workflow_id: int) -> List[Dict[str, Any]]:
        """Get conversations for a recipe in execution order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.conversation_id, c.conversation_name, c.actor_id,
                cs.step_id, cs.execution_order, 
                cs.on_success_action, cs.on_failure_action
            FROM workflow_conversations cs
            JOIN conversations c ON cs.conversation_id = c.conversation_id
            WHERE cs.workflow_id = %s AND c.enabled = TRUE
            ORDER BY cs.execution_order
        """, (workflow_id,))
        
        return cursor.fetchall()
    
    def get_conversation_instructions(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Get instructions for a conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                instruction_id, step_number, step_description,
                prompt_template, timeout_seconds
            FROM instructions
            WHERE conversation_id = %s AND enabled = TRUE
            ORDER BY step_number
        """, (conversation_id,))
        
        return cursor.fetchall()
    
    def get_dialogue_steps(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Get dialogue steps for a multi-actor conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                dialogue_step_id, dialogue_step_name, actor_id, actor_role,
                execution_order, reads_from_step_ids, prompt_template, timeout_seconds
            FROM conversation_dialogue
            WHERE conversation_id = %s AND enabled = TRUE
            ORDER BY execution_order
        """, (conversation_id,))
        
        return cursor.fetchall()
    
    def check_conversation_type(self, conversation_id: int) -> str:
        """Check if conversation is single_actor or multi_actor_dialogue"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT conversation_type FROM conversations WHERE conversation_id = %s
        """, (conversation_id,))
        
        result = cursor.fetchone()
        return result['conversation_type'] if result else 'single_actor'
    
    def create_conversation_run(self, workflow_run_id: int, step_id: int, conversation_id: int, execution_order: int, execution_mode: str = 'testing') -> int:
        """Create a conversation_run record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generate conversation_run_name
        run_name = f"wf{workflow_run_id}_step{step_id}_conv{conversation_id}_{int(time.time())}"
        
        cursor.execute("""
            INSERT INTO conversation_runs (
                conversation_run_name, conversation_id, workflow_step_id, execution_order,
                run_id, run_type, status, started_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'RUNNING', CURRENT_TIMESTAMP)
            RETURNING conversation_run_id
        """, (run_name, conversation_id, step_id, execution_order, workflow_run_id, execution_mode))
        
        conversation_run_id = cursor.fetchone()['conversation_run_id']
        conn.commit()
        
        return conversation_run_id
    
    def get_actor_details(self, actor_id: int) -> Optional[Dict[str, Any]]:
        """Fetch actor details from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT actor_id, actor_name, actor_type, execution_type,
                   script_code, script_language, script_version, 
                   execution_path, url, enabled
            FROM actors
            WHERE actor_id = %s
        """, (actor_id,))
        
        return cursor.fetchone()
    
    def migrate_script_to_db(self, actor_id: int, execution_path: str) -> bool:
        """
        Automatically migrate script from file to database.
        Returns True if successful, False otherwise.
        """
        import os
        from pathlib import Path
        
        base_path = Path('/home/xai/Documents/ty_learn')
        full_path = base_path / execution_path
        
        if not full_path.exists():
            print(f"    ⚠️  Script file not found: {execution_path}")
            return False
        
        try:
            # Read script content
            with open(full_path, 'r', encoding='utf-8') as f:
                script_code = f.read()
            
            # Determine language from extension
            ext = full_path.suffix.lower()
            if ext == '.py':
                script_language = 'python'
            elif ext == '.sh':
                script_language = 'bash'
            else:
                script_language = 'unknown'
            
            # Update actor with script code
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE actors 
                SET script_code = %s,
                    script_language = %s,
                    script_version = 1
                WHERE actor_id = %s
            """, (script_code, script_language, actor_id))
            
            conn.commit()
            
            print(f"    ✅ Auto-migrated script to database ({len(script_code)} chars)")
            return True
            
        except Exception as e:
            print(f"    ❌ Failed to migrate script: {e}")
            return False
    
    def execute_script_actor(self, actor: Dict[str, Any], prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a script actor (Python/Bash script)"""
        import tempfile
        import os
        
        start_time = time.time()
        script_code = actor['script_code']
        script_language = actor['script_language']
        execution_path = actor['execution_path']
        
        try:
            # Priority 1: Execute from database
            if script_code:
                print(f"    📜 Executing {script_language} script from database (version {actor['script_version']})")
                
                # Create temporary file with script code
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{script_language}', delete=False) as f:
                    f.write(script_code)
                    temp_script_path = f.name
                
                try:
                    # Execute based on language
                    if script_language == 'python':
                        cmd = ['python3', temp_script_path]
                    elif script_language == 'bash':
                        cmd = ['bash', temp_script_path]
                    else:
                        raise ValueError(f"Unsupported script language: {script_language}")
                    
                    result = subprocess.run(
                        cmd,
                        input=prompt,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                finally:
                    # Clean up temp file
                    os.unlink(temp_script_path)
            
            # Priority 2: Fallback to file (and auto-migrate)
            elif execution_path:
                print(f"    ⚠️  Script not in database, falling back to file: {execution_path}")
                
                # Try to auto-migrate
                if self.migrate_script_to_db(actor['actor_id'], execution_path):
                    # Retry execution from DB
                    return self.execute_script_actor(
                        self.get_actor_details(actor['actor_id']), 
                        prompt, 
                        timeout
                    )
                
                # If migration failed, execute from file
                base_path = '/home/xai/Documents/ty_learn'
                full_path = os.path.join(base_path, execution_path)
                
                if execution_path.endswith('.py'):
                    cmd = ['python3', full_path]
                elif execution_path.endswith('.sh'):
                    cmd = ['bash', full_path]
                else:
                    raise ValueError(f"Unknown script type: {execution_path}")
                
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            else:
                raise ValueError("No script_code or execution_path available")
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                return {
                    'status': 'SUCCESS',
                    'response': result.stdout.strip(),
                    'latency_ms': latency_ms,
                    'error': None
                }
            else:
                return {
                    'status': 'FAILED',
                    'response': None,
                    'latency_ms': latency_ms,
                    'error': result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'TIMEOUT',
                'response': None,
                'latency_ms': timeout * 1000,
                'error': f'Timeout after {timeout}s'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'response': None,
                'latency_ms': int((time.time() - start_time) * 1000),
                'error': str(e)
            }
    
    def execute_instruction(self, actor_id: int, prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute instruction by routing to appropriate actor type.
        
        Supports:
        - AI models (actor_type='ai_model'): Calls Ollama
        - Scripts (actor_type='script'): Executes Python/Bash from DB or file
        - Humans (actor_type='human'): Creates human_tasks entry (future)
        
        Script Execution Priority:
        1. script_code (database) - source of truth
        2. execution_path (file) - fallback, auto-migrates to DB
        3. Error if neither exists
        """
        start_time = time.time()
        
        # Fetch actor details
        actor = self.get_actor_details(actor_id)
        if not actor:
            return {
                'status': 'ERROR',
                'response': None,
                'latency_ms': 0,
                'error': f'Actor {actor_id} not found in database'
            }
        
        if not actor['enabled']:
            return {
                'status': 'ERROR',
                'response': None,
                'latency_ms': 0,
                'error': f"Actor '{actor['actor_name']}' is disabled"
            }
        
        try:
            # Route based on actor type
            if actor['actor_type'] == 'script':
                return self.execute_script_actor(actor, prompt, timeout)
            
            elif actor['actor_type'] == 'ai_model':
                # Call Ollama API with actor_name (e.g., "qwen2.5:7b")
                actor_name = actor['actor_name']
                print(f"    🤖 Calling AI model: {actor_name}")
                
                result = subprocess.run(
                    ['ollama', 'run', actor_name],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                if result.returncode == 0:
                    return {
                        'status': 'SUCCESS',
                        'response': result.stdout.strip(),
                        'latency_ms': latency_ms,
                        'error': None
                    }
                else:
                    return {
                        'status': 'FAILED',
                        'response': None,
                        'latency_ms': latency_ms,
                        'error': result.stderr
                    }
            
            elif actor['actor_type'] == 'human':
                # TODO: Create human_tasks entry
                return {
                    'status': 'ERROR',
                    'response': None,
                    'latency_ms': 0,
                    'error': 'Human actor execution not yet implemented'
                }
            
            else:
                return {
                    'status': 'ERROR',
                    'response': None,
                    'latency_ms': 0,
                    'error': f"Unknown actor type: {actor['actor_type']}"
                }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'TIMEOUT',
                'response': None,
                'latency_ms': timeout * 1000,
                'error': f'Timeout after {timeout}s'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'response': None,
                'latency_ms': int((time.time() - start_time) * 1000),
                'error': str(e)
            }
    
    def save_instruction_run(self, conversation_run_id: int, instruction_id: int, 
                            step_number: int, prompt: str, result: Dict[str, Any],
                            actor_id: int, workflow_run_id: int) -> int:
        """
        Save instruction_run record and log to llm_interactions
        
        Args:
            conversation_run_id: Which conversation execution
            instruction_id: Which instruction template was used
            step_number: Order within the conversation
            prompt: The rendered prompt sent to LLM
            result: The result dict from execute_instruction
            actor_id: Which AI actor was called
            workflow_run_id: Which workflow execution this belongs to
            
        Returns:
            instruction_run_id: The ID of the created instruction_run record
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Insert directly into llm_interactions (instruction_runs is just a legacy view)
        # This is the unified logging for all LLM interactions
        interaction_id = self.log_llm_interaction(
            workflow_run_id=workflow_run_id,
            conversation_run_id=conversation_run_id,
            actor_id=actor_id,
            execution_order=step_number,
            prompt_sent=prompt,
            response_received=result['response'],
            latency_ms=result['latency_ms'],
            status=result['status'],
            instruction_id=instruction_id,
            dialogue_step_run_id=None,  # Not a dialogue
            error_message=result['error']
        )
        
        # Return interaction_id as both values for backward compatibility
        # (instruction_run_id was removed in Migration 035, it's now just interaction_id)
        return interaction_id, interaction_id
    
    def get_instruction_branches(self, instruction_id: int) -> List[Dict[str, Any]]:
        """Get branches for an instruction, ordered by priority DESC"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                instruction_step_id, instruction_id, branch_condition,
                next_instruction_id, next_conversation_id, max_iterations,
                branch_priority, branch_description, enabled
            FROM instruction_steps
            WHERE instruction_id = %s AND enabled = TRUE
            ORDER BY branch_priority DESC
        """, (instruction_id,))
        
        return cursor.fetchall()
    
    def evaluate_branches(self, instruction_id: int, instruction_run_id: int, 
                         output: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate branches for an instruction based on its output.
        Returns the first matching branch (highest priority) or None.
        """
        import re
        
        branches = self.get_instruction_branches(instruction_id)
        
        if not branches:
            return None  # No branches defined
        
        print(f"\n  🔀 Evaluating {len(branches)} branches...")
        
        for branch in branches:
            condition = branch['branch_condition']
            priority = branch['branch_priority']
            description = branch['branch_description']
            
            # Handle catch-all wildcard
            if condition == '*':
                print(f"    ✅ Matched catch-all (priority {priority}): {description}")
                self.record_branch_execution(instruction_run_id, branch['instruction_step_id'], output)
                return branch
            
            # Try regex matching
            try:
                if re.search(condition, output, re.IGNORECASE):
                    print(f"    ✅ Matched '{condition}' (priority {priority}): {description}")
                    self.record_branch_execution(instruction_run_id, branch['instruction_step_id'], output)
                    return branch
                else:
                    print(f"    ⏭️  No match: '{condition}'")
            except re.error as e:
                print(f"    ⚠️  Invalid regex '{condition}': {e}")
                continue
        
        print(f"    ℹ️  No branches matched - continuing linearly")
        return None
    
    def record_branch_execution(self, instruction_run_id: int, instruction_step_id: int, 
                               matched_output: str):
        """Record that a branch was taken"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current iteration count for this branch in this session_run
        cursor.execute("""
            SELECT COALESCE(MAX(iteration_count), 0) as current_iter
            FROM instruction_branch_executions ibe
            JOIN instruction_runs ir ON ibe.instruction_run_id = ir.instruction_run_id
            WHERE ibe.instruction_step_id = %s 
              AND ir.conversation_run_id = (
                  SELECT conversation_run_id FROM instruction_runs WHERE instruction_run_id = %s
              )
        """, (instruction_step_id, instruction_run_id))
        
        result = cursor.fetchone()
        iteration_count = (result['current_iter'] if result else 0) + 1
        
        # Insert execution record
        cursor.execute("""
            INSERT INTO instruction_branch_executions (
                instruction_run_id, instruction_step_id, condition_matched, iteration_count
            ) VALUES (%s, %s, %s, %s)
        """, (instruction_run_id, instruction_step_id, matched_output[:500], iteration_count))
        
        conn.commit()
    
    def update_session_run(self, conversation_run_id: int, status: str, error: Optional[str] = None):
        """Update session_run status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversation_runs 
            SET status = %s, completed_at = CURRENT_TIMESTAMP, error_details = %s
            WHERE conversation_run_id = %s
        """, (status, error, conversation_run_id))
        
        conn.commit()
    
    def update_workflow_run(self, workflow_run_id: int, status: str, error: Optional[str] = None):
        """Update recipe_run status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflow_runs 
            SET status = %s, completed_at = CURRENT_TIMESTAMP, error_details = %s
            WHERE workflow_run_id = %s
        """, (status, error, workflow_run_id))
        
        conn.commit()
    
    def render_prompt(self, template: str, test_case_data: Dict[str, Any], 
                     session_outputs: Dict[int, str], session_number: int, 
                     strict: bool = True) -> tuple[str, List[str]]:
        """
        Render prompt template by replacing placeholders dynamically
        
        Placeholder Types:
        1. {variations_param_1} - Input data from variations table
           Example: {variations_param_1} → job description text
           
        2. {session_N_output} - Output from conversation N
           Example: {session_1_output} → skills extracted by conversation 1
           
        3. {session_A_output?session_B_output} - Fallback syntax
           Example: {session_4_output?session_1_output}
           Uses conversation 4 if available, otherwise falls back to conversation 1
        
        Args:
            template: Prompt template with placeholders
            test_case_data: Input data from variations.test_data JSONB column
            session_outputs: Dictionary mapping session_number → output text
            session_number: Current conversation number (for forward reference detection)
            strict: If True, raises exception when placeholders are missing
        
        Returns:
            tuple: (rendered_template, list_of_missing_placeholders)
            
        Raises:
            ValueError: If strict=True and placeholders are missing
            
        Example:
            template = "Extract skills from: {variations_param_1}"
            test_case_data = {"param_1": "Job posting text..."}
            → "Extract skills from: Job posting text..."
        """
        import re
        
        # Find all placeholders in template: {something} or {something?fallback}
        placeholder_pattern = r'\{([^}]+)\}'
        found_placeholders = set(re.findall(placeholder_pattern, template))
        
        rendered = template
        missing = []
        
        # Process each placeholder found in template
        for placeholder_name in found_placeholders:
            placeholder = f"{{{placeholder_name}}}"
            
            # Check for fallback syntax: session_4_output?session_1_output
            if '?' in placeholder_name:
                primary_name, fallback_name = placeholder_name.split('?', 1)
                primary_name = primary_name.strip()
                fallback_name = fallback_name.strip()
                
                # Try primary first
                value = None
                if primary_name.startswith('session_') and primary_name.endswith('_output'):
                    match = re.match(r'session_(\d+)_output', primary_name)
                    if match:
                        session_num = int(match.group(1))
                        if session_num in session_outputs:
                            value = session_outputs[session_num] or ""
                
                # If primary failed, try fallback
                if value is None:
                    if fallback_name.startswith('session_') and fallback_name.endswith('_output'):
                        match = re.match(r'session_(\d+)_output', fallback_name)
                        if match:
                            session_num = int(match.group(1))
                            if session_num in session_outputs:
                                value = session_outputs[session_num] or ""
                
                if value is not None:
                    rendered = rendered.replace(placeholder, value)
                else:
                    missing.append(f"{primary_name} (primary) and {fallback_name} (fallback)")
                
                continue  # Skip regular processing
            
            # Check if it's a variations parameter: {variations_param_1}
            if placeholder_name.startswith('variations_'):
                param_name = placeholder_name.replace('variations_', '')
                if param_name in test_case_data:
                    rendered = rendered.replace(placeholder, str(test_case_data[param_name]))
                else:
                    missing.append(f"variations.{param_name}")
            
            # Check if it's a conversation output: {session_N_output}
            elif placeholder_name.startswith('session_') and placeholder_name.endswith('_output'):
                # Extract conversation number from {session_3_output}
                match = re.match(r'session_(\d+)_output', placeholder_name)
                if match:
                    session_num = int(match.group(1))
                    if session_num in session_outputs:
                        rendered = rendered.replace(placeholder, session_outputs[session_num] or "")
                    else:
                        # Check if this is a forward reference (conversation hasn't run yet)
                        if session_num > session_number:
                            missing.append(f"session_{session_num}_output (FORWARD REFERENCE - conversation hasn't run yet)")
                        else:
                            missing.append(f"session_{session_num}_output (conversation completed but no output stored)")
            
            # Unknown placeholder type
            else:
                missing.append(f"{placeholder_name} (unknown type)")
        
        # Strict mode: fail if any placeholders are missing
        if strict and missing:
            error_msg = f"Missing placeholders in template:\n" + "\n".join(f"  - {m}" for m in missing)
            raise ValueError(error_msg)
        
        return rendered, missing
    
    def resolve_placeholders_from_registry(self, workflow_id: int, test_case_data: Dict[str, Any], 
                                           dialogue_outputs: Dict[int, str] = None) -> Dict[str, Any]:
        """
        Resolve all placeholders for a workflow using the placeholder registry
        
        This is the ELEGANT solution - placeholders are data, not code!
        All placeholder logic is stored in the database and resolved dynamically.
        
        Args:
            workflow_id: Which workflow we're executing
            test_case_data: Input data (may contain job_id, profile_id, etc.)
            dialogue_outputs: Previous dialogue step outputs (for multi-actor workflows)
            
        Returns:
            Dict mapping placeholder_name -> resolved_value
            
        Example:
            resolved = resolve_placeholders_from_registry(1124, {'job_id': 15}, {1: 'analyst output', 2: 'skeptic output'})
            # Returns: {
            #   'job_description': 'Full job posting text...',
            #   'skill_keywords': ['Python', 'SQL', ...],
            #   'step_1_output': 'analyst output',
            #   'step_2_output': 'skeptic output',
            #   ...
            # }
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        dialogue_outputs = dialogue_outputs or {}
        resolved = {}
        
        # Get all placeholders this workflow needs
        cursor.execute("""
            SELECT 
                pd.placeholder_name,
                pd.source_type,
                pd.source_table,
                pd.source_column,
                pd.source_query,
                pd.default_value,
                wp.is_required
            FROM workflow_placeholders wp
            JOIN placeholder_definitions pd ON pd.placeholder_id = wp.placeholder_id
            WHERE wp.workflow_id = %s
            ORDER BY wp.is_required DESC, pd.placeholder_name
        """, (workflow_id,))
        
        placeholders = cursor.fetchall()
        
        for p in placeholders:
            name = p['placeholder_name']
            source_type = p['source_type']
            value = None
            
            try:
                if source_type == 'test_case_data':
                    # Direct from test_case JSON
                    value = test_case_data.get(name)
                    
                elif source_type == 'posting':
                    # Fetch from postings table
                    job_id = test_case_data.get('job_id')
                    if job_id:
                        cursor.execute(f"SELECT {p['source_column']} FROM {p['source_table']} WHERE posting_id = %s", (job_id,))
                        result = cursor.fetchone()
                        if result:
                            value = result[p['source_column']]
                            # Handle JSONB columns
                            if value and isinstance(value, (list, dict)):
                                import json
                                value = json.dumps(value) if isinstance(value, dict) else str(value)
                                
                elif source_type == 'profile':
                    # Fetch from profiles table
                    profile_id = test_case_data.get('profile_id')
                    if profile_id:
                        cursor.execute(f"SELECT {p['source_column']} FROM {p['source_table']} WHERE profile_id = %s", (profile_id,))
                        result = cursor.fetchone()
                        if result:
                            value = result[p['source_column']]
                            
                elif source_type == 'dialogue_output':
                    # From previous dialogue steps
                    # Extract step number from name: step_1_output -> 1
                    import re
                    match = re.match(r'step_(\d+)_output', name)
                    if match:
                        step_num = int(match.group(1))
                        value = dialogue_outputs.get(step_num)
                        
                elif source_type == 'static':
                    # Use default value
                    value = p['default_value']
                    
                elif source_type == 'custom_query':
                    # Execute custom SQL
                    query = p['source_query']
                    # Replace :job_id, :profile_id parameters
                    query = query.replace(':job_id', str(test_case_data.get('job_id', 'NULL')))
                    query = query.replace(':profile_id', str(test_case_data.get('profile_id', 'NULL')))
                    cursor.execute(query)
                    result = cursor.fetchone()
                    if result:
                        value = list(result.values())[0]  # Get first column
                
                # Store resolved value
                resolved[name] = value if value is not None else ''
                
            except Exception as e:
                if p['is_required']:
                    raise ValueError(f"Failed to resolve required placeholder '{name}': {e}")
                else:
                    resolved[name] = ''  # Optional placeholder, use empty string
        
        return resolved
    
    def validate_workflow_placeholders(self, workflow_id: int, test_case_data: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate that a workflow has all required placeholders before execution
        
        Uses the database validation function to check if all required placeholders
        can be resolved from the provided test_case_data.
        
        Args:
            workflow_id: Which workflow to validate
            test_case_data: Input data to check
            
        Returns:
            (is_valid: bool, missing_required: list[str])
            
        Example:
            valid, missing = validate_workflow_placeholders(1124, {'job_id': 15})
            if not valid:
                print(f"Missing required placeholders: {missing}")
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        import json
        cursor.execute("""
            SELECT * FROM validate_workflow_placeholders(%s, %s::jsonb)
        """, (workflow_id, json.dumps(test_case_data)))
        
        result = cursor.fetchone()
        is_valid = result['is_valid']
        missing = result['missing_required'] or []
        
        return is_valid, missing
    
    def execute_multi_actor_dialogue(self, conversation_run_id: int, conversation_id: int, test_case_data: Dict[str, Any], timeout: int = 300) -> tuple[bool, Optional[str]]:
        """
        Execute a multi-actor dialogue with scripted, deterministic turns
        
        Each dialogue step executes in order:
        1. Fetch dialogue step (actor, prompt template, reads_from)
        2. Render prompt with outputs from previous steps
        3. Execute actor (call LLM or script)
        4. Store result in dialogue_step_runs
        5. Continue to next step
        
        Args:
            conversation_run_id: ID of the conversation run
            conversation_id: Which conversation template to use
            test_case_data: Input data for placeholders
            timeout: Max seconds per dialogue step
            
        Returns:
            (success: bool, final_output: Optional[str])
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all dialogue steps for this conversation
        dialogue_steps = self.get_dialogue_steps(conversation_id)
        
        if not dialogue_steps:
            print(f"  ⚠️  No dialogue steps defined for multi-actor conversation {conversation_id}")
            return False, None
        
        print(f"  🎭 Multi-actor dialogue: {len(dialogue_steps)} actors will speak")
        
        # Track each actor's output for context building
        dialogue_outputs = {}
        
        # Track interaction IDs for lineage logging
        dialogue_step_interactions = {}
        
        # Execute each dialogue step in order
        for step in dialogue_steps:
            dialogue_step_id = step['dialogue_step_id']
            actor_id = step['actor_id']
            actor_role = step['actor_role']
            execution_order = step['execution_order']
            reads_from_step_ids = step['reads_from_step_ids'] or []
            prompt_template = step['prompt_template']
            step_timeout = step['timeout_seconds'] or timeout
            
            print(f"\n  🎤 Turn {execution_order}: {actor_role} (actor {actor_id})")
            
            # Get workflow_run_id early (needed for placeholder resolution)
            cursor.execute("SELECT run_id FROM conversation_runs WHERE conversation_run_id = %s", 
                          (conversation_run_id,))
            workflow_run_id = cursor.fetchone()['run_id']
            
            cursor.execute("SELECT workflow_id FROM workflow_runs WHERE workflow_run_id = %s",
                          (workflow_run_id,))
            workflow_id = cursor.fetchone()['workflow_id']
            
            # USE PLACEHOLDER REGISTRY! This is the elegant way.
            # All placeholder logic is in the database, not scattered in code.
            resolved_placeholders = self.resolve_placeholders_from_registry(
                workflow_id=workflow_id,
                test_case_data=test_case_data,
                dialogue_outputs=dialogue_outputs
            )
            
            # Render prompt with resolved placeholders
            rendered_prompt = prompt_template
            for placeholder_name, value in resolved_placeholders.items():
                rendered_prompt = rendered_prompt.replace(f'{{{placeholder_name}}}', str(value))
            
            print(f"     Reads from: {reads_from_step_ids if reads_from_step_ids else 'none (first speaker)'}")
            
            # Execute this actor
            start_time = time.time()
            result = self.execute_instruction(actor_id, rendered_prompt, step_timeout)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log directly to llm_interactions (dialogue_step_runs is now a view)
            interaction_id = self.log_llm_interaction(
                workflow_run_id=workflow_run_id,
                conversation_run_id=conversation_run_id,
                actor_id=actor_id,
                execution_order=execution_order,
                prompt_sent=rendered_prompt,
                response_received=result['response'],
                latency_ms=latency_ms,
                status=result['status'],
                instruction_id=None,  # Multi-actor dialogues don't use instruction templates
                dialogue_step_run_id=None,  # Not used anymore
                error_message=result.get('error')
            )
            conn.commit()
            
            # Log lineage: this interaction reads from previous steps
            for prev_step_order in reads_from_step_ids or []:
                if prev_step_order in dialogue_step_interactions:
                    self.log_interaction_lineage(
                        downstream_interaction_id=interaction_id,
                        upstream_interaction_id=dialogue_step_interactions[prev_step_order],
                        influence_type='dialogue_context',
                        placeholder_used=f'dialogue_step_{prev_step_order}_output'
                    )
            
            # Track this interaction for lineage
            dialogue_step_interactions[execution_order] = interaction_id
            
            if result['status'] != 'SUCCESS':
                print(f"     ❌ {result['status']}: {result.get('error', 'Unknown error')}")
                return False, None
            
            # Store output for next actors to read (by execution_order for placeholder matching)
            dialogue_outputs[execution_order] = result['response']
            
            print(f"     ✅ {actor_role} responded ({latency_ms}ms)")
            if len(result['response']) > 100:
                print(f"     💬 {result['response'][:100]}...")
            else:
                print(f"     💬 {result['response']}")
        
        # Return final output (last actor's response)
        final_output = dialogue_outputs[dialogue_steps[-1]['execution_order']]
        print(f"\n  ✅ Multi-actor dialogue completed - {len(dialogue_steps)} turns")
        
        return True, final_output
    
    def execute_recipe(self, workflow_id: int, test_data: str, batch_id: int = 1, difficulty_level: int = 1, strict: bool = True, execution_mode: str = 'production', target_batch_count: int = 1, job_id: str = None, profile_id: int = None) -> bool:
        """
        Execute a complete recipe workflow
        
        This is the main orchestration method that:
        1. Creates/finds a variation for the input data
        2. Creates a recipe_run to track execution
        3. Executes each conversation in order
        4. For each conversation, executes all instructions
        5. Stores results in database
        6. Auto-saves outputs to target tables (postings/profiles)
        
        Flow:
            Recipe → Sessions (ordered) → Instructions (ordered) → LLM Actor
            Results stored: instruction_runs → conversation_runs → workflow_runs
            Outputs automatically saved to postings or profiles if skill data detected
        
        Args:
            workflow_id: Recipe to execute
            test_data: Input text (job description, profile, etc.)
            batch_id: Batch number for tracking multiple runs (default: 1)
            difficulty_level: Complexity level (default: 1)
            strict: Fail if template placeholders missing (default: True)
            execution_mode: 'testing' or 'production' (affects unique constraints)
            target_batch_count: Expected number of batches (default: 1)
            job_id: Optional job_id to link in variation and save results to
            profile_id: Optional profile_id to link and save results to
            
        Returns:
            bool: True if recipe executed successfully, False otherwise
            
        Side Effects:
            - Creates records in workflow_runs, conversation_runs, instruction_runs
            - May update postings.skill_keywords if job_id provided and skills detected
            - May update profiles.skill_keywords if profile_id provided and skills detected
            
        Example:
            runner = BYRecipeRunner()
            success = runner.execute_recipe(
                workflow_id=1121,
                test_data="Job posting text...",
                job_id="TEST_ORACLE_DBA_001",
                execution_mode="production"
            )
        """
        print(f"\n{'='*70}")
        print(f"🚀 BY Recipe Runner")
        print(f"{'='*70}")
        
        # Get or create test case
        test_case_id = self.get_or_create_test_case(workflow_id, test_data, difficulty_level, job_id)
        
        # Get test case data for template rendering
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT test_data FROM test_cases WHERE test_case_id = %s", (test_case_id,))
        test_case_data = cursor.fetchone()['test_data']
        
        # Create workflow_run with execution_mode
        workflow_run_id = self.create_workflow_run(workflow_id, test_case_id, batch_id, execution_mode, target_batch_count)
        
        # Track conversation outputs for template substitution
        session_outputs = {}
        
        # Track interaction IDs for lineage (maps execution_order -> last interaction_id)
        session_interaction_ids = {}
        
        # Get conversations
        conversations = self.get_recipe_sessions(workflow_id)
        
        if not conversations:
            print("❌ No conversations found for recipe")
            self.update_workflow_run(workflow_run_id, 'FAILED', 'No conversations found')
            return False
        
        print(f"📋 Found {len(conversations)} conversations to execute")
        
        # Update recipe_run to RUNNING
        self.update_workflow_run(workflow_run_id, 'RUNNING')
        
        # Execute conversations with conversation-level branching (index-based loop so we can jump)
        def find_index_by_order(sessions_list, order):
            for i, s in enumerate(sessions_list):
                if s['execution_order'] == order:
                    return i
            return None

        idx = 0
        while idx < len(conversations):
            conversation = conversations[idx]
            conversation_id = conversation['conversation_id']
            step_id = conversation['step_id']
            conversation_name = conversation['conversation_name']
            actor_id = conversation['actor_id']
            execution_order = conversation['execution_order']

            print(f"\n{'─'*70}")
            print(f"📍 Session {execution_order}: {conversation_name} (actor: {actor_id})")
            print(f"{'─'*70}")

            # Create conversation_run
            conversation_run_id = self.create_conversation_run(workflow_run_id, step_id, conversation_id, execution_order, execution_mode)

            # Check if this is a multi-actor dialogue
            conversation_type = self.check_conversation_type(conversation_id)
            
            if conversation_type == 'multi_actor_dialogue':
                # Execute multi-actor dialogue (scripted turns)
                dialogue_success, final_output = self.execute_multi_actor_dialogue(
                    conversation_run_id, conversation_id, test_case_data, timeout=300
                )
                
                if not dialogue_success:
                    self.update_session_run(conversation_run_id, 'FAILED', 'Multi-actor dialogue failed')
                    self.update_workflow_run(workflow_run_id, 'FAILED', f'Conversation {execution_order} dialogue failed')
                    return False
                
                # Store final output for next conversations
                session_outputs[execution_order] = final_output
                session_last_response = final_output
                
                self.update_session_run(conversation_run_id, 'SUCCESS')
                print(f"\n  ✅ Session {execution_order} completed successfully")
                
                # Multi-actor dialogues don't have branching yet - always continue
                idx += 1
                continue
            
            # Standard single-actor conversation (original code path)
            # Get instructions
            instructions = self.get_conversation_instructions(conversation_id)

            if not instructions:
                print(f"  ⚠️  No instructions found for conversation {conversation_name}")
                self.update_session_run(conversation_run_id, 'FAILED', 'No instructions')
                # default behavior: stop
                self.update_workflow_run(workflow_run_id, 'FAILED', f'No instructions for conversation {execution_order}')
                return False

            print(f"  📝 {len(instructions)} instructions to execute")

            # Execute each instruction
            session_success = True
            session_last_response = None
            last_instruction_run_id = None  # Track for branch evaluation

            for instruction in instructions:
                instruction_id = instruction['instruction_id']
                step_num = instruction['step_number']
                description = instruction['step_description']
                prompt_template = instruction['prompt_template']
                timeout = instruction['timeout_seconds'] or 30

                print(f"\n  Step {step_num}: {description}")

                # Render prompt with validation (strict mode by default)
                try:
                    rendered_prompt, missing_placeholders = self.render_prompt(
                        prompt_template, test_case_data, session_outputs, execution_order, strict=strict
                    )
                except ValueError as e:
                    print(f"  ❌ Template rendering failed:")
                    print(f"     {str(e)}")
                    self.update_session_run(conversation_run_id, 'FAILED', str(e))
                    session_success = False
                    break

                print(f"  🤖 Calling {actor_id}...")

                # Execute
                result = self.execute_instruction(actor_id, rendered_prompt, timeout)

                # Save result (store rendered prompt, not template) and log to llm_interactions
                last_instruction_run_id, interaction_id = self.save_instruction_run(
                    conversation_run_id, instruction_id, 
                    step_num, rendered_prompt, result,
                    actor_id, workflow_run_id
                )
                
                # Track interaction for lineage
                # If this instruction used previous conversation outputs, log lineage
                if session_outputs:
                    # Check which placeholders were used in the prompt_template
                    import re
                    session_placeholder_pattern = r'\{session_(\d+)_output\}'
                    matches = re.findall(session_placeholder_pattern, prompt_template)
                    for prev_session_order in matches:
                        prev_order = int(prev_session_order)
                        if prev_order in session_interaction_ids:
                            self.log_interaction_lineage(
                                downstream_interaction_id=interaction_id,
                                upstream_interaction_id=session_interaction_ids[prev_order],
                                influence_type='direct_read',
                                placeholder_used=f'session_{prev_order}_output'
                            )
                
                # Also log sequential relationship within same conversation
                if step_num > 1:
                    # This instruction follows the previous one in the conversation
                    # Look for previous interaction in this conversation
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT interaction_id 
                        FROM llm_interactions 
                        WHERE conversation_run_id = %s AND execution_order = %s
                    """, (conversation_run_id, step_num - 1))
                    prev_interaction = cursor.fetchone()
                    if prev_interaction:
                        self.log_interaction_lineage(
                            downstream_interaction_id=interaction_id,
                            upstream_interaction_id=prev_interaction['interaction_id'],
                            influence_type='sequential',
                            placeholder_used=None
                        )
                
                # Store response for next instructions
                if result['status'] == 'SUCCESS' and result['response']:
                    session_last_response = result['response']

                # Display result
                if result['status'] == 'SUCCESS':
                    response_preview = result['response'][:100] if result['response'] else 'N/A'
                    print(f"  ✅ {result['status']} ({result['latency_ms']}ms)")
                    print(f"  💬 Response: {response_preview}...")
                else:
                    print(f"  ❌ {result['status']}: {result['error']}")
                    session_success = False
                    break

            # Store conversation output for future conversation templates
            if session_last_response:
                session_outputs[execution_order] = session_last_response
                # Store the last interaction ID for this conversation (for lineage tracking)
                # Get the last interaction from this conversation
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT interaction_id 
                    FROM llm_interactions 
                    WHERE conversation_run_id = %s 
                    ORDER BY execution_order DESC 
                    LIMIT 1
                """, (conversation_run_id,))
                last_interaction = cursor.fetchone()
                if last_interaction:
                    session_interaction_ids[execution_order] = last_interaction['interaction_id']
                print(f"  💾 Stored conversation {execution_order} output for future templates")

            # Update conversation status
            if session_success:
                self.update_session_run(conversation_run_id, 'SUCCESS')
                print(f"\n  ✅ Session {execution_order} completed successfully")
            else:
                self.update_session_run(conversation_run_id, 'FAILED', 'Instruction failed')
                print(f"\n  ❌ Session {execution_order} failed")
                # Check failure action
                if conversation.get('on_failure_action') == 'stop':
                    print(f"\n❌ Stopping recipe execution (on_failure_action = stop)")
                    self.update_workflow_run(workflow_run_id, 'FAILED', f'Session {execution_order} failed')
                    return False

            # Determine next conversation to execute (DYNAMIC BRANCHING)
            next_order = None
            
            # If last instruction had branches, evaluate them
            if last_instruction_run_id and session_last_response:
                # Get last instruction_id from the last instruction in conversation
                last_instruction = instructions[-1]
                last_instruction_id = last_instruction['instruction_id']
                
                matched_branch = self.evaluate_branches(
                    last_instruction_id, 
                    last_instruction_run_id, 
                    session_last_response
                )
                
                if matched_branch:
                    # Branch matched! Determine target
                    if matched_branch['next_conversation_id']:
                        # Jump to a different conversation
                        target_session_id = matched_branch['next_conversation_id']
                        
                        # Find execution_order for this conversation in our recipe
                        for s in conversations:
                            if s['conversation_id'] == target_session_id:
                                next_order = s['execution_order']
                                print(f"\n  🔀 BRANCH: Jumping to conversation {next_order} ({s['conversation_name']})")
                                break
                        
                        if next_order is None:
                            print(f"  ⚠️  Branch target conversation_id {target_session_id} not found in recipe!")
                            # Fall through to linear
                    
                    elif matched_branch['next_instruction_id']:
                        # Jump to different instruction (same conversation)
                        # For now, we'll treat this as "continue in same conversation"
                        # More complex intra-conversation branching would need additional logic
                        print(f"  🔀 BRANCH: Instruction-level branch (staying in conversation)")
                        next_order = execution_order + 1
                    
                    else:
                        # Branch says END SESSION (both next_instruction_id and next_conversation_id are NULL)
                        print(f"  🔀 BRANCH: End conversation (no next target)")
                        break  # Exit conversation loop, recipe complete
            
            # Default: continue linearly
            if next_order is None:
                next_order = execution_order + 1

            # Compute next index
            next_idx = find_index_by_order(conversations, next_order)
            if next_idx is None:
                # no more conversations in sequence -> finish
                break
            else:
                idx = next_idx
                # continue while loop (do not idx += 1 here)
                continue
            
            idx += 1
        
        # All conversations completed - save outputs BEFORE updating recipe_run status
        # 
        # CRITICAL: Save outputs before updating recipe_run to SUCCESS to avoid
        # unique constraint crashes that would prevent saving.
        #
        # AUTO-SAVE LOGIC:
        # If the last conversation output is a JSON array with skill objects (has 'skill' key),
        # automatically save to the appropriate table:
        # - job_id provided → save to postings.skill_keywords
        # - profile_id provided → save to profiles.skill_keywords
        #
        # This makes the runner generic - it works with any recipe that outputs skills,
        # without needing to hardcode recipe IDs or conversation numbers.
        if job_id and session_outputs:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get ALL conversation outputs - find the last one that has content
            last_session_output = None
            last_session_order = None
            for order in sorted(session_outputs.keys(), reverse=True):
                if session_outputs[order]:
                    last_session_output = session_outputs[order]
                    last_session_order = order
                    break
            
            # Legacy support: check for specific conversation patterns
            session_7_output = session_outputs.get(7)  # Formatted summary (old Recipe 1114)
            session_9_output = session_outputs.get(9)  # Skill keywords (old Recipe 1114)
            
            # Determine what to save based on recipe structure and outputs
            if last_session_output and job_id:
                # GENERIC SKILL DETECTION:
                # Try to parse as JSON to determine if it's skills data.
                # This avoids hardcoding recipe IDs or conversation numbers.
                # Any recipe that outputs skill objects will work automatically.
                try:
                    import json
                    parsed_output = json.loads(last_session_output)
                    
                    # Check if it looks like skills data (array of objects with "skill" key)
                    # Example: [{"skill": "Python", "importance": "essential", ...}, ...]
                    if isinstance(parsed_output, list) and len(parsed_output) > 0:
                        if isinstance(parsed_output[0], dict) and 'skill' in parsed_output[0]:
                            # This is skills data - save to skill_keywords
                            try:
                                cursor.execute("""
                                    UPDATE postings 
                                    SET skill_keywords = %s::jsonb,
                                        updated_at = NOW()
                                    WHERE posting_id = %s
                                    RETURNING posting_id, jsonb_array_length(skill_keywords) as skill_count
                                """, (last_session_output, job_id))
                                result = cursor.fetchone()
                                conn.commit()
                                
                                if result:
                                    print(f"\n💾 Saved skills to postings table:")
                                    print(f"   Posting ID: {result['posting_id']}")
                                    print(f"   Skills: {result['skill_count']} extracted")
                                    print(f"   From conversation: {last_session_order}")
                                else:
                                    print(f"\n⚠️  Warning: Could not update job_id {job_id} in postings table")
                                
                            except Exception as e:
                                conn.rollback()
                                print(f"\n❌ Error saving skills to postings table: {e}")
                            finally:
                                cursor.close()
                                conn.close()
                        else:
                            print(f"\n⚠️  Session {last_session_order} output doesn't look like skills data (no 'skill' key)")
                            cursor.close()
                            conn.close()
                    else:
                        print(f"\n⚠️  Session {last_session_order} output is not a valid JSON array")
                        cursor.close()
                        conn.close()
                        
                except json.JSONDecodeError:
                    # Not JSON - might be a summary. Check legacy patterns
                    print(f"\n⚠️  Session {last_session_order} output is not valid JSON")
                    cursor.close()
                    conn.close()
                    
            elif session_7_output and session_9_output:
                # Both summary and skills available (full Recipe 1114 with 9 conversations - legacy)
                try:
                    cursor.execute("""
                        UPDATE postings 
                        SET extracted_summary = %s,
                            skill_keywords = %s::jsonb,
                            summary_extraction_status = 'success',
                            updated_at = NOW()
                        WHERE posting_id = %s
                        RETURNING posting_id, LENGTH(extracted_summary) as summary_length, 
                                  jsonb_array_length(skill_keywords) as skill_count
                    """, (session_7_output, session_9_output, job_id))
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"\n💾 Saved to postings table:")
                        print(f"   Posting ID: {result['posting_id']}")
                        print(f"   Summary: {result['summary_length']:,} characters")
                        print(f"   Skills: {result['skill_count']} extracted")
                    else:
                        print(f"\n⚠️  Warning: Could not update job_id {job_id} in postings table")
                    
                except Exception as e:
                    conn.rollback()
                    print(f"\n❌ Error saving to postings table: {e}")
                finally:
                    cursor.close()
                    conn.close()
                    
            elif session_7_output:
                # Only summary available (Recipe 1114 with 7 conversations - old version)
                try:
                    cursor.execute("""
                        UPDATE postings 
                        SET extracted_summary = %s,
                            summary_extraction_status = 'success',
                            updated_at = NOW()
                        WHERE posting_id = %s
                        RETURNING posting_id, LENGTH(extracted_summary) as summary_length
                    """, (session_7_output, job_id))
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"\n💾 Saved extracted summary to postings table:")
                        print(f"   Posting ID: {result['posting_id']}")
                        print(f"   Summary length: {result['summary_length']:,} characters")
                    else:
                        print(f"\n⚠️  Warning: Could not update job_id {job_id} in postings table")
                        
                except Exception as e:
                    print(f"\n⚠️  Error saving summary to postings table: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()
            else:
                print(f"\n⚠️  Warning: No conversation output to save")
        
        # NOW update recipe_run status to SUCCESS (after outputs are saved)
        self.update_workflow_run(workflow_run_id, 'SUCCESS')
        
        print(f"\n{'='*70}")
        print(f"✅ Recipe execution completed successfully!")
        print(f"   Recipe Run ID: {workflow_run_id}")
        print(f"{'='*70}\n")
        
        return True

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Execute BY workflows from PostgreSQL')
    parser.add_argument('--recipe-id', type=int, required=True, help='Recipe ID to execute')
    parser.add_argument('--variation-id', type=int, help='Use existing variation by ID')
    parser.add_argument('--test-data', type=str, help='Test data/input for recipe (if not using variation-id)')
    parser.add_argument('--job-id', type=str, help='Job ID from postings table (will fetch job_description)')
    parser.add_argument('--profile-id', type=int, help='Profile ID from profiles table (will fetch profile_raw_text)')
    parser.add_argument('--batch-id', type=int, default=1, help='Batch ID (default: 1)')
    parser.add_argument('--difficulty', type=int, default=1, help='Difficulty level (default: 1)')
    parser.add_argument('--allow-missing', action='store_true', help='Allow missing placeholders (disable strict mode)')
    parser.add_argument('--execution-mode', type=str, default='production', 
                       choices=['testing', 'production'],
                       help='Execution mode: testing (5 batches) or production (1 batch)')
    parser.add_argument('--target-batch-count', type=int, default=1,
                       help='Target number of batches (default: 1 for production, 5 for testing)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.variation_id and not args.test_data and not args.job_id and not args.profile_id:
        print("❌ Error: Must provide either --variation-id, --test-data, --job-id, or --profile-id")
        exit(1)
    
    runner = BYRecipeRunner()
    
    # Track job_id or profile_id if provided
    job_id_for_variation = None
    profile_id_for_variation = None
    
    # If using job_id, fetch from postings table
    if args.job_id:
        job_id_for_variation = args.job_id
        conn = runner.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_description, job_title, location_city, location_country
            FROM postings 
            WHERE posting_id = %s
        """, (args.job_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Error: Job ID {args.job_id} not found in postings")
            exit(1)
        
        job_description = result['job_description']
        test_data = job_description
        location = f"{result['location_city']}, {result['location_country']}" if result['location_city'] else result['location_country']
        print(f"✅ Loaded job {args.job_id}: {result['job_title']} in {location}")
        print(f"   Description length: {len(job_description):,} characters")
        
    # If using profile_id, fetch from profiles table
    elif args.profile_id:
        profile_id_for_variation = args.profile_id
        conn = runner.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT profile_raw_text, full_name, current_title 
            FROM profiles 
            WHERE profile_id = %s AND enabled = TRUE
        """, (args.profile_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Error: Profile ID {args.profile_id} not found in profiles")
            exit(1)
        
        profile_raw_text = result['profile_raw_text']
        test_data = profile_raw_text
        print(f"✅ Loaded profile {args.profile_id}: {result['full_name']} - {result['current_title']}")
        print(f"   Profile length: {len(profile_raw_text):,} characters")
        
    # If using existing test case, fetch it and use directly
    elif args.variation_id:
        conn = runner.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT test_data FROM test_cases WHERE test_case_id = %s", (args.variation_id,))
        result = cursor.fetchone()
        if not result:
            print(f"❌ Error: Test case {args.variation_id} not found")
            exit(1)
        
        print(f"✅ Using existing test case {args.variation_id}")
        test_data = ""
    else:
        test_data = args.test_data
    
    strict_mode = not args.allow_missing  # Strict by default, unless --allow-missing flag
    success = runner.execute_recipe(
        args.recipe_id, 
        test_data, 
        args.batch_id, 
        args.difficulty, 
        strict_mode,
        execution_mode=args.execution_mode,
        target_batch_count=args.target_batch_count,
        job_id=job_id_for_variation,
        profile_id=profile_id_for_variation
    )
    
    exit(0 if success else 1)

if __name__ == '__main__':
    main()
