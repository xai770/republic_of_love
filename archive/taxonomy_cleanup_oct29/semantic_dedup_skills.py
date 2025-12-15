#!/usr/bin/env python3
"""
Semantic Similarity Deduplication
==================================

Uses embeddings to find semantically similar skills, then asks LLM to judge
whether they're truly duplicates and which name to keep.

Process:
1. Get all skills with same parent (siblings only)
2. Generate embeddings for display names
3. Calculate pairwise cosine similarity
4. For pairs > threshold, ask Qwen: "Same skill? Which name better?"
5. Auto-merge based on verdict

Created: 2025-10-29
Author: Arden
Motto: "Failure is not an option. We just iterate."
"""

import psycopg2
import json
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# LLM and embedding settings
LLM_MODEL = "qwen2.5:7b"
EMBED_MODEL = "nomic-embed-text"
SIMILARITY_THRESHOLD = 0.85  # Pairs above this are suspicious
OUTPUT_DIR = Path('/home/xai/Documents/ty_learn/temp/semantic_dedup')

def get_embedding(text):
    """Get embedding vector for text using ollama API"""
    
    # Use curl to call ollama API
    result = subprocess.run(
        ['curl', '-s', 'http://localhost:11434/api/embeddings', 
         '-d', json.dumps({'model': EMBED_MODEL, 'prompt': text})],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        raise Exception(f"Embedding error: {result.stderr}")
    
    # Parse embedding from JSON response
    try:
        response = json.loads(result.stdout)
        embedding = response.get('embedding')
        if not embedding:
            raise Exception(f"No embedding in response: {result.stdout[:200]}")
        return np.array(embedding)
    except json.JSONDecodeError:
        raise Exception(f"Could not parse embedding response: {result.stdout[:200]}")

def cosine_similarity(v1, v2):
    """Calculate cosine similarity between two vectors"""
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def ask_llm(prompt):
    """Ask Qwen a question"""
    
    result = subprocess.run(
        ['ollama', 'run', LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode != 0:
        raise Exception(f"LLM error: {result.stderr}")
    
    return result.stdout.strip()

def parse_json_response(response):
    """Extract JSON from LLM response"""
    
    response = response.strip().replace('```json', '').replace('```', '').strip()
    
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
    
    return None

def get_siblings_by_parent(conn):
    """Get all skills grouped by their parent"""
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            h.parent_skill,
            sa_parent.display_name as parent_name,
            h.skill,
            sa_child.display_name as child_name
        FROM skill_hierarchy h
        JOIN skill_aliases sa_parent ON h.parent_skill = sa_parent.skill
        JOIN skill_aliases sa_child ON h.skill = sa_child.skill
        ORDER BY h.parent_skill, sa_child.display_name
    """)
    
    results = cur.fetchall()
    cur.close()
    
    # Group by parent
    siblings_by_parent = defaultdict(list)
    for parent_id, parent_name, child_id, child_name in results:
        siblings_by_parent[parent_id].append({
            'parent_name': parent_name,
            'child_id': child_id,
            'child_name': child_name
        })
    
    return siblings_by_parent

def find_similar_pairs(siblings):
    """Find semantically similar pairs among siblings"""
    
    if len(siblings) < 2:
        return []
    
    print(f"   Generating embeddings for {len(siblings)} skills...")
    
    # Get embeddings
    embeddings = {}
    for sibling in siblings:
        try:
            embeddings[sibling['child_id']] = get_embedding(sibling['child_name'])
        except Exception as e:
            print(f"   ⚠️  Embedding failed for {sibling['child_name']}: {e}")
    
    # Calculate pairwise similarities
    similar_pairs = []
    skill_ids = list(embeddings.keys())
    
    for i in range(len(skill_ids)):
        for j in range(i+1, len(skill_ids)):
            id1, id2 = skill_ids[i], skill_ids[j]
            similarity = cosine_similarity(embeddings[id1], embeddings[id2])
            
            if similarity >= SIMILARITY_THRESHOLD:
                # Find original sibling data
                name1 = next(s['child_name'] for s in siblings if s['child_id'] == id1)
                name2 = next(s['child_name'] for s in siblings if s['child_id'] == id2)
                
                similar_pairs.append({
                    'id1': id1,
                    'name1': name1,
                    'id2': id2,
                    'name2': name2,
                    'similarity': float(similarity)
                })
    
    return similar_pairs

def judge_pair(pair, parent_name):
    """Ask Qwen if two skills are duplicates and which to keep"""
    
    prompt = f"""You are a taxonomy specialist. Two skills under "{parent_name}" appear semantically similar (similarity: {pair['similarity']:.3f}).

SKILL A: {pair['name1']} (ID: {pair['id1']})
SKILL B: {pair['name2']} (ID: {pair['id2']})

Are these the SAME skill/concept (duplicates that should be merged)?

If YES:
- Which name is better? (more standard, clearer, more professional)
- Respond with JSON:
  {{
    "duplicate": true,
    "keep_id": "ID_TO_KEEP",
    "keep_name": "NAME_TO_KEEP",
    "merge_id": "ID_TO_MERGE",
    "reason": "brief explanation"
  }}

If NO (they're different skills):
- Respond with JSON:
  {{
    "duplicate": false,
    "reason": "brief explanation of the difference"
  }}

Respond with ONLY the JSON object."""

    response = ask_llm(prompt)
    verdict = parse_json_response(response)
    
    return verdict if verdict else {'duplicate': False, 'reason': 'Parse error'}

def apply_merge(conn, old_skill, canonical_skill):
    """Merge old_skill into canonical_skill"""
    
    cur = conn.cursor()
    
    try:
        # Remove duplicate relationships first
        cur.execute("""
            DELETE FROM skill_hierarchy
            WHERE skill = %s AND parent_skill IN (
                SELECT parent_skill FROM skill_hierarchy
                WHERE skill = %s
            )
        """, (canonical_skill, old_skill))
        
        # Update children
        cur.execute("""
            UPDATE skill_hierarchy
            SET parent_skill = %s
            WHERE parent_skill = %s
        """, (canonical_skill, old_skill))
        
        children = cur.rowcount
        
        # Update parents
        cur.execute("""
            UPDATE skill_hierarchy
            SET skill = %s
            WHERE skill = %s
        """, (canonical_skill, old_skill))
        
        parents = cur.rowcount
        
        # Mark as merged
        cur.execute("""
            UPDATE skill_aliases
            SET notes = COALESCE(notes || ' | ', '') || 
                        'MERGED INTO: ' || %s || ' (Semantic dedup ' || %s || ')'
            WHERE skill = %s
        """, (canonical_skill, datetime.now().strftime('%Y-%m-%d'), old_skill))
        
        conn.commit()
        cur.close()
        
        return children, parents
        
    except Exception as e:
        conn.rollback()
        cur.close()
        raise e

def main():
    """Main semantic deduplication"""
    
    print("=" * 80)
    print("🧠 SEMANTIC SIMILARITY DEDUPLICATION")
    print("=" * 80)
    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Judge model: {LLM_MODEL}")
    print(f"Similarity threshold: {SIMILARITY_THRESHOLD}")
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("📊 Grouping skills by parent...")
    siblings_by_parent = get_siblings_by_parent(conn)
    
    # Filter to parents with 3+ children
    candidates = {parent_id: siblings 
                  for parent_id, siblings in siblings_by_parent.items() 
                  if len(siblings) >= 3}
    
    print(f"   Found {len(candidates)} parent categories with 3+ children\n")
    
    all_judgments = []
    all_merges = []
    
    for i, (parent_id, siblings) in enumerate(candidates.items(), 1):
        parent_name = siblings[0]['parent_name']
        
        print(f"[{i}/{len(candidates)}] Analyzing: {parent_name} ({len(siblings)} children)")
        
        # Find similar pairs
        similar_pairs = find_similar_pairs(siblings)
        
        if not similar_pairs:
            print(f"   ✓ No similar pairs found\n")
            continue
        
        print(f"   🔍 Found {len(similar_pairs)} similar pairs")
        
        # Judge each pair
        for pair in similar_pairs:
            print(f"      Judging: {pair['name1']} vs {pair['name2']} ({pair['similarity']:.3f})")
            
            verdict = judge_pair(pair, parent_name)
            
            judgment = {
                'parent_id': parent_id,
                'parent_name': parent_name,
                'pair': pair,
                'verdict': verdict
            }
            all_judgments.append(judgment)
            
            if verdict.get('duplicate'):
                print(f"      ✓ DUPLICATE - Keep: {verdict['keep_name']}")
                all_merges.append(judgment)
            else:
                print(f"      ✓ DIFFERENT - {verdict.get('reason', 'No reason')}")
        
        print()
    
    # Save judgments
    judgment_file = OUTPUT_DIR / f"semantic_judgments_{timestamp}.json"
    with open(judgment_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'embedding_model': EMBED_MODEL,
            'judge_model': LLM_MODEL,
            'threshold': SIMILARITY_THRESHOLD,
            'judgments': all_judgments
        }, f, indent=2)
    
    print(f"{'='*80}")
    print(f"📋 DEDUPLICATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Parents analyzed: {len(candidates)}")
    print(f"Similar pairs found: {len(all_judgments)}")
    print(f"Duplicates identified: {len(all_merges)}")
    
    if len(all_merges) == 0:
        print("\n✨ No semantic duplicates found!")
        conn.close()
        return
    
    print(f"\n📄 Judgments saved to: {judgment_file}")
    
    # Show merges
    print(f"\n{'='*80}")
    print("MERGES TO APPLY:")
    print(f"{'='*80}\n")
    
    for judgment in all_merges:
        verdict = judgment['verdict']
        pair = judgment['pair']
        print(f"• [{judgment['parent_name']}]")
        print(f"  Keep: {verdict['keep_name']} ({verdict['keep_id']})")
        print(f"  Merge: {pair['name1'] if verdict['merge_id'] != pair['id1'] else pair['name2']}")
        print(f"  Reason: {verdict['reason']}")
        print(f"  Similarity: {pair['similarity']:.3f}\n")
    
    # Apply merges
    print(f"{'='*80}")
    print("🔨 APPLYING MERGES")
    print(f"{'='*80}\n")
    
    stats = {'merged': 0, 'relationships': 0, 'errors': 0}
    
    for i, judgment in enumerate(all_merges, 1):
        verdict = judgment['verdict']
        parent_name = judgment['parent_name']
        
        keep_id = verdict['keep_id']
        merge_id = verdict['merge_id']
        
        print(f"[{i}/{len(all_merges)}] [{parent_name}] {verdict['keep_name']}")
        
        try:
            children, parents = apply_merge(conn, merge_id, keep_id)
            stats['merged'] += 1
            stats['relationships'] += children + parents
            print(f"   ✓ {merge_id} → {keep_id}\n")
        except Exception as e:
            print(f"   ❌ {merge_id}: {e}\n")
            stats['errors'] += 1
    
    conn.close()
    
    # Final summary
    print(f"{'='*80}")
    print("✅ SEMANTIC DEDUPLICATION COMPLETE")
    print(f"{'='*80}\n")
    print(f"📊 Statistics:")
    print(f"   Items merged: {stats['merged']}")
    print(f"   Relationships updated: {stats['relationships']}")
    print(f"   Errors: {stats['errors']}")
    print(f"\n📄 Judgments: {judgment_file}")
    print(f"\n🔄 Next: Re-export folder structure")
    print(f"   python3 export_skills_to_folders.py")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
