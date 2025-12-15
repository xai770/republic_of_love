#!/usr/bin/env python3
"""
Entity Registry Exporter - WF3005 Final Step

Generates a file tree representation of the entity registry hierarchy.
Each domain becomes a folder, each skill becomes a file.

Output structure:
    entity_registry/
    ├── INDEX.md           # Summary stats
    ├── technology/
    │   ├── _index.md      # Domain summary
    │   ├── python.md      # Skill details
    │   └── sql.md
    ├── data_and_analytics/
    │   └── ...
    └── ...

Author: Arden
Date: December 9, 2025
"""

import json
import os
import re
import shutil
from datetime import datetime


def sanitize_filename(name: str) -> str:
    """Convert entity name to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe = re.sub(r'\s+', '_', safe)
    safe = safe.lower().strip('_')
    return safe[:100]


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Export entity registry as a file tree.
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        export_dir = os.path.join(os.getcwd(), 'entity_registry')
        
        # Clean existing folders (keep INDEX.md until regenerated)
        if os.path.exists(export_dir):
            for item in os.listdir(export_dir):
                item_path = os.path.join(export_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        
        os.makedirs(export_dir, exist_ok=True)
        
        # Get all domains
        cursor.execute("""
            SELECT e.entity_id, e.canonical_name, e.description
            FROM entities e
            WHERE e.entity_type = 'skill_domain'
              AND e.status = 'active'
            ORDER BY e.canonical_name
        """)
        domains = cursor.fetchall()
        
        # Get orphan count
        cursor.execute("""
            SELECT COUNT(*) 
            FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er 
                  WHERE er.entity_id = e.entity_id 
                  AND er.relationship = 'is_a'
              )
        """)
        orphan_count = cursor.fetchone()[0]
        
        tree_stats = {"domains": 0, "skills": 0, "files_created": 0}
        domain_summaries = []
        
        for domain_id, domain_name, domain_desc in domains:
            domain_dir = os.path.join(export_dir, sanitize_filename(domain_name))
            os.makedirs(domain_dir, exist_ok=True)
            tree_stats["domains"] += 1
            
            # Get skills in this domain
            cursor.execute("""
                SELECT e.entity_id, e.canonical_name, e.description,
                       rd.confidence, rd.reasoning, rd.review_status
                FROM entities e
                JOIN entity_relationships er ON er.entity_id = e.entity_id
                LEFT JOIN registry_decisions rd ON rd.subject_entity_id = e.entity_id
                    AND rd.target_entity_id = %s
                WHERE er.related_entity_id = %s
                  AND er.relationship = 'is_a'
                  AND e.status = 'active'
                ORDER BY e.canonical_name
            """, (domain_id, domain_id))
            skills = cursor.fetchall()
            
            domain_summaries.append((domain_name, len(skills)))
            
            # Create domain _index.md
            domain_md = f"# {domain_name}\n\n"
            if domain_desc:
                domain_md += f"{domain_desc}\n\n"
            domain_md += f"**Skills:** {len(skills)}\n\n"
            domain_md += "| Skill | Confidence | Status |\n"
            domain_md += "|-------|------------|--------|\n"
            
            for skill_id, skill_name, skill_desc, conf, reasoning, status in skills:
                tree_stats["skills"] += 1
                safe_name = sanitize_filename(skill_name)
                
                conf_str = f"{conf:.0%}" if conf else "-"
                status_str = status or "-"
                domain_md += f"| [{skill_name}]({safe_name}.md) | {conf_str} | {status_str} |\n"
                
                # Create skill file
                skill_md = f"# {skill_name}\n\n"
                skill_md += f"**Domain:** [{domain_name}](_index.md)\n"
                if conf:
                    skill_md += f"**Confidence:** {conf:.0%}\n"
                if status:
                    skill_md += f"**Status:** {status}\n"
                skill_md += "\n"
                
                if skill_desc:
                    skill_md += f"## Description\n\n{skill_desc}\n\n"
                
                if reasoning:
                    skill_md += f"## Classification Reasoning\n\n{reasoning}\n"
                
                skill_path = os.path.join(domain_dir, f"{safe_name}.md")
                with open(skill_path, 'w') as f:
                    f.write(skill_md)
                tree_stats["files_created"] += 1
            
            domain_index_path = os.path.join(domain_dir, "_index.md")
            with open(domain_index_path, 'w') as f:
                f.write(domain_md)
            tree_stats["files_created"] += 1
        
        # Generate main INDEX.md
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        index_md = f"""# Entity Registry

**Generated:** {now}

## Tree Structure

```
entity_registry/
"""
        for domain_name, skill_count in domain_summaries:
            index_md += f"├── {sanitize_filename(domain_name)}/ ({skill_count} skills)\n"
        
        index_md += f"""```

## Summary

| Metric | Count |
|--------|-------|
| **Domains** | {tree_stats['domains']} |
| **Skills** | {tree_stats['skills']} |
| **Orphans** | {orphan_count} |

## Browse by Domain

| Domain | Skills | Browse |
|--------|--------|--------|
"""
        for domain_name, skill_count in domain_summaries:
            safe = sanitize_filename(domain_name)
            index_md += f"| {domain_name} | {skill_count} | [→ {safe}/]({safe}/_index.md) |\n"
        
        # Decision stats
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE review_status = 'auto_approved') as auto,
                COUNT(*) FILTER (WHERE review_status = 'approved') as manual,
                COUNT(*) FILTER (WHERE review_status = 'pending') as pending
            FROM registry_decisions
        """)
        auto, manual, pending = cursor.fetchone()
        
        index_md += f"""
## Classification Stats

| Status | Count |
|--------|-------|
| Auto-approved | {auto} |
| Manually approved | {manual} |
| Pending review | {pending} |

---

*Auto-generated by WF3005 after each update.*
"""
        
        with open(os.path.join(export_dir, 'INDEX.md'), 'w') as f:
            f.write(index_md)
        
        return {"status": "success", "exported_to": export_dir, "stats": tree_stats}
        
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}


if __name__ == "__main__":
    import sys
    import psycopg2
    from dotenv import load_dotenv
    
    load_dotenv()
    
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except:
            pass
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )
    
    result = execute(input_data, conn)
    conn.close()
    
    print(json.dumps(result))
