#!/usr/bin/env python3
"""
Recipe 3: Match Profiles to Job Postings (Enhanced with Proficiency/Years + LLM-Guided Matching)

Weighted matching that considers:
- Skill importance (essential, critical, important, preferred)
- Proficiency levels (expert, advanced, intermediate, beginner)
- Years of experience required vs. candidate's years
- LLM-guided skill resolution (Qwen determines if skills match instead of pattern matching)

Usage:
    python3 scripts/recipe_3_matching.py --profile-id 2 --job-id TEST_ORACLE_DBA_001
    python3 scripts/recipe_3_matching.py --profile-id 2 --job-id TEST_ORACLE_DBA_001 --use-llm-matching
"""

import psycopg2
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from llm_skill_matcher import batch_match_skills, find_matching_alias

DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost'
}

def calculate_weighted_match(
    profile_skills: List,
    job_requirements: List[Dict],
    profile_name: str = "Unknown",
    use_llm_matching: bool = False,
    job_context: str = ""
) -> Dict:
    """
    Calculate weighted match score between profile and job with proficiency/years comparison
    
    Returns dict with:
    - match_percentage
    - qualified (bool)
    - breakdown by importance category
    - matched/missing skills
    - proficiency_gaps (skills where candidate has skill but insufficient proficiency/years)
    """
    
    # Build profile skill lookup with metadata
    # Format: {normalized_name: {'skill': name, 'proficiency': level, 'years_experience': num}}
    profile_skill_map = {}
    
    if profile_skills:
        for s in profile_skills:
            if isinstance(s, dict):
                skill_name = s.get('skill', '')
                normalized = skill_name.lower().replace('_', ' ').replace('-', ' ')
                profile_skill_map[normalized] = s
            else:
                # Simple string format (old style)
                normalized = s.lower().replace('_', ' ').replace('-', ' ')
                profile_skill_map[normalized] = {
                    'skill': s,
                    'proficiency': None,
                    'years_experience': None
                }
    
    profile_skill_names_normalized = set(profile_skill_map.keys())
    
    total_weight = 0
    matched_weight = 0
    
    essential_total = 0
    essential_met = 0
    critical_total = 0
    critical_met = 0
    important_total = 0
    important_met = 0
    preferred_total = 0
    preferred_met = 0
    
    matched_skills = []
    missing_essential = []
    missing_critical = []
    missing_important = []
    proficiency_gaps = []
    
    # Proficiency level scoring: expert=4, advanced=3, intermediate=2, beginner=1
    proficiency_scores = {'expert': 4, 'advanced': 3, 'intermediate': 2, 'beginner': 1}
    
    # Use LLM to resolve skill matches if requested
    llm_matches = {}
    batch_result = None
    if use_llm_matching:
        print(f"\n🤖 Using LLM-guided skill matching for {profile_name}...")
        batch_result = batch_match_skills(job_requirements, profile_skills, job_context)
        
        # Build lookup: job_skill -> matched candidate skill
        for match in batch_result['matches']:
            llm_matches[match['job_skill']] = {
                'candidate_skill': match['candidate_skill'],
                'confidence': match['confidence'],
                'proficiency': match.get('candidate_proficiency'),
                'years': match.get('candidate_years')
            }
        print(f"✅ LLM matched {len(llm_matches)}/{len(job_requirements)} skills\n")
    
    for req in job_requirements:
        weight = req.get('weight', 50)
        importance = req.get('importance', 'important')
        skill = req.get('skill', '')
        required_proficiency = req.get('proficiency', 'intermediate')
        required_years = req.get('years_required', 0)
        
        total_weight += weight
        
        # Normalize job skill name for comparison
        skill_normalized = skill.lower().replace('_', ' ').replace('-', ' ')
        
        # Find matching profile skill
        matched_profile_skill = None
        
        # Use LLM match if available
        if use_llm_matching and skill in llm_matches:
            llm_match = llm_matches[skill]
            candidate_skill_name = llm_match['candidate_skill']
            
            # Ask Qwen to find the matching alias in candidate's actual skills
            # This handles cases like "Oracle Real Application Clusters" vs "Oracle Real Application Clusters (RAC)"
            matched_profile_skill = find_matching_alias(candidate_skill_name, profile_skills)
            
            if not matched_profile_skill:
                # Fallback: create from LLM data
                if llm_match['proficiency']:
                    matched_profile_skill = {
                        'skill': candidate_skill_name,
                        'proficiency': llm_match['proficiency'],
                        'years_experience': llm_match['years']
                    }
        else:
            # Fallback to pattern matching
            # Check normalized exact match
            if skill_normalized in profile_skill_map:
                matched_profile_skill = profile_skill_map[skill_normalized]
            else:
                # Check substring matches
                for prof_norm, prof_data in profile_skill_map.items():
                    if skill_normalized in prof_norm or prof_norm in skill_normalized:
                        matched_profile_skill = prof_data
                        break
        
        if matched_profile_skill:
            # Skill found - now check proficiency and years
            candidate_proficiency = matched_profile_skill.get('proficiency', 'intermediate')
            candidate_years = matched_profile_skill.get('years_experience') or 0
            
            # Calculate proficiency match (scale 0-1)
            prof_required_score = proficiency_scores.get(required_proficiency, 2)
            prof_candidate_score = proficiency_scores.get(candidate_proficiency, 2) if candidate_proficiency else 2
            proficiency_match = min(prof_candidate_score / prof_required_score, 1.0)
            
            # Calculate years match (scale 0-1)
            years_match = 1.0
            if required_years > 0:
                years_match = min(candidate_years / required_years, 1.0) if candidate_years else 0.5
            
            # Combined skill quality score (average of proficiency and years match)
            quality_score = (proficiency_match + years_match) / 2
            
            # Award weighted points based on quality
            matched_weight += weight * quality_score
            
            # Track full vs partial matches
            if quality_score >= 0.9:
                matched_skills.append(skill)
            else:
                matched_skills.append(f"{skill} (partial: {int(quality_score*100)}%)")
                proficiency_gaps.append({
                    'skill': skill,
                    'required_proficiency': required_proficiency,
                    'candidate_proficiency': candidate_proficiency,
                    'required_years': required_years,
                    'candidate_years': candidate_years,
                    'quality_score': quality_score
                })
            
            if importance == 'essential':
                essential_met += 1
            elif importance == 'critical':
                critical_met += 1
            elif importance == 'important':
                important_met += 1
            elif importance == 'preferred':
                preferred_met += 1
        else:
            if importance == 'essential':
                missing_essential.append(skill)
            elif importance == 'critical':
                missing_critical.append(skill)
            elif importance == 'important':
                missing_important.append(skill)
        
        # Count totals by category
        if importance == 'essential':
            essential_total += 1
        elif importance == 'critical':
            critical_total += 1
        elif importance == 'important':
            important_total += 1
        elif importance == 'preferred':
            preferred_total += 1
    
    # Calculate base match percentage
    if total_weight > 0:
        match_percentage = (matched_weight / total_weight) * 100
    else:
        match_percentage = 0
    
    # Apply essential gate: missing ANY essential = cap at 25%
    if missing_essential:
        match_percentage = min(match_percentage, 25)
        qualified = False
    else:
        qualified = match_percentage >= 60  # 60% threshold for "qualified"
    
    # Determine match category
    if match_percentage >= 80:
        match_category = 'HIGH'
    elif match_percentage >= 50:
        match_category = 'MEDIUM'
    elif match_percentage >= 25:
        match_category = 'LOW'
    else:
        match_category = 'DISQUALIFIED'
    
    # Extract ambiguous requirements if using LLM matching
    ambiguous_requirements = []
    if batch_result:
        ambiguous_requirements = batch_result.get('ambiguous', [])
    
    return {
        'match_percentage': match_percentage,
        'match_category': match_category,
        'qualified': qualified,
        'matched_requirements': len(matched_skills),
        'total_weight': total_weight,
        'matched_weight': matched_weight,
        'essential_skills_met': essential_met,
        'essential_skills_total': essential_total,
        'critical_skills_met': critical_met,
        'critical_skills_total': critical_total,
        'important_skills_met': important_met,
        'important_skills_total': important_total,
        'preferred_skills_met': preferred_met,
        'preferred_skills_total': preferred_total,
        'matched_skills': matched_skills,
        'missing_essential': missing_essential,
        'missing_critical': missing_critical,
        'missing_important': missing_important,
        'proficiency_gaps': proficiency_gaps,
        'ambiguous_requirements': ambiguous_requirements
    }


