#!/usr/bin/env python3
"""
Export Registry Decisions as Folder Tree
=========================================

Exports registry_decisions to skills_taxonomy/ for human review.
Uses the new UEO schema (entities, entity_relationships, registry_decisions).

Structure:
    skills_taxonomy/
    ├── _PENDING/           # Skills needing review (grouped by proposed parent)
    │   ├── Technology/
    │   │   ├── skill_name.md
    │   │   └── ...
    │   └── ...
    ├── _AUTO_APPROVED/     # High-confidence auto-approved (for spot-checking)
    │   └── ...
    └── INDEX.md            # Summary and statistics

Each .md file contains:
- Skill name and entity_id
- Proposed parent domain
- Classifier confidence
- Classifier reasoning
- Grader agreement/correction
- Action buttons (conceptual - for human to update DB)

Created: December 7, 2025
Author: Sandy
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Output directory
OUTPUT_DIR = Path('/home/xai/Documents/ty_wave/skills_taxonomy')

load_dotenv()


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )


def sanitize_name(name: str) -> str:
    """Convert name to valid folder/file name."""
    if not name:
        return "Unnamed"
    sanitized = str(name).replace('/', '_').replace('\\', '_').replace(':', '_')
    sanitized = sanitized.replace('?', '').replace('*', '').replace('|', '_')
    sanitized = sanitized.replace('<', '_').replace('>', '_').replace('"', '')
    sanitized = sanitized.replace('\n', ' ').replace('\r', '')
    return sanitized.strip()[:100] or "Unnamed"


def get_decisions(conn) -> list:
    """Get all registry decisions with entity details."""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("""
        SELECT 
            rd.decision_id,
            rd.decision_type,
            rd.subject_entity_id,
            rd.target_entity_id,
            rd.confidence,
            rd.reasoning,
            rd.review_status,
            rd.model,
            rd.created_at,
            e.canonical_name as skill_name,
            t.canonical_name as parent_name
        FROM registry_decisions rd
        JOIN entities e ON rd.subject_entity_id = e.entity_id
        LEFT JOIN entities t ON rd.target_entity_id = t.entity_id
        WHERE rd.decision_type = 'assign'
        ORDER BY rd.review_status, rd.confidence DESC, e.canonical_name
    """)
    
    decisions = cursor.fetchall()
    cursor.close()
    return decisions


def parse_reasoning(reasoning_json: str) -> dict:
    """Parse the reasoning JSON field."""
    if not reasoning_json:
        return {}
    try:
        return json.loads(reasoning_json)
    except json.JSONDecodeError:
        return {'raw': reasoning_json}


def create_skill_file(decision: dict, output_dir: Path):
    """Create markdown file for a skill decision."""
    skill_name = decision['skill_name'] or 'Unknown'
    parent_name = decision['parent_name'] or 'Unknown'
    confidence = decision['confidence'] or 0.5
    reasoning = parse_reasoning(decision['reasoning'])
    status = decision['review_status']
    
    # Status emoji
    status_emoji = {
        'auto_approved': '✅',
        'pending': '⏳',
        'approved': '👍',
        'rejected': '❌'
    }.get(status, '❓')
    
    # Grader info
    grader_agrees = reasoning.get('grader_agrees', True)
    grader_icon = '✓' if grader_agrees else '✗'
    final_parent = reasoning.get('final_parent', parent_name)
    
    content = f"""# {skill_name}

## Decision Summary

| Field | Value |
|-------|-------|
| **Entity ID** | {decision['subject_entity_id']} |
| **Proposed Parent** | {parent_name} |
| **Final Parent** | {final_parent} |
| **Confidence** | {confidence:.2f} |
| **Status** | {status} {status_emoji} |
| **Grader Agrees** | {grader_icon} {grader_agrees} |
| **Model** | {decision['model']} |
| **Created** | {decision['created_at']} |

## Classifier Reasoning

{reasoning.get('classifier', 'No classifier reasoning available.')}

## Grader Review

{reasoning.get('grader', 'No grader review available.')}

