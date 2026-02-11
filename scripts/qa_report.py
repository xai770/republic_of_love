#!/usr/bin/env python3
"""
QA Report: Daily Data Quality Check

Run after nightly fetch or on-demand to surface problems.
Outputs to stdout and optionally writes a markdown report.

Usage:
    python3 scripts/qa_report.py              # stdout only
    python3 scripts/qa_report.py --save       # also save to reports/
    python3 scripts/qa_report.py --quiet      # summary only

Author: Arden ℵ
Created: 2026-02-07
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection using standard env vars."""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )


def run_query(cur, query: str, params=None) -> list:
    """Execute query and return results as list of dicts."""
    cur.execute(query, params or ())
    return cur.fetchall()


def format_number(n: int) -> str:
    """Format number with commas."""
    return f"{n:,}"


def format_pct(n: int, total: int) -> str:
    """Format as percentage."""
    if total == 0:
        return "N/A"
    return f"{n/total*100:.1f}%"


def get_health_icon(pct: float, good_threshold: float = 90, warn_threshold: float = 70) -> str:
    """Return icon based on health percentage."""
    if pct >= good_threshold:
        return "✅"
    elif pct >= warn_threshold:
        return "⚠️"
    else:
        return "❌"


class QAReport:
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=RealDictCursor)
        self.now = datetime.now()
        self.issues = []
        self.warnings = []
        
    def check_total_counts(self) -> dict:
        """Get overall posting counts."""
        result = run_query(self.cur, """
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE posting_status = 'active') AS active,
                COUNT(*) FILTER (WHERE first_seen_at >= NOW() - INTERVAL '24 hours') AS new_24h,
                COUNT(*) FILTER (WHERE first_seen_at >= NOW() - INTERVAL '7 days') AS new_7d
            FROM postings
        """)[0]
        return dict(result)
    
    def check_descriptions(self) -> dict:
        """Check job description coverage."""
        result = run_query(self.cur, """
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE job_description IS NOT NULL AND job_description != '') AS with_desc,
                COUNT(*) FILTER (WHERE job_description IS NULL OR job_description = '') AS null_desc,
                COUNT(*) FILTER (WHERE job_description IS NULL AND first_seen_at >= NOW() - INTERVAL '24 hours') AS null_desc_24h
            FROM postings
            WHERE posting_status = 'active'
        """)[0]
        return dict(result)
    
    def check_descriptions_by_source(self) -> list:
        """Check descriptions broken down by source."""
        return run_query(self.cur, """
            SELECT 
                source,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE job_description IS NOT NULL) AS with_desc,
                COUNT(*) FILTER (WHERE job_description IS NULL) AS null_desc
            FROM postings
            WHERE posting_status = 'active'
            GROUP BY source
            ORDER BY total DESC
        """)
    
    def check_external_partners(self) -> list:
        """Check external partner jobs (AA jobs that redirect)."""
        return run_query(self.cur, """
            SELECT 
                SUBSTRING(external_id FROM 'aa-(\d+)-') AS prefix,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE job_description IS NOT NULL) AS with_desc,
                COUNT(*) FILTER (WHERE job_description IS NULL) AS null_desc,
                COUNT(*) FILTER (WHERE external_url NOT LIKE '%%arbeitsagentur.de%%') AS has_external_url
            FROM postings
            WHERE source = 'arbeitsagentur' 
              AND posting_status = 'active'
              AND external_id LIKE 'aa-%%'
            GROUP BY SUBSTRING(external_id FROM 'aa-(\d+)-')
            HAVING COUNT(*) FILTER (WHERE job_description IS NULL) > 0
            ORDER BY COUNT(*) FILTER (WHERE job_description IS NULL) DESC
            LIMIT 15
        """)
    
    def check_berufenet(self) -> dict:
        """Check berufenet classification coverage."""
        result = run_query(self.cur, """
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE berufenet_id IS NOT NULL) AS with_berufenet,
                COUNT(*) FILTER (WHERE berufenet_id IS NULL) AS null_berufenet
            FROM postings
            WHERE posting_status = 'active'
        """)[0]
        return dict(result)
    
    def check_embeddings(self) -> dict:
        """Check embedding coverage."""
        # Embeddings table uses text_hash as key, not posting_id
        # So we just report total count vs active postings as a rough comparison
        result = run_query(self.cur, """
            SELECT 
                (SELECT COUNT(*) FROM postings WHERE posting_status = 'active') AS active_postings,
                (SELECT COUNT(*) FROM embeddings) AS total_embeddings
        """)[0]
        # Rough estimate: embeddings should be >= active postings
        result['coverage_ok'] = result['total_embeddings'] >= result['active_postings']
        return dict(result)
    
    def check_recent_fetches(self) -> list:
        """Get recent fetch activity by day."""
        return run_query(self.cur, """
            SELECT 
                DATE(first_seen_at) AS date,
                source,
                COUNT(*) AS new_postings,
                COUNT(*) FILTER (WHERE job_description IS NOT NULL) AS with_desc
            FROM postings
            WHERE first_seen_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(first_seen_at), source
            ORDER BY DATE(first_seen_at) DESC, source
        """)
    
    def check_stale_jobs(self) -> dict:
        """Check for jobs not updated recently."""
        result = run_query(self.cur, """
            SELECT 
                COUNT(*) FILTER (WHERE last_seen_at < NOW() - INTERVAL '7 days' AND posting_status = 'active') AS stale_7d,
                COUNT(*) FILTER (WHERE last_seen_at < NOW() - INTERVAL '14 days' AND posting_status = 'active') AS stale_14d
            FROM postings
        """)[0]
        return dict(result)
    
    def check_owl_config(self) -> dict:
        """Check owl configuration status."""
        result = run_query(self.cur, """
            SELECT 
                (SELECT COUNT(*) FROM owl WHERE owl_type = 'external_job_site' AND status = 'active') AS external_sites,
                (SELECT COUNT(*) FROM owl WHERE owl_type = 'berufenet_synonym' AND status = 'active') AS berufenet_synonyms
        """)[0]
        return dict(result)
    
    def generate_report(self, quiet: bool = False) -> str:
        """Generate the full QA report."""
        lines = []
        
        # Header
        lines.append(f"# QA Report: {self.now.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # === SUMMARY ===
        counts = self.check_total_counts()
        desc = self.check_descriptions()
        beruf = self.check_berufenet()
        embed = self.check_embeddings()
        
        desc_pct = desc['with_desc'] / desc['total'] * 100 if desc['total'] > 0 else 0
        beruf_pct = beruf['with_berufenet'] / beruf['total'] * 100 if beruf['total'] > 0 else 0
        # Embeddings use text_hash dedup, so total may exceed postings (but should be >= active)
        embed_status = "✅" if embed['coverage_ok'] else "⚠️"
        
        lines.append("## 📊 Summary")
        lines.append("")
        lines.append("| Metric | Value | Coverage | Status |")
        lines.append("|--------|-------|----------|--------|")
        lines.append(f"| Total postings | {format_number(counts['total'])} | — | — |")
        lines.append(f"| Active postings | {format_number(counts['active'])} | — | — |")
        lines.append(f"| New (24h) | {format_number(counts['new_24h'])} | — | — |")
        lines.append(f"| With description | {format_number(desc['with_desc'])} | {desc_pct:.1f}% | {get_health_icon(desc_pct)} |")
        lines.append(f"| With berufenet_id | {format_number(beruf['with_berufenet'])} | {beruf_pct:.1f}% | {get_health_icon(beruf_pct, 75, 50)} |")
        lines.append(f"| Total embeddings | {format_number(embed['total_embeddings'])} | ≥{format_number(embed['active_postings'])} | {embed_status} |")
        lines.append("")
        
        # Check for critical issues
        if desc['null_desc_24h'] > 100:
            self.issues.append(f"❌ {format_number(desc['null_desc_24h'])} new jobs (24h) missing descriptions")
        if beruf_pct < 70:
            self.warnings.append(f"⚠️ Berufenet coverage below 70% ({beruf_pct:.1f}%)")
        if not embed['coverage_ok']:
            self.warnings.append(f"⚠️ Embeddings ({format_number(embed['total_embeddings'])}) less than active postings ({format_number(embed['active_postings'])})")
        
        if quiet:
            # Just return summary
            if self.issues:
                lines.append("## ❌ Issues")
                for issue in self.issues:
                    lines.append(f"- {issue}")
                lines.append("")
            if self.warnings:
                lines.append("## ⚠️ Warnings")
                for warn in self.warnings:
                    lines.append(f"- {warn}")
                lines.append("")
            return "\n".join(lines)
        
        # === DESCRIPTIONS BY SOURCE ===
        lines.append("## 📝 Descriptions by Source")
        lines.append("")
        desc_by_source = self.check_descriptions_by_source()
        lines.append("| Source | Total | With Desc | NULL | Coverage |")
        lines.append("|--------|-------|-----------|------|----------|")
        for row in desc_by_source:
            pct = row['with_desc'] / row['total'] * 100 if row['total'] > 0 else 0
            lines.append(f"| {row['source']} | {format_number(row['total'])} | {format_number(row['with_desc'])} | {format_number(row['null_desc'])} | {pct:.1f}% {get_health_icon(pct)} |")
        lines.append("")
        
        # === EXTERNAL PARTNERS (NULL DESC) ===
        external = self.check_external_partners()
        if external:
            lines.append("## 🔗 External Partner Jobs (Missing Descriptions)")
            lines.append("")
            lines.append("Jobs that redirect to external sites and need scraping:")
            lines.append("")
            lines.append("| Prefix | Total | NULL Desc | Has External URL | Action Needed |")
            lines.append("|--------|-------|-----------|------------------|---------------|")
            for row in external:
                prefix = row['prefix'] or 'unknown'
                has_url = row['has_external_url'] or 0
                action = "✅ Can scrape" if has_url > 0 else "⚠️ Need URL mapping"
                lines.append(f"| {prefix} | {format_number(row['total'])} | {format_number(row['null_desc'])} | {format_number(has_url)} | {action} |")
            lines.append("")
            
            total_external_null = sum(r['null_desc'] for r in external)
            if total_external_null > 500:
                self.warnings.append(f"⚠️ {format_number(total_external_null)} external partner jobs missing descriptions")
        
        # === RECENT FETCHES ===
        lines.append("## 📅 Recent Fetch Activity (7 days)")
        lines.append("")
        recent = self.check_recent_fetches()
        lines.append("| Date | Source | New | With Desc | Coverage |")
        lines.append("|------|--------|-----|-----------|----------|")
        for row in recent:
            pct = row['with_desc'] / row['new_postings'] * 100 if row['new_postings'] > 0 else 0
            lines.append(f"| {row['date']} | {row['source']} | {format_number(row['new_postings'])} | {format_number(row['with_desc'])} | {pct:.1f}% |")
        lines.append("")
        
        # === STALE JOBS ===
        stale = self.check_stale_jobs()
        if stale['stale_7d'] > 0 or stale['stale_14d'] > 0:
            lines.append("## ⏰ Stale Jobs")
            lines.append("")
            lines.append(f"- Not seen in 7 days: {format_number(stale['stale_7d'])}")
            lines.append(f"- Not seen in 14 days: {format_number(stale['stale_14d'])}")
            lines.append("")
            if stale['stale_14d'] > 1000:
                self.warnings.append(f"⚠️ {format_number(stale['stale_14d'])} jobs not seen in 14+ days (consider invalidating)")
        
        # === OWL CONFIG ===
        owl = self.check_owl_config()
        lines.append("## ⚙️ Configuration")
        lines.append("")
        lines.append(f"- External job site configs: {owl['external_sites']}")
        lines.append(f"- Berufenet synonyms: {owl['berufenet_synonyms']}")
        lines.append("")
        
        # === ISSUES & WARNINGS ===
        if self.issues:
            lines.append("## ❌ Critical Issues")
            lines.append("")
            for issue in self.issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        if self.warnings:
            lines.append("## ⚠️ Warnings")
            lines.append("")
            for warn in self.warnings:
                lines.append(f"- {warn}")
            lines.append("")
        
        if not self.issues and not self.warnings:
            lines.append("## ✅ All Clear")
            lines.append("")
            lines.append("No critical issues or warnings detected.")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Generated: {self.now.strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate QA report for data quality")
    parser.add_argument("--save", action="store_true", help="Save report to reports/ directory")
    parser.add_argument("--quiet", "-q", action="store_true", help="Summary only")
    args = parser.parse_args()
    
    conn = get_db_connection()
    try:
        report = QAReport(conn)
        output = report.generate_report(quiet=args.quiet)
        
        print(output)
        
        if args.save:
            # Save to reports directory
            reports_dir = Path(__file__).parent.parent / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            filename = f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            filepath = reports_dir / filename
            
            with open(filepath, "w") as f:
                f.write(output)
            
            print(f"\n📁 Report saved to: {filepath}")
        
        # Exit code based on issues
        if report.issues:
            sys.exit(1)
        sys.exit(0)
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
