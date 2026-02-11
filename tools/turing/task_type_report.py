#!/usr/bin/env python3
"""
Task Type Reporter - Generate MD report for any task type

Shows everything needed to debug/review a task type:
- Task type config
- Instruction template
- Actor code (if thick actor)
- Recent tickets samples
- RAQ config

Usage:
    python3 tools/turing/task_type_report.py lily_cps_extract
    python3 tools/turing/task_type_report.py 9383  # by ID
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw, return_connection


def get_task_type(conn, identifier: str) -> dict:
    """Get task type by name or ID."""
    cur = conn.cursor()
    
    # Try by ID first
    if identifier.isdigit():
        cur.execute("SELECT * FROM task_types WHERE task_type_id = %s", (int(identifier),))
    else:
        # Try by name (fuzzy match)
        cur.execute("""
            SELECT * FROM task_types 
            WHERE LOWER(REPLACE(task_type_name, ' ', '_')) LIKE LOWER(%s)
               OR LOWER(task_type_name) LIKE LOWER(%s)
            LIMIT 1
        """, (f"%{identifier}%", f"%{identifier}%"))
    
    row = cur.fetchone()
    return dict(row) if row else None


def get_instruction(conn, instruction_id: int) -> dict:
    """Get instruction by ID."""
    if not instruction_id:
        return None
    cur = conn.cursor()
    cur.execute("SELECT * FROM instructions WHERE instruction_id = %s", (instruction_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_actor_code(actor_type: str) -> str:
    """Try to find actor code file."""
    if not actor_type:
        return None
    
    # Convert to filename
    filename = actor_type.replace('-', '_').replace(' ', '_').lower() + '.py'
    
    # Check common locations (updated 2026-01-22)
    locations = [
        PROJECT_ROOT / 'actors' / filename,
    ]
    
    for path in locations:
        if path.exists():
            return path.read_text()
    
    return None


def get_recent_logs(conn, task_type_id: int, limit: int = 5) -> list:
    """Get recent tickets for this task type."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ticket_id, subject_id, status, consistency,
               created_at, completed_at,
               SUBSTRING(output::text, 1, 500) as output_preview
        FROM tickets
        WHERE task_type_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (task_type_id, limit))
    return [dict(row) for row in cur.fetchall()]


def get_stats(conn, task_type_id: int) -> dict:
    """Get stats for this task type."""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'running') as running,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as avg_duration_sec
        FROM tickets
        WHERE task_type_id = %s
    """, (task_type_id,))
    return dict(cur.fetchone())


def generate_report(identifier: str) -> str:
    """Generate full MD report for a task type."""
    conn = get_connection_raw()
    
    try:
        # Get task type
        tt = get_task_type(conn, identifier)
        if not tt:
            return f"❌ Task type not found: {identifier}"
        
        # Get related data
        instruction = get_instruction(conn, tt.get('instruction_id'))
        actor_code = get_actor_code(tt.get('actor_type'))
        recent_logs = get_recent_logs(conn, tt['task_type_id'])
        stats = get_stats(conn, tt['task_type_id'])
        
        # Build report
        lines = []
        lines.append(f"# Task Type Report: {tt['task_type_name']}")
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Task Type ID:** {tt['task_type_id']}")
        
        # Overview
        lines.append("\n## Overview\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Name | {tt['task_type_name']} |")
        lines.append(f"| Actor Type | {tt.get('actor_type', 'N/A')} |")
        lines.append(f"| Instruction ID | {tt.get('instruction_id', 'N/A')} |")
        lines.append(f"| Model | {tt.get('requires_model', 'N/A')} |")
        lines.append(f"| Temperature | {tt.get('llm_temperature', 'N/A')} |")
        lines.append(f"| Seed | {tt.get('llm_seed', 'N/A')} |")
        lines.append(f"| Enabled | {tt.get('enabled', False)} |")
        
        # Stats
        lines.append("\n## Statistics\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Runs | {stats['total']} |")
        lines.append(f"| Completed | {stats['completed']} |")
        lines.append(f"| Failed | {stats['failed']} |")
        lines.append(f"| Pending | {stats['pending']} |")
        lines.append(f"| Avg Duration | {stats['avg_duration_sec']:.1f}s |" if stats['avg_duration_sec'] else "| Avg Duration | N/A |")
        
        # Work Query
        if tt.get('work_query'):
            lines.append("\n## Work Query\n")
            lines.append("```sql")
            lines.append(tt['work_query'])
            lines.append("```")
        
        # Instruction Template
        if instruction:
            lines.append(f"\n## Instruction Template (ID: {instruction['instruction_id']})\n")
            lines.append(f"**Name:** {instruction.get('instruction_name', 'N/A')}")
            lines.append("\n### Input Template\n")
            lines.append("```")
            lines.append(instruction.get('input_template', '(empty)'))
            lines.append("```")
        
        # RAQ Config
        if tt.get('raq_config'):
            lines.append("\n## RAQ Config\n")
            lines.append("```json")
            import json
            lines.append(json.dumps(tt['raq_config'], indent=2))
            lines.append("```")
        
        # Actor Code
        if actor_code:
            lines.append(f"\n## Actor Code\n")
            lines.append(f"**File:** `actors/{tt.get('actor_type', 'unknown').replace('-', '_')}.py`")
            lines.append("\n```python")
            # Truncate if too long
            if len(actor_code) > 5000:
                lines.append(actor_code[:5000])
                lines.append("\n# ... (truncated)")
            else:
                lines.append(actor_code)
            lines.append("```")
        
        # Recent Logs
        if recent_logs:
            lines.append("\n## Recent Task Logs\n")
            lines.append("| ID | Subject | Status | Consistency | Duration |")
            lines.append("|-----|---------|--------|-------------|----------|")
            for log in recent_logs:
                duration = ""
                if log.get('completed_at') and log.get('created_at'):
                    try:
                        d = (log['completed_at'] - log['created_at']).total_seconds()
                        duration = f"{d:.1f}s"
                    except (KeyError, TypeError, AttributeError):
                        pass
                lines.append(f"| {log['ticket_id']} | {log.get('subject_id', 'N/A')} | {log['status']} | {log.get('consistency', '1/1')} | {duration} |")
        
        return "\n".join(lines)
        
    finally:
        return_connection(conn)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 task_type_report.py <task_type_name_or_id>")
        print("\nExamples:")
        print("  python3 task_type_report.py lily_cps_extract")
        print("  python3 task_type_report.py 9383")
        sys.exit(1)
    
    identifier = sys.argv[1]
    report = generate_report(identifier)
    
    # Output to stdout or file
    if len(sys.argv) > 2 and sys.argv[2] == '--save':
        filename = f"reports/task_type_{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        Path(filename).parent.mkdir(exist_ok=True)
        Path(filename).write_text(report)
        print(f"✅ Report saved: {filename}")
    else:
        print(report)


if __name__ == '__main__':
    main()
