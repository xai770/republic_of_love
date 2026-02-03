#!/usr/bin/env python3
"""
Generate skill hierarchy folder tree from WF3011 classifications.

Creates NESTED hierarchy:
  entity_registry_new/
  ├── INDEX.md
  ├── programming_languages/           (root group - no parent)
  │   ├── _index.md
  │   ├── python.md
  │   ├── java.md
  │   └── web_frameworks/              (child group)
  │       ├── _index.md
  │       └── react.md
  ├── aml_kyc_compliance/              (root group)
  │   ├── _index.md
  │   ├── aml_kyc_frameworks/          (child group)
  │   │   └── ...
  │   └── ...
  └── ...

Works with:
- owl_type: skill_atomic, skill_group, skill_root
- relationship: is_a (group→group, skill→group)
"""

import sys
import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '.')
from core.database import get_connection

REGISTRY_PATH = Path('/home/xai/Documents/ty_learn/entity_registry_new')


def slugify(name):
    """Convert name to filename-safe slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    if len(slug) > 80:
        slug = slug[:80].rsplit('_', 1)[0]
    return slug


def get_hierarchy(conn):
    """
    Build NESTED hierarchy from database.
    Returns:
      - group_children: {parent_group: [child_groups]}
      - group_skills: {group: [skills]}
      - root_groups: [groups with no parent or parent=skill_root]
    """
    cur = conn.cursor()
    
    # 1. Get group→group relationships (child group → parent group)
    cur.execute('''
        SELECT 
            child.canonical_name as child_group,
            parent.canonical_name as parent_group
        FROM owl child
        JOIN owl_relationships er ON child.owl_id = er.owl_id AND er.relationship = 'is_a'
        JOIN owl parent ON er.related_owl_id = parent.owl_id
        WHERE child.owl_type = 'skill_group'
        AND child.status = 'active'
        AND parent.owl_type IN ('skill_group', 'skill_root')
    ''')
    
    group_parent = {}  # child → parent
    group_children = defaultdict(list)  # parent → [children]
    
    for r in cur.fetchall():
        child = r['child_group']
        parent = r['parent_group']
        group_parent[child] = parent
        if parent != 'skill_root':  # Don't add skill_root as a folder
            group_children[parent].append(child)
    
    print(f"Found {len(group_parent)} groups with parent relationships")
    print(f"Found {len(group_children)} groups that have child groups")
    
    # 2. Get skill→group relationships
    cur.execute('''
        SELECT 
            s.canonical_name as skill,
            s.owl_id as skill_id,
            g.canonical_name as group_name
        FROM owl s
        JOIN owl_relationships er ON s.owl_id = er.owl_id AND er.relationship = 'is_a'
        JOIN owl g ON er.related_owl_id = g.owl_id
        WHERE s.owl_type = 'skill_atomic'
        AND s.status = 'active'
        AND g.owl_type = 'skill_group'
        ORDER BY g.canonical_name, s.canonical_name
    ''')
    
    group_skills = defaultdict(list)
    for r in cur.fetchall():
        # Include owl_id for uniqueness
        group_skills[r['group_name']].append((r['skill'], r['skill_id']))
    
    print(f"Found {sum(len(s) for s in group_skills.values())} skills across {len(group_skills)} groups")
    
    # 3. Find root groups (no parent, or parent = skill_root)
    all_groups = set(group_skills.keys()) | set(group_children.keys())
    root_groups = []
    for g in all_groups:
        parent = group_parent.get(g)
        if parent is None or parent == 'skill_root':
            root_groups.append(g)
    
    print(f"Found {len(root_groups)} root-level groups")
    
    return group_children, group_skills, sorted(root_groups)


def generate_skill_md(skill_name, group_name, skill_id):
    """Generate markdown content for a skill."""
    return f"""# {skill_name.replace('_', ' ').title()}

**Entity ID:** {skill_id}
**Group:** {group_name.replace('_', ' ').title()}

## Description

{skill_name.replace('_', ' ')}

## Related Skills

