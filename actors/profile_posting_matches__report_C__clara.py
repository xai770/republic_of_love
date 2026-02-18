#!/usr/bin/env python3
"""
Profile-Posting Match Report Generator — Clara

PURPOSE:
Given a profile and posting, Clara:
1. Checks domain + qualification gates (cheap, no LLM)
2. Computes embedding similarity (profile text vs posting text)
3. Analyzes match via LLM — makes apply/skip recommendation
4. Generates a cover letter (apply) or no-go narrative (skip)

Input:  profile_id + posting_id (via work_query or CLI)
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
Rewritten: 2026-02-18 (fixed broken import, added work history context,
           real embedding matching, restructured prompt)
"""

import sys
import json
import os
import re
import hashlib
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
import requests

from core.database import get_connection
from core.logging_config import get_logger
from config.settings import OLLAMA_GENERATE_URL, OLLAMA_EMBED_URL, EMBED_MODEL

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
MODEL = "qwen2.5:7b"
FALLBACK_MODEL = "gemma3:4b"
MATCH_THRESHOLD = 0.70
PARTIAL_THRESHOLD = 0.55

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
EXPERIENCE_TO_KLDB = {
    'executive': 4, 'senior': 4, 'expert': 4,
    'specialist': 3, 'lead': 3,
    'mid': 2, 'fachkraft': 2,
    'junior': 2, 'entry': 1, 'helfer': 1,
    None: None,
}


# ============================================================================
# EMBEDDING HELPERS
# ============================================================================

def get_embedding(text: str) -> Optional[np.ndarray]:
    """Get embedding vector from Ollama (bge-m3)."""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            emb = np.array(resp.json()['embedding'])
            if np.any(np.isnan(emb)):
                return None
            return emb
    except Exception as e:
        logger.error("Embedding error: %s", e)
    return None


def get_cached_embedding(conn, text: str) -> Optional[np.ndarray]:
    """Get embedding from DB cache, or compute and cache it."""
    text_clean = text.strip().lower()
    text_hash = hashlib.sha256(text_clean.encode()).hexdigest()[:32]

    cur = conn.cursor()
    cur.execute("SELECT embedding FROM embeddings WHERE text_hash = %s", (text_hash,))
    row = cur.fetchone()
    if row:
        return np.array(row['embedding'])

    emb = get_embedding(text_clean)
    if emb is not None:
        cur.execute("""
            INSERT INTO embeddings (text_hash, text, embedding, model)
            VALUES (%s, %s, %s, %s) ON CONFLICT (text_hash) DO NOTHING
        """, (text_hash, text_clean[:2000], json.dumps(emb.tolist()), EMBED_MODEL))
        conn.commit()
    return emb


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ============================================================================
# DATA LOADING
# ============================================================================
def get_profile_data(conn, profile_id: int) -> Optional[Dict]:
    """Load profile with skills, work history, and technologies."""
    cur = conn.cursor()

    # Basic info — use yogi_name for anonymity (never expose real name)
    cur.execute("""
        SELECT p.profile_id, COALESCE(u.yogi_name, 'Yogi') AS display_name,
               p.current_title, p.skill_keywords, p.experience_level,
               p.profile_summary, p.years_of_experience
        FROM profiles p
        LEFT JOIN users u ON p.user_id = u.user_id
        WHERE p.profile_id = %s
    """, (profile_id,))
    row = cur.fetchone()
    if not row:
        return None

    profile = {
        'profile_id': row['profile_id'],
        'name': row['display_name'],
        'title': row['current_title'],
        'skills': [],
        'experience_level': row['experience_level'],
        'qualification_level': EXPERIENCE_TO_KLDB.get(row['experience_level']),
        'years_of_experience': row['years_of_experience'],
        'profile_summary': row['profile_summary'] or '',
        'work_history': [],
    }

    # Skills from profiles.skill_keywords
    skills = row['skill_keywords'] or []
    if isinstance(skills, str):
        skills = json.loads(skills)
    for s in skills:
        if isinstance(s, str):
            profile['skills'].append(s)
        elif isinstance(s, dict) and 'skill' in s:
            profile['skills'].append(s['skill'])
    profile['skills'] = list(set(profile['skills']))

    # Work history with technologies
    cur.execute("""
        SELECT company_name, job_title, start_date, end_date, is_current,
               duration_months, job_description, technologies_used
        FROM profile_work_history
        WHERE profile_id = %s
        ORDER BY COALESCE(end_date, '2099-01-01') DESC, start_date DESC
    """, (profile_id,))
    for wh in cur.fetchall():
        entry = {
            'company': wh['company_name'] or '',
            'title': wh['job_title'] or '',
            'description': wh['job_description'] or '',
            'technologies': wh['technologies_used'] or [],
        }
        if wh.get('start_date'):
            entry['start'] = wh['start_date'].strftime('%Y')
        if wh.get('end_date'):
            entry['end'] = wh['end_date'].strftime('%Y')
        elif wh.get('is_current'):
            entry['end'] = 'present'
        elif wh.get('duration_months'):
            entry['duration_years'] = round(wh['duration_months'] / 12, 1)
        profile['work_history'].append(entry)

    return profile