def generate_match_explanation(match_data, profile_info, job_info):
    """Generate human-readable match explanation"""
    
    explanation = []
    
    # 1. MATCH VERDICT
    percentage = match_data['match_percentage']
    category = match_data['match_category']
    qualified = match_data['qualified']
    
    if category == 'HIGH':
        verdict = f"🎯 **STRONG MATCH ({percentage}%)**"
        if qualified:
            verdict += " - Highly recommended for interview."
        else:
            verdict += " - Good skills overlap but missing some essentials."
    elif category == 'MEDIUM':
        verdict = f"⚠️  **MODERATE MATCH ({percentage}%)**"
        verdict += " - Partial fit with some transferable skills. Review carefully."
    elif category == 'LOW':
        verdict = f"❌ **WEAK MATCH ({percentage}%)**"
        verdict += " - Few overlapping skills. Not recommended."
    else:
        verdict = f"🚫 **DISQUALIFIED ({percentage}%)**"
        verdict += " - Missing essential requirements."
    
    explanation.append(verdict)
    explanation.append("")
    
    # 2. STRENGTHS
    if match_data['matched_skills']:
        explanation.append("**STRENGTHS:**")
        
        # Show essential matches first
        if match_data['essential_skills_met'] > 0:
            essential_pct = (match_data['essential_skills_met'] / match_data['essential_skills_total'] * 100) if match_data['essential_skills_total'] > 0 else 0
            explanation.append(f"  ✅ Essential skills: {match_data['essential_skills_met']}/{match_data['essential_skills_total']} ({essential_pct:.0f}%)")
        
        # Show critical matches
        if match_data['critical_skills_met'] > 0:
            critical_pct = (match_data['critical_skills_met'] / match_data['critical_skills_total'] * 100) if match_data['critical_skills_total'] > 0 else 0
            explanation.append(f"  ✅ Critical skills: {match_data['critical_skills_met']}/{match_data['critical_skills_total']} ({critical_pct:.0f}%)")
        
        # List some key matched skills
        if len(match_data['matched_skills']) <= 8:
            explanation.append(f"  ✅ Matched: {', '.join(match_data['matched_skills'])}")
        else:
            explanation.append(f"  ✅ Matched: {', '.join(match_data['matched_skills'][:8])} + {len(match_data['matched_skills']) - 8} more")
        
        explanation.append("")
    
    # 3. PROFICIENCY GAPS (has skill but insufficient level/experience)
    if match_data.get('proficiency_gaps'):
        explanation.append("**PROFICIENCY GAPS:**")
        for gap in match_data['proficiency_gaps'][:5]:  # Show top 5
            skill = gap['skill']
            req_prof = gap['required_proficiency']
            cand_prof = gap['candidate_proficiency'] or 'unknown'
            req_years = gap['required_years']
            cand_years = gap['candidate_years'] or 0
            quality = gap['quality_score']
            
            gap_details = []
            if req_prof and cand_prof != req_prof:
                gap_details.append(f"has {cand_prof}, needs {req_prof}")
            if req_years and cand_years < req_years:
                gap_details.append(f"has {cand_years}y, needs {req_years}y")
            
            explanation.append(f"  ⚡ {skill}: {' & '.join(gap_details)} ({int(quality*100)}% match)")
        explanation.append("")
    
    # 4. AMBIGUOUS REQUIREMENTS (need clarification)
    if match_data.get('ambiguous_requirements'):
        explanation.append("**⚠️  AMBIGUOUS JOB REQUIREMENTS (Need Clarification):**")
        for amb in match_data['ambiguous_requirements']:
            skill = amb['job_skill']
            importance = amb['job_requirement'].get('importance', 'unknown')
            reasoning = amb.get('reasoning', 'Requirement is vague or unclear')
            explanation.append(f"  ❓ {skill} ({importance}): {reasoning}")
        explanation.append("")
    
    # 5. GAPS (missing skills entirely)
    has_gaps = match_data['missing_essential'] or match_data['missing_critical'] or match_data['missing_important']
    
    if has_gaps:
        explanation.append("**GAPS:**")
        
        if match_data['missing_essential']:
            explanation.append(f"  🚫 Missing essential: {', '.join(match_data['missing_essential'])}")
        
        if match_data['missing_critical']:
            if len(match_data['missing_critical']) <= 5:
                explanation.append(f"  ⚠️  Missing critical: {', '.join(match_data['missing_critical'])}")
            else:
                explanation.append(f"  ⚠️  Missing critical: {', '.join(match_data['missing_critical'][:5])} + {len(match_data['missing_critical']) - 5} more")
        
        if match_data['missing_important'] and len(match_data['missing_important']) <= 3:
            explanation.append(f"  ℹ️  Missing nice-to-have: {', '.join(match_data['missing_important'])}")
        
        explanation.append("")
    
    # 6. RECOMMENDATION
    explanation.append("**RECOMMENDATION:**")
    if category == 'HIGH' and qualified:
        explanation.append("  ➡️  Schedule interview. Candidate meets core requirements.")
    elif category == 'HIGH' and not qualified:
        explanation.append("  ➡️  Review missing essentials. May need training or compensatory experience.")
    elif category == 'MEDIUM':
        explanation.append("  ➡️  Consider for roles with similar skill sets. Assess transferable skills.")
    elif category == 'LOW':
        explanation.append("  ➡️  Not recommended for this position. Skill gap too large.")
    else:
        explanation.append("  ➡️  Do not proceed. Missing critical essential requirements.")
    
    return '\n'.join(explanation)


