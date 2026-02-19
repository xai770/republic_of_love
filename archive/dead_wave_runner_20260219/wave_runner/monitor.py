#!/usr/bin/env python3
"""
Workflow Monitoring Queries
===========================
Production monitoring for Wave Runner V2.

Queries:
- Workflow progress by posting
- Step completion rates
- Error rates and patterns
- Performance metrics
- Stale interaction detection

Author: xai & Arden
Date: 2025-11-23
"""

import psycopg2
from typing import Dict, Any, List, Optional
from psycopg2.extras import RealDictCursor


class WorkflowMonitor:
    """Monitor workflow execution health and progress"""
    
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn
    
    def get_workflow_summary(self, workflow_id: int = 3001) -> Dict[str, Any]:
        """
        Get high-level workflow progress summary.
        
        Args:
            workflow_id: Workflow to monitor
            
        Returns:
            Summary dict with counts and percentages
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT i.posting_id) as total_postings,
                COUNT(DISTINCT CASE WHEN i.status = 'completed' THEN i.posting_id END) as completed_postings,
                COUNT(*) as total_interactions,
                SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) as completed_interactions,
                SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) as failed_interactions,
                SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) as pending_interactions,
                SUM(CASE WHEN i.status = 'running' THEN 1 ELSE 0 END) as running_interactions,
                MIN(i.created_at) as first_interaction_at,
                MAX(i.updated_at) as last_update_at
            FROM interactions i
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE wr.workflow_id = %s
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
        """, (workflow_id,))
        
        result = cursor.fetchone()
        
        # Calculate percentages
        total_postings = result['total_postings'] or 1
        total_interactions = result['total_interactions'] or 1
        
        return {
            'postings': {
                'total': result['total_postings'],
                'completed': result['completed_postings'],
                'percent_complete': round(100 * result['completed_postings'] / total_postings, 2)
            },
            'interactions': {
                'total': result['total_interactions'],
                'completed': result['completed_interactions'],
                'failed': result['failed_interactions'],
                'pending': result['pending_interactions'],
                'running': result['running_interactions'],
                'percent_complete': round(100 * result['completed_interactions'] / total_interactions, 2)
            },
            'timeline': {
                'started': result['first_interaction_at'],
                'last_update': result['last_update_at']
            }
        }
    
    def get_step_completion_rates(self, workflow_id: int = 3001) -> List[Dict[str, Any]]:
        """
        Get completion rates by conversation/step.
        
        Args:
            workflow_id: Workflow to analyze
            
        Returns:
            List of step stats
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                i.conversation_id,
                COUNT(*) as total,
                SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN i.status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN i.status = 'running' THEN 1 ELSE 0 END) as running,
                ROUND(100.0 * SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as percent_complete,
                AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as avg_duration_seconds
            FROM interactions i
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE wr.workflow_id = %s
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
            GROUP BY i.conversation_id
            ORDER BY i.conversation_id
        """, (workflow_id,))
        
        return cursor.fetchall()
    
    def get_actor_performance(self, workflow_id: int = 3001) -> List[Dict[str, Any]]:
        """
        Get performance metrics by actor.
        
        Args:
            workflow_id: Workflow to analyze
            
        Returns:
            List of actor stats
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                a.actor_id,
                a.actor_name,
                a.actor_type,
                COUNT(*) as total_executions,
                SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN i.status = 'failed' THEN 1 ELSE 0 END) as failed,
                ROUND(100.0 * SUM(CASE WHEN i.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
                AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as avg_duration_seconds,
                MIN(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as min_duration_seconds,
                MAX(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as max_duration_seconds
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE wr.workflow_id = %s
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
            GROUP BY a.actor_id, a.actor_name, a.actor_type
            ORDER BY total_executions DESC
        """, (workflow_id,))
        
        return cursor.fetchall()
    
    def get_error_patterns(
        self, 
        workflow_id: int = 3001,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get common error patterns.
        
        Args:
            workflow_id: Workflow to analyze
            limit: Max errors to return
            
        Returns:
            List of error records
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                i.interaction_id,
                i.posting_id,
                i.conversation_id,
                a.actor_name,
                i.error_message,
                i.retry_count,
                i.updated_at
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE wr.workflow_id = %s
              AND i.status = 'failed'
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
            ORDER BY i.updated_at DESC
            LIMIT %s
        """, (workflow_id, limit))
        
        return cursor.fetchall()
    
    def get_stale_interactions(self, threshold_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Find interactions stuck in 'running' state.
        
        Args:
            threshold_minutes: How long before considered stale
            
        Returns:
            List of stale interaction records
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                i.interaction_id,
                i.posting_id,
                i.workflow_run_id,
                a.actor_name,
                i.started_at,
                EXTRACT(EPOCH FROM (NOW() - i.started_at)) / 60 as minutes_running
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            WHERE i.status = 'running'
              AND i.started_at < NOW() - INTERVAL '%s minutes'
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
            ORDER BY i.started_at
        """, (threshold_minutes,))
        
        return cursor.fetchall()
    
    def get_throughput_stats(
        self, 
        workflow_id: int = 3001,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get throughput metrics (interactions/hour).
        
        Args:
            workflow_id: Workflow to analyze
            hours: Time window
            
        Returns:
            Throughput stats
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_completed,
                COUNT(*) / NULLIF(EXTRACT(EPOCH FROM (MAX(i.completed_at) - MIN(i.started_at))) / 3600, 0) as interactions_per_hour,
                MIN(i.started_at) as window_start,
                MAX(i.completed_at) as window_end
            FROM interactions i
            JOIN workflow_runs wr ON i.workflow_run_id = wr.workflow_run_id
            WHERE wr.workflow_id = %s
              AND i.status = 'completed'
              AND i.started_at >= NOW() - INTERVAL '%s hours'
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
        """, (workflow_id, hours))
        
        result = cursor.fetchone()
        
        return {
            'total_completed': result['total_completed'],
            'interactions_per_hour': round(result['interactions_per_hour'] or 0, 2),
            'window_start': result['window_start'],
            'window_end': result['window_end']
        }
    
    def get_posting_status(self, posting_id: int) -> Dict[str, Any]:
        """
        Get detailed status for a specific posting.
        
        Args:
            posting_id: Posting to check
            
        Returns:
            Detailed status dict
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all interactions for this posting
        cursor.execute("""
            SELECT 
                i.interaction_id,
                i.conversation_id,
                i.execution_order,
                a.actor_name,
                i.status,
                i.error_message,
                i.started_at,
                i.completed_at,
                EXTRACT(EPOCH FROM (i.completed_at - i.started_at)) as duration_seconds
            FROM interactions i
            JOIN actors a ON i.actor_id = a.actor_id
            WHERE i.posting_id = %s
              AND i.enabled = TRUE
              AND i.invalidated = FALSE
            ORDER BY i.execution_order, i.interaction_id
        """, (posting_id,))
        
        interactions = cursor.fetchall()
        
        # Calculate stats
        total = len(interactions)
        completed = sum(1 for i in interactions if i['status'] == 'completed')
        failed = sum(1 for i in interactions if i['status'] == 'failed')
        pending = sum(1 for i in interactions if i['status'] == 'pending')
        running = sum(1 for i in interactions if i['status'] == 'running')
        
        return {
            'posting_id': posting_id,
            'total_steps': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'running': running,
            'percent_complete': round(100 * completed / total, 2) if total > 0 else 0,
            'interactions': interactions
        }


def print_dashboard(monitor: WorkflowMonitor, workflow_id: int = 3001):
    """
    Print a console dashboard of workflow status.
    
    Args:
        monitor: WorkflowMonitor instance
        workflow_id: Workflow to display
    """
    print("\n" + "="*60)
    print(f"WORKFLOW {workflow_id} DASHBOARD")
    print("="*60)
    
    # Overall summary
    summary = monitor.get_workflow_summary(workflow_id)
    print(f"\n📊 OVERALL PROGRESS")
    print(f"   Postings: {summary['postings']['completed']}/{summary['postings']['total']} ({summary['postings']['percent_complete']}%)")
    print(f"   Interactions: {summary['interactions']['completed']}/{summary['interactions']['total']} ({summary['interactions']['percent_complete']}%)")
    print(f"   Failed: {summary['interactions']['failed']}")
    print(f"   Pending: {summary['interactions']['pending']}")
    print(f"   Running: {summary['interactions']['running']}")
    
    # Step completion rates
    steps = monitor.get_step_completion_rates(workflow_id)
    print(f"\n📝 STEP COMPLETION RATES")
    for step in steps[:10]:  # First 10 steps
        print(f"   Step {step['conversation_id']}: {step['completed']}/{step['total']} ({step['percent_complete']}%) - avg {step['avg_duration_seconds']:.1f}s")
    
    # Actor performance
    actors = monitor.get_actor_performance(workflow_id)
    print(f"\n🎭 TOP ACTORS BY VOLUME")
    for actor in actors[:5]:  # Top 5
        print(f"   {actor['actor_name']}: {actor['successful']}/{actor['total_executions']} ({actor['success_rate']}%) - avg {actor['avg_duration_seconds']:.1f}s")
    
    # Stale interactions
    stale = monitor.get_stale_interactions(threshold_minutes=5)
    if stale:
        print(f"\n⚠️  STALE INTERACTIONS (>5 min)")
        for s in stale[:5]:
            print(f"   {s['interaction_id']}: {s['actor_name']} - running for {s['minutes_running']:.0f} min")
    
    # Errors
    errors = monitor.get_error_patterns(workflow_id, limit=5)
    if errors:
        print(f"\n❌ RECENT ERRORS")
        for err in errors:
            print(f"   {err['actor_name']}: {err['error_message'][:60]}...")
    
    print("\n" + "="*60)