def get_posting_data(conn, posting_id: int) -> Optional[Dict]:
    """Load posting with summary and description for LLM context."""
    cur = conn.cursor()

    cur.execute("""
        SELECT posting_id, job_title, source, extracted_summary,
               job_description, qualification_level, location_city,
               berufenet_name
        FROM postings WHERE posting_id = %s
    """, (posting_id,))
    row = cur.fetchone()
    if not row:
        return None

    posting = {
        'posting_id': row['posting_id'],
        'title': row['job_title'],
        'company': row['source'] or 'Unknown',
        'location': row['location_city'] or '',
        'qualification_level': row['qualification_level'],
        'berufenet_name': row['berufenet_name'] or '',
        'summary': row['extracted_summary'] or '',
        'description': row['job_description'] or '',
    }

    # Build match_text — same format as embeddings pipeline uses
    if posting['summary']:
        posting['match_text'] = posting['summary']
    elif posting['description']:
        posting['match_text'] = f"job title: {posting['title']} " + posting['description'][:2000]
    else:
        posting['match_text'] = posting['title']

    return posting


def build_profile_text(profile: Dict) -> str:
    """Build a text representation of the profile for embedding comparison."""
    parts = []
    if profile['title']:
        parts.append(f"current role: {profile['title']}")
    if profile['skills']:
        parts.append(f"skills: {', '.join(profile['skills'][:20])}")
    for wh in profile['work_history'][:5]:
        parts.append(f"worked as {wh['title']} at {wh['company']}")
        if wh.get('technologies'):
            parts.append(f"using {', '.join(wh['technologies'][:5])}")
    return ' '.join(parts)


# ============================================================================
# DOMAIN GATES
# ============================================================================
def detect_posting_domain(posting: Dict) -> Optional[str]:
    """Detect if posting belongs to a restricted domain."""
    title = posting.get('title', '').lower()
    summary = posting.get('summary', '').lower()

    for domain, config in RESTRICTED_DOMAINS.items():
        for kw in config['title_keywords']:
            if kw in title:
                return domain
        for kw in config['skill_keywords']:
            if kw in summary:
                return domain

    return None


def check_domain_gate(profile: Dict, posting: Dict) -> Tuple[bool, str]:
    """Check if profile can pass the domain gate."""
    posting_domain = detect_posting_domain(posting)

    if not posting_domain:
        return True, "No restricted domain"

    # Check if profile skills mention the required domain
    profile_text = ' '.join(profile.get('skills', [])).lower()
    profile_text += ' ' + (profile.get('title') or '').lower()
    required_domains = RESTRICTED_DOMAINS[posting_domain]['required_domains']

    for req_domain in required_domains:
        if req_domain in profile_text:
            return True, f"Profile has {posting_domain} domain experience"

    return False, f"Posting requires {posting_domain} domain experience"