def match_profile_to_job(profile_id, job_id, save_to_db=True, verbose=True, use_llm_matching=False):
    """Match a single profile to a single job"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get profile data
    cursor.execute("""
        SELECT profile_id, full_name, current_title, skill_keywords, profile_summary
        FROM profiles
        WHERE profile_id = %s
    """, (profile_id,))
    
    profile_row = cursor.fetchone()
    if not profile_row:
        print(f"❌ Profile {profile_id} not found")
        conn.close()
        return None
    
    profile_info = {
        'profile_id': profile_row[0],
        'full_name': profile_row[1],
        'current_title': profile_row[2],
        'skills': profile_row[3] or [],
        'summary': profile_row[4]
    }
    
    # Get job data
    cursor.execute("""
        SELECT job_id, job_title, organization_name, skill_keywords
        FROM postings
        WHERE job_id = %s
    """, (job_id,))
    
    job_row = cursor.fetchone()
    if not job_row:
        print(f"❌ Job {job_id} not found")
        conn.close()
        return None
    
    job_info = {
        'job_id': job_row[0],
        'job_title': job_row[1],
        'organization': job_row[2],
        'requirements': job_row[3] or []
    }
    
    # Calculate match
    job_context = f"{job_info['job_title']} at {job_info['organization']}"
    match_data = calculate_weighted_match(
        profile_info['skills'], 
        job_info['requirements'],
        profile_info['full_name'],
        use_llm_matching=use_llm_matching,
        job_context=job_context
    )
    
    # Generate explanation
    explanation = generate_match_explanation(match_data, profile_info, job_info)
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"MATCHING: {profile_info['full_name']} → {job_info['job_title']}")
        print(f"{'='*80}")
        print(explanation)
        print(f"{'='*80}\n")
    
    # Save to database
    if save_to_db:
        cursor.execute("""
            INSERT INTO profile_job_matches (
                profile_id, job_id, overall_match_score, skill_match_score,
                matched_skills, missing_skills, extra_skills, match_explanation,
                match_status, match_quality, matched_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (profile_id, job_id) 
            DO UPDATE SET
                overall_match_score = EXCLUDED.overall_match_score,
                skill_match_score = EXCLUDED.skill_match_score,
                matched_skills = EXCLUDED.matched_skills,
                missing_skills = EXCLUDED.missing_skills,
                match_explanation = EXCLUDED.match_explanation,
                match_status = EXCLUDED.match_status,
                match_quality = EXCLUDED.match_quality,
                matched_at = EXCLUDED.matched_at
        """, (
            profile_id,
            job_id,
            match_data['match_percentage'],
            match_data['match_percentage'],  # Same for now
            json.dumps(match_data['matched_skills']),
            json.dumps(match_data['missing_essential'] + match_data['missing_critical']),
            json.dumps([]),  # extra_skills TODO
            explanation,
            'completed',  # match_status
            match_data['match_category'].lower(),  # match_quality
            datetime.now()
        ))
        
        conn.commit()
    
    conn.close()
    
    return {
        'profile': profile_info,
        'job': job_info,
        'match': match_data,
        'explanation': explanation
    }


def match_all_test_data():
    """Match all test profiles against all test jobs"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get all test profiles
    cursor.execute("SELECT profile_id, full_name FROM profiles WHERE is_test_profile = TRUE ORDER BY profile_id")
    profiles = cursor.fetchall()
    
    # Get all test jobs
    cursor.execute("SELECT job_id, job_title FROM postings WHERE is_test_posting = TRUE ORDER BY job_id")
    jobs = cursor.fetchall()
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"MATCHING {len(profiles)} TEST PROFILES × {len(jobs)} TEST JOBS = {len(profiles) * len(jobs)} MATCHES")
    print(f"{'='*80}\n")
    
    results = []
    
    for profile_id, profile_name in profiles:
        for job_id, job_title in jobs:
            result = match_profile_to_job(profile_id, job_id, save_to_db=True, verbose=True)
            if result:
                results.append(result)
    
    # Print summary matrix
    print(f"\n{'='*80}")
    print(f"MATCH SUMMARY MATRIX")
    print(f"{'='*80}\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.full_name,
            j.job_title,
            m.overall_match_score,
            m.match_status
        FROM profile_job_matches m
        JOIN profiles p ON m.profile_id = p.profile_id
        JOIN postings j ON m.job_id = j.job_id
        WHERE p.is_test_profile = TRUE AND j.is_test_posting = TRUE
        ORDER BY p.profile_id, j.job_id
    """)
    
    for row in cursor.fetchall():
        status_emoji = {'high': '✅', 'medium': '⚠️', 'low': '❌', 'disqualified': '🚫'}.get(row[3], '❓')
        print(f"{status_emoji} {row[0]:25s} → {row[1]:40s} {row[2]:5.1f}%")
    
    conn.close()
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Recipe 3: Profile-Job Matching Engine')
    parser.add_argument('--profile-id', type=int, help='Profile ID to match')
    parser.add_argument('--job-id', type=str, help='Job ID to match')
    parser.add_argument('--match-all-test-jobs', action='store_true', help='Match profile against all test jobs')
    parser.add_argument('--match-all-test-profiles-and-jobs', action='store_true', help='Match all test profiles against all test jobs')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save results to database')
    parser.add_argument('--use-llm-matching', action='store_true', help='Use LLM-guided skill matching (Qwen resolves skill matches)')
    
    args = parser.parse_args()
    
    if args.match_all_test_profiles_and_jobs:
        match_all_test_data()
    elif args.match_all_test_jobs and args.profile_id:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM postings WHERE is_test_posting = TRUE")
        jobs = cursor.fetchall()
        conn.close()
        
        for (job_id,) in jobs:
            match_profile_to_job(args.profile_id, job_id, save_to_db=not args.no_save)
    elif args.profile_id and args.job_id:
        match_profile_to_job(
            args.profile_id, 
            args.job_id, 
            save_to_db=not args.no_save,
            use_llm_matching=args.use_llm_matching
        )
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
