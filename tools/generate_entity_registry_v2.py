#!/usr/bin/env python3
"""
Generate entity_registry folder tree from database hierarchy (v2 - with families).

Creates:
  entity_registry/
  ├── INDEX.md
  ├── technology/
  │   ├── _index.md
  │   ├── cloud_platforms/
  │   │   ├── _index.md
  │   │   ├── aws_cloud_services.md
  │   │   └── azure_cloud_platform.md  ← Siblings
  │   ├── application_development/
  │   │   ├── _index.md
  │   │   ├── python_programming.md
  │   │   └── java_development.md      ← Siblings
  │   └── ...
  └── ...
"""

import sys
import os
import re
import shutil
from pathlib import Path

sys.path.insert(0, '.')
from core.database import get_connection

REGISTRY_PATH = Path('/home/xai/Documents/ty_learn/entity_registry')


def slugify(name):
    """Convert name to filename-safe slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    if len(slug) > 80:
        slug = slug[:80].rsplit('_', 1)[0]
    return slug


def generate_skill_md(skill_name, family_name, domain_name):
    """Generate markdown content for a skill."""
    return f"""# {skill_name}

**Domain:** {domain_name.replace('_', ' ').title()}
**Family:** {family_name.replace('_', ' ').title()}

## Description

{skill_name}

## Siblings

_Skills in the same family are considered closely related (siblings)._

## Related Skills

_To be populated_
"""


def generate_family_index(family_name, domain_name, skills):
    """Generate _index.md for a family."""
    skill_list = '\n'.join([f'- [{s}]({slugify(s)}.md)' for s in sorted(skills)])
    return f"""# {family_name.replace('_', ' ').title()}

**Domain:** {domain_name.replace('_', ' ').title()}
**Total Skills:** {len(skills)}

Skills in this family are considered **siblings** - closely related for matching purposes.

## Skills

{skill_list}
"""


def generate_domain_index(domain_name, families):
    """Generate _index.md for a domain."""
    family_list = '\n'.join([
        f'- [{f.replace("_", " ").title()}]({f}/) ({c} skills)'
        for f, c in sorted(families.items(), key=lambda x: -x[1])
    ])
    total = sum(families.values())
    return f"""# {domain_name.replace('_', ' ').title()}

**Total Families:** {len(families)}
**Total Skills:** {total}

## Families

{family_list}
"""


def generate_main_index(domains):
    """Generate main INDEX.md."""
    domain_list = '\n'.join([
        f'- [{d.replace("_", " ").title()}]({d}/) ({info["families"]} families, {info["skills"]} skills)'
        for d, info in sorted(domains.items(), key=lambda x: -x[1]['skills'])
    ])
    total_skills = sum(d['skills'] for d in domains.values())
    total_families = sum(d['families'] for d in domains.values())
    return f"""# Entity Registry - Skill Taxonomy

This folder contains the canonical skill hierarchy for job-profile matching.

**Structure:** Domain → Family → Skill

Skills within the same **family** are considered **siblings** (closely related).
For example, AWS and Azure are siblings under `cloud_platforms`.

## Statistics

- **Domains:** {len(domains)}
- **Families:** {total_families}
- **Skills:** {total_skills}

## Domains

{domain_list}

## Generated

This structure was generated from the database by `tools/generate_entity_registry_v2.py`.
Run WF3007 (domain classification) and WF3007b (family classification) first.
"""


def main():
    print("=" * 60)
    print("Generating Entity Registry Folder Tree (v2 - with families)")
    print("=" * 60)
    
    # Clear existing registry
    if REGISTRY_PATH.exists():
        print(f"Clearing existing registry at {REGISTRY_PATH}")
        shutil.rmtree(REGISTRY_PATH)
    REGISTRY_PATH.mkdir(parents=True)
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get skills with domain and family
        # A skill has:
        #   - is_a relationship to domain (from wf3007)
        #   - is_a relationship to family (from wf3007b)
        cur.execute('''
            SELECT 
                s.canonical_name as skill,
                d.canonical_name as domain,
                f.canonical_name as family
            FROM owl s
            -- Skill -> Domain relationship
            JOIN owl_relationships dr ON s.owl_id = dr.owl_id 
                AND dr.relationship = 'is_a'
                AND dr.created_by = 'wf3007_skill_cartographer'
            JOIN owl d ON dr.related_owl_id = d.owl_id 
                AND d.owl_type = 'skill_domain'
            -- Skill -> Family relationship
            LEFT JOIN owl_relationships fr ON s.owl_id = fr.owl_id 
                AND fr.relationship = 'is_a'
                AND fr.created_by = 'wf3007b_skill_cartographer'
            LEFT JOIN owl f ON fr.related_owl_id = f.owl_id 
                AND f.owl_type = 'skill_family'
            WHERE s.owl_type = 'skill'
            ORDER BY d.canonical_name, f.canonical_name, s.canonical_name
        ''')
        
        # Build hierarchy: domain -> family -> skills
        hierarchy = {}
        for r in cur.fetchall():
            domain = r['domain']
            family = r['family'] or 'uncategorized'
            skill = r['skill']
            
            if domain not in hierarchy:
                hierarchy[domain] = {}
            if family not in hierarchy[domain]:
                hierarchy[domain][family] = []
            hierarchy[domain][family].append(skill)
    
    # Create folders and files
    total_files = 0
    domain_stats = {}
    
    for domain, families in hierarchy.items():
        domain_path = REGISTRY_PATH / domain
        domain_path.mkdir(parents=True, exist_ok=True)
        
        family_counts = {}
        
        for family, skills in families.items():
            family_path = domain_path / family
            family_path.mkdir(parents=True, exist_ok=True)
            
            # Create skill files
            for skill in skills:
                slug = slugify(skill)
                skill_file = family_path / f"{slug}.md"
                skill_file.write_text(generate_skill_md(skill, family, domain))
                total_files += 1
            
            # Create family _index.md
            index_file = family_path / "_index.md"
            index_file.write_text(generate_family_index(family, domain, skills))
            
            family_counts[family] = len(skills)
        
        # Create domain _index.md
        domain_index = domain_path / "_index.md"
        domain_index.write_text(generate_domain_index(domain, family_counts))
        
        domain_stats[domain] = {
            'families': len(families),
            'skills': sum(family_counts.values())
        }
        
        print(f"  📁 {domain}/ - {len(families)} families, {sum(family_counts.values())} skills")
    
    # Create main INDEX.md
    main_index = REGISTRY_PATH / "INDEX.md"
    main_index.write_text(generate_main_index(domain_stats))
    
    print()
    print(f"Created {total_files} skill files")
    print(f"Across {sum(d['families'] for d in domain_stats.values())} families")
    print(f"In {len(domain_stats)} domains")
    print()
    print(f"Registry location: {REGISTRY_PATH}")


if __name__ == '__main__':
    main()
