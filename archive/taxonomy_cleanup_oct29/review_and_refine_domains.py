#!/usr/bin/env python3
"""
Have Qwen review and refine its own functional domain categorization.
Self-correction pass to fix obvious misplacements.
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

def review_domain_batch(domain_name, skills, all_domains):
    """Ask Qwen to review skills in a domain and suggest corrections"""
    
    prompt = f"""You are reviewing your OWN categorization work. Be critical and honest about mistakes.

DOMAIN BEING REVIEWED: "{domain_name}"

SKILLS CURRENTLY IN THIS DOMAIN:
{json.dumps(skills[:30], indent=2)}  

ALL AVAILABLE DOMAINS:
1. Software & Technology - programming, development, APIs, code
2. Data & Analytics - data analysis, BI, machine learning, statistics
3. Infrastructure & Cloud - networking, cloud, DevOps, system administration
4. Security & Risk - cybersecurity, compliance, risk management, AML
5. Finance & Accounting - accounting, budgeting, financial analysis, tax, audit
6. Business Operations - operations, supply chain, quality, project management, marketing
7. Leadership & Strategy - directing people/initiatives, strategic planning, change management
8. Communication & Soft Skills - language, teamwork, stakeholder management, negotiation
9. Domain Expertise - industry-specific (healthcare, legal, military, environmental)

REVIEW TASK:
For each skill above, determine if it BELONGS in "{domain_name}" or should be MOVED elsewhere.

Common mistakes to look for:
- Technical tools (Excel, Bash, automation) in soft skills → Should be Software/Infrastructure/Data
- Audit skills in Leadership → Should be Finance & Accounting
- Marketing/Sales in Communication → Should be Business Operations
- Office tools (MS Office) in Professional Skills → Should be Data & Analytics or Business Operations

Return JSON array with ONLY skills that should be MOVED (if all correct, return []):
[
  {{
    "skill_id": "SKILL_ID",
    "current_domain": "{domain_name}",
    "correct_domain_num": 1-9,
    "reasoning": "Why it should move"
  }}
]

Be honest. If you made mistakes, correct them now.

Respond with ONLY the JSON array ([] if no changes needed)."""

    try:
        response = ask_llm(prompt)
        corrections = parse_json_response(response)
        return corrections if corrections else []
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return []

def main():
    print("=" * 80)
    print("🔍 QWEN SELF-REVIEW: Refining Functional Domain Categorization")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print("Strategy: Let Qwen review its own work and fix obvious mistakes\n")
    
    # Load previous categorization
    with open('/tmp/functional_domains_preview.json', 'r') as f:
        data = json.load(f)
    
    domains = data['domains']
    categorization = data['categorization']
    
    # Group by domain
    domain_skills = defaultdict(list)
    skill_map = {}  # skill_id -> full item
    
    for item in categorization:
        domain_num = item['domain']
        domain_name = domains[str(domain_num)]
        domain_skills[domain_name].append(item)
        skill_map[item['skill_id']] = item
    
    print(f"📋 Loaded {len(categorization)} categorized skills")
    print(f"📂 Organized into {len(domain_skills)} domains\n")
    
    all_corrections = []
    
    # Review each domain
    for domain_name in sorted(domain_skills.keys()):
        skills = domain_skills[domain_name]
        count = len(skills)
        
        print(f"🔍 Reviewing: {domain_name} ({count} skills)")
        
        # Review in batches if too large
        batch_size = 30
        domain_corrections = []
        
        for i in range(0, len(skills), batch_size):
            batch = skills[i:i+batch_size]
            if len(skills) > batch_size:
                print(f"   Processing batch {i//batch_size + 1}/{(len(skills) + batch_size - 1)//batch_size}...")
            
            corrections = review_domain_batch(domain_name, batch, domains)
            domain_corrections.extend(corrections)
        
        if domain_corrections:
            print(f"   ⚠️  Found {len(domain_corrections)} skills to move")
            for corr in domain_corrections[:5]:  # Show first 5
                new_domain = domains.get(str(corr['correct_domain_num']), 'Unknown')
                print(f"      • {corr['skill_id']} → {new_domain}")
                print(f"        Reason: {corr['reasoning'][:60]}...")
            if len(domain_corrections) > 5:
                print(f"      ... and {len(domain_corrections) - 5} more")
            all_corrections.extend(domain_corrections)
        else:
            print(f"   ✓ All correct")
        
        print()
    
    # Apply corrections
    print("=" * 80)
    print(f"📊 REVIEW SUMMARY")
    print("=" * 80)
    print(f"Total corrections: {len(all_corrections)}")
    
    if all_corrections:
        # Group corrections by target domain
        corrections_by_target = defaultdict(list)
        for corr in all_corrections:
            target_domain = domains.get(str(corr['correct_domain_num']), 'Unknown')
            corrections_by_target[target_domain].append(corr)
        
        print(f"\nCorrections by target domain:")
        for target_domain, corrs in sorted(corrections_by_target.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {target_domain}: {len(corrs)} skills incoming")
        
        # Apply corrections to categorization
        for corr in all_corrections:
            skill_id = corr['skill_id']
            if skill_id in skill_map:
                skill_map[skill_id]['domain'] = corr['correct_domain_num']
                skill_map[skill_id]['reasoning'] = corr['reasoning']
        
        # Rebuild corrected categorization
        corrected_categorization = list(skill_map.values())
        
        # Recalculate distribution
        corrected_domain_counts = defaultdict(int)
        for item in corrected_categorization:
            domain_num = item['domain']
            domain_name = domains[str(domain_num)]
            corrected_domain_counts[domain_name] += 1
        
        print(f"\n📊 REVISED DISTRIBUTION:")
        print("-" * 80)
        for domain_name in sorted(corrected_domain_counts.keys()):
            count = corrected_domain_counts[domain_name]
            percentage = (count / len(corrected_categorization) * 100)
            bar = "█" * int(percentage / 2)
            print(f"{domain_name:40} {count:4} ({percentage:5.1f}%) {bar}")
        
        # Save corrected version
        output_file = '/tmp/functional_domains_corrected.json'
        with open(output_file, 'w') as f:
            json.dump({
                'domains': domains,
                'categorization': corrected_categorization,
                'corrections_applied': len(all_corrections),
                'distribution': {name: corrected_domain_counts[name] for name in domains.values()},
                'total_categorized': len(corrected_categorization),
                'total_skills': data['total_skills']
            }, f, indent=2)
        
        print(f"\n💾 Corrected categorization saved to: {output_file}")
    else:
        print("\n✓ No corrections needed - original categorization was accurate!")
    
    print("=" * 80)

if __name__ == '__main__':
    main()
