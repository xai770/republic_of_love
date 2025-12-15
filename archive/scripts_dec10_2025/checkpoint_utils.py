"""
Checkpoint Query Utilities
===========================

Standard utilities for querying workflow checkpoints to retrieve conversation outputs.

This module implements the CHECKPOINT QUERY PATTERN as documented in:
docs/CHECKPOINT_QUERY_PATTERN.md

Usage:
    from core.checkpoint_utils import get_conversation_output
    
    # Get a single conversation's output
    summary = get_conversation_output(posting_id, '3341')
    
    # Get multiple outputs
    title = get_conversation_output(posting_id, '3335')
    company = get_conversation_output(posting_id, '3336')

Author: Arden & xai
Date: 2025-11-17
"""

import json
import logging
from typing import Optional, Dict, Any

from core.database import get_connection, return_connection

logger = logging.getLogger(__name__)


def get_conversation_output(posting_id: int, conversation_id: str, 
                            allow_missing: bool = False) -> Optional[str]:
    """
    Get a conversation's output from the most recent checkpoint.
    
    This is the standard way to retrieve data from previous workflow steps.
    Replaces the unreliable template substitution pattern.
    
    Args:
        posting_id: The posting being processed
        conversation_id: The conversation ID whose output you want (e.g., '3341')
        allow_missing: If True, returns None instead of raising error when not found
    
    Returns:
        The output from that conversation as a string, or None if allow_missing=True
        and the output doesn't exist
        
    Raises:
        ValueError: If no checkpoint found with that conversation output 
                   (only when allow_missing=False)
    
    Example:
        # Get formatted summary from conversation 3341
        summary = get_conversation_output(posting_id, '3341')
        
        # Get multiple outputs
        requirements = get_conversation_output(posting_id, '3338')
        benefits = get_conversation_output(posting_id, '3339')
        
        # Optional output (fallback gracefully if not found)
        optional_data = get_conversation_output(posting_id, '3340', allow_missing=True)
        if optional_data:
            process(optional_data)
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        logger.debug(
            f"Querying checkpoint for posting {posting_id}, "
            f"conversation {conversation_id}"
        )
        
        # Query the checkpoint for this conversation's output
        cur.execute("""
            SELECT state_snapshot->'outputs'->%s as output
            FROM posting_state_checkpoints
            WHERE posting_id = %s
              AND state_snapshot->'outputs' ? %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (conversation_id, posting_id, conversation_id))
        
        result = cur.fetchone()
        
        if result and result[0]:
            output = result[0]
            
            # Handle JSONB string quoting
            # JSONB sometimes returns strings wrapped in quotes like: "\"actual text\""
            if isinstance(output, str) and output.startswith('"') and output.endswith('"'):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    # If json.loads fails, just use the string as-is
                    pass
            
            logger.debug(
                f"Retrieved {len(str(output))} characters for conversation {conversation_id}"
            )
            return output
        else:
            if allow_missing:
                logger.debug(
                    f"No output found for conversation {conversation_id} "
                    f"in checkpoints for posting {posting_id} (allow_missing=True)"
                )
                return None
            else:
                raise ValueError(
                    f"No output found for conversation {conversation_id} "
                    f"in checkpoints for posting {posting_id}. "
                    f"Either the conversation hasn't run yet, or it failed. "
                    f"Set allow_missing=True if this is expected."
                )
    
    finally:
        return_connection(conn)


