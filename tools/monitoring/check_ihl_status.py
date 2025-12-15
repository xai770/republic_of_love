#!/usr/bin/env python3
"""
IHL Status Checker - Script Actor for Workflow 3001
====================================================
Checks if a posting already has an IHL score.
Returns branching instruction for workflow routing.

Input (JSON via stdin):
    {
        "posting_id": 123
    }

Output (JSON to stdout):
    {
        "posting_id": 123,
        "has_ihl": true,
        "ihl_score": 5,
        "branch": "[HAS_IHL]"
    }
    OR
    {
        "posting_id": 123,
        "has_ihl": false,
        "ihl_score": null,
        "branch": "[NO_IHL]"
    }

Author: Arden & xai
Date: 2025-11-12
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection


def check_ihl_status(posting_id: int) -> dict:
    """
    Check if posting has IHL score
    
    Args:
        posting_id: ID of posting to check
        
    Returns:
        dict with has_ihl, ihl_score, branch fields
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT ihl_score, ihl_verdict
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        result = cur.fetchone()
        conn.close()
        
        if not result:
            return {
                'posting_id': posting_id,
                'has_ihl': False,
                'ihl_score': None,
                'ihl_verdict': None,
                'branch': '[NO_IHL]',
                'error': 'Posting not found'
            }
        
        has_ihl = result['ihl_score'] is not None
        
        return {
            'posting_id': posting_id,
            'has_ihl': has_ihl,
            'ihl_score': result['ihl_score'],
            'ihl_verdict': result['ihl_verdict'],
            'branch': '[HAS_IHL]' if has_ihl else '[NO_IHL]'
        }
        
    except Exception as e:
        return {
            'posting_id': posting_id,
            'has_ihl': False,
            'ihl_score': None,
            'ihl_verdict': None,
            'branch': '[NO_IHL]',  # Default to running IHL on error
            'error': str(e)
        }


def main():
    """Main entry point - read from stdin, write to stdout"""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())
        posting_id = input_data.get('posting_id')
        
        if not posting_id:
            result = {
                'error': 'Missing posting_id in input',
                'branch': '[NO_IHL]'  # Safe default
            }
        else:
            result = check_ihl_status(posting_id)
        
        # Write result to stdout
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'branch': '[NO_IHL]'  # Safe default - run IHL if unsure
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
