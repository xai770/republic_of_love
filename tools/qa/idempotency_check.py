#!/usr/bin/env python3
"""
Universal Idempotency Check Actor

Purpose: Check if work has already been done for a posting
Prevents re-running expensive operations on already-processed data

Input (JSON via stdin): {
    "posting_id": 858,
    "check_field": "3335",               # Conversation ID to check (e.g., '3335' for summary)
    "check_type": "not_null"             # not_null | min_length
    "min_length": 10                     # Optional: for min_length check
}

Output (JSON to stdout): {
    "posting_id": 858,
    "field": "3335",
    "exists": true,
    "value_length": 1234,
    "should_skip": true,
    "branch": "[SKIP]" or "[RUN]"
}

Examples:
    # Check if summary exists (conversation_id 3335)
    {"posting_id": 858, "check_field": "3335", "check_type": "not_null"}
    
    # Check if summary is at least 50 chars
    {"posting_id": 858, "check_field": "3335", "check_type": "min_length", "min_length": 50}

IMPORTANT: This queries posting_state_projection.outputs (event-sourced source of truth),
NOT postings table columns. See EVENT_SOURCING_PRACTICES.md for why.
"""

import json
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.database import get_connection

def check_field_exists(posting_id, check_field, check_type='not_null', min_length=None):
    """
    Check if a field is populated for a posting by querying the event-sourced projection.
    
    Args:
        posting_id: Posting ID to check
        check_field: Conversation ID to check in outputs (e.g., '3335' for summary)
        check_type: Type of check ('not_null', 'min_length')
        min_length: Minimum length for min_length check
    
    Returns:
        dict with status and branch decision
    
    IMPORTANT: This queries posting_state_projection.outputs (event-sourced source of truth),
    NOT postings table columns (legacy data that may be stale).
    See: EVENT_SOURCING_PRACTICES.md, IDEMPOTENCY_BUG_POSTMORTEM.md
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Query event-sourced projection (SOURCE OF TRUTH)
        # check_field should be conversation_id (e.g., '3335')
        cursor.execute("""
            SELECT outputs->%s as output_value
            FROM posting_state_projection
            WHERE posting_id = %s
        """, (check_field, posting_id))
        
        result = cursor.fetchone()
        if not result:
            return {
                "posting_id": posting_id,
                "error": f"Posting {posting_id} not found in projection",
                "should_skip": False,
                "branch": "[RUN]"
            }
        
        # Output is stored as JSON text in JSONB column
        field_value = result['output_value']  # Will be None if conversation_id not in outputs
        
        # Evaluate based on check_type
        exists = field_value is not None and field_value != ''
        should_skip = False
        reason = ""
        
        if check_type == 'not_null':
            should_skip = exists
            reason = "Field is populated" if exists else "Field is NULL/empty"
        
        elif check_type == 'min_length':
            if not exists:
                should_skip = False
                reason = "Field is NULL/empty"
            else:
                field_length = len(str(field_value))
                min_len = min_length or 1
                should_skip = field_length >= min_len
                reason = f"Length {field_length} >= {min_len}" if should_skip else f"Length {field_length} < {min_len}"
        
        else:
            return {
                "posting_id": posting_id,
                "error": f"Unknown check_type: {check_type}",
                "should_skip": False,
                "branch": "[RUN]"
            }
        
        return {
            "posting_id": posting_id,
            "field": check_field,
            "check_type": check_type,
            "exists": exists,
            "value_length": len(str(field_value)) if exists else 0,
            "should_skip": should_skip,
            "reason": reason,
            "branch": "[SKIP]" if should_skip else "[RUN]"
        }
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        # Read input
        input_data = json.loads(sys.stdin.read())
        
        posting_id = input_data.get('posting_id')
        check_field = input_data.get('check_field')
        check_type = input_data.get('check_type', 'not_null')
        min_length = input_data.get('min_length')
        
        if not posting_id:
            raise ValueError("posting_id is required")
        if not check_field:
            raise ValueError("check_field is required")
        
        # Check field
        result = check_field_exists(posting_id, check_field, check_type, min_length)
        
        # Output ONLY the branch string for workflow branching
        print(result['branch'])
        sys.exit(0)
        
    except Exception as e:
        error_output = {
            "error": str(e),
            "should_skip": False,
            "branch": "[RUN]"  # On error, proceed with work (safer than skipping)
        }
        # Output ONLY the branch string
        print(error_output['branch'])
        sys.exit(1)
