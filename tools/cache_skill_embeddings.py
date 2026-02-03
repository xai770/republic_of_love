#!/usr/bin/env python3
"""
Pre-compute and cache skill embeddings for fast matching.

Instead of computing embeddings on-the-fly for every profile-posting comparison,
we compute them once and store in the database.

This reduces:
  4 users × 2000 postings × 10 skills = 80,000 embedding calls
To:
  5,400 unique skills embedded ONCE

Usage:
    python tools/cache_skill_embeddings.py          # Cache all missing
    python tools/cache_skill_embeddings.py --force  # Recompute all
    python tools/cache_skill_embeddings.py --stats  # Show cache stats
"""
import sys
import json
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection
from tools.skill_embeddings import get_embedding


def get_all_skills(conn) -> set:
    """Get all unique skill names from profiles and postings."""
    cur = conn.cursor()
    
    skills = set()
    
    # Profile skills from profiles.skill_keywords
    cur.execute("SELECT skill_keywords FROM profiles WHERE skill_keywords IS NOT NULL")
    import json
    for row in cur.fetchall():
        keywords = row['skill_keywords']
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        if keywords:
            for s in keywords:
                if isinstance(s, str):
                    skills.add(s.strip())
                elif isinstance(s, dict) and 'skill' in s:
                    skills.add(s['skill'].strip())
    
    # Posting skills from posting_facets (if they exist)
    cur.execute("SELECT DISTINCT skill_owl_name FROM posting_facets WHERE skill_owl_name IS NOT NULL")
    for row in cur.fetchall():
        skills.add(row['skill_owl_name'].strip())
    
    return skills


def get_cached_skills(conn) -> set:
    """Get skills already in cache."""
    cur = conn.cursor()
    cur.execute("SELECT skill_name FROM skill_embeddings")
    return {row['skill_name'] for row in cur.fetchall()}


def cache_embedding(conn, skill_name: str) -> bool:
    """Compute and cache embedding for a skill."""
    embedding = get_embedding(skill_name)
    if embedding is None:
        return False
    
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO skill_embeddings (skill_name, embedding)
        VALUES (%s, %s)
        ON CONFLICT (skill_name) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            created_at = NOW()
    """, (skill_name, json.dumps(embedding.tolist())))
    
    return True


def cache_all_embeddings(conn, skills: set, batch_size: int = 100) -> dict:
    """Cache embeddings for all skills."""
    print(f"📦 Caching {len(skills)} skill embeddings...")
    
    success = 0
    failed = 0
    start = time.time()
    
    skills_list = list(skills)
    for i, skill in enumerate(skills_list):
        if cache_embedding(conn, skill):
            success += 1
        else:
            failed += 1
        
        if (i + 1) % batch_size == 0:
            conn.commit()
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(skills) - i - 1) / rate
            print(f"   {i+1}/{len(skills)} ({rate:.1f}/sec, ETA: {eta:.0f}s)")
    
    conn.commit()
    elapsed = time.time() - start
    
    print(f"✅ Cached {success} embeddings in {elapsed:.1f}s ({success/elapsed:.1f}/sec)")
    if failed:
        print(f"⚠️ Failed: {failed}")
    
    return {'success': success, 'failed': failed, 'elapsed': elapsed}


def show_stats(conn):
    """Show cache statistics."""
    cur = conn.cursor()
    
    # Cache size
    cur.execute("SELECT COUNT(*) as cnt FROM skill_embeddings")
    cached = cur.fetchone()['cnt']
    
    # All skills
    all_skills = get_all_skills(conn)
    
    # Coverage
    cached_skills = get_cached_skills(conn)
    profile_skills = set()
    posting_skills = set()
    
    # Profile skills from profiles.skill_keywords
    cur.execute("SELECT skill_keywords FROM profiles WHERE skill_keywords IS NOT NULL")
    import json
    for row in cur.fetchall():
        keywords = row['skill_keywords']
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        if keywords:
            for s in keywords:
                if isinstance(s, str):
                    profile_skills.add(s.strip())
                elif isinstance(s, dict) and 'skill' in s:
                    profile_skills.add(s['skill'].strip())
    
    cur.execute("SELECT DISTINCT skill_owl_name FROM posting_facets WHERE skill_owl_name IS NOT NULL")
    for row in cur.fetchall():
        posting_skills.add(row['skill_owl_name'].strip())
    
    profile_covered = len(profile_skills & cached_skills) if profile_skills else 0
    posting_covered = len(posting_skills & cached_skills) if posting_skills else 0
    
    print(f"📊 Skill Embedding Cache Stats")
    print(f"   ─────────────────────────────")
    print(f"   Cached embeddings: {cached}")
    print(f"   Total unique skills: {len(all_skills)}")
    print(f"   Coverage: {cached/len(all_skills)*100:.1f}%")
    print()
    print(f"   Profile skills: {len(profile_skills)} ({profile_covered} cached = {profile_covered/len(profile_skills)*100:.1f}%)")
    print(f"   Posting skills: {len(posting_skills)} ({posting_covered} cached = {posting_covered/len(posting_skills)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Cache skill embeddings')
    parser.add_argument('--force', action='store_true', help='Recompute all embeddings')
    parser.add_argument('--stats', action='store_true', help='Show cache statistics')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        if args.stats:
            show_stats(conn)
            return 0
        
        # Get all skills
        all_skills = get_all_skills(conn)
        print(f"📋 Found {len(all_skills)} unique skills")
        
        if args.force:
            # Recompute all
            to_cache = all_skills
        else:
            # Only cache missing
            cached = get_cached_skills(conn)
            to_cache = all_skills - cached
            print(f"   Already cached: {len(cached)}")
            print(f"   To cache: {len(to_cache)}")
        
        if not to_cache:
            print("✅ All skills already cached!")
            show_stats(conn)
            return 0
        
        # Cache embeddings
        result = cache_all_embeddings(conn, to_cache)
        
        print()
        show_stats(conn)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
