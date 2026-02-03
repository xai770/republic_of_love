#!/usr/bin/env python3
"""
Generate entity_registry folder tree from database hierarchy.

Creates:
  entity_registry/
  ├── INDEX.md
  ├── technology/
  │   ├── _index.md
  │   ├── python_programming.md
  │   └── ...
  ├── cybersecurity/
  │   └── ...
  └── ...
"""

import sys
import os
import re
from pathlib import Path

sys.path.insert(0, '.')
from core.database import get_connection

REGISTRY_PATH = Path('/home/xai/Documents/ty_learn/entity_registry')


def slugify(name):
    """Convert skill name to filename-safe slug."""
    # Lowercase
    slug = name.lower()
    # Replace special chars with underscore
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    # Truncate if too long
    if len(slug) > 80:
        slug = slug[:80].rsplit('_', 1)[0]
    return slug


def generate_skill_md(skill_name, domain_name, confidence='high'):
    """Generate markdown content for a skill."""
    return f"""# {skill_name}

**Domain:** {domain_name}
**Confidence:** {confidence}

## Description

{skill_name}

## Related Skills

_To be populated_

## Usage in Postings

_To be populated_
"""


def generate_index_md(domain_name, skills):
    """Generate _index.md for a domain."""
    skill_list = '\n'.join([f'- [{s}]({slugify(s)}.md)' for s in sorted(skills)])
    return f"""# {domain_name.replace('_', ' ').title()}

**Total Skills:** {len(skills)}

## Skills

{skill_list}
"""


def generate_main_index(domains):
    """Generate main INDEX.md."""
    domain_list = '\n'.join([
        f'- [{d.replace("_", " ").title()}]({d}/) ({c} skills)'
        for d, c in sorted(domains.items(), key=lambda x: -x[1])
    ])
    return f"""# Entity Registry - Skill Taxonomy

This folder contains the canonical skill hierarchy for job-profile matching.

## Domains

{domain_list}

## Generated

This structure was generated from the database by `tools/generate_entity_registry.py`.
"""


def main():
    print("=" * 60)
    print("Generating Entity Registry Folder Tree")
    print("=" * 60)
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get all skills with their domains
        cur.execute('''
            SELECT 
                e.canonical_name as skill,
                d.canonical_name as domain,
                er.notes
            FROM owl_relationships er
            JOIN owl e ON er.owl_id = e.owl_id
            JOIN owl d ON er.related_owl_id = d.owl_id
            WHERE er.relationship = 'is_a'
            AND e.owl_type = 'skill'
            AND d.owl_type = 'skill_domain'
            ORDER BY d.canonical_name, e.canonical_name
        ''')
        
        # Group by domain
        domains = {}
        for r in cur.fetchall():
            domain = r['domain']
            skill = r['skill']
            confidence = 'high'
            if r['notes'] and 'confidence:' in r['notes']:
                confidence = r['notes'].split('confidence:')[1].strip()
            
            if domain not in domains:
                domains[domain] = []
            domains[domain].append((skill, confidence))
    
    # Create folders and files
    total_files = 0
    domain_counts = {}
    
    for domain, skills in domains.items():
        domain_path = REGISTRY_PATH / domain
        domain_path.mkdir(parents=True, exist_ok=True)
        
        # Create skill files
        skill_names = []
        for skill, confidence in skills:
            skill_names.append(skill)
            slug = slugify(skill)
            skill_file = domain_path / f"{slug}.md"
            
            # Only create if doesn't exist (don't overwrite)
            if not skill_file.exists():
                skill_file.write_text(generate_skill_md(skill, domain, confidence))
                total_files += 1
        
        # Create/update _index.md
        index_file = domain_path / "_index.md"
        index_file.write_text(generate_index_md(domain, skill_names))
        
        domain_counts[domain] = len(skills)
        print(f"  📁 {domain}/ - {len(skills)} skills")
    
    # Create main INDEX.md
    main_index = REGISTRY_PATH / "INDEX.md"
    main_index.write_text(generate_main_index(domain_counts))
    
    print()
    print(f"Created {total_files} new skill files")
    print(f"Updated {len(domains)} domain indexes")
    print(f"Total skills in registry: {sum(domain_counts.values())}")
    print()
    print(f"Registry location: {REGISTRY_PATH}")


if __name__ == '__main__':
    main()
