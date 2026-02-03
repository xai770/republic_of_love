#!/usr/bin/env python3
"""
profile_matcher.py - Match profiles to postings via embedding similarity

ARCHITECTURE:
    Profile Skills ←→ Posting Requirements (direct comparison)
    No OWL intermediary needed - embeddings do the semantic work.

USAGE:
    # Match a profile against all postings
    python3 tools/profile_matcher.py profile <profile_id>
    
    # Match a posting against all profiles  
    python3 tools/profile_matcher.py posting <posting_id>
    
    # Match specific profile to specific posting
    python3 tools/profile_matcher.py match <profile_id> <posting_id>

THRESHOLD: 0.70 (70% similarity = confident match)

Author: Arden
Date: 2026-01-21
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
from tools.skill_embeddings import get_embedding, cosine_similarity

# ============================================================================
# CONFIGURATION
# ============================================================================
MATCH_THRESHOLD = 0.70  # Confident match
PARTIAL_THRESHOLD = 0.60  # Related concept

# ============================================================================
# DOMAIN GATES - Loaded from config/domain_gates.json
# ============================================================================
def load_domain_gates() -> dict:
    """Load domain gates from config file."""
    gates_file = PROJECT_ROOT / "config" / "domain_gates.json"
    if gates_file.exists():
        with open(gates_file) as f:
            gates = json.load(f)
            # Remove comments
            return {k: v for k, v in gates.items() if not k.startswith('_')}
    return {}

RESTRICTED_DOMAINS = load_domain_gates()

def detect_posting_domain(posting: Dict) -> Optional[str]:
    """
    Detect if posting belongs to a restricted domain.
    Uses title keywords and critical skills.
    """
    title = posting.get('title', '').lower()
    
    for domain, config in RESTRICTED_DOMAINS.items():
        # Check title keywords
        for kw in config['title_keywords']:
            if kw in title:
                return domain
        
        # Check critical/required skills
        critical_skills = [
            r['name'].lower() for r in posting.get('requirements', [])
            if r.get('importance') in ('critical', 'required')
        ]
        for kw in config['skill_keywords']:
            if any(kw in skill for skill in critical_skills):
                return domain
    
    return None


def check_domain_gate(profile: Dict, posting: Dict) -> Tuple[bool, str]:
    """
    Check if profile can pass the domain gate for this posting.
    
    Returns:
        (passes: bool, reason: str)
    """
    posting_domain = detect_posting_domain(posting)
    
    if not posting_domain:
        return True, "No restricted domain"
    
    # Check if profile has matching domain experience
    profile_domains = [d.lower() for d in profile.get('domains', [])]
    required_domains = RESTRICTED_DOMAINS[posting_domain]['required_domains']
    
    for req_domain in required_domains:
        if any(req_domain in pd for pd in profile_domains):
            return True, f"Profile has {posting_domain} domain experience"
    
    return False, f"Posting requires {posting_domain} domain experience"


# ============================================================================
# DATA LOADING
# ============================================================================
def get_profile(conn, profile_id: int) -> Optional[Dict]:
    """Load profile with skills from profiles.skill_keywords."""
    cur = conn.cursor()
    
    # Get profile info with skills
    cur.execute("""
        SELECT profile_id, full_name, current_title, skill_keywords
        FROM profiles
        WHERE profile_id = %s
    """, (profile_id,))
    row = cur.fetchone()
    if not row:
        return None
    
    profile = {
        'profile_id': row['profile_id'],
        'name': row['full_name'],
        'title': row['current_title'],
        'skills': [],
        'domains': [],  # Deprecated: was from profile_facets
        'certificates': [],  # Deprecated: was from profile_facets
    }
    
    # Get skills from profiles.skill_keywords
    skills = row['skill_keywords'] or []
    if isinstance(skills, str):
        import json
        skills = json.loads(skills)
    
    skill_names = []
    for s in skills:
        if isinstance(s, str):
            skill_names.append(s.lower())
        elif isinstance(s, dict) and 'skill' in s:
            skill_names.append(s['skill'].lower())
    profile['skills'] = list(set(skill_names))
    
    return profile


def get_posting(conn, posting_id: int) -> Optional[Dict]:
    """Load posting with requirements."""
    cur = conn.cursor()
    
    # Get posting info
    cur.execute("""
        SELECT posting_id, job_title, source
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    row = cur.fetchone()
    if not row:
        return None
    
    posting = {
        'posting_id': row['posting_id'],
        'title': row['job_title'],
        'company': row['source'] or 'Unknown',
        'requirements': []  # Embeddings handle skill matching, no facets needed
    }
    
    return posting