def check_qualification_gate(profile: Dict, posting: Dict) -> Tuple[bool, str]:
    """Check if posting's qualification level is appropriate for the profile.

    Berufenet KLDB constraint: never match a skilled worker to unskilled jobs.
    """
    profile_level = profile.get('qualification_level')
    posting_level = posting.get('qualification_level')

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
def compute_similarity(conn, profile: Dict, posting: Dict) -> Dict:
    """Compute embedding similarity between profile text and posting text.

    Uses whole-document comparison: profile skills+history vs posting summary.
    Returns a similarity score and skill overlap analysis.
    """
    # Build profile text for embedding
    profile_text = build_profile_text(profile)
    posting_text = posting.get('match_text', posting.get('title', ''))

    if not profile_text or not posting_text:
        return {'score': 0.0, 'method': 'none', 'skill_overlap': []}

    # Get embeddings (cached)
    profile_emb = get_cached_embedding(conn, profile_text)
    posting_emb = get_cached_embedding(conn, posting_text)

    if profile_emb is None or posting_emb is None:
        return {'score': 0.0, 'method': 'embedding_failed', 'skill_overlap': []}

    score = cosine_similarity(profile_emb, posting_emb)

    # Also compute simple keyword overlap for the LLM context
    posting_lower = posting_text.lower()
    skill_overlap = []
    for skill in profile.get('skills', []):
        if skill.lower() in posting_lower:
            skill_overlap.append(skill)

    return {
        'score': round(score, 3),
        'method': 'bge-m3',
        'skill_overlap': skill_overlap,
    }


# ============================================================================
# LLM GENERATION
# ============================================================================
def build_prompt(profile: Dict, posting: Dict, match_data: Dict) -> str:
    """Build a rich prompt with full profile context and posting summary."""

    # --- candidate section ---
    work_history_lines = []
    for wh in profile.get('work_history', [])[:8]:
        dates = ""
        if wh.get('start_date'):
            dates = f" ({wh['start_date']}–{wh.get('end_date') or 'present'})"
        techs = ""
        if wh.get('technologies'):
            techs = f"  Technologies: {', '.join(wh['technologies'][:10])}"
        work_history_lines.append(
            f"- {wh.get('job_title', 'Unknown role')} at {wh.get('company_name', 'Unknown')}{dates}\n"
            f"  {(wh.get('job_description') or '')[:120]}\n{techs}"
        )

    candidate_block = f"""Name: {profile['name']}
Title: {profile.get('title') or 'Not specified'}
Skills: {', '.join(profile.get('skills', [])[:20])}
Years of experience: {profile.get('years_of_experience') or 'unknown'}
Profile summary: {(profile.get('summary') or 'No summary')[:300]}

Work history:
{chr(10).join(work_history_lines) if work_history_lines else 'No work history available'}"""

    # --- posting section ---
    posting_summary = posting.get('summary') or ''
    posting_desc = posting.get('job_description') or ''
    # Prefer extracted_summary (structured), fall back to raw description
    posting_text = posting_summary[:1500] if posting_summary else posting_desc[:1500]

    posting_block = f"""Title: {posting.get('title', 'Unknown')}
Company: {posting.get('company', 'Unknown')}
Location: {posting.get('location_city') or 'Not specified'}
Berufenet category: {posting.get('berufenet_name') or 'Unknown'}

{posting_text}"""

    # --- match analysis ---
    skill_overlap = match_data.get('skill_overlap', [])
    overlap_str = ', '.join(skill_overlap) if skill_overlap else 'none found'

    prompt = f"""You are Clara, a career advisor analyzing whether a candidate should apply for a job.

=== CANDIDATE ===
{candidate_block}

=== JOB POSTING ===
{posting_block}

=== MATCH ANALYSIS ===
Embedding similarity score: {match_data.get('score', 0.0)} (0-1 scale, >0.7 = strong match)
Skill keyword overlap: {overlap_str}

=== YOUR TASK ===
1. Analyze the match between candidate and posting.
2. Decide: should this candidate APPLY or SKIP?
3. List 3-5 GO reasons (why they should apply — be specific about matching skills/experience).
4. List 1-3 NO-GO reasons (gaps, missing requirements, or concerns).
5. Based on your recommendation:
   - If APPLY: Write a professional cover letter (3 paragraphs, ~200 words) that references specific skills and experience from the candidate profile. Set nogo_narrative to null.
   - If SKIP: Write a brief no-go explanation (1-2 sentences). Set cover_letter to null.

OUTPUT FORMAT (valid JSON only, no other text):
{{
  "recommendation": "apply" or "skip",
  "confidence": 0.0-1.0,
  "go_reasons": ["reason1", "reason2", ...],
  "nogo_reasons": ["reason1", "reason2", ...],
  "cover_letter": "Dear Hiring Manager, ..." or null,
  "nogo_narrative": "This posting requires..." or null
}}

RULES:
- Only reference facts from the candidate profile and job posting above.
- If recommendation="apply", cover_letter MUST NOT be null.
- If recommendation="skip", nogo_narrative MUST NOT be null.
- Output ONLY valid JSON."""

    return prompt


