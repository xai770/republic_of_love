#!/usr/bin/env python3
"""
Schema ↔ Code Synchronization Analyzer

Bidirectional analysis:
1. Find database columns NOT used in code (dead schema)
2. Find code references to tables/columns NOT in database (orphaned code)
3. Peek inside unused columns to determine if they're truly empty

Usage: ./schema_code_sync_analyzer.py
"""

import subprocess
import re
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

# Configuration
DB_NAME = "turing"
PROJECT_ROOT = Path("/home/xai/Documents/ty_learn")
OUTPUT_FILE = PROJECT_ROOT / "docs" / "SCHEMA_CODE_SYNC_ANALYSIS.md"
MIGRATION_FILE = PROJECT_ROOT / "sql/migrations/auto_generated_drop_unused_columns.sql"

@dataclass
class ColumnAnalysis:
    table: str
    column: str
    verdict: str
    non_null_count: int
    distinct_count: int
    sample_values: str
    view_dependencies: List[str] = None
    constraints: List[str] = None
    last_code_reference: Optional[datetime] = None
    
    def __post_init__(self):
        if self.view_dependencies is None:
            self.view_dependencies = []
        if self.constraints is None:
            self.constraints = []
    
    @property
    def is_deletable(self):
        # Not deletable if has constraints
        if self.constraints:
            return False
        return self.verdict in ["DELETE_EMPTY", "DELETE_CONSTANT", "DELETE_SPARSE"]

def run_psql(query: str) -> str:
    """Execute PostgreSQL query and return output"""
    cmd = ["sudo", "-u", "postgres", "psql", "-d", DB_NAME, "-t", "-c", query]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return result.stdout.strip()

def grep_search(pattern: str, include_pattern: str = "*.py", exclude_dirs: List[str] = None) -> int:
    """Search for pattern in files and return match count"""
    exclude_dirs = exclude_dirs or ["venv", "archive", "backups"]
    
    cmd = ["grep", "-rw", pattern, "--include", include_pattern]
    for exclude in exclude_dirs:
        cmd.extend(["--exclude-dir", exclude])
    cmd.append(str(PROJECT_ROOT))
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return len(result.stdout.splitlines()) if result.returncode == 0 else 0

def get_all_tables() -> List[str]:
    """Get all table names from database"""
    query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
    """
    output = run_psql(query)
    return [line.strip() for line in output.split('\n') if line.strip()]

def get_table_columns(table: str) -> List[str]:
    """Get all column names for a table"""
    query = f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
          AND table_schema = 'public'
        ORDER BY ordinal_position;
    """
    output = run_psql(query)
    return [line.strip() for line in output.split('\n') if line.strip()]

def analyze_column_data(table: str, column: str) -> Tuple[int, int, str]:
    """Check actual data in column - peek inside the box!"""
    query = f"""
        SELECT 
            COUNT("{column}") as non_null_count,
            COUNT(DISTINCT "{column}") as distinct_values,
            CASE 
                WHEN COUNT(DISTINCT "{column}") <= 5 THEN 
                    array_to_string(array_agg(DISTINCT "{column}"), ', ')
                ELSE 
                    'Too many values (' || COUNT(DISTINCT "{column}")::text || ')'
            END as sample_values
        FROM "{table}"
        WHERE "{column}" IS NOT NULL;
    """
    output = run_psql(query)
    
    if not output or '|' not in output:
        return 0, 0, "(empty table)"
    
    parts = [p.strip() for p in output.split('|')]
    non_null = int(parts[0]) if parts[0] and parts[0].isdigit() else 0
    distinct = int(parts[1]) if parts[1] and parts[1].isdigit() else 0
    samples = parts[2] if len(parts) > 2 else "(empty)"
    
    return non_null, distinct, samples

def determine_verdict(non_null: int, distinct: int) -> str:
    """Decide what to do with this column"""
    if non_null == 0:
        return "DELETE_EMPTY"
    elif distinct == 1:
        return "DELETE_CONSTANT"
    elif non_null < 5:
        return "DELETE_SPARSE"
    else:
        return "REVIEW_HAS_DATA"

