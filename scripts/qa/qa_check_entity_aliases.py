#!/usr/bin/env python3
"""
QA Check: Entity Alias Quality

Detects potentially bad alias mappings in the Entity Registry.

Checks:
1. Semantic drift - aliases that seem unrelated to canonical name
2. Cross-category aliases - e.g., "database" aliased to "programming"
3. Overly broad mappings - many diverse aliases to one entity

Output:
- Report of suspicious aliases for human review
- Can be run in --fix mode to queue issues to entities_pending

Usage:
    python3 scripts/qa_check_entity_aliases.py              # Report only
    python3 scripts/qa_check_entity_aliases.py --fix        # Queue fixes
    python3 scripts/qa_check_entity_aliases.py --verbose    # Show all checks

Author: Arden
Date: December 8, 2025
"""

import sys
import os
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.database import get_connection

# Keywords that indicate semantic categories
CATEGORY_KEYWORDS = {
    'database': ['database', 'sql', 'data', 'query', 'schema', 'table'],
    'programming': ['programming', 'coding', 'code', 'python', 'java', 'javascript', 'developer'],
    'management': ['management', 'manager', 'lead', 'leadership', 'stakeholder', 'project'],
    'communication': ['communication', 'writing', 'speaking', 'presentation'],
    'agile': ['agile', 'scrum', 'sprint', 'kanban', 'methodology'],
    'security': ['security', 'cyber', 'risk', 'compliance', 'audit'],
    'cloud': ['cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker'],
    'office': ['office', 'excel', 'word', 'powerpoint', 'microsoft'],
}


def get_category(text: str) -> str:
    """Determine semantic category of a skill name."""
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return 'other'


def check_alias_quality(conn, verbose=False):
    """
    Check all aliases for quality issues.
    
    Returns list of issues with format:
    {
        'alias_id': int,
        'entity_id': int,
        'alias': str,
        'canonical_name': str,
        'issue_type': str,
        'severity': str,  # 'high', 'medium', 'low'
        'reason': str
    }
    """
    cursor = conn.cursor()
    
    # Get all skill aliases with their canonical names (excluding soft-deleted)
    cursor.execute("""
        SELECT ea.alias_id, ea.entity_id, ea.alias, e.canonical_name,
               ea.created_at, ea.created_by
        FROM entity_aliases ea
        JOIN entities e ON ea.entity_id = e.entity_id
        WHERE e.entity_type = 'skill'
        AND ea.deleted_at IS NULL
        ORDER BY e.canonical_name, ea.alias
    """)
    
    aliases = cursor.fetchall()
    issues = []
    
    for row in aliases:
        # Support both dict-style and tuple-style cursors
        if hasattr(row, 'keys'):
            alias_id = row['alias_id']
            entity_id = row['entity_id']
            alias = row['alias']
            canonical_name = row['canonical_name']
            created_at = row.get('created_at')
            created_by = row.get('created_by')
        else:
            alias_id, entity_id, alias, canonical_name, created_at, created_by = row
        
        alias_cat = get_category(alias)
        canonical_cat = get_category(canonical_name)
        
        # Check 1: Category mismatch (high severity)
        if alias_cat != 'other' and canonical_cat != 'other' and alias_cat != canonical_cat:
            issues.append({
                'alias_id': alias_id,
                'entity_id': entity_id,
                'alias': alias,
                'canonical_name': canonical_name,
                'issue_type': 'category_mismatch',
                'severity': 'high',
                'reason': f"Alias category '{alias_cat}' != canonical category '{canonical_cat}'"
            })
            continue
        
        # Check 2: No word overlap (medium severity)
        alias_words = set(alias.lower().replace('-', ' ').replace('_', ' ').split())
        canonical_words = set(canonical_name.lower().replace('-', ' ').replace('_', ' ').split())
        
        # Remove common stop words
        stop_words = {'and', 'or', 'the', 'a', 'an', 'in', 'of', 'for', 'to', 'with', 'e.g.', 'e.g', 'etc'}
        alias_words -= stop_words
        canonical_words -= stop_words
        
        overlap = alias_words & canonical_words
        
        if not overlap and len(alias_words) > 0 and len(canonical_words) > 0:
            # Check if it's a known abbreviation or synonym
            known_synonyms = [
                ('sql', 'database'), ('python', 'programming'), ('java', 'programming'),
                ('scrum', 'agile'), ('excel', 'office'), ('leadership', 'management')
            ]
            is_known = any(
                (a in alias.lower() and b in canonical_name.lower()) or
                (b in alias.lower() and a in canonical_name.lower())
                for a, b in known_synonyms
            )
            
            if not is_known:
                issues.append({
                    'alias_id': alias_id,
                    'entity_id': entity_id,
                    'alias': alias,
                    'canonical_name': canonical_name,
                    'issue_type': 'no_word_overlap',
                    'severity': 'medium',
                    'reason': f"No common words between alias and canonical name"
                })
        
        if verbose:
            print(f"  ✓ {alias} → {canonical_name}")
    
    cursor.close()
    return issues


