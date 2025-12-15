#!/usr/bin/env python3
"""
QA Finding Reviewer
===================

Interactive tool to review and resolve QA findings.

Usage:
    # Show all open findings
    python3 scripts/qa_review_findings.py
    
    # Show findings from specific run
    python3 scripts/qa_review_findings.py --qa-run 1
    
    # Show only high severity
    python3 scripts/qa_review_findings.py --severity high
    
    # Mark findings as reviewed
    python3 scripts/qa_review_findings.py --resolve 1,2,3 --status reviewed --notes "Confirmed OK"
    
    # Export findings for manual review
    python3 scripts/qa_review_findings.py --export findings.csv
"""

import sys
import os
import csv
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_connection, return_connection


def display_findings(findings: List[dict], show_evidence: bool = False):
    """Display findings in readable format"""
    
    if not findings:
        print("✅ No findings to display!")
        return
    
    print(f"\n{'='*100}")
    print(f"Found {len(findings)} QA findings")
    print(f"{'='*100}\n")
    
    for i, finding in enumerate(findings, 1):
        severity_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢',
            'info': 'ℹ️'
        }.get(finding['severity'], '⚪')
        
        print(f"{i}. {severity_emoji} Finding #{finding['finding_id']} - Posting {finding['posting_id']}")
        print(f"   Type: {finding['check_type']} ({finding['check_category'] or 'N/A'})")
        print(f"   Pattern: {finding['pattern_matched']}")
        print(f"   Severity: {finding['severity'].upper()}")
        print(f"   Status: {finding['status']}")
        print(f"   Description: {finding['description']}")
        
        if finding.get('metric_value'):
            print(f"   Metric: {finding['metric_value']}")
        
        if show_evidence and finding.get('evidence'):
            print(f"   Evidence: {finding['evidence'][:200]}...")
        
        if finding.get('reviewed_by'):
            print(f"   ✓ Reviewed by {finding['reviewed_by']} at {finding['reviewed_at']}")
            if finding.get('resolution_notes'):
                print(f"   Notes: {finding['resolution_notes']}")
        
        print()


def resolve_findings(finding_ids: List[int], status: str, reviewed_by: str, notes: Optional[str] = None):
    """Mark findings as resolved"""
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE qa_findings
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = NOW(),
                resolution_notes = %s
            WHERE finding_id = ANY(%s)
            RETURNING finding_id
        """, (status, reviewed_by, notes, finding_ids))
        
        updated = cur.fetchall()
        conn.commit()
        
        print(f"✅ Updated {len(updated)} findings:")
        for row in updated:
            print(f"   Finding #{row[0]} -> {status}")
        
        return_connection(conn)
    except Exception as e:
        conn.rollback()
        return_connection(conn)
        raise e


def export_findings(findings: List[dict], output_path: str):
    """Export findings to CSV"""
    
    if not findings:
        print("No findings to export")
        return
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=findings[0].keys())
        writer.writeheader()
        writer.writerows(findings)
    
    print(f"✅ Exported {len(findings)} findings to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Review and resolve QA findings')
    parser.add_argument('--qa-run', type=int, help='Filter by QA run ID')
    parser.add_argument('--severity', choices=['high', 'medium', 'low', 'info'], help='Filter by severity')
    parser.add_argument('--status', help='Filter by status (or use with --resolve to set status)')
    parser.add_argument('--check-type', help='Filter by check type')
    parser.add_argument('--posting-id', type=int, help='Show findings for specific posting')
    parser.add_argument('--show-evidence', action='store_true', help='Show evidence excerpts')
    parser.add_argument('--resolve', help='Comma-separated finding IDs to resolve')
    parser.add_argument('--reviewed-by', default='xai', help='Name of reviewer (default: xai)')
    parser.add_argument('--notes', help='Resolution notes')
    parser.add_argument('--export', help='Export findings to CSV file')
    args = parser.parse_args()
    
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        where_clauses = []
        params = []
        
        if args.qa_run:
            where_clauses.append("qa_run_id = %s")
            params.append(args.qa_run)
        
        if args.severity:
            where_clauses.append("severity = %s")
            params.append(args.severity)
        
        if args.status and not args.resolve:
            where_clauses.append("status = %s")
            params.append(args.status)
        elif not args.resolve:
            # Default: show only open findings
            where_clauses.append("status = 'open'")
        
        if args.check_type:
            where_clauses.append("check_type = %s")
            params.append(args.check_type)
        
        if args.posting_id:
            where_clauses.append("posting_id = %s")
            params.append(args.posting_id)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        cur.execute(f"""
            SELECT *
            FROM qa_findings
            WHERE {where_sql}
            ORDER BY 
                CASE severity 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                    ELSE 4 
                END,
                detected_at DESC
        """, params)
        
        findings = [dict(row) for row in cur.fetchall()]
        
        # Handle resolve action
        if args.resolve:
            finding_ids = [int(x.strip()) for x in args.resolve.split(',')]
            
            if not args.status:
                print("Error: --status required when using --resolve")
                sys.exit(1)
            
            resolve_findings(finding_ids, args.status, args.reviewed_by, args.notes)
        
        # Handle export
        elif args.export:
            export_findings(findings, args.export)
        
        # Display findings
        else:
            display_findings(findings, show_evidence=args.show_evidence)
        
        return_connection(conn)
    
    except Exception as e:
        return_connection(conn)
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
