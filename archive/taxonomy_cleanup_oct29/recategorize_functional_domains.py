#!/usr/bin/env python3
"""
Recategorize skills into functional domains using Qwen.
Preview-only mode - doesn't modify database.
"""

import psycopg2
import json
import subprocess
from collections import defaultdict

# Database connection
DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost'
}

# LLM settings
LLM_MODEL = "qwen2.5:7b"

def ask_llm(prompt):
    """Ask LLM and return response"""
    result = subprocess.run(
        ['ollama', 'run', LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        raise Exception(f"Ollama error: {result.stderr}")
    
    return result.stdout.strip()

def parse_json_response(response):
    """Extract JSON from LLM response"""
    response = response.strip().replace('```json', '').replace('```', '').strip()
    
    start_idx = response.find('[')
    end_idx = response.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        return json.loads(json_text)
    
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        json_text = response[start_idx:end_idx+1]
        return json.loads(json_text)
    
    raise ValueError(f"No JSON found in response")

def get_leaf_skills(conn):
    """Get all leaf skills (actual skills, not categories)"""
    cur = conn.cursor()
    
    # Get leaf skills - those that appear in hierarchy but aren't parents
    cur.execute("""
        SELECT DISTINCT sa.skill, sa.display_name
        FROM skill_aliases sa
        WHERE sa.skill IN (
            -- Skills that are in hierarchy
            SELECT skill FROM skill_hierarchy
        )
        AND sa.skill NOT IN (
            -- But not parents
            SELECT DISTINCT parent_skill FROM skill_hierarchy WHERE parent_skill IS NOT NULL
        )
        ORDER BY sa.display_name
    """)
    
    skills = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    cur.close()
    
    return skills

def categorize_batch(skills_batch):
    """Ask Qwen to categorize a batch of skills into functional domains"""
    
    prompt = f"""You are organizing skills into FUNCTIONAL DOMAINS based on what the work achieves.

PROPOSED DOMAINS:
1. Software & Technology - building/maintaining software systems (programming, development, APIs)
2. Data & Analytics - extracting insights from data (data analysis, BI, machine learning)
3. Infrastructure & Cloud - managing IT infrastructure (networking, cloud, DevOps, system admin)
4. Security & Risk - protecting assets and managing risk (cybersecurity, compliance, risk management)
5. Finance & Accounting - managing money (accounting, budgeting, financial analysis, tax)
6. Business Operations - running business processes (operations, supply chain, quality, project mgmt)
7. Leadership & Strategy - directing people/initiatives (leadership, change mgmt, strategic planning)
8. Communication & Collaboration - working with others (communication, teamwork, stakeholder mgmt)
9. Domain Expertise - industry-specific knowledge (healthcare, legal, military, environmental)
10. Professional Skills - foundational work skills (research, analysis, documentation, problem-solving)

SKILLS TO CATEGORIZE:
{json.dumps(skills_batch, indent=2)}

For each skill, determine the SINGLE BEST functional domain (1-10 from above).

Return JSON array:
[
  {{"skill_id": "SKILL_ID", "domain": 1, "reasoning": "brief reason"}},
  ...
]

Use domain numbers 1-10. Be decisive - pick the PRIMARY function.

Respond with ONLY the JSON array."""

    try:
        response = ask_llm(prompt)
        categorized = parse_json_response(response)
        return categorized if categorized else []
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return []

def main():
    print("=" * 80)
    print("🔄 FUNCTIONAL DOMAIN RECATEGORIZATION - PREVIEW MODE")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print("Note: This is PREVIEW ONLY - no database changes will be made\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get all leaf skills
    print("📋 Extracting leaf skills...")
    leaf_skills = get_leaf_skills(conn)
    print(f"   Found {len(leaf_skills)} leaf skills\n")
    
    # Domain mapping
    domains = {
        1: "Software & Technology",
        2: "Data & Analytics",
        3: "Infrastructure & Cloud",
        4: "Security & Risk",
        5: "Finance & Accounting",
        6: "Business Operations",
        7: "Leadership & Strategy",
        8: "Communication & Collaboration",
        9: "Domain Expertise",
        10: "Professional Skills"
    }
    
    # Process in batches of 30
    batch_size = 30
    all_categorized = []
    domain_counts = defaultdict(list)
    
    for i in range(0, len(leaf_skills), batch_size):
        batch = leaf_skills[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(leaf_skills) + batch_size - 1) // batch_size
        
        print(f"🤖 Processing batch {batch_num}/{total_batches} ({len(batch)} skills)...")
        
        categorized = categorize_batch(batch)
        
        if categorized:
            all_categorized.extend(categorized)
            for item in categorized:
                domain_num = item.get('domain')
                if domain_num in domains:
                    domain_counts[domain_num].append(item['skill_id'])
            print(f"   ✓ Categorized {len(categorized)} skills\n")
        else:
            print(f"   ⚠️  Failed to categorize batch\n")
    
    # Show distribution
    print("\n" + "=" * 80)
    print("📊 PROPOSED DISTRIBUTION")
    print("=" * 80)
    
    for domain_num in sorted(domains.keys()):
        domain_name = domains[domain_num]
        count = len(domain_counts[domain_num])
        percentage = (count / len(leaf_skills) * 100) if leaf_skills else 0
        print(f"\n{domain_num}. {domain_name}")
        print(f"   Count: {count} skills ({percentage:.1f}%)")
        
        if count > 0 and count <= 10:
            # Show all if 10 or fewer
            for skill_id in domain_counts[domain_num]:
                skill_name = next((s['name'] for s in leaf_skills if s['id'] == skill_id), skill_id)
                print(f"      • {skill_name}")
        elif count > 10:
            # Show first 5
            for skill_id in domain_counts[domain_num][:5]:
                skill_name = next((s['name'] for s in leaf_skills if s['id'] == skill_id), skill_id)
                print(f"      • {skill_name}")
            print(f"      ... and {count - 5} more")
    
    # Save detailed results
    output_file = '/tmp/functional_domains_preview.json'
    with open(output_file, 'w') as f:
        json.dump({
            'domains': domains,
            'categorization': all_categorized,
            'distribution': {domains[k]: len(v) for k, v in domain_counts.items()},
            'total_categorized': len(all_categorized),
            'total_skills': len(leaf_skills)
        }, f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"💾 Detailed results saved to: {output_file}")
    print("\nNext steps:")
    print("  1. Review the distribution above")
    print("  2. Check if domains make sense")
    print("  3. If good, we can apply this reorganization to the database")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()
