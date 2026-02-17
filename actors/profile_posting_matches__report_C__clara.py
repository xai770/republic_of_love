#!/usr/bin/env python3
"""
Profile-Posting Match Report Generator - Clara analyzes matches and generates recommendations

PURPOSE:
Given a profile and posting, Clara:
1. Reviews the embedding match scores
2. Analyzes go/no-go reasons based on CPS facets
3. Makes a recommendation (apply/skip)
4. Generates the appropriate artifact (cover letter or no-go narrative)

Input:  profile_id + posting_id (via work_query)
Output: profile_posting_matches row with analysis + recommendation + letter/narrative

WORK_QUERY:
    SELECT p.profile_id, po.posting_id
    FROM profiles p
    CROSS JOIN postings po
    WHERE po.posting_status = 'active'
      AND NOT EXISTS (
        SELECT 1 FROM profile_posting_matches m
        WHERE m.profile_id = p.profile_id 
          AND m.posting_id = po.posting_id
      )
    LIMIT 100

Author: Arden
Date: 2026-01-21
Task Type ID: TBD
"""

import sys
import json
import os
import re
from typing import Dict, Any, Optional, List, Tuple

import requests

from core.database import get_connection

from core.logging_config import get_logger
logger = get_logger(__name__)

from tools.skill_embeddings import get_embedding, cosine_similarity

# ============================================================================
# CONFIGURATION
# ============================================================================
MODEL = "qwen2.5:7b"
MATCH_THRESHOLD = 0.70
PARTIAL_THRESHOLD = 0.60

# Domain gates (from profile_matcher.py)
RESTRICTED_DOMAINS = {
    'legal': {
        'title_keywords': ['legal counsel', 'attorney', 'lawyer', 'paralegal', 'solicitor', 'barrister'],
        'skill_keywords': ['legal knowledge', 'legal drafting', 'litigation', 'jurisprudence', 'contract law'],
        'required_domains': ['legal', 'law'],
    },
    'medical': {
        'title_keywords': ['doctor', 'physician', 'surgeon', 'registered nurse', 'clinical director'],
        'skill_keywords': ['medical diagnosis', 'clinical practice', 'patient care', 'surgery'],
        'required_domains': ['medical', 'healthcare', 'clinical'],
    },
    'accounting_cpa': {
        'title_keywords': ['certified public accountant', 'cpa ', 'chartered accountant', 'tax accountant'],
        'skill_keywords': ['cpa certification', 'chartered accountant', 'tax return preparation'],
        'required_domains': ['accounting', 'tax'],
    },
}

# Berufenet KLDB Qualification Levels
# 1 = Helfer (no training), 2 = Fachkraft (vocational), 3 = Spezialist (advanced), 4 = Experte (degree)
# Constraint: Never match a yogi at level N to jobs at level < N (without consent)
EXPERIENCE_TO_KLDB = {
    'executive': 4,
    'senior': 4,
    'expert': 4,
    'specialist': 3,
    'mid': 2,
    'fachkraft': 2,
    'junior': 2,
    'entry': 1,
    'helfer': 1,
    None: None,  # unknown = no constraint
}


