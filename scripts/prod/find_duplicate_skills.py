#!/usr/bin/env python3
"""
Find duplicate skills with full hierarchy paths.
Pass paths to LLM for intelligent deduplication decisions.

Example paths:
  Technology/Database_Management/Oracle
  Technology/Software_Development/Oracle_Database
  
LLM picks the canonical one.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import requests
from collections import defaultdict
from core.database import get_connection

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"

def ask_llm(prompt: str) -> str:
    """Query local LLM."""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=120)
        return resp.json().get("response", "")
    except Exception as e:
        print(f"LLM error: {e}")
        return ""

def get_skill_paths():
    """Get all skills with their full hierarchy path."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Build skill -> parent mapping
    cur.execute("""
        SELECT sh.skill_id, sh.parent_skill_id, sa.display_name
        FROM skill_hierarchy sh
        JOIN skill_aliases sa ON sh.skill_id = sa.skill_id
    """)
    
    parent_map = {}
    name_map = {}
    for row in cur.fetchall():
        skill_id = row['skill_id']
        parent_id = row['parent_skill_id']
        name = row['display_name']
        parent_map[skill_id] = parent_id
        name_map[skill_id] = name
    
    # Also get skills without hierarchy entries
    cur.execute("""
        SELECT skill_id, display_name 
        FROM skill_aliases 
        WHERE display_name IS NOT NULL
    """)
    for row in cur.fetchall():
        skill_id = row['skill_id']
        name = row['display_name']
        if skill_id not in name_map:
            name_map[skill_id] = name
    
    cur.close()
    
    def get_path(skill_id, visited=None):
        """Recursively build path from root to skill."""
        if visited is None:
            visited = set()
        if skill_id in visited:
            return [name_map.get(skill_id) or str(skill_id)]
        visited.add(skill_id)
        
        name = name_map.get(skill_id) or str(skill_id)
        parent_id = parent_map.get(skill_id)
        
        if parent_id and parent_id in name_map:
            parent_path = get_path(parent_id, visited)
            return parent_path + [name]
        else:
            return [name]
    
    # Build paths for all skills
    skill_paths = {}
    for skill_id, name in name_map.items():
        if not name:
            continue
        path = get_path(skill_id)
        # Filter out None values
        path = [p for p in path if p]
        skill_paths[skill_id] = {
            'name': name,
            'path': '/'.join(path),
            'depth': len(path)
        }
    
    return skill_paths

def find_duplicates_by_name(skill_paths):
    """Group skills by display_name."""
    by_name = defaultdict(list)
    for skill_id, info in skill_paths.items():
        by_name[info['name']].append({
            'id': skill_id,
            'path': info['path'],
            'depth': info['depth']
        })
    
    # Only keep duplicates
    duplicates = {name: skills for name, skills in by_name.items() if len(skills) > 1}
    return duplicates

def ask_llm_to_pick_canonical(duplicates, batch_size=10):
    """Ask LLM which path is the best home for each duplicate skill."""
    
    results = []
    items = list(duplicates.items())
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        # Build prompt
        lines = []
        for idx, (name, skills) in enumerate(batch, 1):
            paths = [s['path'] for s in skills]
            ids = [s['id'] for s in skills]
            lines.append(f"{idx}. {name}")
            for j, (path, sid) in enumerate(zip(paths, ids)):
                lines.append(f"   [{chr(65+j)}] (id={sid}) {path}")
        
        prompt = f"""You are organizing a skills taxonomy. For each skill that appears in multiple places, pick the BEST location.

Consider:
- Which category is most specific/appropriate?
- Which path makes the most sense semantically?
- Skills should be in ONE place only

For each skill, respond with JUST the letter of the best choice.

SKILLS WITH MULTIPLE LOCATIONS:
{chr(10).join(lines)}

RESPOND IN THIS EXACT FORMAT (one per line):
1: A
2: B
etc.

Your choices:"""

        response = ask_llm(prompt)
        
        # Parse response
        for line in response.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                try:
                    num_str, choice = line.split(':', 1)
                    num = int(num_str.strip().rstrip('.'))
                    choice = choice.strip().upper()
                    
                    if 1 <= num <= len(batch) and len(choice) == 1:
                        idx = num - 1
                        name, skills = batch[idx]
                        choice_idx = ord(choice) - ord('A')
                        
                        if 0 <= choice_idx < len(skills):
                            canonical = skills[choice_idx]
                            others = [s for j, s in enumerate(skills) if j != choice_idx]
                            results.append({
                                'name': name,
                                'keep': canonical,
                                'remove': others
                            })
                except (ValueError, IndexError):
                    continue
        
        print(f"  Processed {min(i+batch_size, len(items))}/{len(items)} duplicate groups...")
    
    return results