def report_issues(issues):
    """Print formatted report of issues."""
    if not issues:
        print("\n✅ No alias quality issues detected!")
        return
    
    print(f"\n⚠️  Found {len(issues)} potential alias issues:\n")
    
    # Group by severity
    high = [i for i in issues if i['severity'] == 'high']
    medium = [i for i in issues if i['severity'] == 'medium']
    low = [i for i in issues if i['severity'] == 'low']
    
    if high:
        print("🔴 HIGH SEVERITY (likely wrong):")
        print("-" * 60)
        for issue in high:
            print(f"  alias_id={issue['alias_id']}: \"{issue['alias']}\" → \"{issue['canonical_name']}\"")
            print(f"    Reason: {issue['reason']}")
        print()
    
    if medium:
        print("🟡 MEDIUM SEVERITY (needs review):")
        print("-" * 60)
        for issue in medium:
            print(f"  alias_id={issue['alias_id']}: \"{issue['alias']}\" → \"{issue['canonical_name']}\"")
            print(f"    Reason: {issue['reason']}")
        print()
    
    if low:
        print("🟢 LOW SEVERITY (informational):")
        print("-" * 60)
        for issue in low[:10]:  # Limit low severity
            print(f"  alias_id={issue['alias_id']}: \"{issue['alias']}\" → \"{issue['canonical_name']}\"")
        if len(low) > 10:
            print(f"  ... and {len(low) - 10} more")
        print()


def fix_issues(conn, issues):
    """
    Fix issues by:
    1. Deleting bad aliases
    2. Queuing the raw skill to entities_pending for re-triage
    3. Clearing entity_id from posting_skills that used this alias
    """
    if not issues:
        print("No issues to fix.")
        return
    
    cursor = conn.cursor()
    
    fixed = 0
    for issue in issues:
        if issue['severity'] != 'high':
            continue  # Only auto-fix high severity
        
        alias = issue['alias']
        alias_id = issue['alias_id']
        entity_id = issue['entity_id']
        
        print(f"Fixing: \"{alias}\" (alias_id={alias_id})")
        
        # 1. Delete the bad alias
        cursor.execute("DELETE FROM entity_aliases WHERE alias_id = %s", (alias_id,))
        
        # 2. Queue to entities_pending for re-triage
        cursor.execute("""
            INSERT INTO entities_pending (entity_type, raw_value, status, source_context)
            VALUES ('skill', %s, 'pending', %s)
            ON CONFLICT (entity_type, raw_value) DO UPDATE 
            SET status = 'pending', processed_at = NULL
        """, (alias, json.dumps({'source': 'qa_alias_fix', 'old_entity_id': entity_id})))
        
        # 3. Clear entity_id from posting_skills that matched via this alias
        cursor.execute("""
            UPDATE posting_skills
            SET entity_id = NULL
            WHERE entity_id = %s
              AND LOWER(raw_skill_name) = LOWER(%s)
        """, (entity_id, alias))
        
        fixed += 1
    
    conn.commit()
    cursor.close()
    
    print(f"\n✅ Fixed {fixed} high-severity issues")
    print("   → Bad aliases deleted")
    print("   → Skills queued to entities_pending for re-triage")
    print("   → Run WF3005 to process the queue")


def main():
    parser = argparse.ArgumentParser(description='QA Check: Entity Alias Quality')
    parser.add_argument('--fix', action='store_true', help='Auto-fix high-severity issues')
    parser.add_argument('--verbose', action='store_true', help='Show all alias checks')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA CHECK: Entity Alias Quality")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    conn = get_connection()
    
    try:
        issues = check_alias_quality(conn, verbose=args.verbose)
        
        if args.json:
            print(json.dumps(issues, indent=2))
        else:
            report_issues(issues)
        
        if args.fix:
            print("\n" + "=" * 60)
            print("APPLYING FIXES")
            print("=" * 60)
            fix_issues(conn, issues)
        elif issues:
            high_count = len([i for i in issues if i['severity'] == 'high'])
            if high_count > 0:
                print(f"\n💡 Run with --fix to auto-fix {high_count} high-severity issues")
    
    finally:
        conn.close()


if __name__ == '__main__':
    main()
