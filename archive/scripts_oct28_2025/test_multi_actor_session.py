#!/usr/bin/env python3
"""
Test Recipe: skill_gopher Integration Test
Demonstrates multi-actor session with helper support
"""

import json
from universal_executor import UniversalExecutor

def test_multi_actor_session():
    """
    Simulates a session with:
    - Primary actor: phi3:latest (extracts key info)
    - Helper actor: skill_gopher (builds hierarchy)
    """
    
    executor = UniversalExecutor()
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  TEST: Multi-Actor Session with skill_gopher Helper             ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    # Sample job description
    job_description = """
    Senior Full Stack Developer
    
    We're seeking an experienced developer with:
    - 5+ years Python (Django, Flask)
    - Strong PostgreSQL and database design
    - React and modern JavaScript
    - Docker, Kubernetes deployment
    - CI/CD pipelines (GitLab CI, Jenkins)
    - Agile/Scrum experience
    - Excellent communication skills
    """
    
    print("📄 Job Description:")
    print(job_description)
    print("\n" + "="*70 + "\n")
    
    # ========================================
    # Instruction 1: Extract key requirements
    # ========================================
    print("🤖 INSTRUCTION 1: Extract Requirements (phi3:latest)")
    print("-" * 70)
    
    prompt_1 = f"""Extract the key technical requirements from this job:

{job_description}

List only the technical skills and tools mentioned. Be concise."""
    
    try:
        response_1 = executor.call_actor('phi3:latest', prompt_1)
        print("✅ Response:")
        print(response_1)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("\n" + "="*70 + "\n")
    
    # ========================================
    # Instruction 2: Build skill hierarchy with Gopher
    # ========================================
    print("🐹 INSTRUCTION 2: Build Hierarchy (skill_gopher helper)")
    print("-" * 70)
    
    # This simulates using {{SKILL_GOPHER_URL}} in template
    # In real session executor, this would be injected from session_actors
    
    context = {
        'job_description': job_description,
        'job_title': 'Senior Full Stack Developer'
    }
    
    try:
        response_2 = executor.call_actor(
            'skill_gopher', 
            job_description,
            context=context
        )
        
        # Parse JSON response
        gopher_result = json.loads(response_2)
        
        print("✅ Gopher Response:")
        print(f"   Nodes explored: {gopher_result['stats']['nodes_explored']}")
        print(f"   Leaf skills: {gopher_result['stats']['leaf_nodes']}")
        print(f"\n   Hierarchy:")
        for path in gopher_result['hierarchy']:
            depth = path.count('/')
            indent = "     " + ("  " * depth)
            node = path.split('/')[-1]
            print(f"{indent}📂 {node}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("\n" + "="*70 + "\n")
    
    # ========================================
    # Instruction 3: Format final output
    # ========================================
    print("🤖 INSTRUCTION 3: Format Output (phi3:latest)")
    print("-" * 70)
    
    prompt_3 = f"""Given this skill hierarchy:

{chr(10).join(gopher_result['hierarchy'])}

Write a brief summary of the skill categories found (2-3 sentences)."""
    
    try:
        response_3 = executor.call_actor('phi3:latest', prompt_3)
        print("✅ Response:")
        print(response_3)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("\n" + "="*70)
    print("✅ MULTI-ACTOR SESSION COMPLETE!")
    print("="*70)
    print("\n📊 Summary:")
    print(f"   • Used 2 actors (phi3:latest + skill_gopher)")
    print(f"   • Executed 3 instructions")
    print(f"   • skill_gopher acted as HELPER (not primary)")
    print(f"   • Demonstrates session_actors pattern")
    
    executor.close()


if __name__ == "__main__":
    test_multi_actor_session()
