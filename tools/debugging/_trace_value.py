#!/usr/bin/env python3
"""
Value Tracer - Trace how a posting's field was created

Shows complete execution path from raw input to final database value:
- Which conversations ran
- Which actors executed
- What prompts were sent
- What outputs were received
- When values were created/saved
- Total cost and duration

Usage:
    # Trace where extracted_summary came from
    python3 tools/_trace_value.py --posting-id 123 --field extracted_summary
    
    # Trace specific conversation's contribution
    python3 tools/_trace_value.py --posting-id 123 --conversation-id 3335
    
    # Trace most recent run for a posting
    python3 tools/_trace_value.py --posting-id 123
"""

import sys
import argparse
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


def get_posting_info(posting_id: int) -> Optional[Dict]:
    """Get posting basic info"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT 
            posting_id,
            job_title,
            LENGTH(job_description) as desc_length,
            LENGTH(extracted_summary) as summary_length,
            CASE WHEN skill_keywords IS NOT NULL THEN jsonb_array_length(skill_keywords) ELSE 0 END as skill_count,
            ihl_score
        FROM postings
        WHERE posting_id = %s
    ''', (posting_id,))
    
    result = cursor.fetchone()
    return_connection(conn)
    return dict(result) if result else None


def get_execution_path(posting_id: int, conversation_id: Optional[int] = None) -> List[Dict]:
    """Get complete execution path for a posting with LEFT JOINs for safety"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Use LEFT JOINs to handle missing data gracefully
    query = '''
        SELECT 
            psc.workflow_run_id,
            psc.conversation_id,
            COALESCE(c.conversation_name, 'Unknown Conversation') as conversation_name,
            COALESCE(c.canonical_name, 'unknown') as canonical_name,
            COALESCE(wc.execution_order, -1) as execution_order,
            COALESCE(a.actor_name, 'Unknown Actor') as actor_name,
            COALESCE(a.actor_type, 'unknown') as actor_type,
            COALESCE(a.execution_type, 'unknown') as execution_type,
            COALESCE(a.execution_path, '') as execution_path,
            psc.created_at,
            psc.state_snapshot
        FROM posting_state_checkpoints psc
        LEFT JOIN conversations c ON psc.conversation_id = c.conversation_id
        LEFT JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
        LEFT JOIN actors a ON c.actor_id = a.actor_id
        WHERE psc.posting_id = %s
    '''
    
    params = [posting_id]
    
    if conversation_id:
        query += ' AND psc.conversation_id = %s'
        params.append(conversation_id)
    
    query += ' ORDER BY psc.created_at'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    return_connection(conn)
    
    return [dict(r) for r in results]


def get_llm_interactions(posting_id: int, workflow_run_id: int, conversation_id: Optional[int] = None) -> List[Dict]:
    """Get LLM interaction details with LEFT JOINs for safety"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Use LEFT JOINs to handle missing relationships
    query = '''
        SELECT 
            li.interaction_id,
            li.conversation_run_id,
            li.actor_id,
            COALESCE(a.actor_name, 'Unknown Actor') as actor_name,
            COALESCE(c.conversation_name, 'Unknown Conversation') as conversation_name,
            COALESCE(wc.execution_order, -1) as execution_order,
            li.prompt_sent,
            li.response_received,
            li.latency_ms,
            li.tokens_input,
            li.tokens_output,
            li.cost_usd,
            li.status,
            li.started_at
        FROM llm_interactions li
        LEFT JOIN conversation_runs cr ON li.conversation_run_id = cr.conversation_run_id
        LEFT JOIN conversations c ON cr.conversation_id = c.conversation_id
        LEFT JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
        LEFT JOIN actors a ON li.actor_id = a.actor_id
        WHERE li.workflow_run_id = %s
    '''
    
    params = [workflow_run_id]
    
    # Note: We're filtering by workflow_run_id which already scopes to this posting
    # No need to add additional posting filter since workflow_run_id is unique per posting
    
    if conversation_id:
        query += ' AND cr.conversation_id = %s'
        params.append(conversation_id)
    
    query += ' ORDER BY li.started_at'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    return_connection(conn)
    
    return [dict(r) for r in results]


def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration"""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        mins = int(ms / 60000)
        secs = (ms % 60000) / 1000
        return f"{mins}m {secs:.0f}s"


