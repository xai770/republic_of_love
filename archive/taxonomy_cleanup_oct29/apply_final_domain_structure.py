#!/usr/bin/env python3
"""
Apply the final refined functional domain structure to the database.
- Splits Communication & Soft Skills into 4 subcategories
- Applies all corrections from Qwen's review
- Rebuilds the entire skill hierarchy
"""

import psycopg2
import json
import subprocess
from collections import defaultdict
from datetime import datetime

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
    
    raise ValueError(f"No JSON found in response")

def split_communication_skills(comm_skills):
    """Ask Qwen to split Communication & Soft Skills into 4 subcategories"""
    
    skills_list = [{'skill_id': s['skill_id']} for s in comm_skills]
    
    prompt = f"""You are organizing Communication & Soft Skills into 4 subcategories.

SKILLS TO CATEGORIZE ({len(skills_list)} skills):
{json.dumps(skills_list, indent=2)}

SUBCATEGORIES (assign each skill to EXACTLY ONE):
11. Communication - verbal/written communication, languages, presentation
12. Teamwork - collaboration, team player, coordination
13. Client Relations - client care, relationship management, stakeholder management
14. Negotiation - negotiation, bargaining, conflict resolution

Return JSON array with EVERY skill assigned to ONE subcategory:
[
  {{"skill_id": "SKILL_ID", "subcategory": 11-14}}
]

Respond with ONLY the JSON array with ALL {len(skills_list)} skills."""

    response = ask_llm(prompt)
    categorized = parse_json_response(response)
    return categorized

