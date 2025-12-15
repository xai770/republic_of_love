#!/usr/bin/env python3
"""
Generate test descriptions with known quality levels for grader validation
"""

# Perfect output (from gemma3:1b QA test)
PERFECT_DESCRIPTION = """===OUTPUT TEMPLATE===
ROLE: Senior Consultant
KEY_RESPONSIBILITIES: 
• Strategy & Transformation projects
• Client Interaction and meetings
• Project Management and team leadership
REQUIREMENTS: 
• Excellent Academic Background (Bachelor's/Master's)
• Project Management Experience
• Strong Analytical Skills
• Excellent Communication Skills in German and English
===END TEMPLATE==="""

# Flawed outputs for testing
WRONG_ROLE = """===OUTPUT TEMPLATE===
ROLE: Data Scientist
KEY_RESPONSIBILITIES: 
• Strategy & Transformation projects
• Client Interaction and meetings
• Project Management and team leadership
REQUIREMENTS: 
• Excellent Academic Background (Bachelor's/Master's)
• Project Management Experience
• Strong Analytical Skills
• Excellent Communication Skills in German and English
===END TEMPLATE==="""

MISSING_REQUIREMENTS = """===OUTPUT TEMPLATE===
ROLE: Senior Consultant
KEY_RESPONSIBILITIES: 
• Strategy & Transformation projects
• Client Interaction and meetings
• Project Management and team leadership
REQUIREMENTS: 
• Good academic background
===END TEMPLATE==="""

HALLUCINATED_SKILLS = """===OUTPUT TEMPLATE===
ROLE: Senior Consultant
KEY_RESPONSIBILITIES: 
• Strategy & Transformation projects
• Client Interaction and meetings
• Python development and SQL database management
REQUIREMENTS: 
• Excellent Academic Background (Bachelor's/Master's)
• Advanced Python programming skills
• Docker and AWS cloud experience
• Project Management Experience
===END TEMPLATE==="""

POOR_FORMAT = """Senior Consultant role involving strategy work, client meetings, and project management. 
Requirements include good education, experience, and communication skills."""

TOO_VERBOSE = """===OUTPUT TEMPLATE===
ROLE: Senior Consultant for Strategic Management Consulting
KEY_RESPONSIBILITIES: 
• Lead comprehensive strategy and transformation projects across multiple business units
• Engage in extensive direct contact with high-level clients within the bank to conduct independent strategic meetings
• Manage complex project portfolios and provide leadership to diverse team members
• Collaborate extensively with Engagement Managers to prepare detailed decision templates for senior management and board
• Support comprehensive development of project team capabilities and conception of industry best practices
• Develop and implement advanced methodological approaches and frameworks
REQUIREMENTS: 
• Outstanding Bachelor's or Master's degree from prestigious university in any field
• Extensive relevant professional experience, ideally in project management or consulting
• Superior analytical skills and exceptional organizational talent
• Fluent communication skills in German and English languages
• Advanced presentation and stakeholder management capabilities
• Strong business acumen and strategic thinking abilities
===END TEMPLATE==="""

TOO_BRIEF = """===OUTPUT TEMPLATE===
ROLE: Consultant
KEY_RESPONSIBILITIES: Strategy work
REQUIREMENTS: Degree
===END TEMPLATE==="""

# Test cases with expected grades
TEST_CASES = [
    {
        'name': 'perfect_gemma3_output',
        'description': PERFECT_DESCRIPTION,
        'expected_grade': 'PASS',
        'reason': 'Perfect template, correct role, accurate requirements, no hallucinations'
    },
    {
        'name': 'wrong_role_data_scientist', 
        'description': WRONG_ROLE,
        'expected_grade': 'FAIL',
        'reason': 'Role is Data Scientist, should be Senior Consultant'
    },
    {
        'name': 'missing_requirements',
        'description': MISSING_REQUIREMENTS, 
        'expected_grade': 'FAIL',
        'reason': 'Only 1 requirement listed, missing key qualifications'
    },
    {
        'name': 'hallucinated_technical_skills',
        'description': HALLUCINATED_SKILLS,
        'expected_grade': 'FAIL', 
        'reason': 'Invented Python, SQL, Docker, AWS - not in original job posting'
    },
    {
        'name': 'poor_format_no_template',
        'description': POOR_FORMAT,
        'expected_grade': 'FAIL',
        'reason': 'Missing template structure and markers'
    },
    {
        'name': 'too_verbose_excessive_detail',
        'description': TOO_VERBOSE,
        'expected_grade': 'FAIL',
        'reason': 'Overly verbose, not concise, excessive elaboration'
    },
    {
        'name': 'too_brief_insufficient_detail',
        'description': TOO_BRIEF,
        'expected_grade': 'FAIL', 
        'reason': 'Too brief, missing essential information'
    }
]

if __name__ == "__main__":
    print("GRADER VALIDATION TEST CASES")
    print("="*50)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n{i}. {case['name']}")
        print(f"Expected: {case['expected_grade']}")
        print(f"Reason: {case['reason']}")
        print(f"Length: {len(case['description'])} chars")
        print(f"Preview: {case['description'][:100]}...")
    
    print(f"\nTotal test cases: {len(TEST_CASES)}")
    print("Expected results: 1 PASS, 6 FAIL")