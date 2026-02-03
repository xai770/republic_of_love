#!/usr/bin/env python3
"""
Workflow Guard - Entry Point Enforcement for Long-Running Scripts

This module enforces two critical rules:
1. Scripts MUST be run via the wrapper (nohup enforcement)
2. Every workflow run IS an ticket (lineage tracking)

Usage:
    from core.workflow_guard import require_wrapper
    
    # At the TOP of any long-running script:
    ticket_id = require_wrapper(
        script_name="run_batch_cleanup.py",
        description="Batch cleanup - processes pending tickets"
    )
    
    # Pass ticket_id to child operations for lineage

Philosophy:
    The ONLY entry point to Turing is via tickets.
    A workflow run is Sandy (or another agent) asking Turing to do something.
    All child tickets trace back to this parent.

Author: Arden
Date: 2025-11-30
"""

import os
import sys
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# THE SECRET - Shared between wrapper and all guarded scripts
# ═══════════════════════════════════════════════════════════════
TURING_HANDSHAKE = "turing_says_use_nohup_635864"


def _verify_handshake() -> bool:
    """Check if the secret handshake is present."""
    return os.environ.get("TURING_HANDSHAKE", "") == TURING_HANDSHAKE


def _create_workflow_ticket(
    script_name: str,
    description: str,
    actor_name: str = "sandy"
) -> int:
    """
    Create an ticket record for this workflow run.
    
    Returns the ticket_id that child operations should reference.
    """
    from dotenv import load_dotenv
    import psycopg2
    import json
    
    load_dotenv()
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    
    try:
        with conn.cursor() as cur:
            # Get or create actor for the agent running this
            cur.execute("""
                SELECT actor_id FROM actors WHERE actor_name = %s
            """, (actor_name,))
            row = cur.fetchone()
            
            if row:
                actor_id = row[0]
            else:
                # Create actor if doesn't exist (shouldn't happen, but safe)
                cur.execute("""
                    INSERT INTO actors (actor_name, actor_type, url)
                    VALUES (%s, 'script', %s)
                    RETURNING actor_id
                """, (actor_name, f"agent://{actor_name}"))
                actor_id = cur.fetchone()[0]
            
            # Get the "workflow_runs" task_type (meta-task_type for runs)
            cur.execute("""
                SELECT task_type_id FROM task_types 
                WHERE task_type_name = 'workflow_runs'
            """)
            row = cur.fetchone()
            
            if row:
                task_type_id = row[0]
            else:
                # Create the meta-task_type - need an actor_id for it
                # Use the sandy actor we just found/created
                cur.execute("""
                    INSERT INTO task_types (task_type_name, actor_id)
                    VALUES ('workflow_runs', %s)
                    RETURNING task_type_id
                """, (actor_id,))
                task_type_id = cur.fetchone()[0]
            
            # Create the ticket for THIS workflow run
            input_data = json.dumps({
                "script": script_name,
                "description": description,
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(),
                "hostname": os.uname().nodename
            })
            
            cur.execute("""
                INSERT INTO tickets (
                    task_type_id,
                    actor_id,
                    actor_type,
                    status,
                    execution_order,
                    input,
                    started_at
                ) VALUES (
                    %s,
                    %s,
                    'script',
                    'running',
                    (SELECT COALESCE(MAX(execution_order), 0) + 1 
                     FROM tickets WHERE task_type_id = %s),
                    %s,
                    NOW()
                )
                RETURNING ticket_id
            """, (
                task_type_id,
                actor_id,
                task_type_id,
                input_data
            ))
            
            ticket_id = cur.fetchone()[0]
            conn.commit()
            
            return ticket_id
            
    finally:
        conn.close()


def _block_direct_invocation(script_name: str):
    """Print helpful error message and exit."""
    print("═" * 60)
    print("❌ DIRECT INVOCATION BLOCKED")
    print("═" * 60)
    print()
    print(f"Script: {script_name}")
    print()
    print("This script must be run via the wrapper to ensure")
    print("proper background execution with nohup.")
    print()
    print("✅ Correct usage:")
    print(f"   ./scripts/run_workflow.sh {script_name}")
    print()
    print("❌ Don't do this:")
    print(f"   python3 scripts/{script_name}")
    print()
    print("The wrapper ensures:")
    print("  • Process runs in background (won't block terminal)")
    print("  • Process survives if your session ends")
    print("  • Output is logged to a file")
    print("  • Run is recorded as an ticket in Turing")
    print("═" * 60)
    sys.exit(1)


def require_wrapper(
    script_name: str,
    description: str,
    actor_name: str = "sandy"
) -> int:
    """
    Enforce wrapper usage and create workflow ticket.
    
    Call this at the TOP of any long-running script.
    
    Args:
        script_name: Name of the script (for logging/error messages)
        description: What this workflow does (stored in ticket)
        actor_name: Who is running this (default: sandy)
    
    Returns:
        ticket_id: The ID of the workflow-run ticket.
                        Pass this to child operations as parent_ticket_id.
    
    Raises:
        SystemExit: If not called via proper wrapper
    
    Example:
        from core.workflow_guard import require_wrapper
        
        ticket_id = require_wrapper(
            script_name="run_batch_cleanup.py",
            description="Processing pending batch items"
        )
        
        # Now pass ticket_id to child work:
        runner = WaveRunner(parent_ticket_id=ticket_id, ...)
    """
    # First: check the handshake
    if not _verify_handshake():
        _block_direct_invocation(script_name)
    
    # Second: create the ticket record
    ticket_id = _create_workflow_ticket(
        script_name=script_name,
        description=description,
        actor_name=actor_name
    )
    
    print(f"📋 Workflow registered as ticket #{ticket_id}")
    
    return ticket_id


def complete_workflow_ticket(
    ticket_id: int,
    output: Optional[dict] = None,
    error: Optional[str] = None
):
    """
    Mark the workflow ticket as complete.
    
    Call this when the workflow finishes (success or failure).
    
    Args:
        ticket_id: The ID returned by require_wrapper()
        output: Final output/stats (optional)
        error: Error message if failed (optional)
    """
    from dotenv import load_dotenv
    import psycopg2
    
    load_dotenv()
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    
    try:
        with conn.cursor() as cur:
            import json
            status = 'failed' if error else 'completed'
            output_json = json.dumps(output) if output else None
            
            cur.execute("""
                UPDATE tickets
                SET status = %s,
                    output = %s,
                    error_message = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE ticket_id = %s
            """, (status, output_json, error, ticket_id))
            
            conn.commit()
            
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE: For scripts that want to bypass for debugging
# ═══════════════════════════════════════════════════════════════

def is_debug_mode() -> bool:
    """Check if running in debug mode (allows direct invocation)."""
    return os.environ.get("TURING_DEBUG", "").lower() in ("1", "true", "yes")


def require_wrapper_unless_debug(
    script_name: str,
    description: str,
    actor_name: str = "sandy"
) -> Optional[int]:
    """
    Like require_wrapper, but allows bypass with TURING_DEBUG=1.
    
    Returns None in debug mode (no ticket created).
    """
    if is_debug_mode():
        print("⚠️  DEBUG MODE - Wrapper check bypassed")
        print("⚠️  No ticket record created")
        return None
    
    return require_wrapper(script_name, description, actor_name)
