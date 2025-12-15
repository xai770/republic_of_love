#!/usr/bin/env python3
"""
Validate Workflow
=================

Validates workflow definitions for common issues:
- Dead-end branches (unreachable conversations)
- Missing error branches ([FAILED], [TIMEOUT], [ERROR])
- Circular dependencies
- Invalid conversation references
- Orphaned conversations

Usage:
    # Validate from database
    python3 tools/validate_workflow.py --workflow 3001
    
    # Validate from YAML
    python3 tools/validate_workflow.py --file workflows/3001_job_processing.yaml
    
    # Validate all PROD workflows
    python3 tools/validate_workflow.py --environment PROD

Exit codes:
    0 - No issues found
    1 - Warnings found
    2 - Errors found

Author: Arden
Date: 2025-11-13
"""

import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

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


class WorkflowValidator:
    """Validates workflow definitions"""
    
    def __init__(self, workflow_data: Dict[str, Any]):
        self.workflow_data = workflow_data
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
        # Build lookup maps
        self.conversations_by_canonical = {
            c['canonical_name']: c 
            for c in workflow_data.get('conversations', [])
        }
        self.conversations_by_id = {
            c['conversation_id']: c 
            for c in workflow_data.get('conversations', [])
        }
    
    def validate(self) -> Tuple[int, int, int]:
        """
        Run all validation checks
        
        Returns:
            (error_count, warning_count, info_count)
        """
        self.check_reachability()
        self.check_error_branches()
        self.check_branch_references()
        self.check_circular_dependencies()
        self.check_terminal_conversations()
        self.check_actor_availability()
        self.check_disabled_conversation_branches()  # NEW: Catches KeyError 9186 type issues
        
        return (len(self.errors), len(self.warnings), len(self.info))
    
    def check_reachability(self):
        """Check that all conversations are reachable from start"""
        reachable = set()
        
        # Start with first conversation
        conversations = self.workflow_data.get('conversations', [])
        if not conversations:
            self.errors.append("No conversations defined in workflow")
            return
        
        first_conv = min(conversations, key=lambda c: c['execution_order'])
        to_visit = [first_conv['canonical_name']]
        
        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue
            
            reachable.add(current)
            
            # Find all branches from this conversation
            conv = self.conversations_by_canonical.get(current)
            if not conv:
                continue
            
            for branch in conv.get('branches', []):
                next_conv = branch.get('next_conversation')
                if next_conv and next_conv != 'TERMINAL':
                    to_visit.append(next_conv)
        
        # Check for unreachable conversations
        all_conversations = set(self.conversations_by_canonical.keys())
        unreachable = all_conversations - reachable
        
        if unreachable:
            for conv_name in sorted(unreachable):
                self.warnings.append(
                    f"Unreachable conversation: {conv_name} "
                    f"(execution_order {self.conversations_by_canonical[conv_name]['execution_order']})"
                )
    
    def check_error_branches(self):
        """Check that error states have matching branches"""
        error_states = ['[FAILED]', '[TIMEOUT]', '[ERROR]', '[RATE_LIMITED]']
        
        for conv in self.workflow_data.get('conversations', []):
            branches = conv.get('branches', [])
            if not branches:
                continue
            
            branch_conditions = [b['condition'] for b in branches]
            
            # Check if there's a wildcard (catches everything)
            has_wildcard = '*' in branch_conditions
            
            if not has_wildcard:
                # Check each error state
                for error_state in error_states:
                    if error_state not in branch_conditions:
                        # Only warn about FAILED and TIMEOUT (most common)
                        if error_state in ['[FAILED]', '[TIMEOUT]']:
                            self.warnings.append(
                                f"{conv['canonical_name']}: Missing error branch '{error_state}' "
                                f"(conversation will terminate silently on error)"
                            )
    
    def check_branch_references(self):
        """Check that branch next_conversation references are valid"""
        for conv in self.workflow_data.get('conversations', []):
            for branch in conv.get('branches', []):
                next_conv = branch.get('next_conversation')
                
                if not next_conv or next_conv == 'TERMINAL':
                    continue
                
                # Check if referenced conversation exists
                if next_conv not in self.conversations_by_canonical:
                    self.errors.append(
                        f"{conv['canonical_name']}: Branch '{branch['condition']}' "
                        f"references undefined conversation '{next_conv}'"
                    )
    
    def check_circular_dependencies(self):
        """Check for circular dependencies (infinite loops)"""
        for conv in self.workflow_data.get('conversations', []):
            visited = set()
            path = []
            
            if self._has_cycle(conv['canonical_name'], visited, path):
                cycle_str = " → ".join(path + [path[0]])
                self.info.append(
                    f"Potential loop detected: {cycle_str} "
                    f"(this may be intentional for retry logic)"
                )
    
    def _has_cycle(self, conv_name: str, visited: Set[str], path: List[str]) -> bool:
        """Helper for cycle detection"""
        if conv_name in path:
            return True
        
        if conv_name in visited:
            return False
        
        visited.add(conv_name)
        path.append(conv_name)
        
        conv = self.conversations_by_canonical.get(conv_name)
        if not conv:
            return False
        
        for branch in conv.get('branches', []):
            next_conv = branch.get('next_conversation')
            if next_conv and next_conv != 'TERMINAL':
                # Check max_iterations to see if loop is bounded
                max_iter = branch.get('max_iterations')
                if max_iter:
                    continue  # Bounded loop, ok
                
                if self._has_cycle(next_conv, visited, path[:]):
                    return True
        
        return False
    
    def check_terminal_conversations(self):
        """Check that workflow has proper termination"""
        has_terminal = False
        
        for conv in self.workflow_data.get('conversations', []):
            branches = conv.get('branches', [])
            
            if not branches:
                # No branches = terminal
                has_terminal = True
                continue
            
            for branch in branches:
                if branch['condition'] == 'TERMINAL' or not branch.get('next_conversation'):
                    has_terminal = True
                    break
        
        if not has_terminal:
            self.warnings.append(
                "No terminal branches found - workflow may never complete"
            )
    
    def check_actor_availability(self):
        """Check that referenced actors exist in database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT actor_id, actor_name, enabled FROM actors")
        actors = {row['actor_id']: row for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        for conv in self.workflow_data.get('conversations', []):
            actor_id = conv['actor']['actor_id']
            
            if actor_id not in actors:
                self.errors.append(
                    f"{conv['canonical_name']}: References undefined actor_id {actor_id}"
                )
            elif not actors[actor_id]['enabled']:
                self.warnings.append(
                    f"{conv['canonical_name']}: Uses disabled actor '{actors[actor_id]['actor_name']}'"
                )
    
    def check_disabled_conversation_branches(self):
        """Check that branches don't point to disabled conversations in workflow"""
        workflow_id = self.workflow_data.get('workflow_id')
        if not workflow_id:
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all conversations in this workflow (enabled and disabled)
        cursor.execute("""
            SELECT 
                wc.conversation_id,
                c.canonical_name,
                wc.enabled,
                wc.execution_order
            FROM workflow_conversations wc
            JOIN conversations c ON c.conversation_id = wc.conversation_id
            WHERE wc.workflow_id = %s
        """, (workflow_id,))
        
        all_convs = {row['conversation_id']: row for row in cursor.fetchall()}
        enabled_conv_ids = {
            cid for cid, data in all_convs.items() if data['enabled']
        }
        
        # Check all instruction branches
        cursor.execute("""
            SELECT 
                c.canonical_name as source_conversation,
                ist.branch_condition,
                ist.next_conversation_id,
                wc_target.enabled as target_enabled,
                c_target.canonical_name as target_name
            FROM instructions i
            JOIN conversations c ON c.conversation_id = i.conversation_id
            JOIN workflow_conversations wc_source ON wc_source.conversation_id = c.conversation_id
            JOIN instruction_steps ist ON ist.instruction_id = i.instruction_id
            LEFT JOIN workflow_conversations wc_target 
                ON wc_target.conversation_id = ist.next_conversation_id
                AND wc_target.workflow_id = %s
            LEFT JOIN conversations c_target ON c_target.conversation_id = ist.next_conversation_id
            WHERE wc_source.workflow_id = %s
              AND wc_source.enabled = TRUE
              AND ist.next_conversation_id IS NOT NULL
              AND ist.branch_condition != 'TERMINAL'
        """, (workflow_id, workflow_id))
        
        branches = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Check for branches to disabled conversations
        for branch in branches:
            target_id = branch['next_conversation_id']
            
            if target_id not in enabled_conv_ids:
                status = "DISABLED" if branch['target_enabled'] is False else "NOT IN WORKFLOW"
                self.errors.append(
                    f"{branch['source_conversation']}: Branch '{branch['branch_condition']}' → "
                    f"conversation {target_id} ({branch['target_name']}) is {status}"
                )
    
    def print_report(self):
        """Print validation report"""
        workflow_name = self.workflow_data.get('name', 'Unknown')
        workflow_id = self.workflow_data.get('workflow_id', '?')
        
        print(f"\n{'='*80}")
        print(f"Workflow {workflow_id}: {workflow_name}")
        print(f"{'='*80}\n")
        
        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
            print()
        
        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if self.info:
            print(f"ℹ️  INFO ({len(self.info)}):")
            for info_msg in self.info:
                print(f"  - {info_msg}")
            print()
        
        if not self.errors and not self.warnings and not self.info:
            print("✅ No issues found - workflow is valid!\n")


