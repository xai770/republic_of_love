#!/usr/bin/env python3
"""
Export entity hierarchy as folder tree.

Creates a folder structure from entity_relationships is_a hierarchy:

  entity_registry/
  ├── INDEX.md
  ├── human_resources/
  │   ├── _index.md
  │   ├── hiring.md
  │   ├── onboarding.md
  │   └── ...
  ├── data_analytics/
  │   ├── _index.md
  │   ├── python.md
  │   └── sql.md
  └── ...

Usage:
    python tools/export_entity_hierarchy.py
    python tools/export_entity_hierarchy.py --entity-type skill_atomic --output ./skill_tree
"""

import sys
import os
import re
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras


def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', '192.168.1.196'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'by'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )


def slugify(name: str) -> str:
    """Convert name to filename-safe slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    if len(slug) > 80:
        slug = slug[:80].rsplit('_', 1)[0]
    return slug


def get_hierarchy(conn, leaf_type: str = 'skill_atomic') -> dict:
    """
    Build hierarchy from owl_relationships.
    
    Returns dict: {
        'roots': [root groups with no parent],
        'children': {parent_id: [child entities]},
        'entities': {owl_id: entity_data}
    }
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get all entities (groups and leaves)
    cursor.execute("""
        SELECT owl_id, canonical_name, owl_type, status
        FROM owl
        WHERE owl_type IN ('skill_group', %s)
          AND status = 'active'
    """, (leaf_type,))
    
    entities = {r['owl_id']: dict(r) for r in cursor.fetchall()}
    
    # Get all is_a relationships
    cursor.execute("""
        SELECT owl_id, related_owl_id
        FROM owl_relationships
        WHERE relationship = 'is_a'
    """)
    
    # Build parent->children mapping
    children = defaultdict(list)
    has_parent = set()
    
    for r in cursor.fetchall():
        child_id = r['owl_id']
        parent_id = r['related_owl_id']
        if child_id in entities and parent_id in entities:
            children[parent_id].append(child_id)
            has_parent.add(child_id)
    
    # Find roots (groups with no parent)
    roots = []
    for eid, e in owl.items():
        if e['owl_type'] == 'skill_group' and eid not in has_parent:
            roots.append(eid)
    
    return {
        'roots': sorted(roots, key=lambda x: entities[x]['canonical_name']),
        'children': dict(children),
        'entities': entities
    }


def generate_leaf_md(entity: dict, parent_name: str) -> str:
    """Generate markdown for a leaf entity (skill)."""
    name = entity['canonical_name']
    return f"""# {name.replace('_', ' ').title()}

**Type:** {entity['owl_type']}
**Group:** {parent_name.replace('_', ' ').title()}

## Description

_{name.replace('_', ' ')}_

## Related Skills

_Skills in the same group are considered related._
"""


def generate_group_index(entity: dict, children: list, entities: dict) -> str:
    """Generate _index.md for a group."""
    name = entity['canonical_name']
    
    # Separate subgroups from leaves
    subgroups = []
    leaves = []
    for c in children:
        ce = entities[c]
        if ce['owl_type'] == 'skill_group':
            subgroups.append(ce)
        else:
            leaves.append(ce)
    
    subgroups.sort(key=lambda x: x['canonical_name'])
    leaves.sort(key=lambda x: x['canonical_name'])
    
    sections = []
    
    if subgroups:
        sg_list = '\n'.join([
            f"- [{g['canonical_name'].replace('_', ' ').title()}]({slugify(g['canonical_name'])}/)"
            for g in subgroups
        ])
        sections.append(f"## Subgroups\n\n{sg_list}")
    
    if leaves:
        leaf_list = '\n'.join([
            f"- [{l['canonical_name'].replace('_', ' ').title()}]({slugify(l['canonical_name'])}.md)"
            for l in leaves
        ])
        sections.append(f"## Skills ({len(leaves)})\n\n{leaf_list}")
    
    return f"""# {name.replace('_', ' ').title()}

**Total items:** {len(children)}

{chr(10).join(sections)}
"""


