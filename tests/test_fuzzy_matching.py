#!/usr/bin/env python3
"""
Quick test of fuzzy skill matching functions.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.database import get_connection

def test_fuzzy_matching():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Helper to get first column value
    def get_value(query, col_name='count'):
        cursor.execute(query)
        result = cursor.fetchone()
        return result[col_name] if result else 0
    
    print("=" * 70)
    print("FUZZY SKILL MATCHING - LIVE TEST")
    print("=" * 70)
    
    # Test 1: Check data availability
    print("\n1. Data Inventory:")
    profile_count = get_value("SELECT COUNT(*) as count FROM profiles")
    print(f"   Profiles: {profile_count}")
    
    job_count = get_value("SELECT COUNT(*) as count FROM postings WHERE posting_status = 'active'")
    print(f"   Active Jobs: {job_count}")
    
    job_skill_count = get_value("SELECT COUNT(*) as count FROM job_skills")
    print(f"   Job-Skill Mappings: {job_skill_count}")
    
    profile_skill_count = get_value("SELECT COUNT(*) as count FROM profile_skills")
    print(f"   Profile-Skill Mappings: {profile_skill_count}")
    
    # Test 2: Skill path finding
    print("\n2. Test: Find relationship between skills")
    query = """
        SELECT 
            sa1.skill_name as skill_a,
            sa2.skill_name as skill_b,
            p.path_length,
            p.relationship_type,
            p.path_strength
        FROM skill_aliases sa1, skill_aliases sa2
        CROSS JOIN LATERAL find_skill_path(sa1.skill_id, sa2.skill_id) p
        WHERE sa1.skill_name IN ('oracle_database', 'sql')
          AND sa2.skill_name IN ('oracle_database', 'sql')
          AND p.relationship_type != 'exact'
        LIMIT 5
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    for row in results:
        print(f"   {row['skill_a']} ↔ {row['skill_b']}: {row['relationship_type']} (distance={row['path_length']}, strength={row['path_strength']})")
    
    # Test 3: Calculate match score
    print("\n3. Test: Calculate skill match score")
    query = """
        SELECT * FROM calculate_skill_match_score(
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'oracle_database' LIMIT 1),
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'sql' LIMIT 1),
            80,
            'reciprocal'
        )
    """
    cursor.execute(query)
    result = cursor.fetchone()
    
    if result:
        print(f"   Job wants: oracle_database (weight=80)")
        print(f"   Candidate has: sql")
        print(f"   Match score: {result['match_score']:.1f}")
        print(f"   Match type: {result['match_type']}")
        print(f"   Explanation: {result['explanation']}")
    
    # Test 4: Full profile-job matching
    print("\n4. Test: Match profile to job")
    
    # Find a profile with skills
    cursor.execute("""
        SELECT DISTINCT profile_id 
        FROM profile_skills 
        LIMIT 1
    """)
    profile_result = cursor.fetchone()
    
    # Find a job with skills
    cursor.execute("""
        SELECT DISTINCT posting_id 
        FROM job_skills 
        LIMIT 1
    """)
    job_result = cursor.fetchone()
    
    if profile_result and job_result:
        profile_id = profile_result['profile_id']
        posting_id = job_result['posting_id']
        
        query = """
            SELECT 
                total_score,
                max_possible_score,
                match_percentage,
                matched_skills_count,
                required_skills_count
            FROM match_profile_to_job(%s, %s, 'reciprocal')
        """
        cursor.execute(query, (profile_id, posting_id))
        result = cursor.fetchone()
        
        if result:
            print(f"   Profile #{profile_id} vs Job #{posting_id}:")
            print(f"   Match: {result['match_percentage']:.1f}%")
            print(f"   Score: {result['total_score']:.0f} / {result['max_possible_score']:.0f}")
            print(f"   Skills: {result['matched_skills_count']} / {result['required_skills_count']}")
    else:
        print("   ⚠ No profile or job data available")
    
    # Test 5: Find top candidates for a job
    print("\n5. Test: Find top candidates for a job")
    
    query = """
        SELECT 
            p.profile_id,
            p.full_name,
            m.match_percentage,
            m.matched_skills_count,
            m.required_skills_count
        FROM profiles p
        CROSS JOIN LATERAL match_profile_to_job(p.profile_id, %s, 'reciprocal') m
        WHERE m.match_percentage > 0
        ORDER BY m.match_percentage DESC
        LIMIT 3
    """
    cursor.execute(query, (posting_id,))
    results = cursor.fetchall()
    
    if results:
        print(f"   Top candidates for Job #{posting_id}:")
        for i, row in enumerate(results, 1):
            name = row['full_name'] if row['full_name'] else f"Profile #{row['profile_id']}"
            print(f"   {i}. {name}: {row['match_percentage']:.1f}% ({row['matched_skills_count']}/{row['required_skills_count']} skills)")
    else:
        print("   ⚠ No matching candidates found")
    
    # Test 6: Compare decay modes
    print("\n6. Test: Compare decay modes")
    
    score_recip = get_value("""
        SELECT match_score as count
        FROM calculate_skill_match_score(
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'oracle_database' LIMIT 1),
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'sql' LIMIT 1),
            100,
            'reciprocal'
        )
    """)
    
    score_exp = get_value("""
        SELECT match_score as count
        FROM calculate_skill_match_score(
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'oracle_database' LIMIT 1),
            (SELECT skill_id FROM skill_aliases WHERE skill_name = 'sql' LIMIT 1),
            100,
            'exponential'
        )
    """)
    
    print(f"   Oracle ↔ SQL (weight=100):")
    print(f"   Reciprocal mode: {score_recip:.1f} points")
    print(f"   Exponential mode: {score_exp:.1f} points")
    print(f"   Difference: {abs(score_recip - score_exp):.1f} points")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    
    cursor.close()
    conn.close()


if __name__ == '__main__':
    test_fuzzy_matching()
