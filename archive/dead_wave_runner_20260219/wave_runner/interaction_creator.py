"""
Interaction Creator - Create child interactions after parent completes
Author: Sandy (GitHub Copilot)
Date: November 23, 2025

This module handles creating child interactions based on:
1. Instruction steps (branching rules from instruction_steps table)
2. Prompt building (database-driven template substitution)
"""

import psycopg2
import psycopg2.extras
import json
import re
from typing import Dict, List, Any, Optional
import logging


class InteractionCreator:
    """Create child interactions after parent completes."""
    
    def __init__(self, db_conn, db_helper, logger=None):
        """
        Initialize interaction creator.
        
        Args:
            db_conn: psycopg2 connection
            db_helper: DatabaseHelper instance for queries
            logger: Optional logger
        """
        self.conn = db_conn
        self.db = db_helper
        self.logger = logger or logging.getLogger(__name__)
    
    def _get_ancestor_outputs(
        self, 
        parent_interaction_ids: List[int],
        workflow_run_id: Optional[int] = None
    ) -> Dict[int, Any]:
        """
        Walk up the ancestry chain to get all ancestor outputs.
        
        Returns dict of {conversation_id: output} for all ancestors.
        Used by script actors that need access to grandparent/great-grandparent outputs.
        """
        if not parent_interaction_ids:
            return {}
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Walk up to 5 levels of ancestry
        cursor.execute("""
            WITH RECURSIVE ancestors AS (
                -- Start with direct parents
                SELECT i.interaction_id, i.conversation_id, i.output, i.parent_interaction_id, 1 as depth
                FROM interactions i
                WHERE i.interaction_id = ANY(%s)
                
                UNION ALL
                
                -- Walk up the chain
                SELECT p.interaction_id, p.conversation_id, p.output, p.parent_interaction_id, a.depth + 1
                FROM interactions p
                JOIN ancestors a ON p.interaction_id = a.parent_interaction_id
                WHERE a.depth < 5
            )
            SELECT DISTINCT ON (conversation_id) conversation_id, output
            FROM ancestors
            ORDER BY conversation_id, depth
        """, (parent_interaction_ids,))
        
        result = {row['conversation_id']: row['output'] for row in cursor.fetchall()}
        cursor.close()
        return result
    
    def build_prompt_from_template(
        self, 
        conversation_id: int,
        posting_id: int,
        parent_interaction_ids: List[int],
        workflow_run_id: Optional[int] = None
    ) -> str:
        """
        Build prompt from database template by substituting variables.
        
        This is the CORRECT way to create interaction prompts:
        1. Query instruction template from database
        2. Query posting data
        2. Query posting data
        3. Query parent interaction outputs
        4. Load workflow state (semantic keys)
        5. Substitute variables in template
        6. Return final prompt (to store in interactions.input)
        
        Args:
            conversation_id: Conversation ID for this interaction
            posting_id: Posting ID
            parent_interaction_ids: List of parent interaction IDs
            workflow_run_id: Workflow run ID (for loading workflow state)
            
        Returns:
            Fully-built prompt ready to store in interactions.input
        """
        # TEMPORARY DEBUG
        self.logger.info(f"=== build_prompt_from_template called ===")
        self.logger.info(f"  conversation_id={conversation_id}, parent_ids={parent_interaction_ids}")
        
        # 1. Get instruction prompt template
        prompt_template = self.db.get_instruction_prompt(conversation_id)
        if not prompt_template:
            raise ValueError(f"No instruction template for conversation {conversation_id}")
        
        # 2. Get posting data (optional - global workflows don't have postings)
        posting = {}
        if posting_id:
            posting = self.db.get_posting_data(posting_id) or {}
        
        # 3. Get parent outputs (if any)
        parents = {}
        if parent_interaction_ids:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT i.interaction_id, i.conversation_id, i.output
                FROM interactions i
                WHERE i.interaction_id = ANY(%s)
                ORDER BY i.created_at
            """, (parent_interaction_ids,))
            
            for row in cursor.fetchall():
                parents[row['conversation_id']] = row['output']
            
            cursor.close()
        
        # 3a. Walk up the ancestry chain to get all ancestor outputs
        # This allows templates to use {conversation_XXXX_output} for grandparents
        if parent_interaction_ids:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Walk up to 5 levels of ancestry
            cursor.execute("""
                WITH RECURSIVE ancestors AS (
                    -- Start with direct parents
                    SELECT i.interaction_id, i.conversation_id, i.output, i.parent_interaction_id, 1 as depth
                    FROM interactions i
                    WHERE i.interaction_id = ANY(%s)
                    
                    UNION ALL
                    
                    -- Walk up the chain
                    SELECT p.interaction_id, p.conversation_id, p.output, p.parent_interaction_id, a.depth + 1
                    FROM interactions p
                    JOIN ancestors a ON p.interaction_id = a.parent_interaction_id
                    WHERE a.depth < 5
                )
                SELECT DISTINCT ON (conversation_id) conversation_id, output
                FROM ancestors
                ORDER BY conversation_id, depth
            """, (parent_interaction_ids,))
            
            ancestor_rows = cursor.fetchall()
            self.logger.info(f"  Ancestor query returned {len(ancestor_rows)} rows")
            
            for row in ancestor_rows:
                self.logger.info(f"    Ancestor conv {row['conversation_id']}: has_orphan_skills={row['output'].get('orphan_skills') is not None if isinstance(row['output'], dict) else False}")
                # Don't overwrite if already have this conversation's output
                if row['conversation_id'] not in parents:
                    parents[row['conversation_id']] = row['output']
            
            cursor.close()
        
        # 3b. Load workflow state (semantic keys)
        workflow_state = {}
        if workflow_run_id:
            workflow_state = self.db.get_workflow_state(workflow_run_id)
        
        # 3c. Get profile data if workflow_run metadata has profile_id
        profile_raw_text = ''
        if workflow_run_id:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT p.profile_raw_text
                FROM workflow_runs wr
                JOIN profiles p ON (wr.metadata->>'profile_id')::int = p.profile_id
                WHERE wr.workflow_run_id = %s
            """, (workflow_run_id,))
            row = cursor.fetchone()
            if row and row['profile_raw_text']:
                profile_raw_text = row['profile_raw_text']
            cursor.close()
        
        # 4. Build variable mapping
        variables = {
            # Posting data (empty strings if no posting - global workflows)
            'job_description': posting.get('job_description', ''),
            'job_title': posting.get('job_title', ''),
            'posting_id': str(posting_id) if posting_id else '',
            'location_city': posting.get('location_city', ''),
            'location_country': posting.get('location_country', ''),
            
            # Profile data (for WF1122 and profile workflows)
            'profile_raw_text': profile_raw_text,
            
            # Legacy template variables (some instructions use these)
            'variations_param_1': posting.get('job_description', ''),
            'variations_param_2': posting.get('job_title', ''),
            'variations_param_3': posting.get('location_city', ''),
            
            # REMOVED: Workflow state variables (extract_summary, improved_summary, current_summary, etc.)
            # These caused cross-posting contamination in batch runs because workflow_runs.state
            # is shared across all postings in a batch. See: docs/debugging/ROOT_CAUSE_SUMMARY_CONTAMINATION_2025-12-09.md
            # Use {conversation_XXXX_output} or {parent_response} instead - these are per-posting.
        }
        
        # 4a. Auto-expose ALL posting columns as template variables
        # This ensures {extracted_summary}, {skill_keywords}, {ihl_score}, etc. are available
        # See: docs/daily_notes/2025-12-10_template_vs_sql_memo.md
        for key, value in posting.items():
            if key not in variables:
                variables[key] = str(value) if value is not None else ''
        
        # 4b. DYNAMIC parent output extraction (replaces hardcoded mappings)
        # This generates conversation_XXXX_output, session_X_output, etc. automatically
        # See: docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md
        
        for conv_id, parent_output in parents.items():
            if isinstance(parent_output, dict):
                # AI actor outputs have 'response' key
                response = parent_output.get('response', '')
                
                # Generate conversation_XXXX_output pattern
                variables[f'conversation_{conv_id}_output'] = response
                
                # Also extract all other keys from script outputs
                # Script actors output JSON - extract all keys as template variables
                # e.g., {orphan_skills: "..."} becomes {orphan_skills} in template
                for key, value in parent_output.items():
                    if key not in ('response', 'model', 'latency_ms') and isinstance(value, (str, int, float)):
                        if key not in variables:
                            variables[key] = str(value)
        
        # 4c. Generate session_X_output patterns based on parent order
        # This is for legacy templates that use session_1_output, session_2_output, etc.
        parent_list = list(parents.items())
        for idx, (conv_id, parent_output) in enumerate(parent_list, start=1):
            if isinstance(parent_output, dict):
                response = parent_output.get('response', '')
                variables[f'session_{idx}_output'] = response
        
        # 4d. Set parent_response to the LAST parent's response (most common use case)
        # Templates that use {parent_response} expect the immediate parent's output
        if parent_list:
            last_conv_id, last_parent_output = parent_list[-1]
            if isinstance(last_parent_output, dict):
                # For AI actors, use 'response' key; for scripts, stringify the whole output
                if 'response' in last_parent_output:
                    variables['parent_response'] = last_parent_output['response']
                else:
                    variables['parent_response'] = json.dumps(last_parent_output)
        
        # 5. Substitute variables in template
        self.logger.info(f"  Variables available: {list(variables.keys())}")
        self.logger.info(f"  orphan_skills in variables: {'orphan_skills' in variables}")
        
        prompt = prompt_template
        for var_name, var_value in variables.items():
            placeholder = '{' + var_name + '}'
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(var_value))
        
        has_literal = '{orphan_skills}' in prompt
        self.logger.info(f"  Final prompt has literal {{orphan_skills}}: {has_literal}")
        
        # 6. Validate no unresolved variables remain
        # Hard error on unresolved - silent failures caused phi4-mini hallucination disaster
        # See: docs/daily_notes/2025-12-10_template_vs_sql_memo.md
        unresolved = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', prompt)
        if unresolved:
            # Filter out false positives (JSON-like content, code examples)
            # Real template variables are simple identifiers, not nested paths
            real_unresolved = [v for v in unresolved if not any(c in v for c in ['.', '[', ']', ':'])]
            if real_unresolved:
                raise ValueError(
                    f"Unresolved template variables: {real_unresolved}. "
                    f"Posting: {posting_id}, Available variables: {list(variables.keys())}"
                )
        
        return prompt
    
    def check_parallel_group_complete(
        self, 
        workflow_run_id: int, 
        parallel_group: int,
        workflow_id: int
    ) -> tuple[bool, List[int]]:
        """
        Check if ALL interactions in a parallel group have completed.
        
        Used for wait_for_group synchronization. Returns whether all members
        have completed and the list of all their interaction IDs.
        
        Args:
            workflow_run_id: Current workflow run
            parallel_group: The parallel group number (e.g., 1 for WF1125 experts)
            workflow_id: Workflow ID to query workflow_conversations
            
        Returns:
            Tuple of (all_complete: bool, parent_interaction_ids: List[int])
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get all conversation_ids in this parallel group
        cursor.execute("""
            SELECT conversation_id 
            FROM workflow_conversations 
            WHERE workflow_id = %s AND parallel_group = %s AND enabled = true
        """, (workflow_id, parallel_group))
        
        parallel_conv_ids = [row['conversation_id'] for row in cursor.fetchall()]
        
        if not parallel_conv_ids:
            cursor.close()
            return (True, [])
        
        # Check status of interactions for these conversations in this run
        cursor.execute("""
            SELECT interaction_id, conversation_id, status
            FROM interactions
            WHERE workflow_run_id = %s 
              AND conversation_id = ANY(%s)
            ORDER BY conversation_id
        """, (workflow_run_id, parallel_conv_ids))
        
        interactions = cursor.fetchall()
        cursor.close()
        
        # Check if all parallel conversations have a completed interaction
        completed_ids = []
        completed_conv_ids = set()
        
        for i in interactions:
            if i['status'] == 'completed':  # Note: status is 'completed' not 'complete'
                completed_ids.append(i['interaction_id'])
                completed_conv_ids.add(i['conversation_id'])
        
        all_complete = completed_conv_ids == set(parallel_conv_ids)
        
        self.logger.info(
            f"Parallel group {parallel_group} check: "
            f"{len(completed_conv_ids)}/{len(parallel_conv_ids)} complete "
            f"({'ALL COMPLETE' if all_complete else 'waiting'})"
        )
        
        return (all_complete, completed_ids)
    
    def get_wait_for_group_info(
        self, 
        next_conv_id: int,
        workflow_id: int
    ) -> tuple[bool, Optional[int]]:
        """
        Check if a conversation has wait_for_group=true and get its parallel_group.
        
        Args:
            next_conv_id: Conversation ID to check
            workflow_id: Workflow ID
            
        Returns:
            Tuple of (wait_for_group: bool, parallel_group: Optional[int])
            The parallel_group returned is from the PREVIOUS step (the parallel group 
            we're waiting for to complete).
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get wait_for_group flag for this conversation
        cursor.execute("""
            SELECT wait_for_group, execution_order
            FROM workflow_conversations
            WHERE workflow_id = %s AND conversation_id = %s
        """, (workflow_id, next_conv_id))
        
        row = cursor.fetchone()
        if not row or not row['wait_for_group']:
            cursor.close()
            return (False, None)
        
        # Find the parallel_group of the step BEFORE this one
        current_order = row['execution_order']
        cursor.execute("""
            SELECT parallel_group
            FROM workflow_conversations
            WHERE workflow_id = %s 
              AND execution_order < %s 
              AND parallel_group IS NOT NULL
            ORDER BY execution_order DESC
            LIMIT 1
        """, (workflow_id, current_order))
        
        prev_row = cursor.fetchone()
        cursor.close()
        
        if prev_row:
            return (True, prev_row['parallel_group'])
        return (True, None)

    def get_next_conversations(
        self, 
        completed_interaction: Dict[str, Any]
    ) -> List[int]:
        """
        Get next conversation IDs based on branching rules.
        
        Queries instruction_steps table for branching rules and evaluates
        branch_condition against the completed interaction's output.
        
        Args:
            completed_interaction: Completed interaction dict
            
        Returns:
            List of next conversation IDs to create
        """
        conversation_id = completed_interaction['conversation_id']
        output = completed_interaction.get('output', {})
        
        # For AI actors: output.response contains the text
        # For script actors: entire output JSON needs to be checked
        # Convert to string to check for markers like [PASS], [FAIL], [RATE_LIMITED]
        if isinstance(output, dict) and 'response' in output:
            response = output.get('response', '')
        elif isinstance(output, dict):
            # Script actor with dict output - convert to string for pattern matching
            response = json.dumps(output)
        else:
            # Script actor returned list or other type - convert to string
            response = json.dumps(output)
        
        # Get output keys for debugging (handle non-dict outputs)
        output_keys = list(output.keys()) if isinstance(output, dict) else f"[{type(output).__name__}]"
        self.logger.debug(f"get_next_conversations for conv {conversation_id}: output_keys={output_keys}, response_preview='{response[:80]}...'")
        self.logger.info(f"get_next_conversations for conv {conversation_id}: response='{response[:100]}...'")
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query instruction steps for this conversation's instruction
        # instruction_steps uses instruction_id, so we need to join
        cursor.execute("""
            SELECT ist.instruction_step_id, ist.next_conversation_id, 
                   ist.branch_condition, ist.branch_priority
            FROM instruction_steps ist
            JOIN instructions i ON ist.instruction_id = i.instruction_id
            WHERE i.conversation_id = %s AND ist.enabled = TRUE
            ORDER BY ist.branch_priority DESC
        """, (conversation_id,))
        
        steps = cursor.fetchall()
        cursor.close()
        
        if not steps:
            self.logger.info(f"No instruction steps for conversation {conversation_id}")
            return []
        
        # PRIORITY-BASED BRANCHING PATTERN (Nov 26, 2025):
        # ------------------------------------------------
        # This implements a fundamental architectural pattern for workflow branching:
        # 
        # 1. SAME PRIORITY = PARALLEL EXECUTION
        #    All branches with the same priority that match will execute
        #    Example: Grade A (priority 1) + Grade B (priority 1) both execute
        #    Enables parallel processing paths (e.g., multiple graders)
        # 
        # 2. LOWER PRIORITY = STOP EVALUATION
        #    Once a match is found, stop when priority drops
        #    Example: [FAIL] at priority 10, * at priority 0
        #    If [FAIL] matches, the wildcard never executes (conditional branching)
        # 
        # 3. WITHIN PRIORITY = NO DUPLICATES
        #    Prevents same conversation from executing multiple times
        #    Even if multiple branches point to same conversation at same priority
        #    Only added to next_conversations once
        # 
        # This pattern eliminates duplicate conversation execution while enabling
        # parallel paths - critical for workflow correctness.
        
        next_conversations = []
        highest_priority_matched = None
        
        self.logger.debug(f"Evaluating {len(steps)} branch steps for conversation {conversation_id}")
        self.logger.info(f"Evaluating {len(steps)} branch steps for conversation {conversation_id}")
        
        for step in steps:
            condition = step['branch_condition']
            next_conv = step['next_conversation_id']
            priority = step['branch_priority']
            
            self.logger.debug(f"  Step: condition='{condition}', next_conv={next_conv}, priority={priority}")
            self.logger.info(f"  Step: condition='{condition}', next_conv={next_conv}, priority={priority}")
            
            if not next_conv:
                self.logger.debug(f"  Skipping - no next_conversation_id")
                self.logger.info(f"  Skipping - no next_conversation_id")
                continue  # Skip steps with no next_conversation_id
            
            # Evaluate condition
            matches = self._evaluate_branch_condition(response, condition)
            self.logger.debug(f"  Condition '{condition}' matches={matches}")
            self.logger.info(f"  Condition '{condition}' matches={matches}")
            
            if matches:
                # First match - establish the priority bar
                if highest_priority_matched is None:
                    highest_priority_matched = priority
                    self.logger.debug(f"  First match - set priority bar to {priority}")
                
                # Only add if same priority as highest match
                if priority == highest_priority_matched:
                    self.logger.debug(f"Branch condition '{condition}' MATCHED - adding next: {next_conv} (priority {priority})")
                    self.logger.info(f"Branch condition '{condition}' matched - next: {next_conv}")
                    next_conversations.append(next_conv)
                else:
                    # Lower priority - stop checking
                    self.logger.debug(f"  Priority {priority} < {highest_priority_matched} - stopping evaluation")
                    break
        
        self.logger.debug(f"Returning {len(next_conversations)} next conversations: {next_conversations}")
        self.logger.info(f"Returning {len(next_conversations)} next conversations: {next_conversations}")
        return next_conversations
    
    def _evaluate_branch_condition(self, response: str, condition: str) -> bool:
        """
        Evaluate branch condition against response.
        
        Conditions:
        - '*' (wildcard) - always match
        - 'default' - always match (fallback branch)
        - '[PASS]' - check if response contains [PASS]
        - '[FAIL]' - check if response contains [FAIL]
        - '[SKIP]' - check if response contains [SKIP]
        - '[RUN]' - check if response contains [RUN]
        - '[RATE_LIMITED]' - check if response contains [RATE_LIMITED]
        - 'contains:XXX' - check if response contains XXX
        
        Args:
            response: AI or script response text
            condition: Branch condition string
            
        Returns:
            True if condition matches
        """
        if not condition:
            return False
        
        condition = condition.strip()
        
        # Wildcard always matches
        if condition == '*':
            return True
        
        # Default always matches (fallback branch)
        if condition.lower() == 'default':
            return True
        
        # Contains pattern: "contains:SOME_TEXT"
        if condition.lower().startswith('contains:'):
            search_text = condition[9:]  # After "contains:"
            return search_text in response
        
        # Pattern matching
        if condition.startswith('[') and condition.endswith(']'):
            return condition in response
        
        # Fallback: substring match
        return condition in response
    
    def create_child_interactions(
        self,
        parent_interaction: Dict[str, Any]
    ) -> List[int]:
        """
        Create child interactions after parent completes.
        
        This is called by Wave Runner after an interaction completes successfully.
        
        Steps:
        1. Get next conversation IDs from instruction_steps (branching)
        2. For each next conversation:
           - Build prompt from template
           - Create pending interaction
           - Link to parent via input_interaction_ids
        
        Special case: If parent has posting_id=None but output contains posting_ids,
        create child interactions for EACH posting (fan-out pattern for batch fetch).
        
        Args:
            parent_interaction: Completed parent interaction dict
            
        Returns:
            List of created interaction IDs
        """
        parent_id = parent_interaction['interaction_id']
        posting_id = parent_interaction['posting_id']
        workflow_run_id = parent_interaction['workflow_run_id']
        
        # Check for fan-out case: parent has no posting_id but output has posting_ids
        # This happens after fetch creates multiple postings
        posting_ids_to_process = [posting_id] if posting_id else []
        
        if not posting_id:
            # Check if output contains posting_ids array
            # db_job_fetcher returns {"status": "success", "posting_ids": [...], ...}
            output = parent_interaction.get('output', {})
            if isinstance(output, dict):
                # First check direct access (db_job_fetcher format)
                output_posting_ids = output.get('posting_ids', [])
                # Fallback: check nested data structure
                if not output_posting_ids:
                    data = output.get('data', {})
                    if isinstance(data, dict):
                        output_posting_ids = data.get('posting_ids', [])
                
                if output_posting_ids:
                    posting_ids_to_process = output_posting_ids
                    self.logger.info(
                        f"Fan-out: Creating children for {len(output_posting_ids)} postings "
                        f"from parent {parent_id}"
                    )
        
        # Check for skill-based fan-out (WF3002 pattern)
        # unmatched_skills_fetcher returns {"skill_keys": [...], "skills": [...]}
        skill_items_to_process = []
        if not posting_ids_to_process or posting_ids_to_process == [None]:
            output = parent_interaction.get('output', {})
            if isinstance(output, dict) and output.get('skill_keys'):
                # Output from fetcher - multiple skills to fan out
                skills_list = output.get('skills', [])
                for skill in skills_list:
                    skill_items_to_process.append({
                        'raw_skill_name': skill.get('raw_skill_name'),
                        'skill_key': skill.get('skill_key'),
                        'count': skill.get('count', 0),
                        'example_posting_ids': skill.get('example_posting_ids', [])
                    })
                self.logger.info(
                    f"Fan-out: Creating children for {len(skill_items_to_process)} skills "
                    f"from parent {parent_id}"
                )
            else:
                # Check if parent has skill context in INPUT (classifier → saver pattern)
                parent_input = parent_interaction.get('input', {})
                if isinstance(parent_input, dict) and parent_input.get('raw_skill_name'):
                    # Single skill context - carry it forward
                    skill_items_to_process.append({
                        'raw_skill_name': parent_input.get('raw_skill_name'),
                        'skill_key': parent_input.get('skill_key'),
                        'count': parent_input.get('count', 0),
                        'example_posting_ids': parent_input.get('example_posting_ids', [])
                    })
                    self.logger.info(
                        f"Skill carry-forward: Passing skill context from parent {parent_id} "
                        f"({parent_input.get('raw_skill_name')})"
                    )
        
        # If no posting_ids, this is a global workflow - use [None] to create one child per next conversation
        if not posting_ids_to_process:
            posting_ids_to_process = [None]
            self.logger.info(f"Global workflow: Creating children with posting_id=None from parent {parent_id}")
        
        # Get next conversations based on branching
        next_conversations = self.get_next_conversations(parent_interaction)
        
        if not next_conversations:
            self.logger.info(f"No next conversations for interaction {parent_id}")
            return []
        
        # Get workflow_id from workflow_run for wait_for_group check
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT workflow_id FROM workflow_runs WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        wr_row = cursor.fetchone()
        workflow_id = wr_row['workflow_id'] if wr_row else None
        
        created_ids = []
        
        # Determine what we're iterating over: postings, skills, or global
        if skill_items_to_process:
            # Skill-based fan-out (WF3002 pattern)
            items_to_process = skill_items_to_process
            item_type = 'skill'
        else:
            # Posting-based fan-out or global
            items_to_process = posting_ids_to_process
            item_type = 'posting'
        
        # For each item (posting or skill) and each next conversation (branching)
        for current_item in items_to_process:
            # Determine posting_id based on item type
            if item_type == 'skill':
                current_posting_id = None
                skill_context = current_item  # Dict with raw_skill_name, count, etc.
            else:
                current_posting_id = current_item
                skill_context = None
            
            for next_conv_id in next_conversations:
                try:
                    # === WAIT_FOR_GROUP CHECK ===
                    # If next conversation has wait_for_group=true, we need to:
                    # 1. Check if ALL parallel group members have completed
                    # 2. If not, skip - the last completing member will create the child
                    # 3. If yes, use ALL parent IDs so template substitution works
                    if workflow_id:
                        wait_for_group, parallel_group = self.get_wait_for_group_info(
                            next_conv_id, workflow_id
                        )
                        if wait_for_group and parallel_group is not None:
                            all_complete, all_parent_ids = self.check_parallel_group_complete(
                                workflow_run_id, parallel_group, workflow_id
                            )
                            if not all_complete:
                                self.logger.info(
                                    f"wait_for_group: Skipping child creation for conv {next_conv_id} - "
                                    f"waiting for parallel_group {parallel_group} to complete"
                                )
                                continue
                            
                            # Check if child already exists (avoid duplicates in race conditions)
                            cursor.execute("""
                                SELECT interaction_id FROM interactions 
                                WHERE workflow_run_id = %s AND conversation_id = %s
                            """, (workflow_run_id, next_conv_id))
                            if cursor.fetchone():
                                self.logger.info(
                                    f"wait_for_group: Child for conv {next_conv_id} already exists - skipping"
                                )
                                continue
                            
                            # Use ALL parent IDs from the parallel group
                            parent_ids_override = all_parent_ids
                            self.logger.info(
                                f"wait_for_group: Creating child for conv {next_conv_id} "
                                f"with {len(all_parent_ids)} parent IDs: {all_parent_ids}"
                            )
                        else:
                            parent_ids_override = None
                    else:
                        parent_ids_override = None
                    
                    # Get conversation details and instruction_id
                    cursor.execute("""
                        SELECT c.conversation_id, c.conversation_name, 
                               c.actor_id, a.actor_type, a.actor_name,
                               i.instruction_id, i.instruction_name
                        FROM conversations c
                        JOIN actors a ON c.actor_id = a.actor_id
                        LEFT JOIN instructions i ON c.conversation_id = i.conversation_id 
                            AND i.step_number = 1
                        WHERE c.conversation_id = %s
                    """, (next_conv_id,))
                    
                    conv = cursor.fetchone()
                    if not conv:
                        self.logger.warning(f"Conversation {next_conv_id} not found")
                        continue
                    
                    # Build prompt from template
                    # Use parent_ids_override if wait_for_group provided ALL parent IDs
                    parent_ids = parent_ids_override if parent_ids_override else [parent_id]
                    prompt = self.build_prompt_from_template(
                        next_conv_id, 
                        current_posting_id, 
                        parent_ids,
                        workflow_run_id
                    )
                    
                    # Prepare input based on actor type
                    # AI actors: wrap in {"prompt": "..."}
                    # Script actors: parse the JSON directly (prompt contains JSON string)
                    if conv['actor_type'] == 'script':
                        # For scripts, prompt is actually JSON data - parse it
                        try:
                            input_data = json.loads(prompt)
                        except json.JSONDecodeError:
                            # If not valid JSON, wrap in a generic structure
                            input_data = {'data': prompt}
                        
                        # For script actors (like saver), also include parent's output
                        # This is critical for WF3002: saver needs the classification decision
                        parent_output = parent_interaction.get('output', {})
                        if parent_output:
                            # If parent is AI actor, extract the response
                            if 'response' in parent_output:
                                try:
                                    # Parse the LLM's JSON response
                                    decision = json.loads(parent_output['response'])
                                    input_data['decision'] = decision
                                except json.JSONDecodeError:
                                    # Not valid JSON - store as text
                                    input_data['parent_response'] = parent_output['response']
                            else:
                                # Script output - pass as-is
                                input_data['parent_output'] = parent_output
                        
                        # Add all ancestor outputs for multi-step workflows (e.g., WF3005)
                        # This allows saver to access classifier output even when grader is direct parent
                        all_ancestors = self._get_ancestor_outputs(parent_ids, workflow_run_id)
                        for conv_id, ancestor_output in all_ancestors.items():
                            key = f'conversation_{conv_id}_output'
                            if key not in input_data and isinstance(ancestor_output, dict):
                                if 'response' in ancestor_output:
                                    input_data[key] = ancestor_output['response']
                    else:
                        # AI actors expect prompt in input.prompt
                        input_data = {'prompt': prompt}
                    
                    # Add skill context if this is a skill-based workflow
                    if skill_context:
                        input_data['raw_skill_name'] = skill_context.get('raw_skill_name')
                        input_data['skill_key'] = skill_context.get('skill_key')
                        input_data['count'] = skill_context.get('count', 0)
                        input_data['example_posting_ids'] = skill_context.get('example_posting_ids', [])
                        
                        # For AI actors, also inject into the prompt template
                        if conv['actor_type'] == 'ai_model' and 'prompt' in input_data:
                            raw_name = str(skill_context.get('raw_skill_name', ''))
                            count_val = str(skill_context.get('count', 0))
                            examples = str(skill_context.get('example_posting_ids', []))
                            
                            old_prompt = input_data['prompt']
                            new_prompt = old_prompt.replace(
                                '{raw_skill_name}', raw_name
                            ).replace(
                                '{count}', count_val
                            ).replace(
                                '{example_posting_ids}', examples
                            )
                            input_data['prompt'] = new_prompt
                    
                    # Create interaction
                    # Get next execution order
                    cursor.execute("""
                        SELECT COALESCE(MAX(execution_order), 0) + 1 as next_order
                        FROM interactions
                        WHERE workflow_run_id = %s
                    """, (workflow_run_id,))
                    
                    next_order = cursor.fetchone()['next_order']
                    
                    # For wait_for_group: parent_interaction_id = first parent, 
                    #                     input_interaction_ids = ALL parents
                    primary_parent_id = parent_ids[0] if parent_ids else parent_id
                    
                    # Insert interaction (inherit run_id from parent)
                    parent_run_id = parent_interaction.get('run_id')
                    instruction_id = conv.get('instruction_id')  # May be None
                    cursor.execute("""
                        INSERT INTO interactions (
                            posting_id, workflow_run_id, conversation_id,
                            actor_id, actor_type, status, execution_order,
                            parent_interaction_id, input_interaction_ids, input, run_id,
                            instruction_id
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, 'pending', %s,
                            %s, %s, %s, %s,
                            %s
                        ) RETURNING interaction_id
                    """, (
                        current_posting_id, workflow_run_id, next_conv_id,
                        conv['actor_id'], conv['actor_type'], next_order,
                        primary_parent_id, parent_ids, json.dumps(input_data), parent_run_id,
                        instruction_id
                    ))
                    
                    new_id = cursor.fetchone()['interaction_id']
                    created_ids.append(new_id)
                    self.conn.commit()  # Commit each interaction
                    
                    item_desc = skill_context.get('raw_skill_name') if skill_context else current_posting_id
                    parent_desc = f"parents={parent_ids}" if len(parent_ids) > 1 else f"parent={parent_ids[0]}"
                    self.logger.info(
                        f"Created interaction {new_id} for conversation {next_conv_id} "
                        f"({conv['conversation_name']}) {item_type}={item_desc} {parent_desc}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"Error creating child for conversation {next_conv_id} "
                        f"posting {current_posting_id}: {e}"
                    )
                    continue
        
        cursor.close()
        self.conn.commit()
        
        return created_ids