def get_multiple_outputs(posting_id: int, conversation_ids: list[str], 
                         allow_missing: bool = False) -> Dict[str, Optional[str]]:
    """
    Get multiple conversation outputs in a single database query.
    
    More efficient than calling get_conversation_output() multiple times.
    
    Args:
        posting_id: The posting being processed
        conversation_ids: List of conversation IDs to retrieve
        allow_missing: If True, missing outputs are set to None instead of raising error
    
    Returns:
        Dictionary mapping conversation_id -> output string (or None if missing)
        
    Raises:
        ValueError: If any conversation output is missing and allow_missing=False
    
    Example:
        # Get all outputs for final processing
        outputs = get_multiple_outputs(
            posting_id, 
            ['3335', '3336', '3337', '3338', '3339', '3341']
        )
        
        title = outputs['3335']
        company = outputs['3336']
        summary = outputs['3341']
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        logger.debug(
            f"Querying checkpoint for posting {posting_id}, "
            f"conversations {conversation_ids}"
        )
        
        # Get the most recent checkpoint
        cur.execute("""
            SELECT state_snapshot->'outputs' as outputs
            FROM posting_state_checkpoints
            WHERE posting_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (posting_id,))
        
        result = cur.fetchone()
        
        if not result or not result[0]:
            if allow_missing:
                return {conv_id: None for conv_id in conversation_ids}
            else:
                raise ValueError(
                    f"No checkpoint found for posting {posting_id}"
                )
        
        outputs_dict = result[0]
        
        # Extract requested outputs
        results = {}
        for conv_id in conversation_ids:
            output = outputs_dict.get(conv_id)
            
            if output:
                # Handle JSONB string quoting
                if isinstance(output, str) and output.startswith('"') and output.endswith('"'):
                    try:
                        output = json.loads(output)
                    except json.JSONDecodeError:
                        pass
                results[conv_id] = output
            else:
                if allow_missing:
                    results[conv_id] = None
                else:
                    raise ValueError(
                        f"Conversation {conv_id} output not found in checkpoint "
                        f"for posting {posting_id}"
                    )
        
        logger.debug(
            f"Retrieved {len([v for v in results.values() if v])} of "
            f"{len(conversation_ids)} requested outputs"
        )
        
        return results
    
    finally:
        return_connection(conn)


def checkpoint_exists(posting_id: int, conversation_id: Optional[str] = None) -> bool:
    """
    Check if a checkpoint exists for a posting, optionally checking for specific conversation.
    
    Args:
        posting_id: The posting to check
        conversation_id: Optional conversation ID to check for specifically
    
    Returns:
        True if checkpoint exists (and has the conversation output if specified)
        
    Example:
        # Check if any checkpoint exists
        if checkpoint_exists(posting_id):
            process()
        
        # Check if specific conversation has run
        if checkpoint_exists(posting_id, '3341'):
            summary = get_conversation_output(posting_id, '3341')
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        if conversation_id:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 
                    FROM posting_state_checkpoints
                    WHERE posting_id = %s
                      AND state_snapshot->'outputs' ? %s
                )
            """, (posting_id, conversation_id))
        else:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 
                    FROM posting_state_checkpoints
                    WHERE posting_id = %s
                )
            """, (posting_id,))
        
        return cur.fetchone()[0]
    
    finally:
        return_connection(conn)


def get_all_outputs(posting_id: int) -> Dict[str, Any]:
    """
    Get all conversation outputs from the most recent checkpoint.
    
    Useful for debugging or when you need access to everything.
    
    Args:
        posting_id: The posting being processed
    
    Returns:
        Dictionary of all outputs: {conversation_id: output}
        
    Raises:
        ValueError: If no checkpoint exists for this posting
        
    Example:
        # Get everything
        all_outputs = get_all_outputs(posting_id)
        
        # See what's available
        print(f"Available conversations: {list(all_outputs.keys())}")
        
        # Use specific ones
        summary = all_outputs.get('3341', 'Not available')
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT state_snapshot->'outputs' as outputs
            FROM posting_state_checkpoints
            WHERE posting_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (posting_id,))
        
        result = cur.fetchone()
        
        if not result or not result['outputs']:
            raise ValueError(f"No checkpoint found for posting {posting_id}")
        
        outputs = result['outputs']
        
        # Clean up JSONB string quoting for all values
        cleaned = {}
        for key, value in outputs.items():
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            cleaned[key] = value
        
        return cleaned
    
    finally:
        return_connection(conn)