def generate_main_index(roots: list, entities: dict, children: dict) -> str:
    """Generate main INDEX.md."""
    
    def count_descendants(eid):
        """Recursively count all descendants."""
        total = 0
        for cid in children.get(eid, []):
            if entities[cid]['owl_type'] == 'skill_group':
                total += count_descendants(cid)
            else:
                total += 1
        return total
    
    root_lines = []
    total_skills = 0
    for rid in roots:
        re = entities[rid]
        count = count_descendants(rid)
        total_skills += count
        root_lines.append(f"- [{re['canonical_name'].replace('_', ' ').title()}]({slugify(re['canonical_name'])}/) ({count} skills)")
    
    return f"""# Entity Hierarchy

This folder represents the skill taxonomy hierarchy.

## Structure

Skills are organized into groups using `is_a` relationships.
Groups can contain subgroups (recursive hierarchy).

## Statistics

- **Root Groups:** {len(roots)}
- **Total Skills:** {total_skills}

## Groups

{chr(10).join(root_lines)}

## Generated

Generated from `entity_relationships` table by `tools/export_entity_hierarchy.py`.
"""


def export_tree(hierarchy: dict, output_path: Path, entities: dict, children: dict):
    """Recursively export hierarchy to folder tree."""
    
    def export_entity(owl_id: int, parent_path: Path, parent_name: str = ""):
        entity = entities[owl_id]
        name = entity['canonical_name']
        slug = slugify(name)
        
        if entity['owl_type'] == 'skill_group':
            # Create folder for group
            group_path = parent_path / slug
            group_path.mkdir(parents=True, exist_ok=True)
            
            # Get children
            group_children = children.get(owl_id, [])
            
            # Create _index.md
            index_file = group_path / "_index.md"
            index_file.write_text(generate_group_index(entity, group_children, entities))
            
            # Export children
            for cid in group_children:
                export_entity(cid, group_path, name)
            
            return 1 + sum(1 for _ in group_children)
        else:
            # Create .md file for leaf
            leaf_file = parent_path / f"{slug}.md"
            leaf_file.write_text(generate_leaf_md(entity, parent_name))
            return 1
    
    # Clear existing
    if output_path.exists():
        print(f"Clearing {output_path}")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)
    
    total_files = 0
    for root_id in hierarchy['roots']:
        total_files += export_entity(root_id, output_path, "")
    
    # Create main index
    main_index = output_path / "INDEX.md"
    main_index.write_text(generate_main_index(hierarchy['roots'], entities, children))
    
    return total_files


def print_tree(hierarchy: dict, max_depth: int = 3):
    """Print hierarchy as ASCII tree (preview mode)."""
    entities = hierarchy['entities']
    children = hierarchy['children']
    
    def print_node(owl_id: int, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        
        entity = entities[owl_id]
        name = entity['canonical_name']
        etype = entity['owl_type']
        
        node_children = children.get(owl_id, [])
        count = len(node_children)
        
        if etype == 'skill_group':
            print(f"{prefix}📁 {name} ({count})")
        else:
            print(f"{prefix}📄 {name}")
        
        for i, cid in enumerate(sorted(node_children, key=lambda x: entities[x]['canonical_name'])):
            is_last = i == len(node_children) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            print_node(cid, prefix + connector, depth + 1)
    
    print("\n📦 Entity Hierarchy\n")
    for rid in hierarchy['roots'][:10]:  # Limit to first 10 roots
        print_node(rid)
        print()


def main():
    parser = argparse.ArgumentParser(description='Export entity hierarchy as folder tree')
    parser.add_argument('--entity-type', default='skill_atomic', help='Leaf entity type')
    parser.add_argument('--output', default='./entity_registry', help='Output folder')
    parser.add_argument('--preview', action='store_true', help='Preview tree without exporting')
    parser.add_argument('--depth', type=int, default=3, help='Max depth for preview')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Entity Hierarchy Export")
    print("=" * 60)
    
    conn = get_connection()
    
    print(f"\nBuilding hierarchy for {args.owl_type}...")
    hierarchy = get_hierarchy(conn, args.owl_type)
    
    print(f"Found {len(hierarchy['roots'])} root groups")
    print(f"Total entities: {len(hierarchy['entities'])}")
    print(f"Total relationships: {sum(len(c) for c in hierarchy['children'].values())}")
    
    if args.preview:
        print_tree(hierarchy, args.depth)
    else:
        output_path = Path(args.output)
        print(f"\nExporting to {output_path}...")
        total = export_tree(hierarchy, output_path, hierarchy['entities'], hierarchy['children'])
        print(f"Created {total} files")
        print(f"\nDone! Browse at: {output_path.absolute()}")
    
    conn.close()


if __name__ == '__main__':
    main()