def call_llm(prompt: str) -> Dict:
    """Call the LLM with cascading fallback and parse JSON response."""
    models = [MODEL, FALLBACK_MODEL]

    for model in models:
        try:
            resp = requests.post(
                OLLAMA_GENERATE_URL,
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0, 'seed': 42},
                },
                timeout=180,
            )
            resp.raise_for_status()
            response = resp.json().get('response', '').strip()

            # Extract JSON from markdown fences if present
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]

            data = json.loads(response)
            data['_model_used'] = model
            return data

        except json.JSONDecodeError as e:
            logger.warning("JSON parse error with %s: %s — response: %.200s", model, e, response)
            if model == models[-1]:
                return {
                    'recommendation': 'skip',
                    'confidence': 0.0,
                    'go_reasons': [],
                    'nogo_reasons': [f'LLM parse error ({model}): {str(e)}'],
                    'cover_letter': None,
                    'nogo_narrative': f'Error parsing LLM response: {response[:200]}',
                }
        except Exception as e:
            logger.warning("LLM call failed with %s: %s", model, e)
            if model == models[-1]:
                return {
                    'recommendation': 'skip',
                    'confidence': 0.0,
                    'go_reasons': [],
                    'nogo_reasons': [f'LLM error: {str(e)}'],
                    'cover_letter': None,
                    'nogo_narrative': f'Error calling LLM: {str(e)}',
                }

    # Should not reach here, but safety net
    return {
        'recommendation': 'skip',
        'confidence': 0.0,
        'go_reasons': [],
        'nogo_reasons': ['All LLM models failed'],
        'cover_letter': None,
        'nogo_narrative': 'All LLM models failed',
    }


# ============================================================================
# MAIN PROCESS
# ============================================================================
def _store_gated_result(conn, profile_id: int, posting_id: int,
                        gate_reason: str) -> int:
    """Store a gate-failed result (no LLM call needed)."""
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
        0.0, 'skip', f'Gate failed: {gate_reason}', 'gate_only'
    ))
    match_id = cur.fetchone()['match_id']
    conn.commit()
    return match_id


