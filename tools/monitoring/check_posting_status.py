#!/usr/bin/env python3
"""
Script Actor: Check Posting Status (Idempotency Helper)

Purpose: Check if specific work has already been done for a posting
Avoids re-running expensive operations on already-processed data

Input (JSON via stdin): {
    "posting_id": 858,
    "check_fields": ["extracted_summary", "taxonomy_skills"]  # fields to verify
}

Output (JSON to stdout): {
    "posting_id": 858,
    "extracted_summary": {"exists": true, "value_preview": "**Role:** Senior..."},
    "taxonomy_skills": {"exists": false},
    "all_complete": false,
    "branch": "[COMPLETE]" or "[INCOMPLETE]"
}
"""

import json
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.database import get_connection

def check_posting_fields(posting_id, check_fields):
    """Check if specified fields are populated for a posting"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Build query to check specific fields
        cursor.execute(f"""
            SELECT {', '.join(check_fields)}
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        result = cursor.fetchone()
        if not result:
            return {"error": f"Posting {posting_id} not found"}
        
        # Check each field
        field_status = {}
        all_complete = True
        
        for field in check_fields:
            value = result[field]
            exists = value is not None and value != ''
            
            field_status[field] = {
                "exists": exists,
                "value_preview": str(value)[:100] if exists else None
            }
            
            if not exists:
                all_complete = False
        
        return {
            "posting_id": posting_id,
            **field_status,
            "all_complete": all_complete,
            "branch": "[COMPLETE]" if all_complete else "[INCOMPLETE]"
        }
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.stdin.read())
        
        posting_id = input_data.get('posting_id')
        check_fields = input_data.get('check_fields', ['extracted_summary'])
        
        if not posting_id:
            raise ValueError("posting_id is required")
        
        result = check_posting_fields(posting_id, check_fields)
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error_output = {
            "status": "ERROR",
            "error": str(e),
            "branch": "[ERROR]"
        }
        print(json.dumps(error_output))
        sys.exit(1)