---

## Actions

To approve this decision, run:
```sql
UPDATE registry_decisions 
SET review_status = 'approved', reviewed_at = now() 
WHERE decision_id = {decision['decision_id']};
```

To reject and re-classify:
```sql
UPDATE registry_decisions 
SET review_status = 'rejected', review_notes = 'Reason here', reviewed_at = now() 
WHERE decision_id = {decision['decision_id']};
```

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # Create file
    filename = f"{sanitize_name(skill_name)}.md"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def create_category_readme(category_name: str, decisions: list, output_dir: Path):
    """Create README for a category folder."""
    total = len(decisions)
    avg_conf = sum(d['confidence'] or 0.5 for d in decisions) / total if total else 0
    
    # List skills
    skill_list = "\n".join(f"- [{d['skill_name']}]({sanitize_name(d['skill_name'])}.md) ({d['confidence']:.2f})" 
                           for d in sorted(decisions, key=lambda x: x['skill_name']))
    
    content = f"""# {category_name}

**Skills in this category:** {total}  
**Average Confidence:** {avg_conf:.2f}

## Skills

{skill_list}

---

## Bulk Approve All

To approve all skills in this category:
```sql
UPDATE registry_decisions 
SET review_status = 'approved', reviewed_at = now() 
WHERE decision_id IN ({', '.join(str(d['decision_id']) for d in decisions)});
```

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    readme_path = output_dir / '_README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)


def create_index(output_dir: Path, stats: dict):
    """Create INDEX.md with summary and navigation."""
    content = f"""# Skills Taxonomy - Registry Decisions Review

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

| Status | Count |
|--------|-------|
| **Auto-Approved** ✅ | {stats['auto_approved']} |
| **Pending Review** ⏳ | {stats['pending']} |
| **Human Approved** 👍 | {stats['approved']} |
| **Rejected** ❌ | {stats['rejected']} |
| **Total** | {stats['total']} |

## Confidence Distribution

| Range | Count |
|-------|-------|
| 0.90 - 1.00 | {stats['conf_90_100']} |
| 0.80 - 0.89 | {stats['conf_80_89']} |
| 0.70 - 0.79 | {stats['conf_70_79']} |
| < 0.70 | {stats['conf_below_70']} |

## Directories

- **`_PENDING/`** - Skills needing human review (organized by proposed parent)
- **`_AUTO_APPROVED/`** - High-confidence auto-approved skills (for spot-checking)

## Review Workflow

1. Browse `_PENDING/` directories
2. Open skill files to see reasoning
3. Run SQL commands to approve/reject
4. Re-run this export to update

## Quick Commands

```bash
# Count pending by category
find _PENDING -type f -name '*.md' | grep -v README | wc -l

# List all Technology skills
ls _PENDING/Technology/

# Search for a skill
find . -name '*python*.md'
```

---

## Apply Approved Decisions

After reviewing, apply approved decisions to entity_relationships:

```sql
-- Apply all approved decisions (creates child_of relationships)
INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, created_by)
SELECT rd.subject_entity_id, rd.target_entity_id, 'child_of', 'wf3005'
FROM registry_decisions rd
WHERE rd.review_status IN ('approved', 'auto_approved')
  AND rd.decision_type = 'assign'
  AND NOT EXISTS (
      SELECT 1 FROM entity_relationships er
      WHERE er.entity_id = rd.subject_entity_id
        AND er.relationship = 'child_of'
  );
```

