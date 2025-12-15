#!/usr/bin/env python3
"""
Summary Saver - Simple Script Actor for Workflow 3001
=====================================================
Saves formatted summary to postings.extracted_summary WITH DATA LINEAGE

Input (JSON via stdin from prompt_template):
    {
        "posting_id": 123,
        "summary": "**Role:** Data Scientist\\n**Company:** ACME Corp..."
    }

Output (string to stdout - for branching):
    [SAVED]

Data Lineage:
    Queries posting_state_checkpoints to find which llm_interaction_id
    produced the summary, then stores it in summary_llm_interaction_id
    for full forensic traceability.

Author: Arden & xai
Date: 2025-11-18 (updated with lineage tracking)
"""

import sys
import json
import os

# Add parent directory to path
if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())

from core.database import get_connection, return_connection


def save_summary(posting_id: int, summary: str) -> str:
    """
    Save summary to database
    
    Args:
        posting_id: ID of posting
        summary: Formatted summary text
        
    Returns:
        Branch string: [SAVED] or [FAILED]
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Save summary to database (simple version without lineage tracking)
        cur.execute("""
            UPDATE postings 
            SET extracted_summary = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE posting_id = %s
        """, (summary, posting_id))
        
        success = cur.rowcount > 0
        conn.commit()
        return_connection(conn)
        
        if success:
            print(f"[SAVED] Posting {posting_id} → {len(summary)} chars", file=sys.stderr)
        
        return '[SAVED]' if success else '[FAILED]'
        
    except Exception as e:
        print(f"ERROR saving summary for posting {posting_id}: {e}", file=sys.stderr)
        return '[FAILED]'


def main():
    """Main entry point - read from stdin, write to stdout"""
    try:
        # Read input from stdin (passed via prompt_template)
        input_text = sys.stdin.read().strip()
        
        # Wave Runner V2 compatibility: Check if input is JSON wrapped
        try:
            input_json = json.loads(input_text)
            # Extract from {"data": "..."} wrapper if present
            if 'data' in input_json and isinstance(input_json['data'], str):
                input_text = input_json['data']
            elif 'posting_id' in input_json and 'summary' in input_json:
                # Direct JSON format
                posting_id = int(input_json['posting_id'])
                summary = input_json['summary']
                result = save_summary(posting_id, summary)
                # Output JSON for Wave Runner V2
                print(json.dumps({"status": result}))
                sys.exit(0)
        except json.JSONDecodeError:
            # Not JSON, continue with plain text parsing
            pass
        
        # Parse key-value format: "posting_id: 123\nsummary: text..."
        # Split on first newline only to handle multi-line summaries
        if '\n' in input_text:
            first_line, rest = input_text.split('\n', 1)
        else:
            first_line = input_text
            rest = ''
        
        posting_id = None
        summary = None
        
        if first_line.startswith('posting_id:'):
            posting_id = int(first_line.split(':', 1)[1].strip())
        
        if rest.startswith('summary:'):
            summary = rest.split(':', 1)[1].strip()
        
        if not posting_id or not summary:
            # Output JSON for Wave Runner V2
            print(json.dumps({"status": "[FAILED]", "error": "Missing posting_id or summary"}))
            sys.exit(1)
        
        result = save_summary(posting_id, summary)
        # Output JSON for Wave Runner V2
        print(json.dumps({"status": result}))
        sys.exit(0)
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        # Output JSON for Wave Runner V2
        print(json.dumps({"status": "[FAILED]", "error": str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
