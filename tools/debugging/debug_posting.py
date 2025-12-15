#!/usr/bin/env python3
"""
Debug Posting
=============

Single command to explain posting workflow execution with full trace.

Usage:
    # Debug specific posting
    python3 tools/debug_posting.py --posting 64777
    
    # Show full interaction logs
    python3 tools/debug_posting.py --posting 64777 --verbose
    
    # Export full trace to file
    python3 tools/debug_posting.py --posting 64777 --export debug_64777.json

Output:
    - Posting metadata (job title, company, location)
    - Workflow execution path
    - Each conversation with status, timing, output preview
    - Error details if failed
    - Actionable next steps

Author: Arden
Date: 2025-11-13
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


def get_posting_info(posting_id: int, conn) -> Optional[Dict[str, Any]]:
    """Get posting metadata"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            posting_id,
            job_title,
            location_city,
            location_country,
            external_url,
            extracted_summary,
            skill_keywords,
            ihl_score,
            ihl_category,
            posting_status,
            LENGTH(job_description) as job_desc_length
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if not result:
        return None
    
    return dict(result)


def get_workflow_runs(posting_id: int, conn) -> List[Dict[str, Any]]:
    """Get all workflow runs for this posting"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            wr.workflow_run_id,
            wr.workflow_id,
            w.workflow_name,
            w.environment,
            wr.started_at,
            wr.completed_at,
            wr.status,
            wr.error_details as error_message
        FROM workflow_runs wr
        JOIN workflows w ON wr.workflow_id = w.workflow_id
        WHERE wr.input_parameters::jsonb->>'posting_id' = %s
        ORDER BY wr.started_at DESC
    """, (str(posting_id),))
    
    results = cursor.fetchall()
    cursor.close()
    
    return [dict(row) for row in results]


def get_conversation_runs(workflow_run_id: int, conn) -> List[Dict[str, Any]]:
    """Get all conversation runs for a workflow run"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.conversation_run_id,
            cr.conversation_id,
            c.canonical_name,
            c.conversation_name,
            cr.execution_order,
            a.actor_name,
            a.actor_type,
            cr.started_at,
            cr.completed_at,
            cr.status
        FROM conversation_runs cr
        JOIN conversations c ON cr.conversation_id = c.conversation_id
        JOIN actors a ON c.actor_id = a.actor_id
        WHERE cr.run_id = %s
        ORDER BY cr.execution_order, cr.started_at
    """, (workflow_run_id,))
    
    results = cursor.fetchall()
    cursor.close()
    
    return [dict(row) for row in results]


