#!/usr/bin/env python3
"""
Automated QA Script for Workflow 3001
Runs comprehensive quality checks and stores findings in database.
Can be scheduled as a cron job or run manually.

Usage:
    # Run QA on all postings from latest workflow run
    python3 qa_automated_check.py
    
    # Run QA on specific workflow run
    python3 qa_automated_check.py --workflow-run 42
    
    # Run QA on recent postings (last N hours)
    python3 qa_automated_check.py --recent-hours 24
    
    # Skip database storage (dry run)
    python3 qa_automated_check.py --dry-run
    
    # Custom sample sizes
    python3 qa_automated_check.py --random-samples 10 --length-outliers 3
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from qa_check_hallucinations import PATTERNS


def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(
        dbname="turing",
        user="base_admin",
        password="base_yoga_secure_2025",
        host="localhost",
        port=5432
    )


def create_qa_run(conn, description="Automated QA check"):
    """Create a new QA run and return its ID."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO qa_runs (run_started_at, description)
            VALUES (NOW(), %s)
            RETURNING qa_run_id
        """, (description,))
        qa_run_id = cur.fetchone()[0]
        conn.commit()
        return qa_run_id


def finalize_qa_run(conn, qa_run_id, total_findings, high_severity, postings_affected):
    """Update QA run with final statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE qa_runs
            SET run_completed_at = NOW(),
                total_findings = %s,
                high_severity = %s,
                postings_affected = %s
            WHERE qa_run_id = %s
        """, (total_findings, high_severity, postings_affected, qa_run_id))
        conn.commit()


def get_postings_to_check(conn, workflow_run=None, recent_hours=None):
    """
    Get posting IDs to check based on criteria.
    
    Args:
        workflow_run: Ignored (kept for compatibility)
        recent_hours: Check postings from last N hours
        
    Returns:
        List of posting IDs
    """
    with conn.cursor() as cur:
        if recent_hours:
            # Check recent postings
            cutoff = datetime.now() - timedelta(hours=recent_hours)
            cur.execute("""
                SELECT posting_id
                FROM postings
                WHERE summary_extracted_at >= %s
                  AND extracted_summary IS NOT NULL
                  AND extracted_summary != ''
                ORDER BY posting_id
            """, (cutoff,))
        else:
            # Check all postings with summaries
            cur.execute("""
                SELECT posting_id
                FROM postings
                WHERE extracted_summary IS NOT NULL
                  AND extracted_summary != ''
                ORDER BY posting_id
            """)
        
        return [row[0] for row in cur.fetchall()]


def check_hallucinations(conn, qa_run_id, posting_ids):
    """Check for hallucination patterns in summaries."""
    findings = []
    
    with conn.cursor() as cur:
        for posting_id in posting_ids:
            cur.execute("""
                SELECT extracted_summary
                FROM postings
                WHERE posting_id = %s
                LIMIT 1
            """, (posting_id,))
            
            row = cur.fetchone()
            if not row or not row[0]:
                continue
                
            summary = row[0]
            
            # Check each hallucination pattern
            for pattern_name, category, check_fn, severity, description in PATTERNS:
                if check_fn(summary):
                    findings.append({
                        'qa_run_id': qa_run_id,
                        'posting_id': posting_id,
                        'check_type': 'hallucination',
                        'severity': severity,
                        'pattern_matched': pattern_name,
                        'description': description,
                        'field_name': 'extracted_summary',
                        'metric_value': None
                    })
    
    return findings


def check_length_outliers(conn, qa_run_id, posting_ids, top_n=5):
    """Find shortest and longest summaries."""
    findings = []
    
    with conn.cursor() as cur:
        # Shortest summaries
        cur.execute("""
            SELECT posting_id, LENGTH(extracted_summary) as len
            FROM postings
            WHERE posting_id = ANY(%s)
              AND extracted_summary IS NOT NULL
            ORDER BY len ASC
            LIMIT %s
        """, (posting_ids, top_n))
        
        for posting_id, length in cur.fetchall():
            findings.append({
                'qa_run_id': qa_run_id,
                'posting_id': posting_id,
                'check_type': 'length_outlier',
                'severity': 'low' if length > 500 else 'medium',
                'pattern_matched': 'shortest_summary',
                'description': f'Summary is unusually short ({length} chars)',
                'field_name': 'extracted_summary',
                'metric_value': float(length)
            })
        
        # Longest summaries
        cur.execute("""
            SELECT posting_id, LENGTH(extracted_summary) as len
            FROM postings
            WHERE posting_id = ANY(%s)
              AND extracted_summary IS NOT NULL
            ORDER BY len DESC
            LIMIT %s
        """, (posting_ids, top_n))
        
        for posting_id, length in cur.fetchall():
            # Flag extremely long summaries as high severity
            severity = 'high' if length > 20000 else 'medium'
            findings.append({
                'qa_run_id': qa_run_id,
                'posting_id': posting_id,
                'check_type': 'length_outlier',
                'severity': severity,
                'pattern_matched': 'longest_summary',
                'description': f'Summary is unusually long ({length} chars)',
                'field_name': 'extracted_summary',
                'metric_value': float(length)
            })
    
    return findings


def check_processing_time(conn, qa_run_id, posting_ids, top_n=5):
    """Find fastest and slowest processing times."""
    findings = []
    
    with conn.cursor() as cur:
        # Fastest postings
        cur.execute("""
            SELECT posting_id, 
                   EXTRACT(EPOCH FROM (summary_extracted_at - first_seen_at)) as seconds
            FROM postings
            WHERE posting_id = ANY(%s)
              AND summary_extracted_at IS NOT NULL
              AND first_seen_at IS NOT NULL
            ORDER BY seconds ASC
            LIMIT %s
        """, (posting_ids, top_n))
        
        for posting_id, seconds in cur.fetchall():
            findings.append({
                'qa_run_id': qa_run_id,
                'posting_id': posting_id,
                'check_type': 'processing_time',
                'severity': 'info',
                'pattern_matched': 'fastest_processing',
                'description': f'Processed very quickly ({seconds:.0f}s)',
                'field_name': 'processing_time',
                'metric_value': float(seconds)
            })
        
        # Slowest postings
        cur.execute("""
            SELECT posting_id,
                   EXTRACT(EPOCH FROM (summary_extracted_at - first_seen_at)) as seconds
            FROM postings
            WHERE posting_id = ANY(%s)
              AND summary_extracted_at IS NOT NULL
              AND first_seen_at IS NOT NULL
            ORDER BY seconds DESC
            LIMIT %s
        """, (posting_ids, top_n))
        
        for posting_id, seconds in cur.fetchall():
            # Flag very slow processing as high severity
            severity = 'high' if seconds > 3600 else 'medium'  # >1 hour
            findings.append({
                'qa_run_id': qa_run_id,
                'posting_id': posting_id,
                'check_type': 'processing_time',
                'severity': severity,
                'pattern_matched': 'slowest_processing',
                'description': f'Processed very slowly ({seconds:.0f}s)',
                'field_name': 'processing_time',
                'metric_value': float(seconds)
            })
    
    return findings


def check_random_samples(conn, qa_run_id, posting_ids, sample_size=5):
    """Select random postings for manual review."""
    findings = []
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id
            FROM postings
            WHERE posting_id = ANY(%s)
            ORDER BY RANDOM()
            LIMIT %s
        """, (posting_ids, sample_size))
        
        for (posting_id,) in cur.fetchall():
            findings.append({
                'qa_run_id': qa_run_id,
                'posting_id': posting_id,
                'check_type': 'random_sample',
                'severity': 'info',
                'pattern_matched': 'random_selection',
                'description': 'Selected for manual quality review',
                'field_name': None,
                'metric_value': None
            })
    
    return findings