def truncate(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return "(empty)"
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def display_trace(posting_id: int, field: Optional[str] = None, conversation_id: Optional[int] = None):
    """Display complete trace for a posting's value creation"""
    
    # Get posting info
    posting = get_posting_info(posting_id)
    if not posting:
        print(f"ERROR: Posting {posting_id} not found")
        return
    
    # Header
    print(f"\n{'='*100}")
    if field:
        print(f"Tracing: postings.{field} for posting_id = {posting_id}")
    elif conversation_id:
        print(f"Tracing: Conversation {conversation_id} for posting_id = {posting_id}")
    else:
        print(f"Tracing: Complete execution path for posting_id = {posting_id}")
    print(f"{'='*100}\n")
    
    # Posting info
    print(f"Job Title: {posting.get('job_title', 'N/A')}")
    print(f"Description: {posting['desc_length']} chars")
    print(f"Summary: {posting['summary_length']} chars" if posting['summary_length'] else "Summary: NOT YET CREATED")
    print(f"Skills: {posting['skill_count']} extracted")
    print(f"IHL Score: {posting['ihl_score']}" if posting['ihl_score'] else "IHL Score: NOT YET SCORED")
    
    # Get execution path
    path = get_execution_path(posting_id, conversation_id)
    
    if not path:
        print(f"\nNo execution path found for posting {posting_id}")
        return
    
    workflow_run_id = path[0]['workflow_run_id']
    
    # Get LLM interactions
    interactions = get_llm_interactions(posting_id, workflow_run_id, conversation_id)
    
    # Build interaction lookup
    interaction_map = {}
    for i in interactions:
        key = (i['conversation_name'], i['execution_order'])
        interaction_map[key] = i
    
    # Display execution path
    print(f"\n{'='*100}")
    print(f"Execution Path (Workflow Run {workflow_run_id}):")
    print(f"{'='*100}\n")
    
    total_duration = 0
    total_cost = 0
    
    for idx, step in enumerate(path, 1):
        order = step['execution_order']
        name = step['conversation_name']
        actor = step['actor_name']
        actor_type = step['actor_type']
        created = step['created_at']
        
        # Check if this step has LLM interaction
        interaction = interaction_map.get((name, order))
        
        print(f"{'┌' if idx == 1 else '├'}─ Step {order}: {name}")
        print(f"{'│' if idx < len(path) else ' '}  Actor: {actor} ({actor_type})")
        
        if interaction:
            duration_ms = interaction.get('latency_ms', 0) or 0
            total_duration += duration_ms
            
            cost = interaction.get('cost_usd', 0) or 0
            total_cost += cost
            
            tokens_in = interaction.get('tokens_input', 0)
            tokens_out = interaction.get('tokens_output', 0)
            
            prompt = truncate(interaction.get('prompt_sent', ''), 80)
            response = truncate(interaction.get('response_received', ''), 80)
            
            print(f"{'│' if idx < len(path) else ' '}  Conversation Run: {interaction['conversation_run_id']}")
            print(f"{'│' if idx < len(path) else ' '}  LLM Interaction: {interaction['interaction_id']}")
            print(f"{'│' if idx < len(path) else ' '}  Prompt: {prompt}")
            print(f"{'│' if idx < len(path) else ' '}  Output: {response}")
            print(f"{'│' if idx < len(path) else ' '}  Tokens: {tokens_in} in, {tokens_out} out")
            print(f"{'│' if idx < len(path) else ' '}  Duration: {format_duration(duration_ms)}")
            if cost > 0:
                print(f"{'│' if idx < len(path) else ' '}  Cost: ${cost:.4f}")
            print(f"{'│' if idx < len(path) else ' '}  Status: {interaction['status']}")
        
        print(f"{'│' if idx < len(path) else ' '}  Completed: {created.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'│' if idx < len(path) else ' '}")
    
    # Summary
    print(f"{'='*100}")
    print(f"Summary:")
    print(f"{'='*100}\n")
    print(f"  Total Steps: {len(path)}")
    print(f"  LLM Calls: {len(interactions)}")
    if total_duration > 0:
        print(f"  Total Duration: {format_duration(total_duration)}")
    if total_cost > 0:
        print(f"  Total Cost: ${total_cost:.4f}")
    
    if field:
        # Show final value
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SELECT {field} FROM postings WHERE posting_id = %s", (posting_id,))
        result = cursor.fetchone()
        return_connection(conn)
        
        if result and result[field]:
            value = result[field]
            if isinstance(value, str):
                print(f"\nFinal Value in postings.{field}:")
                print(f"  Length: {len(value)} chars")
                print(f"  Preview: {truncate(value, 200)}")
            else:
                print(f"\nFinal Value in postings.{field}:")
                print(f"  {value}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description='Trace value creation for posting fields')
    parser.add_argument('--posting-id', type=int, required=True, help='Posting ID to trace')
    parser.add_argument('--field', type=str, help='Field name to trace (e.g., extracted_summary)')
    parser.add_argument('--conversation-id', type=int, help='Specific conversation to trace')
    
    args = parser.parse_args()
    
    display_trace(args.posting_id, args.field, args.conversation_id)


if __name__ == '__main__':
    main()
