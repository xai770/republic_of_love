#!/usr/bin/env python3
"""
Export Skill Hierarchy to Folder Structure (Turing DB Compatible)
==================================================================

Generates skills_taxonomy/ directory from skill_hierarchy and skill_aliases tables.
Works with current Turing database schema (skill_id, parent_skill_id).

Created: 2025-11-09
Author: Arden
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.database import get_connection
from config.paths import SKILLS_TAXONOMY_DIR

# Output directory
OUTPUT_DIR = SKILLS_TAXONOMY_DIR

def sanitize_name(name):
    """Convert skill name to valid folder/file name"""
    if not name:
        return "Unnamed"
    # Replace problematic characters
    sanitized = str(name).replace('/', '_').replace('\\', '_').replace(':', '_')
    sanitized = sanitized.replace('?', '').replace('*', '').replace('|', '_')
    sanitized = sanitized.replace('<', '_').replace('>', '_').replace('"', '')
    sanitized = sanitized.replace('\n', ' ').replace('\r', '')
    return sanitized.strip() or "Unnamed"

def get_root_skills(conn):
    """Get top-level categories (parents that aren't children)"""
    cur = conn.cursor()
    
    cur.execute("""
        WITH parent_skills AS (
            SELECT DISTINCT parent_skill_id 
            FROM skill_hierarchy 
            WHERE parent_skill_id IS NOT NULL
        ),
        child_skills AS (
            SELECT DISTINCT skill_id 
            FROM skill_hierarchy
        )
        SELECT 
            sa.skill_id,
            sa.skill_name,
            sa.display_name
        FROM parent_skills ps
        JOIN skill_aliases sa ON sa.skill_id = ps.parent_skill_id
        WHERE ps.parent_skill_id NOT IN (SELECT skill_id FROM child_skills)
        ORDER BY sa.display_name
    """)
    
    roots = cur.fetchall()
    cur.close()
    return roots

def get_children(conn, parent_skill_id):
    """Get direct children of a skill"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            sh.skill_id,
            sa.skill_name,
            sa.display_name,
            sh.strength
        FROM skill_hierarchy sh
        JOIN skill_aliases sa ON sa.skill_id = sh.skill_id
        WHERE sh.parent_skill_id = %s
        ORDER BY sa.display_name
    """, (parent_skill_id,))
    
    children = cur.fetchall()
    cur.close()
    return children

def has_children(conn, skill_id):
    """Check if skill has children"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM skill_hierarchy 
        WHERE parent_skill_id = %s
    """, (skill_id,))
    
    count = cur.fetchone()['count']
    cur.close()
    return count > 0

def get_skill_details(conn, skill_id):
    """Get full details for a skill"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            skill_id,
            skill_name,
            skill_alias,
            display_name,
            language,
            confidence,
            created_by,
            created_at,
            notes
        FROM skill_aliases
        WHERE skill_id = %s
    """, (skill_id,))
    
    details = cur.fetchone()
    cur.close()
    return details

def create_skill_file(skill_details, path_parts, output_dir):
    """Create markdown file for a leaf skill"""
    skill_id = skill_details['skill_id']
    skill_name = skill_details['skill_name']
    display_name = skill_details['display_name'] or skill_name
    
    # Create file content
    content = f"""# SKILL: {display_name}

## Metadata

**Skill ID:** {skill_id}
**Skill Name:** {skill_name}
**Skill Alias:** {skill_details['skill_alias'] or skill_name}
**Display Name:** {display_name}
**Language:** {skill_details['language'] or 'en'}
**Confidence:** {skill_details['confidence'] or 0.90:.2f}
**Created By:** {skill_details['created_by'] or 'Unknown'}
**Created At:** {skill_details['created_at']}

## Hierarchy Path

```
{' > '.join(path_parts)}
```

## Notes

{skill_details['notes'] or 'No notes available'}

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # Create file
    filename = f"{sanitize_name(skill_name)}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def create_category_readme(category_name, child_count, output_dir):
    """Create README for a category folder"""
    content = f"""# Category: {category_name}

**Direct Children:** {child_count}

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    readme_path = output_dir / '_README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

