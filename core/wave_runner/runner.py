"""
Wave Runner - Main execution loop
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <100 lines

Updates:
- Nov 30: Added heartbeat mechanism for indestructible workflows
- Dec 4: Added failure classification for intelligent retry decisions
"""

import psycopg2
import time
import logging
import os
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .database import DatabaseHelper
from .audit import AuditLogger
from .executors import AIModelExecutor, ScriptExecutor, HumanExecutor
from .failure_types import classify_failure, should_retry, FailureType
from .script_sync import ScriptSyncManager
from .interaction_creator import InteractionCreator
from .trace_reporter import generate_trace_report
from .work_grouper import WorkGrouper
from .model_cache import ModelCache



class WaveRunner:
    """
    Wave Runner V2 - Event-driven workflow engine.
    
    Architecture:
    - Posting-centric: Each posting progresses independently
    - Interaction-based: Query interactions table for pending work
    - Self-healing: Restarts from exact failure point
    """
    
    def __init__(
        self, 
        db_conn, 
        runner_id: str = None,
        posting_id: Optional[int] = None,
        workflow_run_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        base_dir: Path = None,
        global_batch: bool = False,
        trigger_interaction_id: Optional[int] = None
    ):
        """
        Initialize Wave Runner.
        
        Args:
            db_conn: psycopg2 database connection
            runner_id: Unique identifier for this runner instance
            posting_id: Filter to specific posting (incompatible with global_batch)
            workflow_run_id: Filter to specific workflow run (incompatible with global_batch)
            workflow_id: Filter to specific workflow (works with global_batch!)
            base_dir: Base directory for logs
            global_batch: If True, process ALL pending interactions across workflows (TRUE WAVE BATCHING)
            trigger_interaction_id: Links all child interactions back to the workflow run interaction
        """
        self.conn = db_conn
        self.runner_id = runner_id or f"wave_runner_{int(time.time())}"
        self.global_batch = global_batch
        self.trigger_interaction_id = trigger_interaction_id
        self.workflow_id = workflow_id  # Works with global_batch - filters to one workflow
        # In global_batch mode, ignore posting_id and workflow_run_id filters (but NOT workflow_id)
        self.posting_id = None if global_batch else posting_id
        self.workflow_run_id = None if global_batch else workflow_run_id
        self.logger = logging.getLogger(__name__)
        
        # Trace collection for debugging
        self.trace_data = []
        self.trace_enabled = False
        
        # Initialize helpers
        self.db = DatabaseHelper(db_conn)
        self.audit = AuditLogger(db_conn, correlation_id=f"run_{self.runner_id}")
        
        # Initialize interaction creator for creating child interactions
        self.interaction_creator = InteractionCreator(db_conn, self.db, self.logger)
        
        # Initialize script sync manager
        base_dir = base_dir or Path.cwd()
        self.script_sync = ScriptSyncManager(db_conn, base_dir, self.logger)
        
        # Auto-sync script actors on startup
        drift_count = self.script_sync.sync_all_script_actors()
        if drift_count > 0:
            self.logger.warning(f"Auto-synced {drift_count} script actors on startup")
        
        # Initialize executors
        self.ai_executor = AIModelExecutor(db_helper=self.db, logger=self.logger)
        self.script_executor = ScriptExecutor()
        self.human_executor = HumanExecutor()
        
        # Initialize work grouper and model cache for batching
        self.work_grouper = WorkGrouper(db_conn, self.logger)
        self.model_cache = ModelCache(self.logger)
        
        # Heartbeat mechanism for indestructible workflows
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_interval = 30  # seconds
        self._pid = os.getpid()
        
        # Signal handling for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up handlers for graceful shutdown."""
        self._shutdown_requested = False
        
        def handle_signal(signum, frame):
            signal_name = 'SIGTERM' if signum == signal.SIGTERM else 'SIGINT'
            print(f"🛑 Received {signal_name}, shutting down gracefully...")
            self._shutdown_requested = True
            self._stop_heartbeat()
            # NOTE: No longer marking workflows as 'interrupted' on shutdown.
            # The daemon now auto-resumes on startup, so we just let running
            # workflows stay as 'running' and they'll be picked up next time.
            # This prevents the "462 interrupted workflows" problem.
            import sys
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    
    def _start_heartbeat(self, workflow_run_ids: List[int] = None):
        """Start the heartbeat thread."""
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(workflow_run_ids,),
            daemon=True
        )
        self._heartbeat_thread.start()
        self.logger.info(f"💓 Heartbeat started (every {self._heartbeat_interval}s, PID={self._pid})")
    
    def _stop_heartbeat(self):
        """Stop the heartbeat thread."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_stop.set()
            self._heartbeat_thread.join(timeout=5)
            self.logger.info("💔 Heartbeat stopped")
    
    def _heartbeat_loop(self, workflow_run_ids: List[int] = None):
        """Background thread that sends heartbeats."""
        while not self._heartbeat_stop.is_set():
            try:
                self._update_heartbeat(workflow_run_ids)
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            # Sleep in short intervals to allow quick shutdown
            for _ in range(self._heartbeat_interval):
                if self._heartbeat_stop.is_set():
                    break
                time.sleep(1)
    
    def _update_heartbeat(self, workflow_run_ids: List[int] = None):
        """Update heartbeat for all running workflows."""
        try:
            cursor = self.conn.cursor()
            
            if self.global_batch:
                # Update ALL running workflows
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET state = COALESCE(state, '{}'::jsonb) || 
                        jsonb_build_object(
                            'last_heartbeat', %s,
                            'runner_pid', %s,
                            'runner_id', %s
                        ),
                        updated_at = NOW()
                    WHERE status = 'running'
                    RETURNING workflow_run_id
                """, (datetime.now().isoformat(), self._pid, self.runner_id))
            elif workflow_run_ids:
                # Update specific workflows
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET state = COALESCE(state, '{}'::jsonb) || 
                        jsonb_build_object(
                            'last_heartbeat', %s,
                            'runner_pid', %s,
                            'runner_id', %s
                        ),
                        updated_at = NOW()
                    WHERE workflow_run_id = ANY(%s)
                    RETURNING workflow_run_id
                """, (datetime.now().isoformat(), self._pid, self.runner_id, workflow_run_ids))
            elif self.workflow_run_id:
                # Update single workflow
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET state = COALESCE(state, '{}'::jsonb) || 
                        jsonb_build_object(
                            'last_heartbeat', %s,
                            'runner_pid', %s,
                            'runner_id', %s
                        ),
                        updated_at = NOW()
                    WHERE workflow_run_id = %s
                """, (datetime.now().isoformat(), self._pid, self.runner_id, self.workflow_run_id))
            
            self.conn.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to update heartbeat: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
    
    def _mark_workflows_interrupted(self, signal_name: str):
        """Mark workflows as interrupted when receiving shutdown signal."""
        import sys
        try:
            # Rollback any pending transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass
            
            cursor = self.conn.cursor()
            
            if self.global_batch:
                # In global batch mode, mark all running workflows
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET status = 'interrupted',
                        state = COALESCE(state, '{}'::jsonb) || 
                            jsonb_build_object(
                                'interrupted_at', %s,
                                'signal', %s,
                                'runner_pid', %s
                            ),
                        updated_at = NOW()
                    WHERE status = 'running'
                    RETURNING workflow_run_id
                """, (datetime.now().isoformat(), signal_name, self._pid))
                
                interrupted = cursor.fetchall()
                if interrupted:
                    ids = [r['workflow_run_id'] if isinstance(r, dict) else r[0] for r in interrupted]
                    print(f"🛑 Marked {len(ids)} workflow(s) as interrupted: {ids}")
                    sys.stdout.flush()
                else:
                    print(f"⚠️ No running workflows found to interrupt")
                    sys.stdout.flush()
            elif self.workflow_run_id:
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET status = 'interrupted',
                        state = COALESCE(state, '{}'::jsonb) || 
                            jsonb_build_object(
                                'interrupted_at', %s,
                                'signal', %s,
                                'runner_pid', %s
                            ),
                        updated_at = NOW()
                    WHERE workflow_run_id = %s
                """, (datetime.now().isoformat(), signal_name, self._pid, self.workflow_run_id))
                print(f"🛑 Marked workflow {self.workflow_run_id} as interrupted")
                sys.stdout.flush()
            
            self.conn.commit()
            cursor.close()
        except SystemExit:
            raise  # Re-raise SystemExit, don't catch it
        except Exception as e:
            import traceback
            print(f"❌ Failed to mark workflows interrupted: {type(e).__name__}: {e}")
            traceback.print_exc()
            sys.stdout.flush()
    
    def _update_progress_state(self, stats: Dict[str, int]):
        """Update progress state after each batch."""
        import json
        try:
            cursor = self.conn.cursor()
            
            progress = {
                'interactions_completed': stats.get('interactions_completed', 0),
                'interactions_failed': stats.get('interactions_failed', 0),
                'iterations': stats.get('iterations', 0),
                'last_update': datetime.now().isoformat()
            }
            progress_json = json.dumps(progress)
            
            if self.global_batch:
                # Update ALL running workflows with progress
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET state = COALESCE(state, '{}'::jsonb) || 
                        jsonb_build_object('progress', %s::jsonb),
                        updated_at = NOW()
                    WHERE status = 'running'
                """, (progress_json,))
            elif self.workflow_run_id:
                cursor.execute("""
                    UPDATE workflow_runs 
                    SET state = COALESCE(state, '{}'::jsonb) || 
                        jsonb_build_object('progress', %s::jsonb),
                        updated_at = NOW()
                    WHERE workflow_run_id = %s
                """, (progress_json, self.workflow_run_id))
            
            self.conn.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to update progress state: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
    
    def run(
        self,
        max_iterations: int = 1000,
        max_interactions: Optional[int] = None,
        trace: bool = False,
        trace_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main execution loop.
        
        Pattern:
        1. Query pending interactions
        2. For each interaction:
           a. Claim atomically (FOR UPDATE SKIP LOCKED)
           b. Execute based on actor_type
           c. Update status (completed/failed)
           d. Log to audit
        3. Repeat until no pending work
        
        Args:
            max_iterations: Safety limit to prevent infinite loops
            max_interactions: Stop after N interactions executed (for testing)
            trace: Enable detailed execution trace collection
            trace_file: Path to write trace report (requires trace=True)
            
        Returns:
            Statistics: interactions_completed, interactions_failed, duration_ms
        """
        start_time = datetime.now()
        self.trace_enabled = trace
        self.trace_data = []
        
        stats = {
            'interactions_completed': 0,
            'interactions_failed': 0,
            'iterations': 0
        }
        
        # Start heartbeat for indestructible workflows
        self._start_heartbeat()
        
        try:
            for iteration in range(max_iterations):
                stats['iterations'] = iteration + 1
                
                # Check max_interactions limit
                if max_interactions and (stats['interactions_completed'] + stats['interactions_failed']) >= max_interactions:
                    print(f"⏹️  Stopped: Reached max_interactions limit ({max_interactions})")
                    break
                
                # Get batches grouped by model (WAVE BATCHING!)
                # In global_batch mode: pool ALL pending interactions across workflows
                # Use workflow_id to filter to specific workflow (e.g., 3003 only)
                # In normal mode: filter to specific posting or workflow_run
                batches = self.work_grouper.get_grouped_batches(
                    posting_id=self.posting_id,
                    workflow_run_id=self.workflow_run_id,
                    workflow_id=self.workflow_id
                )
                
                if not batches:
                    # No more work
                    break
                
                # Execute each batch (load model once, process all interactions)
                for batch in batches:
                    batch_results = self._execute_batch(batch, max_interactions, stats)
                    
                    stats['interactions_completed'] += batch_results['completed']
                    stats['interactions_failed'] += batch_results['failed']
                    
                    # Update progress state after each batch
                    self._update_progress_state(stats)
                    
                    # Check max_interactions limit after each batch
                    if max_interactions and (stats['interactions_completed'] + stats['interactions_failed']) >= max_interactions:
                        break
        finally:
            # Always stop heartbeat when done
            self._stop_heartbeat()
        
        stats['duration_ms'] = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Update workflow_runs status if we have a workflow_run_id
        if self.workflow_run_id:
            try:
                cursor = self.conn.cursor()
                
                # Check if all interactions are complete
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(*) FILTER (WHERE status IN ('completed', 'failed')) as done
                    FROM interactions
                    WHERE workflow_run_id = %s
                """, (self.workflow_run_id,))
                
                row = cursor.fetchone()
                total, done = row[0], row[1]
                
                # If all done, mark workflow complete
                if total > 0 and total == done:
                    cursor.execute("""
                        UPDATE workflow_runs
                        SET status = 'completed',
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE workflow_run_id = %s
                          AND status = 'running'
                    """, (self.workflow_run_id,))
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"✅ Workflow {self.workflow_run_id} marked complete ({done} interactions)")
                        stats['workflow_status'] = 'completed'
                    
                    self.conn.commit()
                
                cursor.close()
            except Exception as e:
                self.logger.error(f"Failed to update workflow status: {e}")
                # Don't fail the whole run just because status update failed
        
        # Generate trace report if requested
        if trace and trace_file:
            self._generate_trace_report(trace_file, stats, start_time)
            print(f"📄 Trace report: {trace_file}")
        
        return stats
    
    def _execute_batch(
        self,
        batch: Dict[str, Any],
        max_interactions: Optional[int] = None,
        stats: Dict[str, int] = None
    ) -> Dict[str, int]:
        """
        Execute a batch of interactions with the same model.
        
        Within a batch, interactions with the same parent are executed in parallel
        to enable parallel grading and other multi-path workflows.
        
        Args:
            batch: Batch dict from WorkGrouper with:
                - actor_id, actor_name, actor_type
                - model_used (for AI models)
                - interaction_ids (array)
                - batch_size
            max_interactions: Stop after N total interactions
            stats: Current stats (to check limits)
            
        Returns:
            {'completed': N, 'failed': M}
        """
        actor_type = batch['actor_type']
        model_name = batch.get('model_used')
        interaction_ids = batch['interaction_ids']
        
        self.logger.info(
            f"🌊 Executing batch: {batch['actor_name']} "
            f"({len(interaction_ids)} interactions)"
        )
        
        batch_results = {'completed': 0, 'failed': 0}
        
        # For AI models: Load model once for entire batch
        if actor_type == 'ai_model' and model_name:
            self.logger.info(f"📦 Loading model: {model_name}")
            # Model cache will handle this - no-op if already loaded
            self.model_cache.load_model(model_name)
        
        # Group interactions by parent for parallel execution
        parent_groups = defaultdict(list)
        for interaction_id in interaction_ids:
            interaction = self.db.get_interaction_by_id(interaction_id)
            if interaction:
                parent_id = interaction.get('parent_interaction_id')
                parent_groups[parent_id].append(interaction)
        
        # Execute each parent group (parallel within group, sequential across groups)
        for parent_id, interactions in parent_groups.items():
            # Check max_interactions limit
            if stats and max_interactions:
                total = stats['interactions_completed'] + stats['interactions_failed']
                if total >= max_interactions:
                    self.logger.info(f"⏹️  Batch stopped: Reached max_interactions limit")
                    break
            
            if len(interactions) == 1:
                # Single interaction - execute directly
                try:
                    success = self._execute_interaction(interactions[0])
                    if success:
                        batch_results['completed'] += 1
                    else:
                        batch_results['failed'] += 1
                except Exception as e:
                    self.logger.error(f"Execution error: {e}")
                    import traceback
                    traceback.print_exc()
                    batch_results['failed'] += 1
            else:
                # Multiple interactions with same parent - execute in PARALLEL
                # Cap max_workers to prevent overwhelming resources (especially LLMs)
                # For AI models, use 1 worker (ollama can't parallelize)
                # For scripts, allow more parallelism
                if actor_type == 'ai_model':
                    max_parallel = 1  # LLMs process one at a time
                else:
                    max_parallel = min(len(interactions), 4)  # Scripts can do some parallel
                
                self.logger.info(
                    f"⚡ Executing {len(interactions)} interactions "
                    f"(parent: {parent_id}, max_parallel: {max_parallel})"
                )
                
                with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                    # Submit all interactions in parallel
                    future_to_interaction = {
                        executor.submit(self._execute_interaction, interaction): interaction
                        for interaction in interactions
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_interaction):
                        try:
                            success = future.result()
                            if success:
                                batch_results['completed'] += 1
                            else:
                                batch_results['failed'] += 1
                        except Exception as e:
                            self.logger.error(f"Parallel execution error: {e}")
                            import traceback
                            traceback.print_exc()
                            batch_results['failed'] += 1
        
        # Log batch completion
        self.logger.info(
            f"✅ Batch complete: {batch_results['completed']} succeeded, "
            f"{batch_results['failed']} failed"
        )
        
        return batch_results
    
    def _check_should_skip(self, interaction: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if this interaction should be skipped because it was already done.
        
        Checks:
        1. If run_id is present, NEVER skip (Pipeline V2 explicit reprocessing)
        2. Is there a completed interaction for this posting_id + conversation_id?
        3. If staleness_days is set on the instruction, is the last run still fresh?
        
        Returns:
            (should_skip: bool, reason: str)
        """
        # Pipeline V2: If run_id is present, this is explicit reprocessing - never skip
        run_id = interaction.get('run_id')
        if run_id:
            return False, f"Pipeline V2 run_id={run_id} - explicit reprocessing, no skip"
        
        posting_id = interaction.get('posting_id')
        conversation_id = interaction.get('conversation_id')
        
        if not posting_id or not conversation_id:
            return False, "No posting_id or conversation_id"
        
        cursor = self.db.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check for existing completed interaction (only enabled and NOT invalidated ones count)
        cursor.execute("""
            SELECT 
                i.interaction_id,
                i.completed_at,
                EXTRACT(DAY FROM NOW() - i.completed_at)::int as days_ago,
                inst.staleness_days
            FROM interactions i
            LEFT JOIN instructions inst ON inst.conversation_id = i.conversation_id AND inst.enabled = true
            WHERE i.posting_id = %s
              AND i.conversation_id = %s
              AND i.status = 'completed'
              AND i.enabled = true
              AND i.invalidated = false
            ORDER BY i.completed_at DESC
            LIMIT 1
        """, (posting_id, conversation_id))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return False, "No previous completed interaction"
        
        days_ago = row['days_ago'] or 0
        staleness_days = row['staleness_days']
        
        # If staleness_days is NULL, never re-run
        if staleness_days is None:
            return True, f"Already completed {days_ago} days ago (no staleness limit)"
        
        # If within staleness window, skip
        if days_ago <= staleness_days:
            return True, f"Completed {days_ago} days ago (fresh, staleness={staleness_days} days)"
        
        # Stale - need to re-run
        return False, f"Stale: {days_ago} days ago > {staleness_days} day limit"
    
    def _execute_interaction(self, interaction: Dict[str, Any]) -> bool:
        """
        Execute a single interaction.
        
        Args:
            interaction: Interaction record from database
            
        Returns:
            True if successful, False if failed
        """
        interaction_id = interaction['interaction_id']
        start_time = time.time()
        
        # Check if we should skip (already done and not stale)
        should_skip, skip_reason = self._check_should_skip(interaction)
        if should_skip:
            # Mark as skipped (completed with skip output)
            # Note: This is before claim, so race condition is unlikely but we check anyway
            if self.db.update_interaction_success(interaction_id, {
                'status': '[SKIP]',
                'reason': skip_reason,
                'auto_skipped': True
            }):
                self.logger.info(f"Auto-skipped interaction {interaction_id}: {skip_reason}")
            return True
        
        # Claim interaction (atomic)
        if not self.db.claim_interaction(interaction_id, self.runner_id):
            return False  # Already claimed by another runner
        
        # Log: Started
        start_event_id = self.audit.log_event(
            interaction_id,
            'interaction_started',
            {
                'actor_id': interaction['actor_id'],
                'actor_name': interaction['actor_name'],
                'runner_id': self.runner_id
            }
        )
        
        try:
            # Execute based on actor type
            if interaction['actor_type'] == 'ai_model':
                output = self._execute_ai_model(interaction)
            elif interaction['actor_type'] == 'script':
                output = self._execute_script(interaction)
            elif interaction['actor_type'] == 'human':
                output = self._execute_human(interaction)
            else:
                raise ValueError(f"Unknown actor_type: {interaction['actor_type']}")
            
            # Update: Completed (with optimistic locking)
            # Returns False if interaction was reaped while we were processing
            if not self.db.update_interaction_success(interaction_id, output):
                self.logger.warning(
                    f"Interaction {interaction_id} was reaped while processing. "
                    f"Discarding result to prevent corruption."
                )
                return False  # Don't create children or log success
            
            # Update workflow state with semantic keys
            workflow_run_id = interaction.get('workflow_run_id')
            if workflow_run_id:
                try:
                    state_updates = self._extract_semantic_state(
                        interaction['conversation_id'],
                        output,
                        interaction
                    )
                    if state_updates:
                        self.db.update_workflow_state(workflow_run_id, state_updates)
                except Exception as e:
                    # Don't fail interaction if state update fails
                    self.logger.warning(f"Failed to update workflow state: {e}")
            
            # Log: Completed
            self.audit.log_event(
                interaction_id,
                'interaction_completed',
                {'output': output},
                causation_event_id=start_event_id
            )
            
            # Create child interactions based on branching rules
            # This is where workflow progression happens!
            child_ids = []
            try:
                # Refresh interaction data with output
                interaction['output'] = output
                child_ids = self.interaction_creator.create_child_interactions(interaction)
                
                if child_ids:
                    self.logger.info(
                        f"Created {len(child_ids)} child interaction(s) "
                        f"from parent {interaction_id}: {child_ids}"
                    )
            except Exception as e:
                # Don't fail parent if child creation fails
                self.logger.error(f"Error creating child interactions: {e}")
            
            # Collect trace data if enabled
            if self.trace_enabled:
                end_time = time.time()
                # Query database to get comprehensive trace context
                cursor = self.db.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Get stored input/output
                cursor.execute("""
                    SELECT input, output 
                    FROM interactions 
                    WHERE interaction_id = %s
                """, (interaction_id,))
                stored_data = cursor.fetchone()
                
                # Get full context: workflow, conversation, actor, instructions, steps
                cursor.execute("""
                    SELECT 
                        w.workflow_id, w.workflow_name, w.workflow_description,
                        c.conversation_id, c.conversation_name, c.conversation_description,
                        c.context_strategy, c.conversation_type,
                        a.actor_id, a.actor_name, a.actor_type,
                        a.script_file_path, a.execution_config->>'system_prompt' as system_prompt,
                        (a.execution_config->>'timeout')::int as actor_timeout,
                        i.instruction_id, i.prompt_template, i.step_description,
                        p.posting_id, p.job_title, p.location_city
                    FROM interactions int
                    JOIN conversations c ON int.conversation_id = c.conversation_id
                    JOIN actors a ON c.actor_id = a.actor_id
                    JOIN workflow_runs wr ON int.workflow_run_id = wr.workflow_run_id
                    JOIN workflows w ON wr.workflow_id = w.workflow_id
                    LEFT JOIN instructions i ON i.conversation_id = c.conversation_id
                    LEFT JOIN postings p ON int.posting_id = p.posting_id
                    WHERE int.interaction_id = %s
                    LIMIT 1
                """, (interaction_id,))
                context = cursor.fetchone()
                
                # Get instruction steps (branching logic)
                if context and context.get('instruction_id'):
                    cursor.execute("""
                        SELECT 
                            instruction_step_name,
                            branch_condition,
                            branch_description,
                            branch_priority,
                            next_instruction_id,
                            next_conversation_id
                        FROM instruction_steps
                        WHERE instruction_id = %s AND enabled = true
                        ORDER BY branch_priority DESC
                    """, (context['instruction_id'],))
                    steps = cursor.fetchall()
                else:
                    steps = []
                
                cursor.close()
                
                self.trace_data.append({
                    'interaction_id': interaction_id,
                    'conversation_id': interaction.get('conversation_id'),
                    'conversation_name': interaction.get('conversation_name', 'Unknown'),
                    'actor_name': interaction.get('actor_name', 'Unknown'),
                    'actor_type': interaction.get('actor_type', 'Unknown'),
                    'input': stored_data['input'] if stored_data else {},
                    'output': stored_data['output'] if stored_data else output,
                    'duration': end_time - start_time,
                    'status': 'completed',
                    'parent_interaction_ids': interaction.get('input_interaction_ids', []),
                    'child_interaction_ids': child_ids,
                    # Enriched context
                    'context': context if context else {},
                    'branching_steps': steps if steps else []
                })
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # Classify failure for intelligent retry decisions
            failure_type, is_retriable = classify_failure(e, error_msg)
            
            # Check if we should retry (based on type AND count)
            retry_count = interaction['retry_count']
            max_retries = interaction['max_retries']
            will_retry = is_retriable and retry_count < max_retries
            
            # Update: Failed (or retry) with classification
            self.db.update_interaction_failed(
                interaction_id, 
                error_msg,
                will_retry=will_retry,
                failure_type=failure_type.value
            )
            
            # Log: Failed with classification
            self.audit.log_event(
                interaction_id,
                'interaction_failed' if not will_retry else 'interaction_retried',
                {
                    'error': error_msg,
                    'failure_type': failure_type.value,
                    'is_retriable': is_retriable,
                    'retry_count': retry_count,
                    'will_retry': will_retry
                },
                causation_event_id=start_event_id
            )
            
            # Collect trace data for failed interaction
            if self.trace_enabled:
                end_time = time.time()
                self.trace_data.append({
                    'interaction_id': interaction_id,
                    'conversation_id': interaction.get('conversation_id'),
                    'conversation_name': interaction.get('conversation_name', 'Unknown'),
                    'actor_name': interaction.get('actor_name', 'Unknown'),
                    'actor_type': interaction.get('actor_type', 'Unknown'),
                    'input': interaction.get('input', {}),
                    'output': None,
                    'error': error_msg,
                    'failure_type': failure_type.value,
                    'is_retriable': is_retriable,
                    'duration': end_time - start_time,
                    'status': 'failed' if not will_retry else 'retrying',
                    'parent_interaction_ids': interaction.get('input_interaction_ids', []),
                    'child_interaction_ids': []
                })
            
            return False
    
    def _execute_ai_model(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI model actor."""
        # Get model name from actor (e.g., 'gemma3:1b', 'qwen2.5:7b')
        model_name = interaction.get('actor_name', 'qwen2.5-coder:7b')
        
        # Get system prompt from input if provided (handle NULL input)
        input_data = interaction.get('input') or {}
        system_prompt = input_data.get('system_prompt')
        
        # Get temperature and seed from execution_config (for determinism)
        execution_config = interaction.get('execution_config') or {}
        temperature = execution_config.get('temperature')
        seed = execution_config.get('seed')
        
        # Build conversation-aware prompt (queries database, NO templates!)
        # Falls back to input['prompt'] if conversation not mapped
        try:
            prompt = self.ai_executor._build_ai_prompt(interaction)
        except ValueError as e:
            # Conversation not mapped - use raw prompt from input
            self.logger.warning(f"No prompt builder for conversation {interaction.get('conversation_id')}: {e}")
            prompt = input_data.get('prompt', '')
        
        # Store actual substituted prompt for traceability (Arden's fix Nov 25)
        self.db.update_interaction_prompt(
            interaction['interaction_id'],
            prompt,
            system_prompt
        )
        
        return self.ai_executor.execute(model_name, prompt, system_prompt, temperature, seed)

    def _execute_script(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute script actor."""
        # Use script_file_path if available (Phase 2), otherwise script_code (Phase 1)
        script_file_path = interaction.get('script_file_path')
        script_code = interaction.get('script_code')
        
        if script_file_path:
            # File-based script (Phase 2)
            import os
            full_path = os.path.join(os.getcwd(), script_file_path)
            input_data = interaction.get('input') or {}  # Handle NULL input
            # Add workflow context to input
            input_data['interaction_id'] = interaction['interaction_id']
            input_data['posting_id'] = interaction['posting_id']
            input_data['workflow_run_id'] = interaction['workflow_run_id']
            input_data['run_id'] = interaction.get('run_id')  # Pipeline V2
            
            # Use actor-specific timeout if configured
            timeout = interaction.get('actor_timeout')
            output = self.script_executor.execute(full_path, input_data, timeout=timeout)
            return output
        elif script_code:
            # Inline script code (Phase 1)
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_code)
                script_path = f.name
            
            try:
                input_data = interaction.get('input', {})
                output = self.script_executor.execute(script_path, input_data)
                return output
            finally:
                os.unlink(script_path)
        else:
            raise ValueError(f"No script_file_path or script_code for actor {interaction['actor_id']}")
    
    def _execute_human(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute human actor (manual task)."""
        task = interaction.get('input', {}).get('task_description', 'Manual approval required')
        return self.human_executor.execute(task)
    
    def _generate_trace_report(self, trace_file: str, stats: Dict[str, Any], start_time: datetime):
        """Generate markdown trace report using trace_reporter module."""
        generate_trace_report(
            trace_data=self.trace_data,
            stats=stats,
            start_time=start_time,
            trace_file=trace_file,
            workflow_run_id=getattr(self, 'current_workflow_run_id', None),
            posting_id=getattr(self, 'current_posting_id', None)
        )
    
    def _extract_semantic_state(
        self,
        conversation_id: int,
        output: Dict[str, Any],
        interaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract semantic state updates from interaction output.
        
        Maps conversation outputs to semantic keys that templates can use.
        
        Args:
            conversation_id: Conversation that produced this output
            output: Interaction output (can be dict or list)
            interaction: Full interaction dict
            
        Returns:
            Dict of semantic state updates
        """
        updates = {}
        
        # Handle non-dict outputs (e.g., lists from script actors)
        if not isinstance(output, dict):
            return updates
        
        # Extract text response for AI actors
        response = output.get('response', '')
        
        # Map conversations to semantic state keys
        if conversation_id == 3335:  # Extract Summary
            updates['extract_summary'] = response
            updates['current_summary'] = response  # Also set as current
            
        elif conversation_id == 3338:  # Improve Summary
            updates['improved_summary'] = response
            updates['current_summary'] = response  # Override current
            
        elif conversation_id == 3350:  # Extract Skills
            updates['extracted_skills'] = response
            
        elif conversation_id == 9161:  # IHL Analyst
            updates['ihl_analyst_verdict'] = response
            
        elif conversation_id == 9162:  # IHL Skeptic
            updates['ihl_skeptic_verdict'] = response
        
        # For Job Fetcher, store the staging IDs
        elif conversation_id == 9144:  # Job Fetcher
            if 'staging_ids' in output.get('data', {}):
                updates['staging_ids'] = output['data']['staging_ids']
            if 'jobs_fetched' in output.get('data', {}):
                updates['jobs_fetched'] = output['data']['jobs_fetched']
        
        return updates