def get_all_profiles(conn) -> List[Dict]:
    """Load all profiles."""
    cur = conn.cursor()
    cur.execute("SELECT profile_id FROM profiles WHERE skill_keywords IS NOT NULL")
    profile_ids = [row['profile_id'] for row in cur.fetchall()]
    return [get_profile(conn, pid) for pid in profile_ids if get_profile(conn, pid)]


def get_all_postings(conn, limit: int = 100) -> List[Dict]:
    """Load active postings with summaries."""
    cur = conn.cursor()
    cur.execute("""
        SELECT posting_id 
        FROM postings 
        WHERE posting_status = 'active' AND extracted_summary IS NOT NULL
        LIMIT %s
    """, (limit,))
    posting_ids = [row['posting_id'] for row in cur.fetchall()]
    return [get_posting(conn, pid) for pid in posting_ids if get_posting(conn, pid)]


# ============================================================================
# MATCHING ENGINE
# ============================================================================
def match_skills(profile_skills: List[str], requirements: List[Dict]) -> Dict:
    """
    Compare profile skills against posting requirements.
    
    Returns:
        {
            'matches': [...],
            'unmatched': [...],
            'score': 0.0-100.0,
            'match_rate': '5/7'
        }
    """
    result = {
        'matches': [],
        'partial_matches': [],
        'unmatched': [],
        'score': 0.0,
        'match_rate': ''
    }
    
    if not profile_skills or not requirements:
        return result
    
    # Pre-compute profile skill embeddings
    profile_embs = []
    for skill in profile_skills:
        emb = get_embedding(skill)
        if emb is not None:
            profile_embs.append((skill, emb))
    
    if not profile_embs:
        return result
    
    matched_count = 0
    total_weight = 0
    weighted_score = 0
    
    for req in requirements:
        req_name = req['name']
        req_weight = req.get('weight', 70) or 70
        total_weight += req_weight
        
        req_emb = get_embedding(req_name)
        if req_emb is None:
            continue
        
        # Find best matching profile skill
        best_score = 0.0
        best_skill = None
        
        for skill_name, skill_emb in profile_embs:
            score = cosine_similarity(req_emb, skill_emb)
            if score > best_score:
                best_score = score
                best_skill = skill_name
        
        match_info = {
            'requirement': req_name,
            'importance': req.get('importance', 'medium'),
            'weight': req_weight,
            'matched_by': best_skill,
            'score': round(best_score, 3)
        }
        
        if best_score >= MATCH_THRESHOLD:
            result['matches'].append(match_info)
            matched_count += 1
            weighted_score += req_weight * best_score
        elif best_score >= PARTIAL_THRESHOLD:
            result['partial_matches'].append(match_info)
            weighted_score += req_weight * best_score * 0.5  # Half credit
        else:
            result['unmatched'].append(match_info)
    
    # Calculate overall score
    if total_weight > 0:
        result['score'] = round(weighted_score / total_weight * 100, 1)
    
    result['match_rate'] = f"{matched_count}/{len(requirements)}"
    
    return result


def match_profile_to_posting(profile: Dict, posting: Dict) -> Dict:
    """Full match report for profile vs posting."""
    
    # Check domain gate FIRST
    gate_passes, gate_reason = check_domain_gate(profile, posting)
    
    result = {
        'profile': {
            'id': profile['profile_id'],
            'name': profile['name'],
            'title': profile['title']
        },
        'posting': {
            'id': posting['posting_id'],
            'title': posting['title'],
            'company': posting['company']
        },
        'gate_passed': gate_passes,
        'gate_reason': gate_reason,
    }
    
    if not gate_passes:
        # Domain gate failed - return zero score
        result.update({
            'matches': [],
            'partial_matches': [],
            'unmatched': [],
            'score': 0.0,
            'match_rate': '0/0 (gated)'
        })
        return result
    
    # Gate passed - proceed with skill matching
    skills = profile['skills']
    requirements = posting['requirements']
    
    match_result = match_skills(skills, requirements)
    result.update(match_result)
    
    return result