def insert_findings(conn, findings):
    """Bulk insert QA findings into database."""
    if not findings:
        return
    
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO qa_findings 
            (qa_run_id, posting_id, check_type, severity, pattern_matched,
             description, field_name, metric_value)
            VALUES %s
        """, [
            (f['qa_run_id'], f['posting_id'], f['check_type'], f['severity'],
             f['pattern_matched'], f['description'], f['field_name'], f['metric_value'])
            for f in findings
        ])
        conn.commit()


def get_posting_details(conn, posting_id):
    """Fetch job_description and extracted_summary for a posting."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_description, extracted_summary,
                   LENGTH(job_description) as desc_len,
                   LENGTH(extracted_summary) as summary_len
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        if row:
            return {
                'job_description': row[0] or '',
                'extracted_summary': row[1] or '',
                'desc_len': row[2] or 0,
                'summary_len': row[3] or 0
            }
        return None


def generate_markdown_report(findings, output_path, qa_run_id, description, dry_run=False, conn=None):
    """Generate detailed markdown report with full posting data."""
    from datetime import datetime
    
    total = len(findings)
    by_severity = {}
    by_type = {}
    affected_postings = set()
    
    for f in findings:
        severity = f['severity']
        check_type = f['check_type']
        posting_id = f['posting_id']
        
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[check_type] = by_type.get(check_type, 0) + 1
        affected_postings.add(posting_id)
    
    report = []
    report.append(f"# QA Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(f"**Description:** {description}")
    if not dry_run:
        report.append(f"**QA Run ID:** {qa_run_id}")
    report.append(f"**Mode:** {'DRY RUN (not saved to database)' if dry_run else 'LIVE (saved to database)'}")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(f"- **Total findings:** {total}")
    report.append(f"- **Postings affected:** {len(affected_postings)}")
    report.append("")
    report.append("### Findings by Severity")
    report.append("")
    for severity in ['high', 'medium', 'low', 'info']:
        count = by_severity.get(severity, 0)
        emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢', 'info': '🔵'}.get(severity, '⚪')
        report.append(f"- {emoji} **{severity.upper()}**: {count}")
    report.append("")
    report.append("### Findings by Check Type")
    report.append("")
    for check_type, count in sorted(by_type.items()):
        report.append(f"- **{check_type}**: {count}")
    report.append("")
    
    # Critical findings section
    critical = [f for f in findings if f['severity'] == 'high']
    if critical:
        report.append("## 🔴 Critical Findings (severity=high)")
        report.append("")
        report.append("| Posting ID | Check Type | Pattern | Description | Metric |")
        report.append("|------------|------------|---------|-------------|--------|")
        for f in critical:
            metric = f"{f['metric_value']:.0f}" if f['metric_value'] else "-"
            report.append(f"| {f['posting_id']} | {f['check_type']} | {f['pattern_matched']} | {f['description']} | {metric} |")
        report.append("")
    
    # All findings by severity
    for severity in ['high', 'medium', 'low', 'info']:
        severity_findings = [f for f in findings if f['severity'] == severity]
        if severity_findings:
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢', 'info': '🔵'}.get(severity, '⚪')
            report.append(f"## {emoji} {severity.upper()} Severity Findings")
            report.append("")
            report.append("| Posting ID | Check Type | Pattern | Description | Metric |")
            report.append("|------------|------------|---------|-------------|--------|")
            for f in severity_findings:
                metric = f"{f['metric_value']:.0f}" if f['metric_value'] else "-"
                report.append(f"| {f['posting_id']} | {f['check_type']} | {f['pattern_matched']} | {f['description']} | {metric} |")
            report.append("")
    
    # Detailed posting data for review
    if conn:
        report.append("---")
        report.append("")
        report.append("## 📋 Posting Details for Review")
        report.append("")
        
        # Get unique posting IDs from findings, sorted
        posting_ids = sorted(set(f['posting_id'] for f in findings))
        
        for posting_id in posting_ids:
            details = get_posting_details(conn, posting_id)
            if not details:
                continue
            
            # Get all findings for this posting
            posting_findings = [f for f in findings if f['posting_id'] == posting_id]
            
            report.append(f"### Posting {posting_id}")
            report.append("")
            
            # Show findings for this posting
            report.append("**Findings:**")
            for f in posting_findings:
                severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢', 'info': '🔵'}.get(f['severity'], '⚪')
                metric = f" ({f['metric_value']:.0f})" if f['metric_value'] else ""
                report.append(f"- {severity_emoji} [{f['severity'].upper()}] {f['check_type']}: {f['description']}{metric}")
            report.append("")
            
            # Calculate expansion ratio
            desc_len = details['desc_len']
            summary_len = details['summary_len']
            expansion_ratio = summary_len / desc_len if desc_len > 0 else 0
            
            report.append(f"**Length:** Job description: {desc_len:,} chars → Summary: {summary_len:,} chars (ratio: {expansion_ratio:.2f}x)")
            
            # Warn about suspicious ratios
            if expansion_ratio > 3:
                report.append(f"⚠️ **WARNING:** Expansion ratio >3x suggests potential hallucination/contamination")
            elif expansion_ratio < 0.3 and summary_len > 0:
                report.append(f"⚠️ **WARNING:** Expansion ratio <0.3x suggests potential truncation/data loss")
            
            report.append("")
            
            # Show job description
            report.append("#### Job Description")
            report.append("```")
            report.append(details['job_description'])
            report.append("```")
            report.append("")
            
            # Show extracted summary
            report.append("#### Extracted Summary")
            report.append("```")
            report.append(details['extracted_summary'])
            report.append("```")
            report.append("")
            report.append("---")
            report.append("")
    
    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    return output_path


def print_summary(findings, dry_run=False):
    """Print QA check summary."""
    total = len(findings)
    by_severity = {}
    by_type = {}
    affected_postings = set()
    
    for f in findings:
        severity = f['severity']
        check_type = f['check_type']
        posting_id = f['posting_id']
        
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[check_type] = by_type.get(check_type, 0) + 1
        affected_postings.add(posting_id)
    
    print("\n" + "="*80)
    print("QA CHECK SUMMARY")
    print("="*80)
    print(f"Mode: {'DRY RUN (not saved to database)' if dry_run else 'LIVE (saved to database)'}")
    print(f"Total findings: {total}")
    print(f"Postings affected: {len(affected_postings)}")
    print()
    
    print("Findings by severity:")
    for severity in ['high', 'medium', 'low', 'info']:
        count = by_severity.get(severity, 0)
        if count > 0:
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢', 'info': '🔵'}.get(severity, '⚪')
            print(f"  {emoji} {severity.upper()}: {count}")
    print()
    
    print("Findings by check type:")
    for check_type, count in sorted(by_type.items()):
        print(f"  {check_type}: {count}")
    print()
    
    # Show critical findings
    critical = [f for f in findings if f['severity'] == 'high']
    if critical:
        print("🔴 CRITICAL FINDINGS (severity=high):")
        for f in critical[:10]:  # Show first 10
            print(f"  Posting {f['posting_id']}: {f['description']}")
        if len(critical) > 10:
            print(f"  ... and {len(critical) - 10} more")
        print()
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='Automated QA for Workflow 3001')
    parser.add_argument('--workflow-run', type=int, help='Check specific workflow run ID')
    parser.add_argument('--recent-hours', type=int, help='Check postings from last N hours')
    parser.add_argument('--random-samples', type=int, default=5, help='Number of random samples')
    parser.add_argument('--length-outliers', type=int, default=5, help='Number of length outliers')
    parser.add_argument('--time-outliers', type=int, default=5, help='Number of time outliers')
    parser.add_argument('--dry-run', action='store_true', help='Skip database storage')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--output', type=str, help='Output markdown report to file (default: logs/qa_report_YYYYMMDD_HHMMSS.md)')
    parser.add_argument('--no-report', action='store_true', help='Skip markdown report generation')
    
    args = parser.parse_args()
    
    try:
        conn = get_db_connection()
        
        # Determine what to check
        if args.recent_hours:
            description = f"Automated QA for postings from last {args.recent_hours} hours"
        else:
            description = "Automated QA for all postings with summaries"
        
        if not args.quiet:
            print(f"Starting QA check: {description}")
            print(f"Dry run: {args.dry_run}")
        
        # Get postings to check
        posting_ids = get_postings_to_check(conn, args.workflow_run, args.recent_hours)
        
        if not posting_ids:
            print("❌ No postings found to check")
            return 1
        
        if not args.quiet:
            print(f"Checking {len(posting_ids)} postings...")
        
        # Create QA run (even for dry run, to get an ID)
        qa_run_id = create_qa_run(conn, description) if not args.dry_run else 0
        
        # Run all checks
        all_findings = []
        
        if not args.quiet:
            print("  Checking hallucination patterns...")
        all_findings.extend(check_hallucinations(conn, qa_run_id, posting_ids))
        
        if not args.quiet:
            print("  Checking length outliers...")
        all_findings.extend(check_length_outliers(conn, qa_run_id, posting_ids, args.length_outliers))
        
        if not args.quiet:
            print("  Checking processing times...")
        all_findings.extend(check_processing_time(conn, qa_run_id, posting_ids, args.time_outliers))
        
        if not args.quiet:
            print("  Selecting random samples...")
        all_findings.extend(check_random_samples(conn, qa_run_id, posting_ids, args.random_samples))
        
        # Calculate statistics
        high_severity = sum(1 for f in all_findings if f['severity'] == 'high')
        affected_postings = len(set(f['posting_id'] for f in all_findings))
        
        # Store findings
        if not args.dry_run:
            if not args.quiet:
                print("  Saving findings to database...")
            insert_findings(conn, all_findings)
            finalize_qa_run(conn, qa_run_id, len(all_findings), high_severity, affected_postings)
            if not args.quiet:
                print(f"  ✅ Saved as QA run #{qa_run_id}")
        
        # Generate markdown report (unless disabled)
        if not args.no_report:
            if args.output:
                report_path = args.output
            else:
                # Default: logs/qa_report_YYYYMMDD_HHMMSS.md
                from pathlib import Path
                logs_dir = Path(__file__).parent.parent / 'logs'
                logs_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_path = logs_dir / f'qa_report_{timestamp}.md'
            
            generate_markdown_report(all_findings, report_path, qa_run_id, description, args.dry_run, conn)
            if not args.quiet:
                print(f"📄 Report saved: {report_path}")
        
        # Print summary
        if not args.quiet:
            print_summary(all_findings, args.dry_run)
        
        # Exit with error code if critical findings
        if high_severity > 0:
            if not args.quiet:
                print(f"⚠️  WARNING: {high_severity} critical findings detected")
            return 2  # Non-zero exit for alerting
        
        if not args.quiet:
            print("✅ QA check completed successfully")
        return 0
        
    except Exception as e:
        print(f"❌ Error during QA check: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == '__main__':
    sys.exit(main())
