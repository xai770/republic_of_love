#!/usr/bin/env python3
"""
Comprehensive Data Quality Report
==================================

Multi-dimensional QA analysis for workflow 3001 job summaries.

Analysis dimensions:
1. Hallucinations (using existing patterns from qa_check_hallucinations.py)
2. Length outliers (shortest and longest summaries)
3. Random sampling for manual review
4. Processing time analysis (fastest and slowest postings)
5. LLM interaction patterns

Outputs:
- Stores findings in qa_findings table
- Generates human-readable report for review
- Provides statistics and actionable insights

Usage:
    python3 scripts/qa_comprehensive_report.py
    python3 scripts/qa_comprehensive_report.py --output report.txt
    python3 scripts/qa_comprehensive_report.py --skip-db  # Don't store in database
"""

import sys
import os
import random
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_connection, return_connection

# Import hallucination patterns
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from qa_check_hallucinations import PATTERNS, check_posting


class QAReport:
    """Comprehensive QA analysis and reporting"""
    
    def __init__(self, conn, store_in_db: bool = True):
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=RealDictCursor)
        self.store_in_db = store_in_db
        self.qa_run_id = None
        self.findings = []
        
        if store_in_db:
            # Create new QA run ID
            self.cur.execute("SELECT COALESCE(MAX(qa_run_id), 0) + 1 AS next_id FROM qa_findings")
            result = self.cur.fetchone()
            self.qa_run_id = result['next_id']
    
    def add_finding(self, posting_id: int, check_type: str, severity: str,
                   pattern_matched: str, description: str, 
                   check_category: Optional[str] = None,
                   evidence: Optional[str] = None,
                   field_checked: Optional[str] = None,
                   field_length: Optional[int] = None,
                   metric_value: Optional[float] = None):
        """Add a finding (stores in memory and optionally in DB)"""
        
        finding = {
            'posting_id': posting_id,
            'check_type': check_type,
            'check_category': check_category,
            'severity': severity,
            'pattern_matched': pattern_matched,
            'description': description,
            'evidence': evidence[:500] if evidence else None,  # Truncate evidence
            'field_checked': field_checked,
            'field_length': field_length,
            'metric_value': metric_value,
        }
        
        self.findings.append(finding)
        
        if self.store_in_db:
            params = {
                'posting_id': posting_id,
                'check_type': check_type,
                'check_category': check_category,
                'severity': severity,
                'pattern_matched': pattern_matched,
                'description': description,
                'evidence': evidence[:500] if evidence else None,
                'field_checked': field_checked,
                'field_length': field_length,
                'metric_value': metric_value,
                'qa_run_id': self.qa_run_id,
                'detected_by': 'qa_comprehensive_report.py'
            }
            
            self.cur.execute("""
                INSERT INTO qa_findings (
                    posting_id, check_type, check_category, severity, 
                    pattern_matched, description, evidence,
                    field_checked, field_length, metric_value,
                    qa_run_id, detected_by
                ) VALUES (
                    %(posting_id)s, %(check_type)s, %(check_category)s, %(severity)s,
                    %(pattern_matched)s, %(description)s, %(evidence)s,
                    %(field_checked)s, %(field_length)s, %(metric_value)s,
                    %(qa_run_id)s, %(detected_by)s
                )
            """, params)
    
    def check_hallucinations(self):
        """Check all postings for hallucination patterns"""
        print("🔍 Checking for hallucinations...")
        
        self.cur.execute("""
            SELECT posting_id, extracted_summary
            FROM postings
            WHERE extracted_summary IS NOT NULL
        """)
        
        postings = self.cur.fetchall()
        hallucination_count = 0
        
        for posting in postings:
            matches = check_posting(posting['posting_id'], posting['extracted_summary'])
            
            if matches:
                hallucination_count += 1
                for pattern_name, category, severity, description in matches:
                    # Extract evidence (first occurrence of problematic pattern)
                    evidence = posting['extracted_summary'][:500]
                    
                    self.add_finding(
                        posting_id=posting['posting_id'],
                        check_type='hallucination',
                        check_category=category,
                        severity=severity,
                        pattern_matched=pattern_name,
                        description=description,
                        evidence=evidence,
                        field_checked='extracted_summary',
                        field_length=len(posting['extracted_summary'])
                    )
        
        print(f"   Found {hallucination_count} postings with hallucinations")
        return hallucination_count
    
    def analyze_length_outliers(self, n: int = 5):
        """Find shortest and longest summaries"""
        print(f"📏 Analyzing length outliers (top/bottom {n})...")
        
        # Shortest
        self.cur.execute("""
            SELECT posting_id, job_title, extracted_summary,
                   LENGTH(extracted_summary) as length
            FROM postings
            WHERE extracted_summary IS NOT NULL
            ORDER BY LENGTH(extracted_summary) ASC
            LIMIT %s
        """, (n,))
        
        shortest = self.cur.fetchall()
        for posting in shortest:
            self.add_finding(
                posting_id=posting['posting_id'],
                check_type='length_outlier',
                check_category='SHORTEST',
                severity='medium',
                pattern_matched='shortest_summary',
                description=f"One of {n} shortest summaries ({posting['length']} chars)",
                evidence=posting['extracted_summary'][:500] if posting['extracted_summary'] else None,
                field_checked='extracted_summary',
                field_length=posting['length'],
                metric_value=posting['length']
            )
        
        # Longest
        self.cur.execute("""
            SELECT posting_id, job_title, extracted_summary,
                   LENGTH(extracted_summary) as length
            FROM postings
            WHERE extracted_summary IS NOT NULL
            ORDER BY LENGTH(extracted_summary) DESC
            LIMIT %s
        """, (n,))
        
        longest = self.cur.fetchall()
        for posting in longest:
            self.add_finding(
                posting_id=posting['posting_id'],
                check_type='length_outlier',
                check_category='LONGEST',
                severity='medium',
                pattern_matched='longest_summary',
                description=f"One of {n} longest summaries ({posting['length']} chars)",
                evidence=posting['extracted_summary'][:500] if posting['extracted_summary'] else None,
                field_checked='extracted_summary',
                field_length=posting['length'],
                metric_value=posting['length']
            )
        
        print(f"   Shortest: {shortest[0]['length']} chars (posting {shortest[0]['posting_id']})")
        print(f"   Longest:  {longest[0]['length']} chars (posting {longest[0]['posting_id']})")
        
        return shortest, longest
    
    def get_random_samples(self, n: int = 5):
        """Get random postings for manual review"""
        print(f"🎲 Selecting {n} random samples for manual review...")
        
        self.cur.execute("""
            SELECT posting_id, job_title, extracted_summary,
                   LENGTH(extracted_summary) as length
            FROM postings
            WHERE extracted_summary IS NOT NULL
            ORDER BY RANDOM()
            LIMIT %s
        """, (n,))
        
        samples = self.cur.fetchall()
        
        for posting in samples:
            self.add_finding(
                posting_id=posting['posting_id'],
                check_type='manual_review',
                check_category='RANDOM_SAMPLE',
                severity='info',
                pattern_matched='random_selection',
                description=f"Random sample for manual QA review ({posting['length']} chars)",
                evidence=posting['extracted_summary'][:500] if posting['extracted_summary'] else None,
                field_checked='extracted_summary',
                field_length=posting['length']
            )
        
        print(f"   Selected {len(samples)} random postings")
        return samples
    
    def analyze_processing_time(self, n: int = 5):
        """Find fastest and slowest postings to process"""
        print(f"⏱️  Analyzing processing time outliers (top/bottom {n})...")
        
        # Calculate processing time per posting from interactions
        self.cur.execute("""
            WITH posting_times AS (
                SELECT 
                    posting_id,
                    MIN(started_at) as first_interaction,
                    MAX(completed_at) as last_interaction,
                    EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(started_at))) as duration_seconds,
                    COUNT(*) as interaction_count
                FROM interactions
                WHERE posting_id IS NOT NULL
                  AND started_at IS NOT NULL
                  AND completed_at IS NOT NULL
                GROUP BY posting_id
                HAVING COUNT(*) > 1  -- Need at least 2 interactions to measure duration
            )
            SELECT 
                pt.posting_id,
                p.job_title,
                pt.duration_seconds,
                pt.interaction_count,
                pt.first_interaction,
                pt.last_interaction
            FROM posting_times pt
            JOIN postings p ON pt.posting_id = p.posting_id
            WHERE pt.duration_seconds > 0
            ORDER BY pt.duration_seconds ASC
            LIMIT %s
        """, (n,))
        
        fastest = self.cur.fetchall()
        
        for posting in fastest:
            self.add_finding(
                posting_id=posting['posting_id'],
                check_type='processing_time_outlier',
                check_category='FASTEST',
                severity='info',
                pattern_matched='fastest_processing',
                description=f"One of {n} fastest to process ({posting['duration_seconds']:.1f}s, {posting['interaction_count']} interactions)",
                field_checked='processing_duration',
                metric_value=posting['duration_seconds']
            )
        
        # Slowest
        self.cur.execute("""
            WITH posting_times AS (
                SELECT 
                    posting_id,
                    MIN(started_at) as first_interaction,
                    MAX(completed_at) as last_interaction,
                    EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(started_at))) as duration_seconds,
                    COUNT(*) as interaction_count
                FROM interactions
                WHERE posting_id IS NOT NULL
                  AND started_at IS NOT NULL
                  AND completed_at IS NOT NULL
                GROUP BY posting_id
                HAVING COUNT(*) > 1
            )
            SELECT 
                pt.posting_id,
                p.job_title,
                pt.duration_seconds,
                pt.interaction_count,
                pt.first_interaction,
                pt.last_interaction
            FROM posting_times pt
            JOIN postings p ON pt.posting_id = p.posting_id
            WHERE pt.duration_seconds > 0
            ORDER BY pt.duration_seconds DESC
            LIMIT %s
        """, (n,))
        
        slowest = self.cur.fetchall()
        
        for posting in slowest:
            self.add_finding(
                posting_id=posting['posting_id'],
                check_type='processing_time_outlier',
                check_category='SLOWEST',
                severity='info',
                pattern_matched='slowest_processing',
                description=f"One of {n} slowest to process ({posting['duration_seconds']:.1f}s, {posting['interaction_count']} interactions)",
                field_checked='processing_duration',
                metric_value=posting['duration_seconds']
            )
        
        if fastest:
            print(f"   Fastest: {fastest[0]['duration_seconds']:.1f}s (posting {fastest[0]['posting_id']})")
        if slowest:
            print(f"   Slowest: {slowest[0]['duration_seconds']:.1f}s (posting {slowest[0]['posting_id']})")
        
        return fastest, slowest
    
    def analyze_llm_interactions(self):
        """Analyze LLM interaction patterns"""
        print("🤖 Analyzing LLM interaction patterns...")
        
        # Find postings with unusual interaction counts using interactions table
        self.cur.execute("""
            SELECT 
                i.posting_id,
                p.job_title,
                COUNT(*) as interaction_count,
                COUNT(*) FILTER (WHERE i.status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE i.status = 'failed') as failed_count,
                MIN(i.started_at) as first_started,
                MAX(i.completed_at) as last_completed
            FROM interactions i
            JOIN postings p ON i.posting_id = p.posting_id
            WHERE i.posting_id IS NOT NULL
            GROUP BY i.posting_id, p.job_title
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        high_interaction_postings = self.cur.fetchall()
        
        if high_interaction_postings:
            print(f"   Highest interaction count: {high_interaction_postings[0]['interaction_count']} "
                  f"(posting {high_interaction_postings[0]['posting_id']})")
        
        return high_interaction_postings
    
    def get_posting_details(self, posting_id: int) -> dict:
        """Get full posting details for review"""
        self.cur.execute("""
            SELECT 
                posting_id,
                job_title,
                job_description,
                extracted_summary,
                LENGTH(job_description) as input_length,
                LENGTH(extracted_summary) as output_length,
                external_job_id,
                location_city,
                location_country
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        row = self.cur.fetchone()
        return dict(row) if row else None
    
    def generate_report(self) -> str:
        """Generate human-readable report with embedded posting data"""
        
        report = []
        report.append("=" * 120)
        report.append("COMPREHENSIVE DATA QUALITY REPORT")
        report.append("=" * 120)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.qa_run_id:
            report.append(f"QA Run ID: {self.qa_run_id}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY")
        report.append("-" * 120)
        
        by_type = {}
        by_severity = {}
        for finding in self.findings:
            by_type[finding['check_type']] = by_type.get(finding['check_type'], 0) + 1
            by_severity[finding['severity']] = by_severity.get(finding['severity'], 0) + 1
        
        report.append(f"Total Findings: {len(self.findings)}")
        report.append(f"Unique Postings Affected: {len(set(f['posting_id'] for f in self.findings))}")
        report.append("")
        
        report.append("By Check Type:")
        for check_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            report.append(f"  {check_type:30} {count:5} findings")
        report.append("")
        
        report.append("By Severity:")
        for severity in ['high', 'medium', 'low', 'info']:
            count = by_severity.get(severity, 0)
            if count > 0:
                report.append(f"  {severity:10} {count:5} findings")
        report.append("")
        
        # Detailed findings by category WITH FULL POSTING DATA
        report.append("\n" + "=" * 120)
        report.append("DETAILED FINDINGS WITH POSTING DATA")
        report.append("=" * 120)
        
        # Group by check type, prioritize critical issues
        check_type_priority = {
            'hallucination': 1,
            'length_outlier': 2,
            'processing_time_outlier': 3,
            'manual_review': 4,
            'data_quality': 5
        }
        
        for check_type in sorted(set(f['check_type'] for f in self.findings), 
                                key=lambda x: check_type_priority.get(x, 99)):
            type_findings = [f for f in self.findings if f['check_type'] == check_type]
            
            report.append(f"\n{'='*120}")
            report.append(f"{check_type.upper().replace('_', ' ')}")
            report.append(f"{'='*120}")
            report.append(f"Total: {len(type_findings)} findings\n")
            
            # For critical types, show full data
            show_full_data = check_type in ['hallucination', 'length_outlier', 'manual_review']
            
            # Show examples
            for i, finding in enumerate(type_findings, 1):
                posting = self.get_posting_details(finding['posting_id'])
                if not posting:
                    continue
                
                severity_marker = {
                    'high': '🔴 CRITICAL',
                    'medium': '🟡 WARNING',
                    'low': '🟢 INFO',
                    'info': 'ℹ️  INFO'
                }.get(finding['severity'], '⚪ UNKNOWN')
                
                report.append(f"\n{'-'*120}")
                report.append(f"Finding #{i} - Posting {posting['posting_id']} - {severity_marker}")
                report.append(f"{'-'*120}")
                report.append(f"Job Title: {posting['job_title']}")
                report.append(f"Location: {posting.get('location_city', 'N/A')}, {posting.get('location_country', 'N/A')}")
                report.append(f"External ID: {posting.get('external_job_id', 'N/A')}")
                report.append(f"Pattern: {finding['pattern_matched']}")
                report.append(f"Issue: {finding['description']}")
                
                if finding.get('metric_value') is not None:
                    report.append(f"Metric: {finding['metric_value']}")
                
                # Length comparison
                if posting['input_length'] and posting['output_length']:
                    ratio = posting['output_length'] / posting['input_length']
                    report.append(f"\nLength Analysis:")
                    report.append(f"  Input (job_description):  {posting['input_length']:,} chars")
                    report.append(f"  Output (extracted_summary): {posting['output_length']:,} chars")
                    report.append(f"  Expansion Ratio: {ratio:.2f}x")
                    
                    if ratio > 3:
                        report.append(f"  ⚠️  WARNING: Output is {ratio:.1f}x longer than input - possible hallucination!")
                    elif ratio < 0.3:
                        report.append(f"  ⚠️  WARNING: Output is only {ratio:.1%} of input - possible truncation!")
                
                # Show full data for critical findings
                if show_full_data or finding['severity'] == 'high':
                    report.append(f"\n{'─'*120}")
                    report.append(f"JOB DESCRIPTION (Input):")
                    report.append(f"{'─'*120}")
                    if posting['job_description']:
                        report.append(posting['job_description'])
                    else:
                        report.append("(No job description available)")
                    
                    report.append(f"\n{'─'*120}")
                    report.append(f"EXTRACTED SUMMARY (Output):")
                    report.append(f"{'─'*120}")
                    if posting['extracted_summary']:
                        report.append(posting['extracted_summary'])
                    else:
                        report.append("(No summary available)")
                    report.append(f"{'─'*120}")
                
                # For non-critical, just show preview
                elif finding.get('evidence'):
                    report.append(f"\nPreview: {finding['evidence'][:300]}...")
            
            if len(type_findings) > 20:
                report.append(f"\n... showing first 20 of {len(type_findings)} findings")
                report.append("Run: python3 scripts/qa_review_findings.py --check-type {check_type} for complete list")
        
        return "\n".join(report)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive QA report for job summaries')
    parser.add_argument('--output', help='Output file path (default: print to stdout)')
    parser.add_argument('--skip-db', action='store_true', help='Do not store findings in database')
    parser.add_argument('--samples', type=int, default=5, help='Number of samples per category (default: 5)')
    parser.add_argument('--format', choices=['text', 'markdown'], default='text', 
                       help='Output format (default: text)')
    args = parser.parse_args()
    
    conn = get_connection()
    try:
        qa = QAReport(conn, store_in_db=not args.skip_db)
        
        print("\n🔬 Running comprehensive QA analysis...\n")
        
        # Run all checks
        qa.check_hallucinations()
        qa.analyze_length_outliers(n=args.samples)
        qa.get_random_samples(n=args.samples)
        qa.analyze_processing_time(n=args.samples)
        qa.analyze_llm_interactions()
        
        # Commit findings to database
        if qa.store_in_db:
            conn.commit()
            print(f"\n✅ Stored {len(qa.findings)} findings in database (qa_run_id: {qa.qa_run_id})")
        
        # Generate report
        print("\n📊 Generating report...")
        report = qa.generate_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"✅ Report saved to {args.output}")
        else:
            print("\n" + report)
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