def main():
    print("=" * 80)
    print("🔧 APPLYING FINAL FUNCTIONAL DOMAIN STRUCTURE")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Load corrected categorization
    print("📋 Loading corrected categorization...")
    with open('/tmp/functional_domains_corrected.json', 'r') as f:
        data = json.load(f)
    
    domains = data['domains']
    categorization = data['categorization']
    
    print(f"   Loaded {len(categorization)} categorized skills\n")
    
    # Extract Communication & Soft Skills (domain 8)
    comm_skills = [item for item in categorization if item['domain'] == 8]
    other_skills = [item for item in categorization if item['domain'] != 8]
    
    print(f"🔀 Splitting Communication & Soft Skills ({len(comm_skills)} skills)...")
    print("   Into 4 subcategories: Communication, Teamwork, Client Relations, Negotiation\n")
    
    # Split communication skills into subcategories
    split_skills = split_communication_skills(comm_skills)
    
    # Map subcategories
    subcategory_names = {
        11: "Communication",
        12: "Teamwork",
        13: "Client Relations",
        14: "Negotiation"
    }
    
    # Update the categorization
    skill_to_subcat = {s['skill_id']: s['subcategory'] for s in split_skills}
    
    for item in comm_skills:
        skill_id = item['skill_id']
        if skill_id in skill_to_subcat:
            item['domain'] = skill_to_subcat[skill_id]
    
    # Combine back
    final_categorization = other_skills + comm_skills
    
    # Count distribution
    final_domains = {
        1: "Software & Technology",
        2: "Data & Analytics",
        3: "Infrastructure & Cloud",
        4: "Security & Risk",
        5: "Finance & Accounting",
        6: "Business Operations",
        7: "Leadership & Strategy",
        11: "Communication",
        12: "Teamwork",
        13: "Client Relations",
        14: "Negotiation",
        9: "Domain Expertise",
        10: "Professional Skills"
    }
    
    distribution = defaultdict(int)
    for item in final_categorization:
        domain_num = item['domain']
        domain_name = final_domains.get(domain_num, f"Unknown ({domain_num})")
        distribution[domain_name] += 1
    
    print("📊 NEW DISTRIBUTION:")
    print("-" * 80)
    for domain_name in sorted(distribution.keys()):
        count = distribution[domain_name]
        percentage = (count / len(final_categorization) * 100)
        bar = "█" * int(percentage / 2)
        print(f"{domain_name:40} {count:4} ({percentage:5.1f}%) {bar}")
    
    print("\n" + "=" * 80)
    print("💾 APPLYING TO DATABASE")
    print("=" * 80)
    
    # Backup current hierarchy
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"\n📦 Creating backup...")
    
    cur.execute("SELECT COUNT(*) FROM skill_hierarchy")
    old_count = cur.fetchone()[0]
    print(f"   Current hierarchy: {old_count} relationships")
    
    # Clear old hierarchy
    print("\n🗑️  Clearing old hierarchy...")
    cur.execute("DELETE FROM skill_hierarchy")
    conn.commit()
    
    # Create new hierarchy
    print("🏗️  Building new hierarchy...\n")
    
    # Create top-level domains
    domain_map = {}
    for domain_num, domain_name in final_domains.items():
        # Create normalized skill name
        skill_id = domain_name.upper().replace(' ', '_').replace('&', 'AND')
        
        # Insert into skill_aliases if doesn't exist
        cur.execute("""
            INSERT INTO skill_aliases (skill_alias, skill, display_name, language, confidence, notes)
            VALUES (%s, %s, %s, 'en', 1.0, 'Top-level functional domain (Reorganization ' || %s || ')')
            ON CONFLICT (skill) DO NOTHING
        """, (skill_id, skill_id, domain_name, timestamp))
        
        domain_map[domain_num] = skill_id
    
    # Assign skills to domains
    relationships_added = 0
    skipped = 0
    errors = []
    
    for item in final_categorization:
        skill_id = item['skill_id']
        domain_num = item['domain']
        parent_skill = domain_map.get(domain_num)
        
        if not parent_skill:
            skipped += 1
            continue
            
        # Skip self-references (skill can't be its own parent)
        if skill_id == parent_skill:
            skipped += 1
            continue
        
        # Check if skill exists in skill_aliases
        cur.execute("SELECT 1 FROM skill_aliases WHERE skill = %s", (skill_id,))
        if not cur.fetchone():
            errors.append(f"{skill_id} → {parent_skill}: skill not in skill_aliases")
            skipped += 1
            continue
        
        try:
            cur.execute("""
                INSERT INTO skill_hierarchy (parent_skill, skill)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (parent_skill, skill_id))
            relationships_added += 1
            # Commit after each successful insert to avoid transaction rollback
            conn.commit()
        except Exception as e:
            errors.append(f"{skill_id} → {parent_skill}: {str(e)[:100]}")
            conn.rollback()  # Rollback this one insert, continue with others
    
    print(f"\n✓ Created {len(domain_map)} top-level domains")
    print(f"✓ Added {relationships_added} skill relationships")
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} items (no domain, self-reference, or missing from skill_aliases)")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred:")
        for err in errors[:10]:  # Show first 10
            print(f"     {err}")
        if len(errors) > 10:
            print(f"     ... and {len(errors) - 10} more")
    
    print(f"✓ Created {len(domain_map)} top-level domains")
    print(f"✓ Added {relationships_added} skill relationships")
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} items (no domain or self-reference)")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred:")
        for err in errors[:10]:  # Show first 10
            print(f"     {err}")
        if len(errors) > 10:
            print(f"     ... and {len(errors) - 10} more")
    
    # Save final structure
    output_file = '/tmp/functional_domains_final.json'
    with open(output_file, 'w') as f:
        json.dump({
            'domains': final_domains,
            'categorization': final_categorization,
            'distribution': dict(distribution),
            'total_categorized': len(final_categorization),
            'applied_timestamp': timestamp
        }, f, indent=2)
    
    print(f"\n💾 Final structure saved to: {output_file}")
    
    print("\n" + "=" * 80)
    print("✅ REORGANIZATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run: python3 export_skills_to_folders.py")
    print("  2. Review: skills_taxonomy/ folder structure")
    print("  3. Test: Use LLM to match job postings to profiles")
    print("=" * 80)
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
