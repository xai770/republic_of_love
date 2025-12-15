#!/usr/bin/env python3
"""
Test Recipe 1121: Gopher Skill Extraction
Runs a single job through the extraction pipeline
"""

import sys
import json
from universal_executor import UniversalExecutor

def test_recipe_1121(job_id='15929'):
    """Test Recipe 1121 with a single job"""
    
    executor = UniversalExecutor()
    
    # Get job description
    job_desc = executor.get_job_description(job_id)
    if not job_desc:
        print(f"❌ Job {job_id} not found")
        return False
    
    print(f"🎯 Testing Recipe 1121 with Job {job_id}")
    print(f"📄 Job description length: {len(job_desc)} chars")
    print("=" * 80)
    
    # Step 1: Fetch summary (using raw description since extracted_summary is NULL)
    print("\n📋 Step 1: Fetch job summary")
    print("-" * 40)
    context = {
        'job_id': job_id,
        'extracted_summary': '',  # NULL in database
        'job_description': job_desc
    }
    
    prompt1 = f"""You are a data retriever. Extract the job summary for job_id: {job_id}

The extracted_summary field from the postings table contains:
{context['extracted_summary']}

If the summary is empty or NULL, use the raw job_description instead:
{context['job_description']}

Return ONLY the job description text, no additional commentary."""
    
    response1 = executor.call_actor('phi3:latest', prompt1, context)
    print(f"✓ Retrieved: {len(response1)} chars")
    print(f"Preview: {response1[:200]}...")
    
    # Step 2: Extract skills
    print("\n🔍 Step 2: Extract key skills")
    print("-" * 40)
    prompt2 = f"""You are a skill extraction expert. Analyze this job description and extract ALL skills mentioned:

{response1}

List each skill on a separate line. Include:
- Technical skills (programming languages, tools, frameworks)
- Soft skills (communication, leadership, teamwork)
- Domain knowledge (industry expertise, certifications)
- Methodologies (Agile, DevOps, etc.)

Format: One skill per line, no bullets or numbers."""
    
    response2 = executor.call_actor('phi3:latest', prompt2, {'previous_response': response1})
    print(f"✓ Extracted skills:")
    print(response2)
    
    # Step 3: BUILD HIERARCHY WITH GOPHER! 🚀
    print("\n🌳 Step 3: Build hierarchy with skill_gopher")
    print("-" * 40)
    print("🤖 DELEGATING to autonomous gopher...")
    
    response3 = executor.call_actor('skill_gopher', response2, {'job_content': response2})
    print(f"✓ Gopher complete!")
    
    try:
        gopher_result = json.loads(response3)
        print(f"📊 Stats:")
        print(f"   - Nodes explored: {gopher_result.get('stats', {}).get('nodes_explored', 'N/A')}")
        print(f"   - Leaf skills: {gopher_result.get('stats', {}).get('leaf_count', 'N/A')}")
        print(f"   - Execution time: {gopher_result.get('stats', {}).get('execution_time_seconds', 'N/A')}s")
        print(f"\n🌲 Hierarchy ({len(gopher_result.get('hierarchy', []))} paths):")
        for path in gopher_result.get('hierarchy', [])[:10]:
            print(f"   {path}")
        if len(gopher_result.get('hierarchy', [])) > 10:
            print(f"   ... and {len(gopher_result['hierarchy']) - 10} more")
    except json.JSONDecodeError:
        print(f"⚠️  Raw response (not JSON): {response3[:500]}")
    
    # Step 4: Format for database
    print("\n📝 Step 4: Parse and format hierarchy paths")
    print("-" * 40)
    prompt4 = f"""You are a data formatter. Convert this JSON hierarchy to a clean list:

{response3}

Extract the "hierarchy" array and output each path on a new line.
Remove the ROOT/ prefix from each path.
Format as: CATEGORY/SUBCATEGORY/SKILL

Example:
TECHNICAL/PROGRAMMING/PYTHON
TECHNICAL/DATABASE/SQL
SOFT_SKILLS/COMMUNICATION

Output ONLY the formatted paths, nothing else."""
    
    response4 = executor.call_actor('phi3:latest', prompt4, {'gopher_result': response3})
    print(f"✓ Formatted paths:")
    print(response4[:500])
    
    # Step 5: Extract skill list
    print("\n📦 Step 5: Create skill keywords array")
    print("-" * 40)
    prompt5 = f"""From these hierarchy paths:

{response4}

Extract ONLY the leaf skills (the last part after the final slash).
Output as a JSON array.

Example input:
TECHNICAL/PROGRAMMING/PYTHON
TECHNICAL/DATABASE/SQL

Example output:
["python", "sql"]

Provide ONLY the JSON array, nothing else."""
    
    response5 = executor.call_actor('phi3:latest', prompt5, {'hierarchy_paths': response4})
    print(f"✓ Skill keywords:")
    print(response5)
    
    # Validate JSON
    try:
        skills = json.loads(response5)
        print(f"\n✅ SUCCESS! Extracted {len(skills)} skills")
        return True
    except json.JSONDecodeError:
        print(f"\n⚠️  Warning: Skills not valid JSON")
        return False

if __name__ == '__main__':
    job_id = sys.argv[1] if len(sys.argv) > 1 else '15929'
    success = test_recipe_1121(job_id)
    sys.exit(0 if success else 1)
