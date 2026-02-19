"""
Audit Logger - Immutable event log for compliance and time travel
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <50 lines
Reference: Appendix A (Audit Layer Architecture)
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional
from datetime import datetime


class AuditLogger:
    """Lightweight audit logger for interaction events."""
    
    def __init__(self, db_conn, correlation_id: str):
        """
        Initialize audit logger.
        
        Args:
            db_conn: psycopg2 connection object
            correlation_id: workflow_run_id or unique run identifier
        """
        self.conn = db_conn
        self.correlation_id = correlation_id
    
    def log_event(
        self,
        interaction_id: int,
        event_type: str,
        event_data: Dict[str, Any],
        causation_event_id: Optional[int] = None
    ) -> int:
        """
        Append immutable event to audit log.
        
        Event types:
        - interaction_created
        - interaction_started
        - interaction_completed
        - interaction_failed
        - interaction_invalidated
        - interaction_retried
        
        Args:
            interaction_id: Interaction this event belongs to
            event_type: Type of event (see above)
            event_data: Event payload (stored as JSONB)
            causation_event_id: Parent event that caused this event
            
        Returns:
            event_id of newly created event
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute("""
            INSERT INTO interaction_events (
                interaction_id,
                event_type,
                event_data,
                correlation_id,
                causation_event_id
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING event_id
        """, (
            interaction_id,
            event_type,
            psycopg2.extras.Json(event_data),
            self.correlation_id,
            causation_event_id
        ))
        
        event_id = cursor.fetchone()['event_id']
        self.conn.commit()
        
        return event_id
