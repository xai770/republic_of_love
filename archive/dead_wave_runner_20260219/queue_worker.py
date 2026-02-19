#!/usr/bin/env python3
"""
Queue Worker - Pipeline V2
==========================

Claims postings from the queue table, creates runs, and triggers workflows.

This worker bridges the new queue/runs architecture with the existing wave_runner.

Usage:
    python core/queue_worker.py --batch-size 10 --workflow-id 3001
    
    Options:
        --batch-size N      Number of postings to claim per cycle (default: 10)
        --workflow-id ID    Which workflow to trigger (default: 3001)
        --once              Process one batch and exit (vs continuous loop)
        --dry-run           Show what would be processed without doing it

Architecture:
    1. Claims pending postings from queue (FOR UPDATE SKIP LOCKED)
    2. Creates run record for each posting
    3. Creates seed interaction with run_id set
    4. wave_runner picks up and executes as normal
    5. complete_run step marks run complete and deletes from queue
"""

import sys
import argparse
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

sys.path.insert(0, '/home/xai/Documents/ty_wave')

import psycopg2
import psycopg2.extras


class QueueWorker:
    """Process postings from the queue table."""
    
    def __init__(self, batch_size: int = 10, workflow_id: int = 3001, dry_run: bool = False):
        self.batch_size = batch_size
        self.workflow_id = workflow_id
        self.dry_run = dry_run
        self.conn = None
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger('queue_worker')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)
        
        return logger
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(
            dbname="turing",
            user="base_admin",
            password=os.getenv('DB_PASSWORD', ''),
            host="localhost"
        )
        self.logger.info("Connected to database")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Disconnected from database")
    
    def claim_batch(self) -> List[Dict[str, Any]]:
        """
        Claim a batch of pending postings from the queue.
        
        Uses FOR UPDATE SKIP LOCKED to prevent race conditions with other workers.
        
        Returns:
            List of queue entries claimed
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Atomic claim: select and update in one transaction
        cursor.execute("""
            WITH claimed AS (
                SELECT queue_id, posting_id, start_step, reason, priority, model_override
                FROM queue
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE queue q
            SET status = 'processing',
                processing_started_at = NOW()
            FROM claimed c
            WHERE q.queue_id = c.queue_id
            RETURNING q.queue_id, q.posting_id, q.start_step, q.reason, q.priority, q.model_override
        """, (self.batch_size,))
        
        claimed = cursor.fetchall()
        self.conn.commit()
        
        self.logger.info(f"Claimed {len(claimed)} postings from queue")
        return claimed
    
    def create_run(self, posting_id: int, reason: str, start_step: str, model_override: Optional[dict] = None) -> int:
        """
        Create a run record for a posting.
        
        Args:
            posting_id: Posting to process
            reason: Why we're processing (from queue entry)
            start_step: Which step to start from
            model_override: Optional model config override
            
        Returns:
            run_id
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO runs (posting_id, reason, triggered_by, start_step, model_config, started_at)
            VALUES (%s, %s, 'queue_worker', %s, %s, NOW())
            RETURNING run_id
        """, (posting_id, reason, start_step, psycopg2.extras.Json(model_override) if model_override else None))
        
        run_id = cursor.fetchone()[0]
        self.conn.commit()
        
        return run_id
    
    def update_queue_with_run_id(self, queue_id: int, run_id: int):
        """Link queue entry to its run."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE queue SET run_id = %s WHERE queue_id = %s
        """, (run_id, queue_id))
        self.conn.commit()
    
    def get_seed_conversation(self, start_step: str) -> Optional[int]:
        """
        Get the conversation_id to start from based on start_step.
        
        For now, maps step names to conversation IDs.
        TODO: Make this more dynamic via workflow_steps table.
        
        Args:
            start_step: Which step to start from
            
        Returns:
            conversation_id for the first step
        """
        # Mapping of start_step to conversation_id for WF3001
        step_to_conversation = {
            'fetch_jobs': 9144,           # Fetch Jobs from Deutsche Bank API
            'validate_description': 9193,  # Validate Job Description
            'extract_summary': 3335,       # session_a_extract_summary
            'extract_skills': 9121,        # Hybrid Job Skills Extraction
            'skills_extraction': 9121,     # Hybrid Job Skills Extraction (alias)
            'ihl_analyst': 9161,           # IHL Analyst - Find Red Flags (alias)
            'score_ihl': 9161,             # IHL Analyst - Find Red Flags
        }
        
        return step_to_conversation.get(start_step, 3335)  # Default to extract_summary
    
    def create_seed_interaction(self, posting_id: int, run_id: int, conversation_id: int, workflow_run_id: int) -> int:
        """
        Create the seed interaction that starts the workflow for this posting.
        
        This interaction will have run_id set, and all child interactions will inherit it.
        
        Args:
            posting_id: Posting to process
            run_id: Run to associate with
            conversation_id: Which conversation to start with
            workflow_run_id: Workflow run to attach to
            
        Returns:
            interaction_id
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get actor_id for the conversation
        cursor.execute("""
            SELECT actor_id FROM conversations WHERE conversation_id = %s
        """, (conversation_id,))
        conv = cursor.fetchone()
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        actor_id = conv['actor_id']
        
        # Get actor_type
        cursor.execute("""
            SELECT actor_type FROM actors WHERE actor_id = %s
        """, (actor_id,))
        actor = cursor.fetchone()
        actor_type = actor['actor_type'] if actor else 'ai_model'
        
        # Get next execution order
        cursor.execute("""
            SELECT COALESCE(MAX(execution_order), 0) + 1 as next_order
            FROM interactions
            WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        next_order = cursor.fetchone()['next_order']
        
        # Create seed interaction with run_id
        cursor.execute("""
            INSERT INTO interactions (
                posting_id, workflow_run_id, conversation_id,
                actor_id, actor_type, status, execution_order, run_id
            ) VALUES (
                %s, %s, %s,
                %s, %s, 'pending', %s, %s
            ) RETURNING interaction_id
        """, (
            posting_id, workflow_run_id, conversation_id,
            actor_id, actor_type, next_order, run_id
        ))
        
        interaction_id = cursor.fetchone()['interaction_id']
        self.conn.commit()
        
        return interaction_id
    
    def get_or_create_workflow_run(self) -> int:
        """
        Get or create a workflow_run for batch processing.
        
        For V2, we could use one workflow_run per queue batch,
        or reuse an existing running one.
        
        Returns:
            workflow_run_id
        """
        cursor = self.conn.cursor()
        
        # Create a new workflow run for this batch
        cursor.execute("""
            INSERT INTO workflow_runs (workflow_id, status, started_at)
            VALUES (%s, 'running', NOW())
            RETURNING workflow_run_id
        """, (self.workflow_id,))
        
        workflow_run_id = cursor.fetchone()[0]
        self.conn.commit()
        
        self.logger.info(f"Created workflow_run {workflow_run_id} for batch")
        return workflow_run_id
    
    def process_batch(self) -> int:
        """
        Process one batch of postings from the queue.
        
        Steps:
        1. Claim batch from queue
        2. Create runs for each posting
        3. Create seed interactions with run_id
        4. Let wave_runner pick them up
        
        Returns:
            Number of postings processed
        """
        # 1. Claim batch
        claimed = self.claim_batch()
        if not claimed:
            self.logger.info("No pending postings in queue")
            return 0
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would process {len(claimed)} postings:")
            for job in claimed:
                self.logger.info(f"  - posting_id={job['posting_id']}, reason={job['reason']}, start_step={job['start_step']}")
            # Release the claims in dry run mode
            cursor = self.conn.cursor()
            for job in claimed:
                cursor.execute("""
                    UPDATE queue SET status = 'pending', processing_started_at = NULL
                    WHERE queue_id = %s
                """, (job['queue_id'],))
            self.conn.commit()
            return 0
        
        # 2. Get or create workflow run for this batch
        workflow_run_id = self.get_or_create_workflow_run()
        
        # 3. Process each claimed posting
        created_interactions = []
        for job in claimed:
            try:
                posting_id = job['posting_id']
                reason = job['reason'] or 'queued'
                start_step = job['start_step'] or 'extract_summary'
                model_override = job['model_override']
                
                # Create run
                run_id = self.create_run(posting_id, reason, start_step, model_override)
                self.logger.info(f"Created run {run_id} for posting {posting_id}")
                
                # Link queue entry to run
                self.update_queue_with_run_id(job['queue_id'], run_id)
                
                # Get seed conversation for start_step
                seed_conversation_id = self.get_seed_conversation(start_step)
                
                # Create seed interaction
                interaction_id = self.create_seed_interaction(
                    posting_id, run_id, seed_conversation_id, workflow_run_id
                )
                created_interactions.append(interaction_id)
                
                self.logger.info(
                    f"Created seed interaction {interaction_id} for posting {posting_id} "
                    f"(run={run_id}, conversation={seed_conversation_id})"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to process queue_id={job['queue_id']}: {e}")
                # Mark as failed
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE queue SET status = 'failed', error_message = %s
                    WHERE queue_id = %s
                """, (str(e), job['queue_id']))
                self.conn.commit()
        
        self.logger.info(
            f"Created {len(created_interactions)} seed interactions in workflow_run {workflow_run_id}"
        )
        return len(created_interactions)
    
    def run_once(self):
        """Process one batch and exit."""
        self.connect()
        try:
            processed = self.process_batch()
            self.logger.info(f"Processed {processed} postings")
        finally:
            self.close()
    
    def run_loop(self, sleep_seconds: int = 10):
        """
        Continuous processing loop.
        
        Processes batches until queue is empty, then sleeps.
        
        Args:
            sleep_seconds: How long to sleep when queue is empty
        """
        import time
        
        self.connect()
        try:
            while True:
                try:
                    processed = self.process_batch()
                    
                    if processed == 0:
                        self.logger.info(f"Queue empty, sleeping {sleep_seconds}s...")
                        time.sleep(sleep_seconds)
                    else:
                        # Keep going while there's work
                        pass
                        
                except KeyboardInterrupt:
                    self.logger.info("Interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in processing loop: {e}")
                    time.sleep(sleep_seconds)
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description='Queue Worker - Pipeline V2')
    parser.add_argument('--batch-size', type=int, default=10, help='Postings per batch')
    parser.add_argument('--workflow-id', type=int, default=3001, help='Workflow to trigger')
    parser.add_argument('--once', action='store_true', help='Process one batch and exit')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
    parser.add_argument('--sleep', type=int, default=10, help='Seconds to sleep when empty')
    
    args = parser.parse_args()
    
    worker = QueueWorker(
        batch_size=args.batch_size,
        workflow_id=args.workflow_id,
        dry_run=args.dry_run
    )
    
    if args.once:
        worker.run_once()
    else:
        worker.run_loop(sleep_seconds=args.sleep)


if __name__ == '__main__':
    main()
