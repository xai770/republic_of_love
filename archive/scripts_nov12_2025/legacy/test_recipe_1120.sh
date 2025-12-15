#!/bin/bash
# Test Recipe 1120 with a sample job posting

export PGPASSWORD='base_yoga_secure_2025'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTING RECIPE 1120: SkillBridge Skills Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Insert test job posting
echo "📝 Creating test job posting..."
psql -h localhost -U base_admin -d base_yoga << 'SQL'
INSERT INTO postings (
    job_id, 
    job_title, 
    job_description,
    metadata_source,
    enabled
)
VALUES (
    'test_sb_001',
    'Frontend Developer',
    'Frontend Developer at Tech Innovators Inc.
    
Required Skills:
- HTML, CSS, JavaScript
- React or Angular frameworks
- RESTful APIs integration
- Git version control
- Strong problem-solving skills
- Passion for creating user-friendly interfaces
- Team collaboration and communication',
    'manual_test',
    true
)
ON CONFLICT (job_id) DO UPDATE SET
    job_description = EXCLUDED.job_description,
    updated_at = CURRENT_TIMESTAMP;

SELECT 'Job posting created: ' || job_id || ' - ' || job_title FROM postings WHERE job_id = 'test_sb_001';
SQL

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Now run: python3 recipe_run_test_runner_v32.py"
echo "    Or manually trigger Recipe 1120 with job_id='test_sb_001'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
