#!/usr/bin/env python3
"""
Generate detailed QA traces for problematic postings

Queries the turing database to get full LLM interaction details:
- Prompts sent to models
- Responses received
- Model names and parameters
- Timestamps and costs

Usage:
    python3 scripts/generate_qa_traces.py --posting-id 17
    python3 scripts/generate_qa_traces.py --posting-ids 17,7,5,4492,4550
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get PostgreSQL database connection to turing"""
    return psycopg2.connect(
        dbname="turing",
        user="base_admin",
        password="base_yoga_secure_2025",
        host="localhost",
        port=5432
    )


def get_posting_info(conn, posting_id: int):
    """Get posting basic info"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                posting_id,
                job_title,
                LENGTH(job_description) as desc_length,
                LENGTH(extracted_summary) as summary_length,
                job_description,
                extracted_summary
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        return cur.fetchone()


def get_llm_interactions(conn, posting_id: int):
    """Get all LLM interactions for a posting from turing database"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # First, find workflow_run_id for this posting
        cur.execute("""
            SELECT DISTINCT workflow_run_id
            FROM posting_state_checkpoints
            WHERE posting_id = %s
            ORDER BY workflow_run_id DESC
            LIMIT 1
        """, (posting_id,))
        
        result = cur.fetchone()
        if not result:
            return []
        
        workflow_run_id = result['workflow_run_id']
        
        # Get LLM interactions for this workflow run with actor info
        cur.execute("""
            SELECT 
                li.interaction_id,
                li.workflow_run_id,
                li.prompt_sent,
                li.response_received,
                li.tokens_input,
                li.tokens_output,
                li.cost_usd,
                li.latency_ms,
                li.started_at,
                li.completed_at,
                li.status,
                li.error_message,
                a.actor_name,
                a.actor_type,
                a.execution_config
            FROM llm_interactions li
            LEFT JOIN actors a ON li.actor_id = a.actor_id
            WHERE li.workflow_run_id = %s
            ORDER BY li.started_at
        """, (workflow_run_id,))
        return cur.fetchall()


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return "(empty)"
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration"""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        mins = int(ms / 60000)
        secs = (ms % 60000) / 1000
        return f"{mins}m {secs:.0f}s"


def generate_trace_report(posting_id: int, output_dir: Path):
    """Generate detailed trace report for a posting"""
    
    conn = get_db_connection()
    
    # Get posting info
    posting = get_posting_info(conn, posting_id)
    if not posting:
        print(f"ERROR: Posting {posting_id} not found")
        conn.close()
        return
    
    # Get LLM interactions
    interactions = get_llm_interactions(conn, posting_id)
    
    conn.close()
    
    # Generate report
    report = []
    report.append(f"# QA Trace Report - Posting {posting_id}")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Posting info
    report.append("## Posting Information")
    report.append("")
    report.append(f"- **Job Title:** {posting['job_title']}")
    report.append(f"- **Description Length:** {posting['desc_length']:,} chars")
    report.append(f"- **Summary Length:** {posting['summary_length']:,} chars")
    report.append(f"- **Expansion Ratio:** {posting['summary_length'] / posting['desc_length']:.2f}x" if posting['desc_length'] > 0 else "- **Expansion Ratio:** N/A")
    report.append("")
    
    # LLM Interactions
    report.append("## LLM Interactions")
    report.append("")
    report.append(f"**Total Interactions:** {len(interactions)}")
    report.append("")
    
    if not interactions:
        report.append("⚠️ No LLM interactions found for this posting in the turing database.")
        report.append("")
        report.append("This could mean:")
        report.append("- The posting was processed before LLM interaction logging was implemented")
        report.append("- The interactions were logged to a different database (ty_learn)")
        report.append("- The posting hasn't been processed yet")
    else:
        total_cost = sum(i['cost_usd'] or 0 for i in interactions)
        total_tokens_in = sum(i['tokens_input'] or 0 for i in interactions)
        total_tokens_out = sum(i['tokens_output'] or 0 for i in interactions)
        
        report.append(f"- **Total Cost:** ${total_cost:.4f}")
        report.append(f"- **Total Tokens:** {total_tokens_in:,} in, {total_tokens_out:,} out")
        report.append("")
        
        for idx, interaction in enumerate(interactions, 1):
            report.append(f"### Interaction {idx}")
            report.append("")
            report.append(f"- **Interaction ID:** {interaction['interaction_id']}")
            report.append(f"- **Actor:** {interaction['actor_name']} ({interaction['actor_type']})")
            if interaction['execution_config']:
                import json
                try:
                    config = json.loads(interaction['execution_config']) if isinstance(interaction['execution_config'], str) else interaction['execution_config']
                    if 'model' in config:
                        report.append(f"- **Model:** {config['model']}")
                except:
                    pass
            report.append(f"- **Started:** {interaction['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"- **Duration:** {format_duration(interaction['latency_ms'])}")
            report.append(f"- **Status:** {interaction['status']}")
            report.append(f"- **Tokens:** {interaction['tokens_input'] or 0} in, {interaction['tokens_output'] or 0} out")
            if interaction['cost_usd']:
                report.append(f"- **Cost:** ${interaction['cost_usd']:.4f}")
            if interaction['error_message']:
                report.append(f"- **Error:** {interaction['error_message']}")
            report.append("")
            
            report.append("#### Prompt Sent")
            report.append("```")
            report.append(interaction['prompt_sent'] or "(empty)")
            report.append("```")
            report.append("")
            
            report.append("#### Response Received")
            report.append("```")
            report.append(interaction['response_received'] or "(empty)")
            report.append("```")
            report.append("")
            report.append("---")
            report.append("")
    
    # Job Description
    report.append("## Original Job Description")
    report.append("")
    report.append("```")
    report.append(posting['job_description'] or "(empty)")
    report.append("```")
    report.append("")
    
    # Extracted Summary
    report.append("## Extracted Summary (Final Output)")
    report.append("")
    report.append("```")
    report.append(posting['extracted_summary'] or "(empty)")
    report.append("```")
    report.append("")
    
    # Write report
    output_file = output_dir / f"posting_{posting_id}_trace.md"
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"✅ Generated trace: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Generate QA traces from turing database')
    parser.add_argument('--posting-id', type=int, help='Single posting ID to trace')
    parser.add_argument('--posting-ids', type=str, help='Comma-separated posting IDs (e.g., 17,7,5)')
    parser.add_argument('--output-dir', type=str, default='logs/qa_traces', help='Output directory')
    
    args = parser.parse_args()
    
    # Determine posting IDs to process
    posting_ids = []
    if args.posting_id:
        posting_ids = [args.posting_id]
    elif args.posting_ids:
        posting_ids = [int(pid.strip()) for pid in args.posting_ids.split(',')]
    else:
        print("ERROR: Must provide --posting-id or --posting-ids")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate traces
    print(f"Generating traces for {len(posting_ids)} posting(s)...")
    for posting_id in posting_ids:
        try:
            generate_trace_report(posting_id, output_dir)
        except Exception as e:
            print(f"❌ Error generating trace for posting {posting_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Complete! Traces saved to: {output_dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