def build_hierarchy_recursive(conn, skill_id, skill_name, display_name, output_dir, path_parts, visited_ids=None):
    """Recursively build folder structure"""
    # Cycle detection
    if visited_ids is None:
        visited_ids = set()
    
    if skill_id in visited_ids:
        print(f"   ⚠️  CYCLE DETECTED: {display_name or skill_name} (ID: {skill_id}) - skipping")
        return
    
    visited_ids = visited_ids | {skill_id}  # Create new set with this ID
    
    folder_name = sanitize_name(display_name or skill_name)
    current_dir = output_dir / folder_name
    current_path = path_parts + [display_name or skill_name]
    
    # Get children
    children = get_children(conn, skill_id)
    
    if children:
        # This is a category - create folder
        current_dir.mkdir(parents=True, exist_ok=True)
        create_category_readme(display_name or skill_name, len(children), current_dir)
        
        # Process each child
        for child in children:
            child_id = child['skill_id']
            child_name = child['skill_name']
            child_display = child['display_name']
            
            if has_children(conn, child_id):
                # Child is also a category
                build_hierarchy_recursive(conn, child_id, child_name, child_display, current_dir, current_path, visited_ids)
            else:
                # Child is a leaf skill
                skill_details = get_skill_details(conn, child_id)
                create_skill_file(skill_details, current_path + [child_display or child_name], current_dir)
    else:
        # This is a leaf skill (no children)
        # Create in parent directory, not as subfolder
        skill_details = get_skill_details(conn, skill_id)
        create_skill_file(skill_details, path_parts, output_dir.parent)

def create_index_file(output_dir, stats):
    """Create INDEX.md with navigation and statistics"""
    content = f"""# Skills Taxonomy Index

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Database:** turing

---

## Statistics

- **Top-level categories:** {stats['root_count']}
- **Total skills:** {stats['total_skills']}
- **Leaf skills:** {stats['leaf_skills']}
- **Categories:** {stats['categories']}

## Navigation

- Browse folders to explore categories
- Each category has a `_README.md` file with details
- Leaf skills are `.md` files with complete metadata
- Use `tree` command to see full structure
- Use `find` or `grep` to search for specific skills

## Commands

```bash
# View tree structure (first 3 levels)
tree -L 3 {output_dir}

# Find all skills containing 'security'
find {output_dir} -name '*security*.md' -o -name '*Security*.md'

# Search for specific content
grep -r 'Financial' {output_dir}

# Count total files
find {output_dir} -type f -name '*.md' | wc -l
```

---

*This hierarchy was automatically generated from the turing database.*
"""
    
    index_path = output_dir / 'INDEX.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print("="*70)
    print("SKILLS TAXONOMY EXPORT")
    print("="*70)
    print()
    
    # Clean and recreate output directory
    print(f"📁 Output directory: {OUTPUT_DIR}")
    if OUTPUT_DIR.exists():
        print("   ⚠️  Directory exists - will be overwritten")
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    print("🔌 Connecting to turing database...")
    conn = get_connection()
    
    # Get statistics
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM skill_aliases")
    total_skills = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(DISTINCT skill_id) as count FROM skill_hierarchy")
    skills_in_hierarchy = cur.fetchone()['count']
    
    cur.close()
    
    print(f"📊 Total skills: {total_skills}")
    print(f"📊 Skills in hierarchy: {skills_in_hierarchy}")
    print()
    
    # Get root categories
    print("🌳 Building hierarchy...")
    roots = get_root_skills(conn)
    print(f"   Found {len(roots)} top-level categories")
    print()
    
    # Build hierarchy for each root
    categories_created = 0
    files_created = 0
    
    for i, root in enumerate(roots, 1):
        root_id = root['skill_id']
        root_name = root['skill_name']
        root_display = root['display_name']
        
        print(f"[{i}/{len(roots)}] Processing: {root_display or root_name}")
        
        build_hierarchy_recursive(conn, root_id, root_name, root_display, OUTPUT_DIR, [])
        categories_created += 1
        
        # Count files created
        if (OUTPUT_DIR / sanitize_name(root_display or root_name)).exists():
            file_count = len(list((OUTPUT_DIR / sanitize_name(root_display or root_name)).rglob('*.md')))
            files_created += file_count
            print(f"    ✅ {file_count} skills exported")
    
    # Create index file
    stats = {
        'root_count': len(roots),
        'total_skills': total_skills,
        'leaf_skills': files_created,
        'categories': categories_created
    }
    
    create_index_file(OUTPUT_DIR, stats)
    
    conn.close()
    
    print()
    print("="*70)
    print("✅ EXPORT COMPLETE!")
    print(f"   📁 Location: {OUTPUT_DIR}")
    print(f"   📊 {categories_created} categories")
    print(f"   📊 {files_created} skill files")
    print("="*70)

if __name__ == "__main__":
    main()
