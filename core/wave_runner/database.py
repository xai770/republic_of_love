"""
Database Helper - Query interactions and manage state
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <150 lines
"""

import json
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseHelper:
    """Helper for querying and updating interactions table."""
    
    def __init__(self, db_conn):
        """
        Initialize database helper.
        
        Args:
            db_conn: psycopg2 connection object
        """
        self.conn = db_conn
    
    def get_pending_interactions(
        self, 
        posting_id: Optional[int] = None,
        workflow_run_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get pending interactions ready for execution.
        
        Query pattern: Find interactions where:
        - status = 'pending'
        - enabled = TRUE
        - invalidated = FALSE
        - No parent dependencies OR parent is completed
        
        Args:
            posting_id: Filter by posting (posting-centric mode)
            workflow_run_id: Filter by workflow run (workflow-centric mode)
            limit: Maximum interactions to return
            
        Returns:
            List of interaction dicts (interaction_id, actor_id, input, etc.)
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Base query: Find pending interactions with no blocking parents
        # IMPORTANT: Excludes orphaned interactions (old, no run_id, stale workflow_run)
        query = """
            SELECT 
                i.interaction_id,
                i.posting_id,
                i.conversation_id,
                i.workflow_run_id,
                i.run_id,
                i.actor_id,
                i.actor_type,
                i.execution_order,
                i.parent_interaction_id,
                i.input_interaction_ids,
                i.input,
                i.max_retries,
                i.retry_count,
                a.actor_name,
                a.script_code,
                a.script_file_path,
                a.actor_type as actor_execution_type,
                c.conversation_name
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE i.status = 'pending'
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
              AND (
                  -- No parent dependency
                  i.parent_interaction_id IS NULL
                  OR
                  -- Parent is completed
                  EXISTS (
                      SELECT 1 FROM interactions parent
                      WHERE parent.interaction_id = i.parent_interaction_id
                        AND parent.status = 'completed'
                  )
              )
              -- ORPHAN FILTER: Only process interactions that belong to active runs
              AND (
                  -- Pipeline V2: Has run_id (explicit reprocessing) 
                  i.run_id IS NOT NULL
                  OR
                  -- Legacy: Has workflow_run that is still 'running'
                  EXISTS (
                      SELECT 1 FROM workflow_runs wr 
                      WHERE wr.workflow_run_id = i.workflow_run_id 
                        AND wr.status = 'running'
                  )
                  OR
                  -- Fresh orphans: No workflow_run but created recently (< 2 hours)
                  -- Allows seed interactions to be picked up before workflow_run is set
                  (i.workflow_run_id IS NULL AND i.created_at > NOW() - INTERVAL '2 hours')
              )
        """
        
        params = []
        
        if posting_id is not None:
            query += " AND i.posting_id = %s"
            params.append(posting_id)
        
        if workflow_run_id is not None:
            query += " AND i.workflow_run_id = %s"
            params.append(workflow_run_id)
        
        query += " ORDER BY i.execution_order, i.interaction_id LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_interaction_by_id(self, interaction_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single interaction by ID.
        
        Used by batch execution to fetch interaction details.
        
        Args:
            interaction_id: Interaction to fetch
            
        Returns:
            Interaction dict or None if not found
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT 
                i.interaction_id,
                i.posting_id,
                i.conversation_id,
                i.workflow_run_id,
                i.run_id,
                i.actor_id,
                i.actor_type,
                i.execution_order,
                i.parent_interaction_id,
                i.input_interaction_ids,
                i.input,
                i.max_retries,
                i.retry_count,
                a.actor_name,
                a.script_code,
                a.script_file_path,
                a.actor_type as actor_execution_type,
                a.execution_config,
                c.conversation_name
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE i.interaction_id = %s
        """, (interaction_id,))
        
        return cursor.fetchone()
    
    def claim_interaction(self, interaction_id: int, runner_id: str) -> bool:
        """
        Atomically claim an interaction for execution.
        
        Uses FOR UPDATE SKIP LOCKED to prevent race conditions.
        
        Args:
            interaction_id: Interaction to claim
            runner_id: Identifier for this wave runner instance
            
        Returns:
            True if claimed successfully, False if already claimed
        """
        cursor = self.conn.cursor()
        
        # Atomic claim: Update status only if still pending
        # Also set heartbeat_at so reaper knows when we started
        cursor.execute("""
            UPDATE interactions
            SET status = 'running',
                started_at = NOW(),
                heartbeat_at = NOW(),
                updated_at = NOW()
            WHERE interaction_id = %s
              AND status = 'pending'
            RETURNING interaction_id
        """, (interaction_id,))
        
        result = cursor.fetchone()
        self.conn.commit()
        
        return result is not None
    
    def update_interaction_success(
        self, 
        interaction_id: int, 
        output: Dict[str, Any]
    ) -> bool:
        """
        Mark interaction as completed with output.
        
        Uses optimistic locking: only updates if status='running'.
        This prevents race conditions where the reaper marks an interaction
        as failed while we're still processing it.
        
        Args:
            interaction_id: Interaction that completed
            output: Result data (will be stored as JSONB)
            
        Returns:
            True if updated successfully, False if interaction was reaped/modified
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE interactions
            SET status = 'completed',
                output = %s,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE interaction_id = %s
              AND status = 'running'
            RETURNING interaction_id
        """, (psycopg2.extras.Json(output), interaction_id))
        
        updated = cursor.fetchone()
        self.conn.commit()
        
        if updated is None:
            # Interaction was reaped or modified by another process
            import logging
            logging.getLogger('wave_runner').warning(
                f"Interaction {interaction_id} was modified while processing. "
                f"Result discarded to prevent corruption."
            )
            return False
        return True
    
    def update_interaction_failed(
        self, 
        interaction_id: int, 
        error_message: str,
        will_retry: bool = False,
        failure_type: str = None
    ) -> None:
        """
        Mark interaction as failed with failure classification.
        
        Args:
            interaction_id: Interaction that failed
            error_message: Error description
            will_retry: Will this be retried? (retry_count < max_retries AND retriable)
            failure_type: Classification (timeout, interrupted, script_error, etc.)
        """
        cursor = self.conn.cursor()
        
        if will_retry:
            # Increment retry count, set back to pending
            cursor.execute("""
                UPDATE interactions
                SET status = 'pending',
                    error_message = %s,
                    failure_type = %s,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE interaction_id = %s
            """, (error_message, failure_type, interaction_id))
        else:
            # Mark as failed (no more retries or not retriable)
            cursor.execute("""
                UPDATE interactions
                SET status = 'failed',
                    error_message = %s,
                    failure_type = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE interaction_id = %s
            """, (error_message, failure_type, interaction_id))
        
        self.conn.commit()
    
    def update_interaction_prompt(
        self,
        interaction_id: int,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> None:
        """
        Update interaction input with actual substituted prompt.
        
        For traceability: Store the ACTUAL prompt sent to AI model,
        not just the template. This allows debugging what exactly
        the AI saw when it produced its output.
        
        Args:
            interaction_id: Interaction to update
            prompt: The actual substituted user prompt
            system_prompt: The actual system prompt (if any)
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get current input
        cursor.execute("""
            SELECT input FROM interactions WHERE interaction_id = %s
        """, (interaction_id,))
        row = cursor.fetchone()
        
        if row:
            input_data = row['input'] or {}
            
            # Update with actual prompts
            input_data['prompt'] = prompt
            input_data['prompt_length'] = len(prompt)
            if system_prompt:
                input_data['system_prompt'] = system_prompt
            
            # Store back to database
            cursor.execute("""
                UPDATE interactions
                SET input = %s,
                    updated_at = NOW()
                WHERE interaction_id = %s
            """, (Json(input_data), interaction_id))
            
            self.conn.commit()
    
    def get_previous_interaction_output(
        self, 
        posting_id: int, 
        conversation_id: int,
        execution_order: int
    ) -> Optional[Dict[str, Any]]:
        """
        Query previous interaction's output (for script actors).
        
        Pattern from SCRIPT_ACTOR_COOKBOOK.md: Scripts should query
        the database for input, NOT rely on in-memory state.
        
        Args:
            posting_id: Current posting
            conversation_id: Current conversation
            execution_order: Get interaction BEFORE this order
            
        Returns:
            Previous interaction's output, or None if not found
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT output
            FROM interactions
            WHERE posting_id = %s
              AND conversation_id = %s
              AND execution_order < %s
              AND status = 'completed'
            ORDER BY execution_order DESC
            LIMIT 1
        """, (posting_id, conversation_id, execution_order))
        
        result = cursor.fetchone()
        return result['output'] if result else None
    
    def get_parent_interaction_outputs(
        self, 
        interaction_id: int
    ) -> Dict[int, Dict[str, Any]]:
        """
        Query parent interaction outputs (for AI conversations).
        
        CRITICAL: The interactions table IS your template engine!
        Query it directly instead of using template substitution.
        
        This prevents the template substitution bug that caused 122
        hallucinated summaries in production (multi-wave processing
        loses in-memory state, but database persists reliably).
        
        Reference: docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md
        
        Args:
            interaction_id: Current interaction
            
        Returns:
            Dict mapping conversation_id → output_dict
            Example: {3335: {'response': 'Summary text...'}, 3336: {...}}
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Walk up ancestry chain to get all ancestor outputs (not just direct parents)
        # This is critical for multi-step workflows like WF3005 where grandparent
        # output (orphan_skills from fetcher) needs to reach grandchild (classifier)
        cursor.execute("""
            WITH RECURSIVE ancestors AS (
                -- Start with direct parents
                SELECT i.interaction_id, i.conversation_id, i.output, i.parent_interaction_id, 1 as depth
                FROM interactions i
                WHERE i.interaction_id = ANY(
                    SELECT unnest(input_interaction_ids) 
                    FROM interactions 
                    WHERE interaction_id = %s
                )
                AND i.status = 'completed'
                
                UNION ALL
                
                -- Walk up the chain (grandparents, etc.)
                SELECT p.interaction_id, p.conversation_id, p.output, p.parent_interaction_id, a.depth + 1
                FROM interactions p
                JOIN ancestors a ON p.interaction_id = a.parent_interaction_id
                WHERE a.depth < 5 AND p.status = 'completed'
            )
            SELECT DISTINCT ON (conversation_id) conversation_id, output
            FROM ancestors
            ORDER BY conversation_id, depth
        """, (interaction_id,))
        
        results = cursor.fetchall()
        
        # Return dict: {conversation_id: output_dict}
        return {row['conversation_id']: row['output'] for row in results}
    
    def get_posting_data(self, posting_id: int) -> Optional[Dict[str, Any]]:
        """
        Get posting data for AI prompt building.
        
        Used by AI conversations to access job description, title, etc.
        
        Args:
            posting_id: Posting to fetch
            
        Returns:
            Posting dict with all fields, or None if not found
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT 
                posting_id,
                job_title,
                job_description,
                location_city,
                location_country,
                source,
                external_id,
                extracted_summary,
                skill_keywords,
                ihl_score,
                posting_status,
                source_metadata
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        return cursor.fetchone()
    
    def update_interaction_prompt(
        self,
        interaction_id: int,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> None:
        """
        Update interaction input with actual substituted prompt.
        
        Stores the actual prompt sent to AI (with all placeholders substituted)
        alongside the original template for full traceability and debugging.
        
        Args:
            interaction_id: Interaction to update
            prompt: Actual substituted prompt sent to AI
            system_prompt: Actual system prompt (if any)
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get current input
        cursor.execute("SELECT input FROM interactions WHERE interaction_id = %s", 
                      (interaction_id,))
        row = cursor.fetchone()
        input_data = (row['input'] if row else None) or {}  # Handle both missing row and NULL input
        
        # Update with actual prompt
        input_data['prompt'] = prompt
        input_data['prompt_length'] = len(prompt)
        if system_prompt:
            input_data['system_prompt'] = system_prompt
        
        # Store back
        cursor.execute("""
            UPDATE interactions 
            SET input = %s::jsonb 
            WHERE interaction_id = %s
        """, (json.dumps(input_data), interaction_id))
        
        self.conn.commit()
        cursor.close()
    
    def get_instruction_prompt(self, conversation_id: int) -> Optional[str]:
        """
        Get prompt template for a conversation from instructions table.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Prompt template string with variables like {job_description}, or None if not found
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            SELECT prompt_template
            FROM instructions
            WHERE conversation_id = %s
              AND enabled = TRUE
            LIMIT 1
        """, (conversation_id,))
        
        result = cursor.fetchone()
        return result['prompt_template'] if result else None
    
    def update_workflow_state(
        self,
        workflow_run_id: int,
        updates: Dict[str, Any]
    ) -> None:
        """
        Update workflow state with new key-value pairs.
        
        Merges updates into existing state (doesn't replace).
        
        Args:
            workflow_run_id: Workflow run to update
            updates: Dict of state updates (e.g., {'extract_summary': '...'})
        """
        cursor = self.conn.cursor()
        
        # Use JSONB concatenation operator to merge
        cursor.execute("""
            UPDATE workflow_runs
            SET state = COALESCE(state, '{}'::jsonb) || %s::jsonb
            WHERE workflow_run_id = %s
        """, (json.dumps(updates), workflow_run_id))
        
        self.conn.commit()
        cursor.close()
    
    def get_workflow_state(
        self,
        workflow_run_id: int
    ) -> Dict[str, Any]:
        """Get current workflow state."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT state FROM workflow_runs 
                WHERE workflow_run_id = %s
            """, (workflow_run_id,))
            
            row = cursor.fetchone()
            cursor.close()
            return row['state'] if row and row['state'] else {}
        except Exception as e:
            cursor.close()
            # Don't fail if state retrieval fails - just return empty state
            return {}
