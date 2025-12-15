#!/usr/bin/env python3
"""
Retrospective Trace Generator

Generate comprehensive trace reports for ANY workflow run after execution.
This tool reads completed interactions from the database and reconstructs
the full execution trace - exactly what would have been generated with trace=True.

Usage:
    # Generate trace for a specific workflow run
    python3 tools/generate_retrospective_trace.py --workflow-run-id 167
    
    # Generate trace for a specific posting (latest run)
    python3 tools/generate_retrospective_trace.py --posting-id 4793
    
    # Generate trace for specific interaction range
    python3 tools/generate_retrospective_trace.py --interaction-ids 493-512
    
    # Specify output file
    python3 tools/generate_retrospective_trace.py --workflow-run-id 167 --output reports/trace_retro_167.md

Why this exists:
    "As we go into production hilarity will ensue. Always does.
     Nothing works, results are crazy off the charts.
     Nobody knows why it happens. People huddle around in small groups, whispering.
     
     ...and in THAT situation, the door opens. Sandy, the queen of the waves steps in:
     'Lets run a trace on this critter and take it out.'"
     
    - xai, Nov 26, 2025
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment
load_dotenv()


class RetrospectiveTraceGenerator:
    """Generate trace reports from completed workflow runs."""
    
    def __init__(self, db_conn):
        self.conn = db_conn
        
    def generate_for_workflow_run(self, workflow_run_id: int, output_file: str = None):
        """Generate trace for a completed workflow run."""
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get workflow run details
        cursor.execute("""
            SELECT wr.workflow_run_id, wr.workflow_id, wr.posting_id, wr.status,
                   wr.started_at, wr.completed_at, wr.state,
                   w.workflow_name,
                   p.job_title, p.posting_name
            FROM workflow_runs wr
            JOIN workflows w ON wr.workflow_id = w.workflow_id
            LEFT JOIN postings p ON wr.posting_id = p.posting_id
            WHERE wr.workflow_run_id = %s
        """, (workflow_run_id,))
        
        run_data = cursor.fetchone()
        
        if not run_data:
            raise ValueError(f"Workflow run {workflow_run_id} not found")
        
        # Get all interactions
        cursor.execute("""
            SELECT i.interaction_id, i.conversation_id, i.status, i.created_at, i.completed_at,
                   i.input, i.output, i.input_interaction_ids,
                   c.conversation_name, c.conversation_description, c.conversation_type,
                   c.context_strategy,
                   a.actor_id, a.actor_name, a.actor_type
            FROM interactions i
            JOIN conversations c ON i.conversation_id = c.conversation_id
            JOIN actors a ON c.actor_id = a.actor_id
            WHERE i.workflow_run_id = %s
            ORDER BY i.interaction_id
        """, (workflow_run_id,))
        
        interactions = cursor.fetchall()
        
        if not interactions:
            raise ValueError(f"No interactions found for workflow run {workflow_run_id}")
        
        # Get branching logic for each conversation
        branching_data = {}
        for interaction in interactions:
            cursor.execute("""
                SELECT ins.instruction_id, ins.step_description, ins.prompt_template,
                       ist.instruction_step_name, ist.branch_condition, ist.branch_description,
                       ist.branch_priority, ist.next_conversation_id,
                       nc.conversation_name as next_conv_name
                FROM instructions ins
                LEFT JOIN instruction_steps ist ON ins.instruction_id = ist.instruction_id
                LEFT JOIN conversations nc ON ist.next_conversation_id = nc.conversation_id
                WHERE ins.conversation_id = %s AND ins.enabled = true
                ORDER BY ist.branch_priority DESC
            """, (interaction['conversation_id'],))
            
            branching_data[interaction['interaction_id']] = cursor.fetchall()
        
        cursor.close()
        
        # Generate trace report
        if not output_file:
            output_file = f"reports/trace_retro_run_{workflow_run_id}.md"
        
        self._write_trace_report(run_data, interactions, branching_data, output_file)
        
        return output_file
    
    def generate_for_posting(self, posting_id: int, output_file: str = None):
        """Generate trace for the latest workflow run of a posting."""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT workflow_run_id
            FROM workflow_runs
            WHERE posting_id = %s
            ORDER BY started_at DESC
            LIMIT 1
        """, (posting_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise ValueError(f"No workflow runs found for posting {posting_id}")
        
        workflow_run_id = result[0]
        return self.generate_for_workflow_run(workflow_run_id, output_file)
    
    def generate_for_interaction_range(self, start_id: int, end_id: int, output_file: str = None):
        """Generate trace for a specific range of interactions."""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT workflow_run_id
            FROM interactions
            WHERE interaction_id BETWEEN %s AND %s
        """, (start_id, end_id))
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise ValueError(f"No interactions found in range {start_id}-{end_id}")
        
        workflow_run_id = result[0]
        return self.generate_for_workflow_run(workflow_run_id, output_file)
    
    def _write_trace_report(self, run_data, interactions, branching_data, output_file):
        """Write the trace report to markdown file."""
        
        # Calculate metrics
        total_interactions = len(interactions)
        completed = sum(1 for i in interactions if i['status'] == 'completed')
        failed = sum(1 for i in interactions if i['status'] == 'failed')
        
        duration = None
        if run_data['completed_at'] and run_data['started_at']:
            duration = (run_data['completed_at'] - run_data['started_at']).total_seconds()
        
        # Start writing
        with open(output_file, 'w') as f:
            f.write("# Workflow Execution Trace (Retrospective)\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Retrospective)\n\n")
            
            # Workflow Context
            f.write("## Workflow Context\n\n")
            f.write(f"**Workflow ID:** {run_data['workflow_id']}\n")
            f.write(f"**Workflow Name:** {run_data['workflow_name']}\n")
            f.write(f"**Posting ID:** {run_data['posting_id']}\n")
            f.write(f"**Job Title:** {run_data.get('job_title', 'N/A')}\n")
            f.write(f"**Started:** {run_data['started_at']}\n")
            f.write(f"**Completed:** {run_data.get('completed_at', 'N/A')}\n")
            if duration:
                f.write(f"**Duration:** {duration:.1f} seconds\n")
            f.write(f"**Interactions:** {completed} completed, {failed} failed\n\n")
            f.write("---\n\n")
            
            # Interactions
            for idx, interaction in enumerate(interactions, 1):
                self._write_interaction(f, idx, interaction, branching_data.get(interaction['interaction_id'], []))
        
        print(f"✅ Trace report generated: {output_file}")
        print(f"   Workflow Run: {run_data['workflow_run_id']}")
        print(f"   Interactions: {total_interactions}")
        print(f"   Duration: {duration:.1f}s" if duration else "   Duration: N/A")
    
    def _write_interaction(self, f, idx, interaction, branching_steps):
        """Write a single interaction to the trace."""
        
        status_emoji = "✅" if interaction['status'] == 'completed' else "❌"
        
        f.write(f"## {status_emoji} Interaction {idx}: {interaction['conversation_name']}\n\n")
        f.write(f"**Interaction ID:** {interaction['interaction_id']}\n")
        
        if interaction['completed_at'] and interaction['created_at']:
            duration = (interaction['completed_at'] - interaction['created_at']).total_seconds()
            f.write(f"**Duration:** {duration:.2f}s\n")
        
        f.write(f"**Status:** {interaction['status']}\n\n")
        
        # Conversation Configuration
        f.write("### Conversation Configuration\n\n")
        f.write(f"**Conversation ID:** {interaction['conversation_id']}\n")
        f.write(f"**Name:** {interaction['conversation_name']}\n")
        if interaction.get('conversation_description'):
            f.write(f"**Description:** {interaction['conversation_description']}\n")
        f.write(f"**Type:** {interaction['conversation_type']}\n")
        f.write(f"**Context Strategy:** {interaction['context_strategy']}\n\n")
        
        # Actor Configuration
        f.write("### Actor Configuration\n\n")
        f.write(f"**Actor ID:** {interaction['actor_id']}\n")
        f.write(f"**Name:** {interaction['actor_name']}\n")
        f.write(f"**Type:** {interaction['actor_type']}\n\n")
        
        # Prompt Template (if available from branching_steps)
        if branching_steps and len(branching_steps) > 0:
            first_step = branching_steps[0]
            if first_step.get('prompt_template'):
                f.write("### Prompt Template\n\n")
                if first_step.get('step_description'):
                    f.write(f"**Step Description:** {first_step['step_description']}\n\n")
                f.write("````\n")
                f.write(first_step['prompt_template'])
                f.write("\n````\n\n")
        
        # Branching Logic
        if branching_steps and any(bs.get('branch_condition') for bs in branching_steps):
            f.write("### Branching Logic\n\n")
            f.write("After this interaction completes, the following branching rules apply:\n\n")
            
            for step in branching_steps:
                if step.get('instruction_step_name'):
                    f.write(f"**{step['instruction_step_name']}** (Priority: {step.get('branch_priority', 'N/A')})\n")
                    f.write(f"- **Condition:** `{step['branch_condition']}`\n")
                    if step.get('branch_description'):
                        f.write(f"- **Description:** {step['branch_description']}\n")
                    if step.get('next_conv_name'):
                        f.write(f"- **Next:** Conversation {step['next_conversation_id']} ({step['next_conv_name']})\n")
                    elif step['next_conversation_id']:
                        f.write(f"- **Next:** Conversation {step['next_conversation_id']}\n")
                    else:
                        f.write(f"- **Next:** END (terminal)\n")
                    f.write("\n")
        
        # Parent Interactions
        if interaction.get('input_interaction_ids'):
            f.write("### Parent Interactions\n\n")
            f.write("This interaction received data from:\n\n")
            for parent_id in interaction['input_interaction_ids']:
                f.write(f"- Interaction {parent_id}\n")
            f.write("\n")
        
        # Actual Input
        f.write("### Actual Input (Substituted)\n\n")
        f.write("This is what was actually executed (all placeholders substituted):\n\n")
        f.write("````json\n")
        import json
        f.write(json.dumps(interaction.get('input') or {}, indent=2))
        f.write("\n````\n\n")
        
        # Actual Output
        f.write("### Actual Output\n\n")
        if interaction['status'] == 'completed':
            output_data = interaction.get('output') or {}
            
            # Extract response if it's in standard format
            if isinstance(output_data, dict):
                if 'response' in output_data:
                    f.write("````\n")
                    f.write(str(output_data['response']))
                    f.write("\n````\n\n")
                elif 'data' in output_data:
                    f.write("````json\n")
                    f.write(json.dumps(output_data['data'], indent=2))
                    f.write("\n````\n\n")
                else:
                    f.write("````json\n")
                    f.write(json.dumps(output_data, indent=2))
                    f.write("\n````\n\n")
                
                # Metadata if available
                if 'model' in output_data or 'latency_ms' in output_data:
                    metadata = {}
                    if 'model' in output_data:
                        metadata['model'] = output_data['model']
                    if 'latency_ms' in output_data:
                        metadata['latency_ms'] = output_data['latency_ms']
                    f.write(f"**Metadata:** `{json.dumps(metadata)}`\n\n")
            else:
                f.write("````\n")
                f.write(str(output_data))
                f.write("\n````\n\n")
        else:
            f.write("*Interaction failed - no output*\n\n")
        
        f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate retrospective trace reports from completed workflow runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate trace for workflow run 167
    python3 tools/generate_retrospective_trace.py --workflow-run-id 167
    
    # Generate trace for posting 4793 (latest run)
    python3 tools/generate_retrospective_trace.py --posting-id 4793
    
    # Generate trace for interaction range
    python3 tools/generate_retrospective_trace.py --interaction-ids 493-512
    
    # Specify output file
    python3 tools/generate_retrospective_trace.py -w 167 -o reports/debug_run_167.md
        """
    )
    
    parser.add_argument('-w', '--workflow-run-id', type=int, help='Workflow run ID')
    parser.add_argument('-p', '--posting-id', type=int, help='Posting ID (uses latest run)')
    parser.add_argument('-i', '--interaction-ids', help='Interaction ID range (e.g., 493-512)')
    parser.add_argument('-o', '--output', help='Output file path (default: reports/trace_retro_run_X.md)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.workflow_run_id, args.posting_id, args.interaction_ids]):
        parser.error("Must specify one of: --workflow-run-id, --posting-id, or --interaction-ids")
    
    # Connect to database
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='turing',
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Generate trace
    try:
        generator = RetrospectiveTraceGenerator(conn)
        
        if args.workflow_run_id:
            output = generator.generate_for_workflow_run(args.workflow_run_id, args.output)
        elif args.posting_id:
            output = generator.generate_for_posting(args.posting_id, args.output)
        elif args.interaction_ids:
            start, end = map(int, args.interaction_ids.split('-'))
            output = generator.generate_for_interaction_range(start, end, args.output)
        
        print(f"\n📊 Trace report ready: {output}")
        print(f"   View with: cat {output}")
        
    except Exception as e:
        print(f"❌ Error generating trace: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
