"""
Trace Report Generator for Wave Runner
Generates detailed markdown reports of workflow execution
"""

import json
from datetime import datetime
from typing import List, Dict, Any


def generate_trace_report(
    trace_data: List[Dict[str, Any]],
    stats: Dict[str, Any],
    start_time: datetime,
    trace_file: str,
    workflow_run_id: int = None,
    posting_id: int = None
):
    """
    Generate markdown trace report.
    
    Args:
        trace_data: List of trace entries collected during execution
        stats: Execution statistics
        start_time: Workflow start time
        trace_file: Path to output file
        workflow_run_id: Workflow run ID (optional)
        posting_id: Posting ID (optional)
    """
    with open(trace_file, 'w') as f:
        # Header
        f.write("# Workflow Execution Trace\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Workflow context (from first interaction)
        if trace_data and trace_data[0].get('context'):
            ctx = trace_data[0]['context']
            f.write("## Workflow Context\n\n")
            f.write(f"**Workflow ID:** {ctx.get('workflow_id')}\n")
            f.write(f"**Workflow Name:** {ctx.get('workflow_name')}\n")
            if ctx.get('workflow_description'):
                f.write(f"**Description:** {ctx.get('workflow_description')}\n")
            if workflow_run_id:
                f.write(f"**Workflow Run ID:** {workflow_run_id}\n")
            if posting_id or ctx.get('posting_id'):
                pid = posting_id or ctx.get('posting_id')
                f.write(f"**Posting ID:** {pid}\n")
                if ctx.get('job_title'):
                    f.write(f"**Job Title:** {ctx.get('job_title')}\n")
                if ctx.get('location_city'):
                    f.write(f"**Location:** {ctx.get('location_city')}\n")
            f.write(f"**Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Duration:** {stats.get('duration_ms', 0) / 1000:.1f} seconds\n")
            f.write(f"**Interactions:** {stats['interactions_completed']} completed, {stats['interactions_failed']} failed\n\n")
            f.write("---\n\n")
        else:
            # Fallback to simple header
            if workflow_run_id:
                f.write(f"**workflow_run_id:** {workflow_run_id}\n")
            if posting_id:
                f.write(f"**posting_id:** {posting_id}\n")
            f.write(f"**started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**duration:** {stats.get('duration_ms', 0) / 1000:.1f} seconds\n")
            f.write(f"**interactions:** {stats['interactions_completed']} completed, {stats['interactions_failed']} failed\n\n")
            f.write("---\n\n")
        
        # Each interaction
        for idx, trace in enumerate(trace_data, 1):
            status_icon = '✅' if trace['status'] == 'completed' else '❌'
            f.write(f"## {status_icon} Interaction {idx}: {trace['conversation_name']}\n\n")
            
            # Basic IDs
            f.write(f"**Interaction ID:** {trace['interaction_id']}\n")
            f.write(f"**Duration:** {trace['duration']:.2f}s\n")
            f.write(f"**Status:** {trace['status']}\n\n")
            
            # Conversation context
            ctx = trace.get('context', {})
            if ctx:
                f.write("### Conversation Configuration\n\n")
                f.write(f"**Conversation ID:** {ctx.get('conversation_id')}\n")
                f.write(f"**Name:** {ctx.get('conversation_name')}\n")
                if ctx.get('conversation_description'):
                    f.write(f"**Description:** {ctx.get('conversation_description')}\n")
                f.write(f"**Type:** {ctx.get('conversation_type', 'single_actor')}\n")
                f.write(f"**Context Strategy:** {ctx.get('context_strategy', 'isolated')}\n\n")
            
            # Actor configuration
            if ctx:
                f.write("### Actor Configuration\n\n")
                f.write(f"**Actor ID:** {ctx.get('actor_id')}\n")
                f.write(f"**Name:** {ctx.get('actor_name')}\n")
                f.write(f"**Type:** {ctx.get('actor_type')}\n")
                if ctx.get('actor_type') == 'ai_model':
                    f.write(f"**Model:** {ctx.get('actor_name')}\n")
                if ctx.get('script_file_path'):
                    f.write(f"**Script:** {ctx.get('script_file_path')}\n")
                if ctx.get('system_prompt'):
                    f.write(f"**System Prompt:** {ctx.get('system_prompt')}\n")
                f.write("\n")
            
            # Prompt template (from instructions)
            if ctx and ctx.get('prompt_template'):
                f.write("### Prompt Template\n\n")
                if ctx.get('step_description'):
                    f.write(f"**Step Description:** {ctx.get('step_description')}\n\n")
                f.write("````\n")
                f.write(ctx.get('prompt_template'))
                f.write("\n````\n\n")
            
            # Branching logic
            if trace.get('branching_steps'):
                f.write("### Branching Logic\n\n")
                f.write("After this interaction completes, the following branching rules apply:\n\n")
                for step in trace['branching_steps']:
                    f.write(f"**{step['instruction_step_name']}** (Priority: {step['branch_priority']})\n")
                    f.write(f"- **Condition:** `{step['branch_condition']}`\n")
                    if step.get('branch_description'):
                        f.write(f"- **Description:** {step['branch_description']}\n")
                    if step.get('next_conversation_id'):
                        f.write(f"- **Next:** Conversation {step['next_conversation_id']}\n")
                    elif step.get('next_instruction_id'):
                        f.write(f"- **Next:** Instruction {step['next_instruction_id']}\n")
                    else:
                        f.write(f"- **Next:** END (terminal)\n")
                    f.write("\n")
            
            # Parent interactions
            if trace['parent_interaction_ids']:
                f.write(f"### Parent Interactions\n\n")
                f.write("This interaction received data from:\n\n")
                for parent_id in trace['parent_interaction_ids']:
                    f.write(f"- Interaction {parent_id}\n")
                f.write("\n")
            
            # Show input
            f.write("### Actual Input (Substituted)\n\n")
            f.write("This is what was actually executed (all placeholders substituted):\n\n")
            input_data = trace['input']
            if isinstance(input_data, dict):
                # Format nicely
                if 'prompt' in input_data:
                    # AI actor - show full prompt (no truncation)
                    prompt = input_data['prompt']
                    f.write(f"````\n{prompt}\n````\n\n")
                else:
                    # Script actor - show params
                    f.write(f"````json\n{json.dumps(input_data, indent=2)}\n````\n\n")
            else:
                f.write(f"````\n{input_data}\n````\n\n")
            
            # Show output
            if trace['status'] == 'completed':
                f.write("### Actual Output\n\n")
                output = trace['output']
                if isinstance(output, dict):
                    if 'response' in output:
                        # AI response - show full response (no truncation)
                        response = output['response']
                        f.write(f"````\n{response}\n````\n\n")
                        
                        # Show other fields
                        other_fields = {k: v for k, v in output.items() if k != 'response'}
                        if other_fields:
                            f.write(f"**Metadata:** `{json.dumps(other_fields)}`\n\n")
                    else:
                        # Script output
                        f.write(f"````json\n{json.dumps(output, indent=2)}\n````\n\n")
                else:
                    f.write(f"````\n{output}\n````\n\n")
            else:
                # Failed - show error
                f.write("### Error\n\n")
                f.write(f"````\n{trace.get('error', 'Unknown error')}\n````\n\n")
            
            # Show children created
            if trace.get('child_interaction_ids'):
                f.write(f"### Child Interactions Created\n\n")
                for child_id in trace['child_interaction_ids']:
                    f.write(f"- Interaction {child_id}\n")
                f.write("\n")
            
            f.write("---\n\n")
        
        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total interactions:** {len(trace_data)}\n")
        f.write(f"- **Completed:** {stats['interactions_completed']}\n")
        f.write(f"- **Failed:** {stats['interactions_failed']}\n")
        f.write(f"- **Total duration:** {stats.get('duration_ms', 0) / 1000:.1f}s\n")
        if len(trace_data) > 0:
            f.write(f"- **Avg per interaction:** {stats.get('duration_ms', 0) / len(trace_data) / 1000:.2f}s\n")
