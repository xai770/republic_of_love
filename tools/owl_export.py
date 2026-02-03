#!/usr/bin/env python3
"""
OWL Export - Generate browsable file tree of OWL taxonomy.

Output: owl_export/
    ├── INDEX.md
    ├── technical/
    │   ├── _index.md
    │   ├── python_programming.md
    │   └── ...
    └── _needs_review/
        └── ...

Author: Arden
Date: January 20, 2026
"""

import os
import re
import shutil
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_connection


EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'owl_export')

# The 11 skill dimensions (owl_id 10-20)
SKILL_DIMENSIONS = {
    10: 'perception_and_observation',
    11: 'language_and_communication', 
    12: 'cognitive_and_analytical',
    13: 'creative_and_generative',
    14: 'execution_and_compliance',
    15: 'technical',
    16: 'physical_and_manual',
    17: 'domain_expertise',
    18: 'interpersonal',
    19: 'self_management',
    20: '_needs_review',
}


def sanitize_filename(name: str) -> str:
    """Convert entity name to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.lower().strip('_')
    return safe[:100]


def export_owl():
    """Export OWL taxonomy as file tree."""
    
    # Clean and create export dir
    if os.path.exists(EXPORT_DIR):
        shutil.rmtree(EXPORT_DIR)
    os.makedirs(EXPORT_DIR)
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        stats = {'dimensions': 0, 'skills': 0, 'requires': 0}
        dimension_data = []
        
        # Process each skill dimension
        for dim_id, dim_name in SKILL_DIMENSIONS.items():
            dim_dir = os.path.join(EXPORT_DIR, dim_name)
            os.makedirs(dim_dir, exist_ok=True)
            stats['dimensions'] += 1
            
            # Get skills in this dimension
            cur.execute("""
                SELECT o.owl_id, o.canonical_name, o.owl_type
                FROM owl o
                JOIN owl_relationships r ON o.owl_id = r.owl_id
                WHERE r.relationship = 'belongs_to'
                  AND r.related_owl_id = %s
                ORDER BY o.canonical_name
            """, (dim_id,))
            skills = cur.fetchall()
            
            dimension_data.append((dim_name, len(skills)))
            
            # Create dimension _index.md
            dim_md = f"# {dim_name.replace('_', ' ').title()}\n\n"
            dim_md += f"**Skills:** {len(skills)}\n\n"
            dim_md += "| Skill | Type | Requires |\n"
            dim_md += "|-------|------|----------|\n"
            
            for skill_row in skills:
                skill_id = skill_row['owl_id']
                skill_name = skill_row['canonical_name']
                skill_type = skill_row['owl_type']
                stats['skills'] += 1
                safe_name = sanitize_filename(skill_name)
                
                # Get requires relationships
                cur.execute("""
                    SELECT p.canonical_name, r.forward_strength
                    FROM owl_relationships r
                    JOIN owl p ON r.related_owl_id = p.owl_id
                    WHERE r.owl_id = %s AND r.relationship = 'requires'
                    ORDER BY r.forward_strength DESC
                """, (skill_id,))
                requires = cur.fetchall()
                
                requires_str = ', '.join([f"{r['canonical_name']}" for r in requires[:3]]) if requires else '-'
                if len(requires) > 3:
                    requires_str += f" (+{len(requires)-3})"
                
                dim_md += f"| [{skill_name}]({safe_name}.md) | {skill_type} | {requires_str} |\n"
                
                # Create skill file
                skill_md = f"# {skill_name}\n\n"
                skill_md += f"**Dimension:** [{dim_name}](_index.md)\n"
                skill_md += f"**Type:** {skill_type}\n"
                skill_md += f"**owl_id:** {skill_id}\n\n"
                
                if requires:
                    stats['requires'] += len(requires)
                    skill_md += "## Requires\n\n"
                    skill_md += "| Skill | Forward | Reverse |\n"
                    skill_md += "|-------|---------|--------|\n"
                    for req_row in requires:
                        req_name = req_row['canonical_name']
                        fwd = req_row['forward_strength']
                        # Get reverse strength
                        cur.execute("""
                            SELECT reverse_strength FROM owl_relationships 
                            WHERE owl_id = %s AND relationship = 'requires' 
                            AND related_owl_id = (SELECT owl_id FROM owl WHERE canonical_name = %s)
                        """, (skill_id, req_name))
                        rev_row = cur.fetchone()
                        rev = rev_row['reverse_strength'] if rev_row else None
                        fwd_str = f"{fwd:.2f}" if fwd else "-"
                        rev_str = f"{rev:.2f}" if rev else "-"
                        skill_md += f"| {req_name} | {fwd_str} | {rev_str} |\n"
                
                skill_path = os.path.join(dim_dir, f"{safe_name}.md")
                with open(skill_path, 'w') as f:
                    f.write(skill_md)
            
            dim_index_path = os.path.join(dim_dir, "_index.md")
            with open(dim_index_path, 'w') as f:
                f.write(dim_md)
        
        # Get total counts
        cur.execute("SELECT COUNT(*) as cnt FROM owl WHERE owl_id > 20")
        total_skills = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM owl_relationships WHERE relationship = 'requires'")
        total_requires = cur.fetchone()['cnt']
        
        cur.execute("SELECT status, COUNT(*) FROM owl_pending GROUP BY status ORDER BY status")
        pending_stats = cur.fetchall()
        
        # Generate INDEX.md
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        index_md = f"""# OWL Taxonomy Export

**Generated:** {now}

## Summary

| Metric | Count |
|--------|-------|
| **Skill Dimensions** | {len(SKILL_DIMENSIONS)} |
| **Skills (classified)** | {total_skills} |
| **Requires relationships** | {total_requires} |

## Pipeline Status

| Status | Count |
|--------|-------|
"""
        for row in pending_stats:
            index_md += f"| {row['status']} | {row['count']} |\n"
        
        index_md += "\n## Browse by Dimension\n\n"
        index_md += "| Dimension | Skills | Browse |\n"
        index_md += "|-----------|--------|--------|\n"
        
        for dim_name, skill_count in sorted(dimension_data, key=lambda x: -x[1]):
            index_md += f"| {dim_name.replace('_', ' ').title()} | {skill_count} | [→ {dim_name}/]({dim_name}/_index.md) |\n"
        
        index_md += "\n---\n*Generated by tools/owl_export.py*\n"
        
        with open(os.path.join(EXPORT_DIR, 'INDEX.md'), 'w') as f:
            f.write(index_md)
    
    return stats


if __name__ == "__main__":
    print(f"Exporting OWL to {EXPORT_DIR}...")
    stats = export_owl()
    print(f"Done! {stats['dimensions']} dimensions, {stats['skills']} skills, {stats['requires']} requires relationships")
    print(f"Open {EXPORT_DIR}/INDEX.md to browse")