# ============================================================================
# DATA LOADING
# ============================================================================
def get_profile_data(conn, profile_id: int) -> Optional[Dict]:
    """Load profile with skills from profiles.skill_keywords."""
    cur = conn.cursor()
    
    # Basic info with skills + experience level for qualification gate
    cur.execute("""
        SELECT profile_id, full_name, current_title, skill_keywords, experience_level
        FROM profiles WHERE profile_id = %s
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
        'track_records': [],  # Deprecated: was from profile_facets
        'experience_years': 0,  # Could derive from profile later
        'seniority': None,  # Could derive from title later
        'experience_level': row['experience_level'],
        'qualification_level': EXPERIENCE_TO_KLDB.get(row['experience_level']),
    }
    
    # Get skills from profiles.skill_keywords
    skills = row['skill_keywords'] or []
    if isinstance(skills, str):
        import json
        skills = json.loads(skills)
    
    for s in skills:
        if isinstance(s, str):
            profile['skills'].append(s)
        elif isinstance(s, dict) and 'skill' in s:
            profile['skills'].append(s['skill'])
    
    profile['skills'] = list(set(profile['skills']))  # dedupe
    
    return profile


def get_posting_data(conn, posting_id: int) -> Optional[Dict]:
    """Load posting with facets for LLM context."""
    cur = conn.cursor()
    
    # Basic info
    cur.execute("""
        SELECT posting_id, job_title, source, extracted_summary, qualification_level
        FROM postings WHERE posting_id = %s
    """, (posting_id,))
    row = cur.fetchone()
    if not row:
        return None
    
    posting = {
        'posting_id': row['posting_id'],
        'title': row['job_title'],
        'company': row['source'] or 'Unknown',
        'summary': row['extracted_summary'],
        'requirements': [],  # Embeddings handle skill matching, no facets needed
        'qualification_level': row['qualification_level'],
    }
    
    return posting


# ============================================================================
# DOMAIN GATES
# ============================================================================
def detect_posting_domain(posting: Dict) -> Optional[str]:
    """Detect if posting belongs to a restricted domain."""
    title = posting.get('title', '').lower()
    
    for domain, config in RESTRICTED_DOMAINS.items():
        for kw in config['title_keywords']:
            if kw in title:
                return domain
        
        critical_skills = [
            r['skill'].lower() for r in posting.get('requirements', [])
            if r.get('importance') in ('critical', 'required')
        ]
        for kw in config['skill_keywords']:
            if any(kw in skill for skill in critical_skills):
                return domain
    
    return None


def check_domain_gate(profile: Dict, posting: Dict) -> Tuple[bool, str]:
    """Check if profile can pass the domain gate."""
    posting_domain = detect_posting_domain(posting)
    
    if not posting_domain:
        return True, "No restricted domain"
    
    profile_domains = [d.lower() for d in profile.get('domains', [])]
    required_domains = RESTRICTED_DOMAINS[posting_domain]['required_domains']
    
    for req_domain in required_domains:
        if any(req_domain in pd for pd in profile_domains):
            return True, f"Profile has {posting_domain} domain experience"
    
    return False, f"Posting requires {posting_domain} domain experience"


def check_qualification_gate(profile: Dict, posting: Dict) -> Tuple[bool, str]:
    """Check if posting's qualification level is appropriate for the profile.
    
    Berufenet KLDB constraint: never match a skilled worker to unskilled jobs.
    A yogi at level 4 (Experte) should not see level 1 (Helfer) jobs.
    
    Returns (passed, reason).
    """
    profile_level = profile.get('qualification_level')
    posting_level = posting.get('qualification_level')
    
    # If either is unknown, skip the gate
    if profile_level is None or posting_level is None:
        return True, "Qualification level unknown — gate skipped"
    
    if posting_level < profile_level:
        level_names = {1: 'Helfer', 2: 'Fachkraft', 3: 'Spezialist', 4: 'Experte'}
        profile_name = level_names.get(profile_level, str(profile_level))
        posting_name = level_names.get(posting_level, str(posting_level))
        return False, f"Qualification mismatch: yogi is {profile_name} (level {profile_level}), posting requires only {posting_name} (level {posting_level})"
    
    return True, "Qualification level appropriate"


# ============================================================================
# EMBEDDING MATCHING
# ============================================================================
def compute_skill_matches(profile: Dict, posting: Dict) -> Dict:
    """Compute embedding-based skill matches with full similarity matrix."""
    profile_skills = profile.get('skills', [])
    requirements = posting.get('requirements', [])
    
    if not profile_skills or not requirements:
        return {
            'matches': [],
            'partial_matches': [],
            'gaps': [],
            'score': 0.0,
            'match_rate': '0/0',
            'matrix': None
        }
    
    # Pre-compute profile embeddings (limit to top 20 for matrix size)
    profile_skills_limited = profile_skills[:20]
    profile_embs = []
    for skill in profile_skills_limited:
        emb = get_embedding(skill)
        if emb is not None:
            profile_embs.append((skill, emb))
    
    # Pre-compute requirement embeddings (limit to top 15)
    requirements_limited = requirements[:15]
    req_embs = []
    for req in requirements_limited:
        emb = get_embedding(req['skill'])
        if emb is not None:
            req_embs.append((req['skill'], emb, req.get('weight', 70), req.get('importance', 'required')))
    
    # Build full similarity matrix
    matrix = {
        'profile_skills': [s for s, _ in profile_embs],
        'requirements': [r for r, _, _, _ in req_embs],
        'scores': []  # rows = requirements, cols = profile skills
    }
    
    for req_skill, req_emb, _, _ in req_embs:
        row = []
        for skill_name, skill_emb in profile_embs:
            score = cosine_similarity(req_emb, skill_emb)
            row.append(round(score, 2))
        matrix['scores'].append(row)
    
    # Now compute matches (using all requirements, not just limited)
    matches = []
    partial_matches = []
    gaps = []
    matched_count = 0
    total_weight = 0
    weighted_score = 0
    
    for req in requirements:
        req_skill = req['skill']
        req_weight = req.get('weight', 70)
        total_weight += req_weight
        
        req_emb = get_embedding(req_skill)
        if req_emb is None:
            continue
        
        # Find best match from ALL profile skills
        best_score = 0.0
        best_skill = None
        for skill in profile_skills:
            skill_emb = get_embedding(skill)
            if skill_emb is not None:
                score = cosine_similarity(req_emb, skill_emb)
                if score > best_score:
                    best_score = score
                    best_skill = skill
        
        match_info = {
            'posting_skill': req_skill,
            'profile_skill': best_skill,
            'score': round(best_score, 2),
            'importance': req.get('importance', 'required'),
        }
        
        if best_score >= MATCH_THRESHOLD:
            matches.append(match_info)
            matched_count += 1
            weighted_score += req_weight * best_score
        elif best_score >= PARTIAL_THRESHOLD:
            partial_matches.append(match_info)
            weighted_score += req_weight * best_score * 0.5
        else:
            gaps.append(match_info)
    
    overall_score = 0.0
    if total_weight > 0:
        overall_score = round(weighted_score / total_weight, 3)
    
    return {
        'matches': matches,
        'partial_matches': partial_matches,
        'gaps': gaps,
        'score': overall_score,
        'match_rate': f"{matched_count}/{len(requirements)}",
        'matrix': matrix
    }


# ============================================================================
# LLM GENERATION
# ============================================================================
def build_prompt(profile: Dict, posting: Dict, match_data: Dict) -> str:
    """Build the prompt for Clara."""
    
    # Build JSON context
    context = {
        "candidate_profile": {
            "name": profile['name'],
            "current_title": profile['title'],
            "skills": profile['skills'][:15],  # Top 15
            "experience_years": profile['experience_years'],
            "domains": profile['domains'],
            "seniority": profile['seniority'],
            "track_records": profile['track_records'][:3],  # Top 3
        },
        "job_posting": {
            "title": posting['title'],
            "company": posting['company'],
            "requirements": [
                {"skill": r['skill'], "importance": r['importance']}
                for r in posting['requirements'][:10]  # Top 10
            ],
        },
        "match_analysis": {
            "overall_score": match_data['score'],
            "match_rate": match_data['match_rate'],
            "strong_matches": [
                {"profile": m['profile_skill'], "posting": m['posting_skill'], "score": m['score']}
                for m in match_data['matches'][:5]
            ],
            "partial_matches": [
                {"profile": m['profile_skill'], "posting": m['posting_skill'], "score": m['score']}
                for m in match_data['partial_matches'][:3]
            ],
            "gaps": [
                {"posting": m['posting_skill'], "best_profile_match": m['profile_skill'], "score": m['score']}
                for m in match_data['gaps'][:5]
            ],
        }
    }
    
    prompt = f"""You are a career advisor analyzing a job match for a candidate.

INPUT DATA (use ONLY this data, do not make up facts):
{json.dumps(context, indent=2)}

YOUR TASK:
1. Analyze the match and decide: should this candidate APPLY or SKIP?
2. List 3-5 GO reasons (why they should apply)
3. List 3-5 NO-GO reasons (concerns or gaps)
4. Based on your recommendation:
   - If APPLY: You MUST write a professional cover letter (3 paragraphs, ~200 words). Set nogo_narrative to null.
   - If SKIP: You MUST write a no-go narrative (1-2 sentences explaining why). Set cover_letter to null.

OUTPUT FORMAT (JSON only, no other text):
{{
  "recommendation": "apply" or "skip",
  "confidence": 0.0-1.0,
  "go_reasons": ["reason1", "reason2", ...],
  "nogo_reasons": ["reason1", "reason2", ...],
  "cover_letter": "Dear Hiring Manager, ..." (REQUIRED if apply) or null (if skip),
  "nogo_narrative": "After reviewing..." (REQUIRED if skip) or null (if apply)
}}

CRITICAL RULES:
- If recommendation="apply", cover_letter MUST be a real letter (not null)
- If recommendation="skip", nogo_narrative MUST be a real explanation (not null)
- Only reference facts from the INPUT DATA
- Cover letter should mention specific skills and track records from the profile
- Be concise and professional
- Output ONLY valid JSON, no markdown or explanation"""
    
    return prompt


from config.settings import OLLAMA_GENERATE_URL as OLLAMA_GENERATE_URL


def call_llm(prompt: str) -> Dict:
    """Call the LLM and parse response."""
    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': MODEL, 'prompt': prompt, 'stream': False,
                  'options': {'temperature': 0, 'seed': 42}},
            timeout=120,
        )
        resp.raise_for_status()
        response = resp.json().get('response', '').strip()
        
        # Try to extract JSON from response
        # Sometimes model wraps in markdown
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        
        # Parse JSON
        data = json.loads(response)
        return data
        
    except json.JSONDecodeError as e:
        return {
            'recommendation': 'skip',
            'confidence': 0.0,
            'go_reasons': [],
            'nogo_reasons': [f'LLM parse error: {str(e)}'],
            'cover_letter': None,
            'nogo_narrative': f'Error parsing LLM response: {response[:200]}',
        }
    except Exception as e:
        return {
            'recommendation': 'skip',
            'confidence': 0.0,
            'go_reasons': [],
            'nogo_reasons': [f'LLM error: {str(e)}'],
            'cover_letter': None,
            'nogo_narrative': f'Error calling LLM: {str(e)}',
        }


# ============================================================================
# MAIN PROCESS
# ============================================================================
def process_match(conn, profile_id: int, posting_id: int) -> Dict:
    """Process a single profile-posting match."""
    
    # Load data
    profile = get_profile_data(conn, profile_id)
    if not profile:
        return {'success': False, 'error': f'Profile {profile_id} not found'}
    
    posting = get_posting_data(conn, posting_id)
    if not posting:
        return {'success': False, 'error': f'Posting {posting_id} not found'}
    
    # Check domain gate
    gate_passed, gate_reason = check_domain_gate(profile, posting)
    
    if not gate_passed:
        # Store gated result without LLM call
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO profile_posting_matches 
            (profile_id, posting_id, domain_gate_passed, gate_reason,
             skill_match_score, recommendation, nogo_narrative, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, posting_id) DO UPDATE SET
                domain_gate_passed = EXCLUDED.domain_gate_passed,
                gate_reason = EXCLUDED.gate_reason,
                skill_match_score = EXCLUDED.skill_match_score,
                recommendation = EXCLUDED.recommendation,
                nogo_narrative = EXCLUDED.nogo_narrative,
                computed_at = NOW()
            RETURNING match_id
        """, (
            profile_id, posting_id, False, gate_reason,
            0.0, 'skip', f'Domain gate failed: {gate_reason}', 'gate_only'
        ))
        match_id = cur.fetchone()['match_id']
        conn.commit()
        
        return {
            'success': True,
            'match_id': match_id,
            'gated': True,
            'gate_reason': gate_reason,
        }
    
    # Check qualification gate (Berufenet KLDB constraint)
    qual_passed, qual_reason = check_qualification_gate(profile, posting)
    
    if not qual_passed:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO profile_posting_matches 
            (profile_id, posting_id, domain_gate_passed, gate_reason,
             skill_match_score, recommendation, nogo_narrative, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, posting_id) DO UPDATE SET
                domain_gate_passed = EXCLUDED.domain_gate_passed,
                gate_reason = EXCLUDED.gate_reason,
                skill_match_score = EXCLUDED.skill_match_score,
                recommendation = EXCLUDED.recommendation,
                nogo_narrative = EXCLUDED.nogo_narrative,
                computed_at = NOW()
            RETURNING match_id
        """, (
            profile_id, posting_id, False, qual_reason,
            0.0, 'skip', f'Qualification gate failed: {qual_reason}', 'gate_only'
        ))
        match_id = cur.fetchone()['match_id']
        conn.commit()
        
        return {
            'success': True,
            'match_id': match_id,
            'gated': True,
            'gate_reason': qual_reason,
        }
    
    # Compute embedding matches
    match_data = compute_skill_matches(profile, posting)
    
    # Build prompt and call LLM
    prompt = build_prompt(profile, posting, match_data)
    llm_result = call_llm(prompt)
    
    # Store result
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO profile_posting_matches 
        (profile_id, posting_id, domain_gate_passed, gate_reason,
         skill_match_score, match_rate, recommendation, confidence,
         go_reasons, nogo_reasons, cover_letter, nogo_narrative, model_version,
         similarity_matrix)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (profile_id, posting_id) DO UPDATE SET
            domain_gate_passed = EXCLUDED.domain_gate_passed,
            skill_match_score = EXCLUDED.skill_match_score,
            match_rate = EXCLUDED.match_rate,
            recommendation = EXCLUDED.recommendation,
            confidence = EXCLUDED.confidence,
            go_reasons = EXCLUDED.go_reasons,
            nogo_reasons = EXCLUDED.nogo_reasons,
            cover_letter = EXCLUDED.cover_letter,
            nogo_narrative = EXCLUDED.nogo_narrative,
            similarity_matrix = EXCLUDED.similarity_matrix,
            computed_at = NOW()
        RETURNING match_id
    """, (
        profile_id, posting_id, True, gate_reason,
        match_data['score'], match_data['match_rate'],
        llm_result.get('recommendation', 'skip'),
        llm_result.get('confidence', 0.0),
        json.dumps(llm_result.get('go_reasons', [])),
        json.dumps(llm_result.get('nogo_reasons', [])),
        llm_result.get('cover_letter'),
        llm_result.get('nogo_narrative'),
        MODEL,
        json.dumps(match_data.get('matrix'))
    ))
    match_id = cur.fetchone()['match_id']
    conn.commit()
    
    return {
        'success': True,
        'match_id': match_id,
        'recommendation': llm_result.get('recommendation'),
        'score': match_data['score'],
        'match_rate': match_data['match_rate'],
        'matrix': match_data.get('matrix'),
    }