def get_column_view_dependencies(table: str, column: str) -> List[str]:
    """Check if column is used by any views"""
    query = f"""
        SELECT DISTINCT v.viewname
        FROM pg_views v
        WHERE v.schemaname = 'public'
          AND v.definition LIKE '%{table}%'
          AND v.definition LIKE '%{column}%';
    """
    output = run_psql(query)
    views = [line.strip() for line in output.split('\n') if line.strip()]
    return views

def get_column_constraints(table: str, column: str) -> List[str]:
    """Check if column has foreign key or other constraints"""
    # Check foreign keys where this column is referenced
    query = f"""
        SELECT 
            'FK: ' || tc.table_name || '.' || kcu.column_name || 
            ' -> ' || ccu.table_name || '.' || ccu.column_name as constraint_info
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = '{table}'
          AND ccu.column_name = '{column}'
          AND tc.table_schema = 'public'
        
        UNION ALL
        
        -- Check if this column IS a foreign key
        SELECT 
            'IS FK to: ' || ccu.table_name || '.' || ccu.column_name as constraint_info
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = '{table}'
          AND kcu.column_name = '{column}'
          AND tc.table_schema = 'public'
        
        UNION ALL
        
        -- Check primary keys
        SELECT 
            'PRIMARY KEY' as constraint_info
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_name = '{table}'
          AND kcu.column_name = '{column}'
          AND tc.table_schema = 'public';
    """
    output = run_psql(query)
    constraints = [line.strip() for line in output.split('\n') if line.strip()]
    return constraints

