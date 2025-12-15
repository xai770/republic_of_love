#!/usr/bin/env python3
"""
Visualize Workflow
==================

Generates Mermaid flowchart diagrams from workflow definitions.

Usage:
    # Generate from database
    python3 tools/visualize_workflow.py --workflow 3001
    
    # Generate from YAML file
    python3 tools/visualize_workflow.py --file workflows/3001_job_processing.yaml
    
    # Output to file
    python3 tools/visualize_workflow.py --workflow 3001 --output docs/workflows/3001_diagram.md

Output:
    Mermaid markdown diagram showing:
    - All conversations as nodes
    - Branch conditions as edges
    - Actor types (LLM vs script)
    - Execution order

Author: Arden
Date: 2025-11-13
"""

import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection
from config.paths import BASE_DIR


def load_workflow_from_db(workflow_id: int) -> Dict[str, Any]:
    """Load workflow definition from database"""
    from tools.export_workflows_to_yaml import export_workflow_to_yaml
    
    conn = get_connection()
    workflow_data = export_workflow_to_yaml(workflow_id, conn)
    conn.close()
    return workflow_data


def load_workflow_from_yaml(yaml_path: Path) -> Dict[str, Any]:
    """Load workflow definition from YAML file"""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def generate_mermaid_diagram(workflow_data: Dict[str, Any]) -> str:
    """
    Generate Mermaid flowchart from workflow definition
    
    Returns:
        Mermaid markdown string
    """
    lines = []
    
    # Header
    lines.append("```mermaid")
    lines.append("graph TD")
    lines.append("")
    
    # Add start node
    lines.append("    Start([Start Workflow]) --> C1")
    lines.append("")
    
    # Generate nodes for each conversation
    for conv in workflow_data['conversations']:
        conv_id = conv['canonical_name']
        node_id = f"C{conv['execution_order']}"
        
        # Determine node style based on actor type
        actor_type = conv['actor']['actor_type']
        actor_name = conv['actor']['actor_name']
        
        if actor_type == 'ai_model':
            # LLM actors - rounded box
            label = f"{conv['name']}<br/>🤖 {actor_name}"
            lines.append(f"    {node_id}[\"{label}\"]")
            lines.append(f"    style {node_id} fill:#e1f5ff,stroke:#01579b")
        elif actor_type == 'script':
            # Script actors - hexagon
            label = f"{conv['name']}<br/>⚙️ {actor_name}"
            lines.append(f"    {node_id}{{\"{label}\"}}")
            lines.append(f"    style {node_id} fill:#fff3e0,stroke:#e65100")
        else:
            # Unknown - rectangle
            label = f"{conv['name']}<br/>{actor_name}"
            lines.append(f"    {node_id}[\"{label}\"]")
    
    lines.append("")
    
    # Generate edges for branches
    for conv in workflow_data['conversations']:
        current_node = f"C{conv['execution_order']}"
        
        branches = conv.get('branches', [])
        
        if not branches:
            # No branches - continue to next in sequence
            next_order = conv['execution_order'] + 1
            next_conv = next((c for c in workflow_data['conversations'] 
                            if c['execution_order'] == next_order), None)
            if next_conv:
                next_node = f"C{next_conv['execution_order']}"
                lines.append(f"    {current_node} --> {next_node}")
            else:
                # Last conversation
                lines.append(f"    {current_node} --> End([End])")
        else:
            # Process branches
            for branch in branches:
                condition = branch['condition']
                next_canonical = branch.get('next_conversation')
                
                if condition == 'TERMINAL' or not next_canonical:
                    # Terminal branch - translate condition for readability
                    if condition == '*':
                        clean_condition = "always"
                    else:
                        clean_condition = condition.replace('[', '').replace(']', '')
                    lines.append(f"    {current_node} -->|{clean_condition}| End([End])")
                else:
                    # Find next conversation node
                    next_conv = next((c for c in workflow_data['conversations'] 
                                    if c['canonical_name'] == next_canonical), None)
                    if next_conv:
                        next_node = f"C{next_conv['execution_order']}"
                        
                        # Format condition label - escape square brackets for Mermaid
                        if condition == '*':
                            label = "always"
                        else:
                            # Remove square brackets (Mermaid doesn't like them in labels)
                            label = condition.replace('[', '').replace(']', '')
                        
                        lines.append(f"    {current_node} -->|{label}| {next_node}")
    
    lines.append("")
    lines.append("```")
    
    return "\n".join(lines)


def generate_full_markdown(workflow_data: Dict[str, Any], mermaid_diagram: str) -> str:
    """Generate complete markdown document with diagram and metadata"""
    lines = []
    
    lines.append(f"# Workflow {workflow_data['workflow_id']}: {workflow_data['name']}")
    lines.append("")
    
    if workflow_data.get('description'):
        lines.append(f"**Description**: {workflow_data['description']}")
        lines.append("")
    
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Environment**: {workflow_data.get('environment', 'DEV')}")
    lines.append(f"- **Version**: {workflow_data.get('version', 1)}")
    lines.append(f"- **Enabled**: {workflow_data.get('enabled', False)}")
    lines.append(f"- **Total Conversations**: {len(workflow_data.get('conversations', []))}")
    lines.append("")
    
    lines.append("## Workflow Diagram")
    lines.append("")
    lines.append(mermaid_diagram)
    lines.append("")
    
    lines.append("## Conversations")
    lines.append("")
    
    for conv in workflow_data['conversations']:
        lines.append(f"### {conv['execution_order']}. {conv['name']}")
        lines.append("")
        lines.append(f"- **Canonical Name**: `{conv['canonical_name']}`")
        lines.append(f"- **Actor**: {conv['actor']['actor_name']} ({conv['actor']['actor_type']})")
        
        branches = conv.get('branches', [])
        if branches:
            lines.append(f"- **Branches**: {len(branches)}")
            for branch in branches:
                next_name = branch.get('next_conversation', 'TERMINAL')
                lines.append(f"  - `{branch['condition']}` → {next_name}")
        
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by tools/visualize_workflow.py*")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Mermaid flowchart diagrams from workflow definitions'
    )
    
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--workflow', type=int, help='Workflow ID (load from database)')
    source.add_argument('--file', type=Path, help='YAML file path')
    
    parser.add_argument('--output', type=Path, help='Output file path (default: stdout)')
    parser.add_argument('--diagram-only', action='store_true', 
                       help='Output only Mermaid diagram (no metadata)')
    
    args = parser.parse_args()
    
    # Load workflow data
    if args.workflow:
        workflow_data = load_workflow_from_db(args.workflow)
    else:
        workflow_data = load_workflow_from_yaml(args.file)
    
    # Generate diagram
    mermaid_diagram = generate_mermaid_diagram(workflow_data)
    
    # Generate output
    if args.diagram_only:
        output = mermaid_diagram
    else:
        output = generate_full_markdown(workflow_data, mermaid_diagram)
    
    # Write output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"✓ Diagram written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
