#!/usr/bin/env python3
"""
turing_lint.py - Structural linter for Turing thick actors

GATEKEEPER: The pull_daemon checks lint_status before running any actor.
If an actor fails lint, it won't run in production (unless --force).

This checks:
- Required patterns exist (process, _owns_connection, etc.)
- Naming conventions match {table}__{attribute}_{CRUD}[__name].py
- Basic structure aligns with template

This does NOT check:
- Whether your QA logic is actually good
- Whether your preflight catches all edge cases
- Whether your LLM prompts are well-designed
- RAQ test coverage (that's a separate gate)

Usage:
    turing-lint                         # Audit all actors
    turing-lint --fix                   # Show suggested fixes
    turing-lint lucy                    # Audit specific actor
    turing-lint --register 9388         # Register lint status in DB for task 9388
    turing-lint --json                  # Machine-readable output

Gatekeeper Flow:
    1. Write code → 2. turing-lint --register TASK_ID → 3. RAQ tests → 4. Production

Author: Sandy (with contributions from Arden)
Date: 2026-01-21
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent
ACTORS_DIR = PROJECT_ROOT / 'actors'

# Add to path for database access
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# PATTERN CHECKS
# ============================================================================

REQUIRED_PATTERNS = {
    'process_method': {
        'pattern': r'def process\(self[,\)]',  # process(self) or process(self, ...)
        'description': 'process() method for daemon interface',
        'severity': 'error',
        'fix': 'Add def process(self) -> Dict[str, Any]: method that wraps your main logic',
    },
    'init_db_conn': {
        'pattern': r'def __init__\(self,\s*db_conn\s*=\s*None',
        'description': '__init__(self, db_conn=None) signature',
        'severity': 'error',
        'fix': 'Change __init__ to accept db_conn=None parameter',
    },
    'owns_connection': {
        'pattern': r'self\._owns_connection',
        'description': '_owns_connection tracking for connection lifecycle',
        'severity': 'error',
        'fix': '''Add to __init__:
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection()
            self._owns_connection = True''',
    },
    'input_data': {
        'pattern': r'self\.input_data',
        'description': 'input_data attribute for daemon to pass parameters',
        'severity': 'error',
        'fix': 'Add self.input_data: Dict[str, Any] = {} in __init__',
    },
    'destructor': {
        'pattern': r'def __del__\(self\)',
        'description': '__del__ for connection cleanup',
        'severity': 'warning',
        'fix': '''Add:
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()''',
    },
}

RECOMMENDED_PATTERNS = {
    'preflight': {
        'pattern': r'_preflight|preflight|# PREFLIGHT|PHASE 1',
        'description': 'Preflight validation phase',
        'severity': 'info',
        'note': 'Optional for passthrough actors (commit, arbitrator)',
    },
    'qa_check': {
        'pattern': r'_qa_check|qa_check|# QA|PHASE 3',
        'description': 'QA validation phase',
        'severity': 'info',
        'note': 'Optional for non-LLM actors',
    },
    'llm_settings': {
        'pattern': r'llm_temperature|llm_seed|_get_llm_settings',
        'description': 'LLM settings from database (not hardcoded)',
        'severity': 'warning',
        'note': 'Required for LLM actors per Directive #14',
    },
    'llm_calls_tracking': {
        'pattern': r'self\._llm_calls',
        'description': 'LLM call tracking for auditability',
        'severity': 'info',
        'note': 'Recommended for LLM actors',
    },
}

NAMING_PATTERN = re.compile(
    r'^(?P<table>\w+)__(?P<attribute>\w+)_(?P<crud>[CRUD]+)(?:__(?P<name>\w+))?\.py$'
)

# ============================================================================
# AUDIT FUNCTIONS
# ============================================================================

def audit_file(filepath: Path) -> Dict[str, Any]:
    """Audit a single actor file."""
    content = filepath.read_text()
    filename = filepath.name
    
    result = {
        'file': filename,
        'path': str(filepath),
        'errors': [],
        'warnings': [],
        'info': [],
        'passed': [],
    }
    
    # Check naming convention
    match = NAMING_PATTERN.match(filename)
    if not match:
        result['warnings'].append({
            'check': 'naming_convention',
            'message': f'Filename does not match {"{table}__{attribute}_{CRUD}[__name].py"} pattern',
        })
    else:
        result['naming'] = match.groupdict()
    
    # Check required patterns
    for name, check in REQUIRED_PATTERNS.items():
        if re.search(check['pattern'], content):
            result['passed'].append(name)
        else:
            severity = check['severity']
            issue = {
                'check': name,
                'description': check['description'],
                'fix': check.get('fix'),
            }
            if severity == 'error':
                result['errors'].append(issue)
            elif severity == 'warning':
                result['warnings'].append(issue)
    
    # Check if it's an LLM actor
    is_llm_actor = bool(re.search(r'ollama|call_llm|OLLAMA_URL|requests\.post', content, re.I))
    
    # Check recommended patterns
    for name, check in RECOMMENDED_PATTERNS.items():
        if re.search(check['pattern'], content):
            result['passed'].append(name)
        else:
            # LLM settings only matter for LLM actors
            if name == 'llm_settings' and not is_llm_actor:
                continue
            if name == 'llm_calls_tracking' and not is_llm_actor:
                continue
                
            severity = check['severity']
            issue = {
                'check': name,
                'description': check['description'],
                'note': check.get('note'),
            }
            if severity == 'warning':
                result['warnings'].append(issue)
            else:
                result['info'].append(issue)
    
    # Summary
    result['is_llm_actor'] = is_llm_actor
    result['score'] = len(result['passed']) / (len(REQUIRED_PATTERNS) + len(RECOMMENDED_PATTERNS))
    result['status'] = 'PASS' if not result['errors'] else 'FAIL'
    
    return result


def register_lint_status(task_type_id: int, actor_name: Optional[str] = None) -> Dict[str, Any]:
    """Register lint status for a task_type in the database.
    
    Returns:
        Dict with 'success', 'lint_passed', and 'errors'
    """
    from core.database import get_connection
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get task_type info
        cur.execute("""
            SELECT task_type_id, task_type_name, script_path, execution_type
            FROM task_types WHERE task_type_id = %s
        """, (task_type_id,))
        task = cur.fetchone()
        
        if not task:
            return {'success': False, 'error': f'Task type {task_type_id} not found'}
        
        # Lint only applies to thick actors (execution_type = 'thick' or 'script' with a script_path)
        if task['execution_type'] == 'thin' and not task['script_path']:
            return {
                'success': True,
                'lint_passed': True,
                'message': f"Task {task_type_id} is thin with no script, lint not required"
            }
        
        # Find the actor file
        script_path = task['script_path']
        if not script_path:
            # Try to find by actor name
            if actor_name:
                matches = list(ACTORS_DIR.glob(f'*{actor_name}*.py'))
            else:
                matches = []
            if not matches:
                return {'success': False, 'error': f'No script_path and no actor found for task {task_type_id}'}
            actor_file = matches[0]
        else:
            actor_file = PROJECT_ROOT / script_path
        
        if not actor_file.exists():
            return {'success': False, 'error': f'Actor file not found: {actor_file}'}
        
        # Run lint
        result = audit_file(actor_file)
        lint_passed = result['status'] == 'PASS'
        
        # Update database
        cur.execute("""
            UPDATE task_types SET
                lint_status = %s,
                lint_checked_at = NOW(),
                lint_errors = %s
            WHERE task_type_id = %s
        """, (
            'passed' if lint_passed else 'failed',
            json.dumps(result['errors']) if result['errors'] else None,
            task_type_id
        ))
        conn.commit()
        
        return {
            'success': True,
            'lint_passed': lint_passed,
            'task_type_id': task_type_id,
            'task_name': task['task_type_name'],
            'actor_file': str(actor_file),
            'errors': result['errors'],
            'warnings': result['warnings'],
        }

def print_report(results: List[Dict], verbose: bool = False, show_fixes: bool = False):
    """Print human-readable audit report."""
    total_errors = sum(len(r['errors']) for r in results)
    total_warnings = sum(len(r['warnings']) for r in results)
    
    print("=" * 60)
    print("THICK ACTOR AUDIT REPORT")
    print("=" * 60)
    print()
    
    # Summary table
    print(f"{'Actor':<45} {'Status':<8} {'Errors':<7} {'Warnings'}")
    print("-" * 70)
    
    for r in sorted(results, key=lambda x: (-len(x['errors']), x['file'])):
        status_icon = '✅' if r['status'] == 'PASS' else '❌'
        print(f"{r['file']:<45} {status_icon:<8} {len(r['errors']):<7} {len(r['warnings'])}")
    
    print("-" * 70)
    print(f"{'TOTAL':<45} {'':<8} {total_errors:<7} {total_warnings}")
    print()
    
    # Details for failures
    failures = [r for r in results if r['errors'] or (verbose and r['warnings'])]
    
    if failures:
        print("\n" + "=" * 60)
        print("ISSUES")
        print("=" * 60)
        
        for r in failures:
            if r['errors'] or (verbose and r['warnings']):
                print(f"\n📄 {r['file']}")
                
                for err in r['errors']:
                    print(f"  ❌ ERROR: {err['description']}")
                    if show_fixes and err.get('fix'):
                        print(f"     FIX: {err['fix'][:80]}...")
                
                if verbose:
                    for warn in r['warnings']:
                        print(f"  ⚠️  WARNING: {warn['description']}")
                        if warn.get('note'):
                            print(f"     Note: {warn['note']}")
    
    # Final summary
    print("\n" + "=" * 60)
    if total_errors == 0:
        print("✅ All actors pass required checks!")
    else:
        print(f"❌ {total_errors} errors need fixing")
        if show_fixes:
            print("\nRun with --fix to see suggested code changes")
    
    if total_warnings > 0 and not verbose:
        print(f"ℹ️  {total_warnings} warnings (use --verbose to see)")

def main():
    parser = argparse.ArgumentParser(description='Turing thick actor linter - gatekeeper for production')
    parser.add_argument('actor', nargs='?', help='Specific actor to audit (filename or partial name)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show warnings and info')
    parser.add_argument('--fix', '-f', action='store_true', help='Show suggested fixes')
    parser.add_argument('--json', '-j', action='store_true', help='JSON output')
    parser.add_argument('--register', '-r', type=int, metavar='TASK_ID',
                        help='Register lint status in database for task_type_id')
    args = parser.parse_args()
    
    # Database registration mode
    if args.register:
        result = register_lint_status(args.register, args.actor)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get('lint_passed'):
                print(f"✅ Lint PASSED for task {args.register}")
                print(f"   Actor: {result.get('actor_file', 'N/A')}")
                if result.get('warnings'):
                    print(f"   ⚠️  {len(result['warnings'])} warnings")
            else:
                print(f"❌ Lint FAILED for task {args.register}")
                if result.get('error'):
                    print(f"   Error: {result['error']}")
                for err in result.get('errors', []):
                    print(f"   ❌ {err['description']}")
        sys.exit(0 if result.get('lint_passed', False) or result.get('success', False) else 1)
    
    # Find actor files
    actor_files = list(ACTORS_DIR.glob('*.py'))
    actor_files = [f for f in actor_files if f.name != 'TEMPLATE_thick_actor.py' and not f.name.startswith('__')]
    
    # Filter if specific actor requested
    if args.actor:
        actor_files = [f for f in actor_files if args.actor.lower() in f.name.lower()]
        if not actor_files:
            print(f"No actor found matching '{args.actor}'")
            sys.exit(1)
    
    # Audit each file
    results = [audit_file(f) for f in actor_files]
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, verbose=args.verbose, show_fixes=args.fix)
    
    # Exit code: 1 if any errors
    has_errors = any(r['errors'] for r in results)
    sys.exit(1 if has_errors else 0)


if __name__ == '__main__':
    main()