def is_view_used_in_code(view_name: str) -> Tuple[bool, Optional[datetime]]:
    """Check if a view is referenced in Python/SQL code and when"""
    cmd = [
        "grep", "-rl", view_name,
        "--include", "*.py", "--include", "*.sql",
        "--exclude-dir", "venv", "--exclude-dir", "archive", "--exclude-dir", "backups",
        "--exclude-dir", "migrations",  # Exclude migration files - they're history
        str(PROJECT_ROOT)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
    if result.returncode != 0 or not result.stdout.strip():
        return False, None
    
    # Find the most recent file that references this view
    files = result.stdout.strip().split('\n')
    
    # Filter out migration files and sql/migrations
    files = [f for f in files if 'migration' not in f.lower()]
    
    if not files:
        return False, None
    
    most_recent = None
    
    for file_path in files:
        try:
            mtime = Path(file_path).stat().st_mtime
            file_date = datetime.fromtimestamp(mtime)
            if most_recent is None or file_date > most_recent:
                most_recent = file_date
        except:
            continue
    
    return True, most_recent

def get_last_code_reference_date(table: str, column: str) -> Optional[datetime]:
    """Find when this column was last referenced in code"""
    cmd = [
        "grep", "-rl", column,
        "--include", "*.py", "--include", "*.sql",
        "--exclude-dir", "venv", "--exclude-dir", "archive", "--exclude-dir", "backups",
        "--exclude", "*_schema*.sql", "--exclude", "schema*.sql",
        str(PROJECT_ROOT)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    
    if result.returncode != 0 or not result.stdout.strip():
        return None
    
    files = result.stdout.strip().split('\n')
    most_recent = None
    
    for file_path in files:
        try:
            mtime = Path(file_path).stat().st_mtime
            file_date = datetime.fromtimestamp(mtime)
            if most_recent is None or file_date > most_recent:
                most_recent = file_date
        except:
            continue
    
    return most_recent

def determine_verdict(non_null: int, distinct: int) -> str:
    """Decide what to do with this column"""
    if non_null == 0:
        return "DELETE_EMPTY"
    elif distinct == 1:
        return "DELETE_CONSTANT"
    elif non_null < 5:
        return "DELETE_SPARSE"
    else:
        return "REVIEW_HAS_DATA"

def analyze_unused_columns() -> Tuple[Dict[str, List[ColumnAnalysis]], Dict[str, int]]:
    """Analyze all tables and find unused columns"""
    print("📊 Part 1: Analyzing Database → Code")
    print("Finding columns that exist in DB but aren't used in code...\n")
    
    tables = get_all_tables()
    print(f"Analyzing {len(tables)} tables...")
    
    unused_by_table = defaultdict(list)
    stats = {
        'total_columns': 0,
        'unused_columns': 0,
        'delete_empty': 0,
        'delete_constant': 0,
        'delete_sparse': 0,
        'review_has_data': 0
    }
    
    for i, table in enumerate(tables, 1):
        print(f"  [{i}/{len(tables)}] Analyzing: {table}                    ", end='\r')
        
        columns = get_table_columns(table)
        stats['total_columns'] += len(columns)
        
        for column in columns:
            # Check if column is referenced in code
            python_refs = grep_search(column, "*.py")
            
            # For SQL, exclude schema files and backups
            cmd = [
                "grep", "-rw", column, "--include", "*.sql",
                "--exclude-dir", "backups",
                "--exclude", "*backup*.sql",
                "--exclude", "*_schema*.sql",
                "--exclude", "schema*.sql",
                str(PROJECT_ROOT / "scripts"),
                str(PROJECT_ROOT / "tools"),
                str(PROJECT_ROOT / "core"),
                str(PROJECT_ROOT / "sql/migrations")
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            sql_refs = len(result.stdout.splitlines()) if result.returncode == 0 else 0
            
            total_refs = python_refs + sql_refs
            
            if total_refs == 0:
                # Unused! Peek inside to see what's there
                non_null, distinct, samples = analyze_column_data(table, column)
                verdict = determine_verdict(non_null, distinct)
                
                # Check if used by views (and if those views are used)
                view_deps = get_column_view_dependencies(table, column)
                used_views = []
                for view in view_deps:
                    is_used, last_ref = is_view_used_in_code(view)
                    if is_used:
                        used_views.append(f"{view} (last used: {last_ref.strftime('%Y-%m-%d') if last_ref else 'unknown'})")
                    else:
                        used_views.append(f"{view} (UNUSED VIEW)")
                
                # Check for foreign keys and other constraints
                constraints = get_column_constraints(table, column)
                
                # Get last reference date for this column
                last_ref_date = get_last_code_reference_date(table, column)
                
                analysis = ColumnAnalysis(
                    table=table,
                    column=column,
                    verdict=verdict,
                    non_null_count=non_null,
                    distinct_count=distinct,
                    sample_values=samples,
                    view_dependencies=used_views,
                    constraints=constraints,
                    last_code_reference=last_ref_date
                )
                
                unused_by_table[table].append(analysis)
                stats['unused_columns'] += 1
                stats[verdict.lower()] += 1
    
    print(f"\n✓ Database analysis complete")
    print(f"  Total columns: {stats['total_columns']}")
    print(f"  Unused columns: {stats['unused_columns']}\n")
    
    return unused_by_table, stats

def find_orphaned_tables() -> List[Tuple[str, List[str]]]:
    """Find code references to tables that don't exist in DB"""
    print("📝 Part 2: Analyzing Code → Database")
    print("Finding code references to non-existent tables...\n")
    
    # Get actual DB tables
    db_tables = set(get_all_tables())
    
    # Find table references in Python code
    cmd = [
        "grep", "-rhoE", r"(FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-z_]+)",
        "--include", "*.py",
        "--exclude-dir", "venv",
        "--exclude-dir", "archive",
        "--exclude-dir", "backups",
        str(PROJECT_ROOT)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Extract table names
    code_tables = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            table = parts[-1]
            # Skip SQL keywords
            if table.upper() not in ["SELECT", "WHERE", "AND", "OR", "NOT", "NULL", "TRUE", "FALSE", "AS", "ON"]:
                code_tables.add(table)
    
    # Find orphans
    orphaned = []
    for table in sorted(code_tables - db_tables):
        # Find where it's referenced
        cmd = ["grep", "-rn", rf"\b{table}\b", "--include", "*.py", 
               "--exclude-dir", "venv", "--exclude-dir", "archive", str(PROJECT_ROOT)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        refs = result.stdout.splitlines()[:3]  # First 3 references
        refs = [r.replace(str(PROJECT_ROOT) + "/", "") for r in refs]
        
        if refs:
            orphaned.append((table, refs))
    
    print("✓ Code analysis complete\n")
    return orphaned

def find_select_star_queries() -> List[str]:
    """Find SELECT * queries (anti-pattern)"""
    cmd = [
        "grep", "-rn", "SELECT \\*",
        "--include", "*.py", "--include", "*.sql",
        "--exclude-dir", "venv", "--exclude-dir", "archive", "--exclude-dir", "backups",
        str(PROJECT_ROOT / "core"), str(PROJECT_ROOT / "scripts"), str(PROJECT_ROOT / "tools")
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    refs = result.stdout.splitlines()[:20]
    return [r.replace(str(PROJECT_ROOT) + "/", "") for r in refs]

def generate_report(unused_by_table, stats, orphaned_tables):
    """Generate markdown report"""
    with open(OUTPUT_FILE, 'w') as f:
        f.write(f"""# Schema ↔ Code Synchronization Analysis

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database:** {DB_NAME}
**Project:** {PROJECT_ROOT}

This report identifies mismatches between database schema and code:
1. **Dead Schema:** Columns in DB not used in code
2. **Orphaned Code:** Code referencing tables/columns not in DB

---

## Part 1: Dead Schema (DB → Code)

### Summary by Table

| Table | Total Columns | Unused Columns | Unused % |
|-------|---------------|----------------|----------|
""")
        
        # Table summary
        for table in sorted(unused_by_table.keys()):
            analyses = unused_by_table[table]
            total_cols = len(get_table_columns(table))
            unused_cols = len(analyses)
            pct = int(unused_cols * 100 / total_cols) if total_cols > 0 else 0
            f.write(f"| {table} | {total_cols} | {unused_cols} | {pct}% |\n")
        
        waste_pct = int(stats['unused_columns'] * 100 / stats['total_columns']) if stats['total_columns'] > 0 else 0
        
        f.write(f"""
**Totals:**
- Total columns analyzed: {stats['total_columns']}
- Unused columns found: {stats['unused_columns']}
- Waste percentage: {waste_pct}%

### Data Analysis Summary

| Verdict | Count | Action |
|---------|-------|--------|
| 🗑️ DELETE_EMPTY | {stats['delete_empty']} | Completely empty - safe to drop |
| 🗑️ DELETE_CONSTANT | {stats['delete_constant']} | Only one value - useless |
| 🗑️ DELETE_SPARSE | {stats['delete_sparse']} | < 5 rows populated - negligible |
| ⚠️ REVIEW_HAS_DATA | {stats['review_has_data']} | Has data - manual review needed |

**Safe to auto-delete:** {stats['delete_empty'] + stats['delete_constant'] + stats['delete_sparse']} columns
**Total deletable:** {stats['unused_columns']} columns

### Detailed Unused Columns

""")
        
        # Detailed analysis
        for table in sorted(unused_by_table.keys()):
            f.write(f"**`{table}`:**\n\n")
            for analysis in unused_by_table[table]:
                emoji = "🗑️" if analysis.is_deletable else "⚠️"
                verdict_display = analysis.verdict.replace("DELETE_", "").replace("REVIEW_HAS_", "")
                
                # Build detail string
                details = f"({analysis.non_null_count} rows, {analysis.distinct_count} distinct)"
                
                # Add view dependencies if any
                if analysis.view_dependencies:
                    view_info = ", ".join(analysis.view_dependencies)
                    details += f" - **Views:** {view_info}"
                
                # Add constraints if any
                if analysis.constraints:
                    constraint_info = ", ".join(analysis.constraints)
                    details += f" - **Constraints:** {constraint_info}"
                
                # Add last reference date if available
                if analysis.last_code_reference:
                    days_ago = (datetime.now() - analysis.last_code_reference).days
                    if days_ago > 180:
                        age_flag = "🕸️ STALE"
                    elif days_ago > 90:
                        age_flag = "⚠️ OLD"
                    else:
                        age_flag = "✓ RECENT"
                    details += f" - **Last ref:** {analysis.last_code_reference.strftime('%Y-%m-%d')} ({days_ago}d ago) {age_flag}"
                
                f.write(f"- `{analysis.column}` - **{emoji} {verdict_display}** {details} - {analysis.sample_values}\n")
            f.write("\n")
        
        # Orphaned tables section
        f.write("""---

## Part 2: Orphaned Code (Code → DB)

### Table References in Code Not in Database

""")
        
        if orphaned_tables:
            for table, refs in orphaned_tables:
                f.write(f"**`{table}`** (not in database)\n```\n")
                f.write('\n'.join(refs))
                f.write("\n```\n\n")
        else:
            f.write("✅ No orphaned table references found! All code references valid tables.\n")
        
        # SELECT * patterns
        f.write("""---

## Part 3: Anti-Pattern Detection

### 1. SELECT * Queries (Lazy Schema Coupling)

Files using SELECT * instead of explicit column lists:

""")
        
        select_star = find_select_star_queries()
        if select_star:
            f.write("```\n" + '\n'.join(select_star) + "\n```\n\n")
            f.write("⚠️ **Recommendation:** Replace SELECT * with explicit column lists to prevent breakage when columns are dropped.\n")
        else:
            f.write("✅ No SELECT * patterns found!\n")
        
        # Recommendations
        auto_delete = stats['delete_empty'] + stats['delete_constant'] + stats['delete_sparse']
        f.write(f"""

---

## Recommendations

### Immediate Actions (High Priority)

""")
        
        if auto_delete > 0:
            f.write(f"""1. **Auto-delete {auto_delete} columns (empty/constant/sparse)**
   - These are 100% safe to drop (no data or useless data)
   - Migration script generated: `{MIGRATION_FILE}`
   - Execute in dev, verify, then production

""")
        
        if stats['review_has_data'] > 0:
            f.write(f"""2. **Review {stats['review_has_data']} columns with actual data**
   - Check if data is historical/legacy
   - Export data before dropping if needed
   - Consider archiving to separate table

""")
        
        f.write("""3. **Fix SELECT * queries**
   - Replace with explicit column lists
   - Prevents silent breakage when columns removed

4. **Remove orphaned code references**
   - Delete references to non-existent tables
   - Clean up commented-out legacy code

---

**Philosophy:** A synchronized schema and codebase = confidence in refactoring = freedom to innovate. 🚀
""")
        
        if auto_delete > 0:
            f.write(f"""

---

## Auto-Generated Migration

A migration script has been created for safe deletions:

**File:** `{MIGRATION_FILE}`

**Contents:** {auto_delete} DROP COLUMN statements for empty/constant/sparse columns

**To execute:**
```bash
# Review first!
cat {MIGRATION_FILE}

# Test in dev
sudo -u postgres psql -d turing_dev -f {MIGRATION_FILE}

# If successful, production
sudo -u postgres psql -d turing -f {MIGRATION_FILE}
```
""")

def generate_migration(unused_by_table):
    """Generate SQL migration for safe deletions"""
    deletable = []
    skipped_view_deps = []
    skipped_constraints = []
    
    for table, analyses in unused_by_table.items():
        for analysis in analyses:
            if analysis.constraints:
                # Has FK or other constraints - can't drop
                skipped_constraints.append(analysis)
            elif analysis.is_deletable:
                # Check if it has view dependencies that are actually used
                has_used_views = any("UNUSED VIEW" not in dep for dep in analysis.view_dependencies)
                
                if has_used_views:
                    skipped_view_deps.append(analysis)
                else:
                    deletable.append(analysis)
    
    if not deletable and not skipped_view_deps and not skipped_constraints:
        return
    
    with open(MIGRATION_FILE, 'w') as f:
        f.write(f"""-- Auto-generated migration: Drop unused columns
-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 
-- This migration drops columns that are:
-- 1. Not referenced in any Python or SQL code
-- 2. Either completely empty, contain only one constant value, or have < 5 rows
-- 3. Not used by any active database views
-- 4. Not part of foreign key or primary key constraints
--
-- ⚠️ REVIEW THIS BEFORE EXECUTING ⚠️

BEGIN;

""")
        
        if skipped_constraints:
            f.write("-- SKIPPED (has database constraints):\n")
            for analysis in skipped_constraints:
                constraint_list = ", ".join(analysis.constraints)
                f.write(f"-- {analysis.table}.{analysis.column} - {constraint_list}\n")
            f.write("\n")
        
        if skipped_view_deps:
            f.write("-- SKIPPED (used by views):\n")
            for analysis in skipped_view_deps:
                view_list = ", ".join(analysis.view_dependencies)
                f.write(f"-- {analysis.table}.{analysis.column} - used by: {view_list}\n")
            f.write("\n")
        
        for analysis in deletable:
            age_note = ""
            if analysis.last_code_reference:
                days = (datetime.now() - analysis.last_code_reference).days
                age_note = f", last ref {days}d ago"
            
            f.write(f"""-- Drop {analysis.table}.{analysis.column} ({analysis.verdict}: {analysis.non_null_count} rows, {analysis.distinct_count} distinct{age_note})
-- Sample values: {analysis.sample_values}
ALTER TABLE "{analysis.table}" DROP COLUMN IF EXISTS "{analysis.column}";

""")
        
        f.write("""
COMMIT;

-- Verification queries
-- Run these to confirm the columns are gone:

""")
        
        # Group by table for verification
        tables = sorted(set(a.table for a in deletable))
        for table in tables:
            f.write(f"""-- Verify {table}
SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND table_schema = 'public' ORDER BY ordinal_position;

""")
    
    print(f"📝 Migration script generated: {MIGRATION_FILE}")
    if skipped_constraints:
        print(f"   ⚠️  Skipped {len(skipped_constraints)} columns due to database constraints")
    if skipped_view_deps:
        print(f"   ⚠️  Skipped {len(skipped_view_deps)} columns due to view dependencies")

def main():
    print("═══════════════════════════════════════════════════")
    print("   Schema ↔ Code Synchronization Analyzer")
    print("═══════════════════════════════════════════════════")
    print()
    
    # Part 1: Find unused columns and peek inside
    unused_by_table, stats = analyze_unused_columns()
    
    # Part 2: Find orphaned code
    orphaned_tables = find_orphaned_tables()
    
    # Part 3: Generate reports
    print("🔍 Part 3: Pattern Detection")
    print("Looking for specific anti-patterns...\n")
    
    generate_report(unused_by_table, stats, orphaned_tables)
    generate_migration(unused_by_table)
    
    print("═══════════════════════════════════════════════════")
    print("✅ Analysis Complete!")
    print("═══════════════════════════════════════════════════")
    print()
    print(f"Report saved to: {OUTPUT_FILE}")
    print()
    print("Summary:")
    waste_pct = int(stats['unused_columns'] * 100 / stats['total_columns']) if stats['total_columns'] > 0 else 0
    print(f"  • Dead schema: {stats['unused_columns']} unused columns out of {stats['total_columns']} ({waste_pct}%)")
    print(f"  • Empty columns: {stats['delete_empty']} (safe to delete)")
    print(f"  • Orphaned code: {len(orphaned_tables)} ghost tables referenced")
    print()
    print("Next steps:")
    print(f"  1. Review: cat {OUTPUT_FILE}")
    print(f"  2. Execute migration: sudo -u postgres psql -d turing -f {MIGRATION_FILE}")
    print("  3. Fix SELECT * queries")
    print("  4. Remove orphaned code")
    print()

if __name__ == "__main__":
    main()
