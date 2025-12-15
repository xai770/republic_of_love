"""
Fuzzy Skill Matching - Python Integration

Uses PostgreSQL functions for hierarchical skill similarity scoring.
Enables intelligent candidate-job matching beyond exact matches.

Created: 2025-11-07
"""

from typing import Dict, List, Optional, Tuple
import json
from core.database import get_connection


class FuzzySkillMatcher:
    """
    Hierarchical skill matching using database functions.
    
    Example:
        matcher = FuzzySkillMatcher()
        
        # Match single profile to job
        result = matcher.match_profile_to_job(profile_id=1, posting_id=2)
        print(f"Match: {result['match_percentage']:.1f}%")
        
        # Find top candidates for job
        candidates = matcher.find_top_candidates(posting_id=2, limit=10)
        for c in candidates:
            print(f"{c['name']}: {c['match_pct']:.1f}%")
    """
    
    def __init__(self, decay_mode: str = 'reciprocal'):
        """
        Initialize matcher.
        
        Args:
            decay_mode: 'reciprocal' (1/distance) or 'exponential' (0.7^distance)
        """
        self.decay_mode = decay_mode
        self.conn = None
    
    def _get_connection(self):
        """Get database connection (reuse if exists)."""
        if self.conn is None or self.conn.closed:
            self.conn = get_connection()
        return self.conn
    
    def find_skill_path(self, skill_a_id: int, skill_b_id: int) -> Optional[Dict]:
        """
        Find relationship path between two skills.
        
        Args:
            skill_a_id: First skill ID
            skill_b_id: Second skill ID
            
        Returns:
            {
                'path_length': 2,
                'relationship_type': 'sibling',
                'common_ancestor': 749,
                'path_strength': 1.0
            }
            or None if unrelated
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT path_length, relationship_type, common_ancestor, path_strength
            FROM find_skill_path(%s, %s)
        """
        
        cursor.execute(query, (skill_a_id, skill_b_id))
        result = cursor.fetchone()
        
        if result and result[1] != 'unrelated':
            return {
                'path_length': result[0],
                'relationship_type': result[1],
                'common_ancestor': result[2],
                'path_strength': float(result[3]) if result[3] else 0.0
            }
        return None
    
    def calculate_skill_match(
        self, 
        job_skill_id: int, 
        candidate_skill_id: int,
        job_weight: int
    ) -> Dict:
        """
        Calculate match score for single skill pair.
        
        Args:
            job_skill_id: Required skill ID
            candidate_skill_id: Candidate's skill ID
            job_weight: Importance (10-100)
            
        Returns:
            {
                'match_score': 40.0,
                'match_type': 'sibling',
                'distance': 2,
                'explanation': 'Sibling skill (strength=1.0000 / distance=2)'
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT match_score, match_type, distance, explanation
            FROM calculate_skill_match_score(%s, %s, %s, %s)
        """
        
        cursor.execute(query, (job_skill_id, candidate_skill_id, job_weight, self.decay_mode))
        result = cursor.fetchone()
        
        return {
            'match_score': float(result[0]) if result[0] else 0.0,
            'match_type': result[1],
            'distance': result[2],
            'explanation': result[3]
        }
    
    def match_profile_to_job(
        self,
        profile_id: int,
        posting_id: int
    ) -> Dict:
        """
        Match entire profile to job posting.
        
        Args:
            profile_id: Candidate profile ID
            posting_id: Job posting ID
            
        Returns:
            {
                'total_score': 285.5,
                'max_possible_score': 500,
                'match_percentage': 57.1,
                'matched_skills_count': 8,
                'required_skills_count': 10,
                'skill_matches': [...detailed JSON...]
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                total_score,
                max_possible_score,
                match_percentage,
                matched_skills_count,
                required_skills_count,
                skill_matches
            FROM match_profile_to_job(%s, %s, %s)
        """
        
        cursor.execute(query, (profile_id, posting_id, self.decay_mode))
        result = cursor.fetchone()
        
        return {
            'total_score': float(result[0]) if result[0] else 0.0,
            'max_possible_score': float(result[1]) if result[1] else 0.0,
            'match_percentage': float(result[2]) if result[2] else 0.0,
            'matched_skills_count': result[3],
            'required_skills_count': result[4],
            'skill_matches': result[5]  # Already JSONB, comes as dict
        }
    
    def find_top_candidates(
        self,
        posting_id: int,
        min_match_pct: float = 50.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find best matching candidates for a job.
        
        Args:
            posting_id: Job posting ID
            min_match_pct: Minimum match threshold (0-100)
            limit: Maximum results
            
        Returns:
            [
                {
                    'profile_id': 1,
                    'name': 'John Doe',
                    'match_pct': 87.5,
                    'matched_skills': 12,
                    'required_skills': 14,
                    'coverage': '12/14',
                    'details': {...}
                },
                ...
            ]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                p.profile_id,
                p.full_name,
                m.match_percentage,
                m.matched_skills_count,
                m.required_skills_count,
                m.skill_matches
            FROM profiles p
            CROSS JOIN LATERAL match_profile_to_job(p.profile_id, %s, %s) m
            WHERE m.match_percentage >= %s
            ORDER BY m.match_percentage DESC, m.matched_skills_count DESC
            LIMIT %s
        """
        
        cursor.execute(query, (posting_id, self.decay_mode, min_match_pct, limit))
        results = cursor.fetchall()
        
        return [
            {
                'profile_id': row[0],
                'name': row[1],
                'match_pct': float(row[2]) if row[2] else 0.0,
                'matched_skills': row[3],
                'required_skills': row[4],
                'coverage': f"{row[3]}/{row[4]}",
                'details': row[5]
            }
            for row in results
        ]
    
    def find_top_jobs(
        self,
        profile_id: int,
        min_match_pct: float = 40.0,
        limit: int = 10,
        active_only: bool = True
    ) -> List[Dict]:
        """
        Find best matching jobs for a candidate.
        
        Args:
            profile_id: Candidate profile ID
            min_match_pct: Minimum match threshold (0-100)
            limit: Maximum results
            active_only: Only show active job postings
            
        Returns:
            [
                {
                    'posting_id': 2,
                    'title': 'Senior Python Developer',
                    'location': 'Frankfurt',
                    'match_pct': 82.3,
                    'matched_skills': 9,
                    'required_skills': 11,
                    'details': {...}
                },
                ...
            ]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        status_filter = "AND j.posting_status = 'active'" if active_only else ""
        
        query = f"""
            SELECT 
                j.posting_id,
                j.job_title,
                j.location_city,
                m.match_percentage,
                m.matched_skills_count,
                m.required_skills_count,
                m.skill_matches
            FROM postings j
            CROSS JOIN LATERAL match_profile_to_job(%s, j.posting_id, %s) m
            WHERE m.match_percentage >= %s
            {status_filter}
            ORDER BY m.match_percentage DESC, m.matched_skills_count DESC
            LIMIT %s
        """
        
        cursor.execute(query, (profile_id, self.decay_mode, min_match_pct, limit))
        results = cursor.fetchall()
        
        return [
            {
                'posting_id': row[0],
                'title': row[1],
                'location': row[2],
                'match_pct': float(row[3]) if row[3] else 0.0,
                'matched_skills': row[4],
                'required_skills': row[5],
                'coverage': f"{row[4]}/{row[5]}",
                'details': row[6]
            }
            for row in results
        ]
    
    def get_skill_gap_analysis(
        self,
        profile_id: int,
        posting_id: int
    ) -> Dict:
        """
        Analyze skill gaps between candidate and job.
        
        Returns skills that are:
        - Matched (exact or fuzzy)
        - Missing (no match found)
        - Partial (sibling/parent matches)
        
        Returns:
            {
                'exact_matches': [...],
                'fuzzy_matches': [...],
                'missing_skills': [...],
                'training_recommendations': [...]
            }
        """
        match_result = self.match_profile_to_job(profile_id, posting_id)
        skill_matches = match_result['skill_matches']
        
        exact = []
        fuzzy = []
        missing = []
        
        for match in skill_matches:
            if match['match_type'] == 'exact':
                exact.append({
                    'skill': match['required_skill'],
                    'proficiency': match.get('proficiency'),
                    'years': match.get('years_experience')
                })
            elif match['match_type'] == 'missing':
                missing.append({
                    'skill': match['required_skill'],
                    'importance': match['importance'],
                    'weight': match['max_score']
                })
            else:  # parent, child, sibling
                fuzzy.append({
                    'required': match['required_skill'],
                    'has': match['candidate_skill'],
                    'match_type': match['match_type'],
                    'score_pct': round(match['match_score'] / match['max_score'] * 100, 1),
                    'explanation': match['explanation']
                })
        
        # Training recommendations = missing essential/critical skills
        training = [
            skill for skill in missing
            if skill['importance'] in ['essential', 'critical']
        ]
        
        return {
            'exact_matches': exact,
            'fuzzy_matches': fuzzy,
            'missing_skills': missing,
            'training_recommendations': training,
            'summary': {
                'exact_count': len(exact),
                'fuzzy_count': len(fuzzy),
                'missing_count': len(missing),
                'critical_gaps': len(training)
            }
        }
    
    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Example 1: Match single profile to job
    print("=" * 60)
    print("Example 1: Match Profile to Job")
    print("=" * 60)
    
    with FuzzySkillMatcher(decay_mode='reciprocal') as matcher:
        result = matcher.match_profile_to_job(profile_id=1, posting_id=2)
        
        print(f"Match Percentage: {result['match_percentage']:.1f}%")
        print(f"Skills Matched: {result['matched_skills_count']}/{result['required_skills_count']}")
        print(f"Score: {result['total_score']:.0f}/{result['max_possible_score']:.0f}")
        print()
        
        # Show top 5 matches
        print("Top Skill Matches:")
        for match in result['skill_matches'][:5]:
            print(f"  • {match['required_skill']}: {match['match_type']} "
                  f"(score: {match['match_score']:.1f}/{match['max_score']})")
    
    # Example 2: Find top candidates for job
    print("\n" + "=" * 60)
    print("Example 2: Top 5 Candidates for Job #2")
    print("=" * 60)
    
    with FuzzySkillMatcher() as matcher:
        candidates = matcher.find_top_candidates(posting_id=2, limit=5)
        
        for i, candidate in enumerate(candidates, 1):
            print(f"{i}. {candidate['name']}")
            print(f"   Match: {candidate['match_pct']:.1f}% ({candidate['coverage']} skills)")
    
    # Example 3: Find top jobs for candidate
    print("\n" + "=" * 60)
    print("Example 3: Top 5 Jobs for Profile #1")
    print("=" * 60)
    
    with FuzzySkillMatcher(decay_mode='exponential') as matcher:
        jobs = matcher.find_top_jobs(profile_id=1, limit=5)
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job['title']} ({job['location']})")
            print(f"   Match: {job['match_pct']:.1f}% ({job['coverage']} skills)")
    
    # Example 4: Skill gap analysis
    print("\n" + "=" * 60)
    print("Example 4: Skill Gap Analysis")
    print("=" * 60)
    
    with FuzzySkillMatcher() as matcher:
        gaps = matcher.get_skill_gap_analysis(profile_id=1, posting_id=2)
        
        print(f"✓ Exact Matches: {gaps['summary']['exact_count']}")
        print(f"≈ Fuzzy Matches: {gaps['summary']['fuzzy_count']}")
        print(f"✗ Missing Skills: {gaps['summary']['missing_count']}")
        print(f"⚠ Critical Gaps: {gaps['summary']['critical_gaps']}")
        
        if gaps['training_recommendations']:
            print("\nTraining Recommendations:")
            for skill in gaps['training_recommendations'][:3]:
                print(f"  • {skill['skill']} ({skill['importance']})")
