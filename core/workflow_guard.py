#!/usr/bin/env python3
"""
Workflow Guard - Entry Point Enforcement for Long-Running Scripts

This module enforces two critical rules:
1. Scripts MUST be run via the wrapper (nohup enforcement)
2. Every workflow run IS an interaction (lineage tracking)

Usage:
    from core.workflow_guard import require_wrapper
    
    # At the TOP of any long-running script:
    interaction_id = require_wrapper(
        script_name="run_batch_cleanup.py",
        description="Batch cleanup - processes pending interactions"
    )
    
    # Pass interaction_id to child operations for lineage

Philosophy:
    The ONLY entry point to Turing is via interactions.
    A workflow run is Sandy (or another agent) asking Turing to do something.
    All child interactions trace back to this parent.

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


def _create_workflow_interaction(
    script_name: str,
    description: str,
    actor_name: str = "sandy"
) -> int:
    """
    Create an interaction record for this workflow run.
    
    Returns the interaction_id that child operations should reference.
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
            
            # Get the "workflow_runs" conversation (meta-conversation for runs)
            cur.execute("""
                SELECT conversation_id FROM conversations 
                WHERE conversation_name = 'workflow_runs'
            """)
            row = cur.fetchone()
            
            if row:
                conversation_id = row[0]
            else:
                # Create the meta-conversation - need an actor_id for it
                # Use the sandy actor we just found/created
                cur.execute("""
                    INSERT INTO conversations (conversation_name, actor_id)
                    VALUES ('workflow_runs', %s)
                    RETURNING conversation_id
                """, (actor_id,))
                conversation_id = cur.fetchone()[0]
            
            # Create the interaction for THIS workflow run
            input_data = json.dumps({
                "script": script_name,
                "description": description,
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(),
                "hostname": os.uname().nodename
            })
            
            cur.execute("""
                INSERT INTO interactions (
                    conversation_id,
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
                     FROM interactions WHERE conversation_id = %s),
                    %s,
                    NOW()
                )
                RETURNING interaction_id
            """, (
                conversation_id,
                actor_id,
                conversation_id,
                input_data
            ))
            
            interaction_id = cur.fetchone()[0]
            conn.commit()
            
            return interaction_id
            
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
    print("  • Run is recorded as an interaction in Turing")
    print("═" * 60)
    sys.exit(1)


def require_wrapper(
    script_name: str,
    description: str,
    actor_name: str = "sandy"
) -> int:
    """
    Enforce wrapper usage and create workflow interaction.
    
    Call this at the TOP of any long-running script.
    
    Args:
        script_name: Name of the script (for logging/error messages)
        description: What this workflow does (stored in interaction)
        actor_name: Who is running this (default: sandy)
    
    Returns:
        interaction_id: The ID of the workflow-run interaction.
                        Pass this to child operations as parent_interaction_id.
    
    Raises:
        SystemExit: If not called via proper wrapper
    
    Example:
        from core.workflow_guard import require_wrapper
        
        interaction_id = require_wrapper(
            script_name="run_batch_cleanup.py",
            description="Processing pending batch items"
        )
        
        # Now pass interaction_id to child work:
        runner = WaveRunner(parent_interaction_id=interaction_id, ...)
    """
    # First: check the handshake
    if not _verify_handshake():
        _block_direct_invocation(script_name)
    
    # Second: create the interaction record
    interaction_id = _create_workflow_interaction(
        script_name=script_name,
        description=description,
        actor_name=actor_name
    )
    
    print(f"📋 Workflow registered as interaction #{interaction_id}")
    
    return interaction_id


def complete_workflow_interaction(
    interaction_id: int,
    output: Optional[dict] = None,
    error: Optional[str] = None
):
    """
    Mark the workflow interaction as complete.
    
    Call this when the workflow finishes (success or failure).
    
    Args:
        interaction_id: The ID returned by require_wrapper()
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
                UPDATE interactions
                SET status = %s,
                    output = %s,
                    error_message = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE interaction_id = %s
            """, (status, output_json, error, interaction_id))
            
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
    
    Returns None in debug mode (no interaction created).
    """
    if is_debug_mode():
        print("⚠️  DEBUG MODE - Wrapper check bypassed")
        print("⚠️  No interaction record created")
        return None
    
    return require_wrapper(script_name, description, actor_name)