def get_llm_interactions(conversation_run_id: int, conn, verbose: bool = False) -> List[Dict[str, Any]]:
    """Get LLM interactions for a conversation run"""
    cursor = conn.cursor()
    
    if verbose:
        cursor.execute("""
            SELECT 
                interaction_id,
                execution_order,
                prompt_sent,
                response_received,
                latency_ms,
                status,
                error_message,
                started_at,
                completed_at
            FROM llm_interactions
            WHERE conversation_run_id = %s
            ORDER BY execution_order, started_at
        """, (conversation_run_id,))
    else:
        cursor.execute("""
            SELECT 
                interaction_id,
                execution_order,
                LENGTH(prompt_sent) as prompt_length,
                LENGTH(response_received) as response_length,
                LEFT(response_received, 200) as response_preview,
                latency_ms,
                status,
                error_message
            FROM llm_interactions
            WHERE conversation_run_id = %s
            ORDER BY execution_order, started_at
        """, (conversation_run_id,))
    
    results = cursor.fetchall()
    cursor.close()
    
    return [dict(row) for row in results]


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in human-readable format"""
    if seconds is None:
        return "N/A"
    
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def print_posting_debug(posting_id: int, verbose: bool = False):
    """Print comprehensive debugging information for a posting"""
    conn = get_connection()
    
    # Get posting info
    posting = get_posting_info(posting_id, conn)
    
    if not posting:
        print(f"❌ Posting {posting_id} not found")
        conn.close()
        return
    
    # Print header
    print(f"\n{'='*80}")
    print(f"Posting {posting_id}: {posting['job_title'] or 'N/A'}")
    print(f"{'='*80}\n")
    
    # Print metadata
    print("📋 Metadata:")
    print(f"  - Location: {posting['location_city'] or 'Unknown'}, {posting['location_country'] or 'Unknown'}")
    print(f"  - URL: {posting['external_url'] or 'N/A'}")
    print(f"  - Status: {posting['posting_status']}")
    print(f"  - Job Description: {posting['job_desc_length']} characters")
    print(f"  - Extracted Summary: {'✓ Yes' if posting['extracted_summary'] else '✗ No'}")
    print(f"  - Skills: {'✓ Yes' if posting['skill_keywords'] else '✗ No'}")
    print(f"  - IHL Score: {posting['ihl_score'] or 'Not set'}")
    if posting['ihl_category']:
        print(f"  - IHL Category: {posting['ihl_category']}")
    print()
    
    # Get workflow runs
    workflow_runs = get_workflow_runs(posting_id, conn)
    
    if not workflow_runs:
        print("ℹ️  No workflow executions found for this posting")
        conn.close()
        return
    
    print(f"🔄 Workflow Executions: {len(workflow_runs)}")
    print()
    
    for i, wf_run in enumerate(workflow_runs, 1):
        # Calculate duration
        if wf_run['started_at'] and wf_run['completed_at']:
            duration = (wf_run['completed_at'] - wf_run['started_at']).total_seconds()
        else:
            duration = None
        
        status_icon = "✓" if wf_run['status'] == 'SUCCESS' else "✗"
        
        print(f"{i}. Workflow {wf_run['workflow_id']}: {wf_run['workflow_name']}")
        print(f"   {status_icon} Status: {wf_run['status']}")
        print(f"   - Environment: {wf_run['environment']}")
        print(f"   - Started: {wf_run['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        if wf_run['completed_at']:
            print(f"   - Completed: {wf_run['completed_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Duration: {format_duration(duration)}")
        
        if wf_run['error_message']:
            print(f"   - Error: {wf_run['error_message']}")
        
        # Get conversation runs
        conv_runs = get_conversation_runs(wf_run['workflow_run_id'], conn)
        
        if conv_runs:
            print(f"\n   Execution Path ({len(conv_runs)} conversations):")
            
            for conv in conv_runs:
                # Calculate conversation duration
                if conv['started_at'] and conv['completed_at']:
                    conv_duration = (conv['completed_at'] - conv['started_at']).total_seconds()
                else:
                    conv_duration = None
                
                conv_status_icon = "✓" if conv['status'] == 'SUCCESS' else "✗"
                
                print(f"   {conv['execution_order']:2d}. {conv_status_icon} {conv['canonical_name']}")
                print(f"       Actor: {conv['actor_name']} ({conv['actor_type']})")
                print(f"       Duration: {format_duration(conv_duration)}")
                print(f"       Status: {conv['status']}")
                
                # Get LLM interactions
                interactions = get_llm_interactions(conv['conversation_run_id'], conn, verbose)
                
                if interactions:
                    for interaction in interactions:
                        if verbose:
                            print(f"\n       ─── Interaction {interaction['interaction_id']} ───")
                            print(f"       Prompt ({len(interaction['prompt_sent'])} chars):")
                            print(f"       {interaction['prompt_sent'][:500]}...")
                            print(f"\n       Response ({len(interaction['response_received'])} chars):")
                            print(f"       {interaction['response_received'][:500]}...")
                            print(f"\n       Latency: {interaction['latency_ms']}ms")
                        else:
                            if interaction['status'] != 'SUCCESS':
                                print(f"       ⚠️  {interaction['status']}: {interaction['error_message']}")
                            else:
                                preview = interaction['response_preview']
                                if preview:
                                    preview = preview.replace('\n', ' ')[:80]
                                    print(f"       Output: {preview}...")
                
                print()
        
        print()
    
    conn.close()
    
    # Print next steps
    print(f"{'='*80}")
    print("🔧 Available Actions:")
    print(f"  1. Re-run workflow: python3 -m core.wave_batch_processor --workflow 3001 --limit 1")
    print(f"  2. View workflow diagram: python3 tools/visualize_workflow.py --workflow 3001")
    print(f"  3. Validate workflow: python3 tools/validate_workflow.py --workflow 3001")
    print(f"  4. Export trace: python3 tools/debug_posting.py --posting {posting_id} --export debug.json")
    print(f"{'='*80}\n")


def export_posting_trace(posting_id: int, output_file: str):
    """Export complete posting trace to JSON"""
    conn = get_connection()
    
    data = {
        'posting_id': posting_id,
        'posting': get_posting_info(posting_id, conn),
        'workflow_runs': []
    }
    
    if not data['posting']:
        print(f"❌ Posting {posting_id} not found")
        conn.close()
        return
    
    workflow_runs = get_workflow_runs(posting_id, conn)
    
    for wf_run in workflow_runs:
        wf_data = dict(wf_run)
        wf_data['conversation_runs'] = []
        
        conv_runs = get_conversation_runs(wf_run['workflow_run_id'], conn)
        
        for conv in conv_runs:
            conv_data = dict(conv)
            conv_data['llm_interactions'] = get_llm_interactions(
                conv['conversation_run_id'], conn, verbose=True
            )
            wf_data['conversation_runs'].append(conv_data)
        
        data['workflow_runs'].append(wf_data)
    
    conn.close()
    
    # Convert datetime objects to strings
    def json_serial(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)
    
    print(f"✓ Exported trace to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Debug posting workflow execution'
    )
    
    parser.add_argument('--posting', type=int, required=True,
                       help='Posting ID to debug')
    parser.add_argument('--verbose', action='store_true',
                       help='Show full prompt/response text')
    parser.add_argument('--export', type=str,
                       help='Export full trace to JSON file')
    
    args = parser.parse_args()
    
    if args.export:
        export_posting_trace(args.posting, args.export)
    else:
        print_posting_debug(args.posting, args.verbose)


if __name__ == '__main__':
    main()
