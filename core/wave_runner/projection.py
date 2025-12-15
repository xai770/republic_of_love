#!/usr/bin/env python3
"""
Posting State Projection - Rebuild workflow state from interactions
===================================================================
Event sourcing pattern: Rebuild current state from immutable events.

Author: xai & Arden
Date: 2025-11-23
"""

import psycopg2
from typing import List, Optional, Dict, Any
from psycopg2.extras import RealDictCursor


class PostingProjection:
    """Rebuild posting workflow state from interactions"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def rebuild_full(self) -> Dict[str, int]:
        """
        Rebuild entire projection from scratch.
        WARNING: Slow for large datasets. Use rebuild_incremental() instead.
        
        Returns:
            Stats dict with counts
        """
        cursor = self.conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posting_state_projection (
                posting_id INTEGER PRIMARY KEY,
                workflow_run_id BIGINT,
                workflow_id INTEGER,
                total_steps INTEGER DEFAULT 0,
                completed_steps INTEGER DEFAULT 0,
                failed_steps INTEGER DEFAULT 0,
                pending_steps INTEGER DEFAULT 0,
                current_step_name TEXT,
                current_conversation_id INTEGER,
                workflow_status TEXT,
                started_at TIMESTAMP,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                latest_interaction_id BIGINT,
                latest_event_id BIGINT,
                state_snapshot JSONB,
                FOREIGN KEY (posting_id) REFERENCES postings(posting_id) ON DELETE CASCADE
            )
        """)
        
        # Truncate for full rebuild
        cursor.execute("TRUNCATE TABLE posting_state_projection")
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projection_workflow_run ON posting_state_projection(workflow_run_id);
            CREATE INDEX IF NOT EXISTS idx_projection_status ON posting_state_projection(workflow_status);
            CREATE INDEX IF NOT EXISTS idx_projection_updated ON posting_state_projection(updated_at);
        """)
        
        # Rebuild from interactions
        cursor.execute("""
            INSERT INTO posting_state_projection (
                posting_id, workflow_run_id, workflow_id,
                total_steps, completed_steps, failed_steps, pending_steps,
                workflow_status, started_at, updated_at, latest_interaction_id
            )
            SELECT 
                i.posting_id, i.workflow_run_id, wr.workflow_id,
                COUNT(*) as total_steps,
                SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) as completed_steps,
                SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) as failed_steps,
                SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) as pending_steps,
                CASE 
                    WHEN SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) > 0 THEN 'failed'
                    WHEN SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) > 0 THEN 'running'
                    WHEN COUNT(*) = SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) THEN 'completed'
                    ELSE 'running'
                END as workflow_status,
                MIN(i.created_at) as started_at,
                MAX(i.updated_at) as updated_at,
                MAX(i.interaction_id) as latest_interaction_id
            FROM interactions i
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE i.enabled = TRUE AND i.invalidated = FALSE
            GROUP BY i.posting_id, i.workflow_run_id, wr.workflow_id
        """)
        
        rows_inserted = cursor.rowcount
        self.conn.commit()
        
        return {'rows_inserted': rows_inserted, 'method': 'full_rebuild'}
    
    def rebuild_incremental(self, posting_ids: List[int]) -> Dict[str, int]:
        """Rebuild projection for specific postings only"""
        if not posting_ids:
            return {'rows_updated': 0, 'method': 'incremental'}
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM posting_state_projection WHERE posting_id = ANY(%s)", (posting_ids,))
        rows_deleted = cursor.rowcount
        
        cursor.execute("""
            INSERT INTO posting_state_projection (
                posting_id, workflow_run_id, workflow_id,
                total_steps, completed_steps, failed_steps, pending_steps,
                workflow_status, started_at, updated_at, latest_interaction_id
            )
            SELECT 
                i.posting_id, i.workflow_run_id, wr.workflow_id,
                COUNT(*) as total_steps,
                SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) as completed_steps,
                SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) as failed_steps,
                SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) as pending_steps,
                CASE 
                    WHEN SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) > 0 THEN 'failed'
                    WHEN SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) > 0 THEN 'running'
                    WHEN COUNT(*) = SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) THEN 'completed'
                    ELSE 'running'
                END as workflow_status,
                MIN(i.created_at) as started_at,
                MAX(i.updated_at) as updated_at,
                MAX(i.interaction_id) as latest_interaction_id
            FROM interactions i
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE i.enabled = TRUE AND i.invalidated = FALSE AND i.posting_id = ANY(%s)
            GROUP BY i.posting_id, i.workflow_run_id, wr.workflow_id
        """, (posting_ids,))
        
        rows_inserted = cursor.rowcount
        self.conn.commit()
        
        return {'rows_deleted': rows_deleted, 'rows_inserted': rows_inserted, 'method': 'incremental'}
    
    def get_workflow_progress(self, workflow_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow progress summary"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT * FROM posting_state_projection WHERE 1=1"
        params = []
        
        if workflow_id:
            query += " AND workflow_id = %s"
            params.append(workflow_id)
        if status:
            query += " AND workflow_status = %s"
            params.append(status)
        
        query += " ORDER BY updated_at DESC"
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def get_posting_state(self, posting_id: int) -> Optional[Dict[str, Any]]:
        """Get current workflow state for a specific posting"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM posting_state_projection WHERE posting_id = %s", (posting_id,))
        return cursor.fetchone()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall projection statistics"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT 
                workflow_status,
                COUNT(*) as count,
                SUM(completed_steps) as total_completed_steps,
                SUM(failed_steps) as total_failed_steps,
                SUM(pending_steps) as total_pending_steps
            FROM posting_state_projection
            GROUP BY workflow_status
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row['workflow_status']] = {
                'count': row['count'],
                'completed_steps': row['total_completed_steps'],
                'failed_steps': row['total_failed_steps'],
                'pending_steps': row['total_pending_steps']
            }
        return stats
