#!/usr/bin/env python3
"""
Workflow Documentation Generator
=================================
Generates comprehensive Markdown documentation for Turing workflows.

Usage:
    python3 tools/document_workflow.py 1114
    python3 tools/document_workflow.py 1114 --output docs/workflows/workflow_1114.md
    python3 tools/document_workflow.py --all

Outputs:
    - Complete workflow structure
    - All conversations in execution order
    - Instructions with full prompts
    - Branching logic (instruction_steps)
    - Actors and their capabilities
"""

import sys
import os
import argparse
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database connection directly (avoid core.__init__ imports)
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025'),
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def get_workflow_data(workflow_id):
    """Fetch complete workflow data from database"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Main workflow query
    cur.execute("""
        SELECT
            w.workflow_id,
            w.workflow_name,
            w.enabled,
            w.created_at,
            w.updated_at,
            wc.step_id,
            wc.conversation_id,
            wc.execution_order,
            wc.execute_condition,
            wc.on_success_action,
            wc.on_failure_action,
            c.conversation_name,
            c.conversation_description,
            c.canonical_name,
            c.conversation_type,
            c.context_strategy,
            c.max_instruction_runs,
            i.instruction_id,
            i.instruction_name,
            i.step_number,
            i.step_description,
            i.prompt_template,
            i.timeout_seconds,
            i.is_terminal,
            a.actor_id,
            a.actor_name,
            a.actor_type,
            a.execution_type,
            a.execution_path,
            ist.instruction_step_id,
            ist.instruction_step_name,
            ist.branch_condition,
            ist.next_instruction_id,
            ist.next_conversation_id,
            ist.max_iterations,
            ist.branch_priority,
            ist.branch_description
        FROM workflows w
        INNER JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
        INNER JOIN conversations c ON wc.conversation_id = c.conversation_id
        INNER JOIN actors a ON c.actor_id = a.actor_id
        INNER JOIN instructions i ON c.conversation_id = i.conversation_id
        LEFT JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
        WHERE w.workflow_id = %s
          AND c.enabled = true
        ORDER BY wc.execution_order, i.step_number, ist.branch_priority DESC
    """, (workflow_id,))
    
    rows = cur.fetchall()
    
    if not rows:
        return None
    
    # Get conversation names for next_conversation_id references
    conversation_names = {}
    cur.execute("SELECT conversation_id, conversation_name FROM conversations")
    for row in cur.fetchall():
        conversation_names[row['conversation_id']] = row['conversation_name']
    
    return rows, conversation_names


def generate_workflow_markdown(workflow_id, output_path=None):
    """Generate Markdown documentation for a workflow"""
    
    data = get_workflow_data(workflow_id)
    if not data:
        print(f"❌ Workflow {workflow_id} not found")
        return False
    
    rows, conversation_names = data
    first = rows[0]
    
    # Group by conversation (need this early now)
    conversations = defaultdict(list)
    for row in rows:
        conversations[row['execution_order']].append(row)
    
    # Build Markdown
    md = []
    md.append(f"# Workflow {workflow_id}: {first['workflow_name']}")
    md.append("")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Status:** {'✅ Enabled' if first['enabled'] else '❌ Disabled'}")
    md.append(f"**Created:** {first['created_at']}")
    md.append(f"**Updated:** {first['updated_at']}")
    md.append("")
    md.append("---")
    md.append("")
    
    # Purpose & Goals section (placeholder - to be filled manually)
    md.append("## Purpose & Goals")
    md.append("")
    md.append("**Purpose:** _[Why does this workflow exist? What problem does it solve?]_")
    md.append("")
    md.append("**Expected Outcome:** _[What is produced when this workflow completes successfully?]_")
    md.append("")
    md.append("**Success Criteria:** _[How do you know this workflow succeeded?]_")
    md.append("")
    md.append("---")
    md.append("")
    
    # Input/Output section
    md.append("## Input & Output")
    md.append("")
    md.append("### Input")
    md.append("_[What data/parameters does this workflow expect?]_")
    md.append("")
    # Try to extract input from first instruction prompt
    first_conv_rows = conversations[1] if 1 in conversations else []
    if first_conv_rows and first_conv_rows[0].get('prompt_template'):
        prompt = first_conv_rows[0]['prompt_template'][:500]  # First 500 chars
        if '{' in prompt:
            md.append("**Detected Parameters:**")
            import re
            params = re.findall(r'\{([^}]+)\}', prompt)
            for param in set(params):
                md.append(f"- `{param}`")
            md.append("")
    
    md.append("### Output")
    md.append("_[What data/artifacts does this workflow produce?]_")
    md.append("")
    md.append("---")
    md.append("")
    
    # Table of contents
    md.append("## Table of Contents")
    md.append("")
    for exec_order in sorted(conversations.keys()):
        first_conv = conversations[exec_order][0]
        md.append(f"{exec_order}. [{first_conv['conversation_name']}](#{sanitize_anchor(first_conv['conversation_name'])})")
    md.append("")
    md.append("---")
    md.append("")
    
    # Workflow overview - using enhanced Mermaid diagram from visualize_workflow.py
    md.append("## Workflow Diagram")
    md.append("")
    md.append("```mermaid")
    md.append("graph TD")
    md.append("")
    
    # Start node
    md.append("    Start([Start Workflow]) --> C1")
    md.append("")
    
    # Generate nodes for each conversation with actor-specific styling
    for exec_order in sorted(conversations.keys()):
        conv_rows = conversations[exec_order]
        first_conv = conv_rows[0]
        node_id = f"C{exec_order}"
        
        # Determine node style based on actor type
        actor_type = first_conv['actor_type']
        actor_name = first_conv['actor_name']
        conv_name = first_conv['conversation_name']
        
        if actor_type == 'ai_model':
            # LLM actors - rounded box with emoji
            label = f"{conv_name}<br/>🤖 {actor_name}"
            md.append(f"    {node_id}[\"{label}\"]")
            md.append(f"    style {node_id} fill:#e1f5ff,stroke:#01579b")
        elif actor_type == 'script':
            # Script actors - hexagon with emoji
            label = f"{conv_name}<br/>⚙️ {actor_name}"
            md.append(f"    {node_id}{{\"{label}\"}}")
            md.append(f"    style {node_id} fill:#fff3e0,stroke:#e65100")
        else:
            # Unknown - rectangle
            label = f"{conv_name}<br/>{actor_name}"
            md.append(f"    {node_id}[\"{label}\"]")
    
    md.append("")
    
    # Generate edges for branches
    for exec_order in sorted(conversations.keys()):
        conv_rows = conversations[exec_order]
        first_conv = conv_rows[0]
        current_node = f"C{exec_order}"
        
        # Collect all branches for this conversation
        branches = []
        for row in conv_rows:
            if row['instruction_step_id'] and row['next_conversation_id']:
                # Find the execution order of the next conversation
                for next_order, next_rows in conversations.items():
                    if next_rows[0]['conversation_id'] == row['next_conversation_id']:
                        next_node = f"C{next_order}"
                        condition = row['branch_condition']
                        priority = row['branch_priority']
                        branches.append((next_node, condition, priority))
                        break
            elif row['instruction_step_id'] and not row['next_conversation_id']:
                # Terminal branch
                condition = row['branch_condition']
                priority = row['branch_priority']
                branches.append(('End', condition, priority))
        
        # Sort branches by priority (highest first)
        branches.sort(key=lambda x: x[2], reverse=True)
        
        if branches:
            # Process each branch
            seen_targets = set()
            for next_node, condition, _ in branches:
                # Skip duplicate paths (same target, different conditions)
                branch_key = (current_node, next_node, condition)
                if branch_key in seen_targets:
                    continue
                seen_targets.add(branch_key)
                
                # Format condition label
                if condition == '*':
                    label = "always"
                else:
                    # Remove square brackets for cleaner display
                    label = condition.replace('[', '').replace(']', '')
                
                if next_node == 'End':
                    md.append(f"    {current_node} -->|{label}| End([End])")
                else:
                    md.append(f"    {current_node} -->|{label}| {next_node}")
        else:
            # No explicit branches - check if terminal or continue to next
            if first_conv.get('is_terminal'):
                md.append(f"    {current_node} --> End([End])")
            elif exec_order < max(conversations.keys()):
                # Continue to next in sequence
                next_node = f"C{exec_order + 1}"
                md.append(f"    {current_node} --> {next_node}")
            else:
                # Last conversation with no explicit terminal
                md.append(f"    {current_node} --> End([End])")
    
    md.append("")
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    
    # Detailed conversation documentation
    md.append("## Conversations")
    md.append("")
    
    for exec_order in sorted(conversations.keys()):
        conv_rows = conversations[exec_order]
        first_conv = conv_rows[0]
        
        md.append(f"### {exec_order}. {first_conv['conversation_name']}")
        md.append("")
        md.append(f"**Canonical Name:** `{first_conv['canonical_name']}`")
        md.append(f"**Description:** {first_conv['conversation_description'] or 'N/A'}")
        md.append(f"**Type:** {first_conv['conversation_type']}")
        md.append(f"**Context Strategy:** {first_conv['context_strategy']}")
        md.append(f"**Max Instruction Runs:** {first_conv['max_instruction_runs']}")
        md.append("")
        
        # Actor details
        md.append("#### Actor")
        md.append("")
        md.append(f"- **Name:** {first_conv['actor_name']}")
        md.append(f"- **Type:** {first_conv['actor_type']}")
        if first_conv['execution_type']:
            md.append(f"- **Execution Type:** {first_conv['execution_type']}")
        if first_conv['execution_path']:
            md.append(f"- **Script:** `{first_conv['execution_path']}`")
        md.append("")
        
        # Execution conditions
        md.append("#### Execution Conditions")
        md.append("")
        md.append(f"- **Execute When:** {first_conv['execute_condition']}")
        md.append(f"- **On Success:** {first_conv['on_success_action']}")
        md.append(f"- **On Failure:** {first_conv['on_failure_action']}")
        md.append("")
        
        # Group by instruction
        instructions = defaultdict(list)
        for row in conv_rows:
            instructions[row['instruction_id']].append(row)
        
        md.append("#### Instructions")
        md.append("")
        
        for instr_id in sorted(instructions.keys()):
            instr_rows = instructions[instr_id]
            first_instr = instr_rows[0]
            
            md.append(f"##### Instruction {first_instr['step_number']}: {first_instr['instruction_name']}")
            md.append("")
            
            if first_instr['step_description']:
                md.append(f"**Description:** {first_instr['step_description']}")
                md.append("")
            
            md.append(f"**Timeout:** {first_instr['timeout_seconds']}s")
            md.append(f"**Terminal:** {first_instr['is_terminal']}")
            md.append("")
            
            # Prompt template
            md.append("**Prompt:**")
            md.append("")
            md.append("```")
            md.append(first_instr['prompt_template'] or 'N/A')
            md.append("```")
            md.append("")
            
            # Branching logic
            has_branches = any(row['instruction_step_id'] for row in instr_rows)
            if has_branches:
                md.append("**Branching Logic:**")
                md.append("")
                
                for row in instr_rows:
                    if row['instruction_step_id']:
                        md.append(f"- **Condition:** `{row['branch_condition']}`")
                        md.append(f"  - **Step:** {row['instruction_step_name']}")
                        if row['branch_description']:
                            md.append(f"  - **Description:** {row['branch_description']}")
                        if row['next_instruction_id']:
                            md.append(f"  - **Next Instruction:** {row['next_instruction_id']}")
                        if row['next_conversation_id']:
                            next_conv = conversation_names.get(row['next_conversation_id'], 'Unknown')
                            md.append(f"  - **Next Conversation:** {next_conv}")
                        if row['max_iterations']:
                            md.append(f"  - **Max Iterations:** {row['max_iterations']}")
                        md.append("")
            
        md.append("---")
        md.append("")
    
    # Statistics
    md.append("## Statistics")
    md.append("")
    total_convs = len(conversations)
    total_instrs = len(set(row['instruction_id'] for row in rows))
    total_branches = len(set(row['instruction_step_id'] for row in rows if row['instruction_step_id']))
    
    md.append(f"- **Total Conversations:** {total_convs}")
    md.append(f"- **Total Instructions:** {total_instrs}")
    md.append(f"- **Total Branch Points:** {total_branches}")
    md.append("")
    
    md.append("---")
    md.append("")
    
    # Error Handling Summary
    md.append("## Error Handling")
    md.append("")
    
    # Analyze failure actions
    failure_actions = set(row['on_failure_action'] for row in rows if row['on_failure_action'])
    if failure_actions:
        md.append("**On Failure:**")
        for action in sorted(failure_actions):
            md.append(f"- {action}")
        md.append("")
    
    # List UNEXPECTED/error branches
    error_branches = [row for row in rows if row['instruction_step_id'] and row['branch_condition'] in ('*', 'UNEXPECTED', 'ERROR')]
    if error_branches:
        md.append("**Error Recovery Paths:**")
        for branch in error_branches:
            next_conv = conversation_names.get(branch['next_conversation_id'], 'Unknown') if branch['next_conversation_id'] else 'None'
            md.append(f"- **{branch['instruction_name']}** → `{branch['branch_condition']}` → {next_conv}")
        md.append("")
    
    md.append("---")
    md.append("")
    
    # Dependencies
    md.append("## Dependencies")
    md.append("")
    
    # Collect unique actors by type
    actor_types = defaultdict(set)
    for row in rows:
        actor_types[row['actor_type']].add(row['actor_name'])
    
    if 'ai_model' in actor_types:
        md.append("**AI Models:**")
        for model in sorted(actor_types['ai_model']):
            md.append(f"- {model}")
        md.append("")
    
    if 'script' in actor_types:
        md.append("**Scripts:**")
        script_paths = set(row['execution_path'] for row in rows if row['actor_type'] == 'script' and row['execution_path'])
        for script in sorted(script_paths):
            md.append(f"- `{script}`")
        md.append("")
    
    md.append("**Database Tables:** _[List tables this workflow reads from or writes to]_")
    md.append("")
    
    md.append("---")
    md.append("")
    
    # Usage Examples
    md.append("## Usage Examples")
    md.append("")
    md.append("### Trigger this workflow")
    md.append("```python")
    md.append("from core.turing_orchestrator import TuringOrchestrator")
    md.append("")
    md.append("orchestrator = TuringOrchestrator()")
    md.append(f"result = orchestrator.run_workflow({workflow_id}, task_data={{}})")
    md.append("```")
    md.append("")
    md.append("### Expected Input Format")
    md.append("```json")
    md.append("{")
    md.append('  "example_param": "value"')
    md.append("}")
    md.append("```")
    md.append("")
    md.append("---")
    md.append("")
    
    # Change Log
    md.append("## Change Log")
    md.append("")
    md.append(f"- **{first['created_at']}** - Workflow created")
    if first['updated_at'] != first['created_at']:
        md.append(f"- **{first['updated_at']}** - Last updated")
    md.append("")
    md.append("_Add manual notes about changes here_")
    md.append("")
    
    # Write to file or print
    content = "\n".join(md)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"✅ Documentation written to {output_path}")
    else:
        print(content)
    
    return True


def sanitize_anchor(text):
    """Convert text to markdown anchor format"""
    return text.lower().replace(' ', '-').replace('_', '-')


def list_all_workflows():
    """List all enabled workflows"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT w.workflow_id, w.workflow_name, w.enabled, 
               COUNT(DISTINCT wc.conversation_id) as conv_count
        FROM workflows w
        LEFT JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
        GROUP BY w.workflow_id, w.workflow_name, w.enabled
        ORDER BY w.workflow_id
    """)
    
    print("\n📋 Available Workflows:")
    print("=" * 80)
    
    for row in cur.fetchall():
        status = "✅" if row['enabled'] else "❌"
        print(f"{status} Workflow {row['workflow_id']}: {row['workflow_name']}")
        print(f"   Conversations: {row['conv_count']}")
    
    print("=" * 80)
    print()


def check_if_stale(workflow_id: int) -> bool:
    """Check if workflow documentation is stale"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT is_stale, needs_regeneration, change_count
        FROM workflow_doc_status
        WHERE workflow_id = %s
    ''', (workflow_id,))
    
    result = cursor.fetchone()
    return_connection(conn)
    
    if not result:
        return True  # No record = needs generation
    
    return result['is_stale'] or result['needs_regeneration']


def mark_doc_generated(workflow_id: int):
    """Mark workflow documentation as generated"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT mark_workflow_doc_generated(%s)', (workflow_id,))
    conn.commit()
    return_connection(conn)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Markdown documentation for Turing workflows',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tools/document_workflow.py 1114
  python3 tools/document_workflow.py 1114 -o docs/workflows/workflow_1114.md
  python3 tools/document_workflow.py --all
  python3 tools/document_workflow.py --list
        """
    )
    
    parser.add_argument('workflow_id', nargs='?', type=int, 
                       help='Workflow ID to document')
    parser.add_argument('-o', '--output', 
                       help='Output file path (default: print to stdout)')
    parser.add_argument('--all', action='store_true',
                       help='Generate docs for all enabled workflows')
    parser.add_argument('--list', action='store_true',
                       help='List all available workflows')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_workflows()
        return
    
    if args.all:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT workflow_id, workflow_name FROM workflows WHERE enabled = true ORDER BY workflow_id")
        workflows = cur.fetchall()
        
        print(f"\n📚 Generating documentation for {len(workflows)} workflows...\n")
        
        for row in workflows:
            wf_id = row['workflow_id']
            # Sanitize workflow name for filename
            safe_name = row['workflow_name'].lower().replace(' ', '_').replace('/', '_')
            # Remove special characters
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
            output_path = f"docs/workflows/{wf_id}_{safe_name}.md"
            generate_workflow_markdown(wf_id, output_path)
        
        print(f"\n✅ Generated {len(workflows)} workflow documents in docs/workflows/")
        return
    
    if not args.workflow_id:
        parser.print_help()
        print("\n")
        list_all_workflows()
        return
    
    # If no output specified, auto-save to docs/workflows/
    output_path = args.output
    if not output_path:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT workflow_name FROM workflows WHERE workflow_id = %s", (args.workflow_id,))
        row = cur.fetchone()
        if row:
            safe_name = row['workflow_name'].lower().replace(' ', '_').replace('/', '_')
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
            output_path = f"docs/workflows/{args.workflow_id}_{safe_name}.md"
        cur.close()
        conn.close()
    
    generate_workflow_markdown(args.workflow_id, output_path)


if __name__ == '__main__':
    main()
