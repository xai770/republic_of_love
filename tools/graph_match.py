#!/usr/bin/env python3
"""
graph_match.py - Match candidates to job requirements using overlap graph

CONCEPT: Instead of folders, use the 'requires' relationships as an overlap graph.
A candidate skill matches job requirements if it has high aggregate overlap with
the required skills (transitively through the graph).

Two approaches:
1. FOLDER-BASED (current): skill.belongs_to = dimension, match by dimension
2. GRAPH-BASED (new): sum(requires.strength) over job skills, rank by overlap

Usage:
    python3 tools/graph_match.py "python" "data analysis" "communication"
    python3 tools/graph_match.py --compare "python" "leadership" "sql"
    python3 tools/graph_match.py --job-id 12345

Author: Sandy  
Date: 2026-01-21
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2.extras
from core.database import get_connection


def resolve_skill_ids(conn, skill_names: List[str]) -> Dict[str, int]:
    """
    Resolve skill names to owl_ids.
    Uses fuzzy matching via owl_names.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    resolved = {}
    
    for name in skill_names:
        # Try exact match first
        cur.execute("""
            SELECT n.owl_id, o.canonical_name
            FROM owl_names n
            JOIN owl o USING (owl_id)
            WHERE LOWER(n.display_name) = LOWER(%s)
            LIMIT 1
        """, (name,))
        
        row = cur.fetchone()
        if row:
            resolved[name] = {'owl_id': row['owl_id'], 'canonical': row['canonical_name']}
            continue
        
        # Fuzzy match
        cur.execute("""
            SELECT n.owl_id, o.canonical_name, n.display_name
            FROM owl_names n
            JOIN owl o USING (owl_id)
            WHERE LOWER(n.display_name) LIKE LOWER(%s)
            ORDER BY LENGTH(n.display_name)
            LIMIT 1
        """, (f'%{name}%',))
        
        row = cur.fetchone()
        if row:
            resolved[name] = {'owl_id': row['owl_id'], 'canonical': row['canonical_name']}
        else:
            resolved[name] = None
    
    return resolved


