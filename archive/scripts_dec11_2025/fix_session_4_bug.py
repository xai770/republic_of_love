#!/usr/bin/env python3
"""
Fix session_4_output template substitution bug.

The bug: session_e_qwen25_regrade interactions have literal {session_4_output} 
instead of the actual improved summary from session_d_qwen25_improve.

This script:
1. Finds all pending session_e_qwen25_regrade interactions with the bug
2. For each, looks up the corresponding session_d_qwen25_improve output
3. Updates the prompt with the actual improved summary
"""

import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def main():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cursor = conn.cursor()
    
    # Find buggy interactions
    cursor.execute("""
        SELECT i.interaction_id, i.posting_id, i.input
        FROM interactions i
        JOIN conversations c ON i.conversation_id = c.conversation_id
        WHERE c.conversation_name = 'session_e_qwen25_regrade'
        AND i.status = 'pending'
        AND i.input::text LIKE '%{session_4_output}%'
    """)
    
    buggy = cursor.fetchall()
    print(f"Found {len(buggy)} buggy interactions to fix")
    
    if not buggy:
        print("Nothing to fix!")
        conn.close()
        return
    
    fixed = 0
    failed = 0
    
    for interaction_id, posting_id, input_data in buggy:
        # Get session_d_qwen25_improve output for this posting
        cursor.execute("""
            SELECT i.output::json->>'response'
            FROM interactions i
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE c.conversation_name = 'session_d_qwen25_improve'
            AND i.posting_id = %s
            AND i.status = 'completed'
            ORDER BY i.interaction_id DESC
            LIMIT 1
        """, (posting_id,))
        
        result = cursor.fetchone()
        if not result or not result[0]:
            print(f"  ⚠️  No session_d output for posting {posting_id}, skipping interaction {interaction_id}")
            failed += 1
            continue
        
        improved_summary = result[0]
        
        # Update the prompt
        input_json = input_data if isinstance(input_data, dict) else json.loads(input_data)
        old_prompt = input_json.get('prompt', '')
        new_prompt = old_prompt.replace('{session_4_output}', improved_summary)
        
        if old_prompt == new_prompt:
            print(f"  ⚠️  No change for interaction {interaction_id}, skipping")
            failed += 1
            continue
        
        input_json['prompt'] = new_prompt
        
        cursor.execute("""
            UPDATE interactions
            SET input = %s::jsonb
            WHERE interaction_id = %s
        """, (json.dumps(input_json), interaction_id))
        
        fixed += 1
        if fixed % 20 == 0:
            print(f"  Fixed {fixed} interactions...")
    
    conn.commit()
    print(f"\n✅ Fixed {fixed} interactions, {failed} failed")
    conn.close()

if __name__ == '__main__':
    main()
