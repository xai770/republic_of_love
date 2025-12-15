#!/usr/bin/env python3
"""
Export Skill Hierarchy to Folder Structure
==========================================

Creates a navigable folder/file hierarchy from skill_hierarchy table.
Each skill becomes a text file containing metadata.
Folders represent categories.

Output: skills_taxonomy/ directory with complete hierarchy

Created: 2025-10-29
Author: Arden
"""

import psycopg2
import os
from pathlib import Path
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# Output directory
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/skills_taxonomy')

def sanitize_folder_name(name):
    """Convert skill name to valid folder/file name"""
    # Replace problematic characters
    sanitized = name.replace('/', '_').replace('\\', '_').replace(':', '_')
    sanitized = sanitized.replace('?', '').replace('*', '').replace('|', '_')
    sanitized = sanitized.replace('<', '_').replace('>', '_').replace('"', '')
    return sanitized.strip()

def fetch_skill_details(conn, skill):
    """Get all details about a skill"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            skill_alias,
            skill,
            display_name,
            language,
            confidence,
            created_by,
            notes,
            created_at
        FROM skill_aliases
        WHERE skill = %s
        LIMIT 1
    """, (skill,))
    
    result = cur.fetchone()
    cur.close()
    
    if result:
        return {
            'skill_alias': result[0],
            'skill': result[1],
            'display_name': result[2],
            'language': result[3],
            'confidence': result[4],
            'created_by': result[5],
            'notes': result[6],
            'created_at': result[7]
        }
    return None

def get_skill_path(conn, skill, parent_path=None):
    """Get full path from root to skill - simplified version using parent_path tracking"""
    # If parent_path is provided, just append this skill
    if parent_path:
        return parent_path + [skill]
    
    # Otherwise build path by following parent links
    path = [skill]
    current = skill
    
    cur = conn.cursor()
    
    # Follow parent chain (with max depth to prevent infinite loops)
    for _ in range(20):
        cur.execute("""
            SELECT parent_skill 
            FROM skill_hierarchy 
            WHERE skill = %s
            LIMIT 1
        """, (current,))
        
        result = cur.fetchone()
        if not result:
            break
        
        parent = result[0]
        path.insert(0, parent)
        current = parent
    
    cur.close()
    return path

def get_skill_children(conn, parent_skill):
    """Get direct children of a skill"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT skill, strength
        FROM skill_hierarchy
        WHERE parent_skill = %s
        ORDER BY skill
    """, (parent_skill,))
    
    children = cur.fetchall()
    cur.close()
    
    return children

def get_root_skills(conn):
    """Get all top-level skills (those that are parents but not children)"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT parent_skill
        FROM skill_hierarchy
        WHERE parent_skill NOT IN (
            SELECT skill FROM skill_hierarchy
        )
        ORDER BY parent_skill
    """)
    
    roots = [row[0] for row in cur.fetchall()]
    cur.close()
    
    return roots

def get_leaf_skills(conn):
    """Get all leaf skills (those that are children but not parents)"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT skill
        FROM skill_hierarchy
        WHERE skill NOT IN (
            SELECT parent_skill FROM skill_hierarchy
        )
        ORDER BY skill
    """)
    
    leaves = [row[0] for row in cur.fetchall()]
    cur.close()
    
    return leaves

def create_skill_file(skill_path, skill_data, path_from_root, is_category=False):
    """Create a text file with skill metadata"""
    
    content_lines = []
    
    if is_category:
        content_lines.append(f"# CATEGORY: {skill_data['display_name']}")
        content_lines.append("")
        content_lines.append("This is an intermediate category node in the skill taxonomy.")
    else:
        content_lines.append(f"# SKILL: {skill_data['display_name']}")
    
    content_lines.append("")
    content_lines.append("## Metadata")
    content_lines.append("")
    content_lines.append(f"**Skill ID:** {skill_data['skill']}")
    content_lines.append(f"**Display Name:** {skill_data['display_name']}")
    content_lines.append(f"**Skill Alias:** {skill_data['skill_alias']}")
    content_lines.append(f"**Language:** {skill_data['language']}")
    content_lines.append(f"**Confidence:** {skill_data['confidence']}")
    content_lines.append(f"**Created By:** {skill_data['created_by']}")
    
    if skill_data['created_at']:
        content_lines.append(f"**Created At:** {skill_data['created_at']}")
    
    content_lines.append("")
    content_lines.append("## Hierarchy Path")
    content_lines.append("")
    path_str = " > ".join([p.replace('_', ' ').title() for p in path_from_root])
    content_lines.append(f"```")
    content_lines.append(path_str)
    content_lines.append(f"```")
    
    if skill_data['notes']:
        content_lines.append("")
        content_lines.append("## Notes")
        content_lines.append("")
        content_lines.append(skill_data['notes'])
    
    content_lines.append("")
    content_lines.append("---")
    content_lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    # Write file
    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content_lines))