---
*Generated from registry_decisions table*
"""
    
    index_path = output_dir / 'INDEX.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    print("=" * 70)
    print("REGISTRY DECISIONS EXPORT")
    print("=" * 70)
    print()
    
    # Clean and recreate output directory
    print(f"📁 Output directory: {OUTPUT_DIR}")
    if OUTPUT_DIR.is_symlink():
        # Resolve symlink target
        target = OUTPUT_DIR.resolve()
        print(f"   ℹ️  Symlink → {target}")
        if target.exists():
            print("   ⚠️  Target exists - will be overwritten")
            import shutil
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    elif OUTPUT_DIR.exists():
        print("   ⚠️  Directory exists - will be overwritten")
        import shutil
        shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    print("🔌 Connecting to turing database...")
    conn = get_connection()
    
    # Get all decisions
    print("📊 Fetching registry decisions...")
    decisions = get_decisions(conn)
    print(f"   Found {len(decisions)} decisions")
    
    if not decisions:
        print("   No decisions to export!")
        conn.close()
        return
    
    # Group by status
    pending = [d for d in decisions if d['review_status'] == 'pending']
    auto_approved = [d for d in decisions if d['review_status'] == 'auto_approved']
    approved = [d for d in decisions if d['review_status'] == 'approved']
    rejected = [d for d in decisions if d['review_status'] == 'rejected']
    
    print(f"   - Pending: {len(pending)}")
    print(f"   - Auto-approved: {len(auto_approved)}")
    print(f"   - Approved: {len(approved)}")
    print(f"   - Rejected: {len(rejected)}")
    print()
    
    # Create _PENDING directory structure (by parent)
    print("🌳 Creating _PENDING directory...")
    pending_dir = OUTPUT_DIR / '_PENDING'
    pending_dir.mkdir(exist_ok=True)
    
    # Group pending by parent
    pending_by_parent = {}
    for d in pending:
        parent = d['parent_name'] or 'Unknown'
        if parent not in pending_by_parent:
            pending_by_parent[parent] = []
        pending_by_parent[parent].append(d)
    
    for parent, parent_decisions in pending_by_parent.items():
        parent_dir = pending_dir / sanitize_name(parent)
        parent_dir.mkdir(exist_ok=True)
        
        for d in parent_decisions:
            create_skill_file(d, parent_dir)
        
        create_category_readme(parent, parent_decisions, parent_dir)
        print(f"   ✅ {parent}: {len(parent_decisions)} skills")
    
    # Create _AUTO_APPROVED directory structure
    print("\n🌳 Creating _AUTO_APPROVED directory...")
    auto_dir = OUTPUT_DIR / '_AUTO_APPROVED'
    auto_dir.mkdir(exist_ok=True)
    
    # Group auto-approved by parent
    auto_by_parent = {}
    for d in auto_approved:
        parent = d['parent_name'] or 'Unknown'
        if parent not in auto_by_parent:
            auto_by_parent[parent] = []
        auto_by_parent[parent].append(d)
    
    for parent, parent_decisions in auto_by_parent.items():
        parent_dir = auto_dir / sanitize_name(parent)
        parent_dir.mkdir(exist_ok=True)
        
        for d in parent_decisions:
            create_skill_file(d, parent_dir)
        
        create_category_readme(parent, parent_decisions, parent_dir)
        print(f"   ✅ {parent}: {len(parent_decisions)} skills")
    
    # Calculate stats
    stats = {
        'total': len(decisions),
        'pending': len(pending),
        'auto_approved': len(auto_approved),
        'approved': len(approved),
        'rejected': len(rejected),
        'conf_90_100': len([d for d in decisions if (d['confidence'] or 0) >= 0.90]),
        'conf_80_89': len([d for d in decisions if 0.80 <= (d['confidence'] or 0) < 0.90]),
        'conf_70_79': len([d for d in decisions if 0.70 <= (d['confidence'] or 0) < 0.80]),
        'conf_below_70': len([d for d in decisions if (d['confidence'] or 0) < 0.70]),
    }
    
    # Create index
    create_index(OUTPUT_DIR, stats)
    
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ EXPORT COMPLETE!")
    print(f"   📁 Location: {OUTPUT_DIR}")
    print(f"   📊 {len(pending)} pending review")
    print(f"   📊 {len(auto_approved)} auto-approved")
    print(f"   📊 {len(pending_by_parent)} pending categories")
    print(f"   📊 {len(auto_by_parent)} auto-approved categories")
    print("=" * 70)


if __name__ == "__main__":
    main()
