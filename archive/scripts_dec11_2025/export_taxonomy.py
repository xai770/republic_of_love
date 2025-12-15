#!/usr/bin/env python3
"""
Export Skills Taxonomy to Filesystem

Creates a directory structure representing the current skills hierarchy:
  skills_taxonomy/
    _SNAPSHOT_YYYY-MM-DD_HHMMSS/
      category_name/
        skill_name.txt  (contains display_name)

Usage:
    python3 scripts/export_taxonomy.py              # Creates timestamped snapshot
    python3 scripts/export_taxonomy.py --current    # Creates/updates 'current' symlink
"""

import os
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


def sanitize_filename(name: str) -> str:
    """Replace problematic characters for filesystem."""
    return re.sub(r'[/\\:*?"<>|]', '_', name)


def get_db_connection():
    """Get database connection."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "turing"),
        user=os.getenv("DB_USER", "base_admin"),
        password=os.getenv("DB_PASSWORD", "")
    )


def export_taxonomy(base_dir: Path, snapshot_name: str) -> dict:
    """Export current taxonomy to filesystem."""
    
    snapshot_dir = base_dir / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get hierarchy: parent -> children
    cursor.execute("""
        SELECT 
            parent.canonical_name as category,
            parent.entity_id as category_id,
            child.canonical_name as skill,
            child.entity_id as skill_id,
            COALESCE(en.display_name, child.canonical_name) as display_name
        FROM entity_relationships er
        JOIN entities parent ON er.related_entity_id = parent.entity_id
        JOIN entities child ON er.entity_id = child.entity_id
        LEFT JOIN entity_names en ON child.entity_id = en.entity_id AND en.is_primary = true
        WHERE er.relationship = 'child_of'
          AND parent.status = 'active'
          AND child.status = 'active'
          AND parent.entity_id IN (
            -- Top-level categories: no parent, has children
            SELECT e.entity_id FROM entities e
            WHERE e.entity_type = 'skill' 
              AND e.status = 'active'
              AND NOT EXISTS (
                SELECT 1 FROM entity_relationships r 
                WHERE r.entity_id = e.entity_id AND r.relationship = 'child_of'
              )
          )
        ORDER BY parent.canonical_name, child.canonical_name
    """)
    
    rows = cursor.fetchall()
    
    # Get stats
    cursor.execute("""
        SELECT COUNT(*) as total_active 
        FROM entities 
        WHERE entity_type = 'skill' AND status = 'active'
    """)
    total_active = cursor.fetchone()['total_active']
    
    cursor.execute("""
        SELECT COUNT(*) as total_decisions,
               SUM(CASE WHEN applied_at IS NOT NULL THEN 1 ELSE 0 END) as applied
        FROM registry_decisions
    """)
    decisions = cursor.fetchone()
    
    conn.close()
    
    # Create directory structure
    counts = {}
    for row in rows:
        category = sanitize_filename(row['category'])
        skill = sanitize_filename(row['skill'])
        display = row['display_name']
        
        cat_dir = snapshot_dir / category
        cat_dir.mkdir(exist_ok=True)
        
        skill_file = cat_dir / f"{skill}.txt"
        skill_file.write_text(f"{display}\n")
        
        counts[category] = counts.get(category, 0) + 1
    
    # Write metadata
    metadata = snapshot_dir / "_METADATA.txt"
    with open(metadata, 'w') as f:
        f.write(f"Taxonomy Snapshot\n")
        f.write(f"=================\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Active skills: {total_active}\n")
        f.write(f"Registry decisions: {decisions['total_decisions']} ({decisions['applied']} applied)\n")
        f.write(f"\n")
        f.write(f"Categories ({len(counts)}):\n")
        for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
            f.write(f"  {cat}: {count} skills\n")
        f.write(f"\nTotal in hierarchy: {sum(counts.values())} skills\n")
    
    return {
        "snapshot_dir": str(snapshot_dir),
        "categories": len(counts),
        "skills_in_hierarchy": sum(counts.values()),
        "total_active": total_active,
        "counts": counts
    }


def main():
    parser = argparse.ArgumentParser(description="Export skills taxonomy to filesystem")
    parser.add_argument("--current", action="store_true", 
                        help="Create/update 'current' symlink to latest snapshot")
    parser.add_argument("--dir", default="skills_taxonomy",
                        help="Base directory for exports (default: skills_taxonomy)")
    args = parser.parse_args()
    
    base_dir = Path(args.dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_name = f"_SNAPSHOT_{timestamp}"
    
    print(f"Exporting taxonomy to {base_dir / snapshot_name}...")
    
    result = export_taxonomy(base_dir, snapshot_name)
    
    print(f"\n✅ Export complete!")
    print(f"   Categories: {result['categories']}")
    print(f"   Skills in hierarchy: {result['skills_in_hierarchy']}")
    print(f"   Total active skills: {result['total_active']}")
    print(f"\nCounts per category:")
    for cat, count in sorted(result['counts'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    if args.current:
        current_link = base_dir / "current"
        if current_link.is_symlink():
            current_link.unlink()
        current_link.symlink_to(snapshot_name)
        print(f"\n🔗 Symlink 'current' -> {snapshot_name}")
    
    print(f"\n📁 {result['snapshot_dir']}")


if __name__ == "__main__":
    main()
