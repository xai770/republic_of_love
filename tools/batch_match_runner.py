#!/usr/bin/env python3
"""
Batch Match Runner - Process all postings for a profile efficiently.

Strategy:
1. Compute embedding scores for ALL postings (fast, ~0.1s each)
2. Filter to top N candidates by score
3. Only call LLM (Clara) on the filtered set

This reduces 2000 postings × 15s = 8+ hours
to: 2000 × 0.1s + 50 × 15s = 3 min + 12 min = ~15 min

Usage:
    python tools/batch_match_runner.py <profile_id> [--top N] [--min-score 0.3] [--workers 4]
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection
from tools.skill_embeddings import get_embedding, cosine_similarity


# ============================================================================
# CONFIGURATION
# ============================================================================
MATCH_THRESHOLD = 0.70
PARTIAL_THRESHOLD = 0.60

RESTRICTED_DOMAINS = {
    'legal': {
        'title_keywords': ['lawyer', 'attorney', 'counsel', 'legal', 'paralegal'],
        'skill_keywords': ['bar admission', 'jd degree', 'legal research', 'litigation'],
        'required_domains': ['legal', 'law'],
    },
    'medical': {
        'title_keywords': ['physician', 'doctor', 'nurse', 'surgeon', 'medical director'],
        'skill_keywords': ['medical license', 'board certified', 'clinical'],
        'required_domains': ['medical', 'healthcare', 'clinical'],
    },
    'accounting_cpa': {
        'title_keywords': ['cpa', 'certified public accountant'],
        'skill_keywords': ['cpa license', 'cpa certification'],
        'required_domains': ['accounting', 'cpa'],
    },
}


# ============================================================================
# DATA LOADING
# ============================================================================
def get_profile_data(conn, profile_id: int) -> dict:
    """Load profile with skills from profiles.skill_keywords."""
    cur = conn.cursor()
    cur.execute("""
        SELECT p.profile_id, p.full_name, p.current_title, p.years_of_experience, p.skill_keywords
        FROM profiles p WHERE p.profile_id = %s
    """, (profile_id,))
    row = cur.fetchone()
    if not row:
        return None
    
    profile = {
        'profile_id': row['profile_id'],
        'full_name': row['full_name'],
        'current_title': row['current_title'],
        'years_of_experience': row['years_of_experience'],
    }
    
    # Get skills from skill_keywords
    skills = row['skill_keywords'] or []
    if isinstance(skills, str):
        import json
        skills = json.loads(skills)
    
    skill_names = []
    for s in skills:
        if isinstance(s, str):
            skill_names.append(s)
        elif isinstance(s, dict) and 'skill' in s:
            skill_names.append(s['skill'])
    
    profile['skills'] = list(set(skill_names))
    profile['domains'] = []  # Deprecated: was from profile_facets
    profile['certificates'] = []  # Deprecated: was from profile_facets
    profile['seniority'] = None  # Could derive from title later
    
    return profile


def get_all_postings(conn) -> list:
    """Get all active postings with summaries."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT p.posting_id, p.job_title, p.source
        FROM postings p
        WHERE p.status = 'active'
          AND p.extracted_summary IS NOT NULL
    """)
    
    postings = []
    for row in cur.fetchall():
        postings.append(dict(row))
    
    return postings


def get_posting_facets(conn, posting_id: int) -> list:
    """Deprecated: embeddings handle skill matching."""
    return []  # posting_facets table no longer used


# ============================================================================
# DOMAIN GATES
# ============================================================================
def detect_posting_domain(posting: dict, requirements: list) -> str:
    """Detect if posting belongs to a restricted domain."""
    title = (posting.get('job_title') or '').lower()
    
    for domain, config in RESTRICTED_DOMAINS.items():
        for kw in config['title_keywords']:
            if kw in title:
                return domain
        
        critical_skills = [
            r['skill_owl_name'].lower() for r in requirements
            if r.get('importance') in ('critical', 'required') and r.get('skill_owl_name')
        ]
        for kw in config['skill_keywords']:
            if any(kw in skill for skill in critical_skills):
                return domain
    
    return None


def check_domain_gate(profile: dict, posting_domain: str) -> tuple:
    """Check if profile can pass the domain gate."""
    if not posting_domain:
        return True, "No restricted domain"
    
    profile_domains = [d.lower() for d in profile.get('domains', [])]
    required_domains = RESTRICTED_DOMAINS[posting_domain]['required_domains']
    
    for req_domain in required_domains:
        if any(req_domain in pd for pd in profile_domains):
            return True, f"Profile has {posting_domain} domain experience"
    
    return False, f"Posting requires {posting_domain} domain experience"


# ============================================================================
# EMBEDDING SCORING (FAST)
# ============================================================================
def compute_quick_score(profile_skills: list, requirements: list, profile_emb_cache: dict) -> dict:
    """Compute embedding score without LLM - fast batch operation."""
    if not profile_skills or not requirements:
        return {'score': 0.0, 'match_rate': '0/0', 'matched': 0}
    
    total_weight = 0
    weighted_score = 0
    matched_count = 0
    
    for req in requirements:
        skill_name = req.get('skill_owl_name')
        if not skill_name:
            continue
        
        req_weight = req.get('weight') or 70
        total_weight += req_weight
        
        # Get requirement embedding
        req_emb = get_embedding(skill_name)
        if req_emb is None:
            continue
        
        # Find best match from profile
        best_score = 0.0
        for profile_skill in profile_skills:
            if profile_skill in profile_emb_cache:
                p_emb = profile_emb_cache[profile_skill]
            else:
                p_emb = get_embedding(profile_skill)
                if p_emb is not None:
                    profile_emb_cache[profile_skill] = p_emb
            
            if p_emb is not None:
                score = cosine_similarity(p_emb, req_emb)
                if score > best_score:
                    best_score = score
        
        if best_score >= MATCH_THRESHOLD:
            matched_count += 1
            weighted_score += req_weight * best_score
        elif best_score >= PARTIAL_THRESHOLD:
            weighted_score += req_weight * best_score * 0.5
    
    overall_score = 0.0
    if total_weight > 0:
        overall_score = weighted_score / total_weight
    
    return {
        'score': overall_score,
        'match_rate': f"{matched_count}/{len(requirements)}",
        'matched': matched_count
    }


# ============================================================================
# BATCH PROCESSING
# ============================================================================
def score_all_postings(profile: dict, postings: list, conn) -> list:
    """Score all postings using embeddings only (fast)."""
    print(f"📊 Scoring {len(postings)} postings...")
    
    profile_emb_cache = {}
    results = []
    
    start = time.time()
    for i, posting in enumerate(postings):
        # Get requirements
        requirements = get_posting_facets(conn, posting['posting_id'])
        
        # Check domain gate
        posting_domain = detect_posting_domain(posting, requirements)
        gate_passed, gate_reason = check_domain_gate(profile, posting_domain)
        
        if not gate_passed:
            results.append({
                'posting_id': posting['posting_id'],
                'job_title': posting['job_title'],
                'score': 0.0,
                'match_rate': '0/0',
                'gate_passed': False,
                'gate_reason': gate_reason,
            })
            continue
        
        # Compute score
        score_data = compute_quick_score(profile['skills'], requirements, profile_emb_cache)
        
        results.append({
            'posting_id': posting['posting_id'],
            'job_title': posting['job_title'],
            'score': score_data['score'],
            'match_rate': score_data['match_rate'],
            'gate_passed': True,
            'gate_reason': None,
        })
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f"   {i+1}/{len(postings)} scored ({rate:.1f}/sec)")
    
    elapsed = time.time() - start
    print(f"✅ Scored {len(postings)} in {elapsed:.1f}s ({len(postings)/elapsed:.1f}/sec)")
    
    return results


def run_clara_on_posting(profile_id: int, posting_id: int) -> dict:
    """Run Clara actor on a single posting."""
    import subprocess
    
    try:
        result = subprocess.run(
            ['python3', 'actors/profile_posting_matches__report_C__clara.py', 
             str(profile_id), str(posting_id)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent.parent)
        )
        
        if result.returncode == 0:
            return {'success': True, 'posting_id': posting_id}
        else:
            return {'success': False, 'posting_id': posting_id, 'error': result.stderr[:200]}
    except Exception as e:
        return {'success': False, 'posting_id': posting_id, 'error': str(e)}


def run_clara_batch(profile_id: int, posting_ids: list, workers: int = 4) -> list:
    """Run Clara on multiple postings in parallel."""
    print(f"🤖 Running Clara on {len(posting_ids)} postings with {workers} workers...")
    
    results = []
    start = time.time()
    completed = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_clara_on_posting, profile_id, pid): pid 
            for pid in posting_ids
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            if completed % 5 == 0:
                elapsed = time.time() - start
                rate = completed / elapsed * 60
                remaining = len(posting_ids) - completed
                eta = remaining / (completed / elapsed) if completed > 0 else 0
                print(f"   {completed}/{len(posting_ids)} done ({rate:.1f}/min, ETA: {eta:.0f}s)")
    
    elapsed = time.time() - start
    success = sum(1 for r in results if r['success'])
    print(f"✅ Completed {success}/{len(posting_ids)} in {elapsed:.1f}s")
    
    return results


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description='Batch process matches for a profile')
    parser.add_argument('profile_id', type=int, help='Profile ID')
    parser.add_argument('--top', type=int, default=50, help='Process top N postings by score')
    parser.add_argument('--min-score', type=float, default=0.25, help='Minimum score threshold')
    parser.add_argument('--workers', type=int, default=4, help='Parallel workers for LLM calls')
    parser.add_argument('--score-only', action='store_true', help='Only compute scores, no LLM')
    parser.add_argument('--skip-existing', action='store_true', default=True, help='Skip already processed')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        # Load profile
        print(f"👤 Loading profile {args.profile_id}...")
        profile = get_profile_data(conn, args.profile_id)
        if not profile:
            print(f"❌ Profile {args.profile_id} not found")
            return 1
        print(f"   Name: {profile['full_name']}")
        print(f"   Skills: {len(profile['skills'])}")
        
        # Get all postings
        postings = get_all_postings(conn)
        print(f"📋 Found {len(postings)} postings with facets")
        
        # Filter out already processed
        if args.skip_existing:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_id FROM profile_posting_matches WHERE profile_id = %s
            """, (args.profile_id,))
            existing = {r['posting_id'] for r in cur.fetchall()}
            postings = [p for p in postings if p['posting_id'] not in existing]
            print(f"   After filtering existing: {len(postings)}")
        
        if not postings:
            print("✅ All postings already processed!")
            return 0
        
        # Score all postings (fast)
        scores = score_all_postings(profile, postings, conn)
        
        # Filter and sort
        candidates = [s for s in scores if s['gate_passed'] and s['score'] >= args.min_score]
        candidates.sort(key=lambda x: x['score'], reverse=True)
        candidates = candidates[:args.top]
        
        print(f"\n📊 Score distribution:")
        print(f"   Gate blocked: {sum(1 for s in scores if not s['gate_passed'])}")
        print(f"   Score >= {args.min_score}: {len([s for s in scores if s['gate_passed'] and s['score'] >= args.min_score])}")
        print(f"   Processing top {len(candidates)}")
        
        if args.score_only:
            print("\n🔝 Top candidates:")
            for c in candidates[:20]:
                print(f"   {c['score']*100:5.1f}% - {c['job_title'][:50]}")
            return 0
        
        if not candidates:
            print("⚠️ No candidates above threshold")
            return 0
        
        # Run Clara on top candidates
        print()
        posting_ids = [c['posting_id'] for c in candidates]
        results = run_clara_batch(args.profile_id, posting_ids, args.workers)
        
        # Summary
        print(f"\n📊 Final Summary:")
        print(f"   Total postings: {len(postings)}")
        print(f"   Scored: {len(scores)}")
        print(f"   LLM processed: {len(results)}")
        print(f"   Successful: {sum(1 for r in results if r['success'])}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