def main():
    print("=" * 70)
    print("SKILL DUPLICATE FINDER - Full Path Analysis")
    print("=" * 70)
    
    print("\n📂 Building skill paths...")
    skill_paths = get_skill_paths()
    print(f"   Found {len(skill_paths)} total skills")
    
    print("\n🔍 Finding duplicates...")
    duplicates = find_duplicates_by_name(skill_paths)
    print(f"   Found {len(duplicates)} duplicate groups")
    
    # Show examples
    print("\n📋 Sample duplicates with full paths:")
    print("-" * 70)
    
    count = 0
    for name, skills in sorted(duplicates.items(), key=lambda x: -len(x[1])):
        if count >= 15:
            break
        print(f"\n  {name} ({len(skills)} instances):")
        for s in skills:
            print(f"    • [{s['id']}] {s['path']}")
        count += 1
    
    total_removable = sum(len(skills) - 1 for skills in duplicates.values())
    print(f"\n   → {total_removable} duplicate skills can be consolidated")
    
    # Run LLM deduplication automatically
    print("\n" + "=" * 70)
    print("\n🤖 Asking LLM to pick best locations...")
    decisions = ask_llm_to_pick_canonical(duplicates)
    
    print(f"\n✅ LLM made {len(decisions)} decisions:")
    print("-" * 70)
    
    for d in decisions[:20]:
        print(f"\n  {d['name']}:")
        print(f"    KEEP: {d['keep']['path']}")
        for r in d['remove']:
            print(f"    DEL:  {r['path']} (id={r['id']})")
    
    if len(decisions) > 20:
        print(f"\n  ... and {len(decisions) - 20} more")
    
    # Save decisions
    output_file = '/tmp/skill_dedup_decisions.json'
    with open(output_file, 'w') as f:
        json.dump(decisions, f, indent=2)
    print(f"\n💾 Saved decisions to {output_file}")
    
    # Apply automatically
    if decisions:
        apply_deduplication(decisions)
    
    print("\n✅ Done")

def apply_deduplication(decisions):
    """Apply the deduplication decisions to the database."""
    conn = get_connection()
    cur = conn.cursor()
    
    removed = 0
    skipped = 0
    for d in decisions:
        keep_id = d['keep']['id']
        
        for r in d['remove']:
            remove_id = r['id']
            
            # Skip if trying to merge to self
            if keep_id == remove_id:
                skipped += 1
                continue
            
            try:
                # Move any children to the canonical skill (but not to self)
                cur.execute("""
                    UPDATE skill_hierarchy 
                    SET parent_skill_id = %s 
                    WHERE parent_skill_id = %s
                    AND skill_id != %s
                """, (keep_id, remove_id, keep_id))
                
                # Remove the duplicate from hierarchy
                cur.execute("""
                    DELETE FROM skill_hierarchy 
                    WHERE skill_id = %s
                """, (remove_id,))
                
                removed += 1
            except Exception as e:
                print(f"  Warning: Could not remove {remove_id}: {e}")
                conn.rollback()
                continue
    
    conn.commit()
    cur.close()
    print(f"\n🗑️  Removed {removed} duplicate skill entries from hierarchy (skipped {skipped} self-refs)")

if __name__ == "__main__":
    main()