def build_hierarchy_recursively(conn, skill, current_path, stats, parent_path=None, visited_skills=None):
    """Recursively build folder structure with cycle detection"""
    
    # Initialize visited set for cycle detection
    if visited_skills is None:
        visited_skills = set()
    
    # Check for cycles
    if skill in visited_skills:
        print(f"   ⚠️  Cycle detected: {skill} (skipping)")
        stats['cycles'] = stats.get('cycles', 0) + 1
        return
    
    # Add to visited set
    visited_skills.add(skill)
    
    # Build path for this skill
    if parent_path is None:
        # This is a root skill - start fresh path
        skill_path_list = [skill]
    else:
        # Append to parent's path
        skill_path_list = parent_path + [skill]
    
    # Get skill details
    skill_data = fetch_skill_details(conn, skill)
    if not skill_data:
        print(f"   ⚠️  No data found for {skill}")
        visited_skills.remove(skill)
        return
    
    # Create sanitized folder/file name
    safe_name = sanitize_folder_name(skill_data['display_name'] or skill)
    
    # Check if this skill has children (is a category)
    children = get_skill_children(conn, skill)
    
    if children:
        # This is a category - create a folder
        folder_path = current_path / safe_name
        folder_path.mkdir(exist_ok=True)
        
        # Create a README.md in the folder with category info
        readme_path = folder_path / "_README.md"
        create_skill_file(readme_path, skill_data, skill_path_list, is_category=True)
        
        stats['categories'] += 1
        
        # Recursively process children (pass the path and visited set along)
        for child_skill, strength in children:
            build_hierarchy_recursively(conn, child_skill, folder_path, stats, skill_path_list, visited_skills.copy())
    else:
        # This is a leaf skill - create a file
        file_path = current_path / f"{safe_name}.md"
        create_skill_file(file_path, skill_data, skill_path_list, is_category=False)
        
        stats['skills'] += 1
    
    # Remove from visited set (backtracking)
    visited_skills.remove(skill)

def export_to_folders():
    """Main export function"""
    
    print("=" * 80)
    print("📁 EXPORTING SKILL HIERARCHY TO FOLDER STRUCTURE")
    print("=" * 80)
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    # Create output directory
    if OUTPUT_DIR.exists():
        print(f"⚠️  Directory already exists. Contents will be overwritten.")
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get root skills
    print("📊 Analyzing hierarchy...")
    roots = get_root_skills(conn)
    leaves = get_leaf_skills(conn)
    
    print(f"   Found {len(roots)} top-level categories")
    print(f"   Found {len(leaves)} leaf skills\n")
    
    # Statistics
    stats = {
        'categories': 0,
        'skills': 0
    }
    
    # Build hierarchy for each root
    print("🌳 Building folder structure...\n")
    
    for i, root in enumerate(roots, 1):
        print(f"[{i}/{len(roots)}] Processing {root}...")
        build_hierarchy_recursively(conn, root, OUTPUT_DIR, stats)
    
    # Create master index
    print("\n📝 Creating master index...")
    
    index_path = OUTPUT_DIR / "INDEX.md"
    index_lines = [
        "# Skills Taxonomy Index",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Database:** {DB_CONFIG['database']}",
        "",
        "---",
        "",
        "## Statistics",
        "",
        f"- **Top-level categories:** {len(roots)}",
        f"- **Total categories:** {stats['categories']}",
        f"- **Total skills:** {stats['skills']}",
        f"- **Total items:** {stats['categories'] + stats['skills']}",
        "",
        "## Top-Level Categories",
        ""
    ]
    
    for root in roots:
        root_display = root.replace('_', ' ').title()
        root_folder = sanitize_folder_name(root)
        children = get_skill_children(conn, root)
        index_lines.append(f"- **{root_display}** - {len(children)} direct children")
    
    index_lines.extend([
        "",
        "## Navigation",
        "",
        "- Browse folders to explore categories",
        "- Each category has a `_README.md` file with details",
        "- Leaf skills are `.md` files with complete metadata",
        "- Use `tree` command to see full structure",
        "- Use `find` or `grep` to search for specific skills",
        "",
        "## Commands",
        "",
        "```bash",
        "# View tree structure (first 3 levels)",
        f"tree -L 3 {OUTPUT_DIR}",
        "",
        "# Find all skills containing 'security'",
        f"find {OUTPUT_DIR} -name '*Security*.md'",
        "",
        "# Search for specific content",
        f"grep -r 'Financial' {OUTPUT_DIR}",
        "",
        "# Count total files",
        f"find {OUTPUT_DIR} -type f -name '*.md' | wc -l",
        "```",
        "",
        "---",
        "",
        "*This hierarchy was automatically generated from the base_yoga database.*"
    ])
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(index_lines))
    
    conn.close()
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ EXPORT COMPLETE")
    print("=" * 80)
    print(f"\n📂 Output: {OUTPUT_DIR}")
    print(f"\n📊 Created:")
    print(f"   {stats['categories']} category folders")
    print(f"   {stats['skills']} skill files")
    print(f"   1 master index (INDEX.md)")
    
    if stats.get('cycles', 0) > 0:
        print(f"\n⚠️  Detected {stats['cycles']} cycles (skipped to prevent infinite loops)")
    
    print(f"\n🌳 Browse the hierarchy:")
    print(f"   cd {OUTPUT_DIR}")
    print(f"   tree -L 3")
    print(f"\n🔍 Search for skills:")
    print(f"   find {OUTPUT_DIR} -name '*Network*.md'")
    print(f"   grep -r 'Financial' {OUTPUT_DIR}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        export_to_folders()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