def main():
    parser = argparse.ArgumentParser(
        description='Validate workflow definitions for common issues'
    )
    
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--workflow', type=int, help='Workflow ID (load from database)')
    source.add_argument('--file', type=Path, help='YAML file path')
    source.add_argument('--environment', choices=['DEV', 'UAT', 'PROD', 'OLD'],
                       help='Validate all workflows in environment')
    
    args = parser.parse_args()
    
    # Determine which workflows to validate
    workflows = []
    
    if args.workflow:
        workflows.append(load_workflow_from_db(args.workflow))
    elif args.file:
        workflows.append(load_workflow_from_yaml(args.file))
    else:  # --environment
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT workflow_id 
            FROM workflows 
            WHERE environment = %s AND enabled = TRUE
            ORDER BY workflow_id
        """, (args.environment,))
        workflow_ids = [row['workflow_id'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        for wid in workflow_ids:
            workflows.append(load_workflow_from_db(wid))
    
    # Validate each workflow
    total_errors = 0
    total_warnings = 0
    total_info = 0
    
    for workflow_data in workflows:
        validator = WorkflowValidator(workflow_data)
        errors, warnings, info = validator.validate()
        validator.print_report()
        
        total_errors += errors
        total_warnings += warnings
        total_info += info
    
    # Summary
    if len(workflows) > 1:
        print(f"{'='*80}")
        print(f"Summary: {len(workflows)} workflows validated")
        print(f"  - {total_errors} errors")
        print(f"  - {total_warnings} warnings")
        print(f"  - {total_info} info messages")
        print(f"{'='*80}\n")
    
    # Exit code
    if total_errors > 0:
        sys.exit(2)
    elif total_warnings > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