# ============================================================================
# CLI
# ============================================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate match report for profile-posting pair')
    parser.add_argument('profile_id', type=int, help='Profile ID')
    parser.add_argument('posting_id', type=int, help='Posting ID')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show details')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        logger.debug("Analyzing match: Profile %s↔ Posting %s", args.profile_id, args.posting_id)
        
        result = process_match(conn, args.profile_id, args.posting_id)
        
        if not result['success']:
            logger.error("%s", result.get('error', 'Unknown error'))
            return 1
        
        if result.get('gated'):
            logger.info("GATED: %s", result['gate_reason'])
            return 0
        
        logger.info("Match ID: %s", result['match_id'])
        logger.info("Score:%.1%(%s)", result['score'], result['match_rate'])
        logger.info("Recommendation: %s", result['recommendation'].upper())
        
        if args.verbose:
            # Fetch and display full result
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM profile_posting_matches WHERE match_id = %s
            """, (result['match_id'],))
            row = cur.fetchone()
            
            logger.info("GO REASONS:")
            go_reasons = row['go_reasons'] or []
            if isinstance(go_reasons, str):
                go_reasons = json.loads(go_reasons)
            for r in go_reasons:
                logger.info("%s", r)
            
            logger.info("NO-GO REASONS:")
            nogo_reasons = row['nogo_reasons'] or []
            if isinstance(nogo_reasons, str):
                nogo_reasons = json.loads(nogo_reasons)
            for r in nogo_reasons:
                logger.warning("%s", r)
            
            if row['cover_letter']:
                logger.info("=" * 60)
                logger.info("COVER LETTER:")
                logger.info("=" * 60)
                logger.info("%s", row['cover_letter'])
            
            if row['nogo_narrative']:
                logger.info("=" * 60)
                logger.info("NO-GO NARRATIVE:")
                logger.info("=" * 60)
                logger.info("%s", row['nogo_narrative'])
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
