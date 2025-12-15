#!/usr/bin/env python3
"""
Test Recipe 1121: Gopher Skill Extraction
Executes the actual recipe from database with proper instruction flow
"""

import sys
import json
from universal_executor import UniversalExecutor

def test_recipe_1121(job_id='15929'):
    """Test Recipe 1121 with a single job using actual DB instructions"""
    
    executor = UniversalExecutor()
    
    # Get job description
    job_desc = executor.get_job_description(job_id)
    if not job_desc:
        print(f"❌ Job {job_id} not found")
        return False
    
    print(f"🎯 Testing Recipe 1121 with Job {job_id}")
    print(f"📄 Job description: {len(job_desc)} chars")
    print("=" * 80)
    
    # Fetch instructions from database
    with executor.conn.cursor() as cur:
        cur.execute("""
            SELECT 
                i.instruction_id,
                i.step_number,
                i.step_description,
                i.prompt_template,
                COALESCE(i.delegate_actor_id, s.actor_id) as actor_id
            FROM instructions i
            JOIN sessions s ON i.session_id = s.session_id
            WHERE s.session_id = 9121
            ORDER BY i.step_number
        """)
        instructions = cur.fetchall()
    
    if not instructions:
        print("❌ No instructions found for session 9121")
        return False
    
    # Execute each instruction
    context = {
        'job_id': job_id,
        'job_description': job_desc,
        'extracted_summary': ''  # NULL in DB
    }
    previous_response = job_desc
    
    for instr_id, step_num, step_desc, prompt_template, actor_id in instructions:
        print(f"\n📍 Step {step_num}: {step_desc}")
        print(f"   Actor: {actor_id}")
        print("-" * 40)
        
        # Render prompt with context
        prompt = prompt_template
        
        # Replace template variables
        prompt = prompt.replace('{{job_id}}', str(job_id))
        prompt = prompt.replace('{{job_description}}', context['job_description'])
        prompt = prompt.replace('{{extracted_summary}}', context['extracted_summary'])
        prompt = prompt.replace('{{PREVIOUS_RESPONSE}}', previous_response)
        
        # Execute with appropriate actor
        try:
            response = executor.call_actor(actor_id, prompt, context)
            previous_response = response
            
            # Show response preview
            if actor_id == 'skill_gopher':
                # Parse JSON output from gopher
                try:
                    gopher_data = json.loads(response)
                    print(f"   ✓ Nodes explored: {gopher_data.get('stats', {}).get('nodes_explored', 'N/A')}")
                    print(f"   ✓ Hierarchy paths: {len(gopher_data.get('hierarchy', []))}")
                    print(f"   🌲 Sample paths:")
                    for path in gopher_data.get('hierarchy', [])[:5]:
                        print(f"      {path}")
                except json.JSONDecodeError:
                    print(f"   ⚠️ Response (first 200 chars): {response[:200]}")
            else:
                # For phi3 responses
                print(f"   ✓ Response length: {len(response)} chars")
                preview = response.strip()[:300]
                if '\n' in preview:
                    # Show first few lines
                    lines = preview.split('\n')[:5]
                    for line in lines:
                        if line.strip():
                            print(f"      {line}")
                    if len(preview) > 300 or preview.count('\n') > 5:
                        print(f"      ...")
                else:
                    print(f"      {preview}")
                    if len(response) > 300:
                        print(f"      ...")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    # Final validation - check if last response is valid JSON array
    print("\n" + "=" * 80)
    print("🎯 FINAL RESULT:")
    print("-" * 40)
    
    # Strip markdown code blocks if present
    cleaned_response = previous_response.strip()
    if cleaned_response.startswith('```'):
        # Remove ```json and ``` markers
        lines = cleaned_response.split('\n')
        cleaned_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_response
    
    try:
        skills = json.loads(cleaned_response.strip())
        if isinstance(skills, list):
            print(f"✅ SUCCESS! Extracted {len(skills)} skills:")
            for i, skill in enumerate(skills[:10], 1):
                print(f"   {i}. {skill}")
            if len(skills) > 10:
                print(f"   ... and {len(skills) - 10} more")
            print(f"\n📦 Final JSON array:")
            print(json.dumps(skills, indent=2))
            return True
        else:
            print(f"⚠️ Response is JSON but not an array: {type(skills)}")
            print(previous_response)
            return False
    except json.JSONDecodeError as e:
        print(f"⚠️ Final response is not valid JSON:")
        print(previous_response)
        print(f"\nError: {e}")
        return False

if __name__ == '__main__':
    job_id = sys.argv[1] if len(sys.argv) > 1 else '15929'
    success = test_recipe_1121(job_id)
    sys.exit(0 if success else 1)