_Other skills in {group_name.replace('_', ' ')}_
"""


def generate_group_index(group_name, skills, child_groups):
    """Generate _index.md for a group."""
    content = f"""# {group_name.replace('_', ' ').title()}

**Total Skills:** {len(skills)}
"""
    
    if child_groups:
        subgroup_list = '\n'.join([f'- [{g.replace("_", " ").title()}]({g}/)' for g in sorted(child_groups)])
        content += f"""
## Subgroups

{subgroup_list}
"""
    
    if skills:
        skill_list = '\n'.join([f'- [{s.replace("_", " ").title()}]({slugify(s)}_{sid}.md)' for s, sid in sorted(skills)[:50]])
        more = f"\n\n_...and {len(skills) - 50} more skills_" if len(skills) > 50 else ""
        content += f"""
## Skills

{skill_list}{more}
"""
    
    return content


def generate_main_index(root_groups, total_groups, total_skills):
    """Generate main INDEX.md."""
    group_list = '\n'.join([
        f'- [{g.replace("_", " ").title()}]({g}/)'
        for g in sorted(root_groups)
    ])
    return f"""# Skill Hierarchy - Entity Registry

Generated from WF3011 Conversational Hierarchy Classifier.

## Statistics

- **Root Groups:** {len(root_groups)}
- **Total Groups:** {total_groups}
- **Total Skills:** {total_skills}

## Root Groups

{group_list}

## Generated

Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def create_group_folder(base_path, group_name, group_children, group_skills, stats, visited=None):
    """Recursively create group folder with children. Detects cycles."""
    if visited is None:
        visited = set()
    
    # Cycle detection
    if group_name in visited:
        print(f"    ⚠️  Skipping cycle: {group_name}")
        return 0
    visited = visited | {group_name}  # New set for this branch
    
    group_path = base_path / group_name
    group_path.mkdir(parents=True, exist_ok=True)
    
    skills = group_skills.get(group_name, [])
    children = group_children.get(group_name, [])
    
    # Create skill files in this group
    for skill_name, skill_id in skills:
        slug = slugify(skill_name)
        skill_file = group_path / f"{slug}_{skill_id}.md"
        skill_file.write_text(generate_skill_md(skill_name, group_name, skill_id))
        stats['skill_files'] += 1
    
    # Recursively create child group folders
    for child in children:
        create_group_folder(group_path, child, group_children, group_skills, stats, visited)
    
    # Create group _index.md
    index_file = group_path / "_index.md"
    index_file.write_text(generate_group_index(group_name, skills, children))
    stats['groups'] += 1
    
    return len(skills)


def main():
    print("=" * 60)
    print("Generating Nested Skill Hierarchy Folder Tree")
    print("=" * 60)
    
    # Clear existing registry
    if REGISTRY_PATH.exists():
        print(f"Clearing existing registry at {REGISTRY_PATH}")
        shutil.rmtree(REGISTRY_PATH)
    REGISTRY_PATH.mkdir(parents=True)
    
    with get_connection() as conn:
        group_children, group_skills, root_groups = get_hierarchy(conn)
    
    if not root_groups:
        print("No root groups found!")
        return
    
    print()
    print(f"Creating nested folder structure with {len(root_groups)} root groups...")
    print()
    
    # Create folders and files recursively
    stats = {'skill_files': 0, 'groups': 0}
    
    for group_name in root_groups:
        skill_count = create_group_folder(REGISTRY_PATH, group_name, group_children, group_skills, stats)
        child_count = len(group_children.get(group_name, []))
        print(f"  📁 {group_name}/ - {skill_count} skills, {child_count} subgroups")
    
    # Create main INDEX.md
    total_skills = sum(len(s) for s in group_skills.values())
    main_index = REGISTRY_PATH / "INDEX.md"
    main_index.write_text(generate_main_index(root_groups, stats['groups'], total_skills))
    
    print()
    print(f"✅ Created {stats['skill_files']} skill files")
    print(f"   Across {stats['groups']} groups ({len(root_groups)} root)")
    print()
    print(f"📂 Registry location: {REGISTRY_PATH}")


if __name__ == '__main__':
    main()
