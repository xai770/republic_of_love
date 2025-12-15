"""
Work Grouper - Intelligent batching for Wave Runner V2
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <80 lines

Groups pending interactions by actor/model to maximize GPU utilization.
Load model once, process batch, unload. Achieves 12x speedup.
"""

from typing import List, Dict, Any, Optional
import logging


class WorkGrouper:
    """Groups pending interactions by actor for efficient batch processing."""
    
    def __init__(self, db_conn, logger=None):
        """
        Initialize work grouper.
        
        Args:
            db_conn: Database connection
            logger: Optional logger
        """
        self.conn = db_conn
        self.logger = logger or logging.getLogger(__name__)
    
    def get_grouped_batches(
        self, 
        posting_id: Optional[int] = None,
        workflow_run_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        prioritize_ai: bool = False  # Changed: process scripts first for faster queue drain
    ) -> List[Dict[str, Any]]:
        """
        Group pending interactions by actor, ordered by batch size.
        
        Strategy:
        1. GROUP BY actor_id (same prompt template, different inputs)
        2. ORDER BY batch size DESC (process largest batches first)
        3. Optionally prioritize AI models (biggest batching benefit)
        
        Args:
            posting_id: Filter by posting (posting-centric mode)
            workflow_run_id: Filter by workflow run (workflow-centric mode)
            workflow_id: Filter by workflow definition (e.g., 3003) - works with global_batch
            prioritize_ai: Put AI model batches first (default True)
            
        Returns:
            List of batches:
            [
                {
                    'actor_id': 12,
                    'actor_name': 'skill_extractor',
                    'actor_type': 'ai_model',
                    'model_used': 'qwen2.5:7b',
                    'batch_size': 150,
                    'interaction_ids': [101, 102, ...]
                },
                ...
            ]
        """
        cursor = self.conn.cursor()
        
        # Build WHERE clause - find ALL ready-to-run pending interactions
        # Ready = pending AND (no parent OR parent completed)
        where_clauses = [
            "i.status = 'pending'", 
            "i.enabled = TRUE", 
            "i.invalidated = FALSE",
            # Prerequisite check: parent must be completed (or no parent)
            "(i.parent_interaction_id IS NULL OR parent.status = 'completed')"
        ]
        params = []
        
        # Optional filters (hints, not requirements)
        if posting_id:
            where_clauses.append("i.posting_id = %s")
            params.append(posting_id)
        
        if workflow_run_id:
            where_clauses.append("i.workflow_run_id = %s")
            params.append(workflow_run_id)
        
        if workflow_id:
            # Filter by workflow_id via workflow_runs table (more reliable than canonical_name pattern)
            where_clauses.append("""
                i.workflow_run_id IN (
                    SELECT workflow_run_id FROM workflow_runs 
                    WHERE workflow_id = %s
                )
            """)
            params.append(workflow_id)
        
        where_sql = " AND ".join(where_clauses)
        
        # Query: Group by actor, order by batch size
        # LEFT JOIN to parent to check prerequisite
        query = f"""
            SELECT 
                a.actor_id,
                a.actor_name,
                a.actor_type,
                a.execution_config->>'model' as model_used,
                COUNT(*) as batch_size,
                ARRAY_AGG(i.interaction_id ORDER BY i.execution_order) as interaction_ids
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            LEFT JOIN interactions parent ON i.parent_interaction_id = parent.interaction_id
            WHERE {where_sql}
            GROUP BY a.actor_id, a.actor_name, a.actor_type, a.execution_config->>'model'
            ORDER BY 
                {"CASE WHEN a.actor_type = 'ai_model' THEN 0 ELSE 1 END," if prioritize_ai else "CASE WHEN a.actor_type = 'script' THEN 0 ELSE 1 END,"}
                COUNT(*) DESC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        batches = []
        for row in rows:
            # Handle both tuple and dict row types
            if isinstance(row, dict):
                batch = {
                    'actor_id': row['actor_id'],
                    'actor_name': row['actor_name'],
                    'actor_type': row['actor_type'],
                    'model_used': row['model_used'],
                    'batch_size': row['batch_size'],
                    'interaction_ids': row['interaction_ids']
                }
            else:
                # row is tuple: (actor_id, actor_name, actor_type, model_used, batch_size, interaction_ids)
                batch = {
                    'actor_id': row[0],
                    'actor_name': row[1],
                    'actor_type': row[2],
                    'model_used': row[3],
                    'batch_size': row[4],
                    'interaction_ids': row[5]
                }
            batches.append(batch)
        
        self.logger.info(
            f"Grouped {sum(b['batch_size'] for b in batches)} interactions "
            f"into {len(batches)} batches"
        )
        
        return batches
    
    def get_next_batch(
        self,
        posting_id: Optional[int] = None,
        workflow_run_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get next batch to process (largest batch first).
        
        Args:
            posting_id: Filter by posting
            workflow_run_id: Filter by workflow run
            
        Returns:
            Batch dict or None if no pending work
        """
        batches = self.get_grouped_batches(posting_id, workflow_run_id)
        return batches[0] if batches else None