# ============================================================================
# DISPLAY
# ============================================================================
def print_match_report(report: Dict):
    """Pretty print a match report."""
    print()
    print('=' * 70)
    print(f"MATCH REPORT")
    print('=' * 70)
    print(f"Profile: {report['profile']['name']} ({report['profile']['title']})")
    print(f"Posting: {report['posting']['title']} @ {report['posting']['company']}")
    print()
    
    # Show gate status
    if not report.get('gate_passed', True):
        print(f"🚫 DOMAIN GATE FAILED: {report.get('gate_reason', 'Unknown')}")
        print(f"   This posting requires specialized domain experience.")
        print()
        return
    
    print(f"📊 OVERALL SCORE: {report['score']}% ({report['match_rate']} requirements matched)")
    print()
    
    if report['matches']:
        print("✅ MATCHED REQUIREMENTS:")
        for m in report['matches']:
            imp = m['importance'] or 'medium'
            print(f"   [{imp[:3].upper()}] {m['requirement'][:35]:<35} ← {m['matched_by'][:30]} ({m['score']:.0%})")
    
    if report['partial_matches']:
        print()
        print("⚠️  PARTIAL MATCHES (60-70%):")
        for m in report['partial_matches']:
            print(f"   {m['requirement'][:35]:<35} ~ {m['matched_by'][:30]} ({m['score']:.0%})")
    
    if report['unmatched']:
        print()
        print("❌ UNMATCHED REQUIREMENTS:")
        for m in report['unmatched']:
            print(f"   {m['requirement'][:35]:<35}   (best: {m['matched_by'][:25]}, {m['score']:.0%})")
    
    print()


def print_ranking(rankings: List[Dict], entity_type: str, show_gated: bool = False):
    """Print ranked list of matches."""
    print()
    print('=' * 70)
    print(f"TOP MATCHES (ranked by score)")
    print('=' * 70)
    print()
    
    # Filter out gated postings unless requested
    active_rankings = [r for r in rankings if r.get('gate_passed', True)]
    gated_count = len(rankings) - len(active_rankings)
    
    for i, r in enumerate(active_rankings[:10], 1):
        if entity_type == 'profile':
            print(f"{i:2}. [{r['score']:5.1f}%] {r['posting']['title'][:40]} @ {r['posting']['company'][:20]}")
        else:
            print(f"{i:2}. [{r['score']:5.1f}%] {r['profile']['name'][:30]} - {r['profile']['title'][:30]}")
        print(f"         Matched: {r['match_rate']}")
    
    if gated_count > 0:
        print()
        print(f"🚫 {gated_count} postings excluded by domain gates (legal, medical, accounting)")
        if show_gated:
            gated = [r for r in rankings if not r.get('gate_passed', True)][:5]
            for r in gated:
                print(f"   - {r['posting']['title'][:45]} ({r['gate_reason']})")
    print()


# ============================================================================
# CLI COMMANDS
# ============================================================================
def cmd_match(args):
    """Match specific profile to specific posting."""
    with get_connection() as conn:
        profile = get_profile(conn, args.profile_id)
        if not profile:
            print(f"❌ Profile {args.profile_id} not found")
            return
        
        posting = get_posting(conn, args.posting_id)
        if not posting:
            print(f"❌ Posting {args.posting_id} not found")
            return
        
        report = match_profile_to_posting(profile, posting)
        print_match_report(report)


