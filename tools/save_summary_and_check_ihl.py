#!/usr/bin/env python3
"""
Summary Saver + IHL Status Checker - Script Actor for Workflow 3001
===================================================================
DUAL PURPOSE:
1. Saves formatted summary to postings.extracted_summary
2. Checks if IHL score already exists

This enables conditional branching:
- If IHL exists → [HAS_IHL] → TERMINAL (skip IHL scoring)
- If IHL missing → [NO_IHL] → Continue to skills extraction + IHL scoring

Input (JSON via stdin from prompt_template):
    {
        "posting_id": 123,
        "summary": "**Role:** Data Scientist\\n**Company:** ACME Corp..."
    }

Output (JSON to stdout):
    {
        "posting_id": 123,
        "summary_saved": true,
        "has_ihl": true,
        "ihl_score": 5,
        "branch": "[HAS_IHL]"
    }

Author: Arden & xai
Date: 2025-11-12
"""

import sys
import json
import os

# Add parent directory to path (handle both file execution and -c execution)
if __name__ == '__main__':
    # When executed via python3 -c, use current working directory
    sys.path.insert(0, os.getcwd())

from core.database import get_connection


def save_summary_and_check_ihl(posting_id: int, summary: str) -> dict:
    """
    Save summary to database and check IHL status
    
    Args:
        posting_id: ID of posting
        summary: Formatted summary text
        
    Returns:
        dict with summary_saved, has_ihl, ihl_score, branch fields
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # GUARD: Check expansion ratio to detect hallucinations
        cur.execute("""
            SELECT LENGTH(job_description) as desc_len
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        desc_len = row['desc_len'] if row and row['desc_len'] else 0
        summary_len = len(summary) if summary else 0
        
        expansion_ratio = (summary_len / max(desc_len, 1)) * 100
        
        # REJECT if expansion ratio > 200% (likely hallucination)
        if expansion_ratio > 200:
            conn.close()
            return {
                'posting_id': posting_id,
                'summary_saved': False,
                'has_ihl': False,
                'ihl_score': None,
                'ihl_category': None,
                'branch': '[HALLUCINATION_REJECTED]',
                'error': f'Summary expansion ratio {expansion_ratio:.0f}% exceeds 200% limit',
                'expansion_ratio': expansion_ratio
            }
        
        # Step 1: Save summary to database
        cur.execute("""
            UPDATE postings 
            SET extracted_summary = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE posting_id = %s
        """, (summary, posting_id))
        
        summary_saved = cur.rowcount > 0
        
        # Step 2: Check if IHL score exists
        cur.execute("""
            SELECT ihl_score, ihl_category
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        result = cur.fetchone()
        conn.commit()
        conn.close()
        
        if not result:
            return {
                'posting_id': posting_id,
                'summary_saved': False,
                'has_ihl': False,
                'ihl_score': None,
                'ihl_category': None,
                'branch': '[NO_IHL]',
                'error': 'Posting not found'
            }
        
        has_ihl = result['ihl_score'] is not None
        
        return {
            'posting_id': posting_id,
            'summary_saved': summary_saved,
            'has_ihl': has_ihl,
            'ihl_score': result['ihl_score'],
            'ihl_category': result['ihl_category'],
            'branch': '[HAS_IHL]' if has_ihl else '[NO_IHL]'
        }
        
    except Exception as e:
        return {
            'posting_id': posting_id,
            'summary_saved': False,
            'has_ihl': False,
            'ihl_score': None,
            'ihl_category': None,
            'branch': '[NO_IHL]',  # Default to running full workflow on error
            'error': str(e)
        }


def main():
    """Main entry point - read from stdin, write to stdout"""
    try:
        # Read input from stdin (passed via prompt_template)
        input_text = sys.stdin.read().strip()
        
        # Parse key-value format: "posting_id: 123\nsummary: text..."
        lines = input_text.split('\n', 1)
        posting_id = None
        summary = None
        
        if len(lines) >= 1 and lines[0].startswith('posting_id:'):
            posting_id = int(lines[0].split(':', 1)[1].strip())
        
        if len(lines) >= 2 and lines[1].startswith('summary:'):
            summary = lines[1].split(':', 1)[1].strip()
        
        if not posting_id:
            result = {
                'error': 'Missing posting_id in input',
                'branch': '[NO_IHL]'
            }
        elif not summary:
            result = {
                'posting_id': posting_id,
                'error': 'Missing summary in input',
                'branch': '[NO_IHL]'
            }
        else:
            result = save_summary_and_check_ihl(posting_id, summary)
        
        # Write result to stdout
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'branch': '[NO_IHL]'  # Safe default - run full workflow if unsure
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