def process_match(conn, profile_id: int, posting_id: int) -> Dict:
    """Process a single profile-posting match end-to-end."""

    # Load data
    profile = get_profile_data(conn, profile_id)
    if not profile:
        return {'success': False, 'error': f'Profile {profile_id} not found'}

    posting = get_posting_data(conn, posting_id)
    if not posting:
        return {'success': False, 'error': f'Posting {posting_id} not found'}

    # --- Domain gate ---
    gate_passed, gate_reason = check_domain_gate(profile, posting)
    if not gate_passed:
        match_id = _store_gated_result(conn, profile_id, posting_id, gate_reason)
        return {'success': True, 'match_id': match_id, 'gated': True,
                'gate_reason': gate_reason}

    # --- Qualification gate ---
    qual_passed, qual_reason = check_qualification_gate(profile, posting)
    if not qual_passed:
        match_id = _store_gated_result(conn, profile_id, posting_id, qual_reason)
        return {'success': True, 'match_id': match_id, 'gated': True,
                'gate_reason': qual_reason}

    # --- Embedding similarity ---
    match_data = compute_similarity(conn, profile, posting)

    # --- LLM analysis ---
    prompt = build_prompt(profile, posting, match_data)
    llm_result = call_llm(prompt)

    # --- Store result ---
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
        match_data['score'],
        f"{len(match_data.get('skill_overlap', []))} keyword overlaps",
        llm_result.get('recommendation', 'skip'),
        llm_result.get('confidence', 0.0),
        json.dumps(llm_result.get('go_reasons', [])),
        json.dumps(llm_result.get('nogo_reasons', [])),
        llm_result.get('cover_letter'),
        llm_result.get('nogo_narrative'),
        llm_result.get('_model_used', MODEL),
        json.dumps({
            'embedding_score': match_data['score'],
            'method': match_data['method'],
            'skill_overlap': match_data['skill_overlap'],
        }),
    ))
    match_id = cur.fetchone()['match_id']
    conn.commit()

    return {
        'success': True,
        'match_id': match_id,
        'recommendation': llm_result.get('recommendation'),
        'confidence': llm_result.get('confidence'),
        'score': match_data['score'],
        'skill_overlap': match_data.get('skill_overlap', []),
    }


# ============================================================================
# CLI
# ============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Clara — generate match report for profile↔posting pair')
    parser.add_argument('profile_id', type=int, help='Profile ID')
    parser.add_argument('posting_id', type=int, help='Posting ID')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show details')

    args = parser.parse_args()

    with get_connection() as conn:
        logger.info("Analyzing match: Profile %s ↔ Posting %s",
                     args.profile_id, args.posting_id)

        result = process_match(conn, args.profile_id, args.posting_id)

        if not result['success']:
            logger.error("%s", result.get('error', 'Unknown error'))
            return 1

        if result.get('gated'):
            logger.info("GATED: %s", result['gate_reason'])
            return 0

        logger.info("Match ID: %s", result['match_id'])
        logger.info("Embedding score: %.3f", result['score'])
        logger.info("Recommendation: %s (confidence: %.2f)",
                     result['recommendation'].upper(),
                     result.get('confidence', 0))
        logger.info("Skill overlap: %s",
                     ', '.join(result.get('skill_overlap', [])) or 'none')

        if args.verbose:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM profile_posting_matches WHERE match_id = %s
            """, (result['match_id'],))
            row = cur.fetchone()

            go_reasons = row['go_reasons'] or []
            if isinstance(go_reasons, str):
                go_reasons = json.loads(go_reasons)
            logger.info("GO REASONS:")
            for r in go_reasons:
                logger.info("  + %s", r)

            nogo_reasons = row['nogo_reasons'] or []
            if isinstance(nogo_reasons, str):
                nogo_reasons = json.loads(nogo_reasons)
            logger.info("NO-GO REASONS:")
            for r in nogo_reasons:
                logger.warning("  - %s", r)

            if row['cover_letter']:
                logger.info("=" * 60)
                logger.info("COVER LETTER:\n%s", row['cover_letter'])

            if row['nogo_narrative']:
                logger.info("=" * 60)
                logger.info("NO-GO NARRATIVE:\n%s", row['nogo_narrative'])

    return 0


if __name__ == '__main__':
    sys.exit(main())