def cmd_profile(args):
    """Match a profile against all postings."""
    import sys
    
    with get_connection() as conn:
        profile = get_profile(conn, args.profile_id)
        if not profile:
            print(f"❌ Profile {args.profile_id} not found")
            return
        
        print(f"🔍 Matching {profile['name']} against all postings...")
        print(f"   Profile has {len(profile['skills'])} skills")
        print(f"   Profile domains: {profile.get('domains', [])}")
        
        postings = get_all_postings(conn, limit=args.limit)
        print(f"   Found {len(postings)} postings with requirements")
        print(f"   Computing embeddings (first run is slow, then cached)...")
        sys.stdout.flush()
        
        rankings = []
        for i, posting in enumerate(postings, 1):
            if posting['requirements']:
                report = match_profile_to_posting(profile, posting)
                rankings.append(report)
            
            # Progress every 10 postings
            if i % 10 == 0 or i == len(postings):
                print(f"   Progress: {i}/{len(postings)} postings", end='\r')
                sys.stdout.flush()
        
        print()  # Clear progress line
        
        # Sort by score
        rankings.sort(key=lambda x: x['score'], reverse=True)
        
        print_ranking(rankings, 'profile', show_gated=args.show_gated)
        
        # Show top match details
        if rankings and args.verbose:
            # Find top match that passed gate
            for r in rankings:
                if r.get('gate_passed', True):
                    print_match_report(r)
                    break


def cmd_posting(args):
    """Match a posting against all profiles."""
    with get_connection() as conn:
        posting = get_posting(conn, args.posting_id)
        if not posting:
            print(f"❌ Posting {args.posting_id} not found")
            return
        
        print(f"🔍 Matching '{posting['title']}' against all profiles...")
        
        profiles = get_all_profiles(conn)
        print(f"   Found {len(profiles)} profiles with skills")
        
        rankings = []
        for profile in profiles:
            if profile['skills']:
                report = match_profile_to_posting(profile, posting)
                rankings.append(report)
        
        # Sort by score
        rankings.sort(key=lambda x: x['score'], reverse=True)
        
        print_ranking(rankings, 'posting')
        
        # Show top match details
        if rankings and args.verbose:
            print_match_report(rankings[0])


def cmd_demo(args):
    """Demo with real data."""
    with get_connection() as conn:
        # Get first profile with skills
        profiles = get_all_profiles(conn)
        if not profiles:
            print("❌ No profiles with skills found")
            return
        
        # Get first posting with requirements
        postings = get_all_postings(conn, limit=10)
        if not postings:
            print("❌ No postings with requirements found")
            return
        
        print(f"📋 Found {len(profiles)} profiles, {len(postings)} postings")
        print()
        
        # Match first profile against first few postings
        profile = profiles[0]
        print(f"Testing: {profile['name']} ({len(profile['skills'])} skills)")
        print()
        
        for posting in postings[:3]:
            report = match_profile_to_posting(profile, posting)
            print(f"  vs {posting['title'][:40]}: {report['score']}% ({report['match_rate']})")


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Match profiles to postings via embedding similarity'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # match command
    match_parser = subparsers.add_parser('match', help='Match profile to posting')
    match_parser.add_argument('profile_id', type=int, help='Profile ID')
    match_parser.add_argument('posting_id', type=int, help='Posting ID')
    
    # profile command
    profile_parser = subparsers.add_parser('profile', help='Match profile to all postings')
    profile_parser.add_argument('profile_id', type=int, help='Profile ID')
    profile_parser.add_argument('--limit', type=int, default=50, help='Max postings to check')
    profile_parser.add_argument('-v', '--verbose', action='store_true', help='Show top match details')
    profile_parser.add_argument('--show-gated', action='store_true', help='Show postings excluded by domain gates')
    
    # posting command
    posting_parser = subparsers.add_parser('posting', help='Match posting to all profiles')
    posting_parser.add_argument('posting_id', type=int, help='Posting ID')
    posting_parser.add_argument('-v', '--verbose', action='store_true', help='Show top match details')
    
    # demo command
    demo_parser = subparsers.add_parser('demo', help='Demo with real data')
    
    args = parser.parse_args()
    
    if args.command == 'match':
        cmd_match(args)
    elif args.command == 'profile':
        cmd_profile(args)
    elif args.command == 'posting':
        cmd_posting(args)
    elif args.command == 'demo':
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