def match_by_graph(conn, job_skill_ids: List[int], limit: int = 20) -> List[Dict]:
    """
    GRAPH-BASED MATCHING: Find skills with highest aggregate overlap.
    
    Algorithm:
    1. For each candidate skill, sum the strength of 'requires' edges to job skills
    2. Normalize by number of job skills
    3. Rank by aggregate overlap
    
    This captures transitive relationships through the graph.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    if not job_skill_ids:
        return []
    
    placeholders = ','.join(['%s'] * len(job_skill_ids))
    
    # Direct overlap: skills that require the job skills
    cur.execute(f"""
        WITH job_skills AS (
            SELECT unnest(ARRAY[{placeholders}]::int[]) as owl_id
        ),
        direct_overlap AS (
            -- Skills that directly require job skills
            SELECT 
                r.owl_id as candidate_id,
                SUM(r.strength) as total_strength,
                COUNT(*) as matched_skills,
                ARRAY_AGG(o2.canonical_name) as matched_names
            FROM owl_relationships r
            JOIN owl o2 ON r.related_owl_id = o2.owl_id
            WHERE r.relationship = 'requires'
              AND r.related_owl_id IN (SELECT owl_id FROM job_skills)
            GROUP BY r.owl_id
        ),
        transitive_overlap AS (
            -- Skills connected via one hop (skill -> X -> job_skill)
            SELECT 
                r1.owl_id as candidate_id,
                SUM(r1.strength * r2.strength) as total_strength,
                COUNT(DISTINCT r2.related_owl_id) as matched_skills
            FROM owl_relationships r1
            JOIN owl_relationships r2 ON r1.related_owl_id = r2.owl_id
            WHERE r1.relationship = 'requires'
              AND r2.relationship = 'requires'
              AND r2.related_owl_id IN (SELECT owl_id FROM job_skills)
              AND r1.owl_id NOT IN (SELECT owl_id FROM job_skills)  -- Exclude job skills themselves
            GROUP BY r1.owl_id
        )
        SELECT 
            o.canonical_name,
            o.owl_id,
            COALESCE(d.total_strength, 0) as direct_overlap,
            COALESCE(d.matched_skills, 0) as direct_matches,
            COALESCE(t.total_strength, 0) as transitive_overlap,
            -- Weighted score: direct connections worth more than transitive
            (COALESCE(d.total_strength, 0) + 0.5 * COALESCE(t.total_strength, 0)) / %s as overlap_score,
            d.matched_names as direct_matched
        FROM owl o
        LEFT JOIN direct_overlap d ON o.owl_id = d.candidate_id
        LEFT JOIN transitive_overlap t ON o.owl_id = t.candidate_id
        WHERE (d.total_strength IS NOT NULL OR t.total_strength IS NOT NULL)
          AND o.owl_id NOT IN (SELECT owl_id FROM job_skills)
        ORDER BY overlap_score DESC
        LIMIT %s
    """, (*job_skill_ids, len(job_skill_ids), limit))
    
    return [dict(row) for row in cur.fetchall()]


def match_by_folder(conn, job_skill_ids: List[int], limit: int = 20) -> List[Dict]:
    """
    FOLDER-BASED MATCHING: Find skills in same folders as job skills.
    
    Algorithm:
    1. Find which folders contain job skills
    2. Return all skills in those folders
    3. Rank by... well, nothing really (that's the problem!)
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    if not job_skill_ids:
        return []
    
    placeholders = ','.join(['%s'] * len(job_skill_ids))
    
    cur.execute(f"""
        WITH job_skills AS (
            SELECT unnest(ARRAY[{placeholders}]::int[]) as owl_id
        ),
        job_folders AS (
            -- Find folders containing job skills
            SELECT DISTINCT r.related_owl_id as folder_id
            FROM owl_relationships r
            WHERE r.owl_id IN (SELECT owl_id FROM job_skills)
              AND r.relationship = 'belongs_to'
        ),
        folder_skills AS (
            -- Find all skills in those folders
            SELECT 
                r.owl_id as candidate_id,
                o2.canonical_name as folder_name
            FROM owl_relationships r
            JOIN owl o2 ON r.related_owl_id = o2.owl_id
            WHERE r.related_owl_id IN (SELECT folder_id FROM job_folders)
              AND r.relationship = 'belongs_to'
              AND r.owl_id NOT IN (SELECT owl_id FROM job_skills)
        )
        SELECT 
            o.canonical_name,
            o.owl_id,
            fs.folder_name,
            1.0 as folder_score  -- No ranking within folder!
        FROM owl o
        JOIN folder_skills fs ON o.owl_id = fs.candidate_id
        ORDER BY o.canonical_name
        LIMIT %s
    """, (*job_skill_ids, limit))
    
    return [dict(row) for row in cur.fetchall()]


def compare_approaches(conn, job_skills: List[str], limit: int = 15):
    """
    Run both matching approaches and compare results.
    """
    # Resolve skill names
    resolved = resolve_skill_ids(conn, job_skills)
    
    print("\n" + "="*70)
    print("GRAPH vs FOLDER MATCHING COMPARISON")
    print("="*70)
    
    print(f"\n📋 JOB REQUIREMENTS:")
    valid_ids = []
    for name, info in resolved.items():
        if info:
            print(f"   ✓ {name} → {info['canonical']} (owl_id={info['owl_id']})")
            valid_ids.append(info['owl_id'])
        else:
            print(f"   ✗ {name} → NOT FOUND")
    
    if not valid_ids:
        print("\n❌ No valid skills found. Cannot match.")
        return
    
    # Graph-based matching
    print(f"\n🔗 GRAPH-BASED MATCHING (overlap score)")
    print("   " + "-"*65)
    graph_results = match_by_graph(conn, valid_ids, limit)
    for i, r in enumerate(graph_results[:limit], 1):
        score = r['overlap_score']
        direct = r['direct_overlap']
        trans = r['transitive_overlap']
        bar = '█' * int(score * 20)
        print(f"   {i:2}. {r['canonical_name'][:40]:40} {score:.2f} {bar}")
        if r['direct_matched']:
            matched = ', '.join(r['direct_matched'][:3])
            print(f"       └─ directly requires: {matched}")
    
    # Folder-based matching
    print(f"\n📁 FOLDER-BASED MATCHING (same folder)")
    print("   " + "-"*65)
    folder_results = match_by_folder(conn, valid_ids, limit)
    
    # Group by folder
    by_folder = {}
    for r in folder_results:
        folder = r['folder_name']
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(r['canonical_name'])
    
    for folder, skills in sorted(by_folder.items()):
        print(f"   📂 {folder}:")
        for skill in skills[:5]:
            print(f"      • {skill}")
        if len(skills) > 5:
            print(f"      ... and {len(skills)-5} more")
    
    # Comparison
    print(f"\n📊 COMPARISON ANALYSIS")
    print("   " + "-"*65)
    
    graph_set = {r['canonical_name'] for r in graph_results}
    folder_set = {r['canonical_name'] for r in folder_results}
    
    both = graph_set & folder_set
    graph_only = graph_set - folder_set
    folder_only = folder_set - graph_set
    
    print(f"   Skills found by BOTH methods:      {len(both)}")
    print(f"   Skills found ONLY by graph:        {len(graph_only)}")
    print(f"   Skills found ONLY by folder:       {len(folder_only)}")
    
    if graph_only:
        print(f"\n   🔗 Graph found but folder missed:")
        for skill in list(graph_only)[:5]:
            print(f"      • {skill}")
    
    if folder_only:
        print(f"\n   📁 Folder found but graph missed:")
        for skill in list(folder_only)[:5]:
            print(f"      • {skill}")


def main():
    parser = argparse.ArgumentParser(description='Graph-based skill matching')
    parser.add_argument('skills', nargs='*', help='Skill names to match against')
    parser.add_argument('--compare', action='store_true', help='Compare graph vs folder matching')
    parser.add_argument('--limit', type=int, default=15, help='Max results')
    parser.add_argument('--graph-only', action='store_true', help='Only show graph-based results')
    
    args = parser.parse_args()
    
    if not args.skills:
        print("Usage: python3 tools/graph_match.py 'python' 'sql' 'leadership'")
        print("       python3 tools/graph_match.py --compare 'python' 'data analysis'")
        return
    
    with get_connection() as conn:
        if args.compare or not args.graph_only:
            compare_approaches(conn, args.skills, args.limit)
        else:
            resolved = resolve_skill_ids(conn, args.skills)
            valid_ids = [info['owl_id'] for info in resolved.values() if info]
            results = match_by_graph(conn, valid_ids, args.limit)
            for r in results:
                print(f"{r['overlap_score']:.2f}  {r['canonical_name']}")


if __name__ == '__main__':
    main()
